# STOCK_SCORECARD_750 — Gate-3 Cheap-Test V2 (CURRENT v6.3 methodology)
Owner: Arjun Rao (Head of Quant) · 2026-07-20 · seed 20260719
Extends the 2026-07-17 2-pillar quintile cheap-test to the CURRENT frozen engine: full 6-pillar
dual-horizon composite, decile buckets, IC, placebo + regime hard gates. Quant layer ONLY.

## Data lineage
- Universe: `STOCK_SCORECARD_750/results/reference_full_with_portfolio.csv` — 332 names (survivor-biased
  CURRENT membership; << full 750). All 332 priced; 331 with market-cap-derived shares.
- Prices: `ALPHA_RANKER/data/prices/<sym>.parquet` (Close/Adj Close/Volume), span 2021-07-16..2026-07-16.
- Fundamentals: `ALPHA_RANKER/data/fundamentals/MASTER_fundamentals_pit.parquet` (PIT `available_date`), 35,914 rows in-universe.
- Formations: month-end, 12M-forward (Adj Close). Requested window 2021-08..2025-06 (47) — but momentum
  pillars need trailing price history, so the EFFECTIVE window is **2022-07..2025-06 (36 months)**;
  24M momentum only exists from 2023-07; the original's early "pre" regime is NOT testable here.

## Fidelity (my PIT recompute vs the frozen engine's reference CSV, current date; Spearman)
quality 0.906 · growth 1.000 · value 0.978 · stage_3y 0.920 · sector_macro 0.967 · accumulation 0.595
→ composite_3y 0.914, final_3y_adj 0.924 (STRONG) | composite_1y 0.791, final_1y_adj 0.822 (softer — mechanical
stage_1y/RSI + OBV approximations; real engine replaces 1Y stage with agent judgment for researched names).
Adopted 5yr-mean ROE/ROCE for Quality (lifted quality fidelity 0.75→0.91). mcap tercile 98% match.
Ownership-Flow pillar DROPPED (no PIT FII/DII locally) → weights renormalized over 6 pillars; regime tilt
omitted (would be lookahead). Imperfect fidelity adds RANKING NOISE → conservative (can only weaken signal).

## Decile tables — mean forward-12M return by decile (D1=lowest score … D10=highest)
Absolute levels are inflated by survivorship + the 2023-24 melt-up and are NOT tradeable; only the SHAPE matters.

| Score | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 | D10−D1 | mono ρ | IC (NW-t) | hit% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **3Y composite** (final_3y_adj) | +54.4 | +45.5 | +46.7 | +39.0 | +32.0 | +28.6 | +33.1 | +28.3 | +33.2 | +41.1 | **−13.3pp** | **−0.58** | **−0.062 (−2.53)** | 50.6 |
| **1Y composite** (final_1y_adj) | +43.0 | +35.7 | +47.0 | +37.8 | +32.7 | +33.9 | +36.0 | +36.4 | +39.8 | +39.8 | −3.2pp | −0.07 | +0.015 (+1.38) | 53.8 |

3Y is **inverted** (top decile UNDERperforms bottom); 1Y is **flat/null**. Hit-rate (% of top-decile names
beating the cross-sectional median) ≈ 50% for both → no top-decile edge.

## Hard gates
- **Placebo (200 shuffles, seed 20260719):** 3Y real −13.3pp at **0.0 percentile** of the null (p=1.000) —
  significantly NEGATIVE, not merely null. 1Y real −3.2pp at 12th percentile (p=0.88) — fails to beat null.
  → The composite does NOT pass the placebo as a positive signal. VERDICT on gate: FAIL.
- **Monotonicity (all 10 deciles):** 3Y ρ=−0.58 (inverted), 1Y ρ=−0.07 (flat). FAIL both.
- **Regime decomposition (spread | IC):** melt-up-tail 2022-07..2023-09 (n=15): 3Y −24.0pp / IC −0.114 ·
  recent 2023-10..2025-06 (n=21): 3Y −5.6pp / IC −0.025. Negative in BOTH sub-periods (worse in melt-up),
  so the negative is broad, not one outlier month.
- **36M-forward context (n=13):** spread −73pp, IC −0.067 — negative at the 3Y design horizon too.

## Distinctness — do 3Y and 1Y carry different information?
Mean cross-sectional rank-corr(composite_3y, composite_1y) = **0.53** → genuinely DISTINCT (not noisy copies).
IC: comp3 −0.034 · comp1 +0.048 · 60/40 combo −0.002 → combining does NOT beat the 1Y leg alone
(`combo_beats_best_alone = False`). They are distinct, but the "distinct" 3Y signal is the negative one.

## Factor decomposition — WHY the composite is negative (window vs composition)
Single-pillar IC over the window [full | melt-up | recent], % months positive:
| Pillar | IC full (NW-t) | melt-up | recent | pos% |
|---|---|---|---|---|
| **Value (cheapness, 4-comp)** | **+0.095 (+2.46)** | +0.183 | +0.032 | **89** |
| **Quality (5yr ROE/ROCE)** | **−0.106 (−1.93)** | −0.235 | −0.015 | 17 |
| Momentum (stage_3y) | +0.060 (+1.20) | +0.132 | +0.009 | 53 |
| Pure Q+V (equal, mirrors original) | −0.016 (−0.94) | −0.045 | +0.005 | 33 |
| Full composite 3Y | −0.034 (−1.63) | −0.041 | −0.030 | 25 |

**The composite is NOT broken — it equal-weights a genuinely POSITIVE Value pillar (t +2.46, the new
4-component blend is validated) against a regime-NEGATIVE Quality pillar (high-ROE names lagged the
2023-24 junk/cyclical melt-up), netting to ~null/negative.** This is the original's "regime-dependence"
resolved into its factor components: value won, quality lost, over the only testable window.

## Sector-exemption artifact check (financial-sector D/E exemption)
Financials = 14.6% of rows, ALL correctly `N/A-financial-sector` (never D/E-gated), mean 3Y score 48.6 ≈
non-fin 49.3, and only **8.4% of the top decile vs 15% of the universe** (ratio 0.57 — UNDER-represented).
Non-financials: 22% got AMBER/RED-gated. → The exemption removes a wrongful distress-gate WITHOUT
manufacturing any top-decile financials artifact. BENIGN.

## SEPARATE — analyst forward-growth face-validity (consistency check, NOT predictive; see face_validity.json)
113 researched names (task said 84; the set has grown), 83 join the reference universe. Analyst
`expected_next_3y_growth_pct`: rank-corr +0.70 vs historical 3Y revenue CAGR (coherent, not a mechanical
copy), −0.44 vs cheapness (sensible — high-growth priced expensive), monotone across terciles (hist CAGR
4.7→12.5→37.3). Caveat: identical for Hold (12.5) vs Sell (12.7) — growth alone does not drive the call.
→ Estimates look ANCHORED IN OBSERVABLE FUNDAMENTALS, not arbitrary. (This is a consistency check only —
it does NOT test whether the estimates predict returns.)

## Verdict vs the original ("real but fragile, regime-concentrated")
**WEAKER as a composite, RICHER in diagnosis.** On the only PIT-testable window the full composite's
cross-sectional forward-return IC is negative (3Y, significant) to null (1Y) and FAILS placebo + monotonicity.
The decomposition explains it: the score dilutes a real Value edge with a regime-negative Quality tilt, so
the monolithic 0-100 ranker inverts/nulls out-of-the-original-sample. Weakest single assumption: that the
2021-08..2022-05 window (where the original's positive result lived) generalizes — it is NOT testable here,
and everything that IS testable (2022-25) is quality-hostile/value-friendly.

## Known limitations
Survivor-biased current-membership baseline (absolute returns not tradeable; placebo shuffles within same set
→ decision robust). Ownership-Flow dropped. 1Y fidelity 0.82. n=332 → ~33/decile (thin; sector×tier value
legs cascade constantly). Gross of costs. Universe-sensitive: Q+V sign differs vs the original's 750-universe
result → a robust edge should not flip between the 750 and a 332 subset. Gate-4 needs PIT membership + full
750 + cost/turnover-matched benchmark (D-029). As a Sell/Hold RISK screen (its actual purpose), a downside-
capture / drawdown test is the fair lens — this return-IC test is the return-prediction lens, where it fails.
