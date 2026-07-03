"""Technical indicators — all strictly lookback-only (bars [t-n, t-1] + close(t)).

Every function takes/returns pandas objects aligned to the 1-min bar index.
A value at timestamp t uses ONLY data up to and including bar t's close, so a
signal evaluated at t and executed at t+1's open has no lookahead.

Volume note (PLAN.md caveat 1): index data has no volume, so
  - "VWAP" is a session-anchored mean of typical price (TWAP),
  - volume-expansion confirmations use true-range expansion instead.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False, min_periods=period).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI."""
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50.0)


def bollinger(close: pd.Series, period: int = 20, n_std: float = 2.0
              ) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Returns (mid, upper, lower, width). Width = (upper-lower)/mid."""
    mid = close.rolling(period).mean()
    sd = close.rolling(period).std(ddof=0)
    upper, lower = mid + n_std * sd, mid - n_std * sd
    return mid, upper, lower, (upper - lower) / mid


def rolling_pctile_rank(s: pd.Series, window: int, min_periods: int) -> pd.Series:
    """Percentile rank of the CURRENT value within the trailing window (0..1)."""
    return s.rolling(window, min_periods=min_periods).rank(pct=True)


def true_range(df: pd.DataFrame) -> pd.Series:
    """True range per bar; prev close from the prior bar (lookback-only)."""
    pc = df["close"].shift(1)
    return pd.concat([df["high"] - df["low"],
                      (df["high"] - pc).abs(),
                      (df["low"] - pc).abs()], axis=1).max(axis=1)


def atr(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return true_range(df).rolling(period).mean()


def session_twap(df: pd.DataFrame) -> pd.Series:
    """Session-anchored (reset 09:15 daily) running mean of typical price.

    Equal-weight stand-in for VWAP (index data has no volume).
    Value at t includes bar t's own H/L/C — all known at t's close.
    """
    tp = (df["high"] + df["low"] + df["close"]) / 3
    day = df.index.normalize()
    cum = tp.groupby(day).cumsum()
    n = tp.groupby(day).cumcount() + 1
    return cum / n


def _wilder(s: pd.Series, period: int) -> pd.Series:
    return s.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def adx(df5: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder ADX on (already aggregated) bars. Index = bar END times."""
    up = df5["high"].diff()
    dn = -df5["low"].diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df5.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df5.index)
    tr = true_range(df5)
    atr_w = _wilder(tr, period)
    pdi = 100 * _wilder(plus_dm, period) / atr_w
    mdi = 100 * _wilder(minus_dm, period) / atr_w
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return _wilder(dx.fillna(0.0), period)


def adx_5min_on_1min(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ADX(period) on 5-min aggregated bars, mapped back to the 1-min index.

    Each 5-min bucket is labelled by its END bar's timestamp (e.g. the
    09:15–09:19 bucket completes at the close of the 09:19 1-min bar).
    merge_asof(direction='backward') then gives every 1-min bar the ADX of the
    most recent COMPLETED bucket — at t = bucket end, both the 1-min close and
    the bucket aggregation are known simultaneously, so this is lookahead-free.
    Buckets are formed within each session day (no overnight bleed).
    """
    g = df.groupby([df.index.normalize(), df.index.floor("5min")])
    df5 = g.agg(high=("high", "max"), low=("low", "min"), close=("close", "last"))
    # label each bucket by its SCHEDULED end (floor + 4 min): a partially
    # filled trailing bucket then sorts AFTER current time and is never
    # selected by the backward merge_asof — identical results on prefix data
    sched_end = df5.index.get_level_values(1) + pd.Timedelta(minutes=4)
    df5.index = pd.DatetimeIndex(sched_end, name="dt")
    df5 = df5.sort_index()
    a = adx(df5, period).rename("adx")
    out = pd.merge_asof(pd.DataFrame(index=df.index).reset_index(),
                        a.reset_index(), on="dt", direction="backward")
    return out.set_index("dt")["adx"]


def orb_levels(df: pd.DataFrame, orb_minutes: int) -> tuple[pd.Series, pd.Series]:
    """Opening-range high/low per day from the first `orb_minutes` bars.

    Values are NaN during the opening window and only populate from the bar
    AFTER the window completes, so the levels are always fully formed before
    any breakout test (no lookahead).
    """
    day = df.index.normalize()
    bar_n = df.groupby(day).cumcount()  # 0-based bar number within day
    in_orb = bar_n < orb_minutes
    orb_h = df["high"].where(in_orb).groupby(day).transform("max")
    orb_l = df["low"].where(in_orb).groupby(day).transform("min")
    after = bar_n >= orb_minutes
    return orb_h.where(after), orb_l.where(after)
