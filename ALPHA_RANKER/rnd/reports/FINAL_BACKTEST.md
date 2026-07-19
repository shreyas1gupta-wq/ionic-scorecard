# CAPSTONE — Final 1Y Model Portfolio Backtest (Arjun Rao, 2026-07-17)

**Verdict: FRAGILE-but-real.** The strategy makes money net-of-cost across the years it can actually
be tested on, but the headline long-only CAGR is inflated by a small/mid-cap size tilt vs the
cap-weighted NIFTY500 benchmark, and there is NO reliable pre-2012 data — the "21yr" framing in
FINAL_MODEL.md does not survive at the portfolio level. See caveats before quoting any number.

## Data lineage
- `ALPHA_RANKER/rnd/panel/panel_long.parquet` — 148,297 rows, 249 monthly dates 2005-04-29→2025-12-05,
  969 symbols. Used for `fwd_ret_1M_raw`, `mktcap_log`, `disc_event_in_window_1M`.
- `ALPHA_RANKER/rnd/panel/capstone_legs.parquet` — 1,310,958 rows, 12 legs. Reused 6 of 7 final legs
  as-is (`value_EY`, `trend_ma65_slope`, `quality_QMJ`, `bs_issuance`, `bs_asset_growth`,
  `quality_cfo_pat`); the 7th (PLAIN 12-1 residual momentum) was **not** cached (only its
  peer-relative sibling was) and was rebuilt fresh via the unmodified
  `run_long_confirm.build_mom_resid_12_1()`.
- `ALPHA_RANKER/rnd/panel/market_state.parquet` (breadth) + `macro_state.parquet` (India-VIX, 127
  rows, 2016-01 onward only) for the exposure scalar.
- `Shreyas_Ionic_AMC/06_TRADING_DESK/COST_STANDARDS.md` — STATUS: APPROVED (D-021); costs via the
  same tier-blend the harness already uses (large ~43bps / mid ~63 / small ~93 / micro ~123 RT),
  itself an [INFERENCE] arithmetic combination, not an independently-approved bps number.
- Code: `ALPHA_RANKER/rnd/lib/backtest_final.py`. Full run log + all figures below reproducible by
  re-running it.

## Guards passed
- `Shreyas_Ionic_AMC/04_RND_LAB/lib/guards.py` imported (mandatory per charter); monthly-frequency
  adaptation of `degenerate_flags` run on all three return series — **0 flags** (Sharpe<4 all series,
  equity-curve R²<0.98, monthly win-rate<85%).
- Disc-event contamination guard: 47 (date,symbol) rows with `disc_event_in_window_1M>0` excluded
  from realized returns before any portfolio math (data-quality filter, not an alpha filter — confirmed
  separately that ALL rows with `fwd_ret_1M_raw>300%` in the full panel are disc-flagged; the filter is
  doing real work, not decoration).
- P&L booked in the EXIT/holding period only (`fwd_ret_1M_raw`, a clean single 21-trading-day forward
  window per `PANEL_SCHEMA.md`) — no spread-across-days booking.
- Exposure-scalar lookahead FIX (self-caught): `run_capstone.py`'s existing breadth overlay used
  `rank(pct=True)` over the **full 21yr sample** to rank a value at each date — i.e., a 2008 exposure
  reading used information from 2024. Replaced with a causal **expanding** percentile rank here.

## Validation battery
| Check | Status |
|---|---|
| Walk-forward / no re-fit here | N/A — this is the AGGREGATION of already-validated legs (`incremental_value.csv`, `FINAL_MODEL.md` S1), not a fresh parameter search. No new grid was swept. |
| Parameters | 3 free choices: rank-band hysteresis (10%, reused from `run_long_confirm.apply_rank_band`), exposure floor (0.5, reused from `run_capstone.py`'s validated breadth overlay), VIX panic floor (0.70, **NEW, not independently validated** — flagged below) |
| DSR/PBO | Not recomputed at portfolio level (per-leg DSR/PBO already in `CAPSTONE_leg_cards.json` / `incremental_value.csv` — several legs individually KILL on PBO>0.5 there; this capstone does not cure that, it just shows what the combined book actually earns) |
| ≥30 trades/parameter | Top/bottom quintile averages ~120 names/month × 162 reliable months — satisfied for the portfolio-construction parameters |
| Regime slices | 2018/2020/2022 present and economically sane (see below); **2008 and 2011 NOT available** (see data-thinness finding) |

## Degenerate flags
None triggered. Independently investigated the single largest anomaly (2014 net long return
+166%) by hand: no single month or name dominates (12 positive months, ~100-108 diversified names
each), consistent with India's real 2014 small/mid-cap rally (Nifty Smallcap indices were up
70-90% that year) — judged REAL, not a data artifact, but it is exactly the kind of number that
should make you suspicious, which is why it was checked.

## CRITICAL FINDING — data-thinness, not just "pre-2012 thin" (worse than FINAL_MODEL.md's own caveat)
The composite's per-date name count **jumps from 49 to 470 between 2012-04-30 and 2012-05-31** — a
cliff, not a ramp — driven by a coverage discontinuity in the `value_EY` leg's underlying
fundamentals source. `quality_cfo_pat` (needs 5y trailing CFO/PAT) stays under 20 names until
~2015-16 and doesn't reach broad coverage until ~2018. **Practical consequence: there is no
trustworthy cross-section before 2012-05, and the "7-leg" composite is really a 4-leg
(EY+momentum+MA65+QMJ) blend for much of 2012-2015**, with issuance/asset-growth/CFO-PAT
phasing in gradually. The 2008 and 2011 bear years the task asked to show explicitly **do not
exist in usable form** in this panel — reported as MISSING below, not fabricated.

## Results — LONG top-quintile (equal-weight, monthly rebalance, 10% rank-band hysteresis)

| Metric | WITH exposure scalar | WITHOUT scalar | Long-short (top−bottom) | NIFTY500 |
|---|---|---|---|---|
| Window | 2011-11→2025-10 (168mo, but see reliability note) | same | same | same |
| CAGR | 29.5% | 34.3% | 11.6% | 14.0% |
| Sharpe | 1.61 | 1.52 | 0.71 | 0.88 |
| Sortino | 2.29 | 1.95 | 0.71 | 1.21 |
| Max DD | **-25.8%** | -37.2% | -38.5% | -30.0% |
| Avg monthly turnover (top quintile) | 17.4% | — | — | — |

### RELIABLE window only (n_universe≥400, i.e. 2012-05→2025-10, 162mo — the honest test)
| Metric | WITH scalar | WITHOUT scalar | Long-short | NIFTY500 |
|---|---|---|---|---|
| CAGR | 30.9% | 36.0% | 12.6% | 13.7% |
| Sharpe | 1.70 | 1.59 | 0.85 | 0.87 |
| Max DD | -25.8% | -37.2% | -38.5% | -30.0% |

**2x-cost stress** (scalar-on): CAGR 27.8%, Sharpe 1.53, maxDD -27.2% — costs are not the swing
factor here (turnover is moderate); the exposure-scalar DD benefit and the long-vs-LS gap matter far
more than the cost line.

## Per-calendar-year, LONG (with scalar) vs NIFTY500 vs Long-Short
| Year | Long (scalar) | NIFTY500 | Long-Short | Note |
|---|---|---|---|---|
| 2008 | **NOT AVAILABLE** | — | — | data too thin (see finding above) |
| 2011 | 2 months only, not usable | — | — | partial-year stub, excluded from headline stats |
| 2018 | **-11.0%** | -3.4% | +21.3% | Real India small/mid-cap crash year (NIFTY500 held up cap-weighted; equal-weight long was hit harder — economically sane, cross-checks against known history) |
| 2020 | **+30.3%** | +16.7% | **-28.9%** | V-shaped recovery: momentum/value LS crashed (global momentum-crash pattern), but the long-only book still benefited from the broad rally + high exposure re-risking post-March |
| 2022 | **+5.2%** | +3.0% | **+24.2%** | Rate-hike bear year: LS (quality/value) worked well; momentum-heavy long-only book was muted — sane rotation |
| 2014 | +155.2% | +37.8% | +32.6% | Real small-cap rally (verified, see Degenerate flags) — but shows the size-tilt problem below |

## THE HONEST VERDICT
**Yes, net-of-cost, across the regimes actually testable (2012-2025), the portfolio makes money —
but by much less than the long-only headline suggests.** The 29-36% long-only CAGR is contaminated
by equal-weight small/mid-cap BETA relative to the cap-weighted NIFTY500 benchmark (this is not a
fair benchmark match). The **long-short top-minus-bottom quintile spread — same universe, same size
distribution, market-neutral — is the honest edge estimate: ~11.6-12.6%/yr, Sharpe 0.71-0.85,
maxDD ~-38%.** That is real and durable across 2018/2020/2022 with economically sane regime
behavior, but it is a **single-digit-to-low-teens edge, not the 30%+ headline**, and several of its
component legs individually KILL on PBO in `incremental_value.csv` — this capstone shows what the
combined book earns, it does not cure the individual-leg overfitting flags.

## Weakest assumption
The exposure scalar's India-VIX component (panic floor at 0.70 above the 80th expanding percentile)
is a **new, untested addition** — FINAL_MODEL.md mentions VIX qualitatively but `run_capstone.py`'s
own validated overlay used breadth ONLY. The breadth-only component (halves the drawdown, -37%→-26%,
matching the FINAL_MODEL.md S3 claim) is validated; the VIX floor on top of it is not, and should be
red-teamed separately before anyone sizes off the "WITH scalar" column specifically because of VIX.

## Caveats (mandatory disclosure)
1. **Survivorship**: not independently re-verified against `NIFTY500_TICKER_2005_2025_Final.xlsx`
   PIT snapshots in this pass — panel_long's universe construction was inherited, not re-audited here.
2. **5Y-fundamentals thin pre-2012** (FINAL_MODEL.md's own caveat) is **worse than stated at the 1Y
   horizon too** — see the data-thinness finding above.
3. **Costs are DRAFT-adjacent**: COST_STANDARDS.md is APPROVED (D-021), but the per-tier bps blend
   consumed here is the harness's own [INFERENCE] arithmetic combination of the approved line items,
   not a separately-approved number.
4. Long-only vs NIFTY500 is a **benchmark mismatch** (equal-weight small/mid-tilt vs cap-weighted
   index) — do not quote the "34% vs 14%" gap as "alpha."

## Files
- `ALPHA_RANKER/rnd/lib/backtest_final.py` — the backtest.
- `ALPHA_RANKER/rnd/results/final_equity_curve.parquet` — monthly panel (168 rows × 21 cols):
  gross/net/scaled returns, turnover, cost bps, exposure, breadth/VIX percentiles, NIFTY500 return.
- `ALPHA_RANKER/rnd/reports/FINAL_BACKTEST_stats.json` — full + reliable-window stats, per-year, flags.
- `ALPHA_RANKER/rnd/reports/FINAL_BACKTEST.md` — this report.
