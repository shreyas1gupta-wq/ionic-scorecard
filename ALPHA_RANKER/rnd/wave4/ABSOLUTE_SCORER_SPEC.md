# ABSOLUTE CONVICTION SCORER — SPEC (design only, not built)
Author: Arjun Rao (Head of Quant, E-004). 2026-07-17. Status: BLUEPRINT for a Principal architecture decision.
Governs against: `rnd/CONSOLIDATION.md` §3 (return-blend REJECTED), `rnd/FINAL_MODEL.md` §3/§5,
`02_SCORING_ENGINE.md`, `06_FRAMEWORK_5Y.md`, `rnd/forward_test/FROZEN_SPEC.md`, `rnd/wave4/MEMO_CRAFT.md`.
Tags: [DATA]=on-record fact, [INFERENCE]=my construction, [OPINION]=my judgment.

---

## 0. RECOMMENDATION (read first): KEEP BOTH, COMPOSE — do NOT replace

**[OPINION]** Keep the RELATIVE (rank) scorer as the SELECTION engine, unchanged, and add the ABSOLUTE
scorer as a thin regime/sector transform ON TOP of it. Do not replace relative with absolute. Three reasons:

1. **Relative is the only robust thing we have.** The 7-leg composite is validated *cross-sectionally* —
   its edge (IC_IR 1.76 PIT, monotone deciles, lag/placebo clean) comes precisely from being within-date,
   which cancels the common market factor. [DATA: FINAL_MODEL §5-RISKOFFICE] Replacing it with an absolute
   score would throw away the robust axis and lean the whole product on the market-regime layer, which is
   the *most* data-starved thing in the building (~5 independent bears vs a ~13yr cross-section).
2. **A rank structurally cannot answer the Principal's question.** `score = 200·(rank_pct − 0.5)` is
   zero-sum: it always crowns a #1 at +100, even in March 2008. It says WHAT to own relative to peers; it
   is *silent* on whether you should own anything at all. The absolute score exists to answer "is this a
   good time to own even the best names, and in which direction" — a question the rank cannot express.
3. **Composition can be made order-preserving**, so the absolute layer *cannot* corrupt the validated
   selection (see §1 invariant). That is the exact property the failed return-blend overlay lacked — it
   re-ordered the cross-section and diluted the decile spread [DATA: CONSOLIDATION §3]. This design changes
   only the common LEVEL and SCALE, never the within-date ordering.

Net: the Principal gets two orthogonal statements per name — **relative rank = what to own** (trustworthy
today, pending forward grade) and **absolute conviction = how much / which direction overall** (sign+sizing
trustworthy, magnitude provisional until forward data).

---

## 1. THE COMPOSITION FORMULA (sign + exposure-scalar on the rank — NOT a return-blend)

Notation, per horizon `h ∈ {1M, 1Y, 5Y}`:
- `r_h` = the RELATIVE score, unchanged: `200·(rank_pct(composite_h) − 0.5) ∈ [−100,+100]`. SELECTION axis, centred at 0.
- `M ∈ (−1,+1)` = **market valuation level**, SOFT band. From a Shiller/Buffett-class market series (market-cap/GDP,
  or Nifty CAPE / earnings-yield-gap vs its own long history), mapped smoothly:
  `M = tanh( (v_fair − v) / w )`, where `v` is the current band reading, `v_fair ≈ 100` (fair), `w` = softness width.
  Cheap (v≈60–70) → M>0; fair (100) → M≈0; crash-risk (v≥160) → M strongly negative. **No hard cutoffs — tanh, by design.**
- `T_sec ∈ (−1,+1)` = **sector tailwind/headwind**, same tanh construction at the sector level (sector valuation-band
  position + sector trend/breadth relative to market).
- `s_mkt ∈ [0,1]` = **market EXPOSURE scalar** — the ALREADY-VALIDATED %>200DMA-breadth × India-VIX-regime scalar
  (maxDD −52%→−26%) [DATA: FINAL_MODEL §3, §5a]. This is the "size down in danger" dial.

**Composition:**
```
absolute_h = clip(  α_h·(100·M)  +  β_h·(100·T_sec)  +  s_mkt · r_h ,  −100, +100 )
```
- `α_h·100·M`  = additive MARKET-LEVEL shift → can drive the WHOLE cross-section negative in a dangerous market. THIS sets sign.
- `β_h·100·T_sec` = additive SECTOR tilt.
- `s_mkt · r_h` = the relative selection score, COMPRESSED toward 0 in high-vol/thin-breadth (identical scalar for every name).
- `α_h, β_h` are horizon constants **pre-set from economic priors, not fitted** (see §3 for the horizon profile).

**The guardrail invariant (this is what makes it not-a-blend):** at any fixed regime `(M, T_sec, s_mkt)`, `absolute_h`
is a strictly increasing affine function of `r_h`. Therefore `rank(absolute_h | regime) ≡ rank(r_h)` — **the
within-cross-section selection ordering is preserved exactly.** The absolute layer only sets the common level and
scale; it never reorders stocks, so it cannot recreate the decile-spread dilution that killed the return-blend overlay.
This is enforced as a **unit test**: assert `argsort(absolute) == argsort(r)` whenever regime inputs are held constant.
Any proposed variant that fails this test IS a return-blend and is rejected by construction.

**Can the whole score go negative for a good stock in a dangerous market? YES — by design, and mostly at 5Y.**
A #1 relative pick has `r ≈ +100`; in a 160+ crash-risk market `M ≈ −1`. At 5Y (`α_5Y` meaningful, `s_mkt`
compressed) the additive `α_5Y·(−100)` term overwhelms the compressed `s_mkt·100`, so absolute lands negative:
"best house on a street that's on fire." At 1Y the drag is modest; at 1M (`α_1M≈0`) it is essentially absent —
correct, because valuation does not predict 1-month returns.

---

## 2. CALIBRATION PATH — brutal honesty on what's real vs provisional

The absolute score is a NUMBER on [−100,+100]. The temptation is to publish `p_up = 73%, E[ret] = +11%`.
**We must not, yet.** Any score→probability map fit on our history inherits the DSR≈0 / PBO≈0.92
multiple-testing verdict [DATA: FROZEN_SPEC §0; FINAL_MODEL §5-RISKOFFICE]. Calibration is DEFERRED [DATA:
FROZEN_SPEC §6, Principal instruction].

**Target mapping (once data exists):** `p_up = calibrator_[h, coarse-regime](absolute_h)` (isotonic/Platt),
`win_rate` = realized hit-rate of the historical bucket, `E[ret], p10–p90` = that bucket's forward-return
distribution [DATA: 02_SCORING_ENGINE §7, 11_BACKTEST_CALIBRATION]. Zero free parameters — it reads off
bucketed forward returns.

**What is trustworthy NOW (buildable, no forward data, no new fitting):**
- **STRUCTURE** — the formula, the order-preserving invariant, the dual display.
- **SIGN** — direction of `M` (cheap→+, crash→−) and of `r` (the validated composite) are both economically
  grounded and directionally defensible without a fitted magnitude.
- **SIZING** — `s_mkt` is validated independently on maxDD/Sharpe [DATA: FINAL_MODEL §5a]; it needs no score
  calibration to be trusted as an exposure dial.

**What WAITS for forward data (wide error bars until then):**
- **MAGNITUDE → probability.** No `p_up` as a false-precise %. Until the frozen forward test grades
  (~Dec 2026, IC expected ~0.11-class, decayed) [DATA: FROZEN_SPEC §5], `p_up` may appear ONLY as a coarse
  band (strong-neg / neg / neutral / pos / strong-pos) carrying an explicit **"magnitude provisional"** flag,
  or as a historical decile hit-rate at the decayed ~0.11 IC with visible wide bands — never a fitted per-score number.
- **The numeric constants** `α_h, β_h, w, v_fair` beyond their economic-prior seed values.
- **Promotion of the market-regime term** from PROVISIONAL-sign to calibrated-magnitude.

**[OPINION]** State this in the product itself, per MEMO_CRAFT §3: a ±80 reads as "top-position-sized idea IF
you had a book," not "80% certain." The magnitude is a position-sizing instruction with wide bars, not a probability.

---

## 3. HORIZON HANDLING — the band is a 5Y predictor, so weight it by horizon

The market-valuation band predicts returns through SLOW mean-reversion (multi-year half-life). Forcing it into
short horizons overstates it. `s_mkt` (a vol/risk conditioner, not a return predictor) is legitimate at ALL horizons.

| Horizon | `α_h` (market level) | `β_h` (sector) | `s_mkt` sizing | Rationale |
|---|---|---|---|---|
| **1M** | ≈ 0 (pinned) | ≈ 0 | ON | Valuation does not predict 1M. `absolute_1M ≈ s_mkt·r_1M` — risk-scaled selection only. Matches FINAL_MODEL "1M is thin/low-conviction". |
| **1Y** | small (~0.2–0.3) | small (~0.1) | ON | Valuation weakly conditions 1Y; the honest model is 1Y and the drag must stay modest. |
| **5Y** | meaningful (~0.5–0.7) | moderate (~0.2–0.3) | ON | This is where the band earns its keep [DATA: 06_FRAMEWORK_5Y §scoring — entry valuation regime-sensitive]. |

`α_h, β_h` are **monotone increasing in horizon and pinned by prior, not fitted.** `α_1M≈0` is a design
constraint, not a search result. Consequence: the same stock can read a compressed-but-positive 1M absolute,
a modestly-dragged 1Y, and a deeply-negative 5Y in a 160+ market — which is the honest cross-horizon picture,
not a contradiction. (Cross-horizon tax from 02_SCORING §9 — a large-negative 1M taxing 5Y entry timing — is a
separate, compatible overlay, kept small.)

---

## 4. FAILURE MODES / ANTI-OVERFIT

1. **Return-blend relapse (the known landmine).** GUARD = the §1 order-preservation invariant + its unit test.
   If a variant reorders the cross-section at fixed regime, it is a blend → auto-reject. The failed overlay
   diluted the decile spread by re-ranking; this design provably cannot [DATA: CONSOLIDATION §3].
2. **Overfitting the ~5 crashes (the bigger risk — market regime is MORE data-starved than the cross-section).**
   - Coefficients PRE-SET from economic priors, never fitted to maximize a backtest.
   - SOFT continuous band (`tanh`), never per-crash dummy indicators (that memorizes 2008/2020).
   - CAP the `|α_h·M|` contribution so one regime read cannot single-handedly dominate the score.
   - **Leave-one-bear-out sensitivity is mandatory** before the market term ships: drop each bear (2008/2011/
     2020/2018/2022), re-check sign stability. If it flips dropping any one bear, it does NOT ship — same bar
     the copper/gold sizing candidate had to clear [DATA: WAVE4_FINDINGS §2].
   - The market term is PROVISIONAL-SIGN only until the forward test; it never gets a calibrated magnitude on
     in-sample data.
3. **Keep the regime layer THIN.** Two inputs only: the soft valuation band + the already-validated breadth/VIX
   scalar. No new fitted market-timing model, no HMM, no macro kitchen-sink. Every input added is another trial.
4. **One-directional.** The absolute layer NEVER feeds back into the relative engine — the selection composite
   stays frozen (FROZEN_SPEC hash intact). Absolute is a read-only downstream transform.
5. **Two documented data-starvation levels:** cross-section (~13yr fundamentals) and market regime (~5 bears).
   The market layer is the more fragile → it gets the smaller coefficients AND the loudest provisional flag.

---

## 5. PRESENTATION TO THE PRINCIPAL (dual score + ranked falsification, per MEMO_CRAFT)

Every name ships with BOTH scores and the decomposition that reconciles them:
- **Relative rank** (trustworthy selection): "#7 / 802, top decile."
- **Absolute conviction** (sign+sizing trustworthy, magnitude provisional): e.g. in a rich market
  "**−12 (market-regime-capped)** — a top-decile pick, but the valuation band is at 155 (crash-risk), so overall
  conviction is negative." vs a cheap market "**+58 (positive, magnitude provisional)**."
- **Additive decomposition** (SHAP-style, mandatory per 02_SCORING §Explainability): show
  `absolute = s_mkt·r  (selection, +X)  −  α_h·market_drag (−Y)  +  β_h·sector_tilt (±Z)` so the Principal SEES
  why absolute < relative.
- **P(up):** coarse band + "magnitude provisional" flag — never a false-precise %.
- **Ladder-stage** (MEMO_CRAFT §3): initial-stage (score capped) vs confirmed-stage (full range).
- **Ranked falsification clause** (MEMO_CRAFT §1, MANDATORY, same paragraph as the thesis): what breaks this,
  fastest-acting first — (1) fundamental deterioration, (2) capital-allocation red flag, (3) valuation — PLUS a
  market-regime line: "if the valuation band breaks above `v_crash`, the absolute layer flips negative regardless
  of the name." This makes the market-level assumption itself falsifiable and visible.

---

## 6. BUILD ORDER

**NOW (no forward data, no new fitting, no Principal sign-off beyond this spec's approval):**
1. Formula skeleton (§1) + the order-preservation unit test.
2. Wire `s_mkt` (already validated) as the multiplicative compressor.
3. Soft valuation band `M` from an existing market-valuation series (data-officer confirms on-disk / pulls
   market-cap-to-GDP or Nifty EY-gap; D-009 gate) — SIGN only, coefficients as economic-prior constants.
4. Sector tilt `T_sec` from the panel's own sector column + sector breadth.
5. Presentation layer: dual display + additive decomposition + provisional `p_up` band + ranked falsification.
6. Leave-one-bear-out sensitivity on the market term (§4.2) — gate before it ships.

**WAITS (forward data + Principal sign-off + IC memo CIO+FM):**
1. Calibration of magnitude → `p_up / E[ret] / win_rate` — needs the frozen forward grade (~Dec 2026) + more bears.
2. Any tuning of `α_h, β_h, w, v_fair` beyond economic priors.
3. Promotion of the market-regime term from provisional-sign to calibrated-magnitude.
4. IC-memo adoption gate (unchanged; the relative engine's own DSR/PBO/forward-test status is untouched by this layer).
