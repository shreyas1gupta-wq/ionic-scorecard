# AG2 -- Earnings-PIT Catalyst / Anticipation Module (1M primary, 1Y secondary)

Run date (REF_DATE): 2026-07-16

## Data vintage (verified, not fabricated)
`quarterly_earnings_pit.parquet` for all 10 pilot names caps at quarter_end 2023-09-01 / available_date ~Oct-Nov 2023 (13 quarters back to 2020-09-01, exact per-symbol counts below). Growth/surprise factors are therefore computed on the LATEST quarter the PIT source actually has for each name, not a live current print. The days-to/-since-result calendar factors use the separate, actively-refreshed `earnings_dates.csv` / `forthcoming_results.csv` feed and DO reflect real 2026 dates.

Quarters available per pilot symbol: all 10 = 13 (range 2020-09-01 to 2023-09-01).

## Method
- Revenue = `Sales` for non-financials, `Revenue` (total income) for banks/NBFCs (Sales is NaN there, e.g. HDFCBANK).
- YoY = latest quarter vs same quarter prior year (quarter_end lag 4). QoQ = latest vs immediately prior quarter.
- Growth ACCELERATION = latest YoY minus prior-quarter's own YoY (Net Profit and Sales).
- OPM change = latest OPM% minus trailing-4-quarter average OPM% (own history, no sector comparison).
- Earnings-surprise proxy = actual Net Profit / Sales vs a linear-trend expectation fit on the PRECEDING 4 quarters and extrapolated one step forward (own-trend beat/miss, not a sell-side consensus -- we don't have one).
- Consistency = count of the last 4 quarters (that have enough trailing history) whose Net Profit surprise was positive (0-4).
- days_to_next_result / upcoming_1m_event(<=30d) from `forthcoming_results.csv`; days_since_last_result / post_earnings_drift_window(<=30d) from `earnings_dates.csv` (actuals only, filtered <= REF_DATE).
- All factors -> cross-sectional percentile (0-100) among the pilot 10, no hard cutoffs (per `02_SCORING_ENGINE.md`); Catalyst/EarningsMomentum theme = simple mean of the available percentiles. Uncalibrated relative rank only.

**Caveat:** TATASTEEL's np_yoy/np_surprise_pct are large negative multiples (e.g. -602%) because Net Profit swung from a small positive base (Rs 1,297cr, Sep-2022) to a loss (Rs -6,511cr, Sep-2023) -- a real, verified swing (checked against the raw parquet), not a bug, but a reminder that %-growth off a small/negative base is noisy in magnitude. Percentile (rank-only) scoring is used specifically to avoid this distorting other names' scores.

## Catalyst/EarningsMomentum theme score (0-100, higher = stronger earnings momentum + beat consistency)
| nse_symbol   |   theme_catalyst_earnings_momentum |   np_yoy |   np_growth_accel |   np_surprise_pct |   np_consistency_beats |
|:-------------|-----------------------------------:|---------:|------------------:|------------------:|-----------------------:|
| SHAKTIPUMP   |                               90   |    208.4 |             297   |             398.7 |                      3 |
| MARUTI       |                               79.1 |     78.2 |             -65.5 |              34.2 |                      3 |
| HDFCBANK     |                               76.4 |     55.1 |              26.1 |              31.8 |                      2 |
| GRAVITA      |                               62.1 |     31.1 |              13.3 |              -5.6 |                      2 |
| NESTLEIND    |                               60.6 |     37.4 |               0.5 |              23.4 |                      2 |
| INFY         |                               43.6 |      3.1 |              -7.7 |               3.6 |                      2 |
| HINDALCO     |                               43   |     -0.4 |              40   |             -14.1 |                      2 |
| ASIANPAINT   |                               40.5 |     53.2 |               1.2 |             -31.6 |                      3 |
| TCS          |                               38.5 |      8.7 |              -8.1 |              -1.9 |                      2 |
| TATASTEEL    |                               18.4 |   -602   |            -508.8 |           -1087.3 |                      2 |

## Upcoming results / event proximity (1M catalyst gate)
Pilot names with an upcoming result WITHIN the 1M (~30d) window flagged in `forthcoming_results.csv`:
| nse_symbol   | next_result_date   |   days_to_next_result |
|:-------------|:-------------------|----------------------:|
| HDFCBANK     | 2026-07-18         |                     2 |
| NESTLEIND    | 2026-07-22         |                     6 |
| INFY         | 2026-07-23         |                     7 |
| HINDALCO     | 2026-08-07         |                    22 |

Pilot names with NO upcoming date in `forthcoming_results.csv` (feed only covers ~2026-07-09 to 2026-08-07):
ASIANPAINT, GRAVITA, MARUTI, SHAKTIPUMP, TATASTEEL, TCS

Full per-symbol calendar (`pilot_upcoming_results.csv`):
| nse_symbol   | last_result_date   |   days_since_last_result | next_result_date   |   days_to_next_result |   upcoming_1m_event |   post_earnings_drift_window |
|:-------------|:-------------------|-------------------------:|:-------------------|----------------------:|--------------------:|-----------------------------:|
| HDFCBANK     | 2026-04-18         |                       89 | 2026-07-18         |                     2 |                   1 |                            0 |
| NESTLEIND    | 2026-04-21         |                       86 | 2026-07-22         |                     6 |                   1 |                            0 |
| INFY         | 2026-04-23         |                       84 | 2026-07-23         |                     7 |                   1 |                            0 |
| HINDALCO     | 2026-05-22         |                       55 | 2026-08-07         |                    22 |                   1 |                            0 |
| ASIANPAINT   | 2026-05-29         |                       48 |                    |                   nan |                   0 |                            0 |
| GRAVITA      | 2026-05-07         |                       70 |                    |                   nan |                   0 |                            0 |
| MARUTI       | 2026-04-28         |                       79 |                    |                   nan |                   0 |                            0 |
| SHAKTIPUMP   | 2026-05-07         |                       70 |                    |                   nan |                   0 |                            0 |
| TATASTEEL    | 2026-05-15         |                       62 |                    |                   nan |                   0 |                            0 |
| TCS          | 2026-04-09         |                       98 |                    |                   nan |                   0 |                            0 |

## Outputs
- `ALPHA_RANKER/results/pilot_catalyst_factors.csv` -- raw factors + percentiles + theme score
- `ALPHA_RANKER/results/pilot_upcoming_results.csv` -- event-calendar distances

## Landmines enforced
- D-028/T-series lookahead: all growth/surprise factors gated on `available_date` <= REF_DATE, never `quarter_end`.
- Landmine 3: PIT dataset with `available_date`, not quarter-end, used throughout.
- No fabrication: data-vintage gap (PIT caps 2023-Q3) stated explicitly above, not smoothed over.