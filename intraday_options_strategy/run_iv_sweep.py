"""Break-even IV analysis for short-premium sleeves.

Sweeps the IV-vs-VIX multiplier m (real ATM IV / India VIX). For each m we
re-price S2 (range straddle) and S3 (0DTE straddle) entries and exits at
sigma = m x VIX, keeping the REAL Nifty path. Reports per-sleeve WR / PF /
avg P&L per lot vs m, and the break-even m (smallest m with PF >= 1).

Interpretation: if a sleeve breaks even at m* and real-world ATM short-DTE IV
typically runs at multiplier m_real > m*, the sleeve is viable in reality even
though the m=1 (VIX-priced) base sim shows losses. This quantifies the edge
we need, BEFORE we have NSE option data to measure m_real directly.

Honest split: metrics reported IN-SAMPLE vs OOS (post 2022-12-16) separately.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest.engine_v2 import simulate_orders  # noqa: E402
from config import IS_FRACTION, PROCESSED_DIR, RESULTS_DIR  # noqa: E402
from features.horizon import day_features  # noqa: E402
from strategies.sleeves import (  # noqa: E402
    all_expiry_days, s2_range_premium, s3_zero_dte,
)

M_GRID = [1.0, 1.05, 1.10, 1.15, 1.20, 1.30, 1.50, 1.80]

t0 = time.time()
nifty = pd.read_parquet(PROCESSED_DIR / "nifty_1min.parquet")
vix = pd.read_parquet(PROCESSED_DIR / "vix_on_bars.parquet")["vix"]
filters = pd.read_parquet(PROCESSED_DIR / "filters.parquet")
days = pd.DatetimeIndex(pd.read_csv(PROCESSED_DIR / "trading_calendar.csv",
                                    parse_dates=["day"])["day"])
n_is = int(len(days) * IS_FRACTION)
oos_start = days[n_is]

dayf = day_features(nifty, vix)
expiry_days = all_expiry_days(days)
orders = {"S2": s2_range_premium(nifty, dayf, filters, expiry_days),
          "S3": s3_zero_dte(nifty, dayf, filters, expiry_days)}
print(f"setup {time.time()-t0:.0f}s; S2={len(orders['S2'])} S3={len(orders['S3'])} orders")


def metrics(tr: pd.DataFrame) -> dict:
    if not len(tr):
        return {"trades": 0, "wr": np.nan, "pf": np.nan, "avg": np.nan}
    pnl = tr["pnl_per_lot"] - tr["fixed_cost"]
    wins = pnl > 0
    gl = -pnl[~wins].sum()
    return {"trades": len(tr), "wr": float(wins.mean()),
            "pf": float(pnl[wins].sum() / gl) if gl > 0 else np.inf,
            "avg": float(pnl.mean())}


rows = []
for sleeve, ods in orders.items():
    for m in M_GRID:
        tr = simulate_orders(nifty, vix, ods, iv_mult=m)
        tr["day"] = tr["entry_dt"].dt.normalize()
        for seg, mask in [("IS", tr["day"] < oos_start), ("OOS", tr["day"] >= oos_start)]:
            r = metrics(tr[mask])
            rows.append({"sleeve": sleeve, "m": m, "seg": seg, **r})

res = pd.DataFrame(rows)
res.to_csv(RESULTS_DIR / "iv_sweep.csv", index=False)

print("\n=== IV break-even sweep (per lot, after costs) ===")
for sleeve in ["S2", "S3"]:
    print(f"\n--- {sleeve} ---")
    piv = res[res.sleeve == sleeve].pivot_table(
        index="m", columns="seg", values=["wr", "pf", "avg"])
    print(piv.round(3).to_string())
    for seg in ["IS", "OOS"]:
        sub = res[(res.sleeve == sleeve) & (res.seg == seg)].sort_values("m")
        be = sub[sub["pf"] >= 1.0]["m"].min()
        print(f"  {seg} break-even m (PF>=1): "
              f"{be if not np.isnan(be) else 'none in grid'}")
print(f"\nsaved -> {RESULTS_DIR / 'iv_sweep.csv'}  ({time.time()-t0:.0f}s)")
