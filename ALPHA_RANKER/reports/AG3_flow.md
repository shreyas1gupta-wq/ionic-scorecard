# AG3 — Delivery/Flow + Microstructure Factor Library (1M lens)

Script: `src/factors/factors_flow.py` | Output: `results/pilot_flow_factors.csv`
Complement to `src/factors/factors_technical.py` (technical/momentum, already built — not touched).

## [DATA] Delivery-parquet coverage check (all 10 pilot symbols present)

`datasets/nse_bhavcopy_daily/delivery_2022_2026.parquet` — 820,466 rows total, min/max date across
the WHOLE file (not just pilot) is **2022-10-03 → 2024-06-21**, despite the "2026" in the filename.

| symbol | min | max | n rows |
|---|---|---|---|
| ASIANPAINT | 2022-10-03 | 2024-06-21 | 450 |
| GRAVITA | 2022-10-03 | 2024-06-21 | 450 |
| HDFCBANK | 2022-10-03 | 2024-06-21 | 450 |
| HINDALCO | 2022-10-03 | 2024-06-21 | 450 |
| INFY | 2022-10-03 | 2024-06-21 | 450 |
| MARUTI | 2022-10-03 | 2024-06-21 | 450 |
| NESTLEIND | 2022-10-03 | 2024-06-21 | 450 |
| SHAKTIPUMP | 2022-10-03 | **2024-06-06** | 372 (shorter — stops 2 weeks earlier than the rest) |
| TATASTEEL | 2022-10-03 | 2024-06-21 | 450 |
| TCS | 2022-10-03 | 2024-06-21 | 450 |

## [DATA] CRITICAL FINDING — new landmine: delivery data has a live gap, not just a filename mismatch

`ALPHA_RANKER/data/prices/*.parquet` (the pilot OHLCV) covers **2024-07-16 → 2026-07-16** ("today").
The delivery parquet ends **2024-06-21**. **There is zero date overlap** between the two — delivery
history stops about 3-4 weeks before the OHLCV pilot window even begins, and is therefore **~2 years
stale relative to today**.

Implication (no-fabrication / no-lookahead rule): a "latest delivery %, spike vs 20d/60d" factor
**cannot honestly be reported as current**. Any pipeline that silently merges this delivery file
against today's price/rank and presents the result as a live signal would be quoting a 2-year-old
delivery print as if it were this week's. This mirrors the firm's existing option-data-gap landmine
(`option-data-17month-gap`) — same failure shape, different dataset. **Action item for Data Office:**
this needs a fresh NSE bhavcopy delivery pull (D-033 permits auto-fetch of reliable NSE archives) to
bring it current before delivery factors can feed a live 1M score.

## What was built given the gap (honest, not fabricated)

Two factor groups, each computed only where data actually supports it, kept separate rather than
silently blended:

1. **`theme_flow_delivery_hist_asof2024`** — delivery-dependent factors, computed **as of the last
   available delivery date per symbol** (2024-06-21, or 2024-06-06 for SHAKTIPUMP). Price series for
   this historical window comes from `datasets/nse_bhavcopy_daily/close_all.parquet` (EQ series only,
   full history back to ~2010) merged on (symbol, date) with the delivery rows — `data/prices/` does
   not reach back that far. Volume proxy for this window = delivery's own `ttl_qty` (total traded qty).
   Factors: `deliv_pct_latest`, `deliv_z20`, `deliv_z60` (z-score of latest deliv% vs rolling 20d/60d
   mean+std), `deliv_qty_trend` (slope of deliv_qty over last 20 obs, normalised by mean |deliv_qty|),
   `deliv_accum_up_minus_down` (mean deliv% on up-days minus down-days over the trailing 40 obs —
   positive = delivery concentrated on up-days = accumulation; negative = distribution).

2. **`theme_flow_micro_current`** — non-delivery microstructure factors, computed **as of today
   (2026-07-16)** straight from `data/prices/<TICKER>.parquet` — no dependency on the stale delivery
   file, so these ARE live. Factors: `vol_expansion_5_60` (5d/60d avg volume ratio), `obv_slope20`
   (OBV linear-trend slope over 20d, normalised), `amihud_illiq` (mean |return|/rupee-turnover over
   20d, ×1e6 — sign-flipped in scoring since higher = more illiquid = worse), `turnover_adj_mom`
   (21d return divided by the stock's own 20d/120d turnover ratio — rewards momentum built on
   below-average turnover over momentum built on a volume spike).

3. **`theme_flow_ALLTIME_REFERENCE_mixed_dates`** — simple average across all 9 factors, provided
   only because the task literally asked for one blended Flow/Accumulation theme. **Caveat: mixes a
   2024-06 snapshot with a 2026-07 snapshot — do not use for a live conviction call until the
   delivery data is refreshed.**

Cross-sectional percentile ranking (0-100, no hard cutoffs) applied per column across the 10 pilot
names, per `02_SCORING_ENGINE.md` convention; sign-flip only on `amihud_illiq`.

## Results (sorted by `theme_flow_micro_current`, the only genuinely live column)

| symbol | theme_flow_micro_current (live) | theme_flow_delivery_hist_asof2024 (stale snapshot) | ALLTIME ref (mixed, caveat) |
|---|---|---|---|
| MARUTI | 72.5 | 68.0 | 70.0 |
| TCS | 70.0 | 26.0 | 45.6 |
| GRAVITA | 65.0 | 34.0 | 47.8 |
| HDFCBANK | 62.5 | 70.0 | 66.7 |
| ASIANPAINT | 47.5 | 48.0 | 47.8 |
| HINDALCO | 47.5 | 76.0 | 63.3 |
| NESTLEIND | 40.0 | 34.0 | 36.7 |
| TATASTEEL | 40.0 | 74.0 | 58.9 |
| INFY | 40.0 | 34.0 | 36.7 |
| SHAKTIPUMP | 40.0 | 86.0 | 65.6 |

Full raw factor values + as-of dates per symbol: `results/pilot_flow_factors.csv`.

## Next step (not done here, flagged for Data Office / next session)

Re-pull NSE delivery bhavcopy forward from 2024-06-21 to present (D-033 auto-fetch permitted for
this source class) so `theme_flow_delivery_hist` can be recomputed as a genuinely current factor and
safely blended with `theme_flow_micro_current` into one live Flow/Accumulation theme.
