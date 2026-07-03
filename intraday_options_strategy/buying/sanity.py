"""Sanity test: prove we can pull real option prices and simulate one buy->exit.

Picks a sample trend day, finds the nearest weekly expiry, buys the ATM CE at
09:30, and walks the REAL 1-min option price path to an exit (target/stop/EOD).
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

import chain

STEP = 50  # NIFTY strike step


def atm_strike(spot: float) -> int:
    return int(round(spot / STEP) * STEP)


def opt_series(cdf: pd.DataFrame, strike: int, otype: str) -> pd.Series:
    s = cdf[(cdf["strike"] == strike) & (cdf["option_type"] == otype)]
    return s.set_index("t")["close"].sort_index()


def run_one(day: dt.date):
    exp = chain.nearest_expiry(day, min_dte=0, max_dte=7)
    if exp is None:
        print(f"{day}: no expiry"); return
    cdf = chain.day_chain(exp, day)
    if cdf.empty:
        print(f"{day}: chain empty for exp {exp}"); return
    idx = chain.load_index()
    day_spot = idx[idx.index.date == day]
    if day_spot.empty:
        print(f"{day}: no spot"); return

    # spot at 09:30
    entry_t = pd.Timestamp(day) + pd.Timedelta(hours=9, minutes=30)
    spot_now = day_spot.asof(entry_t)["close"]
    k = atm_strike(spot_now)
    ce = opt_series(cdf, k, "CE")
    pe = opt_series(cdf, k, "PE")
    if ce.empty:
        # snap to nearest available strike
        avail = sorted(cdf["strike"].unique())
        k = min(avail, key=lambda x: abs(x - spot_now))
        ce = opt_series(cdf, k, "CE")
        pe = opt_series(cdf, k, "PE")

    print(f"\n=== {day}  exp={exp} ({(exp-day).days} DTE)  spot@9:30={spot_now:.0f}  ATM K={k}")
    print(f"    chain: {cdf['strike'].nunique()} strikes, "
          f"CE bars={len(ce)} PE bars={len(pe)}, "
          f"day range {cdf['t'].min().time()}..{cdf['t'].max().time()}")
    if ce.empty:
        print("    no CE series"); return

    entry_px = ce.asof(entry_t)
    eod_px = ce.iloc[-1]
    hi = ce[ce.index >= entry_t].max()
    lo = ce[ce.index >= entry_t].min()
    print(f"    CE ATM entry@9:30 = {entry_px:.2f}  | intraday hi={hi:.2f} lo={lo:.2f} eod={eod_px:.2f}")
    print(f"    if bought & held to EOD: {(eod_px/entry_px-1)*100:+.1f}%  "
          f"| best-case exit at hi: {(hi/entry_px-1)*100:+.1f}%  "
          f"| worst at lo: {(lo/entry_px-1)*100:+.1f}%")


if __name__ == "__main__":
    # a few varied days across the sample
    for d in [dt.date(2024, 6, 4),   # big move day (election result)
              dt.date(2025, 3, 5),
              dt.date(2023, 9, 15),
              dt.date(2022, 1, 24),
              dt.date(2025, 11, 20)]:
        try:
            run_one(d)
        except Exception as e:
            print(f"{d}: ERROR {type(e).__name__}: {e}")
