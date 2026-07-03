---
name: desk-open
description: Morning/session-start routine for Shreyas_Ionic_AMC — sync the books, check overnight health, list today's events and due actions. Use for /desk-open, "open the desk", or at the start of any working session.
---
# /desk-open — start-of-day
1. Read `Shreyas_Ionic_AMC/01_COMMAND_CENTER/CURRENT_STATE.md` + last 2 `SESSION_JOURNAL.md` entries (mandatory sync protocol).
2. Health: AngelDailyOptionCapture log (yesterday post-close line?), data freshness (angel_capture max date, forthcoming_results age).
3. Today's tape: events due (earnings/expiry/macro from `datasets/nse_earnings_dates/forthcoming_results.csv` + STRATEGY_REGISTER event gates), entries due per 08_Execution sheets, open paper positions (PAPER_LEDGER).
4. Output a 10-line DESK BRIEF: state, health, today's actions, blockers. Cheap tier; no subagents unless something is broken.
