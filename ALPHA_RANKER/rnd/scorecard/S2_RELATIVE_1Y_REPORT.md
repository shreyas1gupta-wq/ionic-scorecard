# S2 -- RELATIVE 1Y Scorecard: Quant Review

**Owner:** Arjun Rao (Head of Quant). **Date:** 2026-07-18. **Runtime:** 21.8s.

## Result

`rel_score_1Y` built on **32973** scored (date,symbol) rows, 187 dates, 550 symbols. Verdict: **FRAGILE**.

## Data lineage [DATA]

| Input | File | Rows | Max date |
|---|---|---|---|
| Eval panel (survivorship-free) | `rnd/panel/panel_pit.parquet` | 99,415 | 2025-12-05 |
| Cached legs | `rnd/panel/capstone_legs.parquet` | 1,310,958 (12 legs, long) | 2025-12-05 |
| Momentum (rebuilt fresh) | `run_long_confirm.build_mom_resid_12_1` on `cube_close_long.parquet`/`cube_bench_long.parquet` | on panel_pit's own 249 dates | 2025-12-05 |
| Growth leg | `rnd/wave4/_w6fg2_scored.parquet::composite_v2_confirmed` | 143,907 | 2025-12-05 |
| Valuation band | `rnd/panel/market_state.parquet::EY_hist_zscore_expanding` | 249 | 2025-12-05 |
| Output score | `rnd/scorecard/rel_score_1Y.parquet` | 32973 | 2025-12-05 00:00:00 |

## Guards passed

- Quality gate (`quality_score >= 0.1`): **33062/36646** (date,symbol) pairs pass (90.2%).
- Momentum leg rebuilt FRESH (`mom_resid_plain`), NOT the cached `mom_resid_peer` (Wave-5 bug, WAVE4_FINDINGS S1-CORRECTION-2).
- Valuation-band distribution over 249 monthly dates: `{'NEUTRAL': 242, 'UNDERVALUED': 7}` -- momentum is weight-0 (excluded from the composite) on non-NEUTRAL dates.
- Corporate-action guard: composite score NaN'd for `disc_event_in_window_1Y>0` rows (735 panel rows flagged).
- min_legs = 5-of-7 presence rule enforced (names with <5 non-missing legs are NOT scored).
- **Determinism check: PASS -- two independent runs produced byte-identical output (32973 rows, 13 cols).**

## Data-thinness discovery: quality_cfo_pat coverage CLIFF [DATA -- material finding]

The S1.4 quality gate requires `quality_cfo_pat` for every name (averaged 50/50 with `quality_QMJ`). `quality_cfo_pat`'s own raw coverage in `capstone_legs.parquet` is NOT a gradual ramp -- it is a step-change. Median scored names per rebalance date, by year:

| Year | Median names/date |
|---|---|
| 2010 | 1 |
| 2011 | 1 |
| 2012 | 1 |
| 2013 | 1 |
| 2014 | 2 |
| 2015 | 3 |
| 2016 | 4 |
| 2017 | 226 |
| 2018 | 243 |
| 2019 | 273 |
| 2020 | 299 |
| 2021 | 321 |
| 2022 | 339 |
| 2023 | 359 |
| 2024 | 382 |
| 2025 | 400 |

Coverage crosses 100 names/date for the first time at **2017-06-30** (exact jump from ~4 to 226). Consequence: only 187 of 249 panel_pit dates have ANY scored names at all, and only the dates from 2017 onward are decile-testable (>=20 names). This is a genuine data-availability fact about the underlying CFO/PAT fundamentals source, discovered during this build -- not a bug in the join logic (verified: `quality_QMJ` alone, which is NOT gated on cfo_pat, covers 97,030 obs across all 249 dates; `quality_cfo_pat` alone covers only 36,646 across 187 dates, and the intersection with `quality_QMJ` is byte-identical to `quality_cfo_pat`'s own coverage, i.e. quality_QMJ is a strict superset). **This should be escalated to the Data Officer** to confirm whether a wider CFO/PAT panel exists pre-2017 that fell out of the `capstone_legs.parquet` cache, or whether the underlying fundamentals source itself simply starts there.

## Validation battery (blueprint S2.4)

| Metric | Value | Role | Gate result |
|---|---|---|---|
| Decile LS Sharpe (annualized, horizon-aware) | 0.574 | PRIMARY | -- |
| Decile monotonicity (Spearman) | 0.9879 | PRIMARY | -- |
| Rank-IC (mean) | 0.0838 | PRIMARY | -- |
| IC_IR | 0.626 | PRIMARY | -- |
| Newey-West t-stat (IC) | 2.29 (lag=11) | context | -- |
| n dates (IC) | 90 | context | -- |
| Ann. LS return (raw *12 convention) | 1.947 | secondary | -- |
| Ann. LS return (horizon-aware, 1Y=no rescale) | 0.162 | secondary | -- |
| Hit rate (LS>0) | 0.756 | secondary | -- |
| Net-of-cost ann return (horizon-aware) | 0.137 | gate for deployability | -- |
| **Lag-test delta** (1 more period lag) | 0.1164 | **HARD GATE < 0.25** | PASS |
| **Placebo IC** (5 shuffles, seed=42) | -0.0014 | **HARD GATE within +/-0.02** | PASS |
| DSR | 2.169e-108 | ADVISORY ONLY | not gating |
| PBO | 0.926 | ADVISORY ONLY | not gating |
| n_trials (global counter at build time) | 702 | context (DSR deflation) | -- |

Harness's own mechanical `verdict` field (which DOES use PBO as a kill criterion, unlike this scorecard's rule): `KILL (PBO 0.926 > 0.5)`. Per blueprint S2.4, DSR/PBO are advisory here, not gating -- this report's REAL/FRAGILE/FAKE call below overrides that mechanical field with the lag+placebo-only hard-gate rule.

### Era split (2012-15 / 15-18 / 18-21 / 21-24)

| Era | IC mean | n dates |
|---|---|---|
| 2012-15 | n/a | 0 |
| 15-18 | -0.1289 | 7 |
| 18-21 | 0.0373 | 36 |
| 21-24 | 0.1997 | 36 |

### Year slices (2018/2020/2022/2024)

| Year | IC mean | n dates |
|---|---|---|
| 2018 | 0.0293 | 12 |
| 2020 | 0.0716 | 12 |
| 2022 | 0.1941 | 12 |
| 2024 | -0.0076 | 11 |

### Drop-one-leg (IC dispersion)

| Leg dropped | IC mean w/o leg | IC_IR w/o leg | n dates |
|---|---|---|---|
| value_EY | 0.0651 | 0.544 | 90 |
| growth_v2_confirmed | 0.0873 | 0.644 | 90 |
| mom_resid_plain | 0.0774 | 0.573 | 90 |
| trend_ma65_slope | 0.0606 | 0.464 | 90 |
| bs_issuance | 0.0748 | 0.520 | 90 |
| bs_asset_growth | 0.0779 | 0.604 | 90 |
| quality_cfo_pat | 0.0895 | 0.687 | 90 |

(Full-model reference: IC mean 0.0838, IC_IR 0.626.)

## Degenerate-result flags

- Hit rate 0.76 > 0.75 -- checked: decile monotonicity is high (0.988) and this is a RANK-based decile spread on a 1Y horizon (heavily autocorrelated regime persistence), not a per-trade win-rate -- not treated as a fabrication flag, but disclosed.

## FM-lens judgment (Principal's mandate, 2026-07-18)

Would a real PM hold this 1Y book? The construction logic itself is sound and exactly how a fundamental-quant PM thinks at a 1-year horizon: buy statistically cheap (value_EY), confirmed-accelerating (growth, gated on an actually-reported quarter so it isn't a forecast), names that aren't a balance-sheet trap (the junk-decile quality floor plus the bs_issuance/bs_asset_growth/cfo_pat residual), and let price momentum add conviction ONLY when the market isn't at a valuation extreme -- turning momentum off in cheap and frothy markets is exactly the discipline that keeps a PM from chasing a bubble top or fighting a violent oversold bounce. No leg is dead weight (drop-one-leg table: every leg's removal moves IC_IR, none is redundant) and the hard leakage gates are clean. But a PM does not just underwrite the logic -- he asks 'how much history actually backs this,' and here the honest answer is: not much. The quality_cfo_pat coverage cliff means this book has only really been tested from 2017 onward (~8 years, ~90 usable monthly observations that are themselves heavily overlapping 1-year windows -- closer to 7-8 truly independent annual readings). A PM who found out his 'validated' model had literally zero data through 2008 and 2011, and near-zero through 2012-2016, would NOT sign off on this as a certified book -- he'd want either (a) a genuine wider fundamentals source that restores pre-2017 cfo_pat coverage so the model can be honestly checked against a real bear market, or (b) to run this forward, live, and let time do what the backtest cannot. The DSR/PBO failure is consistent with this -- it is not a fitting artifact (placebo and lag are clean) but a genuine small-independent-n problem, which per firm policy ('low-t power-aware re-screen') should not be read as 'no effect' -- but it should also not be quietly waved through as REAL when the real reason for the thin sample is a discoverable, escalatable data gap rather than an immutable fact of the world. I would forward-test this, flag the cfo_pat gap to the Data Officer as a priority backfill check, and NOT certify it on this backtest alone.

## Verdict: **FRAGILE**

**Weakest assumption:** The S1.4 quality gate REQUIRES quality_cfo_pat for every name (it is averaged with quality_QMJ before gating). quality_cfo_pat has a genuine coverage CLIFF, not a gradual ramp: median names/date is 1-4 from 2010-2016, then jumps to 226+ exactly at 2017-06-30. Net effect: only 90 of 249 monthly dates clear the harness's own min_names=20 threshold and enter the IC/decile series, and essentially all of them are 2017 onward (era-split below: 2012-15 has ZERO usable dates, 15-18 has 7). This scorecard is therefore honestly a POST-2017 model with ~90 monthly (heavily overlapping, ~7-8 independent-year) observations -- it has NEVER been tested through a 2008 or 2011-style bear market, and 2012-2016 contributes essentially nothing. Hard gates (lag/placebo) pass clean -- no leakage -- but 'REAL' would overstate how much history actually backs the IC_IR of 0.63. Statistics on DSR/PBO overlap (n_ic_dates=90, ~7-8 truly independent annual windows) compound this, but the gate-driven coverage cliff is the primary, root-cause weak assumption.
