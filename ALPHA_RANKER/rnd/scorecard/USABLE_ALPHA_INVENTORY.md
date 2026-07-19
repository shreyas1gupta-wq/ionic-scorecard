# USABLE ALPHA INVENTORY — ALPHA_RANKER Scorecard Reset (Step 1)

**Owner:** rnd-head-aditya-verma (E-011) · **Date:** 2026-07-18 · **Status:** consolidation only, NO new research.
**Mandate:** RESEARCH_QUEUE.md top block (SCORECARD RESET). Reduce the wave4/5/6 "spider-web" to the clean set of
already-found (and wrongly-rejected) alpha the two scorecards can actually use. Logic > statistics; FM lens on every item.

**Standing rule applied throughout (Principal, 3x):** significance alone (t/p/DSR/PBO/small-n) NEVER kills. Only
STRUCTURAL failure kills — leakage (fails lag/placebo), wrong/flipped sign, redundancy (corr>0.6–0.7 with an existing
leg), gross-return shortfall after realistic cost, flat/coin-flip, or a proven data artifact. Language: never "KILL (PBO)".

**FM lens applied throughout:** for each item, one line on whether the *economic* story would make a real PM size it —
flagging where stats look clean but the story is weak (probably spurious) and where the story is strong but the stats are thin (KEEP).

---

## (a) RELATIVE-SCORECARD-USABLE COMPONENTS

### A1. FROZEN — the validated 7-leg relative composite (DO NOT TOUCH)
**Status: FROZEN / forward-test (freeze pinned; grades ~Dec 2026).** Horizon: **1Y primary** (also the backbone the 1M/5Y
scorecards inherit quality/value/momentum from). Source: `rnd/cards/CANONICAL_7LEG_1Y.json`,
`rnd/cards/CANONICAL_7LEG_PIT_1Y.json`, `rnd/forward_test/FROZEN_SPEC.md`, `rnd/cards/W5V_base7_sanity.json`.

| # | Leg | Family | Economic WHY |
|---|---|---|---|
| 1 | **value_EY** (earnings yield) | Value | Cheapness premium; but standalone LS ≈ 0 in-sample — its edge historically leaned on a sector tilt (see A5) |
| 2 | **mom_resid_plain** (plain residual 12-1 momentum) | Momentum | FF-neutral trend persistence. **NOT mom_resid_peer** — that substitution was the wave5 root-cause bug |
| 3 | **MA-65 slope** | Trend | 65-DMA slope (less-gamed than 50); trend confirmation |
| 4 | **quality_QMJ** | Quality | Quality-minus-junk profitability/safety premium |
| 5 | **bs_issuance** (net-issuance) | Capital discipline | Firms that dilute under-perform; buyback discipline out-performs |
| 6 | **bs_asset_growth** | Capital discipline | Asset-growth anomaly — aggressive balance-sheet expansion under-performs |
| 7 | **quality_cfo_pat** (CFO/PAT) | Earnings quality | Cash-backing of accounting profit; accrual-quality tell |

- **Metrics:** IC_IR **1.345** (biased/survivorship universe) / **1.760** (PIT, survivorship-free). Both were flagged
  PARK/KILL on DSR/PBO but are KEPT (frozen) under the low-t rule. Reconciled honest edge: market-neutral LS **~12% CAGR /
  Sharpe ~0.8 / maxDD −38%**; realistic **forward IC ~0.11-class** (NOT the in-sample 1.35–1.76). Long-only 29–34% CAGR is a
  small/mid SIZE-TILT artifact, not the edge. [DATA: FINAL_MODEL §5a, DECISION_PACKAGE.md]
- **FM lens:** Textbook multi-factor sleeve — value + momentum + trend + quality + two capital-discipline legs + cash-quality.
  Every leg has an independent, well-documented economic rationale a PM would defend. This is the anchor; the reset builds around it, not over it.

### A2. CERTIFIED — oversold mean-reversion regime switch (rev5d)
**Status: research-CERTIFIED (Red-Team review recommended before live wiring); forward-watch.** Horizon: **1M** (short-horizon
reversal). Source: `rnd/wave4/REGIME_SPEC_V2.md` §0, `rnd/wave4/W5MR_CERT_results.json`, cards `W5MR_cert_*`.
- **Rule:** flip ON a 5-day reversal (`rev5d`) long-short **only** when breadth is washed out (≤20th expanding percentile of
  Nifty500 below 200DMA, ~17% of history); OFF everywhere else. `rsi2_factor` = confirm-only, never sized.
- **Metrics:** oversold IC lift **2.91x** (0.027→0.079); per-episode drop-one 0/12 failures; era-split holds directionally
  (disclosed GFC-era weak spot ~1.04x); breadth-threshold PLATEAU (10th/20th/30th all work); net-of-cost **survives 2x stress
  (+1.20%/active month)**; placebo/lag clean. DSR/PBO fail at n=42 — advisory only, disclosed small-sample degeneracy.
- **FM lens:** Real, sized-able. "Buy the washout" is a mechanism every discretionary PM knows; the certification is honest about
  its GFC-era softness and cost survival. rsi2 correctly demoted (fails 2x cost) — good discipline, not over-fitting.

### A3. FORWARD-WATCH — credit-market implied borrowing cost / convex hedge (W5-02)
**Status: forward-watch (convex-hedge candidate), NOT an IC leg.** Horizon: 1Y as an overlay/hedge, not a selection leg.
Source: WAVE4_FINDINGS §1-CORRECTION-2 + VERDICT RECLASSIFICATION; `hypotheses_w5.json` W5-02.
- **Logic:** interest / avg-borrowings (size+sector-residualized) imports the CREDIT market's view of a firm; convex via
  short-leg-blowup avoidance. Reclassified from "KILL" because the death was on robustness/significance, not structure.
- **Honest caveat:** thin and one-episode-heavy — COVID-crash month (Mar-2020) was NEGATIVE, 2022 was 4/7 months negative,
  unconditional IC sign-flips across halves (+0.050→−0.044). Crash-protective in ~2/3 windows only.
- **FM lens:** Story is strong (credit desks price default risk before equity does), stats are thin — exactly the "keep, don't
  discard" case. But size it as a *hedge/tail overlay* on a fresh forward clock, never as a return leg. Watch, don't deploy.

### A4. FORWARD-WATCH — clean-surplus / phantom-earnings (convex overlay)
**Status: forward-watch, CONVEX-OVERLAY candidate — NOT standalone-tradeable, NOT IC-additive.** Horizon: overlay across 1Y.
Source: WAVE4_FINDINGS §1, §1-CORRECTION, VERDICT RECLASSIFICATION; W4F-02.
- **Logic:** equity-channel earnings authenticity (does the change in equity reconcile to reported earnings?). Positive skew
  (+3.04) = tail-protective. Standalone mono ≈ 0.006 (untradeable alone); incremental to composite ≈ +0.009 (negligible after
  the base-7/date-match bug fixes).
- **FM lens:** Sound forensic logic, but it is a *quality/tail overlay*, not a selection leg — a PM would use it to veto/flag
  suspect names, not to rank. Correctly reclassified as a convex-overlay watch item, not resurrected as an alpha leg.

### A5. NOTE — sector-relative construction (design input, not a new leg)
**Status: design directive, not a standalone component.** Source: WAVE4_FINDINGS §2b, SECTOR_RELATIVE_REBUILD.md, memory #7.
- Blind sector weighting makes the composite monotonically WORSE (IC_IR 1.70 at 0% → 1.23 at 100% sector weight). BUT ~41% of the
  composite's historical edge was sector-TIMING and EY standalone LS ≈ 0 (the sector tilt did EY's work).
- **For the reset:** 5Y scorecard should blend sector-relative WITH absolute quality/growth/valuation merit (NOT blind
  neutralization) — a genuine high-ROE/high-growth/fair-value name earns absolute credit beyond its within-sector rank.
- **FM lens:** Correct PM instinct — don't neutralize away a real bet, but don't hide a sector-timing bet inside "stock selection" either.

---

## (b) ABSOLUTE-SCORECARD-USABLE INPUTS
Absolute scorer target: expected return = **expected-EPS-growth × PE-re-rating** (from current valuation + regime) → probability +
intensity, long-only, CAGR + Calmar. Source: RESEARCH_QUEUE spec, REGIME_SPEC_V2.md, ABSOLUTE_SCORER_SPEC.md.

### B1. EPS-growth / earnings-inflection input — 5Y conditional inflection
**Status: forward-watch (KEEP per low-t rule).** Horizon: **5Y.** Source: `rnd/wave4/W5IN_battery_results.json` variant
`W5IN_cond_noqual` (5Y).
- **Metrics:** IC_IR **0.397**, mono **0.358**, ann LS **+20.1%**, era-split BOTH halves positive (0.42 pre / 0.395 post),
  drop-one sector 0 flips / drop-one year 0 flips, lag clean (0.006), placebo clean (−0.007), skew **+1.74** (convex, right-tailed).
  Harness said "KILL" on PBO 0.853 / DSR only — pure significance, no structural failure → KEEP.
- **Caveat:** the RAW unconditional suppression variant (`W5IN_supp_raw`) is structurally BAD at 1Y (lag_test_delta 3.42 =
  leakage, negative IC) — use ONLY the conditional 5Y variant. The full-quality-gated variant (`cond_full`) is weaker (IC_IR 0.105,
  post-era negative).
- **FM lens:** Strong story (investment-suppressed earnings pre-inflection → 5Y re-rating, conditional on it not being the raw
  asset-growth anomaly), clean robustness, convex payoff, thin only on DSR. A long-horizon PM would size this. Best genuine 5Y input this program found.

### B2. Valuation / PE-re-rating input — broad-market richness band (sign-only)
**Status: usable as a SIGN-ONLY / slow-tilt input; NOT a monthly lever.** Horizon: **5Y primary, 1Y secondary.**
Source: REGIME_SPEC_V2 layers C/D, MARKET_REGIME.md, BROAD_MARKET_VALUATION.md, memory alpha-ranker-valuation-band.
- Principal's **0-65 / 65-160 / 160+** band is the sole market gauge (sign-only). ρ(richness, fwd-1Y) ≈ −0.30; fwd-5Y direction
  robust (cheap → positive, strengthens 5Y ex-2008). Drop Buffett indicator. Momentum GATED OFF at both valuation tails
  (undervalued-extreme <65 and overvalued-extreme ≥160).
- **Empirical gap (disclosed):** ≥160 band has NEVER printed in 21yr India (max ~122–139); the ≥160 rules are precautionary /
  economic-logic only. Monthly valuation-scalar backtest was flat-to-negative (driven by 2008) → NOT a tactical monthly dial.
- **FM lens:** Cheap markets pay better over 5Y — sound and every allocator uses it. Correctly demoted from a monthly timing tool
  to a slow directional prior. The 160+ rule is honest speculation, labeled as such.

### B3. Regime-conditional sizing — breadth extremes (VIX dropped)
**Status: usable as the de-risk/sizing conditioner; layer-E-as-exposure-scalar not yet separately backtested (flagged).**
Horizon: tactical (feeds absolute gross-exposure). Source: REGIME_SPEC_V2 layers A/B/E, RESEARCH_QUEUE batch-3.
- Fire the sizing/de-risk trigger ONLY at breadth TAILS — washout (>~30% of Nifty500 below 200DMA) or froth (<~5% below
  50/200DMA); breadth does nothing in the middle. VIX = noise, down-weighted. Momentum lookback by regime: 12m in bull/normal,
  SUPPRESS entirely in bear-oversold. Overbought-in-recovery = hold/ride, NOT fade (only fade froth in a sustained uptrend).
- **FM lens:** "Only act at extremes" is exactly how a risk-aware PM uses breadth; dropping VIX-as-signal is correct (mostly noise
  in India). The breadth-as-exposure-scalar use is a sensible design placeholder but is explicitly un-backtested — do not present as certified.

### B4. Gold/cash crisis state (absolute default safe asset)
**Status: PRECAUTIONARY / economic-logic only — never fired, cannot be backtested.** Horizon: crisis/tail. Source: REGIME_SPEC_V2
layer F, RESEARCH_QUEUE gold/cash de-risk directive.
- At richness ≥160 OR a co-crash state (cross-sectional leg correlations converge to 1, relative selection stops protecting) →
  de-gross equities, route to GOLD/CASH via the ETF sleeve. Cash = default safe asset, gold = crisis hedge.
- **FM lens:** The one thing relative stock-picking CANNOT do is protect when everything falls together — only asset allocation can.
  Economically airtight, empirically untested (never triggered in 21yr). Ship as a watched precautionary rule, labeled untested.

---

## (c) CONTEXT / OVERLAY LAYER (analyst + forensic) — gates raw scores, NOT standalone alpha
These do not rank or generate return; they REINTERPRET and VETO raw scores before a verdict. Source: `rnd/analyst_layer/`,
`rnd/forensic/`.

### C1. Analyst contextualization layer
- `analyst_layer/CONTEXT_VERDICT_FRAMEWORK.md` + `sector_norms.json` (21 macro-sectors, n≥5) + `edge_case_playbook.md`.
- **Function:** a raw score is a *lead, not a verdict*. Sector-norm benchmarks stop false flags (e.g. KPIGREEN solar EPC: very
  negative `bs_asset_growth` leg = high raw capex growth = NORMAL for a committed-order-book build-out, not "value-destroying
  growth"; low CFO/PAT is structurally normal for EPC/Realty/BFSI). Edge-case playbook covers capex build-out, turnaround,
  cyclical trough, high-growth-dilutive.
- **Plug-in point:** sits between the scoring engine and any human/agent verdict — the scorecard emits a raw score, this layer
  sector-conditions it before it becomes a call.
- **FM lens:** This IS fund-manager wisdom encoded — exactly the "would a PM read this score the same way in this sector?" filter
  the Principal asked for. Essential glue, not alpha.

### C2. Forensic red-flag layer
- `forensic/FORENSIC_FRAMEWORK_CA.md` (32-item CA-grade taxonomy: 11 HARD-VETO, HEAVY-PENALTY, WATCH-FLAG tiers) +
  `FRAUD_CASE_LIBRARY.md` (15 named Indian cases) + `forensic_checklist.json` + live scorer `results/universe_forensic_score.parquet`
  (751 names, 0-100 badness) / `universe_forensic_flags.parquet` (14,269 rows).
- **Function:** hard-veto / penalty GATE on the long side (siphoning, phantom cash, stale CWIP, related-party loans, etc.). Mostly
  FILING-READ-ONLY (analyst reading work at deep-dive), a narrow slice DATA-SCREENABLE now.
- **Plug-in point:** a veto/penalty overlay on the absolute (long-only) scorecard's shortlist — caps or removes a name regardless
  of how well it scores.
- **FM lens:** No PM buys a high-scoring name that fails a fraud check. Correct role = downside gate, never a return source.

---

## (d) EXCLUDED / DEAD — with the REAL structural reason (not a bare stat)

| Item | Real structural reason (verified) |
|---|---|
| **Plain PEAD** | Flat/no-effect — IC ≈ −0.003 unconditionally AND dead in every regime with adequate n (CHOPPY −0.003 n=655; OTHER −0.006 n=1966). Genuinely dead in India, not a power problem. [REGIME_SPEC_V2 §1-G] |
| **Momentum-rescue variants** (beta-adj-mom, vol-scaled-mom, MA-slope-as-8th-leg) | REDUNDANT with the existing momentum/trend legs (drop-one v2: HURT the composite −0.05 to −0.17 incremental), era-fragile (2021-26-cube-only, same bug class as H046/H009), collapse to ~1 crowded bet (null-sweep), and ~76-78% of the short leg is UNBORROWABLE in India (gross-shortfall on the short side). Standalone abs-return was real but as *additions* they fail. Stop testing momentum variants. [RESEARCH_QUEUE batch-2, WAVE4_FINDINGS §1-CORRECTION] |
| **W5-01 cost-elasticity** | WRONG/FLIPPED sign on the correct base-7 (reported +0.396 → true −0.069), drop-one 21/21 negative = artifact. [WAVE4_FINDINGS §1-CORRECTION-2] |
| **Distress composite** | Sign-UNSTABLE across horizons (flips 1Y/5Y), hurts book (IR −0.44). [WAVE4_FINDINGS §1] |
| **Cyclical normalized-EY** | Loses to the incumbent it aimed to beat (0.23 vs TTM-EY 0.42 in cyclicals). [WAVE4_FINDINGS §1] |
| **Net Operating Assets (NOA)** | Zero incremental — orthogonal (corr −0.01) but adds nothing to composite (1.34→1.29). [WAVE4_FINDINGS §1] |
| **Momentum-within-quality double-sort** | Structural — forced gating hurts; rank-avg beats it 2.7x, monotonicity collapses. [WAVE4_FINDINGS §1] |
| **Downside-capture ratio (DCR)** | REDUNDANT with BAB at 3m/6m + the convexity was a 2006-12 DATA ARTIFACT. (Queued item DID run — card `rnd/cards/W6DC_dcr_3m_1M.json`.) [WAVE4_FINDINGS reclassification, structurally-dead list] |
| **W5-05 treasury-bloat / W5-08 moat-proxy** | INVERTED sign. [WAVE4_FINDINGS reclassification] |
| **Depreciation-policy laxity (W4F-01)** | Was reported +0.066 lift; on the corrected base-7 it HURTS (−0.053), fails drop-one as an addition. Real accounting-choice logic but not IC-additive. [WAVE4_FINDINGS §1-CORRECTION] |
| **Cross-asset sizing (copper/gold, gold-vs-equity)** | PARK-needs-more-data, not dead: beat VIX/breadth on Sharpe/maxDD and survived era-split + leave-one-bear-out, but only ~5 bears (n≈114 months) — do not start a live sizing sleeve on it. (Distinct from the gold/cash *allocation* state B4.) [WAVE4_FINDINGS §2] |

---

## NEEDS VERIFICATION (flagged, not asserted)

1. **Promoter-drift IC_IR 1.33 provenance.** Cited as "validated IC_IR 1.33" only in WAVE4_FINDINGS §6 data-asks and the
   RESEARCH_QUEUE F1 mandate line — I did NOT find a backing card/battery on disk for the 1.33 figure. It is DATA-BLOCKED regardless
   (needs fresh NSE shareholding/SAST + pledge data, D-009/D-033 gate). Treat as a **data-ask, not a usable signal**; confirm the 1.33
   source before quoting it as validated. It is also NOT in the formal VERDICT RECLASSIFICATION list (that list names only W5-02 +
   clean-surplus) — it and the 5Y inflection were pulled to forward-watch via the queue mandate, not that section.
2. **clean-surplus "real IC 0.68".** The reclassification line states "real IC 0.68 + skew +3.04" — an IC of 0.68 is implausibly high
   for a cross-sectional factor (ICs here run ~0.01-0.19). Standalone mono is 0.006 and incremental ≈ +0.009, consistent with a weak
   overlay. The "0.68" is likely a different metric (rank-corr on a sub-sample, or a typo). Does not change the verdict (convex overlay,
   not a leg) but the 0.68 number should not be quoted until reconciled.
3. **`SECTOR_BIAS_AUDIT.md` existence.** The analyst layer flags it as referenced-but-missing; the grep shows a file now exists at
   `rnd/wave4/SECTOR_BIAS_AUDIT.md`. Minor — the sector-relative conclusion (A5) is independently supported by SECTOR_RELATIVE_REBUILD.md
   cards, so this doesn't block anything, but the two docs should be reconciled by quant-head.
4. **W5-02 internal tension (documented, not an error).** §1-CORRECTION-2 calls W5-02 "DEAD"; the later Principal-directed VERDICT
   RECLASSIFICATION pulls it to forward-watch. I carried it as forward-watch (the later, rule-consistent word) with the honest thinness
   caveat. The sign-flip across halves is borderline-structural — flag for Red Team if it is ever proposed for live wiring.
