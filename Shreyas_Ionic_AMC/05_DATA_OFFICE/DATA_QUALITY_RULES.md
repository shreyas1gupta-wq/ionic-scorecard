# DATA QUALITY RULES — landmines + new-source protocol (Data Officer owns)

## The landmines (violating any = fake backtest; guards in 04_RND_LAB/lib/guards.py)
1. **HF timezone:** daily bars stamped 18:30 UTC = NEXT-day 00:00 IST. Always `dt.tz_convert('Asia/Kolkata').dt.date`.
2. **Pre-open auction:** 1-min "open" at 09:00 is the auction print; real open = first bar ≥ 09:15. (~94% of naive 2026 gap calcs corrupted before fix.)
3. **PIT/earnings lookahead:** act only on `available_date` (earnings_pit; 86.2% exact). NEVER quarter-end dates.
4. **Option-data gap — STATUS UPDATE 2026-07-03: FILLED.** Apr-2024→Aug-2025 + Jun-2026 single-stock options backfilled from NSE UDiFF/legacy bhavcopy (1,408 sym-expiry daily parquets). Residual truths: (a) backfilled files are DAILY (EOD OHLC+settle+vol+OI), not 1-min; (b) untraded strikes carry 0.00 O/H/L (settlement still populated) — filter volume>0 for prints; (c) guard L6 now asserts SCHEMA AWARENESS not trade absence.
5. `india_fundamentals_mc/Train.parquet` `annual_report` column corrupt at source — never read it.
6. **Survivorship:** universe membership ONLY from `NIFTY500_TICKER_2005_2025_Final.xlsx` (42 PIT snapshots).

## Dual-schema warning (stocks_options/)
| Source | Granularity | Timestamp | Extra cols | Tell |
|---|---|---|---|---|
| HF 1-min (2021→Mar-24, Sep-25→May-26) | 1-minute | tz-aware IST | open_interest, symbol, expiry | 100k+ rows/file |
| Bhavcopy backfill (Apr-24→Aug-25, Jun-26, +122 new stocks 2yr) | DAILY | naive 15:30 stamp | settle, oi | ~few-k rows/file |
Consumers must branch on schema or use EOD-only accessors. `angel_capture_2026/` (day/ + minute/) = live forward capture, Jul-2026 onward.

## New-source protocol (D-009 — NO auto-fetch, ever)
1. Propose: source, URL/API, licence, cost, what edge it feeds. 2. Principal approves the FETCH of a sample.
3. Sample 100 rows → schema/dtypes/nulls/dupes/date-monotonicity/PIT-safety; cross-check 5 values vs an independent source.
4. Verdict USE/QUARANTINE + draft DATA_CATALOG entry → Principal approves go-live. 5. Only then: bulk ingestion, with update command documented in the catalog.

## Freshness rules
- Count PERIODS-PER-YEAR (expiries, months, quarters), not just max(date) — the 17-month gap hid behind healthy max-dates.
- Critical sets get a daily ping via 99_OPS/EOD_ROUTINE.md; stale > 2 sessions = flag in CURRENT_STATE.
