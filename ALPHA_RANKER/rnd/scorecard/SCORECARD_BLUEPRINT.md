# SCORECARD BLUEPRINT — two clean scorecards (RELATIVE + ABSOLUTE)

**Owner:** Arjun Rao (Head of Quant, E-004). **Date:** 2026-07-18. **Status:** ARCHITECTURE / DESIGN ONLY —
no implementation code here, no new research. This is the buildable spec the S1–S4/S7 builder-agents implement
mechanically. Tags: **[DATA]** = on-disk verified, **[INFERENCE]** = my construction, **[OPINION]/[MY CALL]** =
my judgment (flagged where the mandate was ambiguous).

**NAMING CORRECTION (flagged by the techno-funda methodology research, 2026-07-18 — see
`Shreyas_Ionic_AMC/04_RND_LAB/FUND_METHODOLOGY_2036/TECHNOFUNDA_PATTERNS.md`):** §1.1 and §2.1 describe
`earnings_confirm_v2` as an "earnings surprise" gate. It is more accurately a **multi-year fundamental
confirmation flag** (persistence of op-growth/margin acceleration across reported quarters), NOT a
single-quarter consensus-beat/miss reaction signal — there is no price-reaction or analyst-estimate
component in it. This does not change any construction or score already built (the leg is used correctly
as-is), but "earnings surprise" language elsewhere in this program should be read as "confirmed multi-quarter
acceleration", not "beat vs. estimates". Relevant to why `earn_1M` (§2.1) contributed ~zero incremental IC
in the S1 build despite its 40% weight (`S1_RELATIVE_1M_REPORT.md`) — it may be behaving as a slower
fundamental-persistence filter rather than the fast-reacting surprise signal the 1M horizon actually wants.

**Governs against / reuses (do NOT redesign these — reuse the tested pieces):**
- `rnd/FINAL_MODEL.md` (canonical 7-leg definition, orthogonality pruning, sizing-not-blending lesson)
- `rnd/wave4/REGIME_SPEC_V2.md` (momentum-by-regime table A, certified `rev5d` oversold-MR switch §0, valuation-band gate C, richness index)
- `rnd/wave4/SECTOR_RELATIVE_REBUILD.md` (SR-v1 blend: 5 legs sector-neutral, asset-growth + cfo-pat RAW)
- `rnd/wave4/ABSOLUTE_MODEL_STANDALONE.md` + `ABSOLUTE_MODEL_V2.md` (what a *fitted* absolute model can/can't do — the honesty floor)
- memory `alpha-ranker-valuation-band-momentum-rule` (#7 non-blind sector-neutralization; 0/65/160 sign-only; momentum fails both valuation tails)

**Supersedes:** `rnd/wave4/ABSOLUTE_SCORER_SPEC.md`'s "keep both, compose / `absolute = α·M + β·T_sec + s_mkt·r`"
recommendation. The Principal's 2026-07-18 mandate is explicit: **the absolute scorecard is STANDALONE, not a
transform of the relative rank.** That old spec is retained as an audit record only.

---

## 0. SCOPE, PHILOSOPHY, NON-GOALS (read first)

**What these two scorecards are.** Two *independent* products over the NIFTY-750 universe, each with its own
construction and its own evaluation lens:
- **RELATIVE** = a cross-sectional ranker. Benchmark = decile **long-short**. Lens = **LS Sharpe + decile
  monotonicity / rank-IC**. Horizon-specific (1M / 1Y / 5Y) because fundamentals vs momentum matter very
  differently by horizon. Answers *"which names to prefer over peers at this horizon."*
- **ABSOLUTE** = a long-only expected-return model. Lens = portfolio **CAGR + Calmar**. Output = **probability
  and intensity** of future return from `E[EPS growth] × PE re-rating`. Answers *"is this a good business to own
  outright, and how much return do we expect."*

**NON-GOALS (hard constraints — a builder that violates these has built the wrong thing):**
1. The ABSOLUTE scorecard **NEVER reads, transforms, or is seeded by the RELATIVE score.** No `s_mkt·r` term,
   no rank hand-off. It is a genuine absolute-return model built from fundamentals + valuation + regime. (This
   is the single biggest change from the superseded `ABSOLUTE_SCORER_SPEC.md`.)
2. Neither scorecard is the **final production model.** These are clean forward-test *candidates*. Magnitudes are
   PROVISIONAL until a frozen forward grade exists (relative: ~Dec 2026 clock; absolute: its own new clock).
3. **No new research, no factor mining, no per-run fitting.** Every leg here is already tested. Weights are
   frozen priors / one-time frozen fits (see §5 determinism contract). Adding a trial re-opens the
   multiple-testing hole `FINAL_MODEL.md §5` is already impaled on.
4. **Neither scorecard touches the frozen 7-leg forward-test** (`rnd/forward_test/FROZEN_SPEC.md`). That clock
   runs untouched. These scorecards are separate artifacts.
5. **Logic-first, FM lens.** Where statistics and sound fund-manager logic disagree at thin sample, logic wins
   for *inclusion*; statistics stay as *disclosed advisory*. Hard structural gates (lag-test, placebo) still kill.
6. Not sized for real capital by anyone but the Principal (D-025 / live gate).

**FM-lens sanity check applied throughout:** every design choice below is annotated with *"would a real PM build
it this way?"* Two examples of where that changed the design: (a) the 1M quality input is a *floor/screen*, not a
heavy weight — a PM does not pick a 1-month trade on ROE; (b) the 5Y sector-neutralization is *blended with
absolute merit*, because a PM will pay up for a genuinely great business regardless of its sector rank.

---

## 1. SHARED FOUNDATIONS (both scorecards use these)

### 1.1 Data lineage [DATA] — all PIT, all on-disk

| Input | File | Key columns | Notes |
|---|---|---|---|
| Panel grain / forward returns | `rnd/panel/panel_pit.parquet` | `date, symbol, sector, beta_252, vol_252, fwd_ret_{1M,1Y,5Y}_{raw,excess,resid}, disc_event_in_window_*` | **Survivorship-free** (42-snapshot PIT membership). USE THIS, not `panel_long` (which has survivorship contamination) for any evaluation. 99,415 rows. |
| The 7 canonical legs | `rnd/panel/capstone_legs.parquet` | long: `date, symbol, value, leg` | legs: `value_EY, trend_ma65_slope, quality_QMJ, bs_issuance, bs_asset_growth, quality_cfo_pat`. **CAVEAT [DATA]:** this cache has `mom_resid_peer`, NOT `mom_resid_plain`. Canonical momentum is PLAIN — builder MUST rebuild it fresh via `run_long_confirm.build_mom_resid_12_1` (see `SECTOR_RELATIVE_REBUILD.md` data-lineage), never silently substitute the cached peer leg (that bug corrupted all of Wave-5, `WAVE4_FINDINGS §1-CORRECTION-2`). |
| Per-stock valuation | `rnd/panel/stock_valuation_pit.parquet` | `EY, PE, PB, net_profit, book_equity, mktcap, cap_tier, sector` | absolute PE/EY per name. |
| Per-stock valuation-vs-cross-section | `rnd/panel/w5bv_stock_percentiles.parquet` | `expensive_pctile_EY/PE/PB, composite_expensive_pctile` | percentile of richness across the cross-section at each date. |
| Earnings growth / surprise / acceleration | `rnd/wave4/_w6fg2_scored.parquet` | `rev_growth_t, op_growth_t, rev_accel, margin_inflection, earnings_confirm_v2, sub_op_persistent, z_accel, composite_v2_confirmed, available_date` | the forward-growth-divergence composite. `earnings_confirm_v2` = the surprise/confirmation gate (acceleration shown in a *reported* quarter, PIT via `available_date`). `sub_op_persistent` = growth-longevity flag (5Y). |
| Market regime gauges | `rnd/panel/market_state.parquet` | `EY_hist_zscore_expanding, breadth_pct_above_200dma, market_vol, PE_by_tier_*` | 249 monthly dates. Expanding-window, causal (t≤now). |
| Sector context | `rnd/panel/sector_context.parquet` | `sec_mom_12_1, sec_val_pctile, sec_earn_yoy, sec_breadth` | for 5Y sector-relative + sector PE anchor. |
| No-negative-news screen | S6 output (`rnd/scorecard/no_neg_news_screen.parquet`, built by S6) | `date, symbol, neg_news_flag` (0/1) | binary exclusion gate for 1M. Built from `india_fin_news` 125K. If a name has no coverage → treat as `neg_news_flag=0` (not screened out — absence of news ≠ bad news). [MY CALL, §6.6] |

### 1.2 The valuation band (Principal's 0/65/160 scale) — SIGN-ONLY, frozen [DATA]

Operational proxy for the Principal's own scale = the **richness index**, reused verbatim from
`REGIME_SPEC_V2` layer C / `BROAD_MARKET_VALUATION.md` (do NOT refit):

```
richness_index(t) = 100 · exp( −0.25 · EY_hist_zscore_expanding(t) )      # market_state.parquet, causal
band(t) =  UNDERVALUED   if richness_index < 65      # cheap → momentum OFF (violent mean-reversion tail)
           NEUTRAL       if 65 ≤ richness_index < 160 # full momentum weight
           OVERVALUED    if richness_index ≥ 160      # froth → momentum OFF (bubble-top reversal tail)
```
- **Sign-only, never a sizing dial** (Principal directive; Buffett indicator explicitly DROPPED). The band gates
  the *momentum weight* (0/1/0) and informs the absolute PE-rerating anchor. It does not scale position size.
- **DISCLOSED empirical gap:** richness has never crossed ~139 in the 21-yr India sample, so the `≥160` branch is
  precautionary/economic-logic only, never fired, untestable (`REGIME_SPEC_V2 §3`). Ships as-is, flagged.

### 1.3 Breadth de-risk trigger (extremes only) [DATA]

Per Principal directive (RESEARCH_QUEUE batch 3): breadth acts **only at the tails**, nowhere in the middle;
VIX is down-weighted/dropped as noise.
```
breadth_pctrank_exp(t) = expanding-percentile rank of breadth_pct_above_200dma(t)   # market_state.parquet
WASHOUT  if breadth_pctrank_exp ≤ 0.20   (equivalently >~30% of Nifty500 below 200DMA)  → oversold-MR ON (relative 1M); de-gross (absolute)
FROTH    if <~5% of names below 50/200DMA                                              → de-gross (absolute)
NEUTRAL  otherwise                                                                     → breadth does nothing
```
Thresholds are soft (plateau-tested 10th/20th/30th all work, `REGIME_SPEC_V2 §0 Check 4`), not knife-edge.

### 1.4 Quality gate — one definition, two thresholds [DATA] + [MY CALL on threshold direction]

```
quality_score(t, name) = rank_pct( 0.5·rank_pct(quality_QMJ) + 0.5·rank_pct(quality_cfo_pat) )   # within-date, cross-sectional
```
- **1Y gate:** keep names with `quality_score ≥ 0.10` (drop the worst-quality decile).
- **5Y gate:** keep names with `quality_score ≥ 0.20` (drop the worst-quality quintile — stricter, because a
  5-year hold cannot survive a junk balance sheet).
- **[MY CALL, §6.1]** The mandate says "top-90th-percentile" (1Y) and "top-80th-percentile" (5Y). I read these as
  *keep the top 90% / top 80%* (i.e. drop the bottom 10% / 20%), NOT *keep only the top 10% / top 20%*. Reasoning:
  (a) the literal "top 10% only" reading makes the 5Y gate (top 20%) *looser* than 1Y (top 10%), which is
  backwards — a longer hold demands a *higher* quality floor, so 5Y must be at least as strict; the drop-bottom
  reading gives exactly that (drop 10% at 1Y, drop 20% at 5Y). (b) A top-10%-only universe (~80 names) is too thin
  to build monotonic deciles for the LS evaluation. (c) FM logic: the gate's job is to *exclude junk*, not to
  pre-select an elite — selection is what the score itself does. This is the coherent, testable, PM-sane reading.

---

## 2. RELATIVE SCORECARD

**Output:** per (date, symbol, horizon): `rel_score_h ∈ [−100, +100] = 200·(rank_pct(composite_h) − 0.5)`,
plus the leg decomposition. Names failing the horizon's gate are **unscored** (NaN, not zero). `min_legs=5-of-7`
presence rule carried from canonical build (a name with <5 legs is not scored as the composite).

### 2.1 RELATIVE 1M — momentum(regime, skip-recent) + earnings surprise/growth + quality-floor + no-neg-news

FM logic (Principal): at 1M fundamentals alone barely move the needle; clubbed with quantamental
news/momentum they do. So momentum + earnings-surprise carry the weight; quality is a floor; news is a veto.

**Components (each → cross-sectional `rank_pct` within date):**
1. **`mom_1M` — regime-conditional momentum, SKIP the most recent 15-20 trading days.**
   - Lookback L by regime (reuse `REGIME_SPEC_V2` table A): BOOMING_BULL → 12m; NORMAL_CHOPPY → 12m (highest-IC
     cell); BEAR_OVERSOLD → momentum SUPPRESSED (weight 0).
   - Construction: cumulative return from `t−L` to `t−SKIP`, `SKIP = 15` trading days [MY CALL, §6.2: the mandate
     says "~15-20"; I pin **15** as the frozen operating value — it is inside the stated band, and the classic
     12-1 leg already skips ~21d, so 15 is a deliberate, slightly-shorter, still-reversal-safe choice. Plateau
     across 15/20 to be recorded in eval, one value frozen].
   - **Oversold-extreme override:** if `WASHOUT` (breadth_pctrank_exp ≤ 0.20), REPLACE `mom_1M` with the
     **certified `rev5d` oversold mean-reversion switch** (`REGIME_SPEC_V2 §0`, drop-one/era/cost-@2x certified;
     `rsi2` confirm-only, never sized). No double-count: momentum is already suppressed in BEAR_OVERSOLD, so the
     switch fires exactly where momentum says "do nothing."
   - **Overbought-in-recovery rule** (Principal batch 2): a high-momentum reading during a sharp recovery OFF a
     fall is NOT faded — only froth-overbought in a *sustained* uptrend is. Encode: the `rev5d` fade fires only
     under WASHOUT/oversold context, never as a blanket overbought fade. (Already satisfied by gating rev5d to
     the washout branch.)
2. **`earn_1M` — earnings growth/surprise.** `rank_pct` of `z_accel` from `_w6fg2_scored.parquet`, GATED on
   `earnings_confirm_v2 = 1` (surprise must have shown in a reported quarter, PIT via `available_date`). Names
   without a confirmed reading get the cross-sectional median rank (neutral), not excluded.
3. **`qual_floor_1M` — "good fundamentals" check (light).** `quality_score` (§1.4). At 1M this enters as a small
   weight AND a soft floor: names in the bottom quality decile are down-weighted, not selected on quality.
4. **`no_neg_news` gate** — hard exclusion: if `neg_news_flag = 1`, the name is **unscored for 1M** (removed from
   the cross-section that month). Screens out adverse-news names before ranking.

**Combine (frozen weights, NEUTRAL regime):** `composite_1M = rank_pct( 0.45·mom_1M + 0.40·earn_1M + 0.15·qual_floor_1M )`
then apply the `no_neg_news` exclusion. Weights are (regime, horizon)-conditional per §5; in BEAR_OVERSOLD the
`mom_1M` slot is the `rev5d` switch and weights shift to `0.55·rev5d + 0.30·earn_1M + 0.15·qual_floor`.
[MY CALL, §6.3 — weights are economic-prior seeds, frozen; not fitted.]

**Confidence flag:** 1M ships with an explicit LOW-CONVICTION flag (`FINAL_MODEL §5.2` — no 21-yr intra-month
confirmation). FM lens: a PM treats a 1M score as a tilt/timing nudge, not a standalone thesis.

### 2.2 RELATIVE 1Y — value + growth + momentum, quality-gated (top 90%), regime-conditional

Base = the validated 1Y engine, re-expressed per the mandate. FM logic: 1Y is the honest core model.

**Universe:** apply the **1Y quality gate** (§1.4, `quality_score ≥ 0.10`) — drop the bottom quality decile
BEFORE ranking. All ranks recomputed WITHIN the gated cross-section.

**Components (each → within-date `rank_pct` on the gated universe):**
1. **Value:** `value_EY` (the canonical value representative; absorbs DCF/market-state/smallcap-tier per
   `FINAL_MODEL §1`).
2. **Growth:** `composite_v2_confirmed` from `_w6fg2_scored.parquet` (earnings-confirmed acceleration + margin
   inflection). This is the "growth" limb the mandate names, and it is the piece the legacy 7-leg lacked.
3. **Momentum:** `mom_resid_plain` (rebuilt fresh — §1.1 caveat), weighted by the **valuation-band gate**:
   `mom_weight = 1.0` in NEUTRAL band, `0.0` in UNDERVALUED (<65) or OVERVALUED (≥160) — momentum fails both
   valuation tails (Principal; `REGIME_SPEC_V2 C`).
4. **Balance-sheet / quality residual** (the rest of the validated stack that keeps it robust and orthogonal):
   `trend_ma65_slope`, `bs_issuance` (−, sign-flipped so higher=better), `bs_asset_growth` (−), `quality_cfo_pat`.
   These are already inside the canonical 7-leg; keep them — dropping them would be *new* (untested) research.

**Combine (frozen, NEUTRAL band):** equal-weight rank-average of the present legs, `min_legs=5-of-7`, exactly the
canonical construction (`FINAL_MODEL §2`, IC_IR 1.76 PIT), with two mandate-driven modifications only:
(i) the quality gate on the universe, (ii) the growth limb added and momentum weight flexed by band.
`composite_1Y = rank_pct( mean(present legs, with mom_resid_plain × mom_weight) )`.
Corporate-action guard applied (`disc_event_in_window_1Y>0` rows NaN'd).

### 2.3 RELATIVE 5Y — valuation + growth PRIMARY, quality-gated (top 80%), non-blind sector-relative

FM logic (Principal + memory #7): at 5Y momentum barely matters; valuation + growth-longevity drive returns;
sector-neutralization must NOT be blind — a genuinely excellent absolute business deserves credit beyond its
within-sector rank.

**Universe:** apply the **5Y quality gate** (§1.4, `quality_score ≥ 0.20`) — stricter junk floor.

**Two parallel composites, then blended:**

*(a) Sector-relative limb* — reuse the **SR-v1 recipe** (`SECTOR_RELATIVE_REBUILD.md`, the adopted candidate):
5 legs sector-neutralized (rank within `sector` each date): `value_EY, mom_resid_plain, trend_ma65_slope,
quality_QMJ, bs_issuance`; `bs_asset_growth` and `quality_cfo_pat` left RAW (v1 dominates v2 — forcing AG
sector-neutral only destroys signal). At 5Y, **overweight valuation + growth-longevity**: weight `value_EY` and
the growth limb (`composite_v2_confirmed`, `sub_op_persistent`) more than the momentum/trend legs.
`sr_5Y = rank_pct( weighted-mean of the sector-neutral legs + growth-longevity )`.

*(b) Absolute-merit limb* — the SAME value/growth/quality signals ranked on the **FULL universe (not sector-
neutralized)**, so a high-ROE / durable-growth / fair-valuation business gets absolute credit:
`abs_merit_5Y = rank_pct( w_val·rank_pct(value_EY_full) + w_grow·rank_pct(growth_longevity_full) + w_qual·rank_pct(quality_score_full) )`,
with valuation + growth-longevity weighted heavily (Principal).

*Blend (non-blind neutralization, memory #7):*
```
composite_5Y = 0.60·sr_5Y + 0.40·abs_merit_5Y
```
[MY CALL, §6.4: 0.60/0.40 is a frozen prior — sector-relative stays the majority anchor (it is the more robust,
era-stable limb per `SECTOR_RELATIVE_REBUILD` era test), but 40% absolute merit implements the Principal's
"sector-neutral 8/10 → real 8.5/10" bump for genuinely excellent absolute businesses. Not fitted.]

**Data-thinness flag:** pre-2012 fundamentals are thin (`FINAL_MODEL §2, §5b`); 5Y magnitudes are DIRECTIONAL.
Ship with the flag.

### 2.4 RELATIVE evaluation harness

Run through the existing `rnd/lib/harness.py` (one code path — same battery every factor here goes through), on
`panel_pit.parquet` (survivorship-free), per horizon:

| Metric | Definition | Role |
|---|---|---|
| **Decile LS Sharpe** | annualized Sharpe of the decile-10-minus-decile-1 monthly return series | PRIMARY (mandate) |
| **Decile monotonicity** | Spearman(decile mean fwd return, decile rank); target ≈ 1 | PRIMARY (mandate) |
| **Rank-IC / IC_IR** | Spearman(score, fwd_ret) per date; IC_IR = mean/std | PRIMARY (mandate) |
| Quintile LS (supplementary) | wider buckets, ≥30-trades/parameter safety | secondary |
| Net-of-cost LS | APPROVED `COST_STANDARDS.md`, mandatory 2× stress | gate for deployability |
| **lag-test** (one-more-period lag) | delta < 0.25 | **HARD GATE** (leakage) |
| **placebo** (5 shuffles, seed=42) | IC inside ±0.02 | **HARD GATE** (leakage) |
| DSR / PBO | honest global + per-family trial count | **ADVISORY** (low-t rule; known to fail at this n) |
| Era split | 2012-15 / 15-18 / 18-21 / 21-24 + 2018/2020/2022/2024 slices | robustness (report, don't gate) |
| Drop-one-leg | dispersion of IC when each leg removed | robustness |

Hard gates = lag + placebo only. DSR/PBO advisory (firm low-t rule + `REGIME_SPEC_V2 §0 Check 3`). Verdict per
horizon: REAL / FRAGILE / FAKE + single weakest assumption.

---

## 3. ABSOLUTE SCORECARD (STANDALONE)

**Output:** per (date, symbol, horizon): `E[return]_h` (annualized %, the **intensity**), `P(up)_h` (the
**probability**), and a coarse conviction band. **Does not read the relative score.**

### 3.1 The core formula — expected return = EPS growth × PE re-rating

Classic return decomposition (a PM's actual mental model — FM lens: this is exactly how a fundamental PM
underwrites a position):
```
E[total_return_h]  =  (1 + g)^H  ×  (PE_fair / PE_current)  −  1  +  H·div_yield
                       └── earnings growth ──┘   └── multiple re-rating ──┘   └ optional carry ┘
```
where `H` = horizon in years (1M→1/12, 1Y→1, 5Y→5), and the two drivers are:

**(A) `g` — expected annual EPS growth.** Deterministic blend of realized + confirmed-forward growth from
fundamentals PIT (`_w6fg2_scored.parquet`, `stock_valuation_pit.parquet`):
```
g = clip(  0.5·op_growth_trailing  +  0.5·(confirmed forward growth proxy) ,  g_floor, g_cap )
```
- trailing = multi-year op-profit / EPS growth (`op_growth_t`, revenue via `rev_growth_t`).
- forward proxy = `rev_accel`/`z_accel` gated on `earnings_confirm_v2=1` (only confirmed acceleration counts;
  otherwise fall back to trailing). `sub_op_persistent` boosts `g` durability at 5Y (growth-longevity).
- `g_floor / g_cap` = frozen sanity clips [MY CALL, §6.5: e.g. −20% / +40% annual — prevents a single blown
  print from producing a fantasy 5-year compounding number; a PM never underwrites 60%/yr for 5 years].

**(B) `PE_fair / PE_current` — the multiple re-rating, operationalized from current valuation + regime.**
```
PE_current   = stock_valuation_pit.PE                                   # per name, PIT
PE_anchor    = median( stock's own trailing PE , sector median PE )     # "fair" absent regime
PE_fair      = PE_anchor × regime_multiplier(band)                      # regime tilts the anchor
rerating_h   = clip( PE_fair / PE_current , rr_floor, rr_cap )          # e.g. 0.5 .. 2.0 total over H
```
- `PE_anchor`: mean-reversion target = blend of the name's own trailing-median PE (expanding, causal) and its
  sector's median PE (`sector_context` / `market_state.PE_by_tier`). A name trading well below its own history and
  its sector → re-rating UP (rerating>1); well above → de-rating (rerating<1). This is where "current valuation
  level" enters.
- `regime_multiplier(band)` — the 0/65/160 band tilts the fair anchor (SIGN-ONLY use of the band):
  UNDERVALUED market (<65) → multiplier > 1 (re-rating tailwind, cheap market re-rates up);
  NEUTRAL (65-160) → 1.0; OVERVALUED (≥160) → multiplier < 1 (de-rating headwind, froth compresses).
  Frozen values [MY CALL, §6.5: e.g. 1.10 / 1.00 / 0.85]. Band ≥160 branch precautionary (never fired).
- **FM lens:** PE re-rating is capped, not open-ended — a PM assumes reversion toward fair, not to the peak
  multiple. `rr_floor/rr_cap` enforce that.

### 3.2 Intensity and probability — both derived from the two drivers, deterministically

- **Intensity** = the annualized expected return itself, `E[annual_return]_h = (1 + E[total_return_h])^(1/H) − 1`,
  mapped to a display band and an optional `[−100,+100]` conviction via a frozen monotone scale. Intensity IS the
  magnitude of `g × rerating`. Flagged MAGNITUDE-PROVISIONAL until forward grade.
- **Probability `P(up)`** = a **frozen, deterministic empirical hit-rate lookup** — NOT a fitted logistic (a
  fitted probability inherits the DSR≈0/PBO≈0.92 verdict per `ABSOLUTE_MODEL_STANDALONE §2.2` and is dishonest at
  this n). Construction, done ONCE and frozen:
  ```
  bucket = ( tercile(g) , sign(rerating−1) , band )                     # e.g. 3×2×3 = 18 buckets
  P(up)_h[bucket] = historical fraction of names in that bucket whose realized fwd_ret_h_raw > 0   # from panel_pit
  ```
  Stored as a versioned frozen table `rnd/scorecard/pup_lookup_v1.parquet`. At scoring time it is a pure lookup —
  deterministic, no refit. Ships as a COARSE band (strong-neg / neg / neutral / pos / strong-pos) with an explicit
  "magnitude provisional" flag, matching the honesty floor both prior absolute-model passes committed to.
- **Horizon shape (embrace it, don't fight it — `ABSOLUTE_MODEL_STANDALONE §4`):** at 1M the re-rating term is
  ~inert (valuation doesn't predict 1M) → `E[return]_1M` is dominated by `g`-carry and reads near-neutral, LOW
  CONVICTION. At 5Y the `g×rerating` product is where the model earns its keep. This matches the fitted-model
  finding that cross-sectional info rises with horizon — a mild corroboration, not a new claim.

### 3.3 The crisis / gold-cash state (book-level, not per-name)

Per Principal GOLD/CASH DE-RISK directive + `REGIME_SPEC_V2` layer F: at OVERVALUED (≥160) band OR a FROTH/co-
crash breadth extreme, the absolute scorecard's *book-level* recommendation de-grosses equities toward cash
(default safe asset) / gold (crisis hedge) via the ETF sleeve. This is a portfolio-construction overlay on the
long-only book, NOT a per-name score change. PRECAUTIONARY / never-fired (disclosed).

### 3.4 ABSOLUTE evaluation harness

Long-only portfolio backtest on `panel_pit.parquet`, per horizon, evaluated on the Principal's absolute lens:

| Metric | Definition | Role |
|---|---|---|
| **CAGR** | portfolio compound annual growth, realized non-overlapping compounding | PRIMARY (mandate) |
| **Calmar** | CAGR / |maxDD| | PRIMARY (mandate) |
| Sharpe, MDD, ann-vol | standard | secondary context |
| Alpha vs NIFTY500 buy-hold | CAGR − benchmark CAGR, same window | context |
| **PLACEBO portfolio** | random-selection AND cap-weighted top-quintile, IDENTICAL mechanics | **MANDATORY** — separates genuine skill from an equal-weight / small-mid-cap tilt riding the bull market (the exact confound that made `ABSOLUTE_MODEL_V2`'s +11pp CAGR unconvincing). If the scorecard doesn't beat both placebos, the CAGR/Calmar edge is a tilt, not the model. |
| Construction | long top-quintile by `E[return]_h` (or `P(up)` band), equal-weight, monthly rebalance, realized `fwd_ret_1M_raw` compounding | fixed, pre-specified before viewing results |
| Costs | gross while `COST_STANDARDS` gate applies (D-025); net-of-cost @2× once approved | disclosed |
| lag / placebo-shuffle on the driver | standard leakage gates | **HARD GATE** |
| Leave-one-non-overlapping-period-out | at 5Y especially (~3-4 independent windows) | robustness — the open question both prior passes flagged |

Verdict per horizon: REAL / FRAGILE / FAKE + single weakest assumption. Expected honest prior: 1M/1Y coarse-only,
5Y the most informative but small-independent-N; nothing certified pre-forward-grade.

---

## 4. DETERMINISM CONTRACT (what "frozen" means, concretely)

This is a HARD, TESTABLE property — run twice on identical data → **byte-identical output.**

1. **All weights/thresholds live in ONE versioned frozen file:** `rnd/scorecard/weights_v1.json` — containing
   every number in §2–§3: per-(regime, horizon) leg weights, quality-gate cutoffs (0.10 / 0.20), skip window
   (15), momentum-band weights (1/0), 5Y blend (0.60/0.40), `g_floor/g_cap`, `rr_floor/rr_cap`,
   `regime_multiplier` values, band cutoffs (65/160), breadth cutoffs (0.20). Nothing hard-coded in scoring logic.
2. **Weights are a deterministic function of (regime, horizon) — chosen ONCE, then applied mechanically.** Either
   economic-prior seeds (default here) or a one-time frozen walk-forward fit. **No per-run refit, ever.** The
   scoring path contains zero `.fit()` calls.
3. **The `P(up)` lookup and any calibration table are frozen artifacts** (`pup_lookup_v1.parquet`), built once,
   read-only at scoring time.
4. **No randomness in the scoring path.** All cross-sectional transforms are `rank_pct` / deterministic clips.
   The only RNG is the placebo shuffle in *evaluation* (not scoring), seed=42 fixed.
5. **Regime gauges are causal** (expanding-window, t≤now) — no future leak, and identical inputs reproduce them.
6. **Enforcement = a unit test in the build:** `assert score_run_1.equals(score_run_2)` (or SHA-256 of the sorted
   output parquet matches) on two independent invocations over the same input snapshot. A version bump
   (`_v1`→`_v2`) is the ONLY way any number changes, and it restarts any forward clock (D-030 discipline).

---

## 5. WHAT THE BUILDER MUST NOT DECIDE (locked by this blueprint)

- Leg list per horizon (§2.1/2.2/2.3), formula shape (§3.1), gate thresholds (§1.4), band cutoffs (§1.2),
  skip window (§2.1), blend weights (§2.3, §3), evaluation metrics (§2.4, §3.4) — all FIXED here.
- The builder implements; it does not search weights, does not add legs, does not swap `panel_pit` for
  `panel_long`, does not substitute `mom_resid_peer` for `mom_resid_plain`, does not fit `P(up)`.

## 6. JUDGMENT CALLS (explicit — mine, not the Principal's)

1. **§6.1 Quality-gate direction:** "top-90th/80th percentile" read as *drop bottom 10%/20%* (keep top 90%/80%),
   not *keep only top 10%/20%*. Reason: internal consistency (5Y must be ≥ as strict as 1Y), decile-testability,
   FM junk-floor logic. If the Principal meant elite-only (top 10%/20%), the gate cutoffs flip to 0.90 / 0.80 and
   the universe shrinks drastically — one-line change in `weights_v1.json`, flagged for his ruling.
2. **§6.2 Skip window = 15 trading days** (inside the stated "~15-20"); plateau 15/20 recorded in eval, one frozen.
3. **§6.3 1M weights 0.45/0.40/0.15** (mom/earn/qual): economic-prior seeds — momentum + earnings-surprise carry
   the 1M signal, quality is a light floor, per the Principal's own "fundamentals alone barely move 1M" logic.
4. **§6.4 5Y blend 0.60 sector-relative / 0.40 absolute-merit:** frozen prior implementing memory #7's non-blind
   neutralization; sector-relative stays majority (more era-stable), absolute merit gets material 40% weight.
5. **§6.5 Absolute-model clips & regime multipliers** (`g` −20%/+40%, rerating 0.5/2.0, regime mult 1.10/1.00/0.85):
   sanity bounds so no single print or open-ended re-rating fabricates a fantasy return; a PM underwrites bounded.
6. **§6.6 No-news = not-screened:** absence of news coverage ≠ adverse news; only an explicit negative flag
   excludes. Avoids silently dropping thinly-covered small-caps.

All six are one-line changes in `weights_v1.json` if the Principal rules differently — none require a rebuild.

## 7. NON-GOALS RESTATED (the fence)

NOT a relative→absolute conversion (§0.1). NOT the final production model — clean forward-test candidates (§0.2).
NOT new research / no per-run fitting (§0.3, §4). Does NOT touch the frozen 7-leg forward-test (§0.4). Magnitudes
PROVISIONAL until a forward grade; probability ships as a coarse band, never a false-precise %.
