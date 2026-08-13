# QFRA-2 vs "Just Buy the 3-Year Topper" — PAC Benchmark

**Author:** Arjun Rao (Head of Quant) · **Date:** 2026-08-04 · **Status:** New analysis, first pass
**Question answered:** "Why not just buy last 3 years' best performers?" (expected PAC question, no answer previously on file)

## Result headline [DATA]

Pooled across the 6 active (non-index-core) categories, on the exact same panel and pooling
convention as the published QFRA-2-vs-Random table:

| Strategy | 3Y median alpha | 5Y median alpha | 3Y win% | 5Y win% | Whole-book churn/yr (raw, no hysteresis) |
|---|---|---|---|---|---|
| **QFRA-2 final-2** (`top2()`) | **+0.48%** | +0.58% | **56.4%** | 57.0% | 11.1 |
| 3Y-alpha Top-2 (naive) | +0.37% | **+0.90%** | 53.4% | **57.4%** | 7.8 |
| 3Y-alpha Top-3 (naive) | +0.31% | +0.27% | 53.2% | 53.4% | 10.8 |
| Random (all eligible, blind pick) | -0.76% | -0.69% | 42.8% | 43.1% | n/a |

QFRA-2 wins 6 of 8 pooled cells outright. The naive Top-2 topper edges QFRA-2 on the two 5Y cells,
by a thin margin (+0.32pp median alpha, +0.4pp win-rate) — see "does it win anywhere" below for the
full unshaded scan. Top-3 loses to QFRA-2 on every pooled cell. **Both naive variants clear Random by
a wide margin — the topper is not noise, it is a real but weaker signal than QFRA-2's blend.**

## Data lineage [DATA]

- **Panel:** `C:\Users\Shreyas.1Gupta\Downloads\Mf_qfra2-20260529T103217Z-3-001\Mf_qfra2\mr_x_framework\outputs\backtest\_strategy_augmented.csv`
  — 2,792 rows x 35 cols, 180 distinct funds, 8 categories, 22 formation dates (2014-01-31 to
  2024-07-31, semi-annual grid, mean gap 182.6 days = 2.000 periods/yr empirically — confirms the
  panel is a Jan/Jul semi-annual validation grid, not the monthly grid config.py's comments describe;
  config.py's DECISION_MONTHS comment is stale relative to what's actually on disk. File not modified.
- **Reference harness (read, not modified):** `...\mr_x_framework\src\qfra2_vs_random.py`
- **New script (written, read-only w.r.t. all existing files):**
  `C:\Users\Shreyas.1Gupta\Downloads\Mf_qfra2-20260529T103217Z-3-001\Mf_qfra2\mr_x_framework\src\qfra2_3y_topper.py`
- **New output (audit trail, does not overwrite anything):**
  `...\mr_x_framework\outputs\backtest\_3y_topper_benchmark.csv`
- `config.py` and `final_model.py` were **not touched** (read-only per instructions).
- Independent cross-checks run (both pre-existing, unmodified repo scripts): `qfra2_vs_random.py`
  (published table) and `capture_test.py` (has an existing `m_3Yalpha` using the same `alpha_ann`
  column, TOPN=2, different aggregation — see Self-Check below).

## Column choice: what is "trailing 3-year alpha" here? [DATA] + [INFERENCE]

The panel has **no column literally named "alpha"** with an obvious single meaning. Inspected all 35
columns (`fund, date, alpha_ann, alpha_t, r2, appraisal, info_ratio, excess_ann, hit_3y, batting,
down_capture, up_capture, sortino, calmar, cagr_3y, max_dd, alpha_ac1, alpha_stab, mom_12_1, n_obs,
b_smb, b_mom, b_qual, b_lvol, fwd_3Y, beat_3Y, fwd_5Y, beat_5Y, category, ens_rank, fwd_1Y, beat_1Y,
dcap6, ucap6, capratio6`). Two real candidates, both computed on the identical trailing 756-trading-day
(~3Y) window as of the formation date (`features.py::compute_features_at`, `window=C.ALPHA_WINDOW_D=756`):

- **`alpha_ann` — PRIMARY.** Jensen alpha from a 6-factor (MKT/SMB/HML/MOM/QUAL/LVOL) OLS regression
  over the trailing 756 days. [INFERENCE] Chosen as primary because it is the standard finance
  definition of "alpha" (risk/factor-adjusted, not raw excess return), and because the repo's own
  `capture_test.py` already labels this exact column **"Best 3Y alpha"** — i.e. this is the established
  in-house meaning of the phrase, not my own invention.
- **`excess_ann` — CROSS-CHECK.** Raw arithmetic mean (fund - benchmark) return over the same trailing
  756-day window, annualized — "alpha" with no factor-risk adjustment. Reported throughout as a
  robustness check, never as the primary claim.
- **`cagr_3y` — explicitly NOT used.** This is the fund's own raw trailing CAGR with nothing subtracted
  — "buy the raw-return topper," a different strategy from "buy the alpha topper." `backtest.py` already
  runs a raw-CAGR baseline internally (its `past` basket) for a different purpose; not reused here
  because the task specifically named "alpha," not "return."

**Degenerate flag [DATA]:** the two alpha definitions do not always agree in *sign* for the same
category/strategy — e.g. Multi Cap Top-2 3Y median is -1.06% under `alpha_ann` but +0.03% under
`excess_ann`; Flexi Cap Top-2 3Y median is +0.54% (alpha_ann) vs -0.82% (excess_ann). The naive
topper's result is **not robust to which reasonable "alpha" column you pick** in several categories.
Small Cap is the one category where both definitions agree directionally and materially (see below) —
that is the one place I'd call the topper's edge real rather than a definitional artifact.

## Guards / PIT check [DATA]

The firm's `04_RND_LAB/lib/guards.py` landmine guards target options/HF-bar/F&O-bhavcopy asset
classes and do not apply to this MF-NAV cross-sectional panel. Read the actual construction code
instead: `forward_outcome()` (`features.py:150-163`) computes forward returns strictly as
`fr.loc[t:end].iloc[1:]` — **excludes day t, strictly future** — and `compute_features_at()`
(`features.py:92-146`) truncates all inputs at `.loc[:t]` before computing `alpha_ann`/`excess_ann` —
no forward information in the ranking signal. `beat_3Y == (fwd_3Y > 0)` verified at 100% agreement
on non-null rows (2,792/2,792 checked). No leakage found. **PASS.**

## Full tables (per category + ACTIVE pooled) [DATA]

Active categories (pooling definition copied exactly from `qfra2_vs_random.py`): Large & Mid Cap,
Flexi Cap, Multi Cap, Small Cap, Focused, Value/Contra. Large Cap and Mid Cap are index-core by
design (model doesn't try to out-pick there) and are shown but excluded from ACTIVE pooling, exactly
as the reference harness does.

### PRIMARY — `alpha_ann` topper, Top-2

| Category | 3Y Top-2 | 3Y QFRA-2 | 3Y Rand | 5Y Top-2 | 5Y QFRA-2 | 5Y Rand | win3 T/Q/R | win5 T/Q/R | N groups |
|---|---|---|---|---|---|---|---|---|---|
| Large Cap (index-core) | -1.34 | -1.09 | -1.51 | -0.17 | -0.65 | -1.51 | 44.1/41.2/27.1 | 46.2/42.3/22.6 | 22 |
| Large & Mid Cap | 0.56 | 0.57 | -2.29 | 1.38 | 0.22 | -1.86 | 58.8/61.8/25.7 | 65.4/50.0/23.3 | 22 |
| Mid Cap (index-core) | -4.37 | -2.55 | -2.61 | -3.52 | -2.55 | -2.12 | 11.8/26.5/28.3 | 7.7/11.5/20.2 | 22 |
| Flexi Cap | 0.54 | 0.44 | -1.46 | 0.21 | 0.21 | -1.07 | 50.0/55.9/35.2 | 53.8/53.8/37.9 | 22 |
| Multi Cap | -1.06 | -0.90 | -0.80 | -1.30 | -0.06 | -0.80 | 29.4/41.2/38.7 | 38.5/50.0/38.5 | 22 |
| Small Cap | **2.45** | 2.20 | 2.03 | **3.44** | 2.04 | 2.32 | 73.5/73.5/64.4 | **76.9**/76.9/68.5 | 22 |
| Focused | 0.48 | 0.19 | -0.01 | 0.12 | 0.51 | -0.38 | **58.3**/54.2/50.0 | 50.0/56.2/43.3 | 17 |
| Value/Contra | -0.06 | -0.03 | 0.12 | 0.98 | 0.45 | 0.91 | 50.0/47.4/51.9 | 56.2/53.3/58.3 | 17 |
| **ACTIVE (pooled)** | **0.37** | **0.48** | **-0.76** | **0.90** | **0.58** | **-0.69** | **53.4/56.4/42.8** | **57.4/57.0/43.1** | N=178 |

Edge (Top-2 - QFRA-2): 3Y = -0.11pp, 5Y = **+0.32pp**.

### PRIMARY — `alpha_ann` topper, Top-3

| Category | 3Y Top-3 | 3Y QFRA-2 | 5Y Top-3 | 5Y QFRA-2 | win3 T/Q | win5 T/Q | N groups |
|---|---|---|---|---|---|---|---|
| Large Cap (idx-core) | -1.36 | -1.09 | -0.49 | -0.65 | 39.2/41.2 | 38.5/42.3 | 22 |
| Large & Mid Cap | -0.75 | 0.57 | -0.41 | 0.22 | 47.1/61.8 | 46.2/50.0 | 22 |
| Mid Cap (idx-core) | -3.12 | -2.55 | -2.44 | -2.55 | 17.6/26.5 | 7.7/11.5 | 22 |
| Flexi Cap | 0.65 | 0.44 | 0.05 | 0.21 | 51.0/55.9 | 51.3/53.8 | 22 |
| Multi Cap | -0.70 | -0.90 | -1.28 | -0.06 | 39.2/41.2 | 41.0/50.0 | 22 |
| Small Cap | **2.69** | 2.20 | **4.28** | 2.04 | **74.5**/73.5 | 76.9/76.9 | 22 |
| Focused | 0.28 | 0.19 | -0.17 | 0.51 | 55.6/54.2 | 45.8/56.2 | 17 |
| Value/Contra | 0.59 | -0.03 | 0.98 | 0.45 | 51.7/47.4 | 58.3/53.3 | 17 |
| **ACTIVE (pooled)** | **0.31** | **0.48** | **0.27** | **0.58** | **53.2/56.4** | **53.4/57.0** | N=269 |

Edge (Top-3 - QFRA-2): 3Y = -0.17pp, 5Y = -0.31pp. **Top-3 loses to QFRA-2 on every pooled metric.**

### CROSS-CHECK — `excess_ann` topper (Top-2 / Top-3), ACTIVE pooled only

| Strategy | 3Y median | 5Y median | win3 | win5 | N |
|---|---|---|---|---|---|
| Top-2 (excess_ann) | 0.01 | 0.38 | 50.0 | 52.9 | 182 |
| Top-3 (excess_ann) | -0.32 | 0.09 | 46.9 | 51.0 | 273 |
| QFRA-2 (unchanged) | 0.48 | 0.58 | 56.4 | 57.0 | — |

Under the un-adjusted excess-return definition, the naive topper **loses to QFRA-2 on every single
pooled cell**, including the two 5Y cells where the risk-adjusted (`alpha_ann`) version had eked out a
thin win. This is the definitional fragility flagged above.

## Turnover [DATA]

Empirical periods/year = 2.000 (mean 182.6-day gap between formations — confirms semi-annual, not
monthly, cadence). Whole-book = summed switches/yr across the 6 active categories (the scope
comparable to the repo's own deployed-vs-raw churn figures).

| Book (6 active cats, summed) | Switches/yr |
|---|---|
| QFRA-2 **deployed** (tau-hysteresis) — cited figure, `qfra2_history_perf.py`, 2018-2024 window | **3.9** |
| QFRA-2 **RAW** `top2()`, no hysteresis — cited figure, same script, 2018-2024 window | 9.8 |
| QFRA-2 RAW `top2()`, no hysteresis — **this script, full 2014-2024 panel** | 11.1 |
| 3Y-alpha Top-2 (naive, no stickiness rule) — this script | **7.8** |
| 3Y-alpha Top-3 (naive, no stickiness rule) — this script | **10.8** |

**Finding, stated plainly because it cuts against the pre-registered expectation in the task brief:**
the naive topper does **not** churn dramatically harder than QFRA-2's own unconstrained ranking — Top-2
(7.8/yr) actually churns *less* than QFRA-2's raw ranking (11.1/yr), and Top-3 (10.8/yr) is essentially
tied with it. QFRA-2's real-world low churn (3.9/yr) comes entirely from the deployed tau-hysteresis
discipline, not from the underlying signal being inherently more stable than trailing alpha. **A
client mechanically chasing the naive topper with no stickiness rule would churn roughly 2x the
deployed QFRA-2 book** (7.8-10.8 vs 3.9) — that comparison (naive-no-rule vs QFRA-2-with-rule) is the
fair "why not just chase the topper" answer; comparing naive-no-rule vs QFRA-2-raw-no-rule shows the
churn gap is much smaller than intuition suggests. Full per-category breakdown is in the script output
and the audit CSV.

## Explicit win scan — does the topper win anywhere? [DATA]

Per instructions, reported unshaded. 28 of 72 checked cells (8 categories x 2 horizons x 2 metrics x
2 basket sizes) show the naive topper numerically ahead of QFRA-2 somewhere. Concentration matters:
- **2 of the 28** are in the ACTIVE POOLED headline (Top-2 only, 5Y horizon only: median alpha +0.90 vs
  +0.58, win-rate 57.4 vs 57.0) — both thin margins, both vanish under the excess_ann cross-check.
- **Most of the rest are single-category, small-N cells** (Focused/Value: 17 formation dates; Multi
  Cap: 6-9 funds per formation) — below the firm's usual ≥30-observation bar for treating a
  median/win-rate as decisive. I would not certify any of these individually.
- **The one exception I'd call real:** Small Cap. Top-2 and Top-3 both beat QFRA-2 on 3Y median
  (+2.45%/+2.69% vs +2.20%), 5Y median (+3.44%/+4.28% vs +2.04%), and it is directionally consistent
  under the `excess_ann` cross-check too (+2.53%/+4.25%). Win-rates are closer (roughly tied at 3Y,
  QFRA-2 slightly ahead or tied at 5Y). This is the one place the naive rule adds real, robust
  magnitude — plausibly because Small Cap manager alpha has more momentum/persistence than the other
  categories, or because QFRA-2's SENTINEL/capture-ratio machinery is calibrated for the other
  categories and does less for Small Cap specifically. Worth a follow-up, not a reason to change the
  frozen model.

## Self-check (correctness verification, not a result) [DATA]

This script's own `top2()`-vs-random ACTIVE-pooled reproduction was diffed against a same-day run of
the unmodified `qfra2_vs_random.py`:

```
Published : 3Y model=0.48 rand=-0.76 | 5Y model=0.58 rand=-0.69 | win3 M/R=56.4/42.8 | win5 M/R=57.0/43.1
This script: 3Y model=0.48 rand=-0.76 | 5Y model=0.58 rand=-0.69 | win3 M/R=56.4/42.8 | win5 M/R=57.0/43.1
```

Exact match. Separately, the primary Top-2 `alpha_ann` per-category medians/win-rates were cross-checked
against the pre-existing (unmodified) `capture_test.py`'s independent `m_3Yalpha` computation (same
column, TOPN=2, different aggregation method, all 8 categories) — matched to within display rounding
on every one of the 16 category x horizon cells checked. Two independently-written implementations
agreeing is the best correctness evidence available here; no bug found.

## Verdict

**REAL, but narrower than the PAC question implies.** The naive "buy the 3-year alpha topper" is not
a fake or noise-driven result — it clears the random-pick baseline by a wide, consistent margin in
every cut. But it is **not a threat to the QFRA-2 pitch**: pooled across the active categories, QFRA-2
beats the Top-2 topper on 6 of 8 measured cells and the Top-3 topper on 8 of 8, and the topper's one
genuine edge (Small Cap magnitude) is a single-category exception, not a pooled result. The topper's
apparent 5Y pooled edge (Top-2 only) is thin, reverses under the `excess_ann` cross-check, and would
require a ~2x higher churn rate than QFRA-2's deployed book to realize even mechanically (no stickiness
rule was applied to the topper here — with one, its net-of-tax edge would erode further).

**Single weakest assumption [OPINION]:** that `alpha_ann` (regression alpha) rather than `excess_ann`
(raw excess) is the "right" reading of "trailing 3-year alpha" the PAC will have in mind. A committee
member thinking in plain "did the fund beat its benchmark" terms (excess_ann) would see QFRA-2 win by
more, not less — so this assumption, if wrong, does not weaken the pitch. The second-weakest
assumption is the fund-name-as-stable-identifier convention used for turnover matching across
formation dates ([INFERENCE], not verified against a rename table — no rename events are known within
this panel's 2014-2024 span, but this was not independently checked against `SCHEME_RENAMES`).

## Files

- Script (new, read-only w.r.t. everything else): `C:\Users\Shreyas.1Gupta\Downloads\Mf_qfra2-20260529T103217Z-3-001\Mf_qfra2\mr_x_framework\src\qfra2_3y_topper.py`
- Audit CSV (new): `C:\Users\Shreyas.1Gupta\Downloads\Mf_qfra2-20260529T103217Z-3-001\Mf_qfra2\mr_x_framework\outputs\backtest\_3y_topper_benchmark.csv`
- Panel read (unmodified): `C:\Users\Shreyas.1Gupta\Downloads\Mf_qfra2-20260529T103217Z-3-001\Mf_qfra2\mr_x_framework\outputs\backtest\_strategy_augmented.csv`
- Columns used: `alpha_ann` (primary "3Y alpha"), `excess_ann` (cross-check), `fwd_3Y`/`fwd_5Y`/`beat_3Y`/`beat_5Y` (forward outcomes), `category`/`date`/`fund` (grouping/identity), plus every column `top2()` itself needs (`info_ratio`, `down_capture`, `calmar`, `mom_12_1`, `appraisal`, `b_qual`, `alpha_stab`, `capratio6`, `r2`).
