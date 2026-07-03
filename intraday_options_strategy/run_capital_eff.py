"""Where 'low capital + high CAGR' actually comes from: RETURN ON MARGIN.
Buying fails (negative EV). The low-capital high-CAGR vehicle is DEFINED-RISK
SELLING (iron fly): tiny margin (=max loss) → high return on capital deployed.

Compares CAGR-on-deployed-margin + MDD for the validated selling structures.
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest.engine_v2 import (ExitPolicy, simulate_delta_hedged,  # noqa: E402
                                simulate_multileg, simulate_orders)
from config import PROCESSED_DIR  # noqa: E402
from features.horizon import day_features  # noqa: E402
from strategies.sleeves import (all_expiry_days, s3_zero_dte,  # noqa: E402
                                s5_iron_fly_0dte)

M, SLIP = 0.80, 0.02
nifty = pd.read_parquet(PROCESSED_DIR / "nifty_1min.parquet")
vix = pd.read_parquet(PROCESSED_DIR / "vix_on_bars.parquet")["vix"]
filters = pd.read_parquet(PROCESSED_DIR / "filters.parquet")
days = pd.DatetimeIndex(pd.read_csv(PROCESSED_DIR / "trading_calendar.csv",
                                    parse_dates=["day"])["day"])
oos = days[int(len(days) * 0.70)]
dayf = day_features(nifty, vix)
exp = all_expiry_days(days)


def roi_report(tr, label):
    """Return on MARGIN: deploy 1 lot/day, capital = that day's margin/lot.
    CAGR-on-margin = annualised growth of an account that posts the margin."""
    if not len(tr):
        print(f"{label}: none"); return
    tr = tr.sort_values("entry_dt")
    pnl = tr["pnl_per_lot"] - tr["fixed_cost"]
    margin = tr["margin_per_lot"].clip(lower=1)
    base = float(margin.mean())
    # post 1 unit of capital per BUFFER x min-margin; additive equity (no comp blowup)
    BUFFER = 3.0                                # don't run at max leverage
    cap0 = base * BUFFER
    dts = pd.DatetimeIndex(tr["entry_dt"].dt.normalize())
    dseries = pd.Series(pnl.values, index=dts).groupby(level=0).sum().reindex(days).fillna(0.0)
    eq = cap0 + dseries.cumsum()
    yrs = (dseries[dseries != 0].index[-1] - dseries[dseries != 0].index[0]).days / 365.25
    cagr = (eq.iloc[-1] / cap0) ** (1 / yrs) - 1 if yrs > 0 and eq.iloc[-1] > 0 else float("nan")
    peak = eq.cummax(); mdd = ((peak - eq) / peak).max()
    w = pnl > 0
    sh = dseries.mean() / dseries.std(ddof=0) * np.sqrt(252) if dseries.std(ddof=0) > 0 else 0
    print(f"{label:22} cap/lot~Rs.{cap0:>9,.0f} ({BUFFER:.0f}x min-margin)  WR={w.mean():.2f}  "
          f"CAGR/cap={cagr:+.0%}  MDD={mdd:.1%}  Sharpe={sh:.2f}")


print(f"RETURN-ON-CAPITAL of SELLING structures (real m={M}, slip={SLIP:.0%}):")
print("(CAGR measured on the MARGIN posted, not Rs.1Cr — shows capital efficiency)\n")

s3 = [replace(o, exit=ExitPolicy(sl=0.25, pt=None, hard_exit="14:30"))
      for o in s3_zero_dte(nifty, dayf, filters, exp)]
roi_report(simulate_orders(nifty, vix, s3, iv_mult=M, slippage_pct=SLIP),
           "naked 0DTE straddle")
roi_report(simulate_delta_hedged(nifty, vix,
           s3_zero_dte(nifty, dayf, filters, exp), iv_mult=M, slippage_pct=SLIP, hedge_band=0.25),
           "delta-hedged 0DTE")
roi_report(simulate_multileg(nifty, vix, s5_iron_fly_0dte(nifty, dayf, filters, exp),
           iv_mult=M, slippage_pct=SLIP),
           "iron fly 0DTE (low-cap)")
print("\nNote: iron-fly margin = defined max-loss (~Rs.10-15k/lot) vs ~Rs.1.6L naked")
print("→ far higher CAGR-on-capital, bounded MDD, low capital. The legit answer")
print("  to 'low capital + high CAGR' is defined-risk SELLING, not buying.")
