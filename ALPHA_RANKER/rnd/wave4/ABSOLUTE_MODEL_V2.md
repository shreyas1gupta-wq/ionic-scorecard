# W6AM2 -- ABSOLUTE P(up) V2: regime-decomposed, beta-propagated, calibrated, portfolio-evaluated

Author: Ishaan Gupta (ML/Data Science, E-012). Date: 2026-07-17. Tags:
[DATA]=on-record verified fact, [INFERENCE]=my construction/derivation,
[OPINION]=my judgment. Follows on from `ABSOLUTE_MODEL_STANDALONE.md` (W6AM
V1, `w6am_build_eval.py`) per Principal directive: build the best-possible
calibrated absolute P(up), embracing (not fighting) V1's finding that
absolute-return direction is beta/regime-dominated, and evaluate on the
Principal's portfolio metrics (CAGR > Sharpe > MDD > alpha).

Code: `rnd/wave4/w6am2_build_eval.py`. Run: **synchronous foreground, waited**
for completion both times (first pass exit 0; a data-source bug was found and
fixed; second pass exit 0, both console logs banked). Outputs:
`rnd/wave4/w6am2_results.json` (full per-fold numbers), `rnd/wave4/
w6am2_portfolio_monthly.parquet` (194-month portfolio ledger), 9 harness
cards `rnd/cards/W6AM2_{betaregime,full_logit,full_gbm}_{1M,1Y,5Y}.json`
(same battery every rule-factor in this repo goes through).

---

## 0. Bottom line (read first)

**Under a genuinely causal (train-strictly-before-test) walk-forward -- stricter
than V1's purged K-fold CV, which allowed training on dates AFTER the test
block -- the decomposition model's stock-specific skill is WEAKER than V1
reported, not stronger.** The one place with real, substantial, and
reasonably robust skill is **beta alone at the 5Y horizon** (causal-OOS AUC
0.634); adding the regime term and the residual stock-specific features
(value/quality/momentum/growth) does **not** improve on beta-alone at 5Y
(full-model AUC 0.51-0.59, both below the beta-only 0.634) and at 1Y the
full model's genuinely held-out AUC is **0.40-0.47 -- worse than a coin
flip**. All 9 cards KILL on the harness's PBO gate (PBO 0.59-1.00, same
bar every factor in this repo must clear), same as V1.

**The market-regime sub-model itself hit two disclosed, honest limits**: (i)
at 5Y, all 4 causal folds' out-of-sample windows (2014-2020, forward-realized
through 2025) had a **literal 100%-up base rate** (78/78) -- AUC is
mathematically undefined there, not "insufficient data," and (ii) because the
regime sub-model needs its own burn-in before it produces real (non-default)
output, the STOCK-level model's earliest training folds see a **constant**
regime input, diluting its measured contribution below what it would be with
a longer regime-model history. Both are disclosed as first-order honesty
issues, not swept under a KILL/PARK label.

**The portfolio (1Y stock-selection ranking + blended-regime exposure dial,
monthly rebalance, realized non-overlapping 1M compounding, gross of costs)
beats buy-and-hold NIFTY500 on CAGR (+11.3pp) and Sharpe (1.12 vs 0.73) but
NOT on MDD (-40.5% vs -29.98%)**. Critically: the stock-selection signal
feeding this portfolio (1Y full-logit P(up)) has a causal-OOS AUC of 0.486 --
statistically indistinguishable from random ranking. **[INFERENCE, important]**:
the portfolio's CAGR/Sharpe edge is far more likely a structural
equal-weight/small-mid-cap tilt riding India's 2009-2025 secular bull market
than genuine stock-picking alpha -- a placebo test (random-selection or
market-cap-only top-quintile, same equal-weight/rebalance mechanics) is the
single most important thing NOT yet done to distinguish these, and is the
top item for the next pass.

**What is usable now, honestly**: beta_252 alone as a coarse 5Y directional
tilt (the one component with real signal in this build); the exposure-dial
concept (fixed, pre-specified, not fitted to the backtest) as a starting
point, though it delivered **zero MDD improvement** here (identical -40.5%
with/without de-risk) while giving up ~3.5pp of CAGR -- meaning, as currently
built, it diluted returns without protecting the worst drawdown. **Nothing in
this pass is certified or should be sized with real capital**: PBO fails
everywhere, and the top-line portfolio win plausibly reflects a tilt effect,
not the model.

---

## 1. Design

### 1.1 Structural decomposition (per task brief)

`P(stock up | h) = f( P(market up | h)_regime , beta_252 , residual stock features )`

- **(a) Market-regime P(up)**: causal walk-forward **logistic regression**
  (linear, cheapest-capable, FACTOR_LIBRARY-first) of the NIFTY500 benchmark's
  own forward-up probability on `valuation_z` (`EY_hist_zscore_expanding`) and
  `breadth_200dma` (`breadth_pct_above_200dma`), both from `market_state.parquet`.
  **[Correction, disclosed]**: the FIRST run used the newer
  `w5bv_broad_richness.parquet` gauge (`broad_richness_index`,
  `breadth_top/bottom_quintile`) -- only 129/249 dates non-null, which left
  **zero** usable causal folds at 5Y (a hard sample-size wall: need
  min_train + embargo + 1 ≈ 85+ candidate dates, had 69). Per
  `BROAD_MARKET_VALUATION.md`'s own prior reasoning ("chosen over the newer
  breadth-gauge specifically for its longer, hard-gated history"), the SECOND
  (reported) run switched the regime model's fitted inputs to
  `market_state.parquet`'s longer-history fields (226/249 and 242/249
  non-null respectively) -- same conceptual valuation-band/breadth-extreme
  decomposition, just the source with enough history to support a genuine
  5Y-embargo causal split. `broad_richness_index` is still used, separately,
  as the **hard-cap diagnostic** for the >=160 de-risk trigger (a threshold
  check, not a fitted input, so its shorter history matters much less there).
- **(b) Beta propagation**: `beta_252` (rolling realised beta) and
  `beta_252 x regime_logit_h` (fitted interaction, not a hand-set multiplier).
- **(c) Residual stock-specific edge**: the SAME already-validated, already-PIT
  V1 features, reused verbatim -- `value_secrel`, `quality_cfo_pat`,
  `quality_QMJ`, `mom_resid_peer`, `fwdgrowth_composite`/`z_accel`/
  `margin_inflection`, `mktcap_log`, `vol_252`.

### 1.2 Two validation regimes, used for different purposes (important distinction)

- `harness.purged_walk_forward_splits()` -- **purged K-fold CV** (train CAN
  include dates chronologically AFTER the test block, only embargoed near
  it). Reused verbatim for the shared IC/IC_IR/DSR/PBO/lag-test/placebo
  battery, for comparability with every other factor in this repo. **This is
  not a live-tradeable simulation.**
- `causal_walk_forward_splits()` (**new, this file**) -- strictly expanding-
  window: train uses ONLY dates before the test block, minus embargo. Used
  for (i) the regime model, (ii) all stock-level predictions that feed the
  portfolio, and (iii) calibration. This is the only way to honestly report
  CAGR/Sharpe/MDD without lookahead in either time direction.

### 1.3 Calibration -- genuine chronological holdout

Pooled causal-OOS predictions per horizon/model are split in **half by date**:
isotonic regression fit on the EARLY half only, reliability curve + Brier
reported on the LATE half only -- fixing V1's disclosed same-pool-calibration
limitation. A SEPARATE isotonic map (fit on the full causal-OOS pool) is used
operationally for the portfolio's conviction number -- disclosed as a
same-pool map for that specific purpose, distinct from the held-out
calibration check reported below.

### 1.4 Portfolio construction (fixed, pre-specified, not tuned to the result)

- Stock selection: **1Y-horizon** full-model calibrated P(up) (chosen over
  1M -- noise floor -- and 5Y -- truncates last 5yr of OOS coverage/small-N).
  Long top quintile, equal-weight, monthly rebalance.
- Compounding: **realized, non-overlapping `fwd_ret_1M_raw` only** -- no
  overlap-inflation.
- Exposure dial: `exposure = clip((0.5*regime_pup_1Y + 0.5*regime_pup_5Y -
  0.35)/(0.65-0.35), 0, 1)`, hard-capped at 0.30 if `broad_richness_index >=
  160`. **Written into the code before viewing any backtest result** --
  never tuned to the CAGR/Sharpe/MDD it's scored on.
- De-risk sleeve: GOLDBEES monthly return where available (`macro_state.parquet`,
  from 2016), else 0% (cash proxy) -- full pre-2016 gold history not
  reconstructed in this pass, disclosed.
- **Gross of costs**: `COST_STANDARDS.md` is still DRAFT/un-approved (D-025)
  -- no cost/slippage haircut applied, per firm rule.

---

## 2. Results

### 2.1 Stage A -- market regime P(up) (causal walk-forward, logistic)

| Horizon | n folds | n candidate dates | AUC | Brier | Note |
|---|---|---|---|---|---|
| 1M | 6 | 225 | 0.573 | 0.239 | weak but real, base rate 59.9% |
| 1Y | 6 | 214 | 0.549 | 0.175 | weak, base rate 79.5% |
| 5Y | 4 (fit) | 166 | **undefined (single-class OOS)** | -- | 78/78 OOS obs were "up" (2014-2020 folds, forward-realized through 2025) -- AUC undefined, not "insufficient," [DATA] |

### 2.2 Stage B -- stock decomposition (causal walk-forward OOS, scored rows only)

| Horizon | Model | AUC (causal-OOS) | Brier | AUC (chrono-HELD-OUT) | Harness verdict | PBO |
|---|---|---|---|---|---|---|
| 1M | betaregime | 0.484 | 0.257 | -- | KILL | 1.000 |
| 1M | full_logit | 0.492 | 0.257 | 0.490 | KILL | 0.996 |
| 1M | full_gbm | 0.507 | 0.268 | 0.515 | KILL | 0.991 |
| 1Y | betaregime | 0.489 | 0.252 | -- | KILL | 1.000 |
| 1Y | full_logit | 0.486 | 0.267 | 0.469 | KILL | 0.957 |
| 1Y | full_gbm | 0.461 | 0.292 | **0.403** | KILL | 0.970 |
| 5Y | betaregime (≈beta alone) | **0.634** | 0.196 | 0.485 | KILL | 0.983 |
| 5Y | full_logit | 0.513 | 0.303 | 0.485 | KILL | 0.996 |
| 5Y | full_gbm | 0.593 | 0.194 | 0.506 | KILL (PBO 0.589, closest to the gate) | 0.589 |

**[INFERENCE] Reading this honestly**: at 5Y, beta-only's causal-OOS AUC
(0.634) beats BOTH full models (0.513, 0.593) -- the residual features do not
add verifiable value here, and the held-out calibration check (fit on
2013-2017, scored on 2017-2020) shows ALL THREE 5Y variants converging to
~0.48-0.51, i.e., no reliable edge survives a genuinely fresh holdout. At 1Y,
`full_gbm`'s held-out AUC (0.403) is worse than random -- a caution flag for
instability with only 6 folds and heavy-imputation features, not a usable
result. **PBO fails (>0.5) for 8 of 9 cards** (5Y full_gbm at 0.589 is the
closest to the 0.5 gate but still fails). DSR ≈0 for essentially every card
(shared global trial counter, same disclosed program-wide artifact as V1).

### 2.3 Reliability (held-out decile curves, abbreviated -- full curves in JSON)

5Y `full_gbm` held-out decile actual-rates range 0.65-0.91 across deciles with
NO monotonic ordering vs `pred_cal_mean` (e.g., bin 5 pred=0.79→actual=0.65,
bin 8 pred=0.79→actual=0.91) -- **not a reliable calibration**, consistent
with the near-0.5 held-out AUC. 1M and 1Y curves show the same pattern
(actual rates bouncing 0.32-0.92 against near-flat predicted means) --
**none of the three horizons' full-model calibration should be read as a
genuine forward probability**, only as a coarse, noisy rank.

### 2.4 Stage C -- portfolio backtest (window 2009-09 to 2025-10, 194 months)

| | CAGR | Sharpe | Ann.Vol | MDD | Final growth |
|---|---|---|---|---|---|
| **Strategy (1Y selection + de-risk dial)** | **22.84%** | **1.12** | 20.3% | **-40.50%** | 27.8x |
| Equity-only (no de-risk overlay) | 26.31% | 1.16 | 22.4% | -40.50% | 43.7x |
| **Benchmark (buy-hold NIFTY500, same window)** | **11.50%** | **0.73** | 16.9% | **-29.98%** | 5.76x |
| Alpha (strategy CAGR - BM CAGR) | **+11.35pp** | | | | |
| Beats BM on Sharpe? | **YES** | | | | |
| Beats BM on MDD? | **NO** (deeper drawdown) | | | | |

**[INFERENCE, most important caveat]**: the exposure dial's MDD is
**identical to the four decimal places** with and without de-risk
(-0.405030...) -- the worst drawdown month(s) occurred while the dial was
still at/near full exposure (consistent with the well-known difficulty of
timing a crash in real time), so the overlay bought **zero** drawdown
protection here while costing ~3.5pp of CAGR. And because the underlying
stock-selection signal (1Y full-logit, chosen for portfolio use) has
causal-OOS AUC 0.486 (indistinguishable from random), **the CAGR/Sharpe win
over buy-and-hold is far more likely a structural equal-weight/small-mid-cap
tilt effect (this universe vs the cap-weighted NIFTY500, in a broadening
2009-2025 bull market) than genuine stock-picking alpha.** A random-selection
or pure-market-cap placebo portfolio, built with the identical equal-weight/
monthly-rebalance/exposure-dial mechanics, is the necessary next test to
separate "tilt" from "model" and was NOT run in this pass (time-boxed).

---

## 3. FACTOR_LIBRARY rule -- explicitly checked

Logistic regression (linear baseline) was run FIRST and checked at every
horizon before trusting the GBM variant, exactly as in V1. Verdict:
**the linear baseline does not clear the hard gate at any horizon** (KILL
throughout, and at 5Y it degrades to near-noise once the residual features
are added -- mirroring V1's Ridge R²=-21.4 instability finding at 5Y). GBM
does not clear the gate either, at any horizon. No exception was needed this
pass since neither model variant is being promoted regardless.

---

## 4. Honest capability statement

**What this build can do, right now, with no further fitting:**
- A structurally correct (a)+(b)+(c) decomposition pipeline, with a properly
  causal (no-lookahead-in-either-direction) walk-forward for every number fed
  into the portfolio -- a stricter, more defensible standard than V1's
  purged-CV pass.
- A genuine held-out (chronological) calibration check per horizon --
  something V1 explicitly could not do.
- A monthly, realized-return, gross-of-cost portfolio backtest that beats
  buy-and-hold on CAGR and Sharpe, over a 194-month/16-year OOS window.

**What this build CANNOT do yet, and must not be sold as doing:**
- No certified stock-picking skill at any horizon (PBO fails 8/9 cards; the
  9th is borderline-fails at 0.589).
- No verified P(up) calibration -- held-out reliability curves are non-
  monotonic at every horizon.
- **No proof the portfolio's outperformance is "the model."** Given the
  stock-selection AUC is statistically at random (0.486), the CAGR/Sharpe win
  plausibly reflects a size/equal-weight tilt riding a bull market, not
  validated alpha -- the single biggest open question, not yet resolved.
- The 5Y market-regime term -- the piece expected to carry the strongest
  signal per the task brief (valuation mean-reversion) -- could not be
  evaluated on AUC at all (single-class OOS window) and, propagated into the
  stock model, is diluted by its own late start relative to the stock
  model's training window (a nested-embargo interaction not fully resolved
  in this pass).
- MDD is WORSE than simple buy-and-hold, and the purpose-built de-risk
  overlay delivered no measurable drawdown protection in this sample.

---

## 5. Next steps (not done in this pass, time-boxed)

1. **Placebo portfolio** (random-selection or market-cap-only top-quintile,
   identical equal-weight/rebalance/exposure-dial mechanics) -- the
   necessary test to separate "tilt effect" from "model skill" in the
   CAGR/Sharpe win. Top priority.
2. Resolve the nested-embargo dilution (regime sub-model's own burn-in
   period bleeding into the stock model's earliest training folds) -- likely
   fix: don't fillna(0.5) for missing regime_pup, instead exclude
   pre-regime-model-start dates from the stock model's training set entirely.
3. Extend the de-risk sleeve's gold series back before 2016 (or substitute a
   T-bill/liquid-fund proxy) so the pre-2016 de-risk sleeve isn't a bare 0%
   cash assumption.
4. Per-family DSR recompute (shared global counter still crushes DSR here,
   same disclosed program-wide artifact as V1).
5. Cost-adjusted portfolio numbers, once COST_STANDARDS.md is Principal-
   approved (currently DRAFT, cannot be used per D-025).
