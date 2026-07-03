"""Re-run the 0DTE short straddle (S3) at the REAL live-calibrated IV
multiplier (m~0.78-0.81 measured at 09:20 from Angel option candles), to get
the HONEST Sharpe now that the optimistic extrapolated m=0.96 is replaced.
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest.engine_v2 import ExitPolicy, simulate_orders  # noqa: E402
from config import PROCESSED_DIR, RESULTS_DIR  # noqa: E402
from features.horizon import day_features  # noqa: E402
from strategies.sleeves import all_expiry_days, s3_zero_dte  # noqa: E402

nifty = pd.read_parquet(PROCESSED_DIR / "nifty_1min.parquet")
vix = pd.read_parquet(PROCESSED_DIR / "vix_on_bars.parquet")["vix"]
filters = pd.read_parquet(PROCESSED_DIR / "filters.parquet")
days = pd.DatetimeIndex(pd.read_csv(PROCESSED_DIR / "trading_calendar.csv",
                                    parse_dates=["day"])["day"])
oos_start = days[int(len(days) * 0.70)]
dayf = day_features(nifty, vix)
expiry_days = all_expiry_days(days)
s3 = s3_zero_dte(nifty, dayf, filters, expiry_days)


def perf(tr, mask=None):
    if mask is not None:
        tr = tr[mask(tr)]
    if len(tr) < 20:
        return {}
    pnl = tr["pnl_per_lot"] - tr["fixed_cost"]
    td = tr["entry_dt"].dt.normalize()
    dt = pnl.groupby(td).sum()
    cal = days[(days >= td.min()) & (days <= td.max())]
    dc = dt.reindex(cal).fillna(0.0)
    wins = pnl > 0
    gl = -pnl[~wins].sum()
    return {"wr": round(float(wins.mean()), 3),
            "pf": round(float(pnl[wins].sum() / gl), 2) if gl > 0 else np.inf,
            "avg": round(float(pnl.mean())), "worst": round(float(pnl.min())),
            "sh_fund": round(float(dc.mean() / dc.std(ddof=0) * np.sqrt(252)), 2)}


print("S3 0DTE short straddle at REAL calibrated m (constant per run):")
print(f"{'m':>5} {'sl':>5} {'slip':>5} | {'WR':>5} {'PF':>5} {'avg/lot':>8} "
      f"{'worst':>8} {'ShFund':>7} {'IS':>6} {'OOS':>6}")
for m in [0.75, 0.80, 0.85, 0.90]:
    for sl in [0.25, 0.40]:
        for slip in [0.01, 0.02]:
            orders = [replace(o, exit=ExitPolicy(sl=sl, pt=None, hard_exit="14:30")) for o in s3]
            tr = simulate_orders(nifty, vix, orders, iv_mult=m,
                                 slippage_pct=slip, stop_slip_mult=3.0)
            tr["day"] = tr["entry_dt"].dt.normalize()
            f = perf(tr)
            i = perf(tr, lambda t: t["day"] < oos_start)
            o = perf(tr, lambda t: t["day"] >= oos_start)
            print(f"{m:>5.2f} {sl:>5.2f} {slip:>5.1%} | {f.get('wr'):>5} {f.get('pf'):>5} "
                  f"{f.get('avg'):>8} {f.get('worst'):>8} {f.get('sh_fund'):>7} "
                  f"{i.get('sh_fund'):>6} {o.get('sh_fund'):>6}")
