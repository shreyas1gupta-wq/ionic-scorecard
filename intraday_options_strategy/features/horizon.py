"""Multi-horizon trend bias + day-type features (daily granularity).

All values for day D are computed from data up to day D-1's close plus D's
09:15–09:19 opening bars only — usable from 09:20 with no lookahead.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

HORIZONS = {"1d": 1, "1w": 5, "1m": 21, "3m": 63, "6m": 126, "3y": 756}


def daily_from_minute(nifty: pd.DataFrame) -> pd.DataFrame:
    day = nifty.index.normalize()
    g = nifty.groupby(day)
    return pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(),
                         "low": g["low"].min(), "close": g["close"].last()})


def horizon_bias(daily_close: pd.Series) -> pd.DataFrame:
    """Trend-bias score per day in [-2, +2], from PRIOR closes only.

    Components (each ±1/3 of a point, then scaled):
      - sign of return over each horizon (1d,1w,1m,3m,6m,3y)
      - EMA stack: close>EMA20>EMA50>EMA200 fully bullish (+1), inverse (-1)
    Shifted by 1 day → value for day D uses closes through D-1.
    """
    c = daily_close
    parts = [np.sign(c.pct_change(n)) for n in HORIZONS.values()]
    ret_score = sum(parts) / len(parts)                     # [-1, 1]
    e20, e50, e200 = (c.ewm(span=n, adjust=False).mean() for n in (20, 50, 200))
    stack = (np.sign(c - e20) + np.sign(e20 - e50) + np.sign(e50 - e200)) / 3
    bias = (ret_score + stack).shift(1)                     # [-2, 2], lagged
    out = pd.DataFrame({"bias": bias})
    for name, n in HORIZONS.items():
        out[f"ret_{name}"] = c.pct_change(n).shift(1)
    return out


def day_features(nifty: pd.DataFrame, vix_on_bars: pd.Series,
                 orb_minutes: int = 15) -> pd.DataFrame:
    """Per-day features available at 09:20: gap, ORB5 width, prior VIX, bias."""
    d = daily_from_minute(nifty)
    bias = horizon_bias(d["close"])
    gap = d["open"] / d["close"].shift(1) - 1

    day = nifty.index.normalize()
    bar_n = nifty.groupby(day).cumcount()
    first5 = nifty[bar_n < 5]
    g5 = first5.groupby(first5.index.normalize())
    orb5_width = (g5["high"].max() - g5["low"].min()) / g5["close"].last()

    vix_day = vix_on_bars.groupby(day).first()              # 09:15 print (lag-safe)
    vix_prev = vix_day.shift(1)
    prev_range = ((d["high"] - d["low"]) / d["close"]).shift(1)

    out = pd.DataFrame({
        "gap_pct": gap, "orb5_width": orb5_width,
        "vix_open": vix_day, "vix_prev": vix_prev,
        "vix_5d_chg": vix_day - vix_day.shift(5),
        "prev_day_range": prev_range,
        "bias": bias["bias"],
    })
    return out
