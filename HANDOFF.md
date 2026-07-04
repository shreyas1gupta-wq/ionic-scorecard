# COMPLETE HANDOFF DOCUMENT — Quant Trading System
**Last updated: 2026-07-04** | Root: `C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500`

Read this file first. It tells you everything about what was built, where every file lives, what format it's in, what's verified, and what's left to do.

---

## 1. ENVIRONMENT & TOOLCHAIN

| Item | Value |
|---|---|
| **Python** | `C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe` |
| **`python` alias** | BROKEN — always use the full path above |
| **Console encoding** | cp1252 — set `PYTHONIOENCODING=utf-8` and `PYTHONUNBUFFERED=1` for all scripts |
| **Corporate proxy** | Present. Threaded HF downloads STALL. Use sequential `requests.Session()` reuse (see `hf_stock_options_v3.py` for pattern) |
| **SSL** | Must call `truststore.inject_into_ssl()` before any external HTTPS request |
| **HuggingFace token** | `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` |
| **OneDrive quirk** | Filenames with `=` chars cannot be deleted via PowerShell — use Bash `rm -rf` instead |
| **Parquet library** | `pyarrow` (installed in system Python) |
| **Angel One API** | API_KEY=8crMtPbu, CLIENT=S59047501 — fund-less/disposable test account, no real money |

### Key pip packages available
pyarrow, pandas, numpy, requests, huggingface_hub, truststore, SmartApi (Angel One SDK)

---

## 2. PROJECT STRUCTURE (top-level)

```
NIFTY 500/
├── RESUME_TOMORROW.md          ← Master index, read first each session
├── HANDOFF.md                  ← THIS FILE — complete reference for new sessions
├── other2/OPERATING_STANDARD_2026.md  ← Elite operating layer spec (8 systems) [moved off root 2026-07-05 reorg]
├── other2/PORTFOLIO_OF_EDGES.md       ← Cross-market/cross-asset strategy layer [moved off root 2026-07-05 reorg]
│
├── intraday_options_strategy/  ← TRACK 1: Intraday Nifty options (MATURE)
│   ├── PLAN.md
│   ├── config.py               ← Strategy config (LOT_SIZE needs fix: 75→65)
│   ├── main.py                 ← Core strategy engine
│   ├── run_today_live.py       ← Live trading runner
│   ├── run_realfill_deltahedged.py ← Real-fill backtest script
│   ├── data/                   ← Data download scripts (see §4)
│   ├── datasets/raw/           ← Raw HF/Kaggle data (options, bhavcopy)
│   ├── results/                ← Backtest results, reports, charts
│   ├── strategies/             ← Strategy implementations
│   ├── backtest/               ← Backtest engine
│   ├── features/               ← Feature engineering
│   ├── analysis/               ← Analysis notebooks/scripts
│   ├── optimisation/           ← WFO, parameter optimization
│   ├── options/                ← Options pricing (synthetic BS)
│   └── portfolio/              ← Portfolio/position management
│
├── swing_momentum/             ← TRACK 2: Small-cap momentum swing (IN PROGRESS)
│   ├── PLAN.md                 ← Phase-by-phase build plan
│   ├── GOD_TIER_EXPANSION.md   ← 10 dimensions (D1-D10)
│   ├── FRONTIER_DIMENSIONS_2026_2040.md ← D11-D14 (adversarially filtered)
│   ├── FORWARD_WATCHLIST.md    ← Thematic watchlist
│   ├── MULTIBAGGER_DNA.md      ← Multibagger characteristics study
│   ├── MULTIBAGGER_STUDY.md    ← Historical multibagger analysis
│   ├── RESULTS.md              ← Backtest results
│   ├── run_swing.py            ← Main swing strategy runner
│   ├── run_multistrat.py       ← Multi-strategy combiner
│   ├── data/                   ← Data scripts + stock minute/daily data
│   ├── backtest/               ← Backtest engine
│   ├── signals/                ← Signal generation
│   └── processed/              ← Processed data outputs
│
├── alpha_research/             ← TRACK 3: New-dimension alpha research
│   ├── PLAN.md                 ← 7 hypotheses (H1-H7), ranked
│   └── experiments/            ← Research notebooks
│
├── datasets/                   ← Shared datasets (news, fundamentals, earnings)
│   ├── nifty500_symbol_mapping.json  ← CRITICAL: rename/merger/demerger/encoding mapping
│   ├── nifty500_current_2026.json    ← Current Nifty 500 constituents (500 stocks)
│   ├── angel_daily_missing/    ← Angel API daily OHLCV for 20 stocks missing from HF
│   ├── kaggle_indian_financials/ ← 8 parquets: QPL, YPL, BS, CF, Ratios, Shareholding (4,492 companies)
│   ├── india_stock_metadata/   ← Indian stock symbols & company metadata
│   ├── nifty_stock_daily/      ← Nifty stock metadata (505 stocks, index membership)
│   ├── yahoo_finance/          ← US stock data from defeatbeta/yahoo-finance-data
│   ├── india_fin_news/         ← Indian financial news (ticker-specific + sentiment)
│   ├── india_earnings_calls/   ← MiMIC earnings call transcripts
│   ├── india_fundamentals_mc/  ← MoneyControl fundamentals (Train/Test parquet)
│   ├── nse_earnings_dates/     ← NSE board meetings + corporate actions
│   ├── bbc_news_alltime/       ← BBC news archive
│   ├── reddit_sp500/           ← Reddit SP500 discussions
│   ├── us_fin_news/            ← US financial news
│   ├── toi_headlines/          ← Times of India headlines
│   ├── moneycontrol_news/      ← MoneyControl news
│   ├── huffpost_news/          ← HuffPost news
│   ├── million_headlines/      ← ABC Million Headlines
│   ├── gdelt_events/           ← GDELT global events
│   └── nifty50_weights/        ← Nifty 50 index weights
│
├── raw/                        ← Older raw data (NSE XBRL, books, corporate actions)
│   ├── books/                  ← 62 files, 1.0 GB
│   ├── corporate_actions/      ← 359 files
│   ├── financial_metadata/     ← 244 files
│   ├── nifty500/               ← 239 files
│   └── xbrl_cache/             ← 581 files
│
├── Strategy_Results/           ← Older strategy output
├── working/                    ← Working/scratch area
├── working101/                 ← Working/scratch area
└── logs/                       ← Log files
```

---

## 3. COMPLETE DATA INVENTORY (verified 2026-07-02, ALL parquets corruption-checked)

### 3A. Stock Price Data

#### Stock Minute Data — `swing_momentum/data/hf_stock_minute/`
- **Source:** HuggingFace `Saintforest/indian-stock-market-minute-data`
- **Format:** Parquet (pyarrow)
- **Minute shards** (8 files in `minute/`):
  | File | Size | Rows |
  |---|---|---|
  | train-00000.parquet | 1,446 MB | 100M |
  | train-00001.parquet | 1,469 MB | 100M |
  | train-00002.parquet | 1,433 MB | 100M |
  | train-00003.parquet | 1,406 MB | 100M |
  | train-00004.parquet | 1,574 MB | 100M |
  | train-00005.parquet | 1,428 MB | 100M |
  | train-00006.parquet | 1,444 MB | 100M |
  | train-00007.parquet | 193 MB | 13.5M |
  | **Total** | **10.4 GB** | **813.5M rows** |
- **Daily shard** (1 file in `day/`): train-00000.parquet — 118 MB, 6.97M rows
- **Status:** All verified OK. Shards 00002-00005 were truncated (missing 12-82 KB each from parquet footer), FIXED via HTTP Range request tail appends.
- **Columns:** Standard OHLCV + symbol, date, time

#### Stock Daily Data — same location as above
- `day/train-00000.parquet` — 118 MB, 6.97M rows
- All Indian stocks, daily OHLCV

### 3B. Options Data

#### Index Options 1-minute — `intraday_options_strategy/datasets/raw/hf_index_options_1m/`
- **Source:** HuggingFace `thetrademarkk/india-index-options-1m`
- **Format:** Parquet files, one per date per instrument

| Subdirectory | Files | Size | Contents |
|---|---|---|---|
| `index/` | 3 | 24 MB | Index-level data (NIFTY, BANKNIFTY) |
| `options/` | 467 | 1,578 MB | Index options (NIFTY/BANKNIFTY CE/PE), 1-min bars |
| `stocks_options/` | 2,319 | 2,112 MB | Individual stock options, 1-min bars |
| `mcx/` | 7 | ~0 MB | MCX commodity options (mostly empty/small) |
| **Total** | **2,796** | **3,714 MB** | |

- **Status:** ALL verified OK (2,319 stock options completed 2026-07-01, zero failures)
- **Columns:** timestamp, open, high, low, close, volume, oi, strike, option_type, expiry, symbol

#### ATM Options — `intraday_options_strategy/datasets/raw/hf_atm_options/`
- **NIFTY/MONTH:** **42/42 files = 100% COMPLETE**
- **NIFTY/WEEK:** **42/42 files = 100% COMPLETE**
- **Source:** `artist-23/nifty-options-data` on HuggingFace (recovered all files that were 404 on `thetrademarkk` repo)
- **Status:** COMPLETE (fixed 2026-07-02)

#### Index Options Gap Analysis
| Index | Expiry Type | Files | Status |
|---|---|---|---|
| NIFTY | Weekly | 262 | OK — full coverage 2021-2026 |
| BANKNIFTY | **Monthly only** | 61 | **GAP** — no weekly expiry data. Kaggle `ayushsacri` may fill this |
| SENSEX | Weekly (Fri) | 144 | OK — 2023-08 to 2026-05 |

#### Kaggle Bhavcopy & Index Data — `intraday_options_strategy/datasets/raw/kaggle/`
- `debashis74017__nifty-50-minute-data/`: 680 files, 4.2 GB — **136 indices** × 5 timeframes (1m, 5m, 15m, 60m, daily), 2015→2026-05. Major indices include NIFTY 50, BANK NIFTY, INDIA VIX, all sector indices, factor indices, midcap/smallcap.
- `rohanrao__nifty50-stock-market-data/`: 52 files, 54 MB — Nifty 50 daily data (2000-2021)
- **Total:** 732 files, 4.3 GB
- **Status:** Verified OK

### 3C. News & Sentiment Data

#### India Financial News — `datasets/india_fin_news/`
| File | Size | Format | Description |
|---|---|---|---|
| `tier_segregated_news.csv` | 1,250 MB | CSV | **125,510 rows**, columns: `date, symbol, direct_news, sectoral_news, global_news`. Coverage: 2020-present, Nifty 50 stocks. Company-specific news by ticker. |
| `news_sentiment.csv` | 22 MB | CSV | Pre-computed sentiment scores. Columns: `Date, Symbol, direct_news_pos/neu/neg, sectoral_news_pos/neu/neg, global_news_pos/neu/neg, direct/sectoral/global_news_count` |
| `processed_news_dataset.csv` | 858 MB | CSV | Full processed news dataset |
| `nifty50_ticker.csv` | 12 MB | CSV | Nifty 50 ticker mapping |
| `tft_ready.csv` | 28 MB | CSV | TFT-model-ready features |
| + 4 other files | | | |

#### Yahoo Finance — `datasets/yahoo_finance/`
| File | Size | Format | Description |
|---|---|---|---|
| `stock_earning_call_transcripts.parquet` | 2,214 MB | Parquet | US earnings call transcripts (234,118 rows, 8 columns). Was truncated by 340 KB, FIXED via Range request tail append. |
| `stock_prices.parquet` | 454 MB | Parquet | US stock daily prices |
| `stock_news.parquet` | 902 MB | Parquet | US stock news |
| `stock_statement.parquet` | 112 MB | Parquet | Financial statements |
| `stock_sec_filing.parquet` | 89 MB | Parquet | SEC filings |
| `exchange_rate.parquet` | 3 MB | Parquet | Exchange rates |
| + 10 other files | | | Various US market data |
- **Source:** HuggingFace `defeatbeta/yahoo-finance-data`

#### Other News Sources
| Dataset | Location | Files | Size | Format |
|---|---|---|---|---|
| MoneyControl News | `datasets/moneycontrol_news/` | 1 | 45 MB | Parquet |
| Times of India Headlines | `datasets/toi_headlines/` | 1 | 238 MB | Parquet |
| BBC News (all-time) | `datasets/bbc_news_alltime/` | 79 | 206 MB | Parquet |
| Million Headlines (ABC) | `datasets/million_headlines/` | 1 | 64 MB | Parquet |
| HuffPost News | `datasets/huffpost_news/` | 1 | 87 MB | Parquet |
| US Financial News | `datasets/us_fin_news/` | 1 | 811 MB | Parquet |
| Reddit SP500 | `datasets/reddit_sp500/` | 1 | 2,463 MB | Parquet |
| GDELT Events | `datasets/gdelt_events/` | 1 | 1.4 MB | Parquet |

### 3D. Fundamentals & Earnings

#### India Fundamentals (MoneyControl) — `datasets/india_fundamentals_mc/`
| File | Size | Rows | Description |
|---|---|---|---|
| `Train.parquet` | 829 MB | 3,968 (991 companies) | Columns: `company_name`, `year`, `label` (full financial data: balance sheet, P&L, ratios), `annual_report` (**CORRUPT at HF source** — snappy compression error). |
| `Test.parquet` | 203 MB | ~1,000 | Same structure, test split |
| `Companies_List.csv` | 0.1 MB | | Company name mapping |

**KNOWN ISSUE:** `Train.parquet` `annual_report` column has snappy corruption AT SOURCE on HuggingFace. Re-download confirmed same issue — size matches exactly (829.2 MB). **Workaround:** Read only `company_name`, `year`, `label` columns — the `label` column actually contains the full financial data (balance sheet, P&L, cash flow, ratios).

```python
import pyarrow.parquet as pq
# Read only the usable columns:
table = pq.read_table("Train.parquet", columns=["company_name", "year", "label"])
```

#### India Earnings Calls (MiMIC) — `datasets/india_earnings_calls/`
- 7 files, 246 MB total
- `MiMIC_Multi-Modal_Indian_Earnings_Calls.xlsx`: 1,042 earnings calls with RESULT DATE, ticker, market prices, financials (57 columns)
- `extracted_texts.zip`: Full transcript texts (159 MB)
- `getting_all_texts_together.pkl`: Consolidated text data (75 MB)
- `final_train.csv`, `final_test.csv`, `final_valid.csv`: Pre-split datasets for ML

#### NSE Earnings Dates — `datasets/nse_earnings_dates/`
| File | Size | Description |
|---|---|---|
| `board_meetings_all.json` | 81 MB | 94,136 board meetings (2020-2026) |
| `earnings_dates.json` | 11 MB | 54,268 earnings dates, 2,532 unique symbols |
| `earnings_dates.csv` | 6 MB | Same data in CSV format |
| `corporate_actions_all.json` | 6 MB | 14,832 corporate actions (dividends, splits, AGMs) |
| `board_meetings_6m.json` | 11 MB | Recent 6-month board meetings |
| + 3 empty placeholder JSONs | | (corporate-announcements, corporate-board-meetings, corporates-corporateActions) |

**Script:** `intraday_options_strategy/data/nse_earnings_history.py` — Fetches from NSE API (requires session cookie from homepage first)

#### Kaggle Indian Financials (Screener-style) — `datasets/kaggle_indian_financials/`
- **Source:** Kaggle `sameerprogrammer/detailed-financial-data-of-4456-nse-and-bse-company`
- **Format:** 8 consolidated Parquet files (extracted from 35,551 individual CSVs, 4,492 companies)
- **Coverage:** 2005-2023, varies by company
| File | Rows | Companies | Description |
|---|---|---|---|
| `quarterly_profit_loss.parquet` | 49,375 | 4,475 | Sales, Expenses, Operating Profit, OPM%, Interest, Depreciation, Tax, Net Profit, EPS per quarter |
| `yearly_profit_loss.parquet` | 49,401 | 4,491 | Same line items, annual |
| `yearly_balance_sheet.parquet` | 45,565 | 4,491 | Total assets, liabilities, equity, borrowings, reserves |
| `yearly_cash_flow.parquet` | 17,964 | ~4,000 | Operating/investing/financing cash flows |
| `ratios.parquet` | 26,571 | ~4,000 | PE, PB, ROE, ROCE, Debt/Equity, Current Ratio, Dividend Payout |
| `quarterly_shareholding.parquet` | 17,930 | 4,299 | Promoter %, FII %, DII %, Public % by quarter |
| `yearly_shareholding.parquet` | 18,414 | 4,299 | Same, annual |
| `basic_info.parquet` | 4,492 | 4,492 | Sector, BSE/NSE codes, Market Cap, PE, Book Value, ROE/ROCE, EPS, Debt, growth rates |
| **Total** | | **4,492** | **8.2 MB** |

**Data format note:** Quarterly/Yearly P&L is in WIDE format — rows are line items (Sales, Expenses, etc.), columns are date periods (2020-09-01, 2020-12-01, etc.). Pivot for time-series analysis.

#### NSE Quarterly Results (Filing Metadata) — `datasets/nse_earnings_dates/quarterly_results_all.json`
- **Source:** NSE India API (`/api/corporates-financial-results`)
- **Size:** 69.5 MB, 76,503 filings from 2,357 unique symbols
- **Coverage:** 2019 to 2026 (2025: 3,960; 2024: 14,328; 2023: 13,147; etc.)
- **Fields:** `symbol`, `companyName`, `financialYear`, `broadCastDate`, `filingDate`, `period` (Quarterly), `audited`, `consolidated`, `xbrl` (link to XBRL filing), `params` (for detail API)
- **Note:** This is filing METADATA (dates, which quarter, audited/unaudited) — actual revenue/profit numbers are in the Kaggle financials above or in the XBRL links

#### India Stock Metadata — `datasets/india_stock_metadata/india.csv`
- **Source:** HuggingFace `kjhq/India-Stock-Symbols-and-Metadata`
- **Size:** 0.3 MB — stock symbols and company metadata for all Indian listed companies

#### Point-in-Time Earnings Dataset — `datasets/earnings_pit/`
- **Purpose:** Lookahead-bias-free financial data for backtesting
- **Built:** 2026-07-03 from Kaggle financials + NSE broadCastDate + XBRL + Screener.in
- **Total:** 9 parquets, 8.5 MB

| File | Rows | Companies | Description |
|---|---|---|---|
| **`unified_quarterly_pit.parquet`** | **31,891** | **2,296** | **PRIMARY DATASET.** Merges Kaggle (pre-2023) + Screener.in (2023-2026), deduped. **86.2% exact dates** (77% NSE broadCastDate + 9.3% board meeting dates). 2025: 95.3%, 2026: 98.0%. 100% Net Profit, 95% Sales, 100% PBT/Interest/Depreciation |
| `quarterly_earnings_pit.parquet` | 52,563 | 4,475 | Kaggle source QPL (includes non-NSE-listed companies). 41% exact dates |
| `screener_quarterly_2023_2026.parquet` | 6,270 | 500 | Screener.in: Nifty 500 × ~13 quarters (2023-2026). 61% exact dates (NSE+BM) |
| `mc_fundamentals_parsed.parquet` | 3,968 | 991 | Full BS+P&L parsed from MoneyControl label column, 146 structured columns |
| `yearly_profit_loss_pit.parquet` | 50,749 | 4,491 | Annual P&L 2004-2023, +90d conservative lag |
| `yearly_balance_sheet_pit.parquet` | 50,924 | 4,491 | Annual BS 2004-2023, +90d lag |
| `ratios_pit.parquet` | 46,000 | ~4,000 | ROE%, ROCE%, Debtor/Inventory/Payable Days, Working Capital Days |
| `quarterly_shareholding_pit.parquet` | 47,322 | 4,299 | Promoter/FII/DII/Public %, +25d lag |
| `xbrl_quarterly_results.parquet` | 581 | 35 | XBRL quarterly filings with Revenue/Profit/EPS (35 banking/financial cos) |

**Year-by-year coverage (unified_quarterly_pit):**
| Year | Companies | Rows | Exact NSE dates |
|---|---|---|---|
| 2020 | 1,850 | 3,696 | 80.4% |
| 2021 | 1,977 | 7,524 | 82.5% |
| 2022 | 2,154 | 7,984 | 81.4% |
| 2023 | 2,245 | 8,029 | 87.6% |
| 2024 | 495 | 1,927 | 94.0% (NSE+BM) |
| 2025 | 494 | 1,962 | 95.3% (board meetings) |
| 2026 | 489 | 489 | 98.0% (board meetings) |

**Nifty 500 specific:** 11,623 rows (2019+), all 500 companies, ~88% exact dates.

**date_source values:** `nse_broadcast` = exact NSE filing date, `board_meeting` = board meeting date (tight proxy), `conservative_lag_50d` = quarter_end + 50 days.

**Usage (no lookahead bias):**
```python
import pyarrow.parquet as pq
df = pq.read_table("datasets/earnings_pit/unified_quarterly_pit.parquet").to_pandas()
# Only use rows where available_date <= your_trading_date
known = df[df['available_date'] <= '2023-01-15']
# date_source: 'nse_broadcast' = exact, 'conservative_lag_50d' = safe assumption
```

**Earnings data limitations:**
1. Quarterly depth: max ~13 quarters per company from Screener scrape; annual data goes back to 2004
2. 2025-2026 filing dates now mostly covered via board meetings (95-98%), only ~5% still use +50d lag
3. No consensus estimates (need I/B/E/S or FactSet for EPS surprise)
4. Pre-2019 filing dates use conservative lag (+50d), not exact broadCastDate
5. ~2,200 Kaggle companies without NSE symbols excluded from unified (non-listed or BSE-only)
6. 217 Nifty 500 symbols (HDFCLIFE, SBILIFE, MCX, etc.) not in NSE quarterly results API (insurance/financial cos file under different NSE category — needs re-fetch without `index=equities` filter from non-corporate-proxied network)

#### Derived Datasets — `datasets/derived/` (NEW 2026-07-03)
| File | Rows | Description |
|---|---|---|
| `corporate_action_factors.parquet` | 613 | 282 bonuses, 281 splits, 50 dividends — symbol, ex_date, action_type, adjustment_factor |
| `cumulative_adj_factors.parquet` | 563 | Cumulative split/bonus factor per symbol for historical price adjustment |
| `sector_industry_map.parquet` | 2,235 | NSE symbol → Screener sector (80 sectors), 85.6% Nifty 500 covered |
| `earnings_beat_miss.parquet` | 31,891 | YoY/QoQ profit+sales growth, beat/miss/strong_beat flags, turnaround/deterioration |
| `nifty_oi_surface.parquet` | 377,034 | NIFTY options OI by strike, DTE<=35, Jun 2021 → May 2026, 402 trading days |
| `banknifty_oi_surface.parquet` | 256,187 | Same for BANKNIFTY |
| `nifty_oi_daily_summary.parquet` | 1,276 | Daily max pain strike, PCR (OI+volume), max CE/PE OI strikes |
| `shareholding_changes.parquet` | 21,713 | QoQ/YoY changes for FII/DII/Promoter/Public for 2,054 companies |

#### Screener Deep Scrape — `datasets/screener_deep/` (COMPLETE 2026-07-03)
- `screener_balance_sheet.parquet`: 5,022 rows, 62 cols — 500 cos × ~10 metrics, Mar 2002→Mar 2026
- `screener_cash_flow.parquet`: 3,000 rows, 61 cols — 500 cos × 6 metrics (CFO/CFI/CFF)
- `screener_annual_pl.parquet`: 6,000 rows, 73 cols — 500 cos × 12 metrics (Sales→EPS), Mar 2002→Mar 2026+TTM
- All 500/500 Nifty 500 companies scraped, 0 errors. Extends existing quarterly-only PIT data

#### Angel Daily Bulk 2026 — `datasets/angel_daily_2026/` (COMPLETE 2026-07-03)
- Feb-Jul 2026 OHLCV for 477/500 Nifty 500 stocks (48,654 rows, 95.4% coverage)
- 23 stocks still rate-limited (Angel AB1021) — retry after ~1hr cooldown
- Consolidated: `datasets/angel_daily_n500_2026.parquet` (48,654 rows, 477 symbols)
- Token map: `datasets/angel_instrument_list.json` (2,465 NSE EQ tokens)

#### Nifty Stock Daily Metadata — `datasets/nifty_stock_daily/1_meta.csv`
- **Source:** HuggingFace `jason1966/akshaypawar7_nifty-dataset`
- **Size:** Small — 505 stocks with index membership flags (Nifty 50/500/Bank/etc) and industry classification

#### Nifty 50 Weights — `datasets/nifty50_weights/`
- 2 files, 0.1 MB — Index constituent weights

### 3E. Nifty 500 Constituent Data & Symbol Mapping

#### Historical Ticker List — `NIFTY500_TICKER_2005_2025_Final.xlsx`
- 21,040 rows × 2 columns (Month-Year, Ticker)
- 42 monthly snapshots Mar 2005 to Sep 2025
- 1,004 unique tickers, ~501 stocks per month average
- THE KEY FILE for point-in-time index membership (survivorship-bias-free backtests)

#### Master Dataset — `Nifty500_Master_Dataset_2005_2025.xlsx`
- 5,363 rows × ~1,200 columns (Date + 976 unique ticker columns)
- Daily prices 2005-2025 for all stocks that were Nifty 500 members
- Contains special-char symbols as columns (M&M, L&TFH, MCDOWELL-N, etc.)

#### Delisted Dataset — `Nifty500_Delisted_2005_2025.xlsx`
- 1,321 rows × 149 columns
- 148 delisted ticker columns with daily prices

#### Symbol Mapping — `datasets/nifty500_symbol_mapping.json`
Comprehensive mapping with 5 sections:
- **encoding_fixes (10):** Excel ticker file strips `&` and `-` from NSE symbols (MM→M&M, BAJAJAUTO→BAJAJ-AUTO, etc.)
- **renames (56):** ZOMATO→ETERNAL, LTIM→LTM, AMARAJABAT→ARE&M, SWANENERGY→SWANCORP, HBLPOWER→HBLENGINE, IBULHSGFIN→IBULLSLTD, PEL→PIRAMALFIN, GLS→GLAXO, ILFSENGG→IL&FSENGG, BHARATFIN→INDUSINDBK(merger), ILFSTRANS→IL&FSTRANS, CADILAHC→ZYDUSLIFE, GMRINFRA→GMRAIRPORT, HDFC→HDFCBANK(merger), etc.
- **mergers (25):** Bank consolidations (SYNDIBANK→CANBK, ALBK→INDIANB, etc.)
- **demergers (3):** TATAMOTORS→TMCV+TMPV, MAX→MAXHEALTH+MAXFIN, JUBILANT→JUBLFOOD+JUBLPHARMA
- **delisted_nclt (27):** DHFL, COXKINGS, JETAIRWAYS, HEXAWARE, etc.
- **data_quality_issues (4):** IISL, GLS, TIFIN, TRIL (minor gaps)

#### Angel API Gap Fills — `datasets/angel_daily_missing/`
20 individual parquets + 1 combined, daily OHLCV from Angel API (2005 to 2026-07-02):
| File | Rows | Date Range | Covers |
|---|---|---|---|
| `ETERNAL_daily.parquet` | 1,220 | 2021-07-23 to 2026-07-01 | ZOMATO (renamed Jan 2025) |
| `JSWDULUX_daily.parquet` | 2,838 | 2015-01-02 to 2026-07-01 | New listing |
| `KESORAMIND_daily.parquet` | 2,838 | 2015-01-02 to 2026-07-01 | Not in HF |
| `SADBHAV_daily.parquet` | 2,838 | 2015-01-02 to 2026-07-01 | Not in HF |
| `NETWORK18_daily.parquet` | 2,837 | 2015-01-02 to 2026-07-01 | Covers TV18BRDCST |
| `UNITDSPR_daily.parquet` | 2,838 | 2015-01-02 to 2026-07-01 | Covers MCDOWELL-N |
| `LTM_daily.parquet` | 2,457 | 2016-07-21 to 2026-07-01 | LTIM renamed |
| `ARE&M_daily.parquet` | 2,838 | 2015-01-02 to 2026-07-01 | AMARAJABAT renamed |
| `SWANCORP_daily.parquet` | 3,478 | 2012-05-29 to 2026-07-01 | SWANENERGY (renamed) |
| `HBLENGINE_daily.parquet` | 4,810 | 2007-01-04 to 2026-07-01 | HBLPOWER (renamed) |
| `IBULLSLTD_daily.parquet` | 3,614 | 2011-08-18 to 2026-07-01 | IBULHSGFIN (renamed) |
| `PIRAMALFIN_daily.parquet` | 159 | 2025-11-07 to 2026-07-01 | PEL (demerger Nov 2025) |
| `GLAXO_daily.parquet` | 5,313 | 2005-01-03 to 2026-07-02 | GLS (GlaxoSmithKline Pharma, symbol change) |
| `IL&FSENGG_daily.parquet` | 4,609 | 2007-10-25 to 2026-07-02 | ILFSENGG (IL&FS Engineering, & encoding) |
| `BHARATFIN_daily.parquet` | 1,947 | 2011-08-12 to 2019-07-04 | BSE:533519, merged into INDUSINDBK Jul 2019 |
| `VISHAL_daily.parquet` | 2,430 | 2014-08-20 to 2026-07-02 | BSE:538598, Vishal (see data_quality note) |
| `IISL_daily.parquet` | 811 | 2023-03-16 to 2026-07-02 | BSE:540134 (see data_quality note) |
| `ILANDFSTRANS_daily.parquet` | 809 | 2022-11-21 to 2026-07-02 | IL&FS Transportation Networks |
| `TRIL_daily.parquet` | 750 | 2023-06-01 to 2026-07-02 | BSE:543915, Transformers & Rectifiers India |
| `TIFIN_daily.parquet` | 23 | 2023-11-23 to 2023-12-28 | BSE:544024, TI Financial (very limited) |
| `all_angel_daily.parquet` | 15,409 | Combined (first 6) | Legacy combined file |
Schema: timestamp, symbol, open, high, low, close, volume

#### Current Nifty 500 — `datasets/nifty500_current_2026.json`
- 500 stocks with company name, industry, symbol (as of Jul 2026)

#### Coverage Summary (audited 2026-07-01)
- **Historical (2005-2025):** 999/1000 real tickers = **99.9%** across HF+Master+Delisted+Angel
- **Current Nifty 500 (Jul 2026):** 500/500 = **100%**
- **ONLY 1 ticker truly missing: COXKINGS** (Cox & Kings, NCLT/fraud, purged from all exchanges, 29 months in index)
- **8 new stocks recovered (2026-07-02):** GLS→GLAXO, ILFSENGG→IL&FSENGG, BHARATFIN(BSE), VISHAL(BSE), IISL(BSE), IL&FSTRANS, TRIL(BSE), TIFIN(BSE)
- **HF daily data** ends 2026-01-22. **Angel daily data** covers 20 stocks to 2026-07-02. Bulk Feb-Jul 2026 gap for remaining ~2,500 HF symbols still open.
- **1-min index data:** 136 indices from Kaggle (2015-2026) + NIFTY/BANKNIFTY/SENSEX spot from options dataset (2021-2026)
- **ATM options:** MONTH 42/42, WEEK 42/42 = **100% COMPLETE** (recovered from artist-23)
- **Options gaps remaining:** BANKNIFTY weekly missing (monthly only)

### 3F. Other Raw Data — `raw/`
| Subdirectory | Files | Size | Description |
|---|---|---|---|
| `books/` | 62 | 1,044 MB | Reference books/PDFs |
| `corporate_actions/` | 359 | 0.2 MB | NSE corporate action JSONs |
| `financial_metadata/` | 244 | 23 MB | Company financial metadata |
| `nifty500/` | 239 | 51 MB | Nifty 500 constituent data |
| `xbrl_cache/` | 581 | 20 MB | XBRL financial filing cache |

---

## 4. DATA DOWNLOAD SCRIPTS — `intraday_options_strategy/data/`

| Script | Purpose | Status |
|---|---|---|
| `hf_chunked.py` | Generic HF downloader (80MB segments, auto-retry). The go-to for large files through corporate proxy. | WORKING |
| `hf_stock_options_v3.py` | Stock options downloader — sequential, `requests.Session()` reuse. **THE PATTERN THAT WORKS through corporate proxy.** | COMPLETED |
| `hf_stock_options_v2.py` | v2 attempt (2 workers) — STALLED through proxy | STALLED |
| `hf_stock_options.py` | v1 attempt (6 workers) — STALLED through proxy | STALLED |
| `hf_earnings_fundamentals.py` | Downloads MiMIC earnings + Charon107 fundamentals | COMPLETED |
| `hf_india_news.py` | India financial news downloader | COMPLETED |
| `hf_news_all.py` | All news datasets downloader | COMPLETED |
| `nse_earnings_history.py` | NSE board meetings + corporate actions fetcher | COMPLETED |
| `download_kaggle_resume.py` | Kaggle bhavcopy downloader with resume | COMPLETED |
| `hf_direct.py` | Direct HF download (small files) | COMPLETED |
| `angel_fetch_options.py` | Angel One API options data fetcher | WORKING |
| `angel_scripmaster.py` | Angel One scripmaster (instrument list) fetcher | WORKING |
| `calibrate_iv.py` | IV calibration from live market data | WORKING |
| `build_dataset.py` | Build consolidated dataset from raw data | WORKING |

### Download pattern that works through corporate proxy:
```python
import truststore; truststore.inject_into_ssl()
import requests

TOKEN = "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"
session = requests.Session()
session.headers.update({"Authorization": f"Bearer {TOKEN}"})

# Sequential downloads, NO threading (proxy kills concurrent connections)
for fname in files_to_download:
    url = f"https://huggingface.co/datasets/{REPO}/resolve/main/{fname}?download=true"
    r = session.get(url, stream=True, timeout=120)
    r.raise_for_status()
    with open(local_path, 'wb') as f:
        for chunk in r.iter_content(1024 * 1024):
            if chunk:
                f.write(chunk)
```

### Fixing truncated parquets (missing footer):
```python
import requests, truststore; truststore.inject_into_ssl()
session = requests.Session()
session.headers.update({"Authorization": f"Bearer {TOKEN}"})

local_size = local_path.stat().st_size
expected_size = ...  # from HF API
missing = expected_size - local_size
headers = {"Range": f"bytes={local_size}-{expected_size-1}"}
r = session.get(url, headers=headers, stream=True, timeout=120)
with open(local_path, 'ab') as f:
    for chunk in r.iter_content(1024*1024):
        if chunk: f.write(chunk)
```

---

## 5. TRACK 1 — Intraday Options Strategy (MATURE)

**Location:** `intraday_options_strategy/`
**Status:** COMPLETE & audit-clean. Real-fill validated.

### What it does
Delta-hedged 0DTE+DTE1 short straddle on NIFTY, with IV filter. Kelly×0.25 sizing, synthetic BS pricing, walk-forward optimization.

### Key results
- **Unfiltered** (259 trades): CAGR +1.3%, MaxDD 17.7%, WR 58%
- **IV-filtered** (160 trades, straddle >= 0.45% of spot): CAGR +5.9%, MaxDD 5.0%, WR 64%
- All 6 years (2021-2026) positive with IV filter
- Real Sharpe ~1.0-1.2

### Key files
| File | Purpose |
|---|---|
| `config.py` | Strategy parameters. **NOTE: LOT_SIZE still says 75, should be 65** |
| `main.py` | Core strategy engine |
| `run_today_live.py` | Live trading runner (Angel One API) |
| `run_realfill_deltahedged.py` | Real-fill backtest with delta hedging |
| `results/REPORT.md` | Full backtest report |
| `results/AUDIT.md` | Strategy audit |
| `results/EXECUTIVE_SUMMARY.md` | Executive summary |
| `results/realfill_deltahedged_nifty.csv` | Real-fill results data |
| `results/STRATEGIES_COMPARISON.md` | Multi-strategy comparison |
| `results/V2_REPORT.md` | V2 strategy report |
| `results/V3_FINDINGS.md` | V3 improvements |

### Live trading flow
1. Check straddle >= 0.45% of spot BEFORE deploying
2. Run `run_today_live.py`
3. Uses Angel One API (SmartApi SDK)

---

## 6. TRACK 2 — Swing Momentum (IN PROGRESS)

**Location:** `swing_momentum/`
**Status:** Engine built, needs upgrades.

### Key files
| File | Purpose |
|---|---|
| `PLAN.md` | Phase-by-phase build plan (7 phases) |
| `GOD_TIER_EXPANSION.md` | 10 capacity-limited dimensions (D1-D10) |
| `FRONTIER_DIMENSIONS_2026_2040.md` | D11-D14 (adversarially filtered from 54 ideas) |
| `FORWARD_WATCHLIST.md` | Thematic sector watchlist |
| `MULTIBAGGER_DNA.md` | Multibagger characteristics |
| `run_swing.py` | Main swing strategy runner |
| `run_multistrat.py` | Multi-strategy combiner |
| `RESULTS.md` | Current backtest results |

### What's needed next (priority order)
1. **Sector map + fundamentals** (RoE/debt/EPS-growth) + volume for 976-symbol universe
2. **Two-stage stop** (tight initial + WIDE ~25-30% trailing)
3. **Regime-scaled leverage** (0 cash / 1.0 green / 1.25-1.5x strong-breadth)
4. **Quality-momentum overlay**
5. **Sector-tilt** to EARLY themes + froth-exit overlay

---

## 7. TRACK 3 — Alpha Research (EARLY)

**Location:** `alpha_research/`
**Status:** Plan written, H1 data-ready.

### Key concept
Model PARTICIPANT STATE & FRAGILITY (forced flows of dealers/retail/passive), not price/value.

### Hypotheses (from PLAN.md)
- **H1:** Dealer-gamma/OI surface from bhavcopy → GEX & zero-gamma flip → event-study
- H2-H7: Additional research dimensions (see PLAN.md)

### Data available for H1
Kaggle bhavcopy data (732 files, 4.0 GB) has the OI data needed to reconstruct gamma surfaces.

---

## 8. KNOWN ISSUES & WORKAROUNDS

| Issue | Detail | Workaround |
|---|---|---|
| `python` alias broken | System `python` command doesn't work | Use full path: `C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe` |
| Console encoding | cp1252 causes unicode errors | Set `PYTHONIOENCODING=utf-8` |
| Corporate proxy kills threads | Concurrent HF downloads stall | Use sequential `requests.Session()` reuse (see §4) |
| OneDrive `=` filenames | PowerShell can't delete files with `=` in OneDrive paths | Use Bash `rm -rf` instead |
| Train.parquet corruption | `annual_report` column has snappy corruption at HF source | Read only `company_name`, `year`, `label` columns |
| **HF timezone bug** | **HF daily timestamps are 18:30 UTC = midnight IST next day. `.date()` on UTC gives WRONG date (1 day behind, shows Sun/Sat as trading days)** | **`df['date'] = df['timestamp'].dt.tz_convert('Asia/Kolkata').dt.date`** |
| LOT_SIZE in config.py | Still says 75 | Should be 65 (per Angel scripmaster 2026) |
| MB vs MiB confusion | HF reports decimal MB (1e6), PowerShell uses binary MiB (1048576) | Be aware when comparing sizes |

---

## 9. DATA VERIFICATION HISTORY (2026-07-01)

### What was checked
- **667 parquet files** across entire project tree scanned with `pyarrow.read_metadata()`
- **2,319 stock options parquets** verified separately after download completion
- Zero-byte file scan across entire project
- Size matching against HuggingFace expected sizes

### What was fixed
| File | Issue | Fix |
|---|---|---|
| `swing_momentum/data/hf_stock_minute/minute/train-00002.parquet` | Truncated (missing ~82 KB) | HTTP Range request tail append |
| `swing_momentum/data/hf_stock_minute/minute/train-00003.parquet` | Truncated (missing ~12 KB) | HTTP Range request tail append |
| `swing_momentum/data/hf_stock_minute/minute/train-00004.parquet` | Truncated (missing ~45 KB) | HTTP Range request tail append |
| `swing_momentum/data/hf_stock_minute/minute/train-00005.parquet` | Truncated (missing ~30 KB) | HTTP Range request tail append |
| `datasets/yahoo_finance/stock_earning_call_transcripts.parquet` | Truncated (missing 348 KB) | HTTP Range request tail append |

### What was cleaned
- ~600 MB of `.cache` directories removed
- Zero-byte ghost file in daily_forex removed (HF repo restructured, directory deleted)
- Empty log files cleaned

### Final result
**0 corrupt parquets across ~3,000 files, ~25+ GB total**

---

## 10. PENDING TASKS (priority order)

0. **DONE (2026-07-03):** Full multi-dimensional data audit complete — stocks, 1-min, options, bhavcopy, news, fundamentals, earnings. PIT earnings dataset built: `unified_quarterly_pit.parquet` (31,891 rows, 2,296 companies, 2005-2026, 77% exact NSE dates for 2019+, 100% Net Profit coverage). Screener.in batch scrape: 500/500 Nifty 500 companies, 6,270 quarterly records (2023-2026). NSE broadcast date matching fixed and merged. Coverage: 99.9% historical, 100% current. See §3D.
0.5. **OPTIONAL: Bulk Feb-Jul 2026 gap fill** for all ~2,500 HF symbols via Angel API batch (HF ends Jan 2026). Low priority unless Track 2 needs recent data NOW.
0.6. **OPTIONAL: BANKNIFTY weekly options** — only 61 monthly files in HF dataset. Kaggle `ayushsacri` may have weekly data. Requires Kaggle credentials.
0.7. **OPTIONAL: Kaggle datasets** (FII/DII flows, additional options, NSE F&O OI history) — requires `~/.kaggle/kaggle.json` setup. Kaggle CLI broken on Python 3.14.
1. **Track 2 data fetch — MOSTLY DONE (2026-07-03):** Sector map (2,235 symbols), earnings beat/miss flags, corporate action adjustments, Angel bulk OHLCV (~200 stocks) ALL BUILT. Remaining: complete Angel OHLCV for remaining ~300 stocks (slower rate limit needed), FII/DII flows (NSE blocked by corporate proxy).
2. **Track 2 engine upgrades**: two-stage stop, regime-scaled leverage, quality-momentum overlay using new `earnings_beat_miss.parquet` + `sector_industry_map.parquet`, sector-tilt. Then re-run `run_swing.py`.
3. **Track 1 finish**: Fix LOT_SIZE 65 vs 75 in `config.py`. Validate live over more weekly expiries. 30-day Angel paper run (ONLY on IV-filter days).
4. **Multi-strat proof**: Combine swing-equity + options-short-vol daily P&L to prove diversification benefit.
5. **Track 3 H1 — DATA READY (2026-07-03):** OI surface built (`nifty_oi_surface.parquet`: 377K rows, Jun 2021→May 2026). Next: GEX calculation, zero-gamma flip event-study, max-pain reversion signals.
6. **Build Risk OS** (from other2/OPERATING_STANDARD_2026.md): vol-targeting, heat cap, correlation-regime monitor, layered DD circuit-breakers.
7. **NSE API items (need VPN/home network):** FII/DII flows, Nifty Total Market / MicroCap 250 constituents, re-fetch quarterly results for insurance/financial cos without `index=equities` filter.

---

## 11. HuggingFace DATASET SOURCES

| HF Repo | Local Location | What |
|---|---|---|
| `Saintforest/indian-stock-market-minute-data` | `swing_momentum/data/hf_stock_minute/` | Indian stock minute + daily prices |
| `thetrademarkk/india-index-options-1m` | `intraday_options_strategy/datasets/raw/hf_index_options_1m/` | NIFTY/BANKNIFTY + stock options 1-min |
| `defeatbeta/yahoo-finance-data` | `datasets/yahoo_finance/` | US stock data (prices, transcripts, news, filings) |
| `Charon107/indian_companies_fundamentals_moneycontrol` | `datasets/india_fundamentals_mc/` | Indian company fundamentals |
| MiMIC (various) | `datasets/india_earnings_calls/` | Indian earnings call transcripts |
| `artist-23/nifty-options-data` | `intraday_options_strategy/datasets/raw/hf_atm_options/` | ATM options (MONTH+WEEK, 42+42 files) |
| `kjhq/India-Stock-Symbols-and-Metadata` | `datasets/india_stock_metadata/` | Indian stock symbols & metadata |
| `jason1966/akshaypawar7_nifty-dataset` | `datasets/nifty_stock_daily/` | Nifty stock metadata (index membership) |
| Kaggle `sameerprogrammer/...` | `datasets/kaggle_indian_financials/` | 4,492 company financials (QPL, BS, CF, Ratios) |
| Various news repos | `datasets/*/` | News datasets (see §3C) |

---

## 12. QUICK-START FOR NEW SESSION

```
1. Read RESUME_TOMORROW.md (master index)
2. Read this HANDOFF.md for data locations and formats
3. Set Python: $python = "C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe"
4. Set encoding: $env:PYTHONIOENCODING = "utf-8"; $env:PYTHONUNBUFFERED = "1"
5. For any HF downloads: use truststore.inject_into_ssl() + sequential requests.Session()
6. Check PLAN.md in the relevant track directory for detailed next steps
7. All data is verified and ready to use as of 2026-07-01
```
