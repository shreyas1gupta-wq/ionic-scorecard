# W6AM -- STANDALONE ABSOLUTE-RETURN MODEL (prototype + honest capability statement)

Author: Ishaan Gupta (ML/Data Science, E-012). Date: 2026-07-17. Tags: [DATA]=on-record
verified fact, [INFERENCE]=my construction/derivation, [OPINION]=my judgment.

Governs against / distinguishes from: `rnd/wave4/ABSOLUTE_SCORER_SPEC.md` (Arjun Rao's
design, STATUS: BLUEPRINT, HELD per WAVE4_PLAN.md) -- **that** document is a hand-set,
economic-prior-constant TRANSFORM of the existing validated RELATIVE (rank) engine
(`absolute = α·M + β·T_sec + s_mkt·r`), explicitly NOT fitted. **This** document is the
Principal-directed, SUPERSEDING architecture: a genuinely FITTED, standalone model that
predicts a stock's forward absolute return, direction, and P(up) directly -- it does not
start from or transform the relative-rank composite at all. Per the Principal's brief this
architecture supersedes the relative→absolute conversion path; `ABSOLUTE_SCORER_SPEC.md` is
retained on disk as a design record but its recommendation ("keep both, compose") is
superseded by this standalone build.

Code: `rnd/wave4/w6am_build_eval.py`. Run: synchronous where possible; the full 3-horizon
walk-forward job exceeded the 120s foreground window and completed in background (exit 0,
no errors) -- console log + JSON results banked immediately, nothing lost.
Outputs: `rnd/wave4/w6am_results.json` (full per-fold, per-model numbers), cards
`rnd/cards/W6AM_{betaonly,ridge,gbm}_{1M,1Y,5Y}.json` (9 cards, through the SAME
`rnd/lib/harness.py` battery every rule-factor in this repo goes through -- DSR, PBO/CSCV,
lag-test, placebo, decile monotonicity, cost-adjusted long-short, one code path, no
per-agent divergence).

---

## 0. Bottom line (read first)

**The model has real, horizon-dependent, but currently UNCERTIFIABLE cross-sectional
skill, and it is dominated everywhere by market/beta/regime, not stock-picking, at 1M and
1Y. At 5Y the GBM variant shows a large jump in cross-sectional information content beyond
beta -- but on an effective sample of only ~3-4 independent 5-year periods, so it reads as
"promising, not proven."** Every single one of the 9 model/horizon combinations gets a hard
**KILL** from the harness's own anti-overfit gate, mainly on PBO (combinatorial-symmetric
overfitting probability) > 0.5 -- i.e., by the same statistical bar every rule factor in
this repo is held to, none of these 9 cards would be promoted today. That KILL verdict is
the correct, honest answer for a first prototype of "the hardest kind of modeling there
is" (per the task brief) and should NOT be read as "this doesn't work" so much as "this is
not yet distinguishable from noise at the confidence bar this firm requires."

**What is usable now**: sign/direction at 5Y (GBM P(up), AUC 0.64, meaningfully better than
a coin flip and better than the linear baseline) as a COARSE conviction band, and the
qualitative finding that cross-sectional signal (beyond pure beta) genuinely strengthens
with horizon. **What must wait for forward data**: any expected-return magnitude, any
fitted probability percentage, and certification of the 5Y result (PBO fails, DSR≈0 under
the shared global trial counter, n effectively ~3-4 independent periods).

---

## 1. Design

### 1.1 What this predicts (NOT relative rank)

Per horizon `h ∈ {1M, 1Y, 5Y}`, two targets, both regressed/classified directly against
each stock's **absolute** (`fwd_ret_h_raw`) forward return -- never cross-sectionally
demeaned, never a resid/excess basis (that would throw away exactly the market-direction
component the Principal asked this model to capture):
- **Regression**: `E[fwd_ret_h_raw]` (expected absolute return).
- **Classification**: `P(fwd_ret_h_raw > 0)` (probability of a positive absolute return).
Both map, in principle, to a single **-100..+100 conviction** via
`conviction = 100·(2·P(up) - 1)` scaled/clipped by the regression sign -- **not implemented
as a shipped number in this prototype**, because (per §4) neither leg has cleared the bar
that would make a fitted magnitude honest to publish yet.

### 1.2 Base panel and universe

`rnd/panel/panel_long.parquet` -- the FULL-HISTORY panel (2005-04 to 2025-12, 969 symbols,
148,297 stock-month rows), not the short `panel.parquet` (2021-2026 only, which would have
starved the walk-forward CV of history, especially at 5Y where the embargo alone is 5
years). [DATA]

### 1.3 Features (all PIT, all reused from already-built/validated firm modules)

| Feature | Source | What it is | PIT proof |
|---|---|---|---|
| `value_secrel` | `builders_value.build_H014_earnings_yield` + `sector_analytics.peer_relative(level='sub_sector', method='z')` | Earnings yield, Z-DEMEANED within sub-sector at each date -- the sector-bias-audit fix (raw EY is sector-contaminated: IT trades rich vs its own history for structural reasons unrelated to mispricing, banks cheap for the same reason; peer-relative isolates the WITHIN-sector cheap/rich signal). | EPS from `MASTER_fundamentals_pit.parquet`, merge_asof-backward on `available_date` (no lookahead); peer-relative transform is purely cross-sectional at each date (no time-series leakage possible by construction). |
| `quality_cfo_pat`, `quality_QMJ` | `rnd/panel/capstone_legs.parquet` | The canonical 7-leg composite's already-validated, already-PIT quality legs (cash-flow-conversion and quality-minus-junk). Reused, not rebuilt. | Inherited PIT proof from the capstone composite build (CAPSTONE_quality_* cards). |
| `mom_resid_peer` | `capstone_legs.parquet` | Peer-relative residual momentum leg. | Same as above. |
| `fwdgrowth_composite`, `z_accel`, `margin_inflection` | `rnd/wave4/_w6fg_scored.parquet` | The Wave-4/6 forward-growth-divergence agent's EARNINGS-CONFIRMED acceleration/margin-inflection composite -- ingested per task instruction, not rebuilt. `composite_confirmed` specifically gates on `earnings_confirm=1` (i.e., the acceleration must have shown up in an actually-reported quarter, not just a forward estimate) per that agent's own construction. | Keyed on the same `available_date`-gated PIT discipline as the rest of the panel (confirmed: date range matches panel_long exactly, 2005-2025). |
| `valuation_z` | `rnd/panel/market_state.parquet`, `EY_hist_zscore_expanding` | Broad market valuation band (expanding-window z-score of median EY vs its own history) -- the SAME primary regime input `BROAD_MARKET_VALUATION.md` recommends for the M-term (chosen there over the newer breadth-gauge specifically for its longer, hard-gated history). Broadcast to every stock on that date. | Expanding-window (t'≤t only, min_periods=24), already audited in `market_state.py`. |
| `breadth_200dma` | `market_state.parquet`, `breadth_pct_above_200dma` | Breadth-of-the-market extreme (% of universe above own 200dma). | Same file, same PIT construction. |
| `beta_252` | `panel_long.parquet` | Rolling 252d realised beta to the equal-weight proxy. **Required per task brief**: absolute returns are dominated by market direction, so beta must be an explicit input, unlike the market-neutral relative model which cancels it by construction. | Rolling window uses data ≤ t only (inherited from `harness.py`/`build_panel_long.py`). |
| `beta_x_valz` = `beta_252 × valuation_z` | derived | Interaction: a high-beta name should carry MORE of the regime's directional pull than a low-beta name -- lets a fitted model learn the leverage-to-regime relationship instead of a hand-set constant. | Product of two already-PIT series; no new lookahead. |
| `mom_x_valz` = `mom_resid_peer × valuation_z` | derived | The **momentum-extreme-rule**, expressed as a FITTED interaction rather than a hand-set dampening multiplier: lets cross-validation decide how much momentum's weight should shift with the market-valuation regime, instead of assuming a shape. Documented tradeoff: `MOMENTUM_VALUATION_EXTREMES.md` found the "overvalued" tail has **zero** historical occurrences (richness index never crossed 160 in the whole sample) and the "undervalued" tail is a single 7-month GFC episode -- so this interaction term is honest about only ever having been trained on one real extreme-regime episode, not a validated momentum-crash rule. | Product of two already-PIT series. |
| `mktcap_log`, `vol_252` | `panel_long.parquet` | Size and realised-vol controls (standard, disclosed, not a novel factor). | Inherited PIT. |

**Coverage caveat, disclosed** [DATA]: `value_secrel` (19.1% non-null over the full panel),
`quality_cfo_pat` (31.9%), and the forward-growth trio (56-61%) have materially thinner
coverage than `beta_252`/`valuation_z`/`quality_QMJ` (92-98%). At 5Y, `value_secrel` was
degenerate (fewer than 2 distinct values) in the TRAINING fold for 4 of 5 folds and was
therefore **dropped from both train and predict for those folds** (see `_degenerate_safe_cols`
in the code, logged per-fold in `w6am_results.json.fold_log[*].gbm_cols_dropped_degenerate`)
-- the promised "sector-relative value" feature barely participated in the 5Y GBM result in
practice. This is a real limitation of the prototype, not silently patched.

### 1.4 Models (cheapest capable, no deep learning per D-011)

1. **BETA-ONLY** (isolation baseline): `beta_252, valuation_z, breadth_200dma, beta_x_valz`
   only, fit with a GBM. Answers "how much of absolute-return predictability is JUST
   market/beta/regime, with zero stock-specific fundamentals."
2. **RIDGE (linear baseline)** -- **run and checked FIRST per the FACTOR_LIBRARY rule**
   ("a linear/rank baseline must clear costs before any ML variant is attempted"): all
   features, median-imputed + standardized, L2-regularized (`alpha=5.0`).
3. **GBM (the ML variant)**: all features, `sklearn.ensemble.HistGradientBoostingRegressor`
   / `Classifier` (`max_depth=3, learning_rate=0.05, min_samples_leaf=200`, L2-regularized).
   **lightgbm is not installed in this environment** (checked, `ModuleNotFoundError`);
   HistGradientBoosting is the same histogram-binned-tree family and the cheapest capable
   substitute available without a new dependency install -- documented substitution, not a
   silent downgrade. It natively handles missing values (unlike Ridge, which needs
   imputation), which matters given the coverage gaps in §1.3.

Classification uses `LogisticRegression` (baseline) and `HistGradientBoostingClassifier`
(ML variant), same feature sets.

### 1.5 Validation (purged walk-forward + the shared anti-overfit battery)

- **Splits**: `harness.purged_walk_forward_splits(dates, horizon, n_splits=5)` reused
  verbatim -- embargo = the horizon's own period length (1/12/60 months either side of each
  test fold), so overlapping forward-return windows cannot leak across the train/test
  boundary. This is the exact same purge/embargo machinery every rule-factor in this repo
  goes through (one code path, RESEARCH_PROTOCOL.md S3).
- **OOS discipline**: every prediction reported below is from a fold where the model was
  trained ONLY on dates outside that test fold's purge+embargo window -- strict walk-forward,
  no fold ever sees its own test-period data (or the embargoed buffer around it) during fit.
- **Evaluation**: the pooled (all-folds-concatenated) OOS predictions are fed AS A FACTOR
  into `harness.evaluate(..., return_basis="raw", ...)` -- reusing the SAME IC/IC_IR,
  decile-monotonicity, cost-adjusted long-short, DSR (honest global trial count), PBO/CSCV,
  lag-test, and placebo-shuffle battery every hard-gated rule factor in this firm is held to.
  This satisfies "the validation battery applies to models exactly as to rules"
  (RESEARCH_SOP §10) directly, rather than inventing a parallel bar for ML.
- **Market-neutral sanity**: because `return_basis="raw"` here means the ABSOLUTE label
  (not resid/excess), the harness's own cross-sectional IC computation is, by construction,
  net of any COMMON per-date market shift (Spearman rank correlation within a date is
  invariant to an additive constant added to every name that day) -- so the harness's
  `ic.ic_mean`/`ic_ir` numbers already ISOLATE cross-sectional (stock-picking) skill from
  pure market-timing, even though the raw target itself is absolute. A SEPARATE, POOLED
  (date+cross-section mixed) Spearman IC is also reported in `w6am_results.json` for
  contrast -- it is higher precisely because it also credits the model for knowing which
  MONTHS were good, not just which STOCKS were good that month.

---

## 2. Results (all numbers OOS, walk-forward, from `w6am_results.json` / the 9 harness cards)

### 2.1 Regression -- expected absolute return

| Horizon | Model | n obs / dates | Pooled R² | Pooled IC (mixed) | **Cross-sec IC_mean** (harness) | **Cross-sec IC_IR** | DSR | PBO | Harness verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1M | beta-only | 146,511 / 247 | -0.005 | 0.116 | 0.0091 | 0.071 | 0.000 | 1.000 | KILL |
| 1M | Ridge | 146,511 / 247 | -0.014 | 0.017 | 0.0195 | 0.143 | 0.000 | 0.961 | KILL |
| 1M | GBM | 146,511 / 247 | -0.008 | 0.100 | 0.0154 | 0.127 | 0.000 | 0.948 | KILL |
| 1Y | beta-only | 137,018 / 236 | -0.036 | 0.137 | 0.0876 | 0.580 | 0.000 | 0.935 | KILL |
| 1Y | Ridge | 137,018 / 236 | **-0.102** | 0.077 | 0.1103 | 0.784 | 0.000 | 0.861 | KILL |
| 1Y | GBM | 137,018 / 236 | -0.011 | 0.114 | 0.0937 | 0.665 | 0.000 | 0.905 | KILL |
| 5Y | beta-only | 99,852 / 187 | -0.043 | 0.196 | 0.0302 | 0.178 | 0.000 | 1.000 | KILL |
| 5Y | Ridge | 99,852 / 187 | **-21.37** | 0.145 | 0.1445 | 0.855 | 0.000 | 0.961 | KILL |
| 5Y | GBM | 99,852 / 187 | -0.138 | 0.278 | **0.2321** | **2.155** | 5.5e-77 (~0) | **0.831** | KILL (PBO only) |

**[INFERENCE] Reading this table honestly:**
- **Pooled R² is negative everywhere, including at 5Y GBM (-0.14).** A flat "predict the
  historical mean" would beat every one of these models on raw explained variance,
  out-of-sample. This is exactly the "R² will be low" the task brief pre-registered --
  confirmed, not merely asserted.
- **Ridge blows up catastrophically at 5Y (R² = -21.4).** [INFERENCE] With ~11 correlated,
  partially-collinear features fit on a training set whose 5Y-embargo purge leaves limited
  effective degrees of freedom, and a target (5Y cumulative return) with a heavy right tail
  (some names compound many-fold over 5 years), an L2-penalized linear model extrapolates
  badly on unseen combinations near that tail -- a genuine, disclosed failure mode of the
  linear baseline at long horizons, not a data bug (lag-test delta 0.002, placebo -0.0016,
  both clean, so it is not lookahead). **This IS the FACTOR_LIBRARY-rule check working as
  intended**: the linear baseline was run first, and it visibly fails at 5Y -- exactly the
  signal the rule exists to surface before trusting anything fancier.
- **Cross-sectional IC_IR (net of common market direction) rises sharply with horizon**:
  ~0.07-0.14 at 1M, ~0.58-0.78 at 1Y, ~0.18 (beta-only) to **2.15 (GBM)** at 5Y. The 1M
  numbers are indistinguishable from noise at this firm's own IC_IR-min-0.20 gate; the 1Y
  numbers look superficially strong but the GAP between beta-only (0.088 IC_mean) and the
  full models (0.093-0.110) is small -- **at 1Y, most of what looks like skill is actually
  just knowing the beta/regime term**, not stock-specific alpha.
- **At 5Y, GBM's cross-sectional IC_mean (0.232) is ~7.7x the beta-only baseline's (0.030)**
  -- the one place in this prototype where the model plausibly adds real information beyond
  market/beta. But: `hit_rate: 1.0` for GBM 5Y (literally every one of 187 monthly
  long-short readings was positive) combined with PBO=0.83 is a **red flag for
  non-independence, not a clean win**: 187 overlapping 5-year-forward observations over a
  ~20-year sample are, by the same overlap logic `BROAD_MARKET_VALUATION.md` already
  flagged for its own 5Y number, closer to **~3-4 independent non-overlapping 5-year
  periods**. A 100% hit rate over ~4 independent draws in India's structurally rising
  2005-2025 equity market is fully consistent with "the model learned to lean into a
  quality/value/momentum tilt during a secular uptrend" and is NOT yet evidence of a
  differentiated, regime-robust stock-picking skill. This is the single most important
  honesty caveat in this whole prototype.
- **PBO fails (>0.5) for every one of the 9 cards.** The harness's own combinatorial-
  symmetric CSCV adaptation says: across in-sample/out-of-sample block splits, the
  configuration that looked best in-sample tends to underperform out-of-sample most of the
  time. This is the dominant KILL reason at 1Y/5Y (1M additionally fails on raw IC_IR). By
  the firm's own hard-gate bar, **none of these 9 cards would be promoted today.**
- **DSR is effectively 0 for 8 of 9 cards** (GBM 5Y is technically 5.5e-77, i.e. also ≈0 in
  any practical sense) [DATA]: the harness's global trial counter had already logged
  654-662 total program trials by the time these cards ran, and DSR deflation is dominated
  by that shared counter (same mechanism flagged in `CONSOLIDATION.md`'s "harness fixes
  needed" item 2 and in `ABSOLUTE_SCORER_SPEC.md`'s DSR≈0/PBO≈0.92 citation) -- this is a
  known, program-wide artifact, not something specific to this model failing worse than
  everything else. A per-family DSR recompute exists (`harness.dsr_from_stats`) but was not
  applied here; disclosed as a limitation of this prototype's reporting, not hidden.

### 2.2 Classification -- P(up)

| Horizon | Model | Base rate (up) | AUC | Brier (raw) | Brier (isotonic, SAME POOL) |
|---|---|---|---|---|---|
| 1M | Logit | 0.527 | 0.495 | 0.261 | 0.249 |
| 1M | GBM | 0.527 | 0.559 | 0.250 | 0.244 |
| 1Y | Logit | 0.600 | 0.499 | 0.264 | 0.237 |
| 1Y | GBM | 0.600 | 0.539 | 0.263 | 0.235 |
| 5Y | Logit | 0.743 | 0.537 | 0.246 | 0.187 |
| 5Y | GBM | **0.743** | **0.641** | 0.188 | 0.179 |

**[INFERENCE]**:
- **1M and 1Y P(up) is barely better than a coin flip** (logit AUC ≈0.50 at both; GBM
  0.54-0.56 -- a weak, likely not-robust edge). Direction at short/medium horizons is NOT
  usable from this prototype as-is.
- **5Y GBM AUC = 0.641 is the standout number in this whole exercise** -- a real ranking
  improvement over random, and over the linear baseline (0.537). But note the base rate is
  already 74.3% "up" at 5Y (India's secular equity drift), so a naive "always predict up"
  classifier gets 74% raw accuracy for free; AUC (which is base-rate-independent) is the
  fairer read, and 0.64 there is genuinely informative -- subject to the SAME small-
  independent-N caveat as §2.1 (this is measured over the same ~187 overlapping / ~3-4
  independent 5Y windows).
- **The isotonic-recalibrated Brier scores are NOT a clean out-of-sample calibration
  check** -- the isotonic map was fit on the SAME pooled OOS prediction/outcome pairs it is
  then scored against (no further held-out split; there isn't enough independent 5Y data
  left to carve one out honestly). This is disclosed as an optimistic upper bound on
  calibration quality, not a genuine forward-calibration result. A true calibration
  read waits for the frozen forward test, same as the relative model.

---

## 3. FACTOR_LIBRARY rule -- explicitly checked

**"A linear/rank baseline must clear costs before any ML variant is attempted"**: Ridge was
run FIRST at every horizon and its harness card checked before trusting GBM. Verdict: **the
linear baseline does NOT clear costs/the hard gate at any horizon** -- KILL at 1M/1Y/5Y, and
outright numerically unstable at 5Y (R²=-21.4). Per the Principal's explicit instruction to
build and prototype this standalone architecture regardless, the GBM variant was still run
and is reported above, but this is disclosed as an EXCEPTION to the rule's normal
gatekeeping role, not a case where the rule was satisfied and GBM was "additionally"
justified. The GBM does NOT clear the hard PBO/DSR gate either, at any horizon.

---

## 4. Honest capability statement (brutal, per task instruction)

**What this model can do, right now, with no further fitting:**
- **Coarse, horizon-DEPENDENT conviction ranking** across stocks, strongest at 5Y (GBM
  cross-sectional IC_mean 0.232, IC_IR 2.15, AUC 0.64) — usable ONLY as a relative-within-
  the-model ranking signal for further scrutiny, not a certified strategy.
- **A qualitative, economically sane finding**: market/beta/regime dominates short-horizon
  absolute-return predictability (1M, 1Y) almost completely; stock-specific fundamentals
  (value/quality/growth) only begin to separate from pure beta at the 5Y horizon. This
  matches the ABSOLUTE_SCORER_SPEC's own design prior (α_1M≈0, α_5Y meaningful) — a fitted
  model INDEPENDENTLY reproducing that same horizon-shape is a mild corroboration of that
  spec's economic intuition, for what it's worth given neither has cleared certification.

**What this model CANNOT do yet, and must not be sold as doing:**
- **No calibrated expected-return magnitude, at any horizon.** Pooled R² is negative
  everywhere; a fitted % return number would be false precision on top of a model that
  currently explains LESS variance than the historical mean.
- **No calibrated P(up) percentage.** 1M/1Y AUC ≈ 0.50-0.56 is not a usable edge; 5Y's 0.64
  is promising but (a) its isotonic calibration is optimistic-by-construction (§2.2) and
  (b) rests on ~3-4 independent periods, not enough to certify a probability.
- **No certified promotion at any horizon.** All 9 cards KILL on this firm's own PBO/DSR
  gate -- the identical bar every rule factor here must clear. Nothing in this document
  should be read as "the absolute model works"; it should be read as "here is where a
  fitted absolute-return model's honest signal currently sits, horizon by horizon, and here
  is exactly why none of it is certifiable yet."
- **The forward-growth and sector-relative-value features are thin.** Coverage gaps (19-61%
  non-null) mean `value_secrel` was outright absent from 4 of 5 5Y training folds. The
  "ingest the forward-growth agent's features" instruction was honoured, but their marginal
  contribution inside this specific prototype was not isolated/ablated here (a natural next
  step, not done in this pass — time-boxed).

**Does the model add genuine forward-absolute info beyond just market-beta?**
- **1M: essentially no** (GBM cross-sec IC 0.0154 vs beta-only 0.0091 -- both near the noise
  floor, Ridge even edges out GBM at 1M with 0.0195, i.e. inside the noise of each other).
- **1Y: marginally** (0.094 vs 0.088 GBM-vs-beta-only -- most of the 1Y signal IS the beta/
  regime term; stock selection adds little on top at this horizon in this sample).
- **5Y: plausibly yes, materially** (0.232 vs 0.030, ~7.7x) -- **but this is the honest-
  hedge answer, not a certified one**: small independent-N, PBO fail, 100% hit-rate red
  flag for overlap-driven inflation. Treat as "the most promising single finding in this
  prototype, worth a dedicated small-N-aware follow-up (leave-one-non-overlapping-period-out,
  same discipline `ABSOLUTE_SCORER_SPEC.md` §4 already requires of the market-regime term),
  not yet as an established result."

---

## 5. Next steps (not done in this pass, time-boxed prototype)

1. **Leave-one-non-overlapping-5Y-period-out** on the 5Y GBM result specifically -- the
   single most important open question this prototype raises (same discipline the firm
   already applies to the market-regime term and to cross-asset candidates in WAVE4).
2. **Per-family DSR recompute** (`harness.dsr_from_stats` with a family-scoped trial count)
   instead of the shared global-program counter, so DSR here isn't automatically crushed by
   unrelated trials elsewhere in the repo.
3. **Feature ablation** at 5Y specifically: isolate how much of the 7.7x IC improvement
   over beta-only comes from quality_QMJ/mom_resid_peer (well-covered, 83-98%) vs the
   thinly-covered value_secrel/fwdgrowth features (19-61%, often dropped per-fold).
4. **A genuinely held-out calibration split** for P(up) once enough forward/live data
   exists to stop reusing the same OOS pool for isotonic fitting and scoring.
5. Conviction-band mapping (`-100..+100`) is deliberately NOT implemented as a shipped
   number in this prototype -- per §4, no leg has cleared the bar that would make a fitted
   magnitude honest to publish. Build it only after (1)-(2) above, and only as a coarse band
   (strong-neg/neg/neutral/pos/strong-pos), never a fitted percentage, matching the same
   discipline `ABSOLUTE_SCORER_SPEC.md` §2 already committed to for its own (different,
   hand-set) construction.
