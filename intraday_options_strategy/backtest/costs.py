"""Transaction cost model — long-options round trip (buy then sell).

Components per spec (conservative):
  brokerage  ₹20 per order × 2 orders
  STT        0.0625% of SELL-side premium turnover
  NSE txn    0.053% of premium turnover (both legs)
  GST        18% on (brokerage + NSE txn)
  SEBI       ₹10 per ₹1 Cr of premium turnover
  slippage   SLIPPAGE_PCT of premium per leg (modelled in fills by the engine,
             reported here for transparency)
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import (  # noqa: E402
    BROKERAGE_PER_ORDER, GST_PCT, LOT_SIZE, NSE_TXN_PCT, SEBI_PER_CRORE,
    SLIPPAGE_PCT, STT_SELL_PCT,
)


@dataclass(frozen=True)
class TradeCosts:
    brokerage: float
    stt: float
    nse_txn: float
    gst: float
    sebi: float
    slippage: float          # informational — already embedded in fills

    @property
    def explicit_total(self) -> float:
        """Charges deducted from P&L on top of slippage-adjusted fills."""
        return self.brokerage + self.stt + self.nse_txn + self.gst + self.sebi


def trade_costs(entry_fill: float, exit_fill: float, lots: int,
                entry_mid: float, exit_mid: float) -> TradeCosts:
    """Costs for one round trip. Fills are slippage-adjusted premia per unit."""
    units = LOT_SIZE * lots
    buy_turn, sell_turn = entry_fill * units, exit_fill * units
    turnover = buy_turn + sell_turn
    brokerage = 2 * BROKERAGE_PER_ORDER
    stt = STT_SELL_PCT * sell_turn
    nse = NSE_TXN_PCT * turnover
    gst = GST_PCT * (brokerage + nse)
    sebi = SEBI_PER_CRORE * turnover / 1e7
    slip = (abs(entry_fill - entry_mid) + abs(exit_mid - exit_fill)) * units
    return TradeCosts(brokerage, stt, nse, gst, sebi, slip)


def round_trip_example(premium: float = 150.0, lots: int = 1) -> str:
    """Printable round-trip cost breakdown per spec S1 (entry=exit=premium)."""
    em = premium * (1 + SLIPPAGE_PCT)
    xm = premium * (1 - SLIPPAGE_PCT)
    c = trade_costs(em, xm, lots, premium, premium)
    units = LOT_SIZE * lots
    lines = [
        f"Round-trip cost example: premium Rs.{premium:.0f}, {lots} lot(s) x {LOT_SIZE}",
        f"  brokerage      : Rs.{c.brokerage:8.2f}",
        f"  STT (sell)     : Rs.{c.stt:8.2f}",
        f"  NSE txn        : Rs.{c.nse_txn:8.2f}",
        f"  GST            : Rs.{c.gst:8.2f}",
        f"  SEBI           : Rs.{c.sebi:8.2f}",
        f"  slippage (2x{SLIPPAGE_PCT:.2%}): Rs.{c.slippage:8.2f}",
        f"  TOTAL          : Rs.{c.explicit_total + c.slippage:8.2f} "
        f"({(c.explicit_total + c.slippage) / (premium * units):.3%} of premium value)",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(round_trip_example())
