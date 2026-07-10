# CHEAP-TEST F9 — NIFTY vs BANKNIFTY Relative Strength (key: rs-nifty-bn)
**Date:** 2026-07-10 | **Verdict: KILL** (pre-registered threshold, frozen before run)

## Spec (pre-registered)
- Data: `intraday_options_strategy/datasets/processed/{nifty,banknifty}_1min.parquet`, 1-min spot, 2015-01-09 -> 2026-05-14, 1,047,492 joined bars. Pre-09:15 bars dropped (guards.drop_preopen).
- Signal: RS = trailing 30-min log-return(BN) - log-return(NIFTY), z-scored over trailing 375 bars (min_periods=300 — mechanical fix: session-start NaNs otherwise starve every window). Event = |z| crosses >=1.5 (activation edge), next-bar entry (assert_next_bar PASS), non-overlapping, no entries after 14:30.
- Outcome: sign(z) x forward NIFTY move in points, 30-min and 60-min horizons (continuation convention; negative = mean-reversion).
- **KILL bar (frozen): day-clustered |t| < 2 OR |mean effect| < 4 NIFTY pts on both horizons; era sign-flip = kill regardless.** Trials ledger: 2 (the two horizons).

## Results
| Horizon | n events | n days | mean pts | t (day-clustered) | Bar |
|---|---|---|---|---|---|
| 30-min | 10,168 | 2,760 | **+0.46** | **1.39** | need >=4 pts, t>=2 -> FAIL |
| 60-min | 7,497 | 2,758 | **+0.25** | **0.31** | FAIL |

Per-era (mean pts / day-clustered t):
| Era | 30-min | 60-min |
|---|---|---|
| 2015-18 | +0.58 / 1.95 | +0.32 / 1.08 |
| 2019-22 | +0.18 / 0.05 | **-0.16 / -0.80 (sign flip)** |
| 2023-26 | +0.65 / 1.02 | +0.67 / 0.67 |

Guards: within-day label-shuffle placebo p = 0.555 (observed |mean| indistinguishable from shuffled). +1-bar extra-lag: mean60 0.12 vs 0.25 base (54% collapse — what little exists sits in the first minute). No horizon/era anywhere near the bar.

## Verdict
KILL. Effect ~0.25-0.46 pts vs the 4-pt bar (~10x short), t ~ 0.3-1.4 vs 2, placebo-consistent, era sign-flip on 60-min. BN->NIFTY 30-60min relative-strength continuation carries no exploitable information; the ~3-pt honest cost floor for a NIFTY option vehicle (COST_STANDARDS D-021) is an order of magnitude above the raw spot edge. Resurrection condition: only a fundamentally different construct (e.g., BN futures order-flow lead at sub-minute horizon), not window/threshold retunes.

## Files
- `rs_nifty_bn_test.py` (this dir) — full script with frozen spec in docstring
- `headline.csv`, `era_table.csv`, `events_h30.csv` (10,168 rows), `events_h60.csv` (7,497 rows)
