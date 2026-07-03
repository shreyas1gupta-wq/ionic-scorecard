# D-M6 — purgedcv v0.1.2 Acceptance (S-01 DSR + PBO recompute)

**Date:** 2026-07-04 · **Owner:** Arjun Rao · **Decision:** whether to replace the hand-rolled DSR/PBO in the RESEARCH_SOP battery with `purgedcv`.

## Result
**VERDICT: ADOPT.** `purgedcv` reproduces the hand-rolled DSR to within **0.006 (0.8%)** and agrees on the S-01 PBO verdict (both FAIL, PBO well above 25%). The one earlier discrepancy (DSR 0.917) was a **caller units error on my side (`bars_per_year`), not a library defect** — corrected, it lands at 0.6926 vs hand-rolled 0.6870. purgedcv's PBO uses the canonical Bailey-Zhu CSCV (more defensible than the hand-rolled ranking-logit) and is stable at ~0.44 across specifications.

## Data lineage
| Item | Value |
|---|---|
| Slice | `iv_rv >= 1.4 & iv < 1.0` of `intraday_options_strategy/buying/rv_iv_vol.parquet` |
| Slice rows | 1,583 · 195 symbols · monthly EW series booked on EXIT month · **T = 47 months** |
| Return col | `short_ret` (return-on-premium, stable denominator) |
| Trials | N = 13 (9 grid cells {1.2,1.4,1.6}×{0.8,1.0,1.2} + 4 historical) |
| var_sharpe | 0.0517 (variance of the 9 grid per-period Sharpes) — **matches hand-rolled exactly** |
| purgedcv | v0.1.2, interpreter `pythoncore-3.14-64` |
| Hand-rolled source | `results/S-01/20260703_validation/validate_S01.py` (DSR 0.687 / PBO 0.553 in `metrics.json`) |

## DSR comparison
| Method | DSR | sr_star | var_sharpe | skew | kurt | Verdict (>0.95) |
|---|---|---|---|---|---|---|
| Hand-rolled (B&LdP 2014) | 0.6870 | 0.3873 | 0.0517 | −3.74 | 20.86 | FAIL |
| **purgedcv (correct units)** | **0.6926** | 0.3873 | 0.0517 | −3.74 | 20.86 | FAIL |
| purgedcv (WRONG bars_per_year=12) | 0.9167 | 0.1118 | 0.00431 | — | — | (units error — discard) |

**Agreement:** identical `sr_star` (0.3873), `emax` (1.7033), `var_sharpe` (0.0517), skew, kurtosis. The 0.006 residual is purgedcv's small-sample Sharpe bias correction (`observed_sr` 0.5449 vs hand-rolled 0.5390) inside the PSR moment form — a *feature*, slightly more conservative-correct. **Two independent implementations of Bailey & López de Prado 2014 converge → the hand-rolled DSR was numerically correct.**

### The discrepancy that must go in the SOP (units trap)
purgedcv's `var_sharpe` is **per-observation** unless you pass `bars_per_year`, in which case it *divides* by it. Our grid Sharpes were already **per-period (per-month)**, so `var_sharpe=0.0517` is already per-observation and `bars_per_year` must be **omitted**. Passing `bars_per_year=12` divided it to 0.00431, collapsed `sr_star` from 0.387 to 0.112, and falsely inflated DSR to 0.917 (a "pass"). **This is exactly the kind of silent unit error that waves a fake through.** SOP note (below) is mandatory.

## PBO comparison
| Method | PBO | Verdict (<0.25) | Notes |
|---|---|---|---|
| Hand-rolled CSCV (ranking-logit, S=12) | 0.5530 | FAIL | `rank/N` fraction-beaten construction |
| purgedcv CSCV n_splits=16 | 0.4384 | FAIL | canonical Bailey-Zhu, slope −0.62 |
| purgedcv CSCV n_splits=12 | 0.4654 | FAIL | slope −0.69, 924 combos (matches hand-rolled combo count) |
| purgedcv CSCV n_splits=8 | 0.4429 | FAIL | slope −0.75 |
| purgedcv (complete-case, no 0-fill) | 0.384–0.443 | FAIL | fill-treatment sensitivity check |

**Reconciliation of the ~8-11pt gap:** (a) purgedcv uses the standard CSCV logit on the actual OOS Sharpe metric with a negative `slope` diagnostic (overfit-consistent); the hand-rolled used a simpler rank-fraction logit that runs hotter. (b) Input orientation: purgedcv requires `(n_configs, n_obs)` = 9×47 (I initially passed the transpose and it errored — fixed). Both methods **agree on the verdict (PBO ≫ 25% → S-01 is overfit-prone)** and purgedcv is stable at ~0.44 across n_splits and fill treatment. The canonical method is preferable to the ad-hoc ranking-logit.

## Guards / self-red-team
- Reproduced the EXACT hand-rolled inputs (same slice, same monthly series, same N=13, same var_sharpe) before comparing — no moving parts.
- Caught and corrected my own `bars_per_year` units error rather than reporting the 0.917 pass.
- Verified PBO orientation and fill-sensitivity (0-fill vs complete-case) — verdict robust either way.

## Decision & SOP changes
**ADOPT `purgedcv` v0.1.2** as the DSR/PBO engine in the RESEARCH_SOP validation battery, replacing the hand-rolled functions, with three binding usage notes:
1. **DSR units:** trial-Sharpe `var_sharpe` MUST be in the same units as the per-observation Sharpe of the returns. For per-period (monthly/daily) trial Sharpes, **omit `bars_per_year`**. Only pass `bars_per_year` if `var_sharpe` came from an *annualised* Sharpe (e.g. `path_metrics` output). Add an assertion in our wrapper that flags when `bars_per_year` is set alongside an already-per-period `var_sharpe`.
2. **PBO input:** matrix is `(n_configs, n_obs)` — transpose our months×configs frames. `n_splits` even, over the time axis; use the same S (12 or 16) firm-wide for comparability; record the `slope` diagnostic.
3. **Report the `deflated_sharpe_ratio_full` diagnostics** (sr_star, expected_max_z, observed_sr, var_sharpe) alongside the scalar so the "why" is auditable — this is what let me catch the units error.

S-01 itself remains **FAIL** on both gates (DSR 0.69 < 0.95, PBO ~0.44 > 0.25) — unchanged by the engine swap. The tail-seller degenerate profile (Sharpe 8.6, win 90%, skew −3.74) stands.

## Files
- `results/S-01/20260704_purgedcv_acceptance/purgedcv_recompute.py` — recompute script
- `results/S-01/20260704_purgedcv_acceptance/recompute.json` — full numeric comparison
- `results/S-01/20260704_purgedcv_acceptance/recompute_raw.txt` — console output
- Compared against: `results/S-01/20260703_validation/metrics.json` (hand-rolled 0.687 / 0.553)
