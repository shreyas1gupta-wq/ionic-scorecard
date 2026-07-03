---
name: pre-trade-check
description: Mandatory pre-trade risk gate (RP-29) — size vs caps, heat, correlation, margin, event windows, exit liquidity. Use for /pre-trade-check <trade> before ANY paper entry.
---
# /pre-trade-check — owner: Ritika Sharma
1. Spawn Ritika with the intended trade (legs/size) + book state.
2. RP-29 checklist vs RISK_LIMITS: each line PASS/FAIL — ONE FAIL BLOCKS (no discretionary override below CIO).
3. Result logged in the trade's PAPER_LEDGER row (checked-by field). Composes with /events (calendar) + /structure-trade (vehicle).
