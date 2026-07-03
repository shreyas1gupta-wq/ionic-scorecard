"""V2 ensemble backtest: sleeves S2/S3/S4 at 1 lot → correlations →
regime/risk-aware portfolio → report. Saves everything to results/.

Sleeve parameters are research priors (RESEARCH.md), NOT grid-optimised on
this data — that keeps this run honest; small per-sleeve WFO comes later.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest.engine_v2 import simulate_orders  # noqa: E402
from config import IS_FRACTION, PROCESSED_DIR, RESULTS_DIR, TOTAL_CAPITAL  # noqa: E402
from features.horizon import day_features  # noqa: E402
from portfolio.allocator import run_portfolio  # noqa: E402
from strategies.sleeves import (  # noqa: E402
    all_expiry_days, s2_range_premium, s3_zero_dte, s4_trend_rider,
)

t0 = time.time()
nifty = pd.read_parquet(PROCESSED_DIR / "nifty_1min.parquet")
vix = pd.read_parquet(PROCESSED_DIR / "vix_on_bars.parquet")["vix"]
filters = pd.read_parquet(PROCESSED_DIR / "filters.parquet")
days = pd.DatetimeIndex(pd.read_csv(PROCESSED_DIR / "trading_calendar.csv",
                                    parse_dates=["day"])["day"])

dayf = day_features(nifty, vix)
expiry_days = all_expiry_days(days)
print(f"setup {time.time() - t0:.0f}s; expiry days: {len(expiry_days)}")

orders = (s2_range_premium(nifty, dayf, filters, expiry_days)
          + s3_zero_dte(nifty, dayf, filters, expiry_days)
          + s4_trend_rider(nifty, dayf, filters))
print(f"orders: {pd.Series([o.sleeve for o in orders]).value_counts().to_dict()}")

tr = simulate_orders(nifty, vix, orders)
tr.to_parquet(RESULTS_DIR / "v2_sleeve_trades_1lot.parquet")
print(f"simulated {len(tr)} trades in {time.time() - t0:.0f}s total")

# ── per-sleeve diagnostics at 1 lot ──────────────────────────────────────
def sleeve_stats(t: pd.DataFrame) -> pd.Series:
    pnl = t["pnl_per_lot"] - t["fixed_cost"]
    wins = pnl > 0
    gl = -pnl[~wins].sum()
    return pd.Series({
        "trades": len(t), "win_rate": wins.mean(),
        "pf": pnl[wins].sum() / gl if gl > 0 else np.inf,
        "avg_pnl_lot": pnl.mean(), "tot_pnl_lot": pnl.sum(),
        "avg_hold_min": t["hold_min"].mean(),
        "sl_rate": (t["reason"] == "SL").mean(),
    })

stats = tr.groupby("sleeve").apply(sleeve_stats, include_groups=False)
print("\n--- sleeve stats (1 lot, after costs) ---")
print(stats.round(3).to_string())

# exit-reason mix per sleeve
print("\nexit reasons:")
print(tr.groupby(["sleeve", "reason"]).size().unstack(fill_value=0).to_string())

# ── daily streams + correlation ──────────────────────────────────────────
tr["day"] = tr["entry_dt"].dt.normalize()
dstream = (tr.assign(pnl=tr["pnl_per_lot"] - tr["fixed_cost"])
           .pivot_table(index="day", columns="sleeve", values="pnl", aggfunc="sum")
           .reindex(days).fillna(0.0))
corr = dstream.corr()
print("\n--- daily P&L correlation (1 lot) ---")
print(corr.round(2).to_string())

# ── portfolio ────────────────────────────────────────────────────────────
daily, scaled = run_portfolio(tr, days)
daily.to_csv(RESULTS_DIR / "v2_portfolio_daily.csv")
if len(scaled):
    scaled.to_parquet(RESULTS_DIR / "v2_scaled_trades.parquet")

def seg_report(d: pd.DataFrame, label: str) -> None:
    if not len(d):
        return
    base = d["Running_Capital"].iloc[0] - d["Daily_PnL"].iloc[0]
    ret = d["Daily_PnL"] / d["Running_Capital"].shift(1).fillna(base)
    yrs = len(d) / 252
    cagr = (d["Running_Capital"].iloc[-1] / base) ** (1 / yrs) - 1
    vol = ret.std(ddof=0) * np.sqrt(252)
    sharpe = (ret.mean() * 252 - 0.065) / vol if vol > 1e-12 else 0
    peak = d["Running_Capital"].cummax()
    mdd = ((peak - d["Running_Capital"]) / peak).max()
    print(f"{label}: CAGR {cagr:+.2%}  vol {vol:.2%}  Sharpe {sharpe:.2f}  "
          f"maxDD {mdd:.2%}  final Rs.{d['Running_Capital'].iloc[-1]:,.0f}")

print("\n--- portfolio (Rs.1Cr, vol-parity + Kelly cap + DD governor) ---")
n_is = int(len(days) * IS_FRACTION)
seg_report(daily, "FULL")
seg_report(daily.iloc[:n_is], "IS  ")
# rebase OOS segment
oos = daily.iloc[n_is:].copy()
seg_report(oos, "OOS ")
print(f"\nsaved -> {RESULTS_DIR}  ({time.time() - t0:.0f}s)")
