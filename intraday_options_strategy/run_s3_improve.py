"""Principled improvements to S3 (no curve-fit): does a tighter GAP gate
(skip gappy = trend-prone mornings) and an EARLIER exit (less time in market =
less tail) robustly raise Sharpe / cut the worst day? Judged IS vs OOS — adopt
only if OOS improves WITHOUT IS/OOS divergence."""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest.engine_v2 import ExitPolicy, simulate_orders  # noqa: E402
from config import PROCESSED_DIR  # noqa: E402
from features.horizon import day_features  # noqa: E402
from strategies.sleeves import all_expiry_days, s3_zero_dte  # noqa: E402

M, SLIP = 0.80, 0.02
nifty = pd.read_parquet(PROCESSED_DIR / "nifty_1min.parquet")
vix = pd.read_parquet(PROCESSED_DIR / "vix_on_bars.parquet")["vix"]
filters = pd.read_parquet(PROCESSED_DIR / "filters.parquet")
days = pd.DatetimeIndex(pd.read_csv(PROCESSED_DIR / "trading_calendar.csv",
                                    parse_dates=["day"])["day"])
oos = days[int(len(days) * 0.70)]
dayf = day_features(nifty, vix)
exp = all_expiry_days(days)
gap_abs = dayf["gap_pct"].abs()

base = s3_zero_dte(nifty, dayf, filters, exp)


def sh(dc):
    return dc.mean() / dc.std(ddof=0) * np.sqrt(252) if dc.std(ddof=0) > 0 else 0


print(f"S3 improvements @ m={M}, slip={SLIP:.0%}:")
print(f"{'gapmax':>7} {'exit':>6} {'n':>4} {'WR':>5} {'avg':>6} {'worst':>7} "
      f"{'ShFull':>7} {'ShIS':>6} {'ShOOS':>6}")
for gap_max in [0.004, 0.003, 0.002]:
    for exit_t in ["14:30", "14:00", "13:00"]:
        orders = [replace(o, exit=ExitPolicy(sl=0.25, pt=None, hard_exit=exit_t))
                  for o in base
                  if gap_abs.get(o.signal_dt.normalize(), 1.0) <= gap_max]
        tr = simulate_orders(nifty, vix, orders, iv_mult=M, slippage_pct=SLIP)
        if not len(tr):
            continue
        pnl = tr["pnl_per_lot"] - tr["fixed_cost"]
        dt = pnl.groupby(tr["entry_dt"].dt.normalize()).sum()
        cal = days[(days >= dt.index.min()) & (days <= dt.index.max())]
        dc = dt.reindex(cal).fillna(0.0)
        print(f"{gap_max:>7.3f} {exit_t:>6} {len(tr):>4} {(pnl>0).mean():>5.2f} "
              f"{pnl.mean():>6.0f} {pnl.min():>7.0f} {sh(dc):>7.2f} "
              f"{sh(dc[dc.index<oos]):>6.2f} {sh(dc[dc.index>=oos]):>6.2f}")
