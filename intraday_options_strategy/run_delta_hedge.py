"""Delta-hedged 0DTE short straddle vs naked S3, at real m=0.80.
Does hedging the directional trend-day loss raise Sharpe / cut the tail?"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest.engine_v2 import (ExitPolicy, simulate_delta_hedged,  # noqa: E402
                                simulate_orders)
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
s3 = s3_zero_dte(nifty, dayf, filters, exp)


def report(tr, label):
    pnl = tr["pnl_per_lot"] - tr["fixed_cost"]
    dt = pnl.groupby(tr["entry_dt"].dt.normalize()).sum()
    cal = days[(days >= dt.index.min()) & (days <= dt.index.max())]
    dc = dt.reindex(cal).fillna(0.0)
    w = pnl > 0; gl = -pnl[~w].sum()
    sh = dc.mean() / dc.std(ddof=0) * np.sqrt(252)
    dco = dc[dc.index >= oos]; sho = dco.mean() / dco.std(ddof=0) * np.sqrt(252)
    dci = dc[dc.index < oos]; shi = dci.mean() / dci.std(ddof=0) * np.sqrt(252)
    peak = dc.cumsum().cummax(); ddmax = (peak - dc.cumsum()).max()
    print(f"{label:16} WR={w.mean():.2f} PF={pnl[w].sum()/gl if gl>0 else 9:.2f} "
          f"avg/lot={pnl.mean():6.0f} worst={pnl.min():7.0f} "
          f"Sh={sh:.2f} IS={shi:.2f} OOS={sho:.2f} maxDD/lot={ddmax:,.0f}")


naked = [replace(o, exit=ExitPolicy(sl=0.25, pt=None, hard_exit="14:30")) for o in s3]
report(simulate_orders(nifty, vix, naked, iv_mult=M, slippage_pct=SLIP), "S3 naked")
for band in [0.10, 0.15, 0.25]:
    tr = simulate_delta_hedged(nifty, vix, s3, iv_mult=M, slippage_pct=SLIP, hedge_band=band)
    report(tr, f"S3 hedged b={band}")
    print(f"   mean rebalances/day={tr['n_rebalance'].mean():.1f}, "
          f"hedge contributes avg {tr['hedge_pnl_lot'].mean():.0f}/lot")
