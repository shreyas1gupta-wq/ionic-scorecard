"""Phase 2 smoke tests: BS pricing, expiry calendar, signals, no-lookahead.

Run:  python tests_smoke.py   (from project root)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (  # noqa: E402
    DIVIDEND_YIELD, PROCESSED_DIR, RISK_FREE_RATE, StrategyParams,
)
from features.indicators import adx_5min_on_1min, ema, rsi, session_twap  # noqa: E402
from features.regime_filter import build_filters  # noqa: E402
from features.signals import signal_events  # noqa: E402
from options.bs_pricing import bs_greeks, bs_price  # noqa: E402
from options.option_selector import ExpiryCalendar, nearest_strike, years_to_expiry  # noqa: E402

PASS, FAIL = "PASS", "FAIL"
failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{PASS if cond else FAIL}] {name} {detail}")
    if not cond:
        failures.append(name)


# ── 1. Black-Scholes sanity ──────────────────────────────────────────────
r, q = RISK_FREE_RATE, DIVIDEND_YIELD
S, K, T, sig = 24000.0, 24000.0, 3 / 365, 0.14
c = float(bs_price(S, K, T, sig, r, q, True))
p = float(bs_price(S, K, T, sig, r, q, False))
parity = c - p - (S * np.exp(-q * T) - K * np.exp(-r * T))
check("BS put-call parity", abs(parity) < 1e-6, f"(resid={parity:.2e})")
check("BS ATM 3d premium plausible", 80 < c < 220, f"(CE={c:.1f}, PE={p:.1f})")

g_c = bs_greeks(S, K, T, sig, r, q, True)
g_p = bs_greeks(S, K, T, sig, r, q, False)
check("delta signs/magnitude",
      0.4 < g_c["delta"] < 0.6 and -0.6 < g_p["delta"] < -0.4,
      f"(dC={float(g_c['delta']):.3f}, dP={float(g_p['delta']):.3f})")
check("gamma>0, vega>0, theta<0",
      g_c["gamma"] > 0 and g_c["vega"] > 0 and g_c["theta"] < 0,
      f"(theta/day={float(g_c['theta']):.2f})")

deep_itm = float(bs_price(S, 20000.0, T, sig, r, q, True))
check("deep ITM ~ discounted intrinsic", abs(deep_itm - (S * np.exp(-q * T) - 20000 * np.exp(-r * T))) < 1.0,
      f"(px={deep_itm:.1f})")

# ── 2. Expiry calendar ───────────────────────────────────────────────────
days = pd.read_csv(PROCESSED_DIR / "trading_calendar.csv", parse_dates=["day"])["day"]
cal = ExpiryCalendar(pd.DatetimeIndex(days))
e1 = cal.next_expiry(pd.Timestamp("2023-06-12"))  # Mon → Thu same week
check("Mon->Thu weekly expiry", e1 == pd.Timestamp("2023-06-15"), f"(got {e1.date()})")
e2 = cal.next_expiry(pd.Timestamp("2023-06-15"))  # Thu itself: DTE 0 < 2 → next week
check("expiry-day rolls to next week", e2 == pd.Timestamp("2023-06-22"), f"(got {e2.date()})")
e3 = cal.next_expiry(pd.Timestamp("2025-10-06"))  # post-switch: Mon → Tue
check("post-Sep-2025 expiry is Tuesday-based", e3.weekday() in (0, 1), f"(got {e3.date()} wd={e3.weekday()})")
check("strike rounding", float(nearest_strike(24013.0)) == 24000.0 and float(nearest_strike(24026.0)) == 24050.0)
t_yrs = years_to_expiry(pd.Timestamp("2023-06-12 09:30:00"), pd.Timestamp("2023-06-15"))
check("years_to_expiry ~3.25d", 3.0 / 365 < t_yrs < 3.5 / 365, f"({t_yrs * 365:.2f}d)")

# ── 3. No-lookahead prefix property on real data (2023 H1) ───────────────
nifty = pd.read_parquet(PROCESSED_DIR / "nifty_1min.parquet")
sub = nifty.loc["2023-01-01":"2023-06-30"]
cut = sub.index[len(sub) // 2]
pre = sub.loc[:cut]
for name, fn in [("ema21", lambda d: ema(d["close"], 21)),
                 ("rsi14", lambda d: rsi(d["close"], 14)),
                 ("twap", session_twap),
                 ("adx5m", adx_5min_on_1min)]:
    full_v = fn(sub).loc[cut]
    pre_v = fn(pre).loc[cut]
    ok = (np.isnan(full_v) and np.isnan(pre_v)) or abs(full_v - pre_v) < 1e-9
    check(f"no-lookahead prefix: {name}", bool(ok), f"(full={full_v:.4f}, prefix={pre_v:.4f})")

# ── 4. Signals end-to-end on 2023 H1 ─────────────────────────────────────
vix = pd.read_parquet(PROCESSED_DIR / "vix_1min.parquet").loc[sub.index.min():sub.index.max()]
filt = build_filters(sub, vix)
ev = signal_events(sub, filt, StrategyParams())
n_days = sub.index.normalize().nunique()
per_day = len(ev) / n_days
print(f"\nsignal events 2023H1: {len(ev)} over {n_days} days = {per_day:.1f}/day")
print(ev["signal"].value_counts().to_string())
print(ev.head(8).to_string(index=False))
check("signal volume in workable range (3-80/day pre-cap)", 3 <= per_day <= 80)
check("both directions present", set(ev["direction"].unique()) == {1, -1})

print(f"\n{'ALL PASS' if not failures else f'FAILURES: {failures}'}")
sys.exit(0 if not failures else 1)
