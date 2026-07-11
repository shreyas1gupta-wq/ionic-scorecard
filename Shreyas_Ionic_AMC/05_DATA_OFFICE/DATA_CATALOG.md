# DATA CATALOG — single source of truth (Data Officer: Kavya Reddy)
Rule: if it's not in here with path+range+bugs, it doesn't exist for research. Counts marked [books] are per DESK-20's journal/RESUME_TOMORROW (not re-verified by DESK-100); unmarked = verified on disk 2026-07-03.

## 1. Options (single-stock + index)
| Dataset | Path (under root) | Granularity | Coverage | Notes/Bugs |
|---|---|---|---|---|
| Single-stock options, 210 F&O names | `intraday_options_strategy/datasets/raw/hf_index_options_1m/stocks_options/{SYM}/{expiry}.parquet` | MIXED: HF 1-min + bhavcopy DAILY | 2021-07→2026-06 **continuous** (gap FILLED 2026-07-03); +122 new names 2024-07→2026-06 daily | DUAL SCHEMA — see DATA_QUALITY_RULES; 0.00-price untraded strikes in daily files; 88 legacy names have 1-min where HF had it |
| NIFTY weekly options 1-min | `.../hf_index_options_1m/` (index dirs) | 1-min | 261 weekly expiries 2021→2026 | accessor: `buying/chain.py` |
| Live forward capture (Angel) | `intraday_options_strategy/datasets/angel_capture_2026/{day,minute}/{SYM}/{expiry}.parquet` | 1-day full life + 1-min (front, rolling) | Jul-2026 → ongoing | fed by `AngelDailyOptionCapture` task 15:45/20:00/23:00; ±10% strikes, 2 expiries |
| NIFTY+BANKNIFTY OI surface | `datasets/derived/nifty_oi_surface.parquet` (377,034) + `banknifty_oi_surface.parquet` (256,187) + `nifty_oi_daily_summary.parquet` (1,276) | **SPARSE snapshots** — NIFTY 402 distinct dates over 2021-06→2026-05 (~31% coverage, 3-16d gaps); BANKNIFTY **stale after 2024-07-04** | 633,221 rows total (verified 2026-07-03, Ishaan) | **PARTIALLY READY** for GEX: no spot/IV/greeks cols on disk — needs spot join + cadence fix before Track-3 gate; max-pain/PCR summary only to 2024-07 |

## 2. Equity prices
| Dataset | Path | Granularity | Coverage | Notes |
|---|---|---|---|---|
| Stock daily (HF) | `swing_momentum/data/hf_stock_minute/day/train-00000.parquet` | daily | →2026-01-22 (**stale tail**) | tz landmine #1; asof() after Jan-26 returns stale prices |
| Stock 1-min (HF) | `swing_momentum/data/hf_stock_minute/` | 1-min | 813M bars 2022-2026 [books] | auction landmine #2 |
| Angel daily 2026 bulk | [books] per RESUME_TOMORROW | daily | 477/500 Feb–Jul-2026; 23 stragglers pending | retry list in RESUME_TOMORROW |
| Daily 2005-2026 long history | [books] | daily | 2005→2026 | with 42 PIT snapshots for survivorship |

## 3. Fundamentals / earnings / ownership (PIT discipline mandatory)
| Dataset | Path | Coverage | Notes |
|---|---|---|---|
| PIT quarterly earnings | `datasets/earnings_pit/unified_quarterly_pit.parquet` | 86.2% exact `available_date` (2025: 95.3%, 2026: 98%) [books] | THE earnings join key |
| Earnings calendar (historical) | `datasets/nse_earnings_dates/earnings_dates.csv` | 2020-01→2026-07 | purpose-filter "Financial Results" |
| Forthcoming results | `datasets/nse_earnings_dates/forthcoming_results.csv` | rolling (refreshed 2026-07-03: 27 Q1-FY27 dates) | refresh via NSE api (cookie warm-up) |
| Screener deep fundamentals | `datasets/screener_deep/` | BS 5,022 / CF 3,000 / PL 6,000 rows (verified 2026-07-04) | **PIT WARNING (Sanjay, 2026-07-04): NO available_date col — fiscal-period cols only; naive use = LOOKAHEAD. Kavya to rule stamping method (join unified_quarterly_pit / +6mo lag) before ANY signal use** |
| Beat/miss (SUE proxy) | `datasets/derived/earnings_beat_miss.parquet` | 31,891 rows [books] | revision-sleeve proxy |
| Shareholding changes | `datasets/derived/shareholding_changes.parquet` | 21,713 QoQ/YoY [books] | flow sleeve (FII/DII/promoter) |
| Corporate actions | `datasets/derived/corporate_action_factors` | 613 events [books] | + cumulative adj factors |
| MC fundamentals | `india_fundamentals_mc/Train.parquet` | — | `annual_report` col CORRUPT (landmine #5) |
| Universe snapshots | `NIFTY500_TICKER_2005_2025_Final.xlsx` | 42 PIT snapshots 2005-25 | survivorship (landmine #6) |

## 3b. Commodities (ETF route)
| Dataset | Path | Coverage | Notes |
|---|---|---|---|
| GOLDBEES daily | `datasets/etf_gold_silver/goldbees_daily.parquet` | 1,357 rows, 2021-01-10→2026-07-02 | D-009 PASS (Kavya 2026-07-04): 7/7 checks, split pre-adjusted, PIT-safe; UTC stamps (+5:30 for IST); update via Angel token 14428 |
| SILVERBEES daily | `datasets/etf_gold_silver/silverbees_daily.parquet` | 1,091 rows, 2022-02-06→2026-07-02 | D-009 PASS; listed 2022-02-07; token 8080 |

## 4. Text / sentiment
| Dataset | Path | Size | Notes |
|---|---|---|---|
| India financial news | `datasets/india_fin_news` [books] | 125K docs, tier-segregated | FinBERT target |
| Earnings-call transcripts | MiMIC set [books] | 1,042 calls | prepared vs Q&A split; join on available_date |

## 5. Strategy outputs (regenerable; source scripts in `intraday_options_strategy/buying/`)
| Output | Path | Regenerate via |
|---|---|---|
| IV/RV trades (210 univ, IV<100% cap) | `buying/rv_iv_vol.parquet` (3,468 rows) | `rv_iv_vol.py` |
| FF calendar candidates (2,612) | `buying/forward_factor_v2.parquet` | `forward_factor_v2.py` |
| Earnings-vol events (1,359) | `buying/stock_earnings_vol.parquet` | `stock_earnings_vol.py` |
| Strangle/jade trades (5,039) | `buying/shortlist_shortvol.parquet` | `shortlist_shortvol.py` |
| Portfolio monthly | `buying/portfolio_monthly_v2.parquet` | `filtered_portfolio.py` |
| Execution sheets + conviction | `FINAL_STRATEGY_FORWARD_CHECK/08_Execution/*.csv` | scratchpad `execution_scanner.py` + `final_execution.py` (rehome to firm repo pending) |

## 6. Reference/config
- Angel scrip master: scratchpad `scrip_master.json` (31MB, refresh daily in capture task) — 153K instruments, 210 OPTSTK names.
- Angel instrument tokens for ETFs (GOLDBEES/SILVERBEES): `datasets/angel_instrument_list.json` [books].

## Update commands (rehome scratchpad scripts → `Shreyas_Ionic_AMC/05_DATA_OFFICE/scripts/` = TODO)
- Option gap/expand backfill: `bhavcopy_backfill.py`, `expanded_backfill.py` (currently in DESK-100 session scratchpad — COPY INTO REPO before scratchpad GC).
- Daily capture: `C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture\daily_capture.py` (outside repo by design — creds adjacency).
| factor_navs_principal | `datasets/index_daily/factor_navs_principal.parquet` (source: Principal-contributed `factor_navs (1).xlsx`, root) | 22 official NSE index NAV series DAILY 2005-04-01 -> 2026-02-27 (5,189 d): N200 Momentum 30 (FULL), N100 LowVol 30, N200 Quality/Value/Alpha 30, N500 Momentum 50/Value 50, Midcap Momentum 50, Smallcap QualMom 100, HighBeta 50, broad indices, GOLDBEES, liquid fund | **D-009 VERIFIED 2026-07-04**: LOWVOL30 2026-02-27 = 20495.0 EXACT match vs independent Angel official series (ratio 1.000, price-index basis). Long format: date/series/nav | Replication benchmark (D-M4); extend past Feb-26 via Angel tokens + nse_official_all_indices.parquet (puller live) |
| nse_official_all_indices | `datasets/index_daily/nse_official_all_indices.parquet` | **COMPLETE 2026-07-04**: 246,597 rows, 174 NSE indices, OHLC+PE/PB/divyield, 2016-01->2026-07-03 (momentum family from 2016-07-07 incl Nifty200 Momentum 30, 1,447d) | **D-009 TRIPLE-VERIFIED: 0.000% max diff vs factor_navs over ALL 1,365 overlap days** (+ Angel token series) | Official benchmark series; daily append via EOD (task ShreyasIonicAMC_IndexClose) |
| sector_industry_map | `datasets/derived/sector_industry_map.parquet` | sector/industry classification, ~976 symbols | UNVERIFIED provenance (inferred vs official NSE codes?) — Kavya to validate before any sector-tilt backtest quotes it | Feeds MULTIBAGGER_DNA sector-momentum overlay (SIG-12) |
| nifty500_master_wide | `Nifty500_Master_Dataset_2005_2025.xlsx` (root, 33.7MB) | daily close-only wide matrix, 5363 d x ~1200 tickers, 2005-2025, incl delisted | Disk-verified 2026-07-04 (inventory sweep). Close-only — use parquet panel for OHLCV | Survivorship-safe price reference; cross-check vs panel |
| nifty500_delisted | `Nifty500_Delisted_2005_2025.xlsx` (root) | delisted/merged names + dates; 239 with daily histories | Disk-verified 2026-07-04 | Delisting-loss realization in backtests (V1->V2 halved CAGR — real lesson) |
| n50_next50_composition | `Historical stock composition of Nifty 50 and Nifty Next 50.xlsx` (root) | monthly membership matrices 2008-> (wide: ticker x month) | Disk-verified 2026-07-04 | N100 = N50 UNION Next50 -> LOWVOL30-v2 exact universe (D-M4, in use tonight) |
| n200_constituents | `NIFTY200_TICKER_2005_2025.xlsx` (root) | monthly N200 membership 2005-2025 (long: Month-Year, Ticker; 8490 rows) | Disk-verified 2026-07-04 | NIFTY200MOMENTM30 exact replication universe (D-M4, in use tonight) |
| multibagger_winners | `swing_momentum/multibaggers/winners_yearwise_50pct.csv` + `top40_per_year.csv` (legacy, read-only; generated by run_multibagger_dump.py from processed/eq_close.parquet) | all >=50% winner-years 2007-2025 (1677 rows) + top-40/yr | From survivorship-safe panel per MULTIBAGGER_STUDY | Winner-profiling research; SIG-12 overlay validation set |
| strategy_results_legacy | `Strategy_Results/Backtest_Results.xlsx` + `swing_momentum/Backtest_Results_India.xlsx` (legacy, read-only) | 4 momentum variants 2006-2025 w/ sensitivity grids + survivorship tests (honest Sharpe ~1.4 ceiling) | Costs 0.375%/side; NO liquidity gate (biggest optimism, flagged in source) | Honest baseline for Track-2 board comparisons; dedup check pending |
| stocks_data_cache | `stocks_data_cache.pkl` (root, Principal-contributed 2026-07-04) | yfinance dict: price 435 tickers 2020-06->2026-01 OHLCV (ADJUSTED, verified), shares outstanding (435), TTM fundamentals (378), sectors, 42 universe snapshots | D-009 adjustment-verified on EICHERMOT/IRCTC ex-dates | TRUE mcap weights for replication D1 (modern era); SIG-12 quality overlay feeder |
| screener_dump_20260704 | `swing_momentum/screener-20260704T144220Z-3-001.zip` (Principal-contributed 2026-07-04) | 984 files (360 xlsx Premium_Report/FALLBACK_FULL/HTML_TABLES + 623 csv) — screener.in per-stock ANNUAL fundamentals Mar2013->Mar2021+, INCLUDING DELISTED names (RELCAPITAL, ORIENTBANK...) | **D-009 PASS (Kavya, 2026-07-04)** — 3/3 live samples verified; extracted to `datasets/screener_dump_20260704/` (347 companies; PnL/CashFlow CSVs Mar2014-TTM + FALLBACK_FULL 10-sheet xlsx). **PIT WARNING: restated as-of-2026-07-04 — FORBIDDEN for event/earnings-reaction work (T1); quality overlays only, T+90 lag min.** Delisted names thinner (FALLBACK only, no PnL csv) | Quality overlay (SIG-12); event work must use datasets/earnings_pit instead |
| xbrl_cache | `raw/xbrl_cache/` | 581 XBRL XMLs (BSE/NSE regulatory quarterly filings: BANKING_*, INDAS_*), ~2019-2023 | Raw regulatory format; needs parser | PIT quarterly fundamentals cross-check vs earnings_pit available_date |
| financial_metadata | `raw/financial_metadata/` | 244 per-stock JSONs (list-structured, ~197 records each; e.g. GLENMARK_meta.json) | Structure part-inspected; full schema pending | Candidate SIG-12 feeder; verify vs screener dump |
| raw_nifty500_delisted_csvs | `raw/nifty500/` | 239 per-stock daily OHLCV csvs (delisted names, SAMPLED windows e.g. 8KMILES 2015-2021) | COUNT CORRECTED 2026-07-04: 239 files (an earlier inventory said 1,905 — wrong) | Union-panel input (survivorship fix) |
| swing_processed_panel | `swing_momentum/processed/eq_close.parquet` + `membership.parquet` (legacy, read-only) | survivorship-safe close panel + membership behind MULTIBAGGER_STUDY | Presumed adjusted (study used it); verify vs forensics method | PRIME union-panel input |
| nse_bhavcopy_daily (PERMANENT) | `datasets/nse_bhavcopy_daily/close_all.parquet` (+ puller script in 05_DATA_OFFICE/scripts, resume-safe) | EVERY NSE-listed stock's official close, 5,569,110 rows, 3,716 symbols, 2013-01-01->2026-07-03 | Official as-traded source; used as ground truth for splices + IPO dates (caught 14 bad membership-xlsx rows) | Coverage questions end here; candidate daily-append |
| **pit_union_panel v1.1 (CANONICAL)** | `datasets/derived/pit_union_panel_v1/close_panel_{price,return}_v11.parquet` (v1 files unchanged — frozen-consumer md5s stay valid) | +126 bhavcopy-recovered names -> **ACHIEVABLE COVERAGE 2014+: 97.0-100%** (2016/2024/2025 = 100.0%); residuals fully named: SREINFRA (real NCLT discontinuity, quarantined not fudged), IISL (not a tradeable equity), UNKNOWN (data-entry artifact) | BUILD_REPORT.md v1.1; D-028 clean 0/0 | Use v11 for all NEW work; v1 for reproducing tonight's audited runs |
| pit_union_panel_v1 (superseded for new work) | `datasets/derived/pit_union_panel_v1/close_panel_{price,return}.parquet` | Survivorship-complete daily closes 2005->2026: PRICE basis 2,511 symbols (HF+Delisted+Raw500) / RETURN basis 2,556 (HF core + ratio-spliced) | Ground-truth based (bhavcopy 94.8%); 9 corrupt segments quarantined; aliases standardized; N200 full-252d coverage 2006 71.8% / 2014 95.5% / 2018 97.0% (vs HF-alone 59.9/83.6/87.9) | THE equity close panels: price-basis for replication/levels, return-basis for backtests. BUILD_REPORT.md has full provenance |

## D-033 ACQUISITION WAVE (2026-07-11) — all in 05_DATA_OFFICE/data/ unless noted; all D-009 spot-verified
| Dataset | File(s) | Span | Source | Verification |
|---|---|---|---|---|
| SPX daily close | us_sp500_daily.parquet | 1975-01..2026-07, n=12,988 | cdn.cboe.com SPX_History | 2020-03-23=2237.40 exact; 2024-12-31=5881.63 exact |
| CBOE vol suite daily | cboe_{vix,vix9d,vix3m,vix6m,vvix,skew}_daily.parquet | VIX 1990.., VVIX 2006.., SKEW 1990.., term 2008-11.. | cdn.cboe.com | VIX 2020-03-16=82.69 exact |
| Fama-French 5 factors daily | ff5_daily.parquet | 1963-07..2026-05, n=15,833 | Ken French/Dartmouth | schema+span sane |
| FF momentum daily | ff_mom_daily.parquet | 1926-11..2026-05, n=26,152 | Ken French/Dartmouth | schema+span sane |
| Gold (XAUUSD) 1-min | commodities_1m/XAUUSD_1m_{2009..2025}.parquet | 2009-01..2025-12, ~5.9M rows | HF fokan/xauusd-2009-2026 (HistData MT4 mirror) | 2020-08 high 2075 OK; 2020-03 low 1451 OK. NOTE: no 2026 file despite dataset name; timezone = HistData EST, NOT IST |
| BTC/ETH 1-min | crypto_1m/{BTCUSDT,ETHUSDT}_{yyyy}.parquet | 2018-01..2026-06 | data.binance.vision official dumps | IN PROGRESS (bg); verify BTC 2021-04 high ~64.8k on completion |
| US stocks daily bulk | us_stocks_daily/train-*.parquet (4 shards, 530MB) | max avail (PWB) | HF paperswithbacktest/Stocks-Daily-Price | IN PROGRESS (bg); verify ticker count + AAPL on completion |
| F&O bhavcopy index derivs | fo_bhavcopy_hist/fo_idx_{2011..2021}.parquet | 2011-01..2021-06 | nsearchives (old DERIVATIVES fmt) | IN PROGRESS (bg, ~2-3h); D-009 5-random-day check pending -> Kavya |

**Blocked/parked routes (2026-07-11):** Stooq (JS anti-bot), FRED (proxy reset), Yahoo (429), iShares holdings (HTML), silver/copper 1-min (no free mirror found), Kaggle (needs API key from Principal), paperswithbacktest Commodities/Indices-Daily (gated=manual -> Principal: click "agree" on HF page to unlock silver/copper daily instantly).
