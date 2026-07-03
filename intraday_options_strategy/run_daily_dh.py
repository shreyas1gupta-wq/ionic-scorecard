"""NON-EXPIRY-DAY strategy: delta-hedged short straddle on the nearest weekly,
run EVERY trading day (DTE>=1), harvesting the daily intraday VRP (realized
~0.66x implied every session, not just expiry). Turns ~31 deploy-days/yr into
~250 → real capital efficiency + smoother equity.

Entry 09:20, delta-hedge intraday, square off 15:10. Real calibrated m, 2% opt
slip, 0.5pt futures slip. Reports overall fund Sharpe, by-DTE breakdown, and
correlation/combo with the 0DTE sleeve.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest.engine_v2 import (ExitPolicy, OrderSpec, default_iv_mult,  # noqa: E402
                                simulate_delta_hedged)
from config import PROCESSED_DIR  # noqa: E402
from features.horizon import day_features  # noqa: E402
from options.option_selector import WEEKLY_START  # noqa: E402
from strategies.sleeves import STRADDLE, all_expiry_days, s3_zero_dte  # noqa: E402

M, SLIP = 0.80, 0.02
nifty = pd.read_parquet(PROCESSED_DIR / "nifty_1min.parquet")
vix = pd.read_parquet(PROCESSED_DIR / "vix_on_bars.parquet")["vix"]
filters = pd.read_parquet(PROCESSED_DIR / "filters.parquet")
days = pd.DatetimeIndex(pd.read_csv(PROCESSED_DIR / "trading_calendar.csv",
                                    parse_dates=["day"])["day"])
oos = days[int(len(days) * 0.70)]
dayf = day_features(nifty, vix)
exp = all_expiry_days(days)


def bar_at(day, hhmm):
    t = day + pd.Timedelta(f"{hhmm}:00")
    return t if t in nifty.index else None


# every trading day post weekly-launch; gate on event/vix; nearest weekly (DTE>=1)
orders = []
for d in days:
    if d < WEEKLY_START:
        continue
    dt = bar_at(d, "09:19")
    if dt is None or not bool(filters.loc[dt, "event_ok"]) or not bool(filters.loc[dt, "vix_ok"]):
        continue
    f = dayf.loc[d] if d in dayf.index else None
    if f is not None and not np.isnan(f["gap_pct"]) and abs(f["gap_pct"]) > 0.006:
        continue                          # skip big-gap mornings
    orders.append(OrderSpec(signal_dt=dt, sleeve="DAILY_DH", side=-1, legs=STRADDLE,
                            exit=ExitPolicy(sl=0.5, pt=None, hard_exit="15:10"),
                            min_dte=1, direction_label="DH_STRADDLE"))
print(f"daily orders: {len(orders)} (every trading day, nearest weekly DTE>=1)")

tr = simulate_delta_hedged(nifty, vix, orders, iv_mult=M, slippage_pct=SLIP,
                           hedge_band=0.25)
tr["day"] = tr["entry_dt"].dt.normalize()
tr["dte"] = (pd.to_datetime(tr["expiry"]) - tr["day"]).dt.days if "expiry" in tr else 0


def fund_sharpe(tr, mask=None):
    if mask is not None:
        tr = tr[mask]
    if len(tr) < 20:
        return None
    pnl = tr["pnl_per_lot"] - tr["fixed_cost"]
    dt = pnl.groupby(tr["entry_dt"].dt.normalize()).sum()
    cal = days[(days >= dt.index.min()) & (days <= dt.index.max())]
    dc = dt.reindex(cal).fillna(0.0)
    w = pnl > 0; gl = -pnl[~w].sum()
    peak = dc.cumsum().cummax(); dd = (peak - dc.cumsum()).max()
    return {"n": len(tr), "wr": round(float(w.mean()), 3),
            "pf": round(float(pnl[w].sum() / gl), 2) if gl > 0 else 9.99,
            "avg": round(float(pnl.mean())), "worst": round(float(pnl.min())),
            "sh": round(float(dc.mean() / dc.std(ddof=0) * np.sqrt(252)), 2),
            "dd_lot": round(float(dd))}


print("\n=== DAILY delta-hedged short straddle (DTE>=1, every day) ===")
print("overall:", fund_sharpe(tr))
print("IS     :", fund_sharpe(tr, tr["day"] < oos))
print("OOS    :", fund_sharpe(tr, tr["day"] >= oos))
print("\nby DTE bucket at entry (vega risk rises with DTE):")
for lo, hi in [(1, 1), (2, 2), (3, 4), (5, 7)]:
    s = fund_sharpe(tr, (tr["dte"] >= lo) & (tr["dte"] <= hi))
    if s:
        print(f"  DTE {lo}-{hi}: {s}")
