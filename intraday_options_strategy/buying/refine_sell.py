"""Refine the DEFINED-RISK iron condor with (a) IV-richness filter (straddle% rank)
and (b) trend avoidance (short-vol dies in trends). Test if these rescue it OOS.
Run all condors unfiltered, then apply filters post-hoc and compare build vs forward.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import replace

import numpy as np
import pandas as pd

import chain
from engine_sell import SellCfg, simulate

CAP = 3_00_000.0


def daily_ctx(spot):
    g = spot.groupby(spot.index.date)
    d = pd.DataFrame({"close": g["close"].last()})
    d.index = [pd.Timestamp(x).date() for x in d.index]
    d["ma20"] = d["close"].rolling(20).mean()
    d["ma50"] = d["close"].rolling(50).mean()
    d["ret20"] = d["close"].pct_change(20)
    return d


def collect(delta, start, end):
    cfg = replace(SellCfg(), structure="iron_condor", short_delta=delta,
                  strad_min=0.0)  # no filter here; filter post-hoc
    spot = chain.load_index()
    _, exps = chain.build_expiry_index()
    rows = []
    for exp in exps:
        if not (start <= exp <= end):
            continue
        try:
            tr = simulate(spot, exp, cfg)
        except Exception:
            continue
        if tr is None or tr.get("skip"):
            continue
        rows.append(tr)
    df = pd.DataFrame(rows)
    return df


def enrich(df, spot):
    d = daily_ctx(spot)
    df = df.copy()
    df["trend_dev"] = df["enter_day"].map(
        lambda x: (d.loc[x, "close"] / d.loc[x, "ma20"] - 1) if x in d.index and pd.notna(d.loc[x, "ma20"]) else np.nan)
    df["ret20"] = df["enter_day"].map(lambda x: d.loc[x, "ret20"] if x in d.index else np.nan)
    # straddle% rolling percentile over trailing 40 expiries
    df = df.sort_values("exp").reset_index(drop=True)
    df["strad_rank"] = df["strad_pct"].rolling(40, min_periods=10).apply(
        lambda w: (w.iloc[-1] >= w).mean(), raw=False)
    return df


def stats(df, label):
    if df.empty:
        print(f"  {label}: no trades"); return
    wr = df["win"].mean(); net = df["net_pnl"].sum()
    w = df[df["net_pnl"] > 0]["net_pnl"]; l = df[df["net_pnl"] <= 0]["net_pnl"]
    pf = w.sum() / abs(l.sum()) if l.sum() != 0 else np.inf
    d2 = df.sort_values("exp")
    eq = CAP + d2["net_pnl"].cumsum().values
    dd = ((eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)).min()
    r = d2["net_pnl"] / CAP
    tpy = len(df) / ((d2["exp"].iloc[-1] - d2["exp"].iloc[0]).days / 365.25 + 1e-9)
    sharpe = r.mean() / r.std() * np.sqrt(tpy) if r.std() > 0 and len(df) > 2 else 0
    print(f"  {label}: n={len(df)} WR={wr:.0%} net=Rs.{net:,.0f} PF={pf:.2f} "
          f"tot={net/CAP:+.1%} maxDD={dd:.0%} Sharpe={sharpe:.2f} worst=Rs.{df['net_pnl'].min():,.0f}")


if __name__ == "__main__":
    spot = chain.load_index()
    for delta in (0.12, 0.16):
        print("\n" + "=" * 74 + f"\nIRON CONDOR short_delta={delta}\n" + "=" * 74)
        allb = enrich(collect(delta, dt.date(2021, 1, 1), dt.date(2025, 12, 31)), spot)
        allf = enrich(collect(delta, dt.date(2026, 1, 1), dt.date(2026, 6, 2)), spot)

        print("[unfiltered]")
        stats(allb, "BUILD"); stats(allf, "FWD  ")

        # filter: rich vol (rank>=0.5) AND not strongly trending (|dev|<4%)
        def filt(df):
            return df[(df["strad_rank"] >= 0.5) & (df["trend_dev"].abs() <= 0.04)]
        print("[IV-rich (rank>=0.5) + trend-avoid (|dev|<=4%)]")
        stats(filt(allb), "BUILD"); stats(filt(allf), "FWD  ")

        # stricter: rank>=0.6 AND |dev|<3%
        def filt2(df):
            return df[(df["strad_rank"] >= 0.6) & (df["trend_dev"].abs() <= 0.03)]
        print("[stricter: rank>=0.6 + |dev|<=3%]")
        stats(filt2(allb), "BUILD"); stats(filt2(allf), "FWD  ")
