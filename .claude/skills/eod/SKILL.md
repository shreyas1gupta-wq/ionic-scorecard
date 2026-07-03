---
name: eod
description: Run the Shreyas_Ionic_AMC end-of-day operations checklist — capture-task health, data freshness, pending queues, journal update. Use for /eod, "run EOD", or at the end of any working session.
---

# /eod — end-of-day ops (DESK-100 cadence)

1. Read `Shreyas_Ionic_AMC/99_OPS/EOD_ROUTINE.md` and execute its manual checklist: capture-log health (`AppData\Local\angel_capture\capture.log` post-close line today), freshness pings (angel_capture day/ max date; forthcoming_results age), pending queues (23 Angel stragglers), expiry-week capture confirmation.
2. Anything stale/broken → fix if ≤15 min (rate-limit-aware), else file under Next Actions in `01_COMMAND_CENTER/CURRENT_STATE.md`.
3. Close the books: append a SESSION_JOURNAL entry (what happened, files touched, handoffs) + refresh CURRENT_STATE. Commit the command layer (`git add -A && git commit`) — data stays out per .gitignore.
4. Cheap tier throughout; this is mechanical hygiene, not judgment.
