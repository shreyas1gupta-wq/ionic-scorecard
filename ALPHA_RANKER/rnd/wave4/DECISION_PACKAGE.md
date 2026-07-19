# ALPHA_RANKER — PRINCIPAL DECISION PACKAGE (IC-memo-candidate)
**Author:** Rajan Mehta (CIO, E-001) · **Date:** 2026-07-17 · **Status:** capital-facing judgment, honest proven-vs-provisional
**Governs / sources:** `rnd/FINAL_MODEL.md`, `rnd/forward_test/FROZEN_SPEC.md`, `rnd/wave4/{WAVE4_FINDINGS, RESURRECTION_RESCREEN, ABSOLUTE_SCORER_SPEC, XASSET_ADVERSARIAL}.md`, `rnd/wave4/w4mkt_regime_results.json`.
**Tags:** [DATA] on-record · [INFERENCE] my construction · [OPINION] my judgment.

> **One-line honest frame:** Nothing in this program is promoted in-sample. The 7-leg model is PARKED under a
> DSR≈0 / PBO≈0.92 multiple-testing wall that no further compute can close — only the frozen forward test can.
> Every new find and every low-t rescue below is a *forward-test candidate*, not a truth; all magnitudes are
> provisional until forward data grades. [DATA]

---

## 1. FROZEN 7-LEG MODEL — STATUS: PARKED, DO NOT TOUCH
- **Legs (7):** value_EY, mom_resid_plain, trend_ma65_slope, quality_QMJ, bs_issuance, bs_asset_growth, quality_cfo_pat. Equal-weight rank-average, min_legs=5-of-7, PIT survivorship-controlled universe. [DATA: FROZEN_SPEC §2-3]
- **In-sample:** IC_IR 1.76 (PIT), monotone deciles, lag/placebo clean; honest edge is market-neutral LS ~12% CAGR / Sharpe ~0.8 / maxDD −38%. Long-only 29-34% CAGR is a small/mid SIZE-TILT artifact — NOT the edge. [DATA: FINAL_MODEL §5a]
- **Why parked, not promoted:** DSR 1.58e-58, PBO 0.922 after 456 logged trials — a multiplicity problem, not a construction defect. Survivorship (T5) remediated and was NOT the inflation source. IC is decaying (0.190 → 0.111, 2015-20 vs 2020-25). [DATA: FINAL_MODEL §5-RISKOFFICE, §5-AUDIT]
- **Freeze mechanics:** content-hash tamper-evident (`9fbfe8d4…`), scores banked as-of 2025-12-05, evaluate ONCE at a ~12-month horizon. **Awaiting the Principal's horizon confirmation. No peeking, no mid-window grading, no edits (any edit voids the test).** [DATA: FROZEN_SPEC §1, §5]
- **CIO ruling:** the freeze is the single most valuable asset in the building precisely because it is untouched. Nothing below merges into it. Every candidate gets its OWN fresh clock. **[OPINION]**

---

## 2. FORWARD-TEST CANDIDATE SLATE (ranked by conviction)
Evidence bar used: orthogonal to the frozen 7, lag/placebo clean, effect size real, and — the one honest guard —
drop-one / era-split confirmation that the edge isn't 1-2 lucky prints.

| # | Candidate | What it is | Evidence strength | Drop-one / era-split | Forward clock it needs |
|---|---|---|---|---|---|
| **1** | **Clean-surplus / phantom-earnings** (W4F-02) | Equity-channel earnings-authenticity tell (dirty-surplus items bypassing P&L); ~6× the coverage of CFO/PAT | **Strong.** Orthogonal (corr 0.27), lag/placebo PASS, 8-leg IC_IR 1.34→**1.81** (biggest lift in the program). Principal-steered forensic lane. [DATA: WAVE4_FINDINGS §1] | **PENDING** — not yet run on this leg (guard applied only to regime signals + Amihud so far) | Fresh 12-mo clock AFTER drop-one/era-split + orthogonality re-confirm vs the 7 |
| **2** | **Depreciation-policy laxity** (W4F-01) | Accounting-choice tell (aggressive useful-life / dep policy) no existing leg touches | **Strong.** Orthogonal, lag/placebo PASS, 8-leg IC_IR 1.34→**1.66**. [DATA: WAVE4_FINDINGS §1] | **PENDING** — same as #1 | Same as #1 — pair them on one forensic-leg forward clock |
| **3** | **Beta-adjusted momentum** (H043) | 12-1 momentum with the beta contribution removed | **Moderate.** IC 0.080, net-LS 19.0%/yr, mono 0.92, sign-stable all regimes; **lowest search (n_trials=15)**; killed only on saturated PBO. Genuinely new rescue. [DATA: RESURRECTION §4] | Regime sign-stable (in-sample); formal drop-one not run | Forward clock ONLY after incremental-IC vs frozen mom_resid_plain / ma65_slope (redundancy risk) |
| **4** | **Vol-scaled ("Sharpe") momentum** (H004) | Trailing return ÷ realized vol, 3/6/12m | **Moderate.** IC 0.087, net-LS 17.6%/yr, mono 0.98 (cleanest), n_trials=27, PBO-only kill. [DATA: RESURRECTION §4] | Regime sign-stable; drop-one not run | Same orthogonality gate as #3, then forward clock |
| **5** | **MA-slope sweep** (H002) | Distance/slope from DMA∈{20..200}, plateau-hunted | **Moderate-, higher search.** IC 0.076, net-LS **19.3%/yr** (highest abs), mono 0.94, but **n_trials=82/family** (more overfit surface) and overlaps trend_ma65_slope already frozen. [DATA: RESURRECTION §4] | Sign-stable; drop-one not run | Lowest-priority momentum rescue — redundancy-heavy; forward-clock only the incremental residual |
| **6** | **Amihud illiquidity** (W4-08) | Illiquidity premium, orthogonal micro-structure leg | **Real but DATA-LIMITED.** Orthogonal (0.10), lag/placebo PASS @1Y, IC_IR 1.19; killed only on single-regime (2022-25) PBO — **volume data is 5yr-only.** [DATA: WAVE4_FINDINGS §1] | Cannot era-split honestly — one regime of data | NEEDS MORE HISTORY first; short forward clock acceptable, grade cautiously |
| **7** | **Copper/gold ratio (6m Δ) sizing scalar** | Cross-asset EXPOSURE scalar (0.5/1.0/1.5×), not selection alpha | **Robustness surprising, stats fail.** Beats VIX-baseline on Sharpe/maxDD, era-split holds, **LOBO survives cleanly (strongest of the two)** — BUT DSR 0.003-0.15, weak lag-IC, n=114 months. [DATA: XASSET_ADVERSARIAL §2,§6] | Era-split + LOBO PASS | **PARK — paper/shadow only.** Re-run battery in +24mo. NOT a live clock today |
| **8** | **Gold-vs-equity (1m) sizing scalar** | Cross-asset exposure scalar | **Weaker twin of #7.** Era-split holds, LOBO survives on Sharpe test, but IC near-zero & sign-flips under one lag month, ~half the excess from 2 episodes, same DSR failure. [DATA: XASSET_ADVERSARIAL §3,§6] | Era-split + LOBO PASS | **PARK — paper/shadow only.** If only one is tracked, prefer #7 |

**Not on the slate (held):** H001 65-DMA slope (its own resurrection condition says "do not resurrect on IC_IR alone"; wants a longer panel); H041 52w-high vs 12-1 (weakest, mono 0.31, negative net-LS — read the decile table before believing). H003 residual 12-1 is ALREADY a frozen leg, not a new candidate. [DATA: RESURRECTION §4, FINAL_MODEL §1]

**CIO conviction ordering & caution [OPINION]:**
- **Green-light now (after the cheap in-house guard): #1 clean-surplus and #2 depreciation-laxity.** These are the wave's genuine new orthogonal edge, in the forensic-quality lane, and the two biggest composite lifts. They only lack drop-one/era-split — a same-day in-house test, no new data.
- **Green-light conditionally: #3 beta-adj and #4 vol-scaled momentum**, but ONLY after an incremental-IC/orthogonality check against the two momentum legs already frozen — my strong prior is they are substantially redundant with mom_resid_plain and ma65_slope. Forward-clock only the residual, and **size any momentum exposure DOWN** — the firm's worst blowups came from momentum crashing in calm-looking names in a bear. This is a tail-risk instruction, not a preference.
- **Park #5-#8.** #5 is redundancy-heavy with high search; #6 is honest but one-regime-of-data; #7-#8 are the most data-starved thing in the building (~5 bears) and fail DSR hard — a strong LOBO showing does NOT substitute for surviving multiplicity.

---

## 3. ABSOLUTE-SCORER BUILD ORDER
**Architecture decision [DATA: ABSOLUTE_SCORER_SPEC §0]: KEEP BOTH, COMPOSE — do not replace relative with absolute.**
The relative rank stays the frozen selection engine (what to own); the absolute layer is a thin, order-preserving
transform on top (how much / which direction overall). The order-preservation invariant + unit test is what makes it
NOT the return-blend that was already tested and rejected. [DATA: ABSOLUTE_SCORER_SPEC §1, CONSOLIDATION §3]

**BUILD NOW (zero new fitting, cannot corrupt the freeze, needs only this spec's approval):**
1. Formula skeleton + the `argsort(absolute)==argsort(r)` order-preservation unit test.
2. Wire the **already-validated breadth+VIX `s_mkt` scalar** as the multiplicative compressor (maxDD −52%→−26% is real). [DATA: FINAL_MODEL §3, §5a]
3. Soft valuation band `M` (tanh) — **SIGN ONLY**, coefficients as economic-prior constants, not fitted.
4. Sector tilt `T_sec` from the panel's own sector column + sector breadth.
5. Dual display + additive (SHAP-style) decomposition + coarse `p_up` band ("magnitude provisional") + ranked falsification clause.
6. **Leave-one-bear-out sensitivity on the market term is a GATE before it ships** (same bar the cross-asset scalars had to clear).

**WAITS for forward data + Principal sign-off + IC memo:**
- Magnitude → `p_up / E[ret] / win_rate` calibration (any map fit on our history inherits the DSR≈0/PBO≈0.92 verdict). Coarse bands only until the frozen grade (~Dec 2026). [DATA: ABSOLUTE_SCORER_SPEC §2]
- Any tuning of α_h, β_h, w, v_fair beyond prior seeds; promotion of the market term from provisional-sign to calibrated-magnitude.

**CIO caution the spec does not yet flag loudly enough [OPINION / DATA: w4mkt_regime_results.json]:** the market-valuation *richness* scalar, when actually backtested as a sizing dial, **UNDERPERFORMED always-invested** (Sharpe 0.53→0.45, maxDD −60.9%→−69.4%). So valuation ships as a **SIGN-only 5Y input** (its predictive rho vs fwd return is a real −0.30, and drop-one-era stable) — it must NOT be given a sizing role. Only breadth+VIX has earned the sizing dial. Do not let the valuation band quietly become a de-lever trigger.

---

## 4. DATA-ASKS — RANKED BY EV (edge unlocked per unit of Principal home-network effort)
| Rank | Ask | Unlocks | Why this EV |
|---|---|---|---|
| **1** | **NSE shareholding / SAST** | Promoter-buying drift | **Validated IC_IR 1.33, near-free.** Highest EV — already proven, cheap pull. [DATA: WAVE4_FINDINGS §6] |
| **2** | **Analyst EPS-revision feed** | Estimate-revision momentum | Highest-documented orthogonal factor in the literature; complements, doesn't overlap, the price-momentum legs. [DATA: WAVE4_FINDINGS §6] |
| **3** | **Receivables/DSO + unbilled/contract-assets + WC split** | Revenue-recognition forensic tells (currently UNBUILDABLE) | Directly feeds the same forensic lane as candidates #1-#2 — compounding EV. [DATA: WAVE4_FINDINGS §6] |
| **4** | **Concall OCR (264-name PDF set) + date-parse** | Management-credibility (bluff-detection) | Only a 139-name pilot exists (too thin/clustered); OCR turns a build-spec into a testable factor. Fix the P0 speaker-attribution regex bug first. [DATA: WAVE4_FINDINGS §4] |
| **5** | **Persist macro FRED enrichment + India 10Y G-sec** | Re-enable cross-asset / India-specific regime | LOW-MEDIUM: regime layer is the most data-starved, and the valuation scalar already failed in-sample. Do it mainly to stop the regime work resting on ephemeral scratch pulls (integrity fix). [DATA: WAVE4_FINDINGS §2, XASSET_ADVERSARIAL §0] |
| **6** | **Refresh delivery-% (stale 2024-06)** | H035 delivery-flow | Lowest — one parked signal, 13 months stale. [DATA: RESURRECTION §7] |

**Governance flag [DATA: XASSET_ADVERSARIAL §0]:** `macro_state.parquet` brent/dxy/real_rate/india10y are still 100% NaN and copper (PCOPPUSDM) + goldbees_ext lineage are NOT in DATA_CATALOG. Data-officer must persist + catalog before anything downstream depends on them (D-009/D-033).

**Pending items to fold in later (agents still running at write time):** the named MARKET_REGIME / MARKET_REGIME_MACRO / SECTOR_CONTEXT / DROPONE_ROBUSTNESS markdowns do not yet exist on disk — only `w4mkt_regime_results.json` (market richness index) landed. Fold their conclusions into §2-§3 when produced.

---

## 5. RECOMMENDED DECISION (what the Principal should do next, in order)
1. **Confirm the forward-test horizon and lock the no-peek rule.** The 7-leg freeze (banked as-of 2025-12-05) grades ONCE at ~Dec 2026. Do not touch the file (any edit voids it). This is the one gate compute cannot close — protect it above everything.
2. **Green-light a SEPARATE forward clock for the two new forensic legs (clean-surplus, depreciation-laxity)**, gated on the one cheap in-house guard first: drop-one / era-split + orthogonality re-confirm vs the frozen 7. Never merge into the freeze — it becomes a distinct 8/9-leg candidate on its own clock.
3. **Approve building the absolute-scorer "NOW" layer** (structure + order-preserving unit test + validated breadth+VIX sizing + SIGN-only valuation band + dual display + LOBO gate). Withhold magnitude→p_up calibration and coefficient fitting until forward data + IC memo. Valuation is SIGN-only, never a sizing dial (it lost to always-invested in-sample).
4. **Fund the top-2 data-asks (NSE SAST promoter-buying; analyst EPS-revision feed)** — the most new orthogonal edge per hour of home-network effort — and have the data-officer persist + catalog the copper/goldbees/FRED macro series (integrity fix).
5. **Park the momentum rescues and cross-asset sizing scalars** pending the orthogonality check (momentum) and +24 months of data (cross-asset); keep the two scalars as paper/shadow-tracked only. Size any future momentum exposure DOWN.

**Dissents recorded:** none at write time (single-author CIO package; running-agent regime/sector/dropone outputs to be folded in on arrival, may add caveats to §2-§3).
