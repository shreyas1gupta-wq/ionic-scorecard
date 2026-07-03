"""Strike & weekly-expiry selection.

Expiry rules (PLAN.md note 3):
  - weekly expiry day = Thursday for dates before 2025-09-01, Tuesday after
    (NSE moved Nifty weekly expiry effective Sep 2025)
  - if the scheduled expiry date is not a trading day (holiday), roll BACK to
    the previous trading day (NSE convention)
  - if fewer than MIN_DTE_CAL_DAYS calendar days remain at entry, roll to the
    following week's expiry
Strike: round(S / 50) * 50. Time to expiry: minutes to 15:30 of expiry date,
expressed in calendar years (365 d).
"""
from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import MIN_DTE_CAL_DAYS, STRIKE_STEP  # noqa: E402

EXPIRY_SWITCH = pd.Timestamp("2025-09-01")  # Thursday -> Tuesday regime
WEEKLY_START = pd.Timestamp("2019-02-11")   # Nifty weekly options launch
EXPIRY_CLOSE = "15:30"


def nearest_strike(spot: float | np.ndarray) -> np.ndarray:
    return np.round(np.asarray(spot) / STRIKE_STEP) * STRIKE_STEP


class ExpiryCalendar:
    """Weekly expiry lookup backed by the actual trading-day calendar."""

    def __init__(self, trading_days: pd.DatetimeIndex) -> None:
        self.days = pd.DatetimeIndex(trading_days).normalize().sort_values()
        self._set = set(self.days)

    def _prev_trading_day(self, d: pd.Timestamp) -> pd.Timestamp:
        while d not in self._set:
            d -= timedelta(days=1)
            if d < self.days[0]:
                raise ValueError("ran off the start of the trading calendar")
        return d

    def _scheduled_weekday(self, d: pd.Timestamp) -> int:
        return 3 if d < EXPIRY_SWITCH else 1  # Thu=3, Tue=1

    def _monthly_expiry(self, entry_day: pd.Timestamp, months_ahead: int = 0
                        ) -> pd.Timestamp:
        """Last Thursday of the month (pre-2019 era), holiday-adjusted."""
        ref = entry_day + pd.offsets.MonthEnd(0) + pd.offsets.MonthEnd(months_ahead)
        back = (ref.weekday() - 3) % 7
        return self._prev_trading_day(ref - timedelta(days=back))

    def next_expiry(self, entry_day: pd.Timestamp, min_dte: int | None = None
                    ) -> pd.Timestamp:
        """Nearest expiry ON/AFTER entry_day honouring the min-DTE roll.

        Weekly from 2019-02-11 (Nifty weekly launch); monthly (last Thursday)
        before that. min_dte=0 permits same-day expiry (0DTE sleeves).
        """
        entry_day = entry_day.normalize()
        min_dte = MIN_DTE_CAL_DAYS if min_dte is None else min_dte
        if entry_day < WEEKLY_START:
            expiry = self._monthly_expiry(entry_day)
            if expiry < entry_day or (expiry - entry_day).days < min_dte:
                expiry = self._monthly_expiry(entry_day, 1)
            return expiry
        wd_target = self._scheduled_weekday(entry_day)
        ahead = (wd_target - entry_day.weekday()) % 7
        scheduled = entry_day + timedelta(days=ahead)
        expiry = self._prev_trading_day(scheduled)
        if expiry < entry_day:  # holiday roll-back crossed entry → next week
            scheduled += timedelta(days=7)
            expiry = self._prev_trading_day(scheduled)
        if (expiry - entry_day).days < min_dte:
            scheduled += timedelta(days=7)
            expiry = self._prev_trading_day(scheduled)
        return expiry


def years_to_expiry(now: pd.Timestamp, expiry_day: pd.Timestamp) -> float:
    """Calendar-time fraction of a year until 15:30 on expiry day."""
    expiry_ts = expiry_day.normalize() + pd.Timedelta(EXPIRY_CLOSE + ":00")
    minutes = max((expiry_ts - now).total_seconds() / 60.0, 1.0)
    return minutes / (365.0 * 24 * 60)
