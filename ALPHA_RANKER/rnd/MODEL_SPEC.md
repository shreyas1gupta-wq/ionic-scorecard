# ALPHA_RANKER — MODEL_SPEC (repeatable, regime-aware, NON-fixed −100..+100 scores)

> Architect: Arjun Rao (Quant). Status: DESIGN-FROZEN candidate, **NOT production**. Nothing here enters
> `weights/` until the OPEN ITEMS (§5) close and the IC memo passes (CIO+FM). This spec supersedes the
> illustrative 7-theme priors in `02_SCORING_ENGINE.md` where empirics contradict them — the design skeleton
> (normalize → theme → regime-weight → cascade → forensic → calibrate → [-100,100]) is kept; the *content*
> (which factors, which weights, how weights flex) is now evidence-driven from the 21-yr consolidation.
>
> Governing principle (learned, not assumed): **combine confirmed durable factors by SIMPLE RANK-AVERAGE**,
> flex the blend by **CONTINUOUS regime probability** (never a discrete switch), and **carry only the legs
> that are regime-right**. ML/ridge/forced-interactions overfit our sample and are banned from the combiner.
> Tags throughout: [DATA] = measured on our panels; [INFERENCE] = reasoned design; [OPINION] = my call.

---

## 0. What is CONFIRMED durable (the only inputs allowed into the blend)
[DATA] Cross-regime (2008/2011/2020 bears on `panel_long.parquet`, lag+placebo clean):

| Factor (leg) | Horizon evidence | IC_IR | Regime character |
|---|---|---|---|
| Residual momentum 12-1, FF-neutral, **sub-sector peer-relative** | 1Y core; 5Y resid-mom 0.60 | 1Y 0.92 | wins bull/calm/low-vol; **crashes in bear** (ic_bear −0.02..−0.06) |
| **65d MA-slope** trend (slope > stack > distance OOS) | 1Y; degrades but positive 5Y (0.41, bear-tilted) | 1Y ~0.72–0.95 | wins trend-up/low-vol; holds better than momentum in bear |
| **Earnings yield (cross-sector, plain)** — the value workhorse | 1Y 1.52; 5Y 2.09 | 1Y 1.52 | **higher IC in bear** (0.156 vs 0.042 bull); the defensive anchor |
| **Market-state tier-value EY** (M3: EY vs own history × cap-tier) | 5Y only | 5Y **2.34** | 5Y valuation-timing layer; best in bear |
| Small-cap-tier EY (relative cap-tier value) | 1Y/5Y | 1Y ~0.63 | bear-tilted (ic_bear 0.107) |

[DATA] **BULL-ONLY ARTIFACTS — excluded**: Weinstein stage-2 (neg 5Y on 21-yr), vol-scaled momentum (mono
0.99→0.07 at 5Y), ridge-learned composites (IC_IR ~0 or negative OOS at 1Y/5Y). [DATA] **TRAPS — excluded**:
raw growth CAGR (negative), short-term reversal (killed), quality-standalone (−0.83 IC_IR 1Y in this
junk-bull — retained ONLY as a regime leg, see §2), low-vol/size standalone (deeply negative 1Y here).

---

## 1. Factor set per horizon (theme buckets, rank-averaged within a live blend)

**1M — thin & honest.** [DATA] Only cross-sectional momentum/technical carry (resid-mom IC_IR ~0.30, hit
~0.81); MA-slope exists but the 65d trend is **not tradeable at a 1M horizon** (signal turns slower than the
holding period). Value at 1M is weak (EY IC_IR 0.39 but net_LS ~0.06). Catalyst/flow themes are DESIGNED
(02/03) but **have no confirmed leg yet** (PEAD needs event-time daily; FII/DII/promoter drift untested).
→ **1M blend = {residual momentum (primary), short-horizon trend/RS (secondary)}.** Label it explicitly
LOW-CONVICTION / THIN in the output; do not manufacture Sentiment/Catalyst weight we haven't earned.

**1Y — the real model.** [DATA] Best-populated, most survivors.
→ **1Y blend = {sub-sector peer-relative residual momentum, 65d MA-slope trend, cross-sector EY (value),
small-cap-tier EY}**, rank-averaged, regime-weighted per §2. Quality enters ONLY as a bear/junk-bull-off leg.

**5Y — value + quality + market-state; growth-gated.** [DATA] Momentum decays (resid-mom 0.60), MA-slope
weak-but-bear-positive; value dominates (EY 2.09), and the **market-state tier-value EY (2.34) is the
strongest 5Y signal we have**. [INFERENCE] Growth is NOT additive raw (trap) — it enters only as a *gate*
(exclude value-traps: cheap + deteriorating fundamentals), never as positive weight.
→ **5Y blend = {market-state tier-value EY (primary), cross-sector EY, residual momentum (small), quality
(regime leg)}**, growth used as a value-trap exclusion filter. **Caveat [DATA]: 5Y is under-determined** —
PIT fundamentals thin pre-2012, only 3/61 bear months in the short panel; 5Y ships as INDICATIVE, not sized.

---

## 2. The regime-weight mechanism — CONTINUOUS, non-fixed, repeatable

[INFERENCE] The naive discrete regime SWITCH does not beat holding momentum (doubles turnover, eats the
edge). Replace it with a **continuous regime-probability overlay** that preserves magnitude and flexes the
rank-average blend smoothly.

**Regime probability (causal, lookahead-free), computed at date t from data ≤ t:**
- `p_bear(t)` from the National/market axis (02 Step-4 / 03 L-N): trend (price vs 65/200 DMA slope, breadth),
  vol (India-VIX pct, realized vol), and market EY-vs-bond-yield. Continuous in [0,1] via a logistic on those
  standardized inputs (rules-based v1; HMM/vol-state upgrade later — OPEN ITEM). Symmetric `p_bull = 1 − p_bear`.

**Continuous theme weight (the NON-FIXED core):**
```
w_theme(t) = w0_theme + p_bear(t) · Δ_theme            # linear tilt in regime probability
then renormalize the surviving legs to sum 1 (drop-regime-wrong-legs, below), so weights are
never hand-fixed — they are a deterministic FUNCTION of the live regime probability.
```
Signed tilts `Δ_theme` (direction is [DATA]-confirmed; magnitude is a prior to be calibrated — OPEN ITEM):

| Theme | base w0 (calm) | Δ per unit p_bear | Rationale |
|---|---|---|---|
| Momentum (resid, peer-rel) | high | **strongly negative** | momentum crashes in bear (ic_bear<0) — down-weight toward 0 |
| Trend (65d slope) | high | mildly negative | holds better than momentum but still a trend leg |
| Value (cross-sector EY) | moderate | **strongly positive** | higher IC in bear — the defensive workhorse |
| Quality | ~0 in bull | **positive** | inverted in junk-bull (mono −0.9); expected to normalize +ve in bear |
| Low-vol / low-beta | ~0 | positive | flight-to-quality legs, bear-only |

**DROP-REGIME-WRONG-LEGS rule** [INFERENCE, from consolidation]: when a leg's regime-conditional IC is the
wrong sign for the *current* `p_regime`, its weight floors at 0 (not negative) before renormalization — we do
not short a factor we merely don't trust; we stop leaning on it. This is what keeps turnover low vs a switch.

**Turnover control:** rank-band hysteresis (b≈10%) on the final composite rank, per the volmom rank-band
survivors — keeps net-of-cost positive. All legs scored on **residual (market/FF-neutral) return**, so we
never reward closet beta/size.

---

## 3. Score → [−100, +100] (cross-sectional rank → signed conviction; calibration attaches LATER)

**Production-now (rank-only, honest):**
```
composite_i(t) = Σ_legs w_leg(t) · rank_pct_leg_i(t)      # rank_pct in [0,1], sub-sector/size peer set
score_i = round( 200 · (rank_pct(composite_i) − 0.5) )    # cross-sectional, symmetric, clipped [-100,100]
```
This is repeatable and needs zero fitted parameters — a stock at the top of the cross-section today scores
near +100, bottom near −100, and the mapping is identical every run. Conviction is RELATIVE (the model's
honest claim), not an absolute return promise.

**Calibration attaches later (02 Steps 7–8, deferred — OPEN ITEM):** once per-(horizon×coarse-regime)
isotonic/Platt calibrators are fit on the PIT backtest, replace the rank map with
`p_up = calibrator(composite)`, then `p_up_adjusted = 0.5 + (p_up−0.5)·squash(|E[r]|/typical_move)` and
`score = 200·(p_up_adjusted − 0.5)`. Until calibrated, ship the rank score and label probability/E[return]
as NOT YET AVAILABLE — do not fabricate a win-rate.

---

## 4. Composition order (forensic penalty · oversight cascade · market-state overlay)

[INFERENCE] Compose in this fixed order so each layer sees the prior layer's output:
```
1. composite       = regime-weighted rank-average of surviving legs        (§2, §3)
2. + cascade_shift  = oversight cascade (03): global→national→sector tailwind/headwind,
                      scale[horizon] (max at 1M–1Y, min at 5Y EXCEPT structural headwinds
                      which bite at 5Y). Sector headwind can CAP the band; override → overrides[].
3. + market-state   = the 5Y tier-value EY overlay (M3) is folded in as the VALUE leg's
                      regime input at 5Y (market cheap/expensive vs own history × cap-tier),
                      not a separate add — it IS how p_regime enters the 5Y value weight.
4. − forensic       = penalty = Σ severity·size_mult·regime_mult (02 Step-6), applied LAST and
                      NONLINEAR; hard-veto flags cap score ≤ HARD_CAP regardless of composite.
5. cross-horizon tax: large-negative 1M taxes 5Y/1Y (bad entry timing); never the reverse.
```
[OPINION] Forensic must be last and subtractive — a great factor stack must never out-vote an auditor
resignation or covenant breach. The cascade shifts, the market-state sets the value weight, forensic vetoes.

---

## 5. OPEN ITEMS blocking production (+ the IC-memo gate)

**TOP 3 (hard blockers):**
1. **DSR-per-family fix + re-score.** [DATA] Current DSR uses a GLOBAL ~300+ cross-family trial count →
   crushes every factor to ~0; PBO is structurally saturated (~1.0) on our monthly, overlapping, few-block
   sample. Both are currently ADVISORY-only, which is NOT good enough to certify. Must recompute DSR with a
   **per-independent-family trial count** (and signed IC_IR in `verdict()`, which currently auto-kills
   correct-sign negative factors like value/low-vol/quality-in-bear). Until this, no honest significance claim.
2. **Continuous-overlay live test on the 21-yr panel.** §2's `w_theme(p_bear)` is DESIGNED but the
   magnitude-preserving overlay has NOT been run end-to-end across the plentiful-bear 21-yr sample vs the
   momentum-hold baseline. Must beat hold net-of-turnover, or the regime machinery is cosmetic.
3. **5Y data thinness + probability calibration.** 5Y rests on pre-2012-thin PIT fundamentals and 3/61 bear
   months; the score→p_up/E[return] calibrators (§3) are unbuilt. 5Y ships INDICATIVE until deepened; no 5Y
   sizing and no win-rate output until calibrated.

**Also pending:** event-time (daily) PEAD + FII/DII/promoter drift to give 1M a real Catalyst/Flow leg;
quality-in-bear confirmation on the next bear (currently inferred, not yet observed positive on hold-out);
HMM regime classifier to replace the rules-based `p_bear`.

**IC-MEMO GATE (adoption, per RESEARCH_PROTOCOL §4 + CONSOLIDATION §adoption):** nothing in this spec enters
`weights/` until — (a) OOS-survivor status on the untouched hold-out, (b) DSR-per-family recompute clears,
(c) red-team pass (placebo/shuffle/incremental-vs-base-beta shuffle BEFORE the memo), (d) an IC memo with
CIO+FM joint sign-off. The §0 durable set is the CANDIDATE list for that memo — pending items 1–2 above.
Do NOT deploy on in-sample shine.
