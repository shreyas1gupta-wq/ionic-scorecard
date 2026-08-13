# Five-Signal Holdings Page + v3 Scoring — FROZEN SPEC
**Status:** page LIVE · v3 scoring **FROZEN 2026-08-07**, sits beside v1 (engine untouched)
**Date:** 2026-08-07 · **Desk:** DESK-20 · **Rulings:** Principal, 2026-08-06/07
**Freeze audit:** `results/V3_FREEZE_AUDIT.md` — **19 of 19 hard invariants pass**

Internal book. Principal-facing version was delivered in chat as tables.

---

## FROZEN RULES — the scoring ladder

```
Ionic = clamp( base + forward_adjustment , 5 , 95 )
   base               = 0.60 x final_3y + 0.40 x final_1y
   forward_adjustment = growth_leg + conviction_leg, clamped +/-20
                        then: expected growth <10%  -> net adj <= 0
                              analyst Sell          -> net adj <= 0

growth_leg      banded on the ANALYST'S EXPECTED EPS GROWTH ALONE (100% EPS, 0% revenue - as v1)
                <5% -15 | 5-10% -5 | 10-15% 0 | 15-20% +5 | 20-25% +10 | >=25% +15
                REVENUE RESCUE: revenue growth >15% (1y OR 3y, March-to-March) AND expected EPS <10%
                                -> the -15 penalty is floored at -5
                +20 EXCEPTIONAL tier DORMANT (needs a dilution field; would be two-of-three otherwise)

conviction_leg  analyst Sell -6 | analyst rescues a quant Sell +6 | agreement 0

THE CALL
   below 40      Sell
   40 - 50       analyst Sell -> Trim; otherwise Trim only if concentrated (>2.5% weight)
   above 50      HOLD, full stop - an analyst Sell is OVERRULED

GATES (inside the score)
   balance sheet   D/E >2.5 or int-cover <1.5 -> RED, caps at 40
                   D/E >1.5 or int-cover <3   -> AMBER, x0.85
                   FINANCIALS exempt from the WHOLE gate (interest expense is their cost of funds;
                     applying coverage flagged NIACL RED at -399x with zero debt)
                   POWER / REALTY / TELECOM / CONSTRUCTION exempt from the D/E trigger only;
                     coverage still applies to them
   liquidity       below the size-tier turnover bar -> caps at 50 (was 40)

GROWTH DATA      March-to-March full fiscal years, never a TTM window (716 of 751 names;
                 35 keep the engine figure where no full-year pair exists)
```

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

**Removed at freeze** (2026-08-07): `chart_signal_options.py` and `chart_dot_formats.py` were one-off
design-option renders used to choose the band words and the dot format; `fix_thin_coverage_v2.py` was
the interim corrector v3 replaced. All three were written against the pre-final API and would fail if
run. The decisions they informed are recorded above and in `SESSION_JOURNAL.md`.

**Not superseded, despite the name:** `results/full750_scored.csv` is the v1 *engine output* and the
INPUT the v3 corrector reads. It is also the file `lib/five_signals.py` joins the universe from.
Deleting it as a "v1 duplicate" breaks the entire scoring chain.

---

## 6b. KNOWN CHALLENGES at freeze — none blocking, all disclosed

| # | Challenge | Size | Status |
|---|---|---|---|
| C1 | **Double-count.** The growth leg and conviction leg correlate +0.24 — an analyst who says Sell usually also forecasts weak growth (median expected 9.1% vs 13.5% for Holds). **95 names are charged by both.** One opinion, two penalties. | 95 names, up to −20 | Fix specced (suppress −6 when growth leg ≤ −5); NOT applied |
| C2 | **Sell rate 26% vs the frozen ~33% expectation.** The Gate A ceiling, the widened D/E exemption and the EPS-only leg each reduce Sells, and they compound. The frozen note calls a low rate the signature of override leakage. | universe-wide | Watch on the next real book |
| C3 | **The forward adjustment is unvalidated.** The PIT test cut the 1Y decile spread from +5.50% to +0.13% with the growth leg on. It used TRAILING growth as a proxy, so it tests the *mechanism*, not analyst foresight — but the mechanism carries no ranking power on its own. | whole leg | Kept on Principal ruling (v1 consistency); revisit when a timestamped estimate exists |
| C4 | **No expected-REVENUE field**, so a true 60:40 cannot be built. One extra field per research file would unblock it. | blocks the ruling | Data gap |
| C5 | **Ownership feed caps at 2023-12** universe-wide. Largest single coverage win available. | 20.8% of names | Data gap |
| C6 | **`compute_client_scores.py` (the CLIENT pipeline) has NOT been updated** — old gates, no March-to-March, no rescue, no 40/50 ladder. Adopt v3 and the deck will disagree with the universe. | every client book | Must be done before adoption |
| C7 | **LT's score is stale.** `pf_mech_flags` recorded analyst Hold (+6 rescue → 45.5); the current research file says Sell. Recomputed it is 33.5, a clean Sell — the "borderline" was an artefact. | 1 name, 4.27% weight | Re-run the mech layer |
| C8 | **Deck reads v1 sources**, Excel reads v3. On the Talaulikar book that is 5 of 11 printed rows, 24 of 93 holdings. | per book | Resolved by adopting v3 |
| C9 | `score_method.py` explains **3** buckets while the page shows **5**. | 1 slide | Not started |
| C10 | **Rescue edge cases.** SPARC qualifies on a 98.8% 3Y CAGR off a tiny base; ITI qualifies on a 3Y CAGR of +16% despite the latest year being **−39.6%**. The "1y OR 3y" reading is mine, not the Principal's words. | 2 of 3 rescues | Flagged for ruling |
| C11 | **35 names still on the engine's TTM window** — no full-year pair exists in the screener data. | 5% of names | Accepted |
| C12 | **Listing-price technical is untestable** in the PIT harness (`score_asof` needs 260 sessions, so sub-1-year names never enter). It rests on the 515-name recovery test only. | 38 names | Accepted |
| C13 | **Exceptional +20 tier dormant** — requires share dilution <2%, which is not in the dataset. Enabling it on two-of-three fired on 27 names. | — | Blocked on data |

## 7. Open decisions

| # | Item | Consequence |
|---|---|---|
| 1 | **Adopt v3?** | Excel is on v3; the deck still reads v1 (`_SOURCES` in five_signals.py). On the Talaulikar book that is **5 of the 11 printed rows** and **24 of 93 in-universe holdings** — all `growth_3y←growth_1y`. Adopting means pointing `_SOURCES` at the v3 file, or folding v3 into the engine. |
| 2 | Ownership feed caps at **2023-12** | universe-wide; refreshing it is the single largest remaining coverage win. |
| 3 | `score_method.py` still explains **3** buckets | the holdings page shows 5 — the deck currently contradicts itself. |
| 4 | L&T `SELL` beside four non-red dots | pending adjudication (45.5 score, 4.27% weight). |
| 5 | Graduated dot size | off by default; the only variant that survives mono print / colour blindness. |
