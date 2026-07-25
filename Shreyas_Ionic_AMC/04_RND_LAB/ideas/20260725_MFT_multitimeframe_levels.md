# MFT — Multi-TimeFrame Level Strategy (Gate-1 INTAKE, pre-registration)

**Created:** 2026-07-25 · **Origin:** Principal direct order ("create a new strategy MFT")
**Status:** GATE-1 INTAKE — pre-registered BEFORE any result was computed. Nothing here may be
edited after the Gate-3 existence test runs; a changed definition = a new version, new trials count.

## Hypothesis
NIFTY 50 price reacts differently at *multi-timeframe swing levels* (prior day/week/month extremes,
major weekly/monthly fractal pivots, sample-max highs) than at ordinary price points. If true, those
levels carry tradeable information for 5–15-min execution. If false, the whole family dies here.

**Direction is deliberately NOT specified.** A level could produce either expansion (breakout) or
reversion. Pre-committing to one would be a free parameter. The existence test measures both.

## Why this needs unusually strict pre-registration
"Key swing high" is trivially definable *after* you know what happened — this family's failure mode
is hindsight in the level definition, not in the entry rule. Two specific traps, both closed below:
1. **Fractal confirmation lag (T-class lookahead).** An N-bar fractal pivot at bar *i* is only
   knowable at bar *i+N*. Marking it active at *i* imports future information.
2. **Level-set inflation.** Every extra timeframe/level type is a design cell. Counted below and
   carried into DSR.

## Pre-registered level definitions (FROZEN)
Execution timeframe: **5-min** (15-min as the single pre-declared robustness check, not a tuning knob).
Data: `intraday_options_strategy/datasets/raw/kaggle/debashis74017__nifty-50-minute-data/NIFTY 50_minute.csv`
(1-min, 2015-01-09 → 2026-05-15, 11.3 yrs), resampled. Daily/weekly/monthly bars derived from the same
source so there is no cross-source basis mismatch.

| # | Level | Definition | Available from |
|---|---|---|---|
| 1 | Prev-day H / L / C | completed prior session | next session open |
| 2 | Prev-week H / L | completed prior calendar week | next week open |
| 3 | Prev-month H / L | completed prior calendar month | next month open |
| 4 | Weekly swing pivots | N=3 fractal on weekly bars | pivot bar + 3 weeks |
| 5 | Monthly swing pivots | N=2 fractal on monthly bars | pivot bar + 2 months |
| 6 | Sample-max high / running low | max/min of all bars strictly before today | next session |

- N values (3 weekly, 2 monthly) are **fixed by declaration, not tuned.** Any other N = new version.
- Level 6 is labelled **sample-max, NOT "all-time"** — history starts 2015-01-09, so a true all-time
  level is not computable from this source. Calling it all-time would be a false claim.
- **Warm-up:** 2015-01-09 → 2015-12-31 is level-formation only. Test window starts **2016-01-01**.
- Current-day developing H/L is deliberately EXCLUDED from the existence test (it is a
  same-bar-simultaneity hazard); it may enter only at the strategy stage, if the gate passes.

## Touch definition (FROZEN)
A *touch* = a 5-min bar whose [low, high] range contains the level, counting only the **first** touch
of that level per session (repeat touches are the same event, not independent observations).
Approach direction = sign of the prior 3-bar move into the level.

## Metrics (FROZEN, both reported)
Over the next **K=6 bars (30 min)** after the touch bar closes:
- **Expansion:** mean |forward return| — do levels mark volatility events?
- **Reversion:** share of touches where the forward move is opposite the approach direction.

## Placebo (the actual gate)
For each real level, a placebo level = same level shifted by a random uniform offset of
±0.2%–1.2% of spot. This preserves price locality, the touch mechanic and the distance distribution
while destroying the "this is a genuine swing level" property. **100 placebo draws.**

## PRE-REGISTERED KILL CRITERIA
- **KILL** if the real-level metric is not in the **top 10%** of the 100-draw placebo distribution
  (i.e. no evidence levels differ from arbitrary nearby prices).
- **KILL** if an effect clears the placebo bar but its magnitude is below a realistic round-trip cost
  at 5-min NIFTY execution per `06_TRADING_DESK/COST_STANDARDS.md` — a real-but-unharvestable effect
  is a dead strategy, and this family's edge-per-trade is small by construction.
- **NOT-KILLED ≠ adopt.** A pass buys a Gate-4 build, nothing more.

## Trials accounting
Level types 6 + 2 execution timeframes + 2 metrics = **declared surface of 24 cells** at this gate.
Carry into DSR at Gate-4. Any post-hoc level variant must increment this count.

## Prior-art obligation (before Gate-4, not before the gate test)
`intraday_options_strategy/` holds ~14 exhaustively-killed intraday NIFTY strategies and OPT-SWEEP-50
found nothing above ~Sharpe 1.0 in this instrument. A `/prior-art` pass is required before any build,
so MFT does not re-test dead ground.

---
# GATE-3 RESULT — **KILLED** (2026-07-25, same day as pre-registration)
Run: `mft_gate3.py`, 209,644 5-min bars 2015-01-09→2026-05-15, test window from 2016-01-01,
**n=4,896 real level touches**, 100 placebo draws, seed 20260725.

| metric | real | placebo mean (sd) | percentile | gate (needs ≥90) |
|---|---|---|---|---|
| Expansion (mean \|30-min fwd ret\|) | 16.21 bps | 16.69 (0.29) | **6** | **FAIL** |
| Reversion (fwd move opposes approach) | 48.39% | 50.19 (0.79) | **1** | **FAIL** |

**Both metrics land at the BOTTOM of the placebo distribution, not the top** — ~2sd *below* random
nearby prices on each. So the result is not merely "no signal": conditional on a touch, genuine
multi-timeframe swing levels are marginally **duller** than arbitrary price points 0.2–1.2% away.
Reversion at 48.39% is a coin flip that leans very slightly toward continuation.

**The one genuine positive finding, worth banking:** real levels were touched **4,896 times vs 3,472
for placebos (+41%)**. Price *does* revisit true swing levels far more often than arbitrary nearby
prices — they are real reference points. But **attraction ≠ prediction**: price goes there more, and
then does nothing distinguishable. That distinction is the reusable lesson.

**NO RE-CUTTING.** Both pre-registered criteria failed at the 6th and 1st percentile. Re-slicing the
test now (level confluence, first-touch-of-month, tighter windows, different K) is exactly the
p-hacking the pre-registration exists to prevent. Any different level definition = a NEW version with
its own trials count, not a rescue of this one. Trials ledger: +24 cells declared.
**Resurrection condition:** only if a *mechanistically different* level construction is proposed
(e.g. volume-at-price / options-OI-derived levels rather than price-extreme levels) — that would be a
genuinely different hypothesis, not this one retuned.

## Honest priors
Level-based S/R is among the most-published retail techniques in existence; strong post-publication
decay is the base case (KNOWLEDGE_BASE lesson 22). The unusual advantage here is that this dataset
**contains COVID, 2018, the 2022 bear and the 2024 election gap** — regimes the firm's option data
lacks entirely. So even a KILL is informative about level behaviour in true tails.
