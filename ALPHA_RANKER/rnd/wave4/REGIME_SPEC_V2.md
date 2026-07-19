# REGIME_SPEC_V2 — Regime / Absolute-Layer Blueprint

**Owner:** Arjun Rao (Quant Head) | **Date:** 2026-07-17 | **Status:** research-certified for the oversold-MR switch and the momentum-by-regime table; the valuation-extreme gate and gold/cash absolute state remain PRECAUTIONARY (economic-logic, not fully backtested — disclosed below). NOT yet Gate-4/IC-adopted as a live overlay.

**Certification script (this pass):** `rnd/wave4/w5mr_certify.py` (run synchronously, foreground, full output logged below). **Outputs:** `rnd/wave4/W5MR_CERT_results.json`, cards `rnd/cards/W5MR_cert_dropone.json`, `W5MR_cert_era.json`, `W5MR_cert_dsr_pbo.json`, `W5MR_cert_threshold.json`, `W5MR_cert_netcost.json`.
**Prior research (reused verbatim, not re-derived):** `rnd/wave4/REGIME_MOMENTUM_HORIZON.md` (momentum-by-regime + the original selective-MR find), `rnd/cards/W5RG_selective_mr.json`, `rnd/wave4/MOMENTUM_VALUATION_EXTREMES.md` (momentum-extreme gate), `rnd/wave4/BROAD_MARKET_VALUATION.md` + `rnd/wave4/MARKET_REGIME.md` (richness/valuation band), `rnd/wave4/RESEARCH_QUEUE.md` (Principal 2026-07-17 GOLD/CASH DE-RISK directive), `rnd/wave4/ABSOLUTE_SCORER_SPEC.md`.

**Data lineage (this pass):** `rnd/panel/panel_long.parquet` (148,297 rows, 31 cols — date-list only, 249 monthly dates 2005-04-29→2025-12-05) · `rnd/panel/cube_close_long.parquet` (5,131×976 daily close — momentum/reversal built fresh) · `rnd/panel/cube_bench_long.parquet` (5,131×1, NIFTY500 index, trend input) · `rnd/panel/market_state.parquet` (249×27, `breadth_pct_above_200dma` + `EY_hist_zscore_expanding` reused, not recomputed).

---

## 0. Certification of the oversold-MR "regime-gold" find — RESULTS

Task: certify `rev5d`/`rsi2_factor` IC lift (0.027→0.079 rev5d, 2.9x; 0.025→0.050 rsi2, 2.0x) conditional on breadth ≤20th expanding percentile, previously found with clean placebo (0.001/0.0005) and clean lag-test (−0.005/−0.007) and an aggregate drop-one range. This pass runs the harder version of every check.

### Check 1 — full per-episode drop-one, explicit lift multiple (12 episodes)

| Factor | Full oversold lift | Drop-one lift range (min–max) | Episodes where lift falls below 2x when dropped |
|---|---|---|---|
| **rev5d** | 2.91x | **2.68x – 4.01x** | **0 / 12 — holds for every single episode** |
| rsi2_factor | 1.98x | 1.74x – 2.14x | **7 / 12 — the >2x claim does NOT survive dropping most episodes** (never goes below unconditional, but the "2x" framing is fragile) |

**Verdict: rev5d's lift is drop-one-robust in the strict sense the task asked (any single episode removed, lift stays >2x). rsi2_factor's is not** — it stays positive and elevated (1.74x floor) but the "2x" number was closer to an aggregate artifact than a per-episode-robust one for that specific factor.

### Check 2 — era split

| Factor | Pre-2015 (n=23) | Post-2015 (n=19) | Third 1 (2007-03→2009-01, n=14) | Third 2 (2009-02→2018-10, n=14) | Third 3 (2018-11→2025-04, n=14) |
|---|---|---|---|---|---|
| rev5d | IC 0.074 | IC 0.084 | **IC 0.028 (lift ≈1.04x — barely above unconditional)** | IC 0.131 (4.85x) | IC 0.077 (2.85x) |
| rsi2_factor | IC 0.044 | IC 0.057 | IC 0.042 (1.66x) | IC 0.053 (2.09x) | IC 0.055 (2.19x) |

No era flips sign for either factor (holds directionally, full period). **But rev5d's first third — dominated by the 2008 GFC, the largest single episode (15 of 42 oversold months) — is nearly unconditional-strength, not lifted**; the 2.9x aggregate is carried almost entirely by the post-2009 two-thirds. rsi2_factor is comparatively era-stable (1.7x–2.2x throughout). **Verdict: era-split holds directionally for both, but rev5d's magnitude is front-loaded-weak / back-loaded-strong — a real nuance the aggregate number hides.**

### Check 3 — DSR/PBO (ADVISORY ONLY, per firm's low-t rule for regime-conditional research — hard gates are placebo+lag, already clean)

| Factor | n_obs (LS series) | PBO (single-factor CSCV, n_blocks=6) | DSR @ N=1 | DSR @ N=613 (global trial count) |
|---|---|---|---|---|
| rev5d | 42 | 1.00 | 0.9997 | **0.0000** |
| rsi2_factor | 42 | 1.00 | 1.0000 | **0.0000** |

As expected and disclosed up front: at n=42 months, the harness's single-factor CSCV/PBO adaptation and the DSR deflation at any honest multi-trial count (this program has logged 613 total trials, 124 distinct families) crush both numbers — **this is a known small-sample degeneracy of the DSR/PBO machinery at this scale, not new evidence against the finding.** Per the task's own framing and `RESEARCH_QUEUE.md`'s standing low-t rule, these are recorded for the file, **not treated as a gate**. The gates that matter (placebo, lag-test) were already clean in the prior pass (rev5d placebo 0.0011/lag −0.0047; rsi2 placebo 0.0005/lag −0.0066) and are unchanged by this run.

### Check 4 — breadth threshold sensitivity (plateau or knife-edge?)

| Factor | 10th pctile (n=19) | 20th pctile (n=42, baseline) | 30th pctile (n=63) | Shape |
|---|---|---|---|---|
| rev5d | IC 0.064 (2.4x), LS ann 66.8% | IC 0.079 (2.9x), LS ann 55.0% | IC 0.073 (2.7x), LS ann 47.6% | **PLATEAU** |
| rsi2_factor | IC 0.065 (2.6x), LS ann 27.9% | IC 0.050 (2.0x), LS ann 31.1% | IC 0.044 (1.7x), LS ann 27.1% | **PLATEAU** |

**Verdict: PLATEAU, not knife-edge.** IC lift stays in a 1.7x–2.9x band across three materially different thresholds (10th/20th/30th) for both factors — no cliff at any specific cutoff. This is real evidence the effect tracks the underlying "breadth washout" mechanism rather than exploiting a single arbitrarily-chosen percentile.

### Check 5 — net-of-cost (APPROVED `COST_STANDARDS.md`, D-021, mandatory 2x stress)

Cost model used (all APPROVED-status numbers, no drafts): STT equity delivery 0.1% both sides (0.20% round trip) + mid-cap slippage tier 20bps one-way (0.40% round trip) + brokerage/exchange/SEBI/GST (~3bps, immaterial) = **0.63% round-trip per leg**; a decile L-S book trades both legs → **1.26% per active month at 1x**, **2.52% at the mandatory 2x stress**. Cost applied only in the ~42 active (oversold) months out of 249 (17% of history) — this switch does not add turnover in the other 83%.

| Factor | Gross monthly | Net @ 1x cost | Net @ 2x stress | Survives 2x? |
|---|---|---|---|---|
| **rev5d** | 3.72% | 2.46% | **1.20%** | **YES** |
| rsi2_factor | 2.28% | 1.02% | **−0.24%** | **NO** |

**Verdict: rev5d clears the mandatory 2x cost stress with room to spare (1.20% net monthly, ~15% net annualized even before considering it only fires ~17% of the time). rsi2_factor does NOT survive 2x stress** — it is cost-negative under the firm's own binding promotion rule.

### Overall certification verdict

**rev5d is the certified oversold-MR switch: passes per-episode drop-one (0/12 failures), era-split (directionally, with a disclosed GFC-era weak-spot), threshold-plateau, and net-of-cost @2x stress.** Clean placebo+lag from the prior pass stand unchanged. DSR/PBO are advisory-only per the low-t rule and both fail at honest trial counts — a known, disclosed small-sample limitation, not a new red flag.

**rsi2_factor is FRAGILE by comparison**: weaker per-episode drop-one (7/12 episodes push its lift below 2x), and it does **not** survive the mandatory 2x cost stress. **Recommendation: encode `rev5d` as the primary/only sized oversold-MR switch; keep `rsi2_factor` as a secondary confirming/diagnostic signal only (e.g., require both to agree in sign before firing), never sized on its own.**

This is a research-tier certification (placebo/lag hard gates clean, drop-one/era/threshold/cost all run and disclosed honestly with their exact failure modes) — **still not a full Gate-4 pass** (no walk-forward OOS split reserved, DSR/PBO uninformative at this n as shown above, ≤5-parameter and ≥30-trades/parameter floors are borderline given only 12 independent episodes). Recommend Red Team review before this switch is wired into any live signal logic, per RESEARCH_SOP.

---

## 1. The full REGIME → SIGNAL table

| Layer | Regime / state | Rule | Confidence | Source |
|---|---|---|---|---|
| **A. Momentum lookback by regime** | BOOMING_BULL (richness↑ 3m, breadth≥70pctile, uptrend) | **12m (or 6m) skip-month momentum** | HIGH — 13 episodes, IC/IR/hit-rate consistent | `REGIME_MOMENTUM_HORIZON.md` §2 |
| | NORMAL_CHOPPY (breadth 35-65pctile, low trend-efficiency) | 12m by IC (highest-IC cell); do NOT hard-code a lookback-shortening rule — 3m wins only on raw decile spread, a genuine metric disagreement | MEDIUM — 48mo/20 episodes | ″ |
| | **BEAR_OVERSOLD** (breadth≤20pctile, downtrend) | **SUPPRESS momentum entirely** — all lookbacks IC<0 (momentum crash), robust to drop-one across all 9 episodes | HIGH — 9 episodes, drop-one stable (−0.020 to −0.049 band) | ″ |
| **B. Oversold mean-reversion switch** | Oversold-extreme (breadth ≤20th expanding pctile, *regardless of trend* — can co-occur with BEAR_OVERSOLD or sit inside NORMAL_CHOPPY) | **Flip ON: 5-day reversal (`rev5d`) long-short.** OFF everywhere else. Sized on `rev5d` only (see §0 verdict); `rsi2_factor` as confirm-only, not sized. Threshold is a plateau (10th/20th/30th all work) — 20th is a reasonable operating choice, not a fragile pick. | **HIGH for rev5d (this pass's certification)**; rsi2_factor MEDIUM-LOW (drop-one/cost-fragile) | This pass (§0) + `REGIME_MOMENTUM_HORIZON.md` §3 |
| **C. Momentum-extreme valuation gate** (Principal's gate) | `richness_index = 100·exp(−0.25·EY_hist_zscore_expanding)` (reused, not refit) — **<65**: undervalued extreme | `momentum_weight = 0.0` — directionally confirmed (2008-09 momentum crash, IC −0.04 to −0.17) but **n=1 crisis episode**, not statistically replicated | MEDIUM (mechanism-consistent, single-episode) | `MOMENTUM_VALUATION_EXTREMES.md` §7-8 |
| | **65–160**: neutral | `momentum_weight = 1.0` — confirmed strong, era-stable (pre/post-2015), placebo-clean, 96.9% of 21yr history | HIGH | ″ |
| | **≥160**: overvalued extreme | `momentum_weight = 0.0` — **NEVER OBSERVED in 21yr India sample** (max reached ≈122–139 across two independently-built gauges). Precautionary, economic-logic only, zero empirical basis. | N/A — untestable, disclosed as such | `MOMENTUM_VALUATION_EXTREMES.md` §7, `BROAD_MARKET_VALUATION.md` §2 |
| **D. Broad-valuation band** (the same richness index, used as a standalone predictor, not just a gate) | Continuous | ρ(richness, fwd 1Y return) ≈ −0.30, ρ(fwd 5Y) ≈ −0.25 to −0.80 depending on gauge build; sign never flips excluding any single crisis era (2008/2020/2022) — genuine slow multi-year mean-reversion signal, use as a 5Y-horizon input (thin at 1M), not a monthly tactical lever (the monthly exposure-scalar backtest was flat-to-negative full-sample, driven by the single 2008 episode where richness cheapened mid-crash — see `MARKET_REGIME.md` §5 / `rnd/cards/W4MKT_exposure_scalar.json`) | HIGH at 5Y / MEDIUM at 1Y / explicitly NOT-a-monthly-lever | `MARKET_REGIME.md`, `BROAD_MARKET_VALUATION.md` |
| **E. Breadth-extreme de-risk** | `breadth_pctrank_exp ≤ 0.20` (same breadth leg as layer B, used here for GROSS EXPOSURE, not stock selection) | De-risk equity gross exposure when breadth is this washed out — this is the layer where a genuine short-horizon trigger belongs (the valuation-based monthly scalar failed this job per layer D; breadth is faster-moving and is what layer B's own plateau test (§0 Check 4) shows is a real, non-arbitrary washout signal) | MEDIUM — breadth-as-de-risk-trigger itself not separately backtested as an exposure scalar in this pass (only as the MR switch's conditioning variable); flagged as the natural next test, not yet run | This pass (§0) + `rnd/cards/W4MKT_exposure_scalar.json`'s own recommendation ("pair with a genuinely short-horizon trigger... for tactical de-risking rather than relying on this valuation series alone") |
| **F. Gold/cash absolute state** | Richness ≥160 (crisis/bubble-top band) OR a co-crash state where cross-sectional leg correlations converge toward 1 (relative selection stops protecting) | **De-gross equities, allocate to GOLD/CASH via the ETF sleeve** — cash is the explicit default safe asset, gold the crisis hedge (not the reverse). Rationale: in genuine crisis, asset ALLOCATION protects when relative stock-picking cannot (everything falls together). | **PRECAUTIONARY / ECONOMIC-LOGIC ONLY — richness has never crossed 160 in 21yr India sample (layer C); this state has NEVER FIRED and cannot be backtested with the data on hand.** Not a statistically validated rule. | `RESEARCH_QUEUE.md` "GOLD/CASH DE-RISK (Principal 2026-07-17)" directive, `ABSOLUTE_SCORER_SPEC.md` |
| **G. PEAD by regime** | Any regime | **No PEAD overlay, anywhere** — dead unconditionally (IC ≈ −0.003) and dead in every regime with adequate n (CHOPPY IC −0.003, n=655; OTHER IC −0.006, n=1966); BEAR_OVERSOLD has only n=2 qualifying PIT events 2020-2025 — untestable in bear specifically, not evidence of absence there, but no resurrection anywhere testable | HIGH (dead everywhere with adequate n) | `REGIME_MOMENTUM_HORIZON.md` §4 |

---

## 2. How the layers compose (operating logic, not yet wired into a live signal)

1. **Classify the regime** (A/B's trailing rules) and **read the two continuous gauges** (richness index for C/D/F, breadth expanding-percentile for B/E) at each month-end, causally (t≤now only).
2. **Stock-selection layer** (relative, per-name ranking): apply the regime-appropriate momentum lookback (A), multiplied by the valuation-extreme gate (C: 0/1/0 weight by richness band). If breadth is oversold-extreme (≤20th pctile, layer B), REPLACE the momentum sleeve with the `rev5d` reversal switch for that month; momentum itself is separately suppressed in BEAR_OVERSOLD regardless (A), so there is no double-counting conflict — B is the active signal exactly where A already says "do nothing."
3. **Exposure/gross layer** (absolute, book-level): richness (D) as a slow 5Y-horizon tilt input only, never a monthly lever (the monthly scalar backtest failed — see D). Breadth-extreme (E) as the faster tactical de-risk trigger — **this specific use (breadth as an exposure scalar, not just an MR-switch conditioner) has not itself been backtested and is flagged as the next test**, not certified here.
4. **Absolute/crisis-state layer**: richness ≥160 (F) → route to gold/cash via the ETF sleeve. **This state has never printed in 21 years of Indian market history on the gauges built so far** — it ships as a precautionary rule with a clear, disclosed empirical gap, to be watched for and re-tested the moment it (or a faster-reading valuation gauge that CAN reach 160) actually fires.
5. PEAD (G): permanently OFF, no regime exception.

---

## 3. Single weakest assumption (per layer, carried forward honestly)

- **B (this pass's subject):** the 2.9x rev5d lift is drop-one-robust per-episode, but its era-split shows the edge is much weaker in the GFC-dominated first third of history (≈1.04x lift) than afterward (2.85x–4.85x) — if the mechanism has structurally changed (e.g., more liquid/efficient short-term reversal markets, algo-driven fades, changed circuit/settlement rules) the forward edge may sit closer to the recent-era numbers than the full-sample 2.9x headline.
- **C/D/F (richness/valuation band):** the entire ≥160 "gold/cash" state and the momentum-extreme-overvalued gate rest on a threshold **never observed** in the sample used to calibrate it (it was shape-matched to the Principal's illustrative bands, not fit to data) — genuinely untestable until either more history accumulates or a materially faster valuation gauge is built.
- **E (breadth-as-exposure-scalar):** not actually backtested as a book-level de-risk trigger in this pass — only validated as the MR switch's conditioning variable. Recommend this as the next concrete test before layer E is treated as certified rather than a design placeholder.
