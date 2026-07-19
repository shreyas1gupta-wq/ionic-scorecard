# WAVE-4 — Consolidated Findings (Principal-facing)
Date 2026-07-17 · DESK-100 · Governs: FRONTIER_OPUS.md (small/orthogonal/next-sleeve) + Principal's
low-t + IC-vs-absolute directives (memory: feedback-low-t-power-aware-rescreen).

## 0. What this wave did
Mapped coverage of the 457-trial program (19 gaps, 10 data-blocked), generated ~37 new orthogonal
hypotheses from on-disk factors + investor books/papers + AIF/PMS memos + forensic craft + cross-asset
macro + concalls, TESTED 7 distinct mechanisms, ran an adversarial pass on 2 regime signals, and
RE-SCREENED all 473 cards to rescue signals killed on significance rather than structure.

## 1. NEW orthogonal finds (wave-4 tests) — money-first verdicts
| Signal | Orthogonal (corr vs 7-leg) | Lag/placebo | Effect | Verdict |
|---|---|---|---|---|
| **Clean-surplus / phantom-earnings** (W4F-02) | Yes (0.27) | PASS | 8-leg composite IC_IR 1.34→**1.81** | **FORWARD-TEST CANDIDATE** (best new find; equity-channel earnings authenticity, ~6x CFO/PAT coverage) |
| **Depreciation-policy laxity** (W4F-01) | Yes | PASS | 8-leg IC_IR 1.34→**1.66** | **FORWARD-TEST CANDIDATE** (accounting-choice tell no leg touches) |
| **Amihud illiquidity** (W4-08) | Yes (0.10) | PASS @1Y | IC_IR **1.19** (1Y) | **FORWARD-TEST CANDIDATE, data-limited** — killed only on single-regime (2022-25) PBO; volume data is 5yr-only. Real+logical+orthogonal; needs more history. |
| Net Operating Assets (W4-01) | Yes (−0.01) | PASS | 8-leg IC_IR 1.34→1.29 (no lift) | DROP — orthogonal but adds nothing incrementally |
| Momentum-within-quality double-sort (W4-12) | n/a | — | rank-avg beats it 2.7x; mono collapses | KILL (structural — forced gating hurts) |
| Distress composite (W4B-02) | Yes (0.24) | PASS | sign-flips 1Y/5Y; hurts book (IR −0.44) | KILL (structural — sign-unstable) |
| Cyclical normalized-EY (W4P-03) | Yes (0.12) | PASS | 0.23 vs TTM-EY 0.42 in cyclicals | KILL (loses to the incumbent it aimed to beat) |

## 2. Cross-asset / regime SIZING signals (the user's commodity/macro ask)
Data was on-disk (macro_state + gold/silver ETFs); copper pulled. Everything KILL except 2 candidates:
- **Copper/gold ratio (6m Δ)** and **gold-vs-equity momentum** as exposure-sizing scalars: BEAT trailing
  VIX/breadth on Sharpe/maxDD, cleared a 200-trial noise floor at the study's top z-scores, and **survived
  era-split + leave-one-bear-out** (NOT a one-bear mirage — notable). BUT fail linear-IC lag stability and
  DSR on n≈114 months. **Verdict: PARK-NEEDS-MORE-DATA** — do not start a live sizing sleeve on ~5 bears.
- Does cross-asset beat trailing-VIX for sizing? Honest answer: MAYBE, unproven at this sample size.
- INTEGRITY FIX: MACRO_XASSET.md claimed a FRED data-fill that did NOT persist to disk (brent/dxy/real-rate
  0% non-null). Annotated in that file; data-officer to actually run+persist the enrichment.

## 2b. SECTOR-context + MARKET-band (Principal's sectoral/market-as-a-whole ask) — recovered from cards
- SECTOR context does NOT add value: blend-weight sweep IC_IR 1.70(0%)→1.61(15%)→1.52(30%)→1.42(50%)→1.23(100%)
  — monotonically WORSE with more sector weight. Best = 0%. Stock-level 7-leg already captures it. β_sector≈0.
  (Consistent with prior sector-rotation kills. At most a qualitative memo context, never a selection input.)
- MARKET valuation-band (richness): PARTIAL SUPPORT — forward-RETURN DIRECTION robust (cheap→+, strengthens
  5Y ex-2008; confirms Principal's "60-70 → positive 5Y" DIRECTIONALLY). BUT crash-magnitude ("160+") NOT
  confirmed, index under-ranges expensive-side post-2009. As active sizing dial = NO (Sharpe 0.53→0.45 vs
  always-invested); only de-risk-only, low-freq (qtly/annual). Cross-ratios (smallcap/sensex/gold) =
  qualitative corroboration only. NET: M-term enters absolute scorer SIGN-ONLY (real esp. 5Y), never sizing.
  Only breadth+VIX earned the sizing role. Cards W4SEC_*, W4MKT_*.

## 1-CORRECTION (2026-07-17, drop-one v2 + reconciliation — SUPERSEDES §1 optimism):
The earlier "clean-surplus lifts composite IC_IR 1.34→1.81 / dep-laxity →1.66" were ARTIFACTS of a flawed
8-leg computation. The careful rebuild (base-7 sanity-checked at official IC_IR 1.345) shows the true
INCREMENTAL deltas: clean-surplus +0.009 (negligible), dep-laxity -0.053 (HURTS), beta-adj-mom -0.167
(HURTS, era-collapses 2nd-half), vol-scaled-mom -0.109 (HURTS, era-collapses). NONE survives drop-one as an
addition to the composite. HONEST NET: wave-4 produced NO new IC-additive leg. clean-surplus standalone
mono=0.006 (untradeable alone) → composite-redundant, not a find. The momentum "rescues" collapse to ~1
crowded bet (null-sweep) AND hurt the book. Salvageable value is on OTHER axes, not IC:
- clean-surplus + CFO/PAT are CONVEX / tail-protective (positive skew) — a hedge/overlay role, NOT an IC leg.
- asset-growth (neg corr in stress) + CFO/PAT are the genuine within-book DIVERSIFIERS (co-crash analysis).
The 7-leg composite stands as-is (~15% reconciled deployable, still parked on multiple-testing). Wave-4's
real yield = design refinements (broad-market valuation gauge, momentum-extreme gate, gold/cash de-risk,
junk-rip conditioner) + honest negative results, NOT new alpha legs.

## 1-CORRECTION-2 (2026-07-17, W5 validation — SYSTEMIC BUG + more kills):
ROOT-CAUSE BUG: run_w5_convex.py (and the W4 8-leg tests) used a "base7_reconstructed" (IC_IR 1.3374) built
with the WRONG momentum leg — mom_resid_PEER (capstone cache) instead of the official mom_resid_PLAIN that
CANONICAL_7LEG specifies (capstone_legs.parquet has NO mom_resid_plain row — silent substitution). So EVERY
"8th-leg adds IR" number this wave was computed against the wrong base. Against the sanity-checked base-7
(reproduces official 1.345 bit-for-bit):
- W5-01 cost-elasticity: reported +0.396 → TRUE −0.069 (HURTS, sign flips), drop-one 21/21 negative = ARTIFACT.
- W5-02 implied-borrowing-cost (the "convex hedge win" — I OVER-CLAIMED it): does NOT hold. COVID crash month
  (Mar-2020) is NEGATIVE; 2022 is 4/7 months negative (mean +0.24% = noise); GFC zero data; unconditional IC
  sign-FLIPS across halves (+0.050→−0.044, Gate-4 red flag). = one lucky COVID month, NOT a structural hedge. DEAD.
SECOND SYSTEMIC ARTIFACT (found in W5-05/06/07/08 run): the 8-leg "incremental IR delta" is ALSO contaminated
by a DATE-MISMATCH — min_legs>=6 drops the base-7 IC-date count 145->141, and that period-selection ALONE
lifts IC_IR 1.337->1.5-1.75 (not information from the candidate). So the incremental-IR column was broken by
TWO independent bugs (wrong momentum leg + date-mismatch). Net: NO "adds IR to composite" number this wave is
trustworthy. Only STANDALONE IC/decile/drop-one/lag/placebo (scale- & date-robust) are reliable. The
incremental-test harness needs a date-matched + correct-base fix before ANY future PROMOTE.
RULE GOING FORWARD: no incremental-IR or convex-hedge claim is believed unless (a) computed vs the base-7 that
reproduces official 1.345 on the SAME date set as the 8-leg, AND (b) survives per-episode drop-one + era-split.
W5-05/06/07/08 all KILL (inverted/redundant/lag-fail/degenerate). Enthusiastic interim reports that
skip this are provisional and have repeatedly evaporated.

## CUMULATIVE HONEST TALLY (wave 4+5): ZERO surviving new IC-additive leg. ZERO surviving convex hedge. All
## candidates (clean-surplus, dep-laxity, NOA, momentum-rescues, distress, cyclical-EY, W5-01/02/04, gap factors)
## died under careful validation. The ONE genuine positive still standing = the OVERSOLD-MEAN-REVERSION regime
## switch (clean placebo/lag/drop-one; certification pending). Everything else of value = DISCIPLINE (bugs caught,
## artifacts killed), KNOWLEDGE (forensic module, business-model KB, co-crash, tail map), and the REGIME/ABSOLUTE
## DESIGN. The 7-leg composite stands unchanged (~15% reconciled, parked). Forward-growth/divergence = open (running).

## VERDICT RECLASSIFICATION (2026-07-17, Principal directive re-emphasized 3x): significance (t/p/DSR/PBO/
## small-n) is NEVER a kill reason. ONLY structural failures kill: leakage (lag/placebo), wrong/flipped sign,
## redundancy (repackages existing leg), gross-shortfall, flat/coinflip, demonstrated data-artifact. A
## logically-sound + correctly-signed + decent-effect signal that fails only on stats = KEEP as forward-test/watch.
## RECLASSIFIED FROM "KILL" -> FORWARD-TEST/WATCH:
##  - W5-02 implied-borrowing-cost: sound credit-market logic, crash-protective 2/3 windows; robustness-unconfirmed
##    (sign-flips halves, one-episode-heavy) is NOT structural death. Convex-hedge candidate for forward test.
##  - clean-surplus: real IC 0.68 + skew +3.04; not a standalone-tradeable/additive leg but a CONVEX-OVERLAY watch candidate.
## STRUCTURALLY DEAD (stay): W5-01 (sign flips on correct base), momentum-rescues (redundant w/ momentum leg +
##  unborrowable short), distress (sign-unstable across horizons), W5-05/08 (INVERTED sign), NOA (0 incremental),
##  downside-capture (redundant w/ BAB @3m/6m + convexity = 2006-12 data artifact).
## TODO: systematic re-audit of ALL wave KILLs to pull any significance-only ones into forward-test/watch.
## LANGUAGE FIX: never report "KILL (PBO>0.5)" — PBO/DSR are advisory; state the STRUCTURAL reason or say KEEP-WATCH.

## 3. RESURRECTION re-screen (473 cards) — your low-t directive, executed
- 179 STRUCTURAL-dead (kept dead: lag/placebo fails, sign-flips, wrong-sign, regime-blend overlay, PEAD
  confirmed-dead, forced-interactions) — correct kills, not power kills.
- 216 forward-test candidates, split honestly:
  - **Tier A (40 cards, ~6 families) = the genuine rescues.** All 1Y momentum/trend factors killed ONLY on
    saturated PBO (fired 0.85-1.00 on EVERY card incl. clean IC_IR>0.7 — uninformative here). Ranked by
    absolute net-of-cost return (your IC-vs-money directive):
    | Family | Mechanism | Abs net-LS/yr (cost-corr) | IC / mono | Note |
    |---|---|---|---|---|
    | H002 MA-slope sweep | slope/dist from DMA plateau | **19.3%** | 0.076 / 0.94 | strongest abs return |
    | H043 beta-adjusted momentum | momentum ex-beta | **19.0%** | 0.080 / 0.92 | genuinely NEW rescue |
    | H004 vol-scaled ("Sharpe") momentum | return/vol 3-12m | **17.6%** | 0.087 / 0.98 | |
    | H003 residual 12-1 momentum | FF-neutral | 17.3% | 0.087 / 0.83 | already a model survivor |
    | H001 65-DMA slope | 65 vs 50 (less-gamed) | 14.3% | 0.074 / 0.84 | KILLED.md: "don't resurrect on IC_IR alone" — wants longer panel |
    | H041 52w-high vs 12-1 | anchoring horse-race | (neg net-LS — caution) | 0.070 / 0.31 | weakest; read decile table |
  - **Tier B (176 cards) = composites, treat skeptically.** High n_trials (450-480) → PBO may be catching
    real search-overfitting, NOT just underpower. Includes the canonical 7-leg + the wave-4 8-leg blends +
    W3_qualgate (quality-in-bear sizing, independently re-confirmed clean) + IDG_I_04 underowned-value
    (40%/yr) + QMJ. These stay parked pending forward-test — the SAME multiple-testing wall, not new rescues.
- 6 NEEDS-MORE-DATA (H050 n=10; H035 delivery stale; H047 Hurst buildable; H049 macro-regime unwired;
  W2_macro_risk_regime single-series). 3 genuinely-dead (MA-slope at 1M — the effect is a 1Y phenomenon).

## 4. Management-credibility signal (bluff-detection) — build-spec, pilot only
139-company text-ready concall set (MiMIC, 2015-24); guidance-vs-delivery design written. PILOT-only (too
thin/clustered for a real cross-sectional test). P0 bug caught: regex miscounts analyst questions as mgmt
commitments — must add speaker attribution. Real backtest needs the 264-name PDF set OCR'd. → DATA ASK.

## 5. Memo-craft (how ALPHA_RANKER presents conviction) — ADOPTED
Every conviction score ships with a **ranked falsification clause** ("what breaks this, in priority order")
in the same paragraph as the thesis — the PMS study showed managers lacking an explicit deterioration→exit
hierarchy underperformed those who had one. Template in MEMO_CRAFT.md.

## 6. DATA-ASKS (highest-EV, blocked on data not compute — for Principal's home-network pull)
1. Fresh NSE shareholding/SAST → promoter-buying drift (validated IC_IR 1.33, near-free EV).
2. Analyst EPS-revision feed → estimate-revision momentum (highest-documented orthogonal factor).
3. Receivables/DSO + unbilled/contract-assets + working-capital split → the revenue-recognition forensic
   tells (aggressive pro-rata / revenue-booked-ahead-of-cash) that are currently UNBUILDABLE.
4. Concall OCR + date-parse (264-name PDF set) → management-credibility signal beyond the 139 pilot.
5. Persist macro_state FRED enrichment + India 10Y G-sec → re-enable cross-asset regime tests.
6. Refresh delivery-% (stale 2024-06) → H035.

## 7. BOTTOM LINE
- The forensic/earnings-quality lane (Principal-steered) produced the wave's real finds: 2 new orthogonal
  quality legs (clean-surplus, depreciation-laxity) that lift composite IR — as forward-test candidates.
- The low-t re-screen rescued ~6 real momentum/trend families (esp. beta-adj momentum, MA-slope, vol-scaled)
  wrongly buried by a saturated PBO — for the Principal to green-light into forward testing.
- Nothing was promoted in-sample. The binding constraint remains the forward test (frozen model grades
  ~Dec 2026). Every rescue/new-find is a fresh-forward-clock candidate that NEVER touches the freeze.
- All new candidates need the ONE honest guard before belief: drop-one / era-split robustness (confirm the
  absolute edge isn't 1-2 lucky prints) — already applied to the regime signals and Amihud.
