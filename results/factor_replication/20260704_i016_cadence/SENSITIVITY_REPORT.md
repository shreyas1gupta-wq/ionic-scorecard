# I-016 N500 LowVol 50 QUARTERLY — Gate-4 Sensitivity Report
**Dr. Sameer Bhat (E-027), Overfit & Sensitivity Analyst, Risk Office. 2026-07-04.**
Strategy under test: `results/factor_replication/20260704_i016_cadence/` — VERDICT.md certified cell
(N=50, 252d inverse-vol lookback, quarterly Mar/Jun/Sep/Dec rebalance): frictionless 17.46% / 1x
16.54% / 2x 15.62%, vol ~12.6%, maxDD -44.2%, turnover 109.6%. Resurrected same-day from K-013 on
Ishaan's corrected per-path frictionless terminal p75 (17.13%, `terminal_cagr_percentiles.csv`).
Engine reused UNCHANGED (`run_i016_cadence.py` imported, not copied) for every perturbation below —
repro-check confirms exact match to the certified headline (fric 17.4595%, net1 16.5390%, net2
15.6236%, maxDD -44.157%, turnover 109.59%) before any cell was varied.

## 1. PARAMETER PERTURBATION GRID (36 cells: N x lookback x weight x rebalance-offset)
N in {40,50,60} x vol-lookback in {189,252,315}d x weight in {inverse-vol, equal} x month-offset
in {0, +1}. Full table: `sens_param_grid.csv`.

| Axis | Range of 2x-cost CAGR | Range of maxDD(2x) |
|---|---|---|
| N=40 | 13.00% – 16.35% | -40.2% to -46.2% |
| N=50 (certified N) | 13.61% – 15.89% | -43.4% to -49.0% |
| N=60 | 13.74% – 15.94% | -45.2% to -50.6% |

**Plateau check:** median cell (2x) = 14.78%, best cell = 16.35% (N=40, lb=252, equal-weight,
offset=0), ratio = **10.6% above median — PASS** (pre-registered plateau rule: best cell must be
≤20% above neighborhood median). The certified cell (N=50/lb=252/invvol/offset=0) itself scores
15.51% at 2x, i.e. it sits IN the plateau, not at its peak — a mild positive sign (the firm isn't
reporting the single luckiest corner of its own grid).

**But the grid hides a structural fault line, not noise:** every single "+1 month" rebalance-offset
cell underperforms its "offset=0" twin, with NO exceptions across all 18 matched pairs:
- Average degradation from shifting the quarterly grid by one month: **-1.0pp CAGR(2x)** and
  **-3.9pp worse maxDD**, consistently, across all N x lookback x weight combinations.
- Two cells (N=60/lb=189/equal/+1 at -50.1%, and N=60/lb=252/equal/+1 at -50.6%) **breach the
  pre-registered -50% maxDD floor** (criterion (d) in the idea file) — the ONLY cells in the whole
  36-cell grid that do. Both are +1-offset cells.

This is not "a parameter is sensitive," it is "the calendar phase of the quarterly grid matters,
and the certified phase is not obviously the best or the worst — it is untested against its own
neighbor in the one dimension (rebalance timing) most likely to reveal a lucky alignment with
March/June/September/December fiscal-year-end effects (dividend record dates, index-rebal flows,
FY-end institutional book-squaring) that a Mar/Jun/Sep/Dec low-vol strategy could be silently
riding." **Flagged, not fatal** — offset=0 (the certified choice) is NOT the worst cell on its axis,
and the degradation is monotonic/graceful rather than a cliff, but it is real and directional.

## 2. SUBSAMPLE STABILITY (on the certified cell, net-2x series)
Full table: `sens_subsample.csv`. Hurdle = 12.74% (D-029 random-N500-50 net mean).

| Cut | Result |
|---|---|
| **Halves** | 2005-15: **+19.77% CAGR (+7.03pp vs hurdle, POS)**. 2016-26: **+11.74% CAGR (-1.00pp vs hurdle, NEG)**. |
| **Per-year** | 10 of 21 calendar years (48%) fall BELOW the 12.74% hurdle: 2008 (-37.8%, GFC), 2011 (-13.6%), 2013, 2015, 2016, 2018 (-0.4%), 2019, 2022, 2024, 2025. 3 years outright negative. |
| **Rate-shock era 2022-2026** | **+12.08% CAGR (-0.66pp vs hurdle, NEGATIVE excess)** — see trap (b) below. |
| Odd vs even quarters | Odd (Q1,Q3) ann. mean-daily 12.22% vs Even (Q2,Q4) 21.55% — asymmetric but both positive; not a red flag on its own, consistent with low-vol's seasonal defensiveness in Q1/Q3 (Budget/monsoon uncertainty windows). |
| High vs low INDIA VIX months (2016+, VIX data start) | High-VIX months ann. 14.82% vs low-VIX 11.49% — the "expected" defensive-factor direction (low-vol strategy does relatively BETTER when fear is high), a supportive sign for the economic story, not a red flag. |

**Worst subsample: the 2016-2026 half, and specifically the 2022-2026 rate-shock sub-era.** The
entire post-2020 excess (+3.51pp per VERDICT.md criterion (c)) is being carried almost entirely by
the 2020-2021 COVID-recovery years; strip those out and the 2016-26 half is UNDER the hurdle, and
2022-2026 alone is also under the hurdle. Criterion (c) as scored (full 2020-2026 window) technically
passes, but this decomposition shows the pass is not evenly distributed across the "recent regime" —
it is front-loaded into two anomalous recovery years. **No outright sign-flip across halves in the
strict sense (2016-26 is still barely CAGR-positive, just hurdle-negative)**, so this does not trip
the automatic Gate-4 FAIL trigger for "edge sign-flips across halves" (that trigger is on the sign of
the RETURN, not the sign of excess-over-hurdle) — but it is the single most important number in this
report and is flagged as the weakest assumption below.

## 3. LOW-VOL-SPECIFIC TRAPS
**(a) Stale-price contamination — CLEAN.** Independently re-derived (not trusting the engine's own
veto) on 20 rebalances sampled evenly across the full 84-rebalance history (`sens_stale_check.json`):
**0 violations** — no selected name in any sampled rebalance had a frozen run inside its trailing
253d vol window or was frozen on the rebalance date itself. Mean 1.75 names vetoed per rebalance by
the stale-mask (out of ~50 selected + vetoed pool), consistent with the 212-symbol/0.9%-of-rows
frozen-price footprint reported in VERDICT.md. The specific low-vol failure mode named in the brief
(inverse-vol overweighting fake-stable frozen names) is verified NOT present in the certified build.

**(b) Interest-rate regime dependence — CONFIRMED, material.** Low-vol is a bond-proxy-like factor;
the 2022-2026 rate-shock era (RBI hiking cycle + since) returns **12.08% CAGR at 2x cost, which is
BELOW the 12.74% hurdle** (see subsample table above) — the sleeve's edge over a naive random basket
effectively disappears in the higher-rate regime that has now persisted for 4+ years and is the
CURRENT regime an investor would be buying into. This is the same regime-artifact caution the firm
already flagged for S-01/S-04 (90%+ win rates in 2024-26 are regime artifacts until proven otherwise)
— here it cuts the other way (the edge UNDERPERFORMS in-regime), but the lesson is the same: do not
extrapolate the 20-year full-sample number into the current rate environment without discount.

**(c) Crowding — unmeasurable but real, noted per instruction.** NSE's own "Nifty500 LowVol50"-style
official indices are large-AUM passive benchmarks; this strategy's inverse-vol/quarterly construction
is close enough in spirit that crowding from index-tracking flows (systematic buying of the same
low-vol names at the same quarter-end dates) is a plausible live-capacity headwind with no way to
measure it from historical price data alone. Flagged for the record, not scored.

## 4. DSR / PBO (purgedcv, quarterly units)
**Units trap avoided:** the strategy trades quarterly (83 realized rebalance-to-rebalance periods
over 20.75 years); DSR/PBO were computed on the QUARTERLY-resampled net-2x return series
(`bars_per_year=4`), NOT on the daily NAV (which would inflate n_obs ~5x on autocorrelated,
overlapping-information daily bars and falsely improve statistical significance).

**Honest family trial count = 47**: factor family (Arjun, D-029, 6 indices trialed) + cadence test
(Devika, I-016, 2 variants: LowVol50-Q + MQ50-semiannual) + dynamic-basket regime-switch test
(3 configs: dynamic + 2 controls, per `20260704_dynamic_basket/run_result.json`) + this sensitivity
grid (Sameer, 36 cells actually computed in the search for neighborhood context). This is NOT "1"
(just the certified cell) — every cell that was computed while searching for/around this result
counts per RESEARCH_SOP honest-trials doctrine.

| Metric | Value | Gate | Result |
|---|---|---|---|
| **DSR** | **0.9995** | >0.95 | **PASS** |
| **PBO** | **19.82%** (CSCV, 16 splits, 12,870 combos, 36 configs) | <25% | **PASS** |

DSR input: cross-cell annualized Sharpe dispersion (var=0.0040, mean=1.167) across the 36-cell grid
used as the `var_sharpe` deflation input. Both gates pass with the full honest trial count — the
sleeve does NOT depend on undercounting trials to look statistically real.

## 5. D-028 LOOKAHEAD AUDIT — see companion `LOOKAHEAD_AUDIT.md` (this same directory)
**Verdict: PASS-WITH-FLAGS.** 0 FAIL, 8 WARN (7 are the automated scanner correctly flagging bare
`.mean()/.std()` calls that ARE trailing-window/rolling on manual inspection — false positives on
review, not leaks; 1 is an expected T5 note that 1,597 of 2,511 union-panel symbols were never N500
members, which is normal for a full-market panel feeding an N500-only strategy). **One-day-lag test:
2.0% collapse ratio (PASS — graceful decay; >50% would indicate leakage).** No FAIL-severity finding.

## VERDICT: PASS-WITH-FLAGS

**Plateau:** PASS (10.6% best-vs-median, well under the 20% rule).
**Worst subsample:** 2016-2026 half / 2022-2026 rate-shock era — both run BELOW the 12.74% hurdle;
the strategy's headline edge is a full-sample average that is not being earned in the current
(post-2020, rate-shock) regime, propped up almost entirely by 2020-2021 recovery-year outliers.
**Stale-price protection:** CONFIRMED CLEAN (0/20 sampled rebalances contaminated).
**DSR/PBO:** DSR 0.9995 (>0.95 PASS), PBO 19.8% (<25% PASS) at the full 47-trial honest count.
**Cost-sensitivity:** fric-to-2x drag is 1.84pp/yr (17.46%→15.62%), well under the "50% of edge"
automatic-FAIL threshold — the edge over the hurdle (+2.88pp at 2x) survives cost stress.

**Single most fragile assumption: that the full-sample 20.75-year edge generalizes into the CURRENT
regime.** The 2022-2026 rate-shock era and the 2016-2026 half both run below the firm's own random-
basket hurdle; the full-period pass is real but is a stale-weighted average dominated by 2005-2015
and by two anomalous 2020-2021 recovery years. This does not meet the bar for an automatic FAIL
(no sign-flip of the RETURN itself, plateau is clean, DSR/PBO pass, no single-spike cell, cost drag
is proportionate) — but it is exactly the kind of regime-dependency this firm has been burned by
before (S-01/S-04 lesson) and should gate SIZE, not existence: paper-trade at modest size with an
explicit rate-regime monitor, not a full-conviction allocation on the strength of the 2005-2015 years.

**Recommendation:** proceed to Nikhil (Red Team) and IC with this flag attached verbatim — this is a
diversifier candidate on real, clean statistical footing (DSR/PBO/plateau/stale-mask all pass), but
its economic case should be argued on the +3.8pp 1x-mean margin and orthogonality (per Devika's
VERDICT.md), not on the headline full-sample CAGR, which overstates what the current regime is
likely to deliver.

---
*Dr. Sameer Bhat (E-027), Overfit & Sensitivity Analyst, Risk Office. Signed 2026-07-04.*

**Files in this run directory (added by this report, engine outputs untouched):**
`sens_param_grid.csv`, `sens_plateau_check.json`, `sens_subsample.csv`, `sens_stale_check.json`,
`sens_dsr_pbo.json`, `sens_repro_check.json`, `sens_lookahead_audit.json`, `LOOKAHEAD_AUDIT.md`,
this file.
