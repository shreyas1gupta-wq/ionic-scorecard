# W5RG — Regime-Conditional Momentum-Horizon + Selective Mean-Reversion

**Owner:** Arjun Rao (Quant Head) | **Date:** 2026-07-17 | **Status:** research pass, NOT certified for capital (no DSR/PBO run — see gaps below)

**Script:** `rnd/wave4/w5_regime_momentum_horizon.py` (run synchronously, foreground, full output below)
**Data lineage:** `rnd/panel/panel_long.parquet` (249 monthly dates, 2005-04-29→2025-12-05, date-list only) · `rnd/panel/cube_close_long.parquet` (5131×976, daily close, momentum/reversal built FRESH from this) · `rnd/panel/cube_bench_long.parquet` (NIFTY500 daily index, same calendar, trend input) · `rnd/panel/market_state.parquet` (249 rows, `breadth_pct_above_200dma` + `EY_hist_zscore_expanding` reused, not recomputed) · `rnd/lib/builders_w2_event.py` PIT earnings events (2642 valid events, 2020-01→2025-11) for the PEAD cut.
**Outputs:** `rnd/wave4/W5RG_regime_momentum_horizon_results.json` (full), `rnd/wave4/w5rg_regime_panel.csv` (249-row regime panel), `rnd/cards/W5RG_momentum_by_regime.json`, `rnd/cards/W5RG_selective_mr.json`, `rnd/cards/W5RG_pead_by_regime.json`.

---

## 1. Regime classification (trailing/causal only)

All inputs use only data with timestamp ≤ t: expanding-window percentile rank (min_periods=24 months — first 2 years, 2005-04→2007-02, left **UNCLASSIFIED**, not forced) of `breadth_pct_above_200dma` and of a Kaufman efficiency ratio (126d trailing) on the NIFTY500 index; sign of trailing 252-day index return for trend direction; 3-month trailing change in the already-audited richness index (`100*exp(-0.25*EY_hist_zscore_expanding)`, reused from `w4mkt_regime_test.py`).

| Regime | Rule | n months (of 249) |
|---|---|---|
| BOOMING_BULL | richness rising (3m Δ>0) AND breadth pctrank ≥0.70 AND uptrend | 47 |
| NORMAL_CHOPPY | breadth pctrank in [0.35,0.65] AND trend-efficiency pctrank ≤0.50 | 48 |
| BEAR_OVERSOLD | breadth pctrank ≤0.20 AND downtrend | 25 |
| OTHER (transitional, unclassified by design) | — | 106 |
| UNCLASSIFIED (warm-up, 2005-04→2007-02) | — | 23 |

BEAR_OVERSOLD (n=25) is composed of **9 distinct episodes**, not one: 2008 GFC (10mo), 2011 (2mo), 2013 (1mo), 2016 (1mo), 2018-19 (4mo), 2019 mid-yr (2mo), 2020 COVID (3mo), 2022 mid-yr (1mo), 2025 (1mo) — good spread, not a single-crisis artifact.

## 2. TEST 1 — Momentum lookback by regime (skip-month, built fresh on `cube_close_long`)

Cross-sectional Spearman IC and decile top–bottom spread, forward 1-month raw return, min 20 names/date.

| Regime | n mo | 3m IC (LS ann) | 6m IC (LS ann) | 12m IC (LS ann) | Winner |
|---|---|---|---|---|---|
| BOOMING_BULL | 47 | 0.042 (30.9%) | 0.061 (32.3%) | **0.064** (32.8%) | 12m (6m close 2nd) |
| NORMAL_CHOPPY | 48 | 0.026 (13.7%) | 0.031 (3.0%) | **0.065** (8.5%) | 12m by IC; 3m by raw LS spread — **mixed** |
| BEAR_OVERSOLD | 25 | −0.040 (−29.4%) | −0.035 (−36.3%) | −0.038 (−46.8%) | all negative — no lookback works |
| UNCONDITIONAL | 235 | 0.029 (15.8%) | 0.043 (27.5%) | **0.051** (22.3%) | 12m (by IC) |

**Hypothesis scorecard:**
- BOOMING_BULL "6-12m best" → **CONFIRMED**. 12m nominally best, 6m a close second, both clearly ahead of 3m on IC, IC-IR, and hit-rate. 13 distinct sub-episodes across 4 decades of bull runs (2007, 2009-10 recovery, 2014, 2016-17, 2020-21, 2023-24) — not single-episode driven. **Confidence: HIGH.**
- NORMAL_CHOPPY "3m best" → **REFUTED on IC** (12m has the highest IC of any regime×lookback cell, 0.065, hit-rate 0.73) but **3m does win on raw decile-spread** (13.7% ann vs 12m's 8.5%). This is a genuine metric disagreement, not noise-dressed-as-signal — 3m's IC is weaker/less consistent but its extreme deciles carry more raw spread in choppy markets, plausibly because 12m momentum accumulates more idiosyncratic cross-sectional dispersion even when the *index* is range-bound. **Verdict: no clean lookback-shortening effect in choppy; if anything 12m is the more consistent (higher-IC) choice even here. Confidence: MEDIUM (48 months, 20 distinct sub-episodes, but the IC/LS-spread disagreement means this cell should not be over-read).**
- BEAR_OVERSOLD "weak/negative" → **CONFIRMED, and stronger than hypothesized**: all three lookbacks show **negative** IC (momentum crash, not just decay), with 12m worst on raw LS spread (−46.8% annualized). Drop-one across all 9 episodes (including dropping the 10-month 2008 GFC block, leaving 15 months) keeps IC in a tight −0.020 to −0.049 band — **robust, not GFC-driven**. **Confidence: HIGH** (mechanism-consistent: crowded momentum unwinds violently in oversold/downtrending tape; matches the well-documented momentum-crash literature).

## 3. TEST 2 — Selective mean-reversion in oversold-extreme breadth

`oversold_extreme` = breadth pctrank ≤0.20 (same breadth criterion as BEAR_OVERSOLD's breadth leg, WITHOUT the downtrend requirement) → **n=42 months**, 12 distinct episodes. Factors built fresh from `cube_close_long`: `rev5d` = −(5-day trailing return) and `rsi2_factor` = 50−RSI(2), both matching the exact sign convention of the existing (short-panel) `H034_rev5d_1M_resid` / `H034_rsi2_1M_resid` cards that were **KILLED unconditionally** in this codebase (`rnd/cards/H034_rev5d_1M_resid.json`: verdict KILL, PBO 0.978, lag_test_delta 0.992).

| Factor | Unconditional IC (n=235) | Oversold-only IC (n=42) | Δ (multiple) | Oversold placebo IC | Oversold lag-test IC |
|---|---|---|---|---|---|
| rev5d | 0.027 (IR 0.24, hit 60%) | **0.079** (IR 0.61, hit 83%) | **2.9x** | 0.001 (clean) | −0.005 (clean — stale signal has no power) |
| rsi2_factor | 0.025 (IR 0.31, hit 62%) | **0.050** (IR 0.62, hit 67%) | **2.0x** | 0.001 (clean) | −0.007 (clean) |

Decile long-short (annualized) jumps 9.1%→**55.0%** (rev5d) and 13.4%→**31.1%** (rsi2) conditional on oversold breadth. Drop-one across all 12 episodes: IC stays in a **0.072–0.108** band for rev5d (0.044–0.054 for rsi2) — dropping the largest single cluster (2008 GFC, 15 of 42 months) actually *raises* the remaining IC (0.108), so this is not a GFC artifact.

**Confirm or refute:** **CONFIRMED — Y, with a caveat.** My unconditional IC (0.027) independently reproduces the prior-art H034 card's unconditional IC (0.0269) almost exactly, despite a different data path (full `cube_close_long` 2005-2025 vs the short `data/prices` panel 2021-2026) and different return basis (raw here vs resid there) — good cross-construction validation. The prior KILL verdict rested on PBO/lag-test machinery run on a much shorter (53-month) window; I did not re-run full PBO/DSR here (out of scope for this pass, and PBO's combinatorial-purge apparatus is not well-posed on a 42-month conditional subsample). **The regime-conditional lift (2-3x IC, clean placebo, clean lag-test, drop-one-stable) is real evidence FOR the "regime-gold" thesis** — but this is a research finding, not a certified factor: **recommend a full DSR/PBO pass restricted to the oversold-extreme subsample before any capital sizing.** n=42 months / 12 episodes clears the ≥30-observation floor in raw count but not in independent-episode count — treat as a promising, mechanism-consistent conditional signal, not yet gate-4 certified.

## 4. TEST 3 (secondary, low expectation) — PEAD by regime

Reused `builders_w2_event.load_quarterly_pit()` + the exact event-window construction of `rnd/lib/run_w3_pead_eventtime.py` (market-adjusted abnormal return, [+2td,+45cd] window), regime label = nearest-PRIOR monthly classification as of each event's `available_date` (causal). Event coverage is 2020-01→2025-11 only (PIT earnings-date matching doesn't reach further back) — this materially limits how much of history-including-2008/2020-bear this cut can actually see.

| Regime | n events | IC (continuous surprise) | p | placebo IC |
|---|---|---|---|---|
| BEAR_OVERSOLD | **2** | — | — | not computed (n<15) |
| BOOMING_BULL | 19 | 0.065 | 0.79 | 0.104 |
| NORMAL_CHOPPY | 655 | −0.003 | 0.94 | 0.010 |
| OTHER | 1966 | −0.006 | 0.78 | 0.013 |

**Verdict: PEAD stays DEAD in every regime with adequate n** (CHOPPY/OTHER IC ≈ 0, matching the unconditional −0.003 kill exactly). BOOMING_BULL's n=19 is too small to read directionally (also fails its own placebo, IC < placebo). BEAR_OVERSOLD has only 2 qualifying events in the 2020-2025 PIT window — **cannot confirm or refute in bear specifically**, honestly flagged, not fabricated. **No resurrection — consistent with the prior-art kill, and the task's own low-expectation framing.**

## 5. Encodable REGIME → SIGNAL table

| Regime (trailing-classified) | Momentum lookback to use | Confidence | Mean-reversion switch | Confidence |
|---|---|---|---|---|
| BOOMING_BULL (richness↑, breadth≥70pctile, uptrend) | **12m (or 6m)** skip-month | HIGH — 13 episodes, consistent across IC/IR/hit-rate | OFF (no oversold trigger by definition) | — |
| NORMAL_CHOPPY (breadth mid, low trend-efficiency) | **12m by IC**; note 3m wins on raw decile spread — do not hard-code a lookback-shortening rule here | MEDIUM — metric disagreement, 48mo/20 episodes | OFF unless breadth also crosses into oversold-extreme (can co-occur at the choppy/bear boundary) | — |
| BEAR_OVERSOLD (breadth≤20pctile, downtrend) | **NONE — suppress momentum entirely** (all lookbacks IC<0, LS negative, robust to drop-one) | HIGH — 9 episodes, drop-one stable | Momentum-off is itself the actionable rule here | HIGH |
| Oversold-extreme (breadth≤20pctile, regardless of trend) | n/a (see momentum row above) | — | **ON — flip to 5d-reversal / RSI(2) selectively**: IC 2-3x unconditional, clean placebo+lag, drop-one stable across 12 episodes | MEDIUM-HIGH — promising but not DSR/PBO-certified; do not size until that pass is run |
| Any regime — PEAD | n/a | — | do not add a PEAD overlay in any regime | HIGH (dead everywhere testable) |

## 6. Weakest assumption / gaps to close before this becomes tradeable

1. **No DSR/PBO run** on the oversold-conditional MR result — the single biggest gap before sizing. n=42 months / 12 episodes is enough for a directional read, not for a capital-sizing certification.
2. **NORMAL_CHOPPY's IC-vs-LS-spread disagreement is unresolved** — I report it honestly rather than picking whichever metric favors the hypothesis; a real answer needs either a robustness check on the decile construction (rank ties, e.g. `pd.qcut` duplicates='drop' behavior in a regime with fewer valid names) or simply accepting "no clean horizon-shortening in choppy" as the finding.
3. **PEAD-by-regime BEAR cell is untestable** (n=2, PIT event coverage only starts 2020) — this is a data-coverage limit, not evidence of absence; a longer PIT earnings-date history would be needed to actually test PEAD-in-bear.
4. **Regime classification is my own construction** (breadth/trend/richness thresholds and the priority order BEAR>BULL>CHOPPY are my design choices, disclosed above) — not previously reviewed/approved; recommend Red Team or Overfit-Analyst sign-off before this table is wired into any live signal logic, per RESEARCH_SOP.
