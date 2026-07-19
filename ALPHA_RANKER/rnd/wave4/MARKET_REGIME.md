# MARKET_REGIME — Market-Level Absolute Valuation Regime Layer

Author: Cyrus Daruwalla (Macro & Events Strategist). Wave-4, ALPHA_RANKER.
Date: 2026-07-17. Tags: [DATA]/[INFERENCE]/[OPINION] used throughout per firm protocol.

Task: build and test a MARKET-LEVEL absolute-regime signal — "is the whole
market cheap or dangerous" — using the Principal's SHAPE intuition (fair=100,
~60-70=very cheap/positive next-5Y, 160+=crash risk), judged on economic
logic + effect size + drop-one robustness, NOT t/DSR (low-n index-level data).

Code: `ALPHA_RANKER/rnd/wave4/w4mkt_regime_test.py`. Raw output:
`w4mkt_regime_results.json`, `w4mkt_richness_series.csv`. Cards:
`ALPHA_RANKER/rnd/cards/W4MKT_richness_1Y.json`, `..._5Y.json`,
`..._crossasset_ratios.json`, `..._exposure_scalar.json`.

---

## 1. What was built

**Did NOT rebuild valuation from scratch.** The firm already has a validated
market-level valuation series: `market_state.parquet`'s `EY_hist_zscore_expanding`
(expanding-window z-score of the cross-sectional median market earnings
yield, EY = net_profit/mktcap, PIT fundamentals, no lookahead — see
`ALPHA_RANKER/rnd/lib/market_state.py`). This column already passed a
market-level predictive test (`W2_market_M1_EY_hist_zscore_expanding_{1Y,5Y}`,
on file: rho=-0.30 @1Y / -0.25 @5Y vs forward NIFTY500 return, hard gates —
lag test + placebo shuffle — both clean, "PROMOTE-CANDIDATE"). [DATA]

**[INFERENCE] New this pass**: repurposed that z-score into the Principal's
requested continuous 0-200-style "richness index", mapped so fair value = 100:

```
richness_index = 100 * exp(-0.25 * EY_hist_zscore_expanding)
```

High EY (cheap market) → negative exponent argument is flipped sign →
richness < 100. Low EY (expensive market) → richness > 100. The constant
0.25 was picked so that a ±2σ EY z-score lands near the Principal's
illustrative ~60-70 / ~160-165 bands — a **shape match**, not a parameter
fit to any forward-return data (no forward return was used to choose 0.25).

**Observed range in this sample (2007-2025, monthly, n=226):** min ≈ 47
(Nov-2008, GFC trough — correctly flagged as the cheapest point in the
series), median ≈ 116, max ≈ 122. **The index never reached the Principal's
160+ "crash-risk" band in this history.** [INFERENCE] Likely cause: the
z-score's *expanding* std is inflated for all post-2009 years by the 2008
outlier sitting permanently in the trailing window, compressing later
readings toward the mean. So this construction is good at flagging the
CHEAP extreme (validated, 2008) but structurally under-detects genuine
overvaluation extremes after 2009 (e.g., 2017-18 midcap mania, 2021 post-
COVID melt-up) — a real calibration limitation, disclosed, not
fabricated-around. A future pass could de-trend or re-base the std window
periodically to restore range on the expensive side.

---

## 2. Predictive tests: forward return, vol, drawdown

| Metric | 1Y (n=215) | 5Y (n=167) |
|---|---|---|
| ρ(richness, fwd return) | **-0.300** | **-0.253** |
| ρ(richness, fwd realized vol) | -0.318 | -0.372 |
| ρ(richness, fwd max-DD from window peak) | +0.038 | +0.354 |
| ρ(richness, fwd worst return from entry) | +0.012 | +0.073 |

**Return-direction claim: robust.** Higher richness → lower forward return,
both horizons, both economically sane (mean reversion) and stable under
drop-one (see §3).

**Vol claim: real but counter-intuitive to naive "expensive=risky" framing.**
Richness is NEGATIVELY correlated with forward realized vol — i.e. cheap
readings (which cluster right after crashes, when vol is still elevated from
the crash aftermath) are followed by HIGHER vol, and rich/calm-bull-market
readings are followed by LOWER vol, on average. [INFERENCE] This is
consistent with vol clustering on its OWN clock (post-crash chop), not on
valuation's clock — valuation is a slow multi-year signal, vol is a fast
one. Do not read "expensive → imminent vol spike" into this data; it says
the opposite in this sample.

**Crash-magnitude claim: NOT confirmed.** Neither the peak-relative
drawdown nor the worst-return-from-entry metric shows a clean, correctly-
signed relationship with richness (rho ≈ 0 to +0.35, wrong sign at 5Y).
[INFERENCE] Interpretation: richness predicts the AVERAGE forward return
direction (mean reversion over years) reasonably well, but does NOT
reliably predict the SIZE of the worst drawdown an investor would
experience along the way — a genuinely different, and weaker, claim. This
is an honest "no" on the specific "crash-risk flag" framing of the task,
even though the "expensive-market-reads-lower-forward-return" framing holds.

---

## 3. Drop-one / era-split robustness (the honesty gate, per task brief)

| Excluded era | 1Y rho | 5Y rho |
|---|---|---|
| None (full sample) | -0.300 | -0.253 |
| Ex-2008 GFC | -0.383 | **-0.500** |
| Ex-2020 COVID | -0.264 | -0.235 |
| Ex-2022 selloff | -0.290 | -0.253 |

**Sign never flips. Magnitude never collapses toward zero.** Excluding the
2008 GFC actually STRENGTHENS the 5Y relationship (rho goes from -0.25 to
-0.50) — the relationship is not an artifact of that one crisis; if
anything 2008 is diluting the estimate (extreme cheap readings that took
years to fully pay off inflate variance without proportionally inflating
the correlation). This is the single strongest piece of evidence for the
signal: it survives removing any one of the three major crisis eras in the
sample, both horizons.

---

## 4. Cross-asset ratios (smallcap/nifty50, smallcap/gold, nifty50/gold)

24-month trailing z-score of each ratio vs forward market/smallcap returns,
2016-07 to 2026-07 (NSE official index series — no smallcap/sensex history
before 2016 on this proxy; sensex itself not on disk, used Nifty 50 as the
large-cap benchmark).

| Ratio | 1Y ρ vs mkt (n=71-77) | 5Y ρ vs mkt (n=23-29) |
|---|---|---|
| smallcap/nifty50 | -0.269 | -0.650 |
| smallcap/gold | -0.432 | -0.772 |
| nifty50/gold | -0.575 | -0.700 |

Directionally consistent with the richness index (extreme risk-appetite
readings → lower forward returns) at 1Y, where n≈71-77 monthly points give
some real (if modest) power. **The 5Y numbers are NOT independently
informative** — a 10-year sample with 60-month overlapping windows leaves
effectively 1-2 non-overlapping 5Y periods; |rho| of 0.65-0.94 there is real
arithmetic but should be read as "consistent with the same regime story,"
not as a separately validated 5Y edge on top of the market_state EY panel
(which has genuine 20-year, 167-obs depth). Flagged explicitly in the card
so this number is never quoted at face value in a later memo.

---

## 5. Exposure-scalar backtest (the intended use case)

Monthly-rebalanced NIFTY500 exposure, `scalar = clip(1 - 0.5*(richness-100)/60, lo, hi)`,
scalar known at month-start from PRIOR month-end richness (1-month lag), no
costs modeled. Two variants: symmetric (lo=0.2, hi=1.4 — levers up when
cheap) and de-risk-only (lo=0.2, hi=1.0 — never levers, realistic for this
firm's unlevered equity book per D-031/032).

| | Full sample 2007-2025 | Ex-2008 GFC |
|---|---|---|
| Always-invested (bench) | Sharpe 0.526, maxDD -60.9% | Sharpe 0.790, maxDD -30.0% |
| Symmetric scalar (levered) | Sharpe 0.447, maxDD **-69.4%** | Sharpe **0.821**, maxDD **-27.3%** |
| De-risk-only scalar | Sharpe 0.512, maxDD -60.9% | Sharpe 0.810, maxDD -27.3% |

**Full-sample verdict is negative-to-flat, and it is driven by ONE episode.**
In 2008-09, richness got progressively CHEAPER as the crash continued —
valuation cheapening and price still falling are not mutually exclusive
mid-crisis. The symmetric scalar levered up toward 1.4x DURING the ongoing
decline (before the eventual 2009 recovery), which mechanically WORSENED
realized drawdown (-69.4% vs -60.9% benchmark). The de-risk-only variant
avoided that specific harm (capped at 1.0x) but also never actually
de-risked in 2008 (richness was cheap, not expensive, throughout that
crash), so its maxDD exactly matches the benchmark for the full sample.

**Excluding 2008, both variants modestly beat the benchmark** (Sharpe 0.82 /
0.81 vs 0.79; maxDD -27.3% vs -30.0%). This is disclosed as the honest
single-episode fragility it is — not cherry-picked as the headline number.

[INFERENCE] Root cause: a valuation z-score built on an *expanding*
mean/std is a slow, multi-year mean-reversion signal (matching its own
economic-logic case in §2-§3). Applying it as a MONTHLY tactical lever
mismatches horizons: it whipsaws, and in the levered form can actively
amplify drawdown during an exogenous or continuing-decline crash it was
never designed to time (valuation getting cheaper is not the same
statement as "the bottom is in").

---

## 6. Overall honest verdict

- **Does market-valuation-band predict forward return?** Yes, both 1Y and
  5Y, sign as expected (rich→lower fwd return, cheap→higher fwd return),
  robust to dropping any of the 3 crisis eras (the strongest evidence on
  file for this layer).
- **Does it flag crash risk?** Partially. It correctly flagged the cheapest
  point in the sample (2008 trough) and correlates with LOWER average
  forward return when rich, but it does NOT cleanly predict the SIZE of the
  worst forward drawdown (rho≈0, wrong sign at 5Y) — treat it as a
  return-tilt signal, not a drawdown-magnitude alarm.
- **Do the cross-asset ratios add anything?** Modestly, directionally, at
  1Y only (n≈71-77); the 5Y cross-asset numbers are decorative given
  window overlap and should not be quoted as independent evidence.
- **Drop-one survives?** Yes — sign never flips, magnitude never collapses,
  ex-2008 actually strengthens the 5Y read.
- **Does it earn a place as a SIZING/exposure-scalar layer?** **MAYBE, with
  a real caveat.** As implemented (monthly, mechanical), the full-sample
  result is flat-to-negative and is driven by a single adverse episode
  (2008) where the "buy more as it gets cheaper" leverage side amplified an
  ongoing crash. As a DE-RISK-ONLY (no leverage), LOWER-FREQUENCY (quarterly
  /annual, strategic rather than tactical) overlay, or combined with a
  genuinely short-horizon trigger (India VIX, breadth) for the tactical leg
  while richness governs the strategic tilt, it is more defensible — but
  that combined design has not been built or tested here. Recommend: usable
  today as a QUALITATIVE regime read in memos/IC discussion (richness level
  + trend, 1-2 sentences, tagged [INFERENCE]) — NOT yet as a mechanical
  monthly sizing formula without the refinements above.

---

## Lessons for the desk

- A market-level z-score whose amplitude is set by an *expanding* std gets
  permanently compressed by the largest historical outlier — check the
  observed range against the intended interpretive bands before quoting
  levels in a memo (this pass: max observed 122, not the intuitive 160+).
- "Predicts lower average forward return" and "predicts a bigger crash" are
  DIFFERENT claims for a slow valuation signal — test both separately (as
  done here) rather than assuming one implies the other.
- Single-episode fragility in an exposure-scalar backtest (here: 2008 alone
  flips the full-sample verdict) must be surfaced via drop-one, not
  smoothed over by only reporting the full-sample number.
