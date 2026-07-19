# FND_panel_long — LONG-HISTORY Companion Panel Build Report

[DATA] Result: `ALPHA_RANKER/rnd/panel/panel_long.parquet` built successfully.

## Data lineage
- Prices: `Nifty500_Master_Dataset_2005_2025.xlsx` (repo root), Sheet1, raw shape includes ~1199 ticker columns, 2005-01-03 -> 2025-12-05
- Post-dedup unique tickers: 976
- Market/calendar: `factor_navs (1).xlsx` "NIFTY 500" NAV series (via `src/lib/factor_bench.py`)
- Universe/sector: `ALPHA_RANKER/data/universe/nifty_total_market_750.csv` (751 rows, CURRENT constituents only)
- Market cap: `ALPHA_RANKER/data/fundamentals/screener_live/<SYM>.json` (CURRENT snapshot, same proxy as short panel)
- Regime: `ALPHA_RANKER/results/regime_timeline.parquet` (max date 2026-02-27)
- FF6 factors: `factor_navs (1).xlsx` via `build_panel.build_ff_factors` (max complete-row date 2025-12-05)

## De-duplication
- 109 base tickers had >1 raw column (pandas `.1`/`.2`/`.3` auto-suffix on load); 223 extra fragment columns dropped, longest-coverage fragment kept per ticker.
- Full log: `panel_long_dedup_log.csv` (332 rows: every raw column, kept/dropped flag, non-null count, min/max date).
- CAVEAT: even the kept (best) fragment for these 109 tickers covers only ~61-81 trading days each (median 80) -- a single quarter, not real multi-year history. Dedup fixed the column-duplication defect; it did not manufacture missing history.

## Discontinuity guard (split/bonus/data-error, |1d ret|>40%)
- 271 events flagged across 103 symbols. Full log: `panel_long_discontinuity_log.csv`.
- Flagged days excluded from vol/beta/FF-regression FEATURE inputs only (see PANEL_SCHEMA.md addendum); price levels and forward returns are untouched.
- Added columns `disc_event_in_window_{1M,1Y,5Y}` let downstream research filter contaminated forward-return rows explicitly rather than have them silently scrubbed.

## Row counts / coverage
- n_obs = 148297
- date range = 2005-04-29 -> 2025-12-05
- n_symbols = 969 / n_rebalance_dates = 249
- sector hit-rate (current-750 join): 604/976 tickers matched
- mktcap hit-rate (screener_live current snapshot): 805/976 tickers matched

## Per-column non-null %

| column | non-null % |
|---|---|
| date | 100.0% |
| symbol | 100.0% |
| sector | 69.9% |
| mktcap_log | 95.8% |
| regime_trend | 97.8% |
| regime_vol | 96.8% |
| regime_leader | 98.8% |
| beta_252 | 96.5% |
| vol_21 | 99.7% |
| vol_63 | 98.5% |
| vol_126 | 97.1% |
| vol_252 | 94.4% |
| idio_vol_252 | 96.5% |
| ff_beta_MKT | 96.5% |
| ff_beta_SMB | 96.5% |
| ff_beta_HML | 96.5% |
| ff_beta_RMW | 96.5% |
| ff_beta_CMA | 96.5% |
| ff_beta_WML | 96.5% |
| fwd_ret_1M_raw | 98.8% |
| fwd_ret_1M_excess | 98.8% |
| fwd_ret_1M_resid | 95.4% |
| fwd_ret_1Y_raw | 92.4% |
| fwd_ret_1Y_excess | 92.4% |
| fwd_ret_1Y_resid | 89.3% |
| fwd_ret_5Y_raw | 67.3% |
| fwd_ret_5Y_excess | 67.3% |
| fwd_ret_5Y_resid | 64.8% |
| disc_event_in_window_1M | 98.9% |
| disc_event_in_window_1Y | 92.8% |
| disc_event_in_window_5Y | 67.9% |

## Headline check (the reason this panel exists)
- fwd_ret_1Y_raw non-null: 92.4%
- fwd_ret_5Y_raw non-null: 67.3% (CONFIRMED > 0%, fixes the short panel 0% gap)

## Known caveats (full detail in PANEL_SCHEMA.md addendum)
- 109 dedup-fixed tickers still only have ~1-quarter of real coverage each (see above) -- do not expect real time-series for these names specifically.
- ~61 further non-fragmented tickers also have <300 non-null observations total (same source-sparsity pattern without the duplicate-column symptom).
- sector/mktcap_log are CURRENT-snapshot joins -- NaN for any delisted/renamed/merged ticker not in the current-750 universe or screener_live.
- Master calendar/market series both use factor_navs "NIFTY 500" (this file has no Nifty column of its own); calendar effectively starts 2005-04-01, not 2005-01-03.
- Discontinuity flags are a GUARD on rolling feature stats, not a data-cleaning pass on forward returns -- see `disc_event_in_window_*` before trusting any single name's 1Y/5Y number.

## Verdict
**REAL, with named caveats** — no lookahead detected in the construction (forward returns strictly t->t+h off the market's own calendar, beta known-at-t only, listing-life gated, dedup and discontinuity events fully logged rather than silently fixed). Weakest assumption: the 109 dedup-fixed tickers and ~61 further sparse tickers contribute far less real history than their presence in the row count suggests -- any 1Y/5Y claim concentrated in a small number of names should be cross-checked against the dedup log and `disc_event_in_window_*` before being trusted. mktcap_log/sector remain current-snapshot [INFERENCE], unchanged from the short panel's caveat.