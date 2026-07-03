---
name: stress-replay
description: Replay a historical crisis path (Mar-2020 / 2022 hikes / Jun-2024 election) on the current paper book, day-by-day (RP-30). Use for /stress-replay <scenario>, monthly CIO stress cadence, or before sizing up.
---
# /stress-replay — owner: Ritika Sharma
1. Spawn Ritika with the scenario + current PAPER_LEDGER positions.
2. RP-30: shock underlyings+IVs along the historical PATH (not endpoint); mark P&L daily; margin spiral; which circuit-breakers trip when.
3. Output: worst-PATH table + survival verdict vs RISK_LIMITS stress rules; file to 07_RISK_OFFICE/, cite in month-end checkpoint.
