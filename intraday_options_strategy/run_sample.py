"""Phase 3 validation: run the engine end-to-end on 2023 and inspect output.

Not a performance claim — default (unoptimised) parameters; the point is
correctness: plumbing, costs, sizing, exits, and eyeballing sample trades.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest.costs import round_trip_example  # noqa: E402
from backtest.engine import EngineConfig, run_backtest  # noqa: E402
from config import PROCESSED_DIR, RESULTS_DIR, StrategyParams  # noqa: E402
from features.regime_filter import build_filters  # noqa: E402
from features.signals import signal_events  # noqa: E402

START, END = "2023-01-01", "2023-12-31"

nifty = pd.read_parquet(PROCESSED_DIR / "nifty_1min.parquet").loc[START:END]
vix = pd.read_parquet(PROCESSED_DIR / "vix_1min.parquet").loc[START:END]

t0 = time.time()
filt = build_filters(nifty, vix)
ev = signal_events(nifty, filt, StrategyParams())
vix_on_bars = vix["vix"].reindex(nifty.index).ffill()
tr, daily = run_backtest(nifty, vix_on_bars, ev, EngineConfig(StrategyParams()))
elapsed = time.time() - t0

print(round_trip_example(150.0, 1))
print(f"\nengine: {len(ev)} events -> {len(tr)} trades in {elapsed:.1f}s")
print(f"days traded: {(daily['Daily_Trades'] > 0).sum()}/{len(daily)}  "
      f"trades/day (traded days): {tr.groupby(tr['entry_dt'].dt.normalize()).size().mean():.1f}")
wins = (tr["net_pnl"] > 0).sum()
print(f"win rate: {wins / len(tr):.1%}   net P&L: Rs.{tr['net_pnl'].sum():,.0f}   "
      f"gross: Rs.{tr['gross_pnl'].sum():,.0f}")
print(f"avg win: {tr.loc[tr.net_pnl > 0, 'net_pnl'].mean():,.0f}  "
      f"avg loss: {tr.loc[tr.net_pnl <= 0, 'net_pnl'].mean():,.0f}  "
      f"avg hold: {tr['hold_min'].mean():.0f} min")
print(f"exit reasons: {tr['reason'].value_counts().to_dict()}")
print(f"by signal: {tr.groupby('signal')['net_pnl'].agg(['count', 'sum']).to_string()}")
print(f"lots: min {tr['lots'].min()} max {tr['lots'].max()} mean {tr['lots'].mean():.1f}")
print(f"final capital: Rs.{daily['Running_Capital'].iloc[-1]:,.0f}")

print("\n--- 8 sample trades ---")
cols = ["entry_dt", "signal", "option", "strike", "spot_entry", "entry_fill",
        "exit_fill", "lots", "reason", "hold_min", "net_pnl", "delta"]
sample = pd.concat([tr.head(3), tr.sample(3, random_state=42), tr.tail(2)])
print(sample[cols].to_string(index=False))

RESULTS_DIR.mkdir(exist_ok=True)
tr.to_parquet(RESULTS_DIR / "sample2023_trades.parquet")
daily.to_csv(RESULTS_DIR / "sample2023_daily.csv")
print(f"\nsaved -> {RESULTS_DIR}")
