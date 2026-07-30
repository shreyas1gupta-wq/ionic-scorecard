# Pre-registration — Debit Spreads vs Naked Long (ARM: DEBIT SPREADS)
Owner: Aakash Jain (Derivatives Structurer). Date: 2026-07-29. Written BEFORE
`run_debit_spreads.py` was executed. Any deviation discovered after seeing results is
logged verbatim in the final memo, not silently absorbed. [DATA]/[INFERENCE]/[OPINION]
tags used throughout the memo as required by firm protocol.

## Question under test
A long option's enemy over a multi-bar/multi-day hold is THETA, not transaction cost
(Rs25/lot/side => ~0.67pt round trip on the long leg alone, per SHARED_CONTEXT). A debit
spread sells a further-out strike to fund part of the premium, cutting theta/vega but
capping upside. Does the theta saved exceed the capped-upside cost, on signals we
actually have signal_budget evidence for? This is a STRUCTURE comparison, not a new
signal search — the entries are IDENTICAL between the naked and spread legs of each
comparison; only the vehicle changes.

## Signal sources (6, all reused, none re-derived)
Reused verbatim from `EMA_INTRADAY_BUYING_20260729/signal_budget/measure_signal_budget.py`
(sweep + ORB detectors) and `intraday_options_strategy/buying/engine_swing.py`
(`entry_days()` for the daily/swing trend triggers):
1. `sweep_priorday_reclaim` — 15-min, mixed direction (10.03 pts, t=3.10 in the budget run).
2. `sweep_intraday_continue` — 15-min, mixed direction (6.52 pts, t=2.94).
3. `volbrk_orb_volfilter` — 5-min, mixed direction, ATR-expansion-gated ORB (5.60 pts, t=2.23).
4. `trend_ema_cross` — daily, long-only (CE only; the design's stated "no short-side edge").
5. `trend_breakout20` — daily, long-only, 20-day high breakout.
6. `trend_bigday` — daily, long-only, >1.0% up-day continuation.
(4-6 are engine_swing's three built-in daily triggers, run with its default params —
included as "the daily/swing trend signals" named in the task; not separately re-tuned.)

## Grid (small, pre-registered — exact trials count below)
- **Long strike**: {ATM, 1-ITM} (2)
- **Spread width**: {0=naked, 1, 2, 4} strikes, STEP=50 (4)
- **DTE bucket at entry**: {0-1, 2-3, 4-7, 8-15} via `chain.nearest_expiry(day,min,max)` (4)
- **Hold**: {intraday_flat (flat 15:25 same day as entry), reversal (exit on the next
  opposite-direction signal from the SAME detector, or the daily mirror-condition for the
  trend triggers), 5day (max 5 calendar days, exit 15:15)} (3)
- Hard exit boundary in every case: the contract's own expiry, cash-settled at INTRINSIC
  from the underlying close (never the expiry-day option settle price — landmine #9).

**Trials count: 2 x 4 x 4 x 3 x 6 signals = 576 cells.** Each cell run once over the full
available history (2021-05..2026-06), then split by date into BUILD (<=2025-12-31, all
selection/reporting of "best cell" happens here) and FORWARD (2026 H1, reported only,
never used to pick a cell). No cell is dropped after the fact even if degenerate (e.g.
hold=5day at dte_bucket=0-1 collapses to hold-to-expiry — flagged, not hidden).

## Costs (binding, per SHARED_CONTEXT + task brief)
- Brokerage-equivalent: **Rs25/lot/side, flat**, charged per leg per side. Naked = 2 sides
  (buy+sell) => Rs50/lot round trip. Spread = 4 sides => Rs100/lot round trip.
- Slippage, applied as flat premium points per side (per SHARED_CONTEXT's own pre-approved
  0.25-0.5pt/side range, not re-derived): **0.25pt/side on the long (near-the-money) leg,
  0.50pt/side on the short (further-OTM) leg** — the higher end applied to the thinner leg.
  [INFERENCE: no bid-ask quote data exists to derive this from real spreads; this is a
  disclosed assumption within the firm's own pre-approved band, not a new heuristic.]
- GROSS = raw mid-price P&L (open-to-close/intrinsic), no costs. NET = GROSS minus
  slippage minus brokerage-equivalent, both reported always, per signal per cell.

## Liquidity honesty (critical point 1)
For every spread trade, the SHORT leg's real 1-min `volume` at its entry fill bar and its
exit fill bar is recorded from the actual option-chain parquet (not assumed). Reported per
signal/width: fraction of short-leg fills with entry OR exit volume == 0, and fraction
with volume < 10 (contracts). No slippage inflation is applied beyond the flat 0.50pt/side
above — the volume fractions are the honesty check on whether that flat assumption is even
defensible, not an input to the cost model.

## Pre-registered kill/verdict rule
- A cell is a **KILL** if BUILD-period NET mean pts/trade <= 0, regardless of naked or
  spread win rate dress-up.
- The spread **wins** the vehicle comparison at a matched (signal, offset, dte, hold) cell
  if its BUILD NET mean pts/trade (or NET Sharpe, reported alongside) exceeds the naked
  leg's at the SAME cell. "Matched" = identical entries; only the structure differs.
- Representative cell per signal for the headline table = the (offset, dte, hold) with the
  best BUILD NET mean pts/trade for the **naked** leg (chosen before comparing to spread
  results, to avoid picking the config that flatters the spread). Full 576-cell grid is
  written to disk regardless for the trials-count/DSR-PBO record.
- No re-tuning after seeing results. Any deviation from this file is logged, not absorbed.
