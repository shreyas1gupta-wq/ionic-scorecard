# W4MVE — Does momentum fail at valuation extremes (both tails)?

Owner: Arjun Rao (Quant Head). Date: 2026-07-17. Tags: [DATA]/[INFERENCE]/[OPINION] used throughout.

Code: ad-hoc scripts run this session (results banked to disk, listed below — not
committed as permanent `rnd/lib/` modules since this is a single conditional-slice
test, not a new production factor builder). Raw output:
`ALPHA_RANKER/rnd/wave4/w4mve_raw_results.json`, `w4mve_zone_series.csv`. Cards:
`ALPHA_RANKER/rnd/cards/W4MVE_momentum_12_1_raw.json`,
`W4MVE_value_EY_zones.json`, `W4MVE_quality_QMJ_zones.json`.

---

## 1. Data lineage [DATA]

| Input | File | Rows | Date range |
|---|---|---|---|
| Valuation signal | `rnd/panel/market_state.parquet` (`EY_hist_zscore_expanding`) | 249 dates, 226 non-NaN | 2005-04-29 → 2025-12-05 |
| Momentum leg | Built fresh from `rnd/panel/cube_close_long.parquet` (976 tickers) — **not** `capstone_legs.parquet`, which has no `mom_resid_plain` leg (checked: available legs are `mom_resid_peer, trend_ma65_slope, value_EY, value_dcf_revgap, value_marketstate_M3, value_smallcap_M2, quality_QMJ, quality_cfo_pat, bs_issuance, bs_asset_growth, defensive_BAB, seasonality`) | 137,753 obs, 237 dates | 2006-04-29 → 2025-12-05 |
| Value leg (contrast) | `rnd/panel/capstone_legs.parquet`, `leg=value_EY` | 105,617 obs, 233 dates | 2006-08-31 → 2025-12-05 |
| Quality leg (contrast) | `rnd/panel/capstone_legs.parquet`, `leg=quality_QMJ` | 144,870 obs, 249 dates | 2005-04-29 → 2025-12-05 |
| Forward returns | `rnd/panel/panel_long.parquet` (`fwd_ret_1M_raw/resid`, `fwd_ret_1Y_raw/resid`) | 148,297 rows | 2005-04-29 → 2025-12-05 |

Date grids of `market_state.parquet` and `panel_long.parquet` verified **identical**
(0 dates in either set not present in the other) — zone assignment merges exactly,
no fuzzy/nearest join needed.

## 2. Valuation-band mapping [INFERENCE, reused not refit]

The Principal's 0-65/65-160/160+ gauge is mapped via the richness index **already
built and validated** in `rnd/wave4/w4mkt_regime_test.py` / `MARKET_REGIME.md`
(2026-07 wave, market-level M1 test, PROMOTE-CANDIDATE: ρ=-0.30 @1Y / -0.25 @5Y
vs fwd NIFTY500 return, hard gates clean):

```
richness_index = 100 * exp(-0.25 * EY_hist_zscore_expanding)
```

Reused verbatim (same calibration constant 0.25, chosen originally as a **shape
match** to the Principal's illustrative bands, not fit to any forward-return
data). Zone cutoffs applied exactly as given: `under`=richness<65,
`neutral`=65≤richness<160, `over`=richness≥160.

**Confirmed per the task's own expectation**: in this 2005-2025 sample the index
ranges **47.4 to 122.4** (mean 109.3) and **never reaches 160**. Zone counts at
the market-state date grain (226 dates with a valid z-score, 24-month
expanding-window warm-up excluded):

| Zone | n dates | % of sample |
|---|---|---|
| under (<65) | **7** | 3.1% |
| neutral (65-160) | **219** | 96.9% |
| over (≥160) | **0** | 0% |

The 7 "under" dates are **one single episode, back to back**: 2008-09, 2008-10,
2008-11, 2008-12, 2009-01, 2009-02, 2009-03 (the GFC trough). Not 7 independent
draws — read as **n=1 crisis event** with 7 overlapping monthly readings inside it.

**Important negative check, run before trusting the zone split**: 2020-03 (COVID
crash) does **NOT** register as an undervalued extreme on this gauge — richness
only dipped to ≈97 (still solidly neutral), because it was a fast V-shaped price
crash with earnings not yet reprinted and a ~2-month recovery, so the median
EY z-score barely moved. **This valuation-extreme test, as operationalized here,
has exactly one historical "undervalued extreme" episode in 21 years, and zero
"overvalued extreme" episodes** — the task asked me to be honest about low-n and
this is the sharpest form of that: the over-tail is **completely untested**, not
weakly tested.

## 3. Guards passed?

- PIT: `EY_hist_zscore_expanding` is expanding-window (t'≤t only, min_periods=24) —
  already audited in `market_state.py`/PANEL_SCHEMA.md. Momentum factor uses only
  `p[t-21]/p[t-252]` (data ≤ t). Forward returns are `panel_long`'s own
  `available_date`-gated, no-lookahead columns. No new PIT violation introduced.
- Zone assignment merge verified exact-date (no leakage from a nearest/tolerance
  join smuggling future valuation into a past date).
- Costs: not modeled — this is a conditional-IC/decile-spread diagnostic, not a
  tradeable strategy submission; no cost claim made.
- Min-names gate: 20 names/date (harness convention) applied uniformly; this is
  **why value_EY's under-zone shows 0 usable dates** (see §5) — a real data
  gap, not a filtering choice that flatters the result.

## 4. Validation battery — honest, not a full Gate-4 pass

This is a **conditional-slice diagnostic**, not a strategy certification. Full
DSR/PBO/walk-forward is not meaningful on n=7 (under) or n=0 (over) — those fail
the ≥30-obs/parameter floor by construction, and computing a DSR on 7 overlapping
monthly points would be theater, not evidence. What WAS run:

| Check | Neutral zone (momentum) | Under zone (momentum) |
|---|---|---|
| n dates (1M IC) | 217 | 7 |
| Era split (pre/post 2015) | IC 0.065 (n=87) → 0.052 (n=130), **stable, no decay** | n too small to split |
| Placebo (shuffle target within date, 5x) | IC ≈ 0 (+0.002 to -0.004) vs real 0.057 — **real signal confirmed, not a methodology artifact** | not run (n=7 insufficient for a placebo distribution to mean anything) |
| Read | Genuine, repeated, era-stable, placebo-clean momentum edge | Single-episode, directionally consistent with "momentum crash," **not statistically certified** |

## 5. Per-zone results table (1M horizon, primary; 1Y in parentheses)

IC = mean daily-cross-sectional Spearman rank IC vs `fwd_ret_resid` (beta-stripped).
Decile L-S = annualized top-minus-bottom-decile spread of `fwd_ret_raw` (tradeable).

| Factor | Zone | n dates | IC (1M) | IC_IR (1M) | Decile L-S ann (1M) | IC (1Y) | Decile L-S ann (1Y) |
|---|---|---|---|---|---|---|---|
| **Momentum 12-1** | under | 7 | **-0.042** | -0.16 | **-82.4%** | **-0.170** | **-91.6%*** |
| | neutral | 217 | **+0.057** | 0.39 | **+22.3%** | +0.105 | +16.5% |
| | over | 0 | n/a — untested | | | | |
| | ALL (blended) | 224 | +0.054 | 0.35 | +19.0% | +0.096 | +13.0% |
| Value (EY) | under | **0** | untestable (data gap, see below) | | | | |
| | neutral | 168 | +0.033 | 0.36 | +6.0% | +0.079 | +13.9% |
| | over | 0 | n/a | | | | |
| Quality (QMJ) | under | 7 | -0.075 | -0.59 | **-41.6%** | +0.154** | **-54.3%*** |
| | neutral | 217 | +0.066 | 0.47 | +11.8% | +0.145 | +26.9% |
| | over | 0 | n/a | | | | |

\* 1Y figures at n=7 (under zone) are near-fully-overlapping windows (12-month
forward return sampled monthly over a 7-month span) — essentially **one 1Y
observation stretched into 7 rows**, reported for completeness, not as 7
independent confirmations.
\*\* Quality's 1Y IC (+0.15) and 1Y decile spread (-54%) have **opposite signs**
at n=7 — a small-sample rank-vs-spread inconsistency, not a coherent "quality
holds" signal.

**Value's under-zone is untestable, not merely thin**: `capstone_legs.parquet`
`value_EY` has only 6 symbols with valid EY per date through Sep-2008→Mar-2009
(fundamentals-data coverage gap during the crisis, verified row-by-row), below
the 20-name minimum — every under-zone date for value drops out before an IC can
even be computed. I cannot report on value's undervalued-extreme performance
with this dataset; I am flagging the gap rather than silently omitting the row.

## 6. Degenerate-result checks

- Sharpe/return magnitudes in the under-zone (-82% to -91% annualized) look
  "too extreme to be real" — this is expected and correct: these are
  **single-episode, overlapping-window, annualized-from-a-7-month-sample**
  figures (a crisis-quarter momentum crash, matching the well-documented
  Daniel-Moskowitz 2016 "momentum crash" phenomenon), not a claim about a
  repeatable annual return. Flagged, not presented as a Sharpe.
- No win-rate/P&L-concentration or R²-equity-line checks apply (no equity
  curve was built — this is an IC/decile-spread diagnostic).
- Neutral-zone momentum (IC 0.057, IR 0.39) is unremarkable in magnitude
  (no Sharpe>4 or >75%-win-rate flags) — consistent with a real, modest,
  well-known factor, not an artifact.

## 7. Verdict

**Does momentum fail BOTH extremes? PARTIAL.**

- **Undervalued extreme (<65): CONFIRMED, but on a single historical episode.**
  Momentum IC flips negative (-0.04 to -0.17) and the decile long-short spread
  turns sharply negative in the 2008-09 GFC trough — directionally exactly the
  "post-bottom momentum crash" the Principal's economic story predicts. This is
  real, economically well-documented behavior, and it survived the one check
  available (both 1M and 1Y horizons agree in sign) — but it is **n=1 crisis
  event**, not a statistically replicated pattern. Quality also broke down in
  this same window (inconsistently), and value could not be tested at all —
  so this reads as "the single most violent episode in 21 years broke momentum
  the hardest and cleanest," not "momentum specifically and uniquely fails while
  other factors are unaffected."
- **Overvalued extreme (≥160): NOT TESTABLE, not "not supported."** This
  valuation gauge never printed a reading above 122 in 21 years of Indian
  market history (2005-2025, including 2008 and 2020). There is **zero data**
  to confirm or deny the bubble-top-reversal half of the hypothesis with this
  signal. Any gate built for this tail is a precautionary/economic-logic
  extrapolation, not an empirically validated rule.
- **Neutral zone: CONFIRMED strong and robust.** IC +0.057 (1M) / +0.105 (1Y),
  stable across two independent half-sample eras (pre/post 2015), placebo-clean.
  Since 96.9% of all dates in this sample are neutral-zone, **the neutral zone
  is responsible for effectively all — in fact slightly more than all — of the
  full-sample edge**: the blended full-sample IC (0.054, 1M) is *lower* than
  the neutral-only IC (0.057) precisely because the 7 under-zone months pull it
  down; there is no month in this sample where the full-sample number is
  flattered by an extreme-zone contribution.

**The single weakest assumption**: that `EY_hist_zscore_expanding`-derived
`richness_index` is *the* correct operationalization of "valuation extreme."
It is a **slow, multi-year, earnings-anchored** measure (expanding mean/std of
median EY) — it is structurally incapable of registering a fast price-driven
crash (2020) as "undervalued," and structurally incapable (in this 21-year
window) of ever reaching an "overvalued" reading at all. A faster or
differently-anchored valuation gauge (e.g., PE/PB-based, or one using a
rolling rather than expanding window) might produce a materially different
zone map and a materially different verdict on the overvalued tail — that has
not been tested here.

## 8. Encodable gate (if adopted)

```
if richness_index < 65:       momentum_weight = 0.0   # single-episode evidence (2008-09), directional not certified
elif richness_index < 160:    momentum_weight = 1.0   # confirmed, era-stable, placebo-clean, 96.9% of history
else:                          momentum_weight = 0.0   # NO empirical basis in 21yr India sample (never observed) -- 
                                                        # precautionary only, on economic-logic grounds, not backtested
```

Recommended framing for CIO/FM: encode as a **precautionary de-risking gate**,
not a certified alpha-conditioning rule for the tails. The neutral-zone
momentum edge itself is real and already carries independent evidence; the
tail-conditioning is a risk-management overlay (kill momentum sizing when the
market prints a reading this gauge has only ever produced once, in the worst
crisis in the sample) rather than a statistically proven edge-improvement.
Should be re-tested the next time richness prints <65 (watch for it) or if a
faster valuation gauge is built that can actually reach >160.
