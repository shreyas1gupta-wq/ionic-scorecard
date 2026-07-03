---
name: events
description: Refresh the earnings/event calendar and run the event-gate check over current positions and pending entries. Use for /events, "refresh calendar", "any earnings in the window", before every strangle/straddle entry batch.
---
# /events — event-gate keeper
1. Refresh: run `Shreyas_Ionic_AMC/05_DATA_OFFICE/scripts/nse_earnings_refresh.py` (NSE cookie warm-up; works on proxy). Output: forthcoming_results.csv.
2. Cross-check every pending entry (08_Execution) and open paper position: earnings/known binary inside the holding window? → flag per RISK_LIMITS rule "no naked short-vol through a binary".
3. Output: OK-to-trade list, GATED list (name, event, date, rule), and calendar age. If NSE blocked, say so verbatim and use the newest cached file with its date shown.
