"""Sleeve order generation (S2 range premium, S3 0DTE, S4 trend rider).

Each generator returns list[OrderSpec] for engine_v2. All gates use only
information available at the signal bar's close (next-bar-open entry).
S1 (v1 momentum long options) stays on the v1 engine; its daily P&L joins
at the portfolio layer.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backtest.engine_v2 import ExitPolicy, MultiLegSpec, OrderSpec  # noqa: E402
from features.indicators import atr, orb_levels, true_range  # noqa: E402
from options.option_selector import WEEKLY_START  # noqa: E402

STRADDLE = ((True, 0), (False, 0))


def _qualified_0dte_days(nifty, dayf, filters, expiry_days, gap_max=0.004,
                         vix_max=24.0):
    """Common 0DTE entry gate → list of (signal_dt, ) at 09:19 on qualifying
    expiry mornings (gap small, VIX ok, not an event day)."""
    out = []
    for d, f in dayf.iterrows():
        if (d not in expiry_days or d < WEEKLY_START or np.isnan(f["gap_pct"])
                or abs(f["gap_pct"]) > gap_max or not (f["vix_open"] < vix_max)):
            continue
        dt = _bar_at(nifty, d, "09:19")
        if dt is None or not bool(filters.loc[dt, "event_ok"]):
            continue
        out.append(dt)
    return out


def s5_iron_fly_0dte(nifty, dayf, filters, expiry_days, wing_steps=5,
                     sl=0.60, pt=0.45) -> list[MultiLegSpec]:
    """0DTE defined-risk: short ATM straddle + long wings at +/- wing_steps*50.
    SL/PT as fraction of net credit. Wings cap the trend-day tail."""
    dts = _qualified_0dte_days(nifty, dayf, filters, expiry_days)
    legs = ((True, 0, -1), (False, 0, -1),
            (True, wing_steps, 1), (False, -wing_steps, 1))
    return [MultiLegSpec(signal_dt=dt, sleeve="S5_IF", legs=legs,
                         exit=ExitPolicy(sl=sl, pt=pt, hard_exit="14:30"),
                         min_dte=0, label="IRON_FLY") for dt in dts]


def s6_iron_condor_0dte(nifty, dayf, filters, expiry_days, short_steps=3,
                        wing_steps=8, sl=0.80, pt=0.40) -> list[MultiLegSpec]:
    """0DTE iron condor: short OTM strangle (+/-short_steps) + long wings.
    Higher win-rate, smaller credit than the fly."""
    dts = _qualified_0dte_days(nifty, dayf, filters, expiry_days)
    legs = ((True, short_steps, -1), (False, -short_steps, -1),
            (True, wing_steps, 1), (False, -wing_steps, 1))
    return [MultiLegSpec(signal_dt=dt, sleeve="S6_IC", legs=legs,
                         exit=ExitPolicy(sl=sl, pt=pt, hard_exit="14:30"),
                         min_dte=0, label="IRON_CONDOR") for dt in dts]


def _bar_at(nifty: pd.DataFrame, day: pd.Timestamp, hhmm: str) -> pd.Timestamp | None:
    t = day + pd.Timedelta(f"{hhmm}:00")
    return t if t in nifty.index else None


def s2_range_premium(nifty: pd.DataFrame, dayf: pd.DataFrame,
                     filters: pd.DataFrame, expiry_days: set,
                     sl: float = 0.30, pt: float = 0.50) -> list[OrderSpec]:
    """Sell ATM straddle at 09:20 on qualifying range days; exit 15:00."""
    orders = []
    for d, f in dayf.iterrows():
        if (np.isnan(f["gap_pct"]) or abs(f["gap_pct"]) > 0.003
                or not (11.0 <= f["vix_open"] <= 22.0) or d in expiry_days):
            continue
        dt = _bar_at(nifty, d, "09:19")
        if dt is None or not bool(filters.loc[dt, "event_ok"]):
            continue
        adx = filters.loc[dt, "adx"]
        if not np.isnan(adx) and adx >= 25:
            continue
        orders.append(OrderSpec(
            signal_dt=dt, sleeve="S2", side=-1, legs=STRADDLE,
            exit=ExitPolicy(sl=sl, pt=pt, hard_exit="15:00"),
            min_dte=2, direction_label="SHORT_STRADDLE"))
    return orders


def s3_zero_dte(nifty: pd.DataFrame, dayf: pd.DataFrame,
                filters: pd.DataFrame, expiry_days: set,
                sl: float = 0.25, pt: float = 0.60) -> list[OrderSpec]:
    """Sell ATM straddle on expiry mornings (post weekly launch); exit 14:30."""
    orders = []
    for d, f in dayf.iterrows():
        if (d not in expiry_days or d < WEEKLY_START
                or np.isnan(f["gap_pct"]) or abs(f["gap_pct"]) > 0.004
                or not (f["vix_open"] < 24.0)):
            continue
        dt = _bar_at(nifty, d, "09:19")
        if dt is None or not bool(filters.loc[dt, "event_ok"]):
            continue
        orders.append(OrderSpec(
            signal_dt=dt, sleeve="S3", side=-1, legs=STRADDLE,
            exit=ExitPolicy(sl=sl, pt=pt, hard_exit="14:30"),
            min_dte=0, direction_label="0DTE_STRADDLE"))
    return orders


def s4_trend_rider(nifty: pd.DataFrame, dayf: pd.DataFrame,
                   filters: pd.DataFrame, orb_minutes: int = 15,
                   sl: float = 0.30, partial_at: float = 0.35,
                   trail: float = 0.25, max_per_day: int = 2) -> list[OrderSpec]:
    """Long ATM option on ORB breakout w/ ADX + range expansion + bias agree.

    Partial booking 50% at +partial_at, breakeven floor + trail on the rest.
    """
    c = nifty["close"]
    day_idx = nifty.index.normalize()
    orb_h, orb_l = orb_levels(nifty, orb_minutes)
    expand = true_range(nifty) > 1.5 * atr(nifty, 20).shift(1)
    brk_up = (c > orb_h) & (c.shift(1) <= orb_h.shift(1)) & expand
    brk_dn = (c < orb_l) & (c.shift(1) >= orb_l.shift(1)) & expand
    adx_ok = filters["adx"] > 28
    win_ok = filters["entry_window"] & filters["event_ok"] & filters["vix_ok"]

    bias = dayf["bias"].reindex(day_idx).to_numpy()
    up = (brk_up & adx_ok & win_ok & (bias >= 1.0)).to_numpy()
    dn = (brk_dn & adx_ok & win_ok & (bias <= -1.0)).to_numpy()

    orders, count = [], {}
    pol = ExitPolicy(sl=sl, pt=None, partial_at=partial_at,
                     partial_frac=0.5, trail=trail, hard_exit="15:20")
    for arr, is_call, lbl in ((up, True, "CE"), (dn, False, "PE")):
        for pos in np.nonzero(arr)[0]:
            d = day_idx[pos]
            if count.get((d, lbl), 0) >= 1 or \
                    sum(v for (dd, _), v in count.items() if dd == d) >= max_per_day:
                continue
            count[(d, lbl)] = 1
            orders.append(OrderSpec(
                signal_dt=nifty.index[pos], sleeve="S4", side=1,
                legs=((is_call, 0),), exit=pol, min_dte=2,
                direction_label=lbl))
    return sorted(orders, key=lambda x: x.signal_dt)


def all_expiry_days(trading_days: pd.DatetimeIndex) -> set:
    """Set of days that are themselves a weekly/monthly expiry."""
    from options.option_selector import ExpiryCalendar
    cal = ExpiryCalendar(trading_days)
    return {d for d in trading_days if cal.next_expiry(d, min_dte=0) == d}
