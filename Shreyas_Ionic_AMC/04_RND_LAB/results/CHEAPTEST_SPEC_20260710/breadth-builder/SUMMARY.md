# BREADTH-BUILDER — Daily NIFTY500 breadth series 2020-2025 (CHEAPTEST_SPEC_20260710)

**Type:** BUILD (unblocks T1 breadth variants + F10 baselines). No pre-registered kill threshold applies; the conditioning check below is INFORMATIONAL only, as specified in the triage doc.
**Verdict: PASS (built + validated).**

## Spec
- Universe: PIT NIFTY500 membership from `NIFTY500_TICKER_2005_2025_Final.xlsx` (42 snapshots; latest snapshot <= date applied — survivorship landmine #6 handled).
- Prices: `datasets/nse_bhavcopy_daily/close_all.parquet` (official NSE closes, EQ+BE series). 2019-10 tail loaded for 20DMA warmup; series emitted 2020-01-01 -> 2025-12-31.
- Metrics per day: adv_pct, dec_pct, ad_net_pct (close vs prior close, members priced both days), pct_above_20dma (min 20 obs), ad_line (cumulative net advancers), n_members/n_matched/n_priced.
- Symbol match: union of 2020+ snapshot tickers 797 -> 785 matched in bhavcopy (98.5%); per-day matched 492-502, priced 477-500.

## Output
- `breadth_daily.parquet` — **1,552 trading days**, 2020-01-01 -> 2025-12-31 (n per era: 261/261/259/260/261/250).
- `conditioning_check.csv`, `build_breadth.py`, `inspect.py` (schema probe).

## Validation vs known crash/rally dates (sanity PASS)
| Date | Event | adv% | %>20DMA |
|---|---|---|---|
| 2020-03-23 | COVID low | 0.4 | 0.4 |
| 2020-03-24 | COVID rebound d1 | 47.7 | 0.4 |
| 2021-10-18 | 2021 top zone | 57.5 | 76.7 |
| 2022-06-17 | 2022 hike low | 28.3 | 6.9 |
| 2024-06-04 | Election shock | 6.7 | 18.1 |
| 2024-06-05 | Election rebound | 86.9 | 36.2 |
| 2025-02-28 | Feb-2025 selloff | 13.1 | 7.7 |

Distribution sane: adv% mean 46.9 (sd 21.2), %>20DMA mean 52.8 (sd 22.1), full 0->95 range hit at the right dates. Per-era means stable (adv% 45.9-47.6; %>20DMA 46.9-57.6, lowest 2022/2025 — correct).

## Informational conditioning check (NO KILL — one look, logged)
Lookahead-safe: breadth known at D-1 close conditions NIFTY 50 open->close move on D (official `nse_official_all_indices` OHLC), n=1,484 days. One obs per day => t is day-clustered by construction.

| Signal | Q1 | Q2 | Q3 | Q4 | Q5 | Q5-Q1 (pts) | t(Q5-Q1) |
|---|---|---|---|---|---|---|---|
| adv_pct(D-1) | +2.1 | -21.4 | -16.5 | -7.9 | -0.9 | -3.0 | -0.23 |
| %>20DMA(D-1) | -7.8 | -10.2 | -4.7 | -11.7 | -10.2 | -2.5 | -0.20 |

**Finding:** day-open breadth regime does NOT condition next-day intraday NIFTY open->close returns — no monotonicity, extreme-quintile spreads ~= -3 pts with |t| ~= 0.2 (noise). Mild non-monotonic dip in middle adv% quintiles (t -2.3/-2.8) is uncorrected for 12 looks and not actionable. Consistent with prior art that intraday NIFTY conditioning signals are 10-25x weaker than option breakeven. Breadth's value, if any, is as a T1 regime-engine INPUT / F10 baseline covariate, not a standalone day-direction signal.

Trial-ledger note: 2 signals x (5 quintiles + 1 spread) = informational looks, logged here per DSR discipline; no promotion claimed.
