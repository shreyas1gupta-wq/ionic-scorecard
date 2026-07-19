# ALPHA_RANKER — Data Pipeline Runbook (reusable / quarterly)

All data is cached on disk and every step is **resume-safe** (skips what already exists). To refresh a
stock, delete its file and re-run. Python = `C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe`
(always `PYTHONIOENCODING=utf-8`). Run scripts from `ALPHA_RANKER/src/lib/`.

## 0. Universe (run each quarter — NSE rebalances it)
`python -c "..."` fetch → `data/universe/nifty_total_market_750.csv` + `symbols_750.txt`.
Source URL (Principal-provided, always current): `https://nsearchives.nseindia.com/content/indices/ind_niftytotalmarket_list.csv`
Columns: Company Name, Industry (→ sector for cascade), Symbol, Series, ISIN.

## 1. Prices (yfinance, 5y daily) — process-parallel, ~5 min for 750
Run 3 processes: `yf_batch.py --slice 0/3`, `--slice 1/3`, `--slice 2/3`, plus `yf_batch.py --benchmark`.
→ `data/prices/<TICKER>.parquet` (+ `_NSEI.parquet`). Skips existing. **Quarterly: delete all + re-pull** for a fresh window, or keep & only new listings pull.

## 2. Fundamentals (screener.in PUBLIC pages) — process-parallel, ~4-5 min for 750
Run 5 processes: `screener_scrape.py --slice 0/5` ... `--slice 4/5`.
→ `data/fundamentals/screener_live/<TICKER>.json` (quarterly/P&L/BS/CF/ratios/shareholding + top-ratios + concall-doc links).
1.6s/req/process politeness (avoids IP-ban); backoff on 429/5xx; logs in `data/fundamentals/_scrape_logs/`.
**Quarterly refresh: delete `screener_live/*.json` then re-run** (or delete only names with new results).
NOTE: public pages carry ~12 quarters + 10y annual + shareholding — enough for all factors. Premium (deeper history/exports) would need a session cookie; not required.

## 3. Consolidate → reusable tidy parquets
`consolidate_screener.py` → `data/fundamentals/consolidated/{quarterly_results,profit_loss,balance_sheet,cash_flow,ratios,shareholding,top_ratios,documents}.parquet` + `coverage_manifest.csv`. Long format (symbol, metric, period, value). Idempotent — re-run anytime.

## 3b. Master fundamentals file (single source, ALL companies, PIT-safe)
`build_master_fundamentals.py` → `data/fundamentals/MASTER_fundamentals_pit.parquet` (+ `MASTER_coverage.csv`).
Merges PIT backbone (`datasets/earnings_pit/yearly_profit_loss_pit` + `yearly_balance_sheet_pit`, 4,491 co, FY04→FY23, `available_date`) with the fresh screener overlay (FY24→26); fresh wins on overlap. LONG: (key_symbol, nse_symbol, company, fiscal_year, statement, metric, value, available_date, source, is_fresh).
**Quarterly:** re-scrape (step 2, over `symbols_all_4491.txt` for all mappable names) → consolidate (step 3) → re-run this. Idempotent.
CAVEAT [verified]: the two PIT yearly files are stale to 2023-11-30 (NOT current/TTM); only the screener overlay is fresh. PIT `nse_symbol` present on just 2,234/4,491 — unmapped names key as `NAME::<company>`, PIT-only.

## 4. Factors → scores (universe-wide)
Factor modules read prices + consolidated parquets, emit cross-sectional percentiles over the FULL universe:
technical/flow (`factors/`), fundamental, catalyst (`fresh_catalyst`-style), forensic, cascade (sector from Industry col), regime (`regime/`, from `factor_navs`). Then `scoring/combine_scores.py` fuses → `results/pilot_final_scores.csv` (rename per universe run).

## Data freshness (as of this build)
| Source | Freshness | Refresh cadence |
|---|---|---|
| Prices (yfinance) | live to today | daily/quarterly |
| Screener fundamentals+shareholding | to Mar/Jun 2026 | **quarterly** (post-results) |
| Factor NAVs (`factor_navs (1).xlsx`) | to 2026-02 | monthly (Principal drop) |
| NSE delivery (`datasets/`) | stale to 2024-06 | needs D-033 forward-fetch |

## Landmines carried
- Ticker remap on corporate actions (TATAMOTORS.NS 404'd — demerger). Maintain a remap table.
- Bank layouts differ (no Sales/OPM/promoter rows) — factor code must branch on schema.
- Cross-source symbol match: NSE symbol == yfinance `<SYM>.NS` == screener `/company/<SYM>/` (holds for the pilot; verify at scale).
