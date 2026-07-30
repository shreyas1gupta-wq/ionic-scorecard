"""[INFERENCE -- not a firm standard; needs CEO+CIO approval under D-025 before adoption].
Explicit, itemised MCX GOLDM (100g) round-trip cost estimate, at 1x and 2x, for cost-sensitivity
reporting on the gold intraday results. COST_STANDARDS.md (D-021, APPROVED) is NSE-only and has
no MCX row -- this fills that gap for THIS mandate only, clearly labelled as unapproved.

Sourced 2026-07-31 (WebSearch, mcxindia.com / mcxccl.com / groww.in / business-standard.com):
  - CTT: 0.01% of trade value, SELL side only (confirmed, mcxccl.com "Commodities Transaction Tax")
  - Exchange transaction charge: ~Rs 2.1/lakh turnover (~0.0021%), MCX fixed-fee structure
    effective 2024-10-01 (SEBI-driven revision)
  - Stamp duty: 0.002% of trade value, BUY side only (uniform post-2020 stamp-duty-reform rate)
  - SEBI turnover fee: Rs 20/crore, both sides (negligible)
  - GST: 18% on (brokerage + exchange txn charge + SEBI fee) -- NOT on CTT or stamp duty
  - Brokerage: ASSUMED flat Rs 20/lot/side (discount-broker convention; NOT sourced from any
    specific broker's live card -- flag this line as the least certain input)
  - Slippage: ASSUMED ~2 ticks/side (Rs 10/tick/lot for GOLDM), i.e. Rs 20/side round-trip-equiv
    -- a judgement call, not measured from real fills (no MCX execution data available here)

NOT SOURCED / weakest links in this estimate: live brokerage card, live bid-ask/slippage in
GOLDM specifically (liquidity is thinner than the 1kg contract). Treat the 2x column as the
realistic worst case, not a remote tail.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gold_lib import mcx_goldm_cost_breakdown

# representative spot: XAUUSD close on the last day of the data (2025-12-31) per gold_lib's own
# verified read; USDINR assumed ~87 (approximate 2025-26 level, NOT a live quote -- [INFERENCE]).
SPOT_USD = 4318.38
USDINR = 87.0

base = mcx_goldm_cost_breakdown(SPOT_USD, USDINR)
print("=== MCX GOLDM (100g) round-trip cost, 1x estimate ===")
for k, v in base.items():
    print(f"  {k:>18}: {v}")

x2 = dict(base)
# 2x sensitivity: double the JUDGEMENT-CALL lines (brokerage, slippage) and the least-certain
# exchange-fee line; CTT/stamp/GST are statutory and would not plausibly double, so they are
# held fixed -- the 2x column answers "what if execution/brokerage costs 2x my assumption",
# which is the actual uncertainty, not "what if the tax rate changes".
notional = base["notional_inr"]
brokerage_rt2 = base["brokerage_rt"] * 2
slippage_rt2 = base["slippage_rt"] * 2
exch_txn_rt2 = base["exch_txn_rt"] * 2
gst2 = (brokerage_rt2 + exch_txn_rt2 + base["sebi_fee_rt"]) * 0.18
total2 = brokerage_rt2 + exch_txn_rt2 + base["ctt"] + base["stamp"] + base["sebi_fee_rt"] + gst2 + slippage_rt2
x2.update(brokerage_rt=round(brokerage_rt2, 2), exch_txn_rt=round(exch_txn_rt2, 2),
          gst=round(gst2, 2), slippage_rt=round(slippage_rt2, 2),
          total_rt_inr=round(total2, 2), pct_of_notional=round(total2 / notional * 100, 4))
print("\n=== MCX GOLDM (100g) round-trip cost, 2x SENSITIVITY (execution/brokerage doubled) ===")
for k, v in x2.items():
    print(f"  {k:>18}: {v}")

print(f"\n=== SUMMARY ===")
print(f"  1x round-trip cost: Rs {base['total_rt_inr']:.0f}  = {base['pct_of_notional']:.4f}% "
      f"of notional  (= breakeven price move, currency-invariant)")
print(f"  2x round-trip cost: Rs {x2['total_rt_inr']:.0f}  = {x2['pct_of_notional']:.4f}% "
      f"of notional")

OUT = Path(__file__).parent
json.dump(dict(spot_usd=SPOT_USD, usdinr=USDINR, cost_1x=base, cost_2x=x2),
          open(OUT / "mcx_cost_estimate.json", "w"), indent=2)
print("\nwrote mcx_cost_estimate.json")
