# BROAD_MARKET_VALUATION — Broad-Market (equal-weight + breadth) Valuation Gauge

Author: Cyrus Daruwalla (Macro & Events Strategist). Wave-4/5, ALPHA_RANKER.
Date: 2026-07-17. Tags: [DATA]/[INFERENCE]/[OPINION] per firm protocol.

Task: rebuild the market-valuation gauge on a BROAD-MARKET basis (per-stock
valuation-vs-own-history + breadth-of-expensiveness), not the cap-weighted
index PE/EY, because the Principal's read is that cap-weighting masks
broad-market froth — and because the prior aggregate-median-EY richness
index (`MARKET_REGIME.md`) never reached the 160+ band (max ≈122, structural
compression from an expanding std with the 2008 outlier permanently inside
the window).

Code: `rnd/wave4/w5bv_broad_market_valuation.py`. Run: synchronous, foreground,
completed cleanly, no errors. Outputs: `rnd/wave4/w5bv_broad_richness_series.csv`,
`rnd/panel/w5bv_broad_richness.parquet`, `rnd/panel/w5bv_stock_percentiles.parquet`,
`rnd/wave4/w5bv_results.json`, cards `rnd/cards/W5BV_*.json`.

---

## 1. What was built

Two NEW ingredients, on top of the already-PIT `stock_valuation_pit.parquet`
(EY/PE/PB per stock per month, PIT via merge_asof-backward on fundamentals
`available_date` — inherited unchanged, see `market_state.py`):

1. **Per-stock expanding percentile-vs-OWN-history** (not vs the cross-
   section, vs itself over time), min_periods=24 (2yr) monthly observations,
   for EY (inverted: high EY=cheap→`1-pctrank`), PE, and PB. Composite per
   stock = median of whichever of the 3 metrics are available that month.
   **[DATA]** EV/EBITDA was evaluated and **NOT built**:
   `MASTER_fundamentals_pit.parquet`'s 34 metrics include "operating profit"
   (screener.in convention = EBITDA) and "borrowing(s)" (gross debt) but
   **no cash/cash-equivalent line item anywhere** — an EV built as
   mktcap+borrowings with no cash netted off would systematically overstate
   EV for every cash-rich name (common in India: IT/pharma/FMCG sit on large
   investment books). Skipped and disclosed, not patched with a fabricated
   cash assumption. EY+PE+PB is the multi-metric composite actually used.
2. **Breadth**: at each date, the % of the universe sitting in its own
   top-decile / top-quintile richest-ever reading simultaneously
   (`breadth_top_decile`, `breadth_top_quintile`) — and the mirror-image
   bottom-decile/quintile for cheapness. This is a genuinely different
   signal from a single aggregate median: it answers "how SYNCHRONIZED is
   the richness across names right now", which a one-number median cannot
   distinguish from a narrow rally in a few large names.

**Combination**: `broad_median_pctile` (cross-sectional median of the
per-stock composite percentiles) and `breadth_top_quintile` are each
z-scored against their OWN expanding history (min_periods=24 valid
market-level months — same discipline as before), averaged equal-weight
(`combined_z`), then mapped `broad_richness_index = 100·exp(0.2351·combined_z)`.
The constant 0.2351 solves `100·exp(2·k)=160` — a **shape match** to the
Principal's illustrative ±2σ↔65/160 bands, computed from the band numbers
themselves, **not fit to any forward-return data** (same discipline as the
prior pass's 0.25 constant). [INFERENCE] construction; [DATA] the metrics
feeding it.

**Coverage tradeoff, disclosed up front**: this construction requires BOTH
(a) 24 months of a stock's OWN history before it contributes, AND (b) 24
valid market-level months before the market-level z-score itself is
trustworthy. Combined with `MASTER_fundamentals_pit.parquet`'s thin pre-2012
coverage (**<110 symbols/year before 2012 vs 1,400–2,300+ from 2012 on**,
[DATA], confirmed this session), the gauge's first EFFECTIVE reading is
**~2015**, not ~2007 like the prior aggregate-EY gauge. **2008 GFC is NOT
usable evidence for this construction** (0-1 valid stocks per month in that
window) — this is an honest cost of the "own-history" design, not fabricated
around. n=129 valid monthly readings, 2015-08 → 2025-12.

---

## 2. Does it reach the extremes the old gauge couldn't?

**Observed range: 57.7 (2020-03-31, COVID trough) to 139.3 (2024-06-28).**

| | Old (`MARKET_REGIME.md`) | New (this gauge) |
|---|---|---|
| Min | ≈47 (2008-11, GFC) | 57.7 (2020-03, COVID) |
| Max | ≈122 | **139.3** |
| Crosses <65 (undervalued)? | not tested in old band terms, but min≈47 implies yes | **YES — 5 months, all 2020-02→2020-05 COVID crash** |
| Crosses <80? | — | **YES — 26 months** (clusters: 2016 Jan-Jun small/midcap wobble, 2018 H2 NBFC-crisis correction, 2020 COVID) |
| Crosses ≥160 (overvalued)? | **NO, never** | **STILL NO.** Max combined_z reached only +1.41σ (vs the -2.34σ reached on the downside) — the ±2σ design target was hit on the cheap side but not yet on the rich side in this ~10yr effective sample. |

**[INFERENCE] Why the ceiling still isn't cleared, and why this is a
DIFFERENT limitation than the old gauge's**: the old gauge's 122 ceiling was
a *structural* bug — an expanding std permanently inflated by the 2008
outlier compressing every later reading. This new gauge's 139 ceiling (a
real improvement, +17 points) is a *sample-size/recency* limitation: the
effective usable history (~2015-2025) simply has not yet contained a
synchronized broad-market mania as extreme, in this metric's own terms, as
the 2020 crash was on the downside. The asymmetry itself is plausible, not
suspicious: a systemic panic can push nearly 100% of the universe into its
own cheapest-ever percentile simultaneously (crash correlations →1), while a
"everyone simultaneously at their own richest-ever" reading requires a more
universal, less panic-driven melt-up that this 10-year window has not
produced at the same statistical extreme. **The known 2017-18 broad
small/mid-cap froth episode does register as elevated (92.7-119.2, mean
104.0) but not extreme** — consistent with that episode being real but not
(per this construction) the single most extreme broad-richness reading on
file; 2024 is the actual observed max (111.7-139.3, mean 123.4).

**[DATA] Flag per task instruction**: since max=139.3 < 160, **the
overvalued-momentum test the Principal wants gated on crossing 160 is still
NOT enabled by this construction** — an honest "not yet", not a fabricated
"yes." This is a real, disclosed finding, not a failure to try: the
breadth+own-history redesign closed 60% of the gap to 160 (122→139 of the
needed +38) without forcing a fit.

---

## 3. Predictive sign: forward 1Y/5Y return, crash risk, 65 vs 80 boundary

| | 1Y (n=118) | 5Y (n=70) |
|---|---|---|
| ρ(richness, fwd return) | **-0.302** | **-0.795** |
| ρ(richness, fwd max-DD from window peak) | -0.156 | +0.316 (wrong sign, same pattern as old gauge) |
| Drop-one (ex-COVID / ex-2022-selloff) | -0.185 / -0.272 (same sign, moves but doesn't vanish) | -0.780 / -0.795 (barely moves) |
| Era-split (first vs second half of own valid range, split 2020-08) | **-0.207 vs -0.781** (same sign, magnitude UNSTABLE) | -0.832 vs NaN (second half n=6, too small to test) |

**[INFERENCE] Honest caveats on the headline 5Y number**: rho=-0.795 at 5Y
looks striking, but n=70 monthly observations over a ~2015-2020 entry window
with 60-month-overlapping forward windows is **effectively only ~1-2
independent 5Y periods** (identical caveat this desk already flagged for
cross-asset ratios in `MARKET_REGIME.md` §4) — do not quote this number as
an independently-validated 5Y edge. The 1Y era-split instability
(-0.207→-0.781) is a genuine fragility signal worth carrying forward: the
sign never flips, but the magnitude is not stable across the only two eras
this short effective history allows testing.

**65 vs 80 boundary (sign-only, per task instruction)**:
- **Below 65**: n=5 (all COVID-crash months) — **too few observations to
  test reliably** (below this desk's own n≥8 reporting floor); disclosed as
  untestable, not silently reported.
- **Below 80**: n=26 — 1Y mean fwd return **+15.3%**, 73% positive; 5Y mean
  fwd return **+134%** (≈18.7%/yr), 100% positive. **Directionally correct
  and large**, but per the n-caveats above (5Y overlap) and per the small,
  cluster-concentrated n (effectively 3 distinct dips: 2016, 2018H2, 2020),
  this is a real, sign-consistent, economically-sane result — not a
  statistically independent one. The 80 boundary is the more USABLE
  threshold of the two on this data; 65 fires too rarely in a 10-year
  effective sample to be tested honestly (not "doesn't work" — "not
  enough data to say").

**Crash-magnitude (max-DD) claim: still not confirmed**, same honest
verdict as the prior pass — richness predicts the AVERAGE forward return
direction, not the SIZE of the worst drawdown along the way (5Y max-DD rho
even wrong-signed, +0.316). Treat as a return-tilt signal, not a
drawdown-magnitude alarm — this conclusion is unchanged by the rebuild.

---

## 4. Contrast vs the old cap-weighted-adjacent (aggregate median-EY) gauge

**Correlation: ρ=0.960 (n=129)** — the two gauges tell almost the same
story most of the time. This is expected: both ultimately derive from
cross-sectional EY/PE/PB information; the new gauge adds per-stock-history
framing and breadth, but does not use an orthogonal data source.

**Divergence episodes (new reads notably CHEAPER than old, in percentile-
rank terms)**: concentrated in **2015-H2/2016-H1** and **2018-H2** (Sep-Dec
2018 the largest gaps, divergence -0.26 to -0.30 in rank-percentile terms).
**[INFERENCE]** 2018 H2 was the NBFC-crisis broad small/mid-cap correction —
the new gauge, built from EACH STOCK'S OWN history plus breadth, registered
that correction as broader/cheaper than the old single-aggregate-median-EY
z-score did. No divergence episode found in the other direction (new
reading notably richER than old) large enough to appear in the top-15 by
absolute divergence — the divergences in this sample all run one way (new
gauge cheaper than old, in corrections).

**Literal cap-weighted-vs-broad-market EY gap** (`market_EY_capw -
market_EY_eqw`, positive = cap-weighted index looks CHEAPER than the broad
equal-weight market): mean ≈ -0.014, but **currently (2025-08 → 2025-12) the
gap has flipped to consistently +0.009 to +0.010** — i.e. right now the
cap-weighted index genuinely IS reading cheaper (higher EY) than the broad
market's equal-weight median, supporting the Principal's underlying concern
directionally, in the most recent data on file. [DATA]

---

## 5. Recommendation: which gauge feeds the absolute-scorer M-term

**[OPINION] Keep the existing `EY_hist_zscore_expanding`-based richness
(the OLD gauge) as the PRIMARY `M`-term input. ADD this new broad/breadth
gauge as a SEPARATE, labeled corroborating overlay for regime commentary —
do not replace.** Same pattern this desk already used for the CAPE/Buffett/
credit-spread battery in `MARKET_REGIME_MACRO.md` §6 (single best gauge
kept, others added as corroborating tilts, not blended in).

Reasons:
1. **History length and hard-gate status.** The old gauge has a genuine
   2007-2025 usable window and already carries a hard-gated PROMOTE-
   CANDIDATE result (`W2_market_M1_EY_hist_zscore_expanding_{1Y,5Y}`, lag +
   placebo clean). This new gauge's effective window is ~2015-2025 only —
   too short, on its own, to carry the same multi-cycle credibility an
   `M`-term regime input needs.
2. **Correlation, not orthogonality.** At ρ=0.960, the new gauge is not an
   independent read at the LEVEL — swapping it in would not materially
   change `M`'s sign in most months, only around the margin (the 2015-16 /
   2018 divergence episodes).
3. **It still doesn't clear 160 either.** The specific motivation for the
   rebuild (reach the overvalued-momentum band) is not yet achieved by this
   construction (max 139.3) — it is an improvement, not a solved problem,
   so it does not yet earn a promotion to primary status on that basis.
4. **What it DOES add, genuinely**: the breadth components
   (`breadth_top_quintile`, `breadth_top_decile`, and their bottom-side
   mirrors) are a new lens with no equivalent in the old gauge — useful,
   as-is, for macro memos and regime notes ("index looks fair, but X% of
   the broad market is at its own richest-ever reading" / the literal
   cap-weighted-vs-broad-market EY gap in §4) even where the composite
   LEVEL number is highly correlated with what the firm already has on
   file. Recommend surfacing `broad_richness_index` and
   `breadth_top_quintile` in the weekly regime-note macro cadence
   alongside (not instead of) the existing richness read.

---

## Lessons for the desk

- A per-stock "vs-own-history" construction is genuinely more informative
  on BREADTH (how synchronized richness is across names) but pays for it
  with a materially SHORTER effective history than a simple aggregate-level
  z-score — check both properties before assuming "more granular" implies
  "strictly better" for a regime input that needs multi-cycle credibility.
- An asymmetric ceiling (cheap extremes reach designed ±2σ, rich extremes
  don't, in the same construction) can be a real, disclosable feature of
  panic-correlation dynamics, not evidence of a coding bug — but it must be
  reported as an observed limitation of the SAMPLE, not silently patched by
  re-fitting the shape constant to force symmetry.
- High correlation (here 0.96) between an old and a new construction is
  itself a finding: it tells you the rebuild changed the FRAMING/BREADTH
  information more than the LEVEL information — decide the new gauge's role
  (corroborating overlay vs primary input) on that basis, not on which one
  "looks more sophisticated."
