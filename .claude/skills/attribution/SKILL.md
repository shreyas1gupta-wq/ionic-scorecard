---
name: attribution
description: Decompose any P&L (book, sleeve, backtest) into beta / regime / factor / selection / costs — the "headlines decompose" analysis. Use for /attribution <target>, monthly book attribution, or "where did this return actually come from".
---
# /attribution — owner: Neel Basu (attribution-analyst-neel-basu)
1. Spawn Neel with the target + data paths (register row, results/ run, or PAPER_LEDGER slice).
2. Method: incremental-vs-base decomposition (RP-13, IC-1 standard) + factor/regime tables with counts.
3. Output: decomposition table + skill verdict; file to 08_BOARD_ROOM/month_end/ (monthly) or the strategy's results dir. Feeds /board-meet.
