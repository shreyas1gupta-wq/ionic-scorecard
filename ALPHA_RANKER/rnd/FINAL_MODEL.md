# ALPHA_RANKER — FINAL MODEL (overnight research output; pre-production, honest)

> Repeatable, regime-aware, NON-fixed -100..+100 scorer for 1M/1Y/5Y. Built money-first, cross-regime-validated
> on the 21-yr panel, orthogonality-pruned. Modest but real edges. NOT production until the gates in §5 clear.

## 1. Independent legs (AFTER orthogonality pruning — this is the key honesty step)
The raw survivor list was ~12 factors, but the orthogonality matrix (`reports/orthogonality_matrix.csv`) shows the
value block is nearly ONE bet — EY~smallcap-tier 0.94, marketstate~smallcap 1.00, EY~DCF 0.74 — and QMJ~BAB 0.77.
Collapsing redundancies leaves **~7 genuinely independent bets** (not 12):
| Leg | Type | Horizon fit | Note |
|---|---|---|---|
| Earnings yield (EY) | value | 1Y+5Y | THE value representative (absorbs DCF/market-state/smallcap-tier — all 0.74-1.00 corr) |
| QMJ composite | quality | 1Y+5Y | bear-defensive; absorbs BAB (0.77). Quality works as COMPOSITE, not single legs |
| Residual 12-1 momentum (PLAIN) | momentum | 1Y | strongest 1Y leg; FRAGILE high-vol → size down. CORRECTION: PLAIN beats sub-sector PEER-RELATIVE on 21yr (0.69 vs 0.55) — the earlier peer-relative>plain (0.92 vs 0.72) was a 5yr-BULL-PANEL ARTIFACT, reversed on full history. Use plain. |
| MA-65 slope | trend | 1Y | stack/slope; not tradeable at 1M |
| Net-share-issuance (−) | balance-sheet | 1Y | orthogonal, era-stable |
| Asset-growth (−) | balance-sheet | 5Y | orthogonal, strengthening post-2015 |
| CFO/PAT authenticity | forensic-quality | 1Y | beats accruals/cash-conv; orthogonal |
| ~~Cross-sectional seasonality~~ | DROPPED | — | leave-one-out passenger (ΔIC_IR −0.047, 2x turnover) — excluded |
DCF kept only as a borderline-distinct 5Y value secondary (0.74 corr to EY). BAB dropped (redundant w/ QMJ).

## 2. Per-horizon composite (SIMPLE RANK-AVERAGE of the horizon's independent legs)
- **1Y (the real model) — VALIDATED by leave-one-out incremental test (rnd/reports/incremental_value.csv):**
  **EY + PLAIN residual momentum + MA-65 + QMJ + net-issuance + asset-growth + CFO/PAT** = 7 orthogonal legs, EACH
  proven to add incremental IC/mono over the base (corr<0.6). Momentum is PLAIN (peer-relative reversed on 21yr).
  asset-growth promoted to 1Y (best add, ΔIC_IR +0.065). DROPPED as passengers: seasonality (ΔIC_IR −0.047, 2x turnover)
  and DCF-at-1Y (IC flat, mono degrades — DCF stays 5Y-only secondary).
  **CANONICAL BUILD (Gate-1 cleared, 2026-07-17): `rnd/lib/composite_final.py` -> `rnd/cards/CANONICAL_7LEG_1Y.json`.
  IC_IR 1.345, monotonicity 0.9999, lag_test_delta 0.060 (clean, <0.25 threshold), n_ic_dates=145 (2015-2025-ish
  trustworthy core, see §5-AUDIT era caveat).** This is the ONE authoritative number; all others below are superseded
  history kept for the audit trail only. Construction fixed: equal-weight rank-average of the 7 legs, **min_legs=5-of-7**
  required to emit a composite value (a date/name with <5 legs present is NOT scored as "the 7-leg composite" — avoids
  a data-thin 2-leg proxy masquerading as the full model), universe = panel_long.parquet as-is (no extra ADV/price
  screen), corporate-action guard applied (disc_event_in_window_1Y>0 rows NaN'd, 1,215/148,297 rows — closed a gap
  neither prior rebuild had). Official card portfolio construction = decile (harness default, unchanged); a
  supplementary QUINTILE long-short (ann_LS 2.83, more names/bucket, safer for the >=30-trades/parameter rule) is
  recorded alongside, per PREIC_AUDIT S1 (decile-vs-quintile does not move IC_IR/monotonicity, only bucket width).
  Spread across 7 independent bets → lower single-factor risk, more durable.
  (SUPERSEDED history: earlier 0.91 used the wrong 4-leg `CAPSTONE_COMPO_1Y_final` card incl. peer-relative
  momentum — never the described 7-leg stack. Two competing 7-leg rebuilds then disagreed — `CONC_composite_1Y_raw`
  1.25 (min_legs=2-of-7, diluted-input) vs `AUDIT_TRUE7_1Y` 1.36 (min_legs=5-of-7) — the gap was the leg-presence
  threshold, NOT decile/quintile/weighting/universe, which were identical in both. min_legs=5 is canonical; min_legs=2
  is SUPERSEDED. `CANONICAL_7LEG_1Y` differs from `AUDIT_TRUE7_1Y` only by the added corporate-action guard.)
  CONCENTRATION CHECK (rnd/reports/concentration_check.md): edge is BROAD (19/20 sectors IC_IR>0.20, no persistent sector/size
  overweight) and SURVIVES neutralization (sector-neutral 85%, size-neutral 107%, both 94% of IC_IR) → genuine within-sector/
  within-size stock selection, NOT a concealed sector/size bet. No concentration red flag for the IC memo.
- **5Y:** EY + QMJ + DCF + asset-growth + CFO/PAT (value+quality+balance-sheet heavy). Indicative — pre-2012
  fundamentals thin; treat magnitudes as directional.
- **1M:** thin/honest — sector-momentum only, LOW-CONVICTION. No tradeable trend/value/catalyst leg at 1M; no 21-yr
  intra-month confirmation. Ship with an explicit low-confidence flag rather than fabricate weight.
- Score map: `score = 200*(rank_pct(composite) - 0.5)` -> [-100,+100]. Zero fitted params today (repeatable, non-fixed).

## 3. Regime handling = SIZING, not blending (corrected lesson)
The return-blend regime overlay was TESTED AND REJECTED (it lifts full-cross-section IC but dilutes the tradeable
extreme-decile spread — loses net-of-cost at every band). The regime insight monetizes as EXPOSURE control:
- **%>200DMA breadth scalar** — scale gross exposure by market breadth: maxDD -52%→-26% (halved), Sharpe 0.56→0.62.
- **India-VIX regime** — vol-spike = higher forward 1Y (buy-the-panic exposure tilt).
- In high-vol, SIZE DOWN momentum exposure (it crashes in bear) and lean on QMJ/EY (bear-defensive) — via weights
  that flex with a causal p_bear, floored at 0 (never short a leg). This is the "non-fixed" part.

## 4. What was rejected (discipline — nothing promoted on shine)
Weinstein stage-2 (bull-only, 21yr sign-flip), vol-scaled-mom at 5Y, raw growth (trap), forced interactions
(QARP/GARP/Greenblatt/magic-formula — none beat EY-alone), short-term mean-reversion, ROCE-longevity streak
(wrong-sign), deleveraging (dead-cat), under-owned-value (doesn't beat EY), frog-in-pan & trend-R² (dilute momentum),
idio-vol/MAX (cost/lag), size, dispersion, breadth-divergence, NH-NL, earnings-stability, the return-blend regime overlay.

## 5. GATES BEFORE PRODUCTION (not crossed — do NOT deploy on in-sample shine)
1. **Calibration** — score→p_up / E[return] / win-rate mapping is NOT built (Principal deferred). Today's output is a
   cross-sectional RANK/conviction, not a probability.
2. **1M unconfirmed** (no 21-yr intra-month cube); **5Y data-thin** (pre-2012).
3. **Magnitudes are MODEST** (low single-digit %/yr net LS decile spreads after the ×12-annualization fix) — real, not the inflated early figures.
4. **Full sensitivity + red-team + lookahead-audit skills pass** on the composite, then **IC memo (CIO+FM)** = the adoption gate.
5. Deep per-stock analyst phase (25 at a time) comes AFTER this model is frozen (Principal order).

## 5-RISKOFFICE. SIGN-OFF WITHHELD (2026-07-17, rnd/reports/LOOKAHEAD_T1T10.md + DSR_PURGEDCV.md) — VERDICT: PARK, NOT PROMOTE
No leak/fabrication found (T1 PIT clean, one-day-lag clean: composite 0.059, legs <0.12). But sign-off WITHHELD for two real reasons:
1. **SURVIVORSHIP BIAS (T5 FAIL) — REMEDIATED 2026-07-17, RESULT: NOT THE INFLATION SOURCE.** Rebuilt the universe PIT-correct: `rnd/lib/build_panel_pit.py` filters `panel_long.parquet` to the NEAREST-PRIOR snapshot membership from the mandated 42-snapshot `NIFTY500_TICKER_2005_2025_Final.xlsx` at every rebalance date (backward merge_asof, no future snapshot ever used) → `rnd/panel/panel_pit.parquet` (99,415 of 148,297 rows kept, 67.0%; coverage tightens with era: 74.7% kept 2005-09, 61.8% kept 2020-25, consistent with panel_long's uncontrolled universe growing to 783 avg names/date by 2020-25 vs the index's true ~500-528). Re-ran `composite_final.py`'s exact TRUE7/min_legs=5/decile-harness logic on this survivorship-free panel (`rnd/lib/composite_pit.py`, ranks recomputed WITHIN the PIT-eligible cross-section per date, not a post-hoc subset of biased ranks) → `rnd/cards/CANONICAL_7LEG_PIT_1Y.json`: **IC_IR 1.760 (UP from the biased 1.345, not down)**, ic_mean 0.181 (vs 0.189 biased, essentially flat), monotonicity 0.988, lag_test_delta 0.052 (clean), placebo_IC -0.003 (clean), n_ic_dates=141 (vs 145 biased). **Honest re-verdict: survivorship bias was NOT inflating this composite's headline IC_IR — the smaller, index-correct universe has slightly LOWER cross-sectional IC variance (ic_std 0.103 vs 0.141), which is what moves the ratio, not a higher/fabricated mean.** T5 is now CLOSED as a construction defect (fixed, re-scored, both numbers on record) but does NOT resolve reason #2 below.
2. **MULTIPLE-TESTING / DSR fails at honest N — CONFIRMED UNCHANGED on the survivorship-free rebuild.** PIT card: DSR 1.58e-58 (≈0), PBO 0.922 (vs 0.909 biased) — if anything marginally worse. After 456 logged trials, deflated-Sharpe DSR fails catastrophically at any realistic trial count; CSCV-PBO stays far above the 0.25 kill line on both universes. This is the core overfit risk and survives the T5 fix untouched — it is a trial-count/multiplicity problem, not a universe problem. FIX is NOT more deflation — it's a FRESH HELD-OUT / FORWARD test of the frozen 7-leg composite (pre-register, evaluate once).
Also: bs_asset_growth never independently lag-tested (gap). → **Composite verdict on BOTH universes = KILL (PBO > 0.5)** per the shared harness's own `verdict()` gate — T5 is remediated, but this does not change the underlying stay-PARK/KILL call; DSR/PBO remain the binding constraint. Do not promote pending a fresh forward test.

## 5-AUDIT. PRE-IC ADVERSARIAL VERDICT (rnd/reports/PREIC_AUDIT.md) — READ BEFORE TRUSTING ANY NUMBER
**Status: FRAGILE-BUT-REAL, robust-to-perturbation, NOT YET GATE-4 CERTIFIABLE (risk-office sign-off WITHHELD — see 5-RISKOFFICE).**
- ROBUST: perturbation battery (weights/decile-quintile/rebalance-offset/random-drop/drop-sector) → tight IC_IR bands, no sign flips, no load-bearing leg/sector. Not knife-edge.
- CANONICAL-BUILD BUG — **CLOSED 2026-07-17**: prior headline (0.91) came from a stale 4-leg card (peer-momentum+redundant
  smallcap), NOT the 7-leg PLAIN stack. The 1.25-vs-1.36 disagreement between two independent 7-leg rebuilds is now
  reconciled: both used identical legs/weighting/universe, and differed ONLY in the `min_legs` leg-presence threshold
  inside the rank-average (2-of-7 → 1.25, diluted by data-thin months scored off as few as 2 legs; 5-of-7 → 1.36,
  refuses to score a date/name as "the 7-leg composite" unless most legs are actually present). **min_legs=5 is
  canonical.** ONE build now exists: `rnd/lib/composite_final.py` → `rnd/cards/CANONICAL_7LEG_1Y.json`,
  **IC_IR 1.345, monotonicity 0.9999, lag clean** — cite this and only this going forward.
- IC DECAY (undisclosed until audit): IC_mean 0.190 (2015-20) → 0.111 (2020-25), nearly halving. Edge is fading — must be disclosed.
- OPEN GATES before any IC memo / production: (1) single canonical composite build; (2) DSR/PBO proper fix = purgedcv (risk-office/Sameer sign-off, not quant-desk "advisory" fiat); (3) formal T1-T10 `lib/lookahead_audit.py` battery — NEVER RUN on ALPHA_RANKER (D-028 gap); (4) usable era coverage is really ~2015-2025 (2005-10 empty, 2010-15 thin); (5) calibration (deferred).

## 5a. PORTFOLIO PERFORMANCE (authoritative — the "does it make money" answer, rnd/reports/FINAL_BACKTEST.md)
- **HONEST edge = market-neutral LONG-SHORT: CAGR ~12%, Sharpe ~0.8, maxDD −38%.** This is the genuine selection alpha.
- Long-only top-quintile shows CAGR 29.5% (w/ exposure scalar) / 34.3% (w/o), Sharpe ~1.5-1.6 — but this is INFLATED by an equal-weight small/mid SIZE TILT vs cap-weighted NIFTF500 (benchmark mismatch). DO NOT quote as the edge.
- **Exposure scalar (breadth+VIX) works:** long-book maxDD −37%→−26% (cut a third) for ~5pt CAGR. Costs not the swing factor (2x cost = −1.7pt CAGR). No degenerate flags; a lookahead bug in old overlay code found & fixed.
- **BACKTEST HORIZON CORRECTION: portfolio-level is effectively ~2012-2025 (~13yr), NOT 21yr.** Fundamentals data cliff (universe 49→470 in 2012) means the full composite CANNOT claim 2008/2011. Real bear tests at portfolio level = 2018 (−11%), 2020 (LS −28.9%, sane momentum-crash), 2022 (LS +24%, value rotation). Factor-level ICs used longer price history, but the fundamental-bearing MODEL is a ~13yr result. Earlier "21yr through 2008/11/20" framing was overstated — corrected.
- Verdict: FRAGILE-BUT-REAL. Weakest unvalidated piece: India-VIX panic-floor in the scalar (breadth part is validated).

## 5b. MAGNITUDE RECONCILIATION (authoritative numbers — resolves a doc inconsistency)
Two number-sets exist in the corpus; **the 21-yr, DSR/annualization-CORRECTED set is authoritative**:
- SURVIVORS.md / early-wave cards quote momentum/value net-LS of ~+11-19%/yr — these are 5-yr BULL-PANEL, PRE-correction (the ×12 annualization bug + bull-sample inflation). SUPERSEDED — do not quote.
- AUTHORITATIVE (21-yr panel_long, ×12 bug fixed, DSR per-family): edges are MODEST — low-single-digit %/yr net long-short decile spreads (e.g. EY ~+2%/yr). IC_IR/monotonicity are the reliable ranking metrics; the equity-curve run (roadmap item) will pin the exact net-of-cost figure. Any IC memo cites ONLY the 21-yr-corrected numbers.
PENDING to fully close: leave-one-leg-out incremental test (running), a 21yr net-of-cost equity curve through 2008/11/20, and per-sector IC of the composite (confirm it's not a concealed sector bet).

## 6. Artifacts
`SURVIVORS.md` (per-factor), `CONSOLIDATION.md` (living verdict log), `MODEL_SPEC.md` (architecture), `scoreboard_v2.csv`,
`reports/orthogonality_matrix.csv`, `cards/` (all experiments incl. FINAL composite), panels `panel.parquet`/`panel_long.parquet`.
