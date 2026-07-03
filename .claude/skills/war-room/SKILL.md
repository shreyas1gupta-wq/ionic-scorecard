---
name: war-room
description: Open/update the live market-hours WAR_ROOM.md — positions, P&L marks, today's firing events, desk chatter. Use for /war-room, "open the war room", "update positions/chatter", during market hours.
---

# /war-room — live market-hours board

1. Read `Shreyas_Ionic_AMC/01_COMMAND_CENTER/WAR_ROOM.md`. If stale from a prior week (per its wipe cadence) and unjournaled, append its content to `SESSION_JOURNAL.md` first, then wipe to the empty template.
2. Update `## Positions`: current open positions (paper or live) with legs, size, entry — pull from PAPER_LEDGER open-positions.
3. Update `## Today's events`: earnings/expiry/macro firing today — cross-check against `/events` output (forthcoming_results.csv + STRATEGY_REGISTER event gates); flag anything gating an open position.
4. Update `## Chatter`: append timestamped one-liners (both desks may append freely — DESK-20 and DESK-100 IST timestamp + note); never delete another desk's chatter line, only add.
5. Weekly wipe: journal the full file content as one entry, then reset to the empty header + three empty sections. Cheap tier; mechanical during-session hygiene, not analysis.
