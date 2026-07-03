"""AUDIT #5 — delta-hedge drift-dependence & execution-realism stress.

(1) MIRROR-PATH test: reflect each day's intraday path around its open
    (S'=open^2/S), flipping the drift sign while preserving volatility. If the
    delta-hedge Sharpe survives, the edge is NOT a Nifty up-drift artifact.
(2) UP vs DOWN regime split (by each day's net return).
(3) Futures-slippage x rebalance-band Sharpe envelope (report worst case).
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest.engine_v2 as eng  # noqa: E402
from backtest.engine_v2 import ExitPolicy, simulate_delta_hedged  # noqa: E402
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


def mirror_path(df: pd.DataFrame) -> pd.DataFrame:
    """Reflect each day's intraday OHLC around that day's OPEN → flips drift,
    preserves intraday vol magnitude. open[day] is the first bar's open."""
    out = df.copy()
    day = df.index.normalize()
    op = df.groupby(day)["open"].transform("first")
    out["open"] = op * op / df["open"]
    out["close"] = op * op / df["close"]
    hi = op * op / df["low"]            # reflection swaps high/low
    lo = op * op / df["high"]
    out["high"], out["low"] = hi, lo
    return out


def fund_sharpe(tr, mask=None):
    if mask is not None:
        tr = tr[mask]
    if len(tr) < 15:
        return float("nan")
    pnl = tr["pnl_per_lot"] - tr["fixed_cost"]
    d = pnl.groupby(tr["entry_dt"].dt.normalize()).sum()
    cal = days[(days >= d.index.min()) & (days <= d.index.max())]
    dc = d.reindex(cal).fillna(0.0)
    return float(dc.mean() / dc.std(ddof=0) * np.sqrt(252)) if dc.std(ddof=0) > 0 else 0.0


base = simulate_delta_hedged(nifty, vix, s3, iv_mult=M, slippage_pct=SLIP, hedge_band=0.25)
base["day"] = base["entry_dt"].dt.normalize()
print("=== (1) MIRROR-PATH drift test (flip drift, keep vol) ===")
print(f"actual path : full {fund_sharpe(base):.2f}  OOS {fund_sharpe(base, base.day>=oos):.2f}  "
      f"hedgePnL/lot {base['hedge_pnl_lot'].mean():.0f}")
mir = simulate_delta_hedged(mirror_path(nifty), vix, s3, iv_mult=M, slippage_pct=SLIP, hedge_band=0.25)
mir["day"] = mir["entry_dt"].dt.normalize()
print(f"mirrored    : full {fund_sharpe(mir):.2f}  OOS {fund_sharpe(mir, mir.day>=oos):.2f}  "
      f"hedgePnL/lot {mir['hedge_pnl_lot'].mean():.0f}")
print("  → if both similar, edge is NOT drift-dependent (theta/gamma, not direction)")

print("\n=== (2) UP vs DOWN day regime (actual path, OOS) ===")
day_ret = nifty.groupby(nifty.index.normalize())["close"].last().pct_change()
up_days = set(day_ret[day_ret > 0].index)
o = base[base.day >= oos]
print(f"up-days  : Sharpe {fund_sharpe(o, o.day.isin(up_days)):.2f}  n={o.day.isin(up_days).sum()}")
print(f"down-days: Sharpe {fund_sharpe(o, ~o.day.isin(up_days)):.2f}  n={(~o.day.isin(up_days)).sum()}")

print("\n=== (3) futures-slippage x band envelope (OOS Sharpe) ===")
orig = eng.FUT_SLIP_PTS
print(f"{'band\\slipPt':>12}" + "".join(f"{s:>8}" for s in [0.5, 1.0, 1.5, 2.0]))
for band in [0.10, 0.15, 0.25]:
    row = f"{band:>12.2f}"
    for sp in [0.5, 1.0, 1.5, 2.0]:
        eng.FUT_SLIP_PTS = sp
        tr = simulate_delta_hedged(nifty, vix, s3, iv_mult=M, slippage_pct=SLIP, hedge_band=band)
        tr["day"] = tr["entry_dt"].dt.normalize()
        row += f"{fund_sharpe(tr, tr.day>=oos):>8.2f}"
    print(row)
eng.FUT_SLIP_PTS = orig
