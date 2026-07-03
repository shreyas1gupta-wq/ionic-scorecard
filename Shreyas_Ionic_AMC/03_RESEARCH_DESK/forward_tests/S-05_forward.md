# S-05 FORWARD TEST — Track-1 delta-hedged 0DTE/DTE1 NIFTY short straddle (PAPER)
**Status: paper-APPROVED (Q3 plan P5, live NOW) · Owner: Vikram Shah · Reconciler: Tara Singh (weekly)**
Registered edge at start (pre-firm validated): CAGR +5.9%, MaxDD 5%, 6/6 years positive [books].
**Entry rule:** trade ONLY when the morning ATM straddle ≥ 0.45% of spot (IV filter). Index-only. Delta-hedged per original spec.
**Ops note:** requires a market-open signal check (09:20 IST): NIFTY ATM straddle price / spot ≥ 0.45%. Until an automated morning task exists, the desk logs the signal manually on session days; missed days are logged as MISSED (not backfilled).
**DoD progress target:** ≥20 trades or 8 weeks (later of), TE explained weekly.

## Signal log (append-only; log BEFORE any fill is known)
| Date | 09:20 straddle/spot | Signal? | Intended entry (legs, px) | Marked fill | Day P&L (paper) | Notes |
|---|---|---|---|---|---|---|
| — | | | | | | |

## Weekly reconciliation
| Week | Trades | Paper P&L | Sim expectation | TE | Decomposition | Action |
|---|---|---|---|---|---|---|
| — | | | | | | |
