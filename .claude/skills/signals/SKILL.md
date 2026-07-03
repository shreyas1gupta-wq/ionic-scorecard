---
name: signals
description: Run the live signal scan for all registered strategies (FF calendar, IV/RV, strangle, earnings) on current Angel data, with conviction + news-risk scoring. Use for /signals, "scan for trades", "what to trade today/this week".
---
# /signals — live signal desk
1. Scripts live in `Shreyas_Ionic_AMC/05_DATA_OFFICE/scripts/`: `execution_scanner.py` (needs angel_cfg + scrip_master in working dir) then `final_execution.py` (conviction + news overlay + earnings gates).
2. Run both; output lands in `FINAL_STRATEGY_FORWARD_CHECK/08_Execution/` (execution_scored.csv, EXECUTION_PLAN.docx).
3. Apply register gates before presenting: S-03 large-cap only; S-02 large-cap + DTE≥7; S-04 event-gate (re-run /events first if calendar >3 days old) + inverse-IV sizing.
4. Present: top trades by conviction with full legs (date/action/strike/CE-PE/price/lots), the AVOID list with reasons, and the macro window warnings. Mark clearly: paper only until Principal live-gate (D-010).
