# EXTRACT_SCORECARD750 — what STOCK_SCORECARD_750 offers ALPHA_RANKER (read-only cross-reference)

Source read (legacy/parallel, not modified): `Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/MASTER_PLAN.md` (+Addendum),
`IMPLEMENTATION_PLAN.md`, `results/STOCK_SCORECARD_750_CHEAPTEST_20260717/{cheaptest_scorecard.py,metrics.json,config.json}`.
Cross-ref: `ALPHA_RANKER/rnd/FINAL_MODEL.md`, `FRAMEWORK_CATALOG.md`, `wave4/COVERAGE_MAP.md`+`coverage_map.json`,
`wave4/WAVE4_FINDINGS.md`, `wave4/SECTOR_CONTEXT.md`, `lib/builders_w2_dcf.py`, `lib/builders_oneil.py`,
`CONSOLIDATION.md`. No STOCK_SCORECARD_750 row found in `04_RND_LAB/IDEA_PIPELINE.md` yet (not logged there as of this pass).

## 1. What it is / duplicate-or-distinct

STOCK_SCORECARD_750 is a **Principal-commissioned, separate-scope project**: a transparent 0-100
percentile-rank composite scorer across 8 pillars (Quality, Growth, Value, DCF, Stage/Technical,
Sector&Macro, Ownership/Flow, Accumulation) + 2 multiplicative overlay gates (Balance-Sheet Safety,
Liquidity) + a 3-bucket valuation-regime weight tilt, explicitly calibrated to a **3-year holding
view** (investment-line, D-032), Phase 1 of a 3-phase plan (Phase 2/3 = qualitative overlay + blend,
not built here). It reuses ALPHA_RANKER's `data/` (universe, fundamentals, prices, sector map) **as
data only, per explicit instruction that ALPHA_RANKER is a separate project** — not a methodology
fork.

**Verdict: DISTINCT PROJECT, but with heavy METHODOLOGY OVERLAP in several pillars** — several of its
building blocks (DCF, sector-neutral ranking, accruals/quality, OBV/flow, stage analysis, sector
rotation-as-score-input, FII/DII flow) are things ALPHA_RANKER has already built, tested, and in a few
cases explicitly **killed**. It is not a duplicate *task* (different output — a static per-stock
scorecard for research/analyst triage vs. ALPHA_RANKER's -100..+100 forward-return-predictive ranker)
but it is re-deriving several already-answered questions from scratch, unaware of the answers.

## 2. Extractable ideas — genuinely NEW vs. ALPHA_RANKER's coverage

| # | Idea | Why it's new | Testable on our data? |
|---|---|---|---|
| 1 | Cyclicality-aware **variable lookback window** for Quality (7-10yr through-cycle avg for Cyclical-tagged sectors — metals/cement/capital goods — vs 3-5yr for Defensive/Sensitive) | ALPHA_RANKER's QMJ/quality legs use one fixed window firm-wide; no sector-cyclicality-conditioned lookback exists in coverage_map or FRAMEWORK_CATALOG | Y — same PIT fundamentals panel + a sector_cyclicality_tag; test as an IC/mono delta of cyclicality-aware vs fixed-window ROE/ROCE quality rank |
| 2 | **Regime-conditional additive WEIGHT-TILT across pillars** keyed to a slow (monthly) 3-bucket stable-valuation regime (Cheap/Neutral/Rich, NIFTY PE/PB percentile) — tilts pillar *weights*, not blended scores and not exposure sizing | Distinct mechanism from both things ALPHA_RANKER tried: (a) return-blend regime overlay (REJECTED, dilutes decile spread) and (b) exposure-scalar sizing (ADOPTED, breadth+VIX). A weight-tilt-on-inputs was not tested | Y, with caution — same family as two things already burned; test via the SECTOR_CONTEXT.md-style incremental-IC + PBO protocol before trusting |
| 3 | **Discrete multiplicative distress GATE** (RED caps score ≤40 hard ceiling; AMBER ×0.85) applied post-composite, vs. folding D/E-style factors into the continuous rank-average | ALPHA_RANKER's construction is pure rank-average (min_legs=5-of-7 is its only discrete gate, on leg *presence* not *distress*); no tail-loss-focused override gate exists | Y — apply the gate to the frozen 7-leg composite's tail names and measure whether it improves max-DD/left-tail without hurting IC (an orthogonal test from "is D/E a factor") |
| 4 | **Coverage-aware pillar re-weighting** — composite re-weights across only the pillars/metrics a stock actually has data for (never zero-fills, never requires full presence) | More granular than ALPHA_RANKER's binary min_legs=5-of-7 threshold (which drops a name entirely below 5 legs rather than re-weighting) | Y — an engineering pattern portable to ALPHA_RANKER's own leg-presence handling, cheap to test as an alternative to min_legs |
| 5 | **Dual percentile output** (quality_sector_percentile scored + quality_universe_percentile shown for context only) to expose sector-ROE bias visibly rather than silently | An output-schema/transparency idea, not a scoring idea; ALPHA_RANKER's sector-neutral cards don't surface the non-neutral number alongside | Y trivially — no new modeling, just an extra output column |
| 6 | **3yr-vs-5yr CAGR divergence QA flag** on Growth (5yr CAGR computed only as a sanity check for base-effect distortion, never scored) | A validation-methodology idea absent from ALPHA_RANKER's growth/asset-growth legs | Y — cheap add-on diagnostic, no new data needed |

## 3. Cheap-test result — noted, not credible as an all-weather signal

`metrics.json` (2-pillar Quality+Value stand-in, NOT the 8-pillar framework): monotonic positive
quintile spread (Q5−Q1 = +4.65pp/yr, 12M, n=47 formation months), beats a shuffled-score placebo
at the 100th percentile (36M secondary: 96th). Sounds clean, but the file's own regime-split kills
the headline: **excluding the 2022-06→2023-09 "meltup" window, mean spread flips to −2.07pp with
Newey-West t = −0.92** (`primary_spread_excluding_meltup`, `primary_nw_t_excluding_meltup` in the
file) — i.e. essentially ALL of the positive result lives in one 16-month bull run, and it's
*negative* in the pre- and post-meltup regimes (42.9% of months positive in the "recent" 2023-10→
2025-06 regime). This is exactly the **bull-panel-artifact pattern ALPHA_RANKER's own discipline was
built to catch** (cf. Weinstein stage-2's identical 21yr sign-flip). Caveats acknowledged by the test
itself: gross of costs, survivor-biased current-membership universe (not PIT membership), only 2 of
8 pillars, weak Newey-West t even in the full sample (1.14). Not a kill (Gate-3 doesn't require
t-stat), but not evidence of a durable all-regime edge either — matches ALPHA_RANKER's general
finding that quality+value composites are real but modest, not the 2022-vintage magnitude.

## 4. Reconciliation — contradictions and confirmations

**Should the two merge?** No — keep as separate projects (Principal's explicit instruction), but
STOCK_SCORECARD_750 should **read ALPHA_RANKER's kill list before finishing pillars 5 ("Stage/Technical"),
7 ("Ownership/Smart-Money Flow"), and part of 6 ("Sector & Macro Positioning")** — it is about to
re-build things already falsified:

- **Weinstein Stage 1-4 (Pillar 5) — direct contradiction.** ALPHA_RANKER killed Weinstein stage-2 as a
  confirmed bull-only overfit artifact (21yr sign-flip: +0.19 IC in a 2021-26 panel → −0.12 on the full
  21yr history; `coverage_map.json` tags it "automatic Gate-4 fail class", no resurrection path). Building
  a Stage pillar on the same construction risks importing a known-dead signal wholesale.
- **FII/DII accumulation "+" in Ownership/Smart-Money Flow (Pillar 7) — direct contradiction for
  that sub-component.** ALPHA_RANKER tested FII/DII accumulation as a drift/momentum signal and killed
  it — **wrong sign** (contrarian, not accumulation-confirms-continuation) — `CONSOLIDATION.md`,
  `coverage_map.json`. However, **Promoter-buying drift specifically shows the correct sign** (IC_IR
  1.33, mono 0.72, clean gates) but only 17% observation coverage (stale shareholding data,
  flagged a strong resurrection candidate once fresh NSE data lands). Useful confirmation:
  STOCK_SCORECARD_750 should split promoter (works) from FII/DII (doesn't) rather than blending all
  three into one "+" pillar.
- **Sector&Macro Positioning (Pillar 6, 10% weight) — adjacent to a tested-and-killed construction.**
  ALPHA_RANKER tested sector rotation standalone (net −12%/yr, gate-fail) AND as a conviction-modulator
  blended onto its 7-leg composite (`wave4/SECTOR_CONTEXT.md`) — incremental IC delta is *negative* at
  every blend weight tested (w=0.15..1.00), and PBO fails (KILL) at every weight. A 10%-weight sector-RS
  pillar in the final composite is functionally the same experiment ALPHA_RANKER already ran and killed.
- **DCF pillar — largely duplicate, not new.** ALPHA_RANKER already built a 2-stage FCF DCF (`builders_w2_dcf.py`):
  Gordon terminal growth, WACC grid {11,13,15%} × terminal {3,5%}, found highly correlated with EY (0.74)
  and kept only as a borderline 5Y secondary (dropped at 1Y, IC flat). STOCK_SCORECARD_750's own
  IMPLEMENTATION_PLAN (Task 11) concedes beta is NOT derivable from the fundamentals source, so its
  discount rate collapses to the same flat risk-free+ERP proxy ALPHA_RANKER already uses — this is
  effectively the same DCF construction, not a new one, despite MASTER_PLAN.md's framing of a
  "beta-adjusted CAPM."
- **Sector-neutral percentile ranking, accruals/CFO-PAT quality, OBV/volume-price divergence** —
  all already built and tested in ALPHA_RANKER (H048 sector-neutral cards; IDG_G05 accruals as a
  canonical 7-leg member; H036 OBV divergence, killed FAIL_GATE at 1M — Accumulation pillar's 6-12M
  horizon isn't an exact retest but is the same family, worth a quick look before assuming it works).

**Confirmation, not contradiction:** both efforts independently rediscovered the same meta-lesson —
apparent multi-year "edges" concentrate in a 2021-23 bull/meltup window and reverse or flatten
afterward (STOCK_SCORECARD_750's own regime-split; ALPHA_RANKER's IC-decay finding 0.190→0.111 and its
"5yr bull-panel artifact" corrections across ~8 killed ideas). This is useful cross-validation of the
firm's general skepticism discipline, not a contradiction.
