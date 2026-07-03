"""Round 2 signal research (build set 2021-2025): the two remaining hopes for a
DIRECTIONAL option-buying edge.

  H-B1  Multi-day momentum: does a daily breakout / momentum signal predict a
        1-3 day forward move big enough (~>0.6-1.0%) for a few-DTE long option?
  H-B2  Cheap-vol conditioning: split intraday breakouts by whether the morning
        ATM straddle is CHEAP vs RICH (% of spot). Buyers should only win when
        vol is underpriced relative to the realized move.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

import chain

BUILD_END = dt.date(2025, 12, 31)
STEP = 50


def daily_from_1min(spot: pd.DataFrame) -> pd.DataFrame:
    g = spot.groupby(spot.index.date)
    d = pd.DataFrame({
        "open": g["open"].first(), "high": g["high"].max(),
        "low": g["low"].min(), "close": g["close"].last(),
    })
    d.index = pd.to_datetime(d.index)
    return d


def test_multiday_momentum(spot):
    d = daily_from_1min(spot)
    d = d[d.index.date <= BUILD_END]
    c = d["close"]
    ret1 = c.pct_change()
    hh20 = d["high"].rolling(20).max()
    ll20 = d["low"].rolling(20).min()
    ema10 = c.ewm(span=10, adjust=False).mean()
    ema20 = c.ewm(span=20, adjust=False).mean()

    sigs = {
        "breakout20_up": (c > hh20.shift(1)),
        "breakout20_dn": (c < ll20.shift(1)),
        "ema_up":  (ema10 > ema20) & (ema10.shift(1) <= ema20.shift(1)),
        "ema_dn":  (ema10 < ema20) & (ema10.shift(1) >= ema20.shift(1)),
        "bigday_up": (ret1 > 0.010),
        "bigday_dn": (ret1 < -0.010),
    }
    print("=" * 78)
    print("H-B1  MULTI-DAY MOMENTUM (signed forward return over N days)")
    print("=" * 78)
    fwd = {h: c.shift(-h) / c - 1 for h in (1, 2, 3, 5)}
    rows = []
    for name, mask in sigs.items():
        direction = 1 if name.endswith("_up") else -1
        idx = mask[mask].index
        row = {"signal": name, "n": len(idx)}
        for h in (1, 2, 3, 5):
            v = (direction * fwd[h].reindex(idx)).dropna()
            row[f"d{h}_mean"] = v.mean()
            row[f"d{h}_hit"] = (v > 0).mean()
        rows.append(row)
    a = pd.DataFrame(rows)
    fmt = {c_: "{:+.2%}".format for c_ in a.columns if c_.endswith("mean")}
    fmt.update({c_: "{:.0%}".format for c_ in a.columns if c_.endswith("hit")})
    print(a.to_string(index=False, formatters=fmt))
    print("Need ~>0.6-1.0% signed move for a few-DTE long option to clear theta+costs.\n")


def _atm(x):
    return int(round(x / STEP) * STEP)


def test_cheap_vol(spot):
    """For each build-set expiry, at ~3 DTE morning: ATM straddle % of spot, then
    the actual |spot move| from entry to expiry close. Are cheap-vol days the ones
    where realized >> implied (i.e., where a directional long option would pay)?"""
    print("=" * 78)
    print("H-B2  CHEAP-VOL: morning ATM straddle% vs realized move to expiry")
    print("=" * 78)
    _, exps = chain.build_expiry_index()
    exps = [e for e in exps if e <= BUILD_END]
    recs = []
    for exp in exps:
        df = chain.load_expiry(exp)
        tdays = sorted(df["trading_day"].unique())
        # pick an entry day ~3 trading days before expiry
        if len(tdays) < 4:
            continue
        entry_day = tdays[-4]  # ~3 sessions to expiry
        eday = dt.date.fromisoformat(entry_day)
        dte = (exp - eday).days
        cd = df[df["trading_day"] == entry_day]
        if cd.empty:
            continue
        t920 = pd.Timestamp(eday) + pd.Timedelta(hours=9, minutes=20)
        sub = cd[cd["t"] <= t920]
        if sub.empty:
            continue
        spot_row = spot[(spot.index.date == eday) & (spot.index <= t920)]
        if spot_row.empty:
            continue
        s0 = spot_row["close"].iloc[-1]
        k = _atm(s0)
        near = cd[(cd["strike"] == k)]
        ce = near[near["option_type"] == "CE"]
        pe = near[near["option_type"] == "PE"]
        ce = ce[ce["t"] <= t920]; pe = pe[pe["t"] <= t920]
        if ce.empty or pe.empty:
            continue
        straddle = ce["close"].iloc[-1] + pe["close"].iloc[-1]
        strad_pct = straddle / s0
        # realized: spot at expiry-day close
        exp_spot = spot[spot.index.date == exp]
        if exp_spot.empty:
            continue
        s1 = exp_spot["close"].iloc[-1]
        realized_move = abs(s1 / s0 - 1)
        # a perfect-direction ATM long intrinsic payoff vs premium paid (one leg ~ straddle/2)
        recs.append({"exp": exp, "dte": dte, "strad_pct": strad_pct,
                     "realized": realized_move, "edge": realized_move - strad_pct})
    r = pd.DataFrame(recs)
    print(f"n={len(r)} expiries")
    r["bucket"] = pd.qcut(r["strad_pct"], 4, labels=["cheapest", "cheap", "rich", "richest"])
    g = r.groupby("bucket", observed=True).agg(
        n=("exp", "size"), avg_strad_pct=("strad_pct", "mean"),
        avg_realized=("realized", "mean"), avg_edge=("edge", "mean"),
        pct_realized_gt_strad=("edge", lambda x: (x > 0).mean()))
    fmt = {"avg_strad_pct": "{:.2%}".format, "avg_realized": "{:.2%}".format,
           "avg_edge": "{:+.2%}".format, "pct_realized_gt_strad": "{:.0%}".format}
    print(g.to_string(formatters=fmt))
    print("\n'edge>0' = realized move exceeded the straddle premium (perfect-direction "
          "long option would profit). This is BEFORE the direction problem.")


if __name__ == "__main__":
    spot = chain.load_index()
    test_multiday_momentum(spot)
    test_cheap_vol(spot)
