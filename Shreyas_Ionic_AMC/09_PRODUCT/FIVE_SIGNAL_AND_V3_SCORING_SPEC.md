# Five-Signal Holdings Page + v3 Scoring — method spec
**Status:** page LIVE · v3 scoring BUILT, NOT ADOPTED (sits beside v1)
**Date:** 2026-08-07 · **Desk:** DESK-20 · **Rulings:** Principal, 2026-08-06/07
**Commits:** `57c65a2` (page + v2) → `3802d7a` (v3) → `50a4163` (60:40 growth, caps, re-rank)

Internal book. Principal-facing version was delivered in chat as tables.

---

## 1. What changed, and why

| # | Change | Driver | Evidence |
|---|---|---|---|
| 1 | Prose one-liner on the holdings page replaced by 5 colour-coded signals | Principal ask | — |
| 2 | Worded chips → traffic-light dots | Principal ask | — |
| 3 | Band floors: even quartiles 75/50/25 | Principal ruling (tuned 67/45/22 measured better on coherence but is harder to state) | `IMPUTATION_TEST.md` |
| 4 | Legend words: "Top 25% / Upper / Lower / Bottom 25%" | Chosen from 4 sets; relative wording is the only set that survives removing the footnote | `signal_words.png` |
| 5 | Both bottom footnotes removed; coverage facts moved to the top scope tag | Principal ask | — |
| 6 | Cash (FCF-yield) signal added then removed | Principal ruling; measurement retained | best spread of any candidate (5/11/33/10) |
| 7 | Thin-history score inflation fixed | Principal-reported bug | `THIN_COVERAGE_DIAG.md` |
| 8 | 1-year sibling substitution | Principal instruction, then backtested | corr 0.906→0.932, MAE 3.86→2.72 |
| 9 | Listing-price technical for <1y names | Principal instruction, then backtested | corr 0.601→0.701 at 3m, 0.735 at 12m |
| 10 | 50/25/25 redistribution **rejected** | backtest — worse than the bug | bias +3.07 vs +2.95, corr 0.445 vs 0.601 |
| 11 | Withdrawal at ≤3 pillars **removed** | Principal ruling (a large cap can be thin) | — |
| 12 | Sell rule moved to the blended composite | Principal ruling | 88 of 246 v1 Sells were above a blended 40 |
| 13 | PAT-vs-Sales earnings rule **replaced** by a profit bridge | Principal correction | 17 of 29 flagged names were margin-driven |
| 14 | Growth signal = 60% expected EPS + 40% trailing revenue | Principal ruling | — |
| 15 | Composite scores capped to [5, 95] | Principal ruling | binds on 0 names today (range 15.1–77.8) |
| 16 | All five signals re-ranked against the universe | own finding — the quartile legend was false | Value was 32/32/19/13 |

---

## 2. The final model

### 2.1 Seven pillars → five signals

| Signal | Built from | 3Y weight | 1Y weight |
|---|---|---|---|
| Quality | `quality_score` = mean(ROE pctile, ROCE pctile), sector-neutral | 20% | 16% |
| Growth | **60% expected EPS growth + 40% trailing revenue-CAGR pctile** | 20% | 16% |
| Value | `value_score` = 0.25 P/E univ + 0.35 P/E sector·tier + 0.20 P/B + 0.20 FCF yield | 18% | 16% |
| Technical | mean(`stage_3y`, `accumulation_3y`) | 22% | 31% |
| Sector & Flows | mean(`ownership_flow_3y`, `sector_macro_3y`) | 20% | 21% |

Weights are the frozen pillar weights, regrouped. Both columns sum to 100.

### 2.2 The Growth blend — why the EPS leg is mapped first

The EPS leg is a raw percentage the analyst wrote down (12%, 22%). The revenue leg is a percentile
rank of the universe (0–100). Averaging 22 with 74 is arithmetic on two different units and would make
a 22% grower look bottom-quartile. The estimate is therefore mapped onto 0–100 through the model's own
frozen growth-leg thresholds before blending:

| expected EPS growth | ≥25% | 20–25% | 15–20% | 10–15% | 5–10% | <5% |
|---|---|---|---|---|---|---|
| mapped score | 92 | 80 | 65 | 50 | 30 | 12 |

`Growth_raw = 0.60 × mapped_EPS + 0.40 × revenue_pctile`. Either leg alone if the other is absent.

### 2.3 Universe re-ranking — why every signal, not just some

The legend claims quartiles. That is only true if each column is uniformly distributed, and **none of
the five is**, because every one is a blend: Quality is the mean of 2 ranks, Value a weighted mix of 4,
Growth a 60/40, Technical and Sector & Flows the mean of 2 each. A blend of ranks is not itself a rank —
it clusters mid-scale (the mean of two uniforms is triangular).

Measured before the fix: Value **32/32/19/13**, blended Growth **12/37/40/11**. After re-ranking each
signal against the universe's own distribution of that same signal:

| | Top 25% | Upper | Lower | Bottom 25% |
|---|---|---|---|---|
| Quality | 25% | 25% | 24% | 25% |
| Growth | 26% | 23% | 26% | 25% |
| Value | 24% | 25% | 25% | 24% |
| Technical | 25% | 25% | 25% | 25% |
| Sector & Flows | 25% | 26% | 25% | 25% |

### 2.4 Bands and colours

| Band | Floor | Word | Dot |
|---|---|---|---|
| 1 | ≥75 | Top 25% | dark green `#1E9E6A` |
| 2 | ≥50 | Upper | light green `#76C7A6` |
| 3 | ≥25 | Lower | yellow `#F2A93C` |
| 4 | <25 | Bottom 25% | red `#E0402F` |
| — | no data | Not scored | hollow grey ring |

Three of four are exact house colours; the light green is a tint of HOLD (the palette has no mid-green).

**Known limitation, stated because it cannot be designed away:** a dot carries no label, so colour is
the whole message. Light green (~0.52) and yellow (~0.50) have almost the same luminance and red
(~0.24) is darker than both, so a mono print or a red-green deficiency (~8% of men) collapses the
ramp. A graduated dot-size variant that survives both is built (`DOT_SIZE_RAMP`) and off by default.

---

## 3. v3 scoring pipeline

Runs on top of the engine's output; **the engine itself is untouched**.

```
full750_scored.csv  (v1, produced by score_n100_quant.py)
   │
   ├─ 0. REPLICATION CHECK — recompute the engine's own composites from its
   │     weights/tilts and assert max |diff| < 0.05.  Currently 0.0000.
   │     Aborts if it fails: every number downstream would be fiction.
   │
   ├─ 1. GROWTH ARTEFACTS — revenue CAGR that is infinite or >200% is a
   │     base-year artefact (first full year after listing), not growth.
   │     Pillar set to missing.                        6 names (incl. JIOFIN)
   │
   ├─ 2. HISTORY CLASS — from the price file:
   │        ret_24m present            → full    667
   │        ret_12m only               → 1-2y     45
   │        neither                    → <1y      39
   │
   ├─ 3. IMPUTATION, in priority order
   │     a) 1-YEAR SIBLING   stage_3y←stage_1y, accumulation_3y←accumulation_1y,
   │                         growth_3y←growth_1y, ownership_3y←ownership_1y
   │     b) LISTING-PRICE    <1y names: technical = return since listing,
   │                         ranked against the universe over the SAME window
   │                         (longest of 12/9/6/3 months the name supports)
   │     c) NEUTRAL 50       anything still unobservable
   │                                    137 names touched, 38 via listing price
   │
   ├─ 4. GATE + PENALTY — the engine's own balance-sheet/liquidity gate re-applied
   │     from its own flags; penalty/boost recovered exactly as
   │     residual = final − gate(composite)
   │
   ├─ 5. CAP — clamp to [5, 95], with an in-run assertion that the cap moves
   │     ZERO recommendations.  Currently binds on no name (range 15.1–77.8).
   │
   └─ 6. CALL on the BLENDED composite  (0.60 × 3Y + 0.40 × 1Y)
            < 40      Sell                    156
            40 – 50   Hold (Trim if concentrated)   236
            > 50      Hold                    359
```

### Why neutral-fill and not 50/25/25

The skip-and-renormalise bug hands a missing pillar's weight to the survivors — on thin names a mean
**37%** of the composite. Backtest on 515 fully-covered names (true score known), deleting exactly the
pillars thin names really lack:

| scheme | bias | MAE | rank corr |
|---|---|---|---|
| skip (the bug) | +2.95 | 10.08 | 0.601 |
| value 50 / growth 25 / quality 25 | **+3.07** | **11.83** | **0.445** |
| neutral-fill 50 | +1.84 | 6.95 | 0.601 |
| 1y sibling (where available) | +0.05 | 2.72 | 0.932 |
| listing-price technical (<1y) | +1.84 | 6.17 | 0.701 |

The 50/25/25 concentrates freed weight on value, which is uncorrelated with the missing pillars, so it
amplifies noise rather than adding information. Under uncertainty, shrinking to the middle wins.

### The schema-gap case, tested separately

`growth_3y` is also missing on ~106 names for a different reason: banks carry `Financing Profit`
instead of `Sales+`, so no revenue line exists. Applying a thin-history rule to a schema gap needed its
own test — substitution still wins (MAE 4.97→3.38, corr 0.843→0.898; the two growth pillars correlate
0.645). This is what moves UNIONBANK −13.7, KTKBANK −12.8, J&KBANK −11.0, CANBK −10.5.

---

## 4. Earnings quality — profit bridge

The old rule (PAT +50% while Sales <10%) was wrong: operating leverage produces that pattern routinely.
Of the 29 names it flagged, **17 (59%) were margin-driven**, not one-offs.

Replaced with a decomposition of the year-on-year PBT change:

```
volume effect  = (Sales₁ − Sales₀) × OPM₀        revenue genuinely grew
margin effect  =  Sales₁ × (OPM₁ − OPM₀)         LEGITIMATE operating leverage
other income   =  OI₁ − OI₀                      NON-OPERATING — the one to watch
finance/dep    = −(Int₁ − Int₀) − (Dep₁ − Dep₀)
```

Bridge closes to **0.6%** (median residual ₹1.0cr against a ₹169.5cr median PBT change) across 662
names — proof the decomposition is complete rather than approximate.

| Flag | Test | Names |
|---|---|---|
| `oi_driven_growth` | >50% of the PBT increase came from other income | 75 |
| `oi_level_high` | other income >25% of PBT (standing dependence) | 140 |
| `oi_spike` | other income >2× its own 3y median AND >15% of PBT | 81 |
| any | | 192 |

Financials exempt throughout — treasury income **is** their operating business. Largest catches: IDEA
(₹58,048cr of a ₹61,916cr PBT change from other income, 171% of PBT), TMPV, ADANIENT, JSWSTEEL.

---

## 5. Workflow

```
STEP 1   score the universe            05_DATA_OFFICE/scripts/score_n100_quant.py
                                       → results/full750_scored.csv          (v1, frozen engine)

STEP 2   earnings quality              04_RND_LAB/.../earnings_quality_decomp.py
                                       → results/EARNINGS_QUALITY.csv        (must run before v3)

STEP 3   v3 corrections                04_RND_LAB/.../fix_thin_coverage_v3.py
                                       → results/full750_scored_v3.csv
                                       aborts if it cannot replicate the engine

STEP 4   750 research Excel            09_PRODUCT/scripts/build_scores_excel.py
                                       → reports/NIFTY750_SCORECARD_<date>.xlsx

STEP 5   client deck                   09_PRODUCT/pr_template/build_<client>.py HNI_DEEP
STEP 6   QA (all mandatory)            check_geometry.py · check_geometry2.py · tellscan.py
                                       + scripts/pptx_slide_png.py <deck> <slide>  ← visual read
STEP 7   Principal sign-off            before anything ships
```

Re-running the backtests (only needed if a rule changes):
`test_imputation_schemes.py` · `test_listing_price_signal.py` · `test_growth_schema_gap.py` ·
`diag_thin_coverage_bias.py`

---

## 6. Where things live

| File | Role |
|---|---|
| `09_PRODUCT/pr_template/lib/five_signals.py` | **single source of truth** — clubbing, bands, words, colours, re-ranking, universe join |
| `09_PRODUCT/pr_template/modules/book_scored.py` | the holdings page |
| `09_PRODUCT/pr_template/slidekit.py` | `dot` and `chip` table cell types; `oval(line=)` |
| `09_PRODUCT/scripts/pptx_slide_png.py` | slide→PNG, closes the visual-QA gate (no poppler on this box) |
| `09_PRODUCT/scripts/build_scores_excel.py` | the 750 research Excel |
| `04_RND_LAB/STOCK_SCORECARD_750/fix_thin_coverage_v3.py` | v3 corrector |
| `04_RND_LAB/STOCK_SCORECARD_750/earnings_quality_decomp.py` | profit bridge |
| `.../results/*.md` | all evidence notes |

Superseded, kept as decision records only (do **not** run — written against the pre-final API):
`chart_signal_options.py`, `chart_dot_formats.py`.

---

## 7. Open decisions

| # | Item | Consequence |
|---|---|---|
| 1 | **Adopt v3?** | Excel is on v3; the deck still reads v1 (`_SOURCES` in five_signals.py). On the Talaulikar book that is **5 of the 11 printed rows** and **24 of 93 in-universe holdings** — all `growth_3y←growth_1y`. Adopting means pointing `_SOURCES` at the v3 file, or folding v3 into the engine. |
| 2 | Ownership feed caps at **2023-12** | universe-wide; refreshing it is the single largest remaining coverage win. |
| 3 | `score_method.py` still explains **3** buckets | the holdings page shows 5 — the deck currently contradicts itself. |
| 4 | L&T `SELL` beside four non-red dots | pending adjudication (45.5 score, 4.27% weight). |
| 5 | Graduated dot size | off by default; the only variant that survives mono print / colour blindness. |
