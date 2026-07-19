# SCRAPING SOP — Screener fundamentals for STOCK_SCORECARD_750 (FROZEN v1, 2026-07-18)
**Frozen by Principal order 2026-07-18 ("FIRST FREEZE OUR REPEATABLE SCRAPING FROM SCREENER PROCESS"). Companion to FROZEN_METHODOLOGY.md — that file owns scoring; this file owns the data feed. Changes only via dated amendment with Principal sign-off.**

## 1. What we pull, from where
Source: screener.in company pages (consolidated view preferred; standalone fallback where consolidated absent). Per stock:
- **Annual P&L** (Sales, Expenses, Operating Profit, OPM, Other Income, Interest, Depreciation, PBT, Tax, Net Profit, EPS, Dividend Payout — raw line items, NOT pre-computed ratios)
- **Balance Sheet** (Equity Capital, Reserves, Borrowings, Other Liabilities, Fixed Assets, CWIP, Investments, Other Assets)
- **Cash Flow** (CFO, CFI, CFF, Net Cash Flow)
- **Quarterly results** (Sales, Expenses, OP, OPM, PBT, Net Profit, EPS — last ~13 quarters)
- **Shareholding pattern** (Promoter/FII/DII/Public, quarterly; promoter PLEDGE % when Screener exposes it — closes the known gate gap)
All ratios (ROE, ROCE, PE, PB, FCF yield, D/E, interest coverage) are DERIVED downstream by `derived_ratios.py` logic from raw line items — never scraped pre-computed (frozen decision 2026-07-17: Screener's own ratio tiles are not stable/complete across companies).

## 2. Storage contract (matches the existing verified layout)
`datasets/screener_deep/` — long format, one row per (symbol, metric), period columns as scraped ("Mar 2018"…"Mar 2026", "TTM", odd fiscal-year-ends kept as-is):
- `screener_annual_pl.parquet`, `screener_balance_sheet.parquet`, `screener_cash_flow.parquet` (existing, verified 2026-07-04: PL 6,000 / BS 5,022 / CF 3,000 rows, 500 symbols)
- NEW at 750-rollout: `screener_quarterly_results.parquet`, `screener_shareholding.parquet` (same long format)
- `_done.json` = list of completed symbols — THE resume marker. A run must be re-runnable at any point: skip symbols in `_done.json`, append only after a symbol's full set is written.
- Every refresh stamps `_meta.json`: {run_date, universe_file, symbols_attempted, symbols_ok, symbols_failed[], scraper_version}.

## 3. Universe
`ALPHA_RANKER/data/universe/symbols_750.txt` is the universe list; sector tags from `ALPHA_RANKER/data/universe/sector_map.parquet` (macro_sector col — note known case-duplicate categories; normalize case on join). Universe file re-checked each refresh against the latest NSE Nifty-750 constituency before scraping.

## 4. Refresh cadence — "basis results" (Principal's rule)
- **Quarterly full refresh ×4/yr**, AFTER each results season completes: ~25 Feb (Q3), ~10 Jun (Q4/FY), ~25 Aug (Q1), ~25 Nov (Q2). Screener pages update as companies file; scraping mid-season gives a half-updated book — never score off a mid-season scrape without noting it.
- **Delta trigger between refreshes:** if `datasets/nse_earnings_dates/` shows a portfolio/coverage name has reported since the last scrape, that symbol may be re-scraped individually (remove from `_done.json`, rerun) before any client deliverable that includes it.
- **Regime check** (Cyrus) is monthly-ish and independent of this cadence.
- **Refresh ledger (keep current — "timing fix", Principal order 2026-07-19):**
  | Last full refresh | Coverage | Next due | Notes |
  |---|---|---|---|
  | 2026-07-03 | 500 names (_done.json) | **~2026-08-25 (post-Q1 FY27)** | Jul-03 scrape is post-Q4FY26 = current until Q1 prints land (season runs mid-Jul→Aug 2026). |
  - Delta-trigger scope EXPANDED 2026-07-19: "coverage names" now = client holdings + the FULL Nifty 100 (Principal's coverage-build order). Any coverage name that reports before 25 Aug gets an individual re-scrape before its data feeds a deliverable. Near-term: holdings knife-edge prints 21–31 Jul (BANDHANBNK 21st, IDFCFIRSTB 25th, SUMICHEM 27th, BAJAJHFL 29-30th, MARUTI 31st + ITC/VBL/TMPV).
  - Current-membership source of truth: `datasets/index_constituents/ind_nifty100list_<yyyymmdd>.csv` (official NSE archives CSV, refetch at each refresh — takes seconds). The local composition xlsx ends Oct-2025: NEVER use it for current membership, PIT history only.

## 5. Politeness / infra (hard-won environment facts)
- `truststore.inject_into_ssl()` before HTTPS; corporate proxy ~0.7MB/s; SEQUENTIAL `requests.Session()` only (threads stall on the proxy); ≥2s sleep between symbols; exponential backoff on 429/5xx; user-agent set honestly; abort the run (don't hammer) on 3 consecutive 403s — Screener rate-limits aggressively on anonymous traffic. Big pulls run as resume-safe background jobs (D-033).
- Full 750-universe pull at ~2.5s/symbol ≈ 35-40 min/table set — schedule off-hours.

## 6. Verification gate (D-009 — every refresh, before ANY scoring use)
1. Spot-check 3 known symbols' Net Profit + Borrowings vs screener.in by eye (values match, units = Rs cr).
2. Row-count sanity vs prior refresh (±15% per table, else investigate before overwrite — never silently clobber the prior parquet; write to `screener_deep/_staging/`, verify, then promote).
3. Schema check: long-format cols present, no new unnamed columns silently absorbed.
4. **PIT WARNING (standing, Sanjay 2026-07-04): screener_deep has NO available_date column — fiscal-period labels only. Fine for CURRENT-state scoring (scorecard use). LOOKAHEAD-ILLEGAL for any backtest without stamping via `unified_quarterly_pit` or a +6mo lag. This SOP freezes scorecard use only.**
5. DATA_CATALOG.md row updated with refresh date + counts (Kavya owns).

## 7. Canonical scraper script
`Shreyas_Ionic_AMC/05_DATA_OFFICE/scripts/scrape_screener_750.py` — [STATUS 2026-07-18: the original one-off scraper that produced screener_deep was not located in the repo at freeze time; Manoj (ops) to rehome or rebuild it TO THIS CONTRACT (sections 1-2, 5) before the first 750 refresh. The data contract above is frozen regardless of implementation.]
Usage: `python scrape_screener_750.py [--universe symbols_750.txt] [--tables pl,bs,cf,qtr,shp] [--symbols CSV-list for delta reruns]`.

## 8. Ownership
Kavya Reddy (Data Officer) owns the feed + catalog + D-009 gate; Manoj Pillai (Ops) owns the script + scheduling; escalation of source-format breaks (Screener HTML changes) goes to both, then Principal if the feed is down through a results season.
