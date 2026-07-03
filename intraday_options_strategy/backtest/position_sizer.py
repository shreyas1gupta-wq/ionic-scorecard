"""Fractional Kelly (×0.25) position sizing on rolling trade history.

f* = (W·AvgWin − L·AvgLoss) / AvgWin   (wins/losses in ₹ per trade)
f_actual = 0.25 × f*
C_risk = capital × f_actual × size_mult
lots = floor(C_risk / (premium × LOT_SIZE × sl_pct)),  clamped [1, 20]
plus premium-outlay cap (10% of capital) and the engine-enforced delta cap.

History rule (no lookahead): stats come from trades CLOSED on days strictly
before the current trading day, within the trailing KELLY_REFRESH_DAYS
trading days. Until MIN_TRADES_FOR_KELLY closed trades exist → 1 lot.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import (  # noqa: E402
    KELLY_FRACTION, KELLY_REFRESH_DAYS, LOT_SIZE, MAX_LOTS,
    MAX_PREMIUM_OUTLAY_PCT, MIN_LOTS,
)

MIN_TRADES_FOR_KELLY = 30


class KellySizer:
    """Tracks closed trades; sizes new trades from trailing-window stats."""

    def __init__(self, trading_days: pd.DatetimeIndex) -> None:
        self._day_pos = {d: i for i, d in enumerate(trading_days)}
        self._closed: list[tuple[int, float]] = []   # (day position, net pnl ₹)
        self.last_f: float = 0.0                     # exposed for reporting

    def record(self, exit_day: pd.Timestamp, net_pnl: float) -> None:
        self._closed.append((self._day_pos[exit_day.normalize()], net_pnl))

    def kelly_fraction(self, today: pd.Timestamp) -> float:
        pos = self._day_pos[today.normalize()]
        lo = pos - KELLY_REFRESH_DAYS
        pnls = [p for d, p in self._closed if lo <= d < pos]
        if len(pnls) < MIN_TRADES_FOR_KELLY:
            self.last_f = 0.0
            return 0.0
        wins = [p for p in pnls if p > 0]
        losses = [-p for p in pnls if p <= 0]
        if not wins or not losses:
            self.last_f = 0.0 if not wins else KELLY_FRACTION
            return self.last_f
        w = len(wins) / len(pnls)
        avg_w, avg_l = sum(wins) / len(wins), sum(losses) / len(losses)
        f_star = (w * avg_w - (1 - w) * avg_l) / avg_w
        self.last_f = max(0.0, f_star) * KELLY_FRACTION
        return self.last_f

    def lots(self, today: pd.Timestamp, capital: float, premium: float,
             sl_pct: float, size_mult: float = 1.0) -> int:
        """Lots for a new trade (0 → skip: Kelly says edge ≤ 0 or warm-up)."""
        prem_per_lot = premium * LOT_SIZE
        f = self.kelly_fraction(today)
        if f <= 0.0:
            n = MIN_LOTS if not self._has_history(today) else 0
        else:
            c_risk = capital * f * size_mult
            n = math.floor(c_risk / (prem_per_lot * sl_pct))
            n = max(MIN_LOTS, min(MAX_LOTS, n))
        # premium outlay cap: 10% of capital
        max_outlay = MAX_PREMIUM_OUTLAY_PCT * capital
        while n > 0 and n * prem_per_lot > max_outlay:
            n -= 1
        return n

    def _has_history(self, today: pd.Timestamp) -> bool:
        pos = self._day_pos[today.normalize()]
        lo = pos - KELLY_REFRESH_DAYS
        return sum(1 for d, _ in self._closed if lo <= d < pos) >= MIN_TRADES_FOR_KELLY
