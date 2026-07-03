"""Shreyas_Ionic_AMC — landmine guards. Import into EVERY backtest entry point.
Usage:
    import sys; sys.path.insert(0, r"<root>/Shreyas_Ionic_AMC/04_RND_LAB/lib")
    import guards as G
    df = G.fix_ist_dates(df); intraday = G.drop_preopen(intraday)
    G.assert_pit(signals); m = G.safe_merge(a, b, on="sym")
See 04_RND_LAB/CODE_CHECKS.md for the full battery (degenerate detectors + placebos).
"""
from __future__ import annotations

from datetime import time as _t

import numpy as np
import pandas as pd


# ---------- L1: HF timezone ----------
def fix_ist_dates(df: pd.DataFrame, ts_col: str = "timestamp", out_col: str = "date") -> pd.DataFrame:
    """Daily HF bars are stamped 18:30 UTC == NEXT-day 00:00 IST. Convert properly."""
    ts = df[ts_col]
    if ts.dt.tz is None:
        raise AssertionError("L1: tz-naive timestamps — refuse to guess. Localize at source.")
    df = df.copy()
    df[out_col] = ts.dt.tz_convert("Asia/Kolkata").dt.date
    return df


# ---------- L2: pre-open auction ----------
def drop_preopen(df: pd.DataFrame, ts_col: str = "timestamp") -> pd.DataFrame:
    """Real open = first bar >= 09:15; 09:00 bars are auction prints."""
    return df[df[ts_col].dt.time >= _t(9, 15)]


# ---------- L3: point-in-time ----------
def assert_pit(df: pd.DataFrame, avail_col: str = "available_date", act_col: str = "action_date") -> None:
    bad = (pd.to_datetime(df[avail_col]) > pd.to_datetime(df[act_col])).sum()
    assert bad == 0, f"L3 LOOKAHEAD: {bad} rows act before data was public"


# ---------- L4: merge safety ----------
def safe_merge(a: pd.DataFrame, b: pd.DataFrame, tolerate: float = 0.0, **kw) -> pd.DataFrame:
    n0 = len(a)
    m = a.merge(b, **kw)
    if abs(len(m) - n0) > tolerate * max(n0, 1):
        raise AssertionError(f"L4 merge blew up rows: {n0} -> {len(m)}")
    return m


# ---------- L5: same-bar sin ----------
def assert_next_bar(signal_ts: pd.Series, trade_ts: pd.Series) -> None:
    assert (pd.to_datetime(trade_ts) > pd.to_datetime(signal_ts)).all(), \
        "L5 same-bar sin: trades must occur strictly AFTER their signal bar"


# ---------- L6: option-data schema awareness (gap FILLED with daily bars 2026-07-03) ----------
DAILY_SCHEMA_HINTS = {"settle"}

def option_schema(df: pd.DataFrame) -> str:
    """Return 'daily' (bhavcopy backfill/new names) or 'minute' (HF)."""
    return "daily" if DAILY_SCHEMA_HINTS & set(df.columns) else "minute"

def clean_daily_options(df: pd.DataFrame) -> pd.DataFrame:
    """Bhavcopy daily rows: drop 0.00-price untraded strikes (settlement rows without prints)."""
    if option_schema(df) != "daily":
        return df
    return df[(df["close"] > 0) & (df["volume"] > 0)]

def assert_intraday_capable(df: pd.DataFrame) -> None:
    assert option_schema(df) == "minute", \
        "L6: intraday logic on DAILY-schema option file (bhavcopy backfill) — use EOD logic"


# ---------- degenerate detectors (post-run; see CODE_CHECKS.md) ----------
def degenerate_flags(daily_ret: pd.Series, trades: pd.DataFrame | None = None,
                     ret_col: str = "ret", sym_col: str = "sym") -> list[str]:
    flags: list[str] = []
    r = daily_ret.dropna()
    if len(r) > 30:
        sharpe = r.mean() / (r.std() + 1e-12) * np.sqrt(252)
        eq = (1 + r).cumprod()
        yrs = max(len(r) / 252, 1e-9)
        cagr = eq.iloc[-1] ** (1 / yrs) - 1
        dd = (eq / eq.cummax() - 1).min()
        if sharpe > 4:
            flags.append(f"Sharpe {sharpe:.1f} > 4")
        if cagr > 0.60 and dd > -0.10:
            flags.append(f"CAGR {cagr:.0%} with MaxDD {dd:.0%}")
        x = np.arange(len(eq))
        r2 = np.corrcoef(x, eq.values)[0, 1] ** 2
        if r2 > 0.98:
            flags.append(f"equity R^2 {r2:.3f} > 0.98 (too smooth)")
    if trades is not None and len(trades) > 10:
        t = trades[ret_col].dropna()
        win = (t > 0).mean()
        wl = t[t > 0].mean() / abs(t[t <= 0].mean() + 1e-12)
        if win > 0.75 and wl < 0.5:
            flags.append(f"tail-seller profile: win {win:.0%}, W/L {wl:.2f} — check crash slices")
        if sym_col in trades.columns:
            top = trades.groupby(sym_col)[ret_col].sum().abs().max()
            tot = abs(trades[ret_col].sum()) + 1e-12
            if top / tot > 0.30:
                flags.append("one symbol >30% of |P&L|")
        top5 = t.nlargest(5).sum()
        if t.sum() - top5 < 0:
            flags.append("negative without top-5 trades")
    return flags
