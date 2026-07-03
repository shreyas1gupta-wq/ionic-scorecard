"""How high can CAGR go on the validated delta-hedged 0DTE+DTE1 book — and what
leverage would '1000% CAGR' actually require? Kelly analysis on the REAL daily
return series. Shows the realistic high-CAGR ceiling and the ruin cliff.

daily return at leverage L = L * (pnl_per_lot / margin_per_lot). Compound over
OOS; ruin if equity <= 0. Reports CAGR / MaxDD / ruin% (bootstrap) per L, plus
Kelly-optimal L and the L needed to 'target' 1000%.
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest.engine_v2 import ExitPolicy, simulate_delta_hedged  # noqa: E402
from config import PROCESSED_DIR  # noqa: E402
from features.horizon import day_features  # noqa: E402
from options.option_selector import ExpiryCalendar, WEEKLY_START  # noqa: E402
from strategies.sleeves import STRADDLE, all_expiry_days, s3_zero_dte  # noqa: E402
from backtest.engine_v2 import OrderSpec  # noqa: E402

M, SLIP = 0.80, 0.02
FUT_MARGIN_FACTOR = 1.6        # straddle margin + futures hedge margin (~0.6x more)
nifty = pd.read_parquet(PROCESSED_DIR / "nifty_1min.parquet")
vix = pd.read_parquet(PROCESSED_DIR / "vix_on_bars.parquet")["vix"]
filters = pd.read_parquet(PROCESSED_DIR / "filters.parquet")
days = pd.DatetimeIndex(pd.read_csv(PROCESSED_DIR / "trading_calendar.csv",
                                    parse_dates=["day"])["day"])
oos = days[int(len(days) * 0.70)]
dayf = day_features(nifty, vix)
exp = all_expiry_days(days)
cal = ExpiryCalendar(days)


def bar_at(d, hhmm):
    t = d + pd.Timedelta(f"{hhmm}:00")
    return t if t in nifty.index else None


def dte_orders(target):
    out = []
    hard = "14:30" if target == 0 else "15:00"
    sl = 0.25 if target == 0 else 0.40
    for d in days:
        if d < WEEKLY_START:
            continue
        if (cal.next_expiry(d, min_dte=0).normalize() - d).days != target:
            continue
        dt = bar_at(d, "09:19")
        if dt is None or not bool(filters.loc[dt, "event_ok"]) or not bool(filters.loc[dt, "vix_ok"]):
            continue
        f = dayf.loc[d] if d in dayf.index else None
        if f is not None and not np.isnan(f["gap_pct"]) and abs(f["gap_pct"]) > 0.005:
            continue
        out.append(OrderSpec(signal_dt=dt, sleeve=f"D{target}", side=-1, legs=STRADDLE,
                   exit=ExitPolicy(sl=sl, pt=None, hard_exit=hard), min_dte=target))
    return out


tr0 = simulate_delta_hedged(nifty, vix, dte_orders(0), iv_mult=M, slippage_pct=SLIP, hedge_band=0.25)
tr1 = simulate_delta_hedged(nifty, vix, dte_orders(1), iv_mult=M, slippage_pct=SLIP, hedge_band=0.25)
both = pd.concat([tr0, tr1], ignore_index=True)
both["day"] = both["entry_dt"].dt.normalize()
# per-active-day return on the margin posted that day (1 lot)
both["margin"] = both["margin_per_lot"] * FUT_MARGIN_FACTOR
both["ret_on_margin"] = (both["pnl_per_lot"] - both["fixed_cost"]) / both["margin"]
# OOS daily return series (sum if both sleeves same day — rare, diff weekdays)
r = both[both["day"] >= oos].groupby("day")["ret_on_margin"].sum().sort_index()
mu, sd = r.mean(), r.std(ddof=0)
n_per_yr = len(r) / ((r.index[-1] - r.index[0]).days / 365.25)
kelly = mu / (sd ** 2)        # optimal leverage (fraction of capital per unit-margin bet)
print(f"book: {len(r)} OOS trade-days (~{n_per_yr:.0f}/yr); per-trade ret-on-margin "
      f"mu={mu:.3%} sd={sd:.2%}; daily Sharpe-ann={mu/sd*np.sqrt(n_per_yr):.2f}")
print(f"Kelly-optimal leverage L*={kelly:.2f} (deploy {kelly:.1f}x capital as margin/day)\n")

rng = np.random.default_rng(42)
arr = r.values


def sim(L, boot=False):
    seq = rng.choice(arr, size=len(arr), replace=True) if boot else arr
    eq = 1.0; peak = 1.0; mdd = 0.0; ruined = False
    for x in seq:
        eq *= (1 + L * x)
        if eq <= 0:
            ruined = True; eq = 1e-9; break
        peak = max(peak, eq); mdd = max(mdd, 1 - eq / peak)
    yrs = len(arr) / n_per_yr
    cagr = eq ** (1 / yrs) - 1 if eq > 0 and not ruined else -1.0
    return cagr, mdd, ruined


print(f"{'leverage L':>10} {'CAGR':>10} {'MaxDD':>8} {'ruin%(boot)':>12}  note")
for L in [0.25, 0.5, 1.0, 2.0, kelly, 3.0, 5.0, 8.0]:
    cagr, mdd, _ = sim(L)
    ruin = np.mean([sim(L, boot=True)[2] for _ in range(300)])
    tag = "<- Kelly (max growth)" if abs(L - kelly) < 1e-6 else (
        "realistic max (~full capital)" if abs(L - 1.0) < 1e-6 else (
        "RUIN territory" if ruin > 0.05 else ""))
    print(f"{L:>10.2f} {cagr:>+9.0%} {mdd:>8.1%} {ruin:>11.0%}  {tag}")

# leverage needed to 'target' 1000% CAGR
target = (1 + 10.0) ** (1 / (len(arr) / n_per_yr))  # daily growth for 1000%/yr
# solve L: median daily (1+L*x) growth ~ target — approx via mean log
from scipy.optimize import brentq
def gap(L):
    g = np.mean(np.log(np.clip(1 + L * arr, 1e-9, None)))
    return g - np.log(1 + 10.0) / (len(arr) / n_per_yr)
try:
    L1000 = brentq(gap, 0.01, 50)
    c, m, _ = sim(L1000)
    ruin = np.mean([sim(L1000, boot=True)[2] for _ in range(300)])
    print(f"\nTo TARGET 1000% CAGR you'd need L~{L1000:.1f} ({L1000:.0f}x capital as margin):"
          f" MaxDD {m:.0%}, ruin prob {ruin:.0%} — i.e. {'WIPEOUT' if ruin>0.3 else 'extreme risk'}.")
except Exception as e:
    print(f"\n1000% CAGR not reachable at any finite leverage without ruin ({e}).")
print(f"\nHONEST: Kelly says max-growth CAGR ~{sim(kelly)[0]:+.0%} (MaxDD {sim(kelly)[1]:.0%}); "
      f"sane (quarter-Kelly) ~{sim(kelly*0.25)[0]:+.0%} (MaxDD {sim(kelly*0.25)[1]:.0%}). "
      f"1000% = betting far past Kelly = ruin.")
