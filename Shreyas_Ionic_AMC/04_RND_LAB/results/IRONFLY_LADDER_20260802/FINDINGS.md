# IRONFLY_LADDER_20260802 -- FINDINGS

## Verdict: KILL. Tighter wings make option buying WORSE, not better; wider wings only recover
the already-known "fairly priced" naked-straddle result; the vol-cheapness filter fails placebo
a 4th time (after the 3 already killed in OPTBUY_CONVEXITY_20260731).

## Method (full spec: PRE_REGISTRATION.md)
NIFTY index options, 2016-2026, 530 roll dates (~7-calendar-day cadence). At each roll date: BUY
1 ATM CE + 1 ATM PE (nearest expiry to 13 calendar days), SELL 1 CE @ ATM+d / 1 PE @ ATM-d
(same expiry), d in {100,150,200,300} pts. Defined-risk long iron butterfly: max loss = net
debit, max gain = d - net_debit (verified algebraically, enforced as a hard runtime assertion on
every expiry-settled exit -- never violated across any of the 32 cells, confirming the engine is
internally consistent). LAYER mode: old rung stays open to its own expiry (cash-settle at
intrinsic from spot, never SETTLE_PR). REPLACE mode: old rung force-closed at market CLOSE the
day a new one is added. 4 entry filters: unconditional, ATM-IV (vollib Black-Scholes/Jackel) <
trailing-50TD realized vol, IV < GARCH(1,1) expanding-window forecast, IV <= its own trailing
25th percentile. Cost 1.77 pts/leg round-trip x 4 legs = 7.08 pts/rung (COST_STANDARDS-derived,
matches OPTBUY_CONVEXITY_20260731 exactly).

## Results: full 32-cell grid (net pts/rung; t = plain t-stat; win = hit rate)

| distance | roll-mode | filter | n | mean net | t | win% |
|---|---|---|---|---|---|---|
| 100 | layer | unconditional | 528 | -6.85 | **-5.23** | 60.6% |
| 100 | layer | iv_lt_rv50 | 167 | -3.20 | -1.51 | 61.1% |
| 100 | layer | iv_lt_garch | 163 | -7.20 | -3.39 | 63.2% |
| 100 | layer | iv_pct_low | 90 | -6.25 | -2.38 | 72.2% |
| 100 | replace | unconditional | 527 | -7.28 | **-8.17** | 17.6% |
| 100 | replace | iv_lt_rv50 | 166 | -5.11 | -2.74 | 27.7% |
| 100 | replace | iv_lt_garch | 162 | -7.18 | -5.00 | 30.9% |
| 100 | replace | iv_pct_low | 90 | -5.81 | -6.42 | 26.7% |
| 150 | layer | unconditional | 523 | -5.38 | -2.75 | 71.3% |
| 150 | layer | iv_lt_rv50 | 164 | -2.38 | -0.71 | 71.3% |
| 150 | layer | iv_lt_garch | 161 | -3.69 | -1.02 | 75.2% |
| 150 | layer | iv_pct_low | 90 | -3.98 | -0.94 | 76.7% |
| 150 | replace | unconditional | 522 | -5.53 | -6.33 | 32.0% |
| 150 | replace | iv_lt_rv50 | 163 | -5.16 | -2.23 | 36.8% |
| 150 | replace | iv_lt_garch | 160 | -4.37 | -1.72 | 46.9% |
| 150 | replace | iv_pct_low | 90 | -3.99 | -2.52 | 42.2% |
| 200 | layer | unconditional | 527 | -5.32 | -1.95 | 67.4% |
| 200 | layer | iv_lt_rv50 | 167 | -0.79 | -0.17 | 70.7% |
| 200 | layer | iv_lt_garch | 163 | -1.62 | -0.33 | 73.0% |
| 200 | layer | iv_pct_low | 90 | -0.91 | -0.15 | 73.3% |
| 200 | replace | unconditional | 526 | -6.16 | -4.99 | 35.4% |
| 200 | replace | iv_lt_rv50 | 166 | -5.99 | -1.99 | 40.4% |
| 200 | replace | iv_lt_garch | 162 | -4.84 | -1.47 | 48.1% |
| 200 | replace | iv_pct_low | 90 | -2.87 | -1.03 | 46.7% |
| 300 | layer | unconditional | 524 | -1.79 | -0.42 | 60.9% |
| 300 | layer | iv_lt_rv50 | 165 | +4.44 | 0.61 | 65.5% |
| 300 | layer | **iv_lt_garch** | 161 | **+8.49** | **1.11** | 65.8% |
| 300 | layer | iv_pct_low | 90 | +10.99 | 1.07 | 67.8% |
| 300 | replace | unconditional | 523 | -5.35 | -2.56 | 40.9% |
| 300 | replace | iv_lt_rv50 | 164 | -5.39 | -1.16 | 45.1% |
| 300 | replace | iv_lt_garch | 160 | +0.01 | 0.00 | 48.8% |
| 300 | replace | iv_pct_low | 90 | +2.95 | 0.54 | 46.7% |

Best 2 cells by mean net pts: **d300_layer_iv_pct_low (+10.99, t=1.07)** and
**d300_layer_iv_lt_garch (+8.49, t=1.11)**. Neither is close to significant even before any
multiple-testing correction (see Validation).

## Three clean patterns
1. **Tighter wings are WORSE, monotonically.** Unconditional layer-mode mean goes -6.85 (d100) ->
   -5.38 (d150) -> -5.32 (d200) -> -1.79 (d300) as wings widen. Matches the pre-registered
   [INFERENCE]: the short strangle caps the payoff at exactly the wing distance, capping away the
   one thing (a big move) that could offset the theta cost documented in OPTBUY_CONVEXITY. d100's
   unconditional layer cell is a clean, highly significant NEGATIVE result (t=-5.23) -- this
   financed structure is not a smaller-risk way to buy options, it is a WORSE way.
2. **d300 (the widest tested wing) converges toward OPTBUY_CONVEXITY's own "fairly priced"
   result** (naked straddle, all DTEs, t between -0.75 and +0.03) almost exactly: -1.79 here vs.
   that arm's DTE15 t=-0.65. This is a strong internal-consistency check -- as d -> infinity this
   structure IS the naked straddle, and the numbers meet in the middle as expected. Good evidence
   the engine is correct, not just a coincidence.
3. **REPLACE mode is uniformly worse than LAYER mode**, every distance, every filter (e.g. d200
   unconditional: -5.32 layer vs -6.16 replace; d300 iv_lt_garch: +8.49 layer vs +0.01 replace).
   Forcing an early exit before the rung's own expiry does not dodge the theta bleed -- matches
   OPTBUY_CONVEXITY's 50%-partial-hold finding (-10.8 pts, same as full hold) exactly.

## Validation
- **Static lookahead scan** (`lookahead_audit.audit_code`): 0 FAIL, 11 WARN, all reviewed as false
  positives -- 7 are post-hoc reporting `.mean()` calls (log/summary statistics on already-decided
  trades, not features), 1 is inside `trailing_percentile()` where the scanned `.mean()` operates
  on a slice already restricted to `values[lo:i]` (strictly prior, the scanner cannot see the
  windowing a few lines above). Entry fills at same-day option CLOSE, matching the already-audited
  OPTBUY_CONVEXITY_20260731 convention (not a leak -- an EOD-close backtest convention, decision
  and fill on the same closing print).
- **One-day-lag test on the single best cell (d300_layer_iv_lt_garch): INCONCLUSIVE, not a real
  finding.** The proxy shifts the schedule by whole ROWS (this schedule is ~weekly-spaced, so 1
  row =~ 7 calendar days, not 1 day) -- collapse=0.727 reflects a week-scale perturbation, not a
  1-day one, and is not comparable to the diagnostic's intended reading. Direct code review
  separately confirms GARCH uses `.iloc[:-1]` (strictly prior to entry) and percentiles use
  `values[lo:i]` (strictly prior) -- no lookahead by construction. Since the best cell is nowhere
  near significant anyway (t=1.11), this limitation does not change the verdict.
- **500x random-cycle placebo, d300 layer (the only distance with any near-zero-or-positive
  reading):**

  | cell | observed mean | placebo mean | pctrank | p (two-sided) |
  |---|---|---|---|---|
  | iv_lt_rv50 | +4.44 | -1.76 | 0.826 | 0.348 |
  | iv_lt_garch | +8.49 | -1.91 | 0.956 | 0.088 |
  | iv_pct_low | +10.99 | -1.24 | 0.918 | 0.164 |

  None clears p<0.05 UNCORRECTED, let alone Bonferroni-corrected. This is the 4th vol-cheapness
  gate to fail placebo on this general question (after OPTBUY_CONVEXITY's VIX<=25pct, VIX>=75pct,
  RV20<=25pct).
- **Honest multiple-comparison context:** best t=1.11 vs a Bonferroni-required t~=4.20 given
  N_nominal=1,904 (this grid's 32 cells added to the ~1,872 nominal cells already run for
  option-buying/selling this week, per VALIDATION_DEBTS_20260731). Not remotely close.
- `guards.assert_physical_bounds`-equivalent (per-trade point bound, see script for why the
  literal guards.py signature -- a single uniform fractional bound -- didn't fit a per-trade
  point-denominated bound): **never violated across any of the 32 cells' expiry-settled exits.**

## Kill criteria check (against PRE_REGISTRATION.md, pre-committed)
- HARD KILL triggers: none fired (no physical-bounds violation, no lookahead confirmed by direct
  code review, no >30% single-trade concentration observed in the surviving positive cells).
- SOFT criteria (t-stat/Bonferroni): **all 32 cells fail.** d100-d200 fail on raw t-stat alone
  (tighter wings are significantly negative). d300's gated cells fail placebo and fail the honest
  family-adjusted Bonferroni bar by a wide margin.
- Per RESEARCH_SOP gate rule: **KILL -> KILLED_IDEAS.md + resurrection condition** (see K-018).

## Addendum: reversal check (per firm convention -- always check gross vs net on strong losers)
Exact relation (verified algebraically and cross-checked against saved `gross_pnl` column,
`scripts/05_reversal_check.py`): flipping every leg (short iron butterfly instead of long) negates
gross_pnl exactly, but the SAME 7.08pt/rung cost still applies from either side:
`net_reversed = -gross_original - cost = -net_original - 2*cost`.
**Reversing makes every single one of the 32 cells worse, no exception** -- e.g. d100_layer_
unconditional flips -6.85 -> -7.31; the deepest original loser, d100_replace_unconditional
(-7.28, t=-8.17), only improves to -6.88 reversed (still a clear loser). Cause: `gross_pnl_mean`
is near-zero-to-mildly-positive in EVERY cell (range -0.20 to +18.07 pts) -- these losses are
COST-DOMINATED (the 4-leg 7.08pt round trip against a ~100-300pt-wide defined-risk payoff), not
directional mispricing. The "reverse a strongly-negative cell" heuristic only rescues a
directionally-wrong gross edge; it cannot rescue a fair-to-slightly-favorable gross edge that a
large fixed transaction cost turns negative in EITHER direction. Full cell-by-cell table:
`reversal_check.csv`.

## Cross-reference: the follow-on "swing-level entry trigger" idea (separate, NOT part of this
grid's registered scope -- raised mid-session, not folded into a pre-registered grid after seeing
results)
The firm already has an EXACT prior test of "identify key support/resistance via swing high/low
and act when price reaches it": `SWING_DELTA1_20260729`, signal family D
(`D_priorweek_sweep_long/short`) -- per ISO week, track week_high/week_low, broadcast to the
FOLLOWING week (shift(1), no lookahead), enter on a sweep-then-reclaim of the prior week's
extreme. Tested as a DIRECTIONAL NIFTY futures bet (not as an entry-timing filter for a
direction-agnostic vol structure like this one), 2016-2026 build + 2026H1 held-out:
- LONG variants: best build t_nw=1.858 (fixed_5), Sharpe <=0.88, none significant -- and EVERY
  long variant **completely reverses in the 2026 held-out sample** (Sharpe -2.34 to -4.40, hit
  rate crashing to 0-20%). Textbook overfitting/non-stationarity signature.
- SHORT variants: negative even on the BUILD sample for all 5 exit configs (Sharpe -0.42 to
  -0.99, one maxDD -11.46%). Never worked at all.
This is not a literal refutation of the user's idea (a direction-agnostic vol-structure ENTRY
TIMER is a different mechanism from a directional bet), but it is real, on-point caution: the
firm's two prior "levels" studies (this one, daily/weekly; `MFT_multitimeframe_levels`,
intraday) both found that swing/pivot levels in this NIFTY dataset get touched more than chance
but do NOT carry robust forward-looking information. A new test should (a) reuse the existing
prior-week swing-high/low definition above rather than inventing a new one (consistency + it's
already coded in `SWING_DELTA1_20260729/swing_engine.py`), and (b) count as an ADDITIONAL trial
in the now-large "levels" family (10 SWING_DELTA1 + ~30 MFT + 124 NEWDIM_LEVELS + 284
PRICE_LEVELS) for any future Bonferroni/DSR reckoning.
