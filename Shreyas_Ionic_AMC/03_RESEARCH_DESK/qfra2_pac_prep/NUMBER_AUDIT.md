# QFRA 2.0 Committee Deck — Number Audit (Red Team)
**Reviewer:** Nikhil Bose, Red Team · **Date:** 2026-08-04 · **Target:** `C:\Users\Shreyas.1Gupta\Downloads\Mf_qfra2-20260529T103217Z-3-001\QFRA2\QFRA2_DECK_committee.pptx` (28 slides, built by `mr_x_framework\src\qfra2_deck_v4.py`)

**Method:** Read the build script line-by-line to trace each number's provenance, then verified against the named source CSVs/scripts directly (not just cross-doc agreement — docs can all copy the same wrong number). Independently reproduced the eligibility-count and live-alpha figures from raw data rather than trusting any markdown claim, including my own priors. Extracted the actual `.pptx` text via `python-pptx` for all 9 target slides and confirmed verbatim match to the build script (no post-hoc hand edits) — footer numbers: slide2→"1", slide6→"4", slide9→"6", slide12→"8", slide13→"9", slide15→"11", slide19→"14", slide20→"15", slide27→"21".

A same-day prior reconciliation (`03_RESEARCH_DESK/QFRA2_SKILL_RECONCILIATION_2026-08-04.md`) independently corroborates §1a (eligibility) and §1d (HELD vs RAW) below via a different method (inverting the qfra_score ladder). Cross-checked, not merely cited.

---

## RANKED FINDINGS (worst first)

### 1. [DATA] Slide 20 "P(beat 3-5y) ~56%" — UNSOURCED, and contradicts the model's own spec
**Slide says (verbatim, extracted from the live pptx):** a chip on the "CLIENT-FACING" scorecard for Aditya Birla SL Small Cap Fund: `P(beat 3-5y)` = `~56%`.
**Trace attempt:**
- `qfra2_deck_v4.py:315` — the value is a **literal hardcoded string** in the chip list: `chips = [..., ("P(beat 3-5y)", "~56%", GOLD)]`. No variable, no file read, no computation in the deck script.
- The fund's actual row in `outputs\recommendations\QFRA2_current.csv` (verified by grep): `qfra_score=100, merit_grade=A, sentinel=clear, cat_beatTRI_pct=80, hit_3y_pct=40, down_capture=0.84`. Neither `cat_beatTRI_pct` (80) nor `hit_3y_pct` (40) is ~56. No column in this fund's own row supports "~56%".
- `mr_x_framework\src\final_model.py` (the frozen production engine per `PIPELINE_RUNBOOK.md`/`HANDOFF.md`): grep for `P(beat|calibrat|logistic` returns **zero matches**.
- `models.py` DOES implement `fit_probability()` (a logistic P(beat) model, line 87-102) — but it is imported only by `recommend.py` and `recommend_live.py`, **not** by `final_model.py`. It is not part of the frozen/deployed path.
- `QFRA2_FINAL\01_MODEL\MODEL_SPEC.md` Part D, step 9: *"Calibrated P(beat 3Y/5Y) is **DEFERRED** — the logistic is in-sample-only and not yet OOS-refit, so it is **not emitted** in the live output."* Step 11: *"(Calibrated P(beat) is **NOT yet emitted**... **do not promise it client-facing** until OOS-refit.)"*
**Verdict: UNSOURCED / CONTRADICTED.** The model's own spec explicitly forbids exactly what this slide does. Most likely origin: the SENTINEL top-decile lift figure (56.6%, an aggregate backtest statistic — see finding #6 below) recycled and mislabeled as a per-fund forward probability. This is the single riskiest number in the deck because it is presented with false precision, on the one slide explicitly headed "client-facing."
**What would change it:** either remove the chip, or replace with a metric the engine actually emits for this fund (`cat_beatTRI_pct=80%` or `hit_3y_pct=40%`, correctly labeled and not called a "probability").

### 2. [DATA] Slide 13 "absolute alpha highest here (+2.2%/yr)... +9pp win-rate" (Small Cap) — sign-flips against the deployed book
**Slide says:** "In Small the model's value is CONSISTENCY: +9pp win-rate (3Y), +8pp (5Y)... absolute alpha is highest here (+2.2%/yr)."
**Source of the deck's number:** `QFRA2_HANDOFF.md` §5 table (from `qfra2_vs_random.py`): Small 3Y model = +2.20%, 3Y win% model/random = 73.5/64.4 (+9.1pp), 5Y win% = 76.9/68.5 (+8.4pp). Exact match — **this table is a simulated/RAW cross-sectional "model-pick vs random-pick" backtest repeated across many historical as-of dates**, not the realized experience of a client holding the actual recommended book.
**Contradicting source (the model's own official realized-performance record):** `outputs\recommendations\QFRA2_recommendation_performance.md`, "By category - HELD book" table: **Small Cap | active | 3Y med a = -1.34 | 3Y win = 50.0 | 5Y med a = -0.54 | 5Y win = 50.0 | n=18.** This is the realized forward alpha of the funds actually recommended at the actual 2018-2024 H1/H2 dates, under the actual τ-hysteresis churn rule that governs the deployed product.
**Verdict: CONTRADICTED on the basis that matters to the committee.** The deployed/held Small Cap book's real 3Y and 5Y median alpha is **negative**, and its win rate is **exactly 50.0%** (a coin flip) at both horizons — not "+9pp better than random" and not "the highest absolute alpha." The deck presents the flattering, simulated number as the category's star proof point and never discloses the realized number, even though both live in the model's own output files.
**What would change it:** disclose the HELD-book row next to the RAW row for Small specifically, or drop the claim.

### 3. [DATA] Slide 2 KPI#1/#2 ("+1.65%", "58% vs 40%") and Slide 6 ("+0.48%/yr, 98.8%") — same raw-vs-held conflation, smaller gap but still ~18x
**Source:** `QFRA2_HANDOFF.md` §5, "ACTIVE pooled (retained 4)" row: 3Y model=+0.53, random=-1.12, edge=**+1.65**; win% M/R 3Y=**58.1/39.5**. Slide 6's "+0.48%/yr (98.8%)" = the pooled-all-8 version of the same RAW/simulated construct, confirmed against `outputs\backtest\QFRA2_evidence.csv` row 2 ("Selection skill... +0.48%/yr; 95% CI [+0.06,+1.05]; P(skill>0)=98.8%... DEPLOYED (core edge)").
**Reality check:** `QFRA2_recommendation_performance.md` "Overall (active categories, pooled)" — **HELD (deployed, tau-hysteresis): 3Y med a = +0.09%, 3Y win = 51.0%.** The number a client actually experienced is ~18x smaller than +1.65%, and the win-rate "edge" (58 vs 40, an 18pt gap) shrinks to barely above a coin flip.
**Verdict: SUPPORTED (traces exactly to the cited files) but RIGHT-NUMBER-WRONG-BASIS.** A committee member reading these as the flagship KPIs would reasonably assume they describe what the product delivers; they describe an idealized, unconstrained, no-churn-discipline simulation instead. This exact gap is already flagged firm-wide as an open action item in `03_RESEARCH_DESK/QFRA2_SKILL_RECONCILIATION_2026-08-04.md` §5 action #6 ("Put HELD-book alpha next to the +0.48% headline in every QFRA-2 deliverable... the PAC deck and QFRA2 committee deck both currently quote the raw figure alone") — confirmed still uncorrected in this deck as of today.
**What would change it:** add the HELD-book row (+0.09%/yr, 51.0% win, 3Y) as the honest companion number, or relabel the KPI tiles "selection-skill backtest (unconstrained)" instead of implying realized experience.

### 4. [DATA] Slide 2/15 "~2.6 / yr active-book turnover" — contradicted by the deck's own supporting data
**Slide says:** KPI tile "~2.6 / yr, active-book turnover (tax-aware)" (Slide 2) and chart caption "~2.6 changes/yr on the active book" (Slide 15).
**Trace:** both numbers originate from `qfra2_charts_ceo.py` line 105's caption string. But the SAME script, 8 lines earlier (line 97), defines the bar-chart's own data: `cats = ["Large & Mid","Multi","Large","Flexi","Mid","Small"]; vals = [7,6,5,5,5,3]` — labeled "changed fund-slots (8 years)". Sum = 7+6+5+5+5+3 = **31** changes over 8 years = **31/8 = 3.875 ≈ 3.9/yr** — not 2.6.
**Cross-checked against every reconciled doc, all independently agreeing on ~3-4/yr:** `MODEL_CARD.md` ("~3-4 fund changes/yr"), `QFRA2_FRAMEWORK.md` §7 ("~3-4 book changes/yr (8-yr realised history: **3.9/yr** active book)"), `BRAND.md` ("~3-4 fund changes/yr; 8-yr realised **~3.9/yr**"), `QFRA2_HANDOFF.md` §3 ("Deployed churn ≈ **3-4/yr**"), `QFRA2_FINAL\README.md` ("churn **~3-4 changes/yr**").
**Additional internal crack:** the deck's own embedded transition-history table (`qfra2_deck_v4.py` `HIST` dict, rendered on slides 22-24, caption "each row = a change") counts **33** total transition rows across the same 6 categories (5+7+6+5+7+3) = 33/8 = **4.1/yr** — itself 2 off from the chart's 31, on Multi (7 vs 6) and Mid (6 vs 5). Three internal sources (chart data, HIST table, external docs) cluster at 3.9-4.1/yr; none support 2.6.
**Verdict: CONTRADICTED**, by the deck's own source script's own chart data, on the exact same slide. The true, multiply-corroborated figure is **~3.9-4.1/yr**, not 2.6.
**What would change it:** recompute the caption from the chart's own bar values (31/8) or cite the reconciled "~3-4/yr" figure everyone else uses.

### 5. [DATA] Slide 9 (pipeline) "ELIGIBILITY... (~40-60 funds)" — independently re-verified as wrong
**Trace:** replicated `final_model.py`'s exact eligibility logic myself against raw data (not just cited the handoff's claim): line 95 drops Regular-plan columns (`'reg(g)' in fl or '-reg(' in fl or '(reg)' in fl`), line 98 requires `len(fr) >= C.MIN_HISTORY_D` (756 trading days = 3y). Ran this against `data\verified_navs_{cat}.csv` for all 8 categories:

| cat | total NAV cols | Direct-plan cols | eligible (>=3y) |
|---|---|---|---|
| large | 26 | 8 | **8** |
| largemid | 22 | 5 | **5** |
| mid | 26 | 9 | **8** |
| flexi | 35 | 6 | **6** |
| multi | 21 | 5 | **5** |
| small | 25 | 7 | **6** |
| focused | 30 | 30 | **30** |
| value | 31 | 31 | **31** |
| **TOTAL** | | | **99** |

(My first pass used a naive "regular"-substring filter and wrongly got 205 — the data uses "-Reg(" not "regular"; re-verified against actual column names before trusting the result. Final 99 total matches the independent count in `QFRA2_SKILL_RECONCILIATION_2026-08-04.md` §1a exactly, via a different method — inverting the qfra_score ladder.)

**Verdict: CONTRADICTED.** True universe = 99 funds total; the six DEPLOYED categories average **~6.3 eligible funds each** (5-8), not 40-60. Read per-category (as the pipeline flowchart, captioned "per category, per as-of date" in `HANDOFF.md` §3, naturally invites), "~40-60" overstates the deployed pool by roughly 6-8x. A direct consequence not stated anywhere in the deck: "top-5 shortlist" is the **entire** eligible field for largemid and multi (5 of 5 funds), i.e. there is no shortlisting happening there at all.
**What would change it:** state the real per-category counts (8/5/8/6/5/6) or the true total (99), and disclose that shortlist-to-final-2 is a near-no-op in 4 of 6 deployed categories.

### 6. [DATA] Slide 2 KPI#4 "+0.9%/yr live realized alpha since Jan-2025" — supported number, undisclosed scope creep
**Verification:** computed directly from `outputs\recommendations\QFRA2_realized.csv` (rank<=2 rows only = actual final-2 picks, Jan-2025 to 2026-05-27): mean of the 14 non-NaN `alpha_ann_pct` values across **all 8 tracked categories** = **0.8714% ≈ 0.9%** — exact match.
**But:** this mean includes **Focused** (+0.8%, +3.6%), a category **explicitly excluded** from the 6-category deployment this very deck asks the committee to approve (Slide 27: "Out of scope for now: Focused and Value/Contra"). Restricted to the actual 6 in-scope categories (Large, L&M, Mid, Flexi, Multi, Small — 12 data points), **mean = +0.65%/yr, median = +0.70%/yr** — still positive, but ~25-35% lower than the headline, and the headline's scope doesn't match the ask's scope.
**Verdict: SUPPORTED-BUT-SCOPE-MISMATCH.** Good news: the deck correctly avoided MODEL_CARD.md's separately-confirmed-wrong "+2.63%/yr" figure (that number is the pre-freeze/stale one; `mr_x_framework\MODEL_CARD.md`'s own newer copy explicitly retracts it: *"Supersedes the earlier +2.63%/yr, measured on pre-freeze picks; QFRA2_realized.csv is the current source"*) — the deck used the right file, just the wrong category scope.
**What would change it:** recompute over the 6 in-scope categories only (+0.65%/yr mean, +0.70% median), or explicitly caption "all 8 tracked categories incl. Focused."

---

## SAFE — verified, no material issue found

| # | Claim (slide) | Source file | Verdict |
|---|---|---|---|
| 7 | Slide 12: "+2.86 (Large & Mid), +1.90 (Flexi)... +1.65%(3Y)/+1.55%(5Y) pooled" | `QFRA2_HANDOFF.md` §5 table (exact match) | **SUPPORTED.** Correctly attributes +2.86 to Large & Mid — contrast `MODEL_CARD.md`'s own text, which wrongly attributes +2.86 to Small ("strongest in Small (+2.86%/yr alpha, 76% hit)" — Small's real 3Y edge is +0.17). The deck did NOT inherit MODEL_CARD's transposition error. Same raw-vs-held caveat as finding #3 applies to the *pooled* figures here too, but the category attribution itself is right. |
| 8 | Slide 6: "SENTINEL lifts... 48.5% -> 56.6%" | `outputs\backtest\QFRA2_evidence.csv` row 3 (named source of record): "48.5% (picks as-is)" -> "56.6% (loser_score=0, clean)" | **SUPPORTED**, independently confirmed against the CSV, not just cross-doc agreement. Minor side-note: `MODEL_CARD.md` separately (and wrongly) states the base as "36.6%" for the same lift — an error in MODEL_CARD that did **not** propagate into the deck. |
| 9 | Slide 19: mid-momentum "+9%/yr, 87% of 3Y, 100% of 5Y windows"; "-2.55 vs -2.61" | `QFRA2_HANDOFF.md` §4 and §5 table (exact match both figures) | **SUPPORTED.** Caveats (backfilled pre-2022 index, ~-72% max-DD, TER/tracking-error) are already honestly disclosed on the same slide. |
| 10 | Slide 20: "Live:... realized +7.3%/yr alpha since" (Aditya Birla SL Small Cap) | `QFRA2_realized.csv`, exact fund row: alpha_ann_pct=7.3 | **SUPPORTED**, exact fund-level match. |
| 11 | Slide 27: "6 equity categories in scope" | `QFRA2_HANDOFF.md` §0 deployment scope (exact match) | **SUPPORTED.** |

---

## Note on `merit_grade` vs CALIBRE (context, not a deck numeric claim)
`QFRA2_current.csv`'s actual column is still `merit_grade`, and `BRAND.md` itself flags this: *"Propagation to the engine output label (merit_grade->calibre_grade)... is a pending rename cascade."* The deck correctly uses "CALIBRE" throughout (no leakage of the old name), but this is worth knowing if anyone pulls a fresh CSV column name into a future build.
