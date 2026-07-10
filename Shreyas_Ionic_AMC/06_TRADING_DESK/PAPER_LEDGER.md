# PAPER LEDGER — append-only (Tara Singh reconciles weekly; RESEARCH_SOP §12)
Rules: log the signal BEFORE market action (timestamp, intended price, size). Mark fills vs actual Angel quotes at action time. Never edit a row — corrections are new rows referencing the old ID.

## Open positions
| PID | Date-in | Strategy | Symbol | Structure (legs/strikes/expiry) | Intended px | Marked fill | Size | Stop/kill | Notes |
|---|---|---|---|---|---|---|---|---|---|
| — | | | | | | | | | |

## Closed trades
| PID | In → Out | Strategy | Symbol | P&L (₹, after draft costs) | Sim-expected P&L | Tracking error | Error decomposition (slippage/timing/fill/decay) |
|---|---|---|---|---|---|---|---|
| — | | | | | | | |

## Weekly reconciliation log
| Week | Trades | Paper P&L | Sim P&L | TE | Dominant cause | Action |
|---|---|---|---|---|---|---|
| — | | | | | | |

**2026-07-10 — S1-F registered for paper forward test** (spec pinned @ b8d2f3d). Per-expiry intents log to `paper/s1f_paper_log.csv` via the daily runner BEFORE action; fills marked vs Angel quotes; Tara reconciles Fridays. First eligible expiry: 2026-07-14 (Tue).
