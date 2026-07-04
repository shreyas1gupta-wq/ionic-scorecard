"""EXECUTION REALISM — circuit-lock + volume-conditional slippage (Principal order, 2026-07-04).
"if volume abruptly low instead of fixed standardized slippage we should give more slippage"
Binding on all equity backtests via COST_STANDARDS section 'Dynamic slippage & circuit rule'.

Why: momentum entries correlate with UPPER circuits (buying strength) and stops with LOWER
circuits (gaps through bands) — fixed-bps slippage on those days fabricates impossible fills.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BAND_PCTS = (0.05, 0.10, 0.20)  # NSE price bands (2% exists for a few; treated via no-range rule)
BAND_TOL = 0.004                # band-pin detection tolerance


def circuit_locked(open_, high, low, close, prev_close, volume=np.nan) -> bool:
    """Heuristic circuit-lock detector from OHLCV (no official band file needed).
    Locked if: (a) zero price range (single-print day, typical hard lock), or
    (b) close pinned AT a band limit vs prev_close AND the day never traded off the band."""
    if any(pd.isna(x) for x in (high, low, close, prev_close)) or prev_close <= 0:
        return False
    if high == low:                                   # (a) no range at all
        return True
    ret = close / prev_close - 1.0
    for b in BAND_PCTS:                               # (b) pinned at +b (close==high) or -b (close==low)
        if abs(ret - b) < BAND_TOL and abs(close - high) / prev_close < 1e-4 and (low / prev_close - 1.0) > b - 2 * BAND_TOL:
            return True
        if abs(ret + b) < BAND_TOL and abs(close - low) / prev_close < 1e-4 and (high / prev_close - 1.0) < -(b - 2 * BAND_TOL):
            return True
    return False


def slippage_multiplier(day_volume, median20_volume) -> float:
    """Volume-conditional multiplier on the COST_STANDARDS tier floor (one-way).
    ratio >= 0.5      -> 1.0x (normal)
    0.2 <= ratio<0.5  -> 2.0x (thin day)
    0 < ratio < 0.2   -> 3.0x (abrupt collapse — Principal rule)
    volume 0/NaN      -> inf (NO FILL)"""
    if pd.isna(day_volume) or pd.isna(median20_volume) or day_volume <= 0 or median20_volume <= 0:
        return float("inf")
    r = day_volume / median20_volume
    if r >= 0.5:
        return 1.0
    if r >= 0.2:
        return 2.0
    return 3.0


def fill_check(open_, high, low, close, prev_close, day_volume, median20_volume,
               base_slippage_bps: float):
    """Returns (fillable: bool, effective_slippage_bps: float, reason: str).
    Circuit-locked or zero-volume day -> NOT fillable: defer the trade to the next
    tradeable day (never fill at the locked print)."""
    if circuit_locked(open_, high, low, close, prev_close, day_volume):
        return False, float("inf"), "circuit_locked"
    m = slippage_multiplier(day_volume, median20_volume)
    if not np.isfinite(m):
        return False, float("inf"), "no_volume"
    return True, base_slippage_bps * m, f"vol_mult_{m:.0f}x"


if __name__ == "__main__":
    ok = 0
    # single-print upper lock
    assert circuit_locked(105, 105, 105, 105, 100) is True; ok += 1
    # pinned +5% band, never traded below band-tol -> locked
    assert circuit_locked(104.9, 105.0, 104.7, 105.0, 100) is True; ok += 1
    # normal day
    assert circuit_locked(101, 103, 99, 102, 100) is False; ok += 1
    # -10% pin
    assert circuit_locked(90.2, 90.3, 90.0, 90.0, 100) is True; ok += 1
    # +5% close but traded full range -> NOT locked
    assert circuit_locked(100, 105.2, 98, 105.0, 100) is False; ok += 1
    assert slippage_multiplier(1000, 1000) == 1.0; ok += 1
    assert slippage_multiplier(300, 1000) == 2.0; ok += 1
    assert slippage_multiplier(100, 1000) == 3.0; ok += 1
    assert slippage_multiplier(0, 1000) == float("inf"); ok += 1
    f, s, r = fill_check(105, 105, 105, 105, 100, 500, 1000, 35)
    assert f is False and r == "circuit_locked"; ok += 1
    f, s, r = fill_check(101, 103, 99, 102, 100, 150, 1000, 35)
    assert f is True and s == 105.0; ok += 1  # 35bps x 3
    print(f"execution_realism self-test: {ok}/11 pass")
