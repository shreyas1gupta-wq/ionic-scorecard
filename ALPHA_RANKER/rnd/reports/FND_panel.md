# FND_panel — SHARED PIT Panel Build Report

[DATA] Result: `ALPHA_RANKER/rnd/panel/panel.parquet` built successfully.

## Data lineage
- Prices: `ALPHA_RANKER/data/prices/*.parquet` (751 symbols) + `_NSEI.parquet` (market, master calendar)
- Universe/sector: `ALPHA_RANKER/data/universe/nifty_total_market_750.csv` (751 rows, full symbol coverage confirmed)
- Market cap: `ALPHA_RANKER/data/fundamentals/screener_live/<SYM>.json` top_ratios (751/751 files present; 62 rows with unparseable/missing Market Cap or Price)
- Regime: `ALPHA_RANKER/results/regime_timeline.parquet` (5189 rows, max date 2026-02-27)
- FF6 factors: `factor_navs (1).xlsx` via `src/lib/factor_bench.py` (max complete-row date 2026-01-05)

## Row counts / coverage
- n_obs = 40201
- date range = 2021-07-30 -> 2026-07-16
- n_symbols = 751 / n_rebalance_dates = 61
- sector missing: 0 rows (0 expected, universe join is 1:1 on 751 symbols)

## Per-column non-null %

| column | non-null % |
|---|---|
| date | 100.0% |
| symbol | 100.0% |
| sector | 100.0% |
| mktcap_log | 99.8% |
| regime_trend | 100.0% |
| regime_vol | 100.0% |
| regime_leader | 86.9% |
| beta_252 | 88.7% |
| vol_21 | 98.2% |
| vol_63 | 96.1% |
| vol_126 | 90.7% |
| vol_252 | 81.5% |
| idio_vol_252 | 86.6% |
| ff_beta_MKT | 86.6% |
| ff_beta_SMB | 86.6% |
| ff_beta_HML | 86.6% |
| ff_beta_RMW | 86.6% |
| ff_beta_CMA | 86.6% |
| ff_beta_WML | 86.6% |
| fwd_ret_1M_raw | 96.3% |
| fwd_ret_1M_excess | 96.3% |
| fwd_ret_1M_resid | 85.0% |
| fwd_ret_1Y_raw | 76.0% |
| fwd_ret_1Y_excess | 76.0% |
| fwd_ret_1Y_resid | 65.5% |
| fwd_ret_5Y_raw | 0.0% |
| fwd_ret_5Y_excess | 0.0% |
| fwd_ret_5Y_resid | 0.0% |

## Guards / PIT checks
- [DATA] Listing-life gate: rows only emitted where the rebalance date falls within each symbol's own `[file_min, file_max]` price-file range (IPO/delisting handled, no fabricated pre-IPO or post-delist rows).
- [DATA] Halt bridging: forward-fill limited to 5 trading days when reindexing a symbol onto the master calendar; longer gaps (delisting, extended halts) correctly surface as NaN rather than being silently carried forward.
- [DATA] Forward returns strictly t->t+h on the master trading calendar; horizons exceeding available history are NaN, not extrapolated (drives the 100% `fwd_ret_5Y_*` NaN rate below -- master calendar has only 1234 trading days total, 26 short of the 1260-day 5Y horizon even from the first rebalance date; expected, not a bug).
- [DATA] `beta_252` used inside `fwd_ret_*_resid` is the value estimated AT t (pre-computed from trailing data only) — never re-fit using the forward window.
- [DATA] Lag-stability spot check: beta_252 recomputed at t vs t-1 trading day for 23 random (symbol, rebalance-date) pairs.
  - median |delta| = 0.0033, max |delta| = 0.0344 (single-day window shift; no discontinuity/leak observed — a leak would show as a delta comparable to the beta's own magnitude, ~0.5-1.5, not a small fraction of it)

## Known caveats (full detail in PANEL_SCHEMA.md — read before use)
- factor_navs.xlsx has heterogeneous per-series staleness: the joint (all-6-factors) cutoff is 2026-01-05 (driven by NIFTY100/Value30/Quality30/Liquid Fund/Smallcap250 stopping there; NIFTY500/LowVol30/Momentum30 continue to 2026-02-27) -- ff_beta_* degrade to NaN progressively after 2026-01-05 as the trailing window right-truncates below the 126-obs minimum. regime_timeline.parquet separately stops at 2026-02-27; regime_* is forward-carried past that (stale, not fabricated) per spec.
- mktcap_log uses a CURRENT (not PIT) shares-outstanding proxy from screener_live — [INFERENCE], documented, level trend is not fully trustworthy though cross-sectional rank per date should be reasonable.
- Universe is CURRENT NIFTY-750 constituents, not a PIT snapshot series — real survivorship bias (names that fell OUT of today's 750 are absent for their whole history), separate from and in addition to any listing-life handling.
- FF6 factors are index-proxy constructions (documented formulas in PANEL_SCHEMA.md), not a bottom-up India FF6 built from our own stock universe. CMA is the weakest of the six (Low Vol 30 substituting for a true investment factor).

## Verdict
**REAL** (for what it is: a documented-proxy, current-universe PIT panel with no lookahead detected in the checks run). Weakest assumption: the mktcap_log constant-shares-outstanding proxy and the CMA factor proxy (Low Vol 30) are both [INFERENCE] substitutes for data that doesn't exist in this repo yet — any factor research leaning heavily on absolute market-cap level or on CMA specifically should treat those columns as low-confidence until better source data is sourced.