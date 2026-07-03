"""Compare the short-vol family at REAL m=0.80 + realistic costs, and test the
uncorrelated ENSEMBLE (short-vol + trend-day convexity hedge).

Sleeves:
  S3    naked 0DTE short straddle (baseline)
  S5_IF 0DTE iron fly (defined-risk short vol)
  S6_IC 0DTE iron condor (wider, higher WR)
  S4    trend-day long rider (long convexity — pays when short-vol bleeds)
Reports per-sleeve stats + the daily P&L correlation + a simple equal-risk
combo (S5_IF + S4) Sharpe/DD to show diversification.
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest.engine_v2 import (ExitPolicy, simulate_multileg,  # noqa: E402
                                simulate_orders)
from config import PROCESSED_DIR, RESULTS_DIR  # noqa: E402
from features.horizon import day_features  # noqa: E402
from strategies.sleeves import (all_expiry_days, s3_zero_dte,  # noqa: E402
                                s4_trend_rider, s5_iron_fly_0dte,
                                s6_iron_condor_0dte)

M_REAL, SLIP = 0.80, 0.02
nifty = pd.read_parquet(PROCESSED_DIR / "nifty_1min.parquet")
vix = pd.read_parquet(PROCESSED_DIR / "vix_on_bars.parquet")["vix"]
filters = pd.read_parquet(PROCESSED_DIR / "filters.parquet")
days = pd.DatetimeIndex(pd.read_csv(PROCESSED_DIR / "trading_calendar.csv",
                                    parse_dates=["day"])["day"])
oos = days[int(len(days) * 0.70)]
dayf = day_features(nifty, vix)
exp = all_expiry_days(days)


def daily(tr):
    pnl = tr["pnl_per_lot"] - tr["fixed_cost"]
    return pnl.groupby(tr["entry_dt"].dt.normalize()).sum()


def stats(tr, label):
    if not len(tr):
        print(f"{label}: no trades"); return None
    pnl = tr["pnl_per_lot"] - tr["fixed_cost"]
    dt = daily(tr)
    cal = days[(days >= dt.index.min()) & (days <= dt.index.max())]
    dc = dt.reindex(cal).fillna(0.0)
    wins = pnl > 0
    gl = -pnl[~wins].sum()
    sh = dc.mean() / dc.std(ddof=0) * np.sqrt(252) if dc.std(ddof=0) > 0 else 0
    dco = dc[dc.index >= oos]
    sho = dco.mean() / dco.std(ddof=0) * np.sqrt(252) if dco.std(ddof=0) > 0 else 0
    print(f"{label:8} n={len(tr):4} WR={wins.mean():.2f} PF={pnl[wins].sum()/gl if gl>0 else 9:.2f} "
          f"avg/lot={pnl.mean():6.0f} worst={pnl.min():7.0f} ShFund={sh:.2f} OOS={sho:.2f}")
    return dt


print(f"=== short-vol family @ real m={M_REAL}, slip={SLIP:.0%}, gap-through stops ===")
res = {}
s3 = [replace(o, exit=ExitPolicy(sl=0.25, pt=None, hard_exit="14:30"))
      for o in s3_zero_dte(nifty, dayf, filters, exp)]
res["S3"] = stats(simulate_orders(nifty, vix, s3, iv_mult=M_REAL, slippage_pct=SLIP), "S3 naked")
res["S5_IF"] = stats(simulate_multileg(nifty, vix, s5_iron_fly_0dte(nifty, dayf, filters, exp),
                     iv_mult=M_REAL, slippage_pct=SLIP), "S5 ironfly")
res["S6_IC"] = stats(simulate_multileg(nifty, vix, s6_iron_condor_0dte(nifty, dayf, filters, exp),
                     iv_mult=M_REAL, slippage_pct=SLIP), "S6 condor")
res["S4"] = stats(simulate_orders(nifty, vix, s4_trend_rider(nifty, dayf, filters),
                  iv_mult=M_REAL, slippage_pct=SLIP), "S4 trend")

# correlation of daily P&L (1-lot)
streams = pd.DataFrame({k: v for k, v in res.items() if v is not None}).reindex(days).fillna(0.0)
print("\ndaily P&L correlation (1-lot):")
print(streams.corr().round(2).to_string())

# equal-risk combo: scale each sleeve to ~equal daily-vol, sum
def combo(names):
    sub = streams[names].copy()
    w = {n: (1.0 / sub[n][sub[n] != 0].std()) if sub[n].std() > 0 else 0 for n in names}
    port = sum(sub[n] * w[n] for n in names)
    sh = port.mean() / port.std(ddof=0) * np.sqrt(252)
    po = port[port.index >= oos]
    sho = po.mean() / po.std(ddof=0) * np.sqrt(252)
    peak = port.cumsum().cummax(); dd = (peak - port.cumsum()).max()
    print(f"  combo {names}: ShFund={sh:.2f} OOS={sho:.2f} (vol-normalised units)")

print("\nuncorrelated ensemble (vol-parity):")
combo(["S5_IF", "S4"])
combo(["S5_IF", "S6_IC", "S4"])
combo(["S3", "S4"])
print(f"\n(real m={M_REAL} from Angel live calibration; slip {SLIP:.0%}; gap-through stops)")
