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
