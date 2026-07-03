"""Multi-strategy mix v2 — with the WINNING IV-filtered strangle + a gap-down-fade sleeve.
Goal: reach Sharpe>2 that ALSO holds up out-of-sample (v1 was 2.08 build / 0.29 fwd).

Sleeves (all fixed sizing, daily P&L in rupees):
  A  Intraday CE-selling (>20DMA + 2.5x stop)              short-vol, short-delta
  B  Weekly strangle, 0.2d, IV-rank>=0.4, no stop (WINNER) short-vol, delta-neutral
  C  Overnight drift (hold NIFTY close->next open)         LONG-delta
  D  Gap-down FADE (buy big gap-down open, exit EOD)       LONG, event-driven
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

import chain
import sell_ce_enhanced as sce
import engine_weekly as ew

pd.set_option("display.width", 200)
START, SPLIT, END = dt.date(2021, 1, 1), dt.date(2025, 12, 31), dt.date(2026, 6, 2)
NOTIONAL = 3_00_000.0


def daily_index():
    spot = chain.load_index()
    days = sorted({d for d in spot.index.date if START <= d <= END})
    return pd.DatetimeIndex(pd.to_datetime(days))


def sleeve_A():
    df = sce.run(sce.Cfg(stop_mult=2.5), START, END)
    s = df.groupby(df["day"])["net_pnl"].sum(); s.index = pd.to_datetime(s.index)
    return s


def sleeve_B(spot, exps):
    dfeat = ew.daily_features(spot)
    _, ivrank = ew.straddle_pct_by_expiry(spot, exps, ew.WCfg())
    ivrank = ivrank.to_dict()
    cfg = ew.WCfg(structure="strangle", ce_delta=0.2, pe_delta=0.2,
                  stop_mult=0.0, iv_rank_min=0.4, pe_below_50dma="none")
    df = ew.run_cfg(spot, exps, cfg, dfeat, ivrank, START, END)
    s = df.groupby("exp")["net_pnl"].sum(); s.index = pd.to_datetime(s.index)
    return s


def sleeve_C(spot):
    g = spot.groupby(spot.index.date)
    d = pd.DataFrame({"open": g["open"].first(), "close": g["close"].last()})
    d.index = pd.to_datetime([pd.Timestamp(x) for x in d.index])
    c2o = d["open"].shift(-1) / d["close"] - 1
    return (c2o * NOTIONAL).shift(1).dropna()


def sleeve_D(spot):
    """Gap-down fade: on days gapping down >0.5%, buy at open, exit close (long)."""
    g = spot.groupby(spot.index.date)
    d = pd.DataFrame({"open": g["open"].first(), "close": g["close"].last()})
    d.index = pd.to_datetime([pd.Timestamp(x) for x in d.index])
    gap = d["open"] / d["close"].shift(1) - 1
    o2c = d["close"] / d["open"] - 1
    pnl = pd.Series(0.0, index=d.index)
    mask = gap < -0.005
    pnl[mask] = (o2c[mask] * NOTIONAL)
    return pnl[mask]


def ann_sharpe(x):
    x = x.dropna()
    return x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0.0


def maxdd(cum):
    peak = np.maximum.accumulate(cum)
    return float(((cum - peak) / np.maximum(np.abs(peak), 1)).min())


if __name__ == "__main__":
    spot = chain.load_index()
    _, exps = chain.build_expiry_index()
    idx = daily_index()
    A = sleeve_A().reindex(idx).fillna(0.0)
    B = sleeve_B(spot, exps).reindex(idx).fillna(0.0)
    C = sleeve_C(spot).reindex(idx).fillna(0.0)
    D = sleeve_D(spot).reindex(idx).fillna(0.0)
    M = pd.DataFrame({"A_CEsell": A, "B_strangleIV": B, "C_overnight": C, "D_gapfade": D})

    print("=== standalone sleeves (ann.Sharpe on daily P&L; BUILD / FWD) ===")
    for c in M.columns:
        s = M[c]; b = s[s.index.date <= SPLIT]; f = s[s.index.date > SPLIT]
        print(f"  {c:14s}: ALL {ann_sharpe(s):5.2f} | BUILD {ann_sharpe(b):5.2f} | "
              f"FWD {ann_sharpe(f):5.2f} | net Rs.{s.sum():>10,.0f} | active {int((s!=0).sum())}")

    print("\n=== CORRELATION (days where >=1 sleeve active) ===")
    act = M[(M != 0).any(axis=1)]
    print(act.corr().round(2).to_string())

    stds = M.std().replace(0, np.nan)
    Z = M / stds

    def rep(series, name):
        b = series[series.index.date <= SPLIT]; f = series[series.index.date > SPLIT]
        print(f"  {name:26s}: ALL {ann_sharpe(series):4.2f} | BUILD {ann_sharpe(b):4.2f} | "
              f"FWD {ann_sharpe(f):4.2f} | maxDD {maxdd(series.cumsum()):.0%}")

    print("\n=== combined portfolios (risk-parity, ann. Sharpe) ===")
    rep(Z[["A_CEsell", "B_strangleIV"]].mean(axis=1), "short-vol only (A+B)")
    rep(Z[["A_CEsell", "B_strangleIV", "C_overnight"]].mean(axis=1), "A+B+C")
    rep(Z.mean(axis=1), "A+B+C+D (all four)")

    # grid-search weights on BUILD, then report FORWARD (robustness check)
    best, bser = None, None
    grid = np.arange(0, 1.01, 0.25)
    for wa in grid:
        for wb in grid:
            for wc in grid:
                wd = 1 - wa - wb - wc
                if wd < -1e-9 or wd > 1 + 1e-9:
                    continue
                s = wa*Z["A_CEsell"] + wb*Z["B_strangleIV"] + wc*Z["C_overnight"] + wd*Z["D_gapfade"]
                bs = ann_sharpe(s[s.index.date <= SPLIT])
                if best is None or bs > best[0]:
                    best, bser = (bs, wa, wb, wc, wd), s
    print(f"\n  best BUILD weights: A={best[1]:.2f} B={best[2]:.2f} C={best[3]:.2f} D={best[4]:.2f}")
    rep(bser, "best-weight mix")
    print("\nKEY CHECK: does the best mix's FORWARD Sharpe hold up (v1 collapsed 2.08->0.29)?")
