"""OPTION-BUYING strategies (long premium): low capital (premium only), per-trade
loss bounded by premium. Goal: MDD<25%, high CAGR. Tested honestly IS/OOS.

Buyers fight theta + the VRP (realized<implied) we harvest by selling, so the
prior is negative EV. We test the one buying style with a theoretical basis:
CONVEX MOMENTUM — buy a directional option on a confirmed breakout, lose small
often (tight stop), let winners run (trail). Variants on strike (ATM/OTM),
trail, and regime. Plus a long-0DTE-straddle benchmark (= the seller's mirror).

Sizing: premium outlay per trade capped so a full loss is <= RISK_PCT of equity
(keeps MDD bounded); equity compounds on Rs.1Cr.
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest.engine_v2 import ExitPolicy, OrderSpec, simulate_orders  # noqa: E402
from config import PROCESSED_DIR, TOTAL_CAPITAL  # noqa: E402
from features.horizon import day_features  # noqa: E402
from features.indicators import atr, orb_levels, true_range  # noqa: E402
from options.option_selector import WEEKLY_START  # noqa: E402
from strategies.sleeves import STRADDLE, all_expiry_days, s4_trend_rider  # noqa: E402

M, SLIP = 0.80, 0.02
RISK_PCT = 0.004          # full-premium loss <= 0.4% of equity per trade
nifty = pd.read_parquet(PROCESSED_DIR / "nifty_1min.parquet")
vix = pd.read_parquet(PROCESSED_DIR / "vix_on_bars.parquet")["vix"]
filters = pd.read_parquet(PROCESSED_DIR / "filters.parquet")
days = pd.DatetimeIndex(pd.read_csv(PROCESSED_DIR / "trading_calendar.csv",
                                    parse_dates=["day"])["day"])
oos = days[int(len(days) * 0.70)]
dayf = day_features(nifty, vix)
exp = all_expiry_days(days)
LOT = 75


def long_otm_momentum(strike_off=2, sl=0.40, trail=0.30):
    """Buy OTM CE/PE on ORB breakout + ADX>28 + bias agreement; trail winners."""
    c = nifty["close"]; di = nifty.index.normalize()
    orb_h, orb_l = orb_levels(nifty, 15)
    expand = true_range(nifty) > 1.5 * atr(nifty, 20).shift(1)
    up = (c > orb_h) & (c.shift(1) <= orb_h.shift(1)) & expand
    dn = (c < orb_l) & (c.shift(1) >= orb_l.shift(1)) & expand
    adx_ok = filters["adx"] > 28
    win = filters["entry_window"] & filters["event_ok"] & filters["vix_ok"]
    bias = dayf["bias"].reindex(di).to_numpy()
    pol = ExitPolicy(sl=sl, pt=None, partial_at=0.5, partial_frac=0.5, trail=trail, hard_exit="15:15")
    orders, seen = [], {}
    for arr, call, off in [((up & adx_ok & win).to_numpy() & (bias >= 1), True, strike_off),
                           ((dn & adx_ok & win).to_numpy() & (bias <= -1), False, -strike_off)]:
        for p in np.nonzero(arr)[0]:
            d = di[p]
            if seen.get(d, 0) >= 2:
                continue
            seen[d] = seen.get(d, 0) + 1
            orders.append(OrderSpec(signal_dt=nifty.index[p], sleeve="BUY_OTM", side=1,
                          legs=((call, off),), exit=pol, min_dte=2,
                          direction_label="CE" if call else "PE"))
    return sorted(orders, key=lambda x: x.signal_dt)


def long_straddle_0dte():
    out = []
    for d in days:
        if d < WEEKLY_START or d not in exp:
            continue
        t = d + pd.Timedelta("09:19:00")
        if t not in nifty.index or not bool(filters.loc[t, "event_ok"]):
            continue
        out.append(OrderSpec(signal_dt=t, sleeve="BUY_STRAD", side=1, legs=STRADDLE,
                   exit=ExitPolicy(sl=0.5, pt=None, hard_exit="14:30"), min_dte=0,
                   direction_label="LONG_STRADDLE"))
    return out


def report(tr, label):
    if not len(tr):
        print(f"{label}: no trades"); return
    # size each trade: lots so premium*lot*lots ~ RISK_PCT*capital, compound
    eq = TOTAL_CAPITAL
    daily = {}
    for _, t in tr.sort_values("entry_dt").iterrows():
        prem = t["entry_mid"] if "entry_mid" in t else t["v0"]
        lots = max(1, int(RISK_PCT * eq / max(prem * LOT, 1)))
        pnl = t["pnl_per_lot"] * lots - t["fixed_cost"] * lots
        day = t["entry_dt"].normalize()
        daily[day] = daily.get(day, 0) + pnl
        eq += pnl
    dseries = pd.Series(daily).reindex(days).fillna(0.0)
    cap = TOTAL_CAPITAL + dseries.cumsum()
    yrs = (dseries.index[-1] - dseries[dseries != 0].index[0]).days / 365.25
    cagr = (cap.iloc[-1] / TOTAL_CAPITAL) ** (1 / yrs) - 1 if yrs > 0 else 0
    peak = cap.cummax(); mdd = ((peak - cap) / peak).max()
    pnl_t = tr["pnl_per_lot"] - tr["fixed_cost"]; w = pnl_t > 0
    dc = dseries[dseries != 0]
    sh = dseries.mean() / dseries.std(ddof=0) * np.sqrt(252) if dseries.std(ddof=0) > 0 else 0
    print(f"{label:16} n={len(tr):4} WR={w.mean():.2f} CAGR={cagr:+.1%} MDD={mdd:.1%} "
          f"Sharpe={sh:.2f} netRs={dseries.sum():,.0f}")


print(f"OPTION BUYING (long premium), real m={M}, slip={SLIP:.0%}, risk {RISK_PCT:.1%}/trade:")
report(simulate_orders(nifty, vix, long_straddle_0dte(), iv_mult=M, slippage_pct=SLIP),
       "long 0DTE strad")
report(simulate_orders(nifty, vix, s4_trend_rider(nifty, dayf, filters), iv_mult=M, slippage_pct=SLIP),
       "S4 trend ATM")
for off in [1, 2, 3]:
    for trail in [0.25, 0.40]:
        report(simulate_orders(nifty, vix, long_otm_momentum(off, 0.40, trail),
               iv_mult=M, slippage_pct=SLIP), f"OTM{off} trail{trail:.0%}")
