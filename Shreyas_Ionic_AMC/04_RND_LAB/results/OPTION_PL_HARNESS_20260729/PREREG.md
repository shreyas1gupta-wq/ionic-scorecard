# PRE-REGISTRATION — shared intraday NIFTY option-P&L harness (`opt_pl.py`)
Written 2026-07-29 BEFORE any run. DESK-100. D-035 binding.

Purpose: build ONE reusable harness that turns (signal timestamps + direction) into
per-trade option P&L on REAL 1-min option prices. No formula proxies (Principal order).
Later agents call it blind, so it is validated before use.

## Acceptance criteria (fixed now, not tunable after seeing output)

### UNIT-1 — arithmetic reconciliation (this is the actual correctness test)
Pick 6 filled trades at random. Independently re-read the raw parquet (`chain.load_expiry`)
and recompute: entry bar timestamp, entry `open`, exit bar timestamp, exit `close`, qty,
gross = (exit_fill - entry_fill) * qty.
PASS: all 6 match the harness output to < 1e-6 absolute.
FAIL: harness is fabricating fills -> stop, do not ship.

### UNIT-2 — expiry intrinsic settlement
For a trade forced to expiry: recompute intrinsic from the UNDERLYING (mean of 1-min index
closes 15:00-15:30 on expiry date) independently.
PASS: matches harness `exit_px` to < 1e-6, and the harness read NO expiry-day option price
for that exit (landmine #9).

### UNIT-3 — no-lookahead invariants (hard asserts)
- entry bar timestamp strictly > signal timestamp, for every filled trade.
- exit bar timestamp >= entry bar timestamp.
- strike chosen from spot AT OR BEFORE the signal timestamp only.
PASS: zero violations. Any violation = do not ship.

### UNIT-4 — degenerate-exit control
Config with stop_pct=0.99, target_pct=99.0, no trail, no time stop must produce
100% `squareoff` / `expiry_settle` exits (no stop/target/trail).
PASS: 100%.

**AMENDED 2026-07-29 AFTER RUNNING — criterion was WRONG, harness was RIGHT.**
The 0.99 stop DID fire twice. Inspection showed those were genuine >99% premium
collapses (a 2-strike-OTM CE decaying to under 1% of entry), i.e. the harness behaved
correctly and my acceptance criterion was unsound. Recorded rather than silently
rewritten. Replaced by (see `unit4.py`):
  UNIT-4a: stop/target/trail/time ALL off -> only squareoff/expiry_settle/data_end.
  UNIT-4b: every 0.99-stop exit must satisfy exit_px <= 1% of entry (proves it was real).
  UNIT-4c: no exit price may violate its own trigger level (stop exit <= stop level,
           target exit >= target level).
This amendment changes a TEST, not the harness, and no strategy result was tuned on it.

### REG-1 — regression vs incumbent `emacross_ITM2` (NOT a correctness proof)
Incumbent (engine_swing.py + compare.py + REPORT.md, 2026-07-01), build 2021-2025:
22 trades / 45% win / PF 2.81 / +17.1% on Rs.3L (= +Rs.51,420 net).
Reproduce the same signal set and instrument through the new harness.
Pre-registered "consistent in magnitude and sign" band:
- trades: 22 +/- 5
- win rate: 45% +/- 15pp
- PF: > 1.0 and < 6.0
- total net: positive, within 0.4x - 2.5x of Rs.51,420
Outside the band -> investigate and report the discrepancy; do NOT tune the harness to fit.
STATED UP FRONT: agreement with the incumbent is a REGRESSION TEST ONLY. Both could be
wrong in the same way. UNIT-1/2/3 are the correctness evidence, not REG-1.

### SANITY-5 — random-timestamp control (MUST be net-negative)
>= 1500 random entry timestamps, uniform over build-period sessions in 09:20-14:30, random
direction, same instrument/exit config as a plain intraday long. Buyers pay theta + spread +
costs, so:
PASS = total NET P&L < 0 AND mean net per trade < 0.
FAIL (net >= 0) = the harness has a bug (most likely optimistic fills / sign error) ->
say so plainly and STOP. Do not ship.
Also report GROSS on the same control: gross should be ~0 or negative. Gross strongly
positive with net negative would mean the cost model is carrying the whole result.

### SANITY-6 — cost monotonicity
gross > net for every filled trade (costs strictly positive). PASS: 100%.

## Reporting rules
- GROSS and NET reported separately, always.
- Zero-volume and thin-volume fill fractions reported (requirement 4).
- Reject reasons counted; nothing silently dropped.
- Concentration flagged if >30% of profit is in one trade.
- Forward window 2026-01..2026-06 is HELD OUT: not used for any validation decision here.
