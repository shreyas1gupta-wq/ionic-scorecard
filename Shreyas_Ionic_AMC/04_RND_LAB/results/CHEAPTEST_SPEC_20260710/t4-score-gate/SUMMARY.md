# T4 — GLBS score-gate (>=4/6) confluence monotonicity — CHEAP-TEST RESULT

**Date:** 2026-07-10 | **Runner:** quant engineer (solo, pre-registered) | **Verdict: KILL**

## Pre-registered spec (FROZEN, triage doc `ideas/20260710_principal_intraday_spec_triage.md`)
- KILL if: day-clustered Spearman t < 2 **OR** (bucket>=4 - bucket<=1) spread < 6 NIFTY pts.
- Top bucket (>=4) alone must clear **10 pts** (2x stressed ATM weekly round-trip, COST_STANDARDS D-021 APPROVED) or System 2 has no vehicle.

## Setup
- Data: NIFTY spot 1-min 2021-05-24 -> 2026-06-03 (1,238 days) + 262 front-weekly option expiry files (1-min, ATM band +/-150).
- Events: 5-min impulse bars 09:30-14:50 IST, |5-min move| >= trailing-20-day 75th pctile (adaptive, trailing only). Direction = sign of move. Entry NEXT 5-min bar open; forward = dir x 30-min move in pts (same day).
- Flags (5 of 6; deviations documented): liq_break (PDH/PDL/round-100/OR15 cross, last 6 bars), FVG (3-bar, last 12 bars), VWAP side (TWAP proxy - index volume is 0 on disk), volume (dir-side ATM option 5-min vol > 1.5x trailing 20-bar median - Kavya proxy decision), premium breakout (dir-side ATM close > prior-12-bar max). **OI-confirm DROPPED** - deferred to T6 3-bar-lag build (pre-registered).
- Guards: drop_preopen, assert_next_bar, audit_session (0 findings), one-bar-lag test, within-day label-shuffle placebo (200 reps). Events restricted to ATM-option-covered bars (79.8% coverage).

## Headline (n=15,298 events, 987 days)
| Metric | Value | Bar | Result |
|---|---|---|---|
| Spearman rho (pooled) | 0.017 | - | flat |
| Spearman t (day-clustered) | **1.67** | >=2 | **FAIL** |
| Top(>=4) - Bottom(<=1) spread | **1.80 pts** | >=6 | **FAIL** |
| Top bucket mean | **1.68 pts** (n=5,338) | >=10 | **FAIL** (6x short) |

## Bucket table (fwd pts, 30-min, directional)
| score | n | mean | median |
|---|---|---|---|
| 0 | 766 | +0.11 | -0.78 |
| 1 | 2,519 | -0.19 | -0.85 |
| 2 | 3,333 | +0.05 | -0.25 |
| 3 | 3,342 | -0.23 | -0.95 |
| 4 | 2,680 | +0.94 | +0.78 |
| 5 | 2,658 | +2.42 | +0.23 |
Not monotone 0->3; small lift only at 4-5, an order of magnitude below the option-vehicle bar.

## Per-era (mandatory)
| era | n | rho | t(day-clust) | top mean | spread |
|---|---|---|---|---|---|
| 2021-22 | 4,753 | 0.002 | 0.09 | 2.23 | 1.29 |
| 2023-24 | 6,109 | 0.025 | 1.56 | 1.92 | 2.53 |
| 2025-26 | 4,436 | 0.019 | 1.05 | 0.73 | 1.27 |
No era passes any bar; top-bucket edge DECAYING (2.23 -> 0.73 pts).

## Per-flag marginals (5 diagnostic trials, no promotion)
| flag | spread (pts) | t(day-clust) |
|---|---|---|
| liq_break | -0.89 | -1.12 |
| FVG (novel) | +1.13 | 1.19 |
| VWAP side | +2.82 | 2.38 |
| volume | +0.70 | 0.84 |
| premium breakout (novel, F8-adjacent) | +1.46 | 1.52 |
FVG novelty: ~1 pt, insignificant - does NOT earn a standalone one-pager (GLBS-E dies with it). Premium-breakout marginal here is weak, but T3 tests F8 properly on campaign breakout events - this does not pre-empt T3.

## Robustness
- Placebo (within-day score shuffle, 200 reps): placebo spread mean 1.69 +/- 0.94 vs real 1.80, p=0.405 - the observed spread is **indistinguishable from noise** (bucket-size artifact).
- One-bar-lag test: spread 1.80 -> -0.62 (134% collapse) - whatever tiny signal exists dies with a 5-min delay.
- Lookahead audit_session: 0 findings.

## Verdict — KILL (both kill conditions hit; top-bucket bar also missed)
System 2's central mechanism (score-gate >=4/6) shows no monotone confluence edge: t=1.67<2, spread 1.80<6 pts, top bucket 1.68<10 pts, placebo-consistent, lag-fragile, decaying by era. Consistent with K-001 filter-mining finding (no filter combination rescues intraday option buying). File against K-001 family; resurrection would require a NEW flag set with top-bucket >=10 pts on pre-registered thresholds.

## Trials ledger
Primary 1 (frozen thresholds), marginals 5 (diagnostic only). See README_trials.md.

## Files
- `t4_score_gate.py` (script), `t4_events.csv` (15,298 scored events), `t4_bucket_stats.csv`, `t4_era_stats.csv`, `t4_flag_marginals.csv`, `t4_result.json`, `atm5_cache/` (ATM 5-min build cache, 18MB - reusable by T3/T5).
