"""India VIX processing.

Provides a no-lookahead VIX series for intraday use: each trading day is
assigned the PRIOR day's VIX close (per spec C1 — intraday VIX unavailable),
plus a realised-vol fallback for dates before VIX history begins.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR, REALISED_VOL_WINDOW, TRADING_DAYS_PER_YEAR  # noqa: E402

VIX_CSV = RAW_DIR / "india_vix_daily.csv"
NIFTY_DAILY_CSV = RAW_DIR / "nifty50_daily.csv"


def load_vix_daily() -> pd.Series:
    """Raw India VIX daily closes, indexed by date (normalised)."""
    df = pd.read_csv(VIX_CSV, parse_dates=["Date"], index_col="Date")
    s = df["Close"].dropna()
    s.index = s.index.normalize()
    return s.sort_index()


def realised_vol_proxy() -> pd.Series:
    """Annualised 20-day realised vol of Nifty daily log returns (×100, VIX units).

    Window uses returns up to and including day t's close; the no-lookahead
    shift to t+1 happens in vix_for_trading() for both sources uniformly.
    """
    df = pd.read_csv(NIFTY_DAILY_CSV, parse_dates=["Date"], index_col="Date")
    ret = np.log(df["Close"]).diff()
    rv = ret.rolling(REALISED_VOL_WINDOW).std() * np.sqrt(TRADING_DAYS_PER_YEAR) * 100
    rv.index = rv.index.normalize()
    return rv.dropna().sort_index()


def vix_for_trading(trading_days: pd.DatetimeIndex) -> pd.Series:
    """VIX value usable on each trading day WITHOUT lookahead.

    Day t gets the most recent close STRICTLY BEFORE t (prior-day close).
    Gaps (pre-2008 or missing dates) fall back to the realised-vol proxy,
    likewise lagged. Returned in VIX units (annualised %, e.g. 14.5).
    """
    days = pd.DatetimeIndex(trading_days).normalize().unique().sort_values()
    vix, rv = load_vix_daily(), realised_vol_proxy()
    # shift(1): value indexed at day t is day t-1's close → no lookahead
    vix_lag = vix.shift(1).reindex(days, method="ffill")
    rv_lag = rv.shift(1).reindex(days, method="ffill")
    out = vix_lag.fillna(rv_lag)
    out.name = "vix_lagged"
    return out


if __name__ == "__main__":
    v = load_vix_daily()
    print(f"VIX: {len(v)} rows, {v.index[0].date()} → {v.index[-1].date()}, "
          f"last={v.iloc[-1]:.2f}, max={v.max():.2f} ({v.idxmax().date()})")
    demo = vix_for_trading(v.index[-5:])
    print(demo)
