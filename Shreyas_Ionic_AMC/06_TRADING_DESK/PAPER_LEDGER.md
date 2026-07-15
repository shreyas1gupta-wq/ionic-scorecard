# PAPER LEDGER — append-only (Tara Singh reconciles weekly; RESEARCH_SOP §12)
Rules: log the signal BEFORE market action (timestamp, intended price, size). Mark fills vs actual Angel quotes at action time. Never edit a row — corrections are new rows referencing the old ID.

## Open positions
| PID | Date-in | Strategy | Symbol | Structure (legs/strikes/expiry) | Intended px | Marked fill | Size | Stop/kill | Notes |
|---|---|---|---|---|---|---|---|---|---|
| S1F-001 | 2026-07-14 | S1-F (0DTE straddle) | NIFTY | **CLOSED same-day (both legs SL): realized -Rs 5,767** | SELL 24150 CE + SELL 24150 PE, 14JUL2026 exp | 09:20 mkt | CE 45.00 / PE 83.15 (09:20 1-min close, Angel) | 2 lots (150 qty/leg) | CE SL 58.50 / PE SL 108.10 (1.30x fill); exit survivors 15:25 | Credit received ₹19,222.50. No vetoes (RSI5(D-1)=56.7, prior-day +0.02%). Log entered 11:35 (late — ok, decision pre-registered from D-1 close, no lookahead). First-ever S1-F ticket. |

## Closed trades
| PID | In → Out | Strategy | Symbol | P&L (₹, after draft costs) | Sim-expected P&L | Tracking error | Error decomposition (slippage/timing/fill/decay) |
|---|---|---|---|---|---|---|---|
| S1F-001 | 2026-07-14 in->out | S1-F 0DTE straddle | NIFTY | **-5,767** | (paper, unlevered) | CE SL@09:24 (-2,025), PE SL@09:46 (-3,742); credit 19,222.5 minus buyback at 1.30x SLs | both legs stopped on AM directional move

## Weekly reconciliation log
| Week | Trades | Paper P&L | Sim P&L | TE | Dominant cause | Action |
|---|---|---|---|---|---|---|
| — | | | | | | |

**2026-07-10 — S1-F registered for paper forward test** (spec pinned @ b8d2f3d). Per-expiry intents log to `paper/s1f_paper_log.csv` via the daily runner BEFORE action; fills marked vs Angel quotes; Tara reconciles Fridays. First eligible expiry: 2026-07-14 (Tue).
