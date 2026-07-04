# RESUME TOMORROW — master index (all tracks)
Built 2026-07-04. Read this first next session, then open the relevant track PLAN.

Python: `C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe`
(`python` alias broken). Set `PYTHONIOENCODING=utf-8` (console is cp1252, no unicode in prints).
Angel creds: user supplies via env vars (data-only account); rotate as hygiene.

## ELITE OPERATING LAYER (build BEFORE scaling) → `other2/OPERATING_STANDARD_2026.md`
(moved off root in the 2026-07-05 reorg — superseded in spirit by 00_GOVERNANCE/07_RISK_OFFICE but kept as source planning doc; see other2/MANIFEST.md)
What separates top-2026 from "good": NOT more signals. 8 systems wrapping all tracks —
S1 **Risk OS** (vol-targeting, heat cap, correlation-regime monitor, layered DD circuit-
breakers, tail/VaR budget, stress replays) ← build FIRST; S2 Execution/TCA (close sim↔live
slippage loop); S3 **Edge-decay detection** (alpha dies — auto-demote breaking sleeves);
S4 AI-augmented research + **audit-as-default** (no un-audited edge trades live); S5
India flow data (FII/DII, participant-wise OI — see new H8); S6 tax/LRS net model; S7
standing tail-hedge / crisis-alpha; S8 process/override discipline. Benchmarks: book net
Sharpe ≥2 good / ≥3 world-class (capacity-limited = our moat), Calmar ≥1.5, MaxDD <25%.

## CROSS-MARKET / CROSS-ASSET LAYER (above all tracks) → `other2/PORTFOLIO_OF_EDGES.md`
(moved off root in the 2026-07-05 reorg; see other2/MANIFEST.md)
Goal: stack uncorrelated edges on the SAME capital (≤₹10Cr) → ~√N Sharpe boost, lower
DD. Trade Indian (Kite: stocks/F&O/MCX) + US stocks/ETFs/commodity-ETFs (INDmoney/LRS).
**HONEST RULE: diversify by EDGE-TYPE (momentum vs short-vol vs commodity-trend vs
long-gamma) and ASSET-CLASS first — geography is weak diversification (US/India equities
correlate, →1 in crises). Short-vol stays INDIAN (no US retail options); US = swing +
commodity/bond diversifier. Timezone is a real win: Indian day + US night = same capital,
two sessions. Model US frictions (LRS cap, TCS, withholding, cap-gains, USD/INR) net.**

## DATA STATUS (verified 2026-07-01, all parquets corruption-checked)
| Dataset | Files | Size | Rows/Records | Status |
|---|---|---|---|---|
| Stock Minute (Saintforest) | 8 shards | 10.4 GB | 813.5M rows | OK |
| Stock Daily | 1 shard | 118 MB | 6.97M rows | OK |
| Index Options 1m | 467 files | 1.5 GB | — | OK |
| **Stock Options 1m** | **2,319 files** | **2.11 GB** | **—** | **OK (completed 2026-07-01)** |
| Yahoo Finance | 16 files | 3.8 GB | — | OK (transcript tail-fixed) |
| India Fin News (tier-segregated) | 9 files | 2.9 GB | 125K rows | OK |
| MoneyControl News | 1 file | 45 MB | — | OK |
| TOI Headlines | 1 file | 238 MB | — | OK |
| BBC News | 79 files | 206 MB | — | OK |
| Million Headlines | 1 file | 64 MB | — | OK |
| HuffPost | 1 file | 87 MB | — | OK |
| US Fin News | 1 file | 811 MB | — | OK |
| Reddit SP500 | 1 file | 2.5 GB | — | OK |
| GDELT | 1 file | 1.4 MB | — | OK |
| Nifty50 Weights | 1 file | 107 KB | — | OK |
| Kaggle Bhavcopy | 732 files | 4.0 GB | — | OK |
| ATM Options | 77 files | 663 MB | — | OK |
| India Earnings Calls (MiMIC) | 7 files | 246 MB | 1,042 calls | OK |
| India Fundamentals MC | 3 files | 1.0 GB | 3,968 rows | OK (annual_report col corrupt at HF source; label col has full financials) |
| NSE Earnings Dates | 8 files | 115 MB | 54,268 earnings dates, 2,532 symbols | OK |
| **Nifty500 Symbol Mapping** | **1 file** | **—** | **10 encoding fixes, 56 renames, 25 mergers, 3 demergers, 27 delistings** | **UPDATED 2026-07-02** |
| **Angel Daily (gap fills)** | **20+1 files** | **~8 MB** | **49,457 rows (20 stocks, 2005-2026-07-02)** | **UPDATED 2026-07-02** |
| **Master Excel (Nifty500)** | **1 file** | **—** | **5,363 rows × 976 tickers (2005-2025)** | **User-provided** |
| **Delisted Excel (Nifty500)** | **1 file** | **—** | **1,321 rows × 148 tickers** | **User-provided** |
| **Ticker History Excel** | **1 file** | **—** | **21,040 rows, 42 monthly snapshots, 1,004 tickers (2005-2025)** | **User-provided** |
| **ATM Options (NIFTY)** | **84 files** | **~1.2 GB** | **MONTH 42/42 + WEEK 42/42** | **100% COMPLETE (artist-23 source)** |
| **Kaggle Indian Financials** | **8 parquets** | **8.2 MB** | **4,492 companies, QPL/YPL/BS/CF/Ratios/Shareholding** | **NEW 2026-07-02** |
| **NSE Quarterly Results** | **1 JSON** | **69.5 MB** | **76,507 filings, 2,357 symbols (2019-2026)** | **UPDATED 2026-07-03** |
| **PIT Earnings Dataset** | **9 parquets** | **8.5 MB** | **31,891 unified rows, 2,296 cos, 2005-2026; 86.2% exact dates** | **UPDATED 2026-07-03** |
| **Derived Datasets** | **8 parquets** | **10.4 MB** | **Corp actions (613), sector map (2,235), beat/miss (31,891), OI surface (377K+256K), shareholding (21,713)** | **NEW 2026-07-03** |
| **Angel Daily 2026 (bulk)** | **500 parquets** | **~5.3 MB** | **500/500 Nifty 500 Feb-Jul 2026 OHLCV (51,000 rows, 100%)** | **UPDATED 2026-07-04** |
| **Screener Deep** | **3 parquets** | **0.75 MB** | **14,022 rows (BS 5,022 + CF 3,000 + PL 6,000), 500 cos** | **COMPLETE 2026-07-03** |
| **India Stock Metadata** | **1 CSV** | **0.3 MB** | **All Indian listed companies** | **NEW 2026-07-02** |
| **TOTAL** | **~4,200+ files** | **~28.5 GB** | | **100% verified** |

**Nifty 500 Data Coverage (audited 2026-07-01):**
- Historical (2005-2025): 999/1000 real tickers = **99.9%** across HF+Master+Delisted+Angel
- Current Nifty 500 (Jul 2026): 500/500 = **100%** (Angel fills LTM, JSWDULUX, Feb-Jul 2026 gap)
- **ONLY 1 ticker truly missing: COXKINGS** (Cox & Kings, NCLT/fraud — purged from all exchanges)
- 8 NEW stocks recovered this session: GLS→GLAXO, ILFSENGG→IL&FSENGG, BHARATFIN(BSE), VISHAL(BSE), IISL(BSE), IL&FSTRANS, TRIL(BSE), TIFIN(BSE)
- HF daily data ends 2026-01-22. Angel daily data covers 20 stocks to 2026-07-02. Bulk Feb-Jul 2026 gap for remaining ~2,500 HF symbols still open.
- `datasets/nifty500_symbol_mapping.json` = comprehensive rename/merger/demerger/encoding mapping (56 renames)
- `datasets/angel_daily_missing/` = 20 stocks: ETERNAL, JSWDULUX, KESORAMIND, SADBHAV, NETWORK18, UNITDSPR, LTM, ARE&M, SWANCORP, HBLENGINE, IBULLSLTD, PIRAMALFIN, GLAXO, IL&FSENGG, BHARATFIN, VISHAL, IISL, ILANDFSTRANS, TRIL, TIFIN

**1-Minute Data Coverage (audited 2026-07-01):**
- Stock 1-min: 2,535 symbols, 713M rows, 2022-01→2026-01 (HF, 10.4 GB)
- Kaggle Index 1-min: **136 indices**, ~60M rows, 2015-01→2026-05 (3.0 GB) — ALL major Nifty sector/factor/broad indices
- Options Index Spot: NIFTY(477K rows), BANKNIFTY(476K), SENSEX(354K) — 2021→2026

**Options Data Coverage (audited 2026-07-02):**
- Index options: NIFTY 262 files (weekly), BANKNIFTY 61 files (**monthly only — no weekly**), SENSEX 144 files (weekly)
- Stock options: 2,319 files, 88 stocks, 187M rows
- **ATM MONTH: 42/42 files = 100% COMPLETE** (recovered from artist-23/nifty-options-data)
- **ATM WEEK: 42/42 files = 100% COMPLETE** (recovered from artist-23/nifty-options-data)
- Bhavcopy: 680 files, 136 instruments × 5 timeframes, 4.2 GB (2015→2026)

**Indian Earnings & Financials Data (new 2026-07-02):**
- Kaggle Financials (Screener-style): 8 parquets, 4,492 companies, 8.2 MB total
  - quarterly_profit_loss.parquet: 49,375 rows (Sales, Expenses, Operating Profit, Net Profit, EPS)
  - yearly_profit_loss.parquet: 49,401 rows
  - yearly_balance_sheet.parquet: 45,565 rows
  - yearly_cash_flow.parquet: 17,964 rows
  - ratios.parquet: 26,571 rows (PE, PB, ROE, ROCE, etc.)
  - quarterly_shareholding.parquet: 17,930 rows (promoter/FII/DII holdings)
  - yearly_shareholding.parquet: 18,414 rows
  - basic_info.parquet: 4,492 rows (sector, BSE/NSE codes, market cap, growth rates)
- NSE Quarterly Results: 76,503 filings from 2,357 symbols (2019-2026), 69.5 MB JSON
- MoneyControl Fundamentals: 991 companies (2019-2023), full P&L+BS in `label` column
- MiMIC Earnings Calls: 1,042 calls with transcripts + financials
- NSE Earnings Dates: 54,268 dates, 2,532 symbols

**Point-in-Time (PIT) Earnings Dataset (updated 2026-07-03):** `datasets/earnings_pit/`
- **unified_quarterly_pit.parquet: 31,891 rows, 2,296 companies, 16 cols — THE PRIMARY DATASET**
  - Merges Kaggle (pre-2023) + Screener.in (2023-2026), deduped, all with `available_date`
  - 86.2% exact dates (77% NSE broadCastDate + 9.3% board meeting dates) for 2019+; 2025: 95.3%, 2026: 98.0%
  - 100% Net Profit, 95% Sales, 100% PBT/Interest/Depreciation coverage
  - **Use this for all PEAD/earnings-momentum backtesting — no lookahead bias**
- quarterly_earnings_pit.parquet: 52,563 rows, 4,475 companies — Kaggle source QPL (includes non-listed cos)
- screener_quarterly_2023_2026.parquet: 6,270 rows, 500 Nifty 500 cos × ~13 quarters (2023→2026)
  - 61% exact NSE+BM dates, 39% +50d lag (2025-2026 now mostly covered via board meetings)
- mc_fundamentals_parsed.parquet: 3,968 rows, 991 companies, 146 cols — full BS+P&L structured
- yearly_profit_loss_pit.parquet: 50,749 rows, 4,491 companies (2004-2023)
- yearly_balance_sheet_pit.parquet: 50,924 rows, 4,491 companies (2004-2023)
- ratios_pit.parquet: 46,000 rows (ROE%, ROCE%, Debtor Days, Working Capital Days)
- quarterly_shareholding_pit.parquet: 47,322 rows (Promoter/FII/DII % with +25d lag)
- xbrl_quarterly_results.parquet: 581 rows (XBRL filings with actual Revenue/Profit/EPS)
- Total: 9 parquets, 8.5 MB

**Derived Datasets (new 2026-07-03):** `datasets/derived/`
- corporate_action_factors.parquet: 613 rows (282 bonuses, 281 splits, 50 dividends) with ex_date + adjustment_factor
- cumulative_adj_factors.parquet: 563 rows — cumulative split/bonus factor per symbol for price adjustment
- sector_industry_map.parquet: 2,235 symbols mapped to 80 Screener sectors (85.6% Nifty 500 covered)
- earnings_beat_miss.parquet: 31,891 rows — YoY/QoQ profit+sales growth, beat/miss flags, turnaround/deterioration
- nifty_oi_surface.parquet: 377,034 rows — NIFTY options OI by strike (DTE<=35), Jun 2021 → May 2026, 402 trading days
- banknifty_oi_surface.parquet: 256,187 rows — BANKNIFTY same
- nifty_oi_daily_summary.parquet: 1,276 rows — daily max pain, PCR (OI+vol), max CE/PE OI strikes
- shareholding_changes.parquet: 21,713 rows — QoQ/YoY FII/DII/Promoter/Public changes for 2,054 companies

**Angel Daily Bulk 2026:** `datasets/angel_daily_2026/`
- 500/500 Nifty 500 stocks × Feb-Jul 2026 daily OHLCV (100% coverage) — **23 stragglers retried + recovered 2026-07-04** (ABSLAMC, ANGELONE, ANTHEM, ANURAS, CAMS, DIXON, ENDURANCE, EXIDEIND, FSL, GVT&D, GODREJCP, HAL, LATENTVIEW, LLOYDSME, NLCINDIA, NETWEB, SUNTV, TATACAP, TATACHEM, TATAELXSI, TATAPOWER, TATASTEEL, ZENTEC); no AB1021 rate-limit hit on retry, all fetched first pass
- Consolidated: `datasets/angel_daily_n500_2026.parquet` (regenerated 2026-07-04: 500 symbols, 51,000 rows)
- Angel instrument list: `datasets/angel_instrument_list.json` (2,465 NSE EQ tokens)

**Screener Deep Scrape (COMPLETE):** `datasets/screener_deep/`
- screener_balance_sheet.parquet: 5,022 rows, 62 cols — 500 cos × ~10 metrics, Mar 2002→Mar 2026
- screener_cash_flow.parquet: 3,000 rows, 61 cols — 500 cos × 6 metrics (CFO/CFI/CFF)
- screener_annual_pl.parquet: 6,000 rows, 73 cols — 500 cos × 12 metrics (Sales→EPS), Mar 2002→Mar 2026+TTM
- All 500/500 Nifty 500 companies scraped, 0 errors

Known issues:
1. `datasets/india_fundamentals_mc/Train.parquet` `annual_report` column has snappy corruption AT SOURCE (HF). Workaround: read only `company_name`, `year`, `label` columns.
2. **HF TIMEZONE BUG (CRITICAL):** HF daily timestamps are `18:30 UTC` = midnight IST next day. `.date()` on raw UTC gives wrong date (1 day behind, shows weekends as trading days). **FIX:** `df['date'] = df['timestamp'].dt.tz_convert('Asia/Kolkata').dt.date`. Verified: 97% exact price match with Angel after IST conversion. Affects ALL HF daily+minute data.
3. **EARNINGS LOOKAHEAD BIAS:** Kaggle financials use quarter-end dates (NOT announcement dates). Fix: use `datasets/earnings_pit/quarterly_earnings_pit.parquet` which has `available_date` = when data was actually public. For pre-2019 data, conservative +50d lag is applied. For 2019+, exact NSE broadCastDate is joined.

## >>> TOMORROW'S TASKS (priority order) <<<
**#0 DONE (2026-07-01):** Full multi-dimensional data audit complete.
**#0.5 DONE (2026-07-03): Data improvement sprint:**
  - PIT earnings dates upgraded: 77% → 86.2% exact (board meetings filled 2,955 rows; 2025: 95.3%, 2026: 98.0%)
  - Corporate action adjustment factors: 613 actions (282 bonuses, 281 splits, 50 dividends) with ex_dates
  - Sector map: 2,235 symbols → 80 sectors (85.6% Nifty 500)
  - Earnings beat/miss: 31,891 rows with YoY/QoQ growth, turnaround flags
  - OI surface: NIFTY 377K + BANKNIFTY 256K rows (Jun 2021 → May 2026), daily max-pain + PCR
  - Screener deep: BS, CF, annual P&L for 500 Nifty 500 companies
  - Angel bulk 2026: 477/500 Nifty 500 stocks × Feb-Jul 2026 OHLCV (48,654 rows; 23 still rate-limited)
  - Shareholding changes: 21,713 rows with QoQ/YoY FII/DII/Promoter changes for 2,054 companies
  - Angel instrument list: 2,465 NSE EQ token map for future API calls
  - NSE API fully blocked by corporate proxy (403 on homepage) — FII/DII + broader index constituents deferred
**#0.6 STILL OPEN: NSE-blocked items** (need VPN/home network):
  - FII/DII daily flows (NSE API 403)
  - Nifty Total Market / MicroCap 250 constituents (NSE 404)
  - Missing 217 Nifty 500 symbols in NSE quarterly results (HDFCLIFE, SBILIFE, MCX, ABBOTINDIA etc. — not in `index=equities` filter; need different API parameter or direct fetch)
  - ~~Complete Angel bulk OHLCV (remaining 23 stocks)~~ DONE 2026-07-04: 23/23 recovered, 500/500 Nifty 500 now covered.
**#0.7 OPTIONAL: BANKNIFTY weekly options** — only 61 monthly files available.
**#1 Track 2 engine upgrades** (data dependencies now mostly met): sector map + fundamentals + beat/miss + OI ready.
  - Quality-momentum overlay using sector_industry_map + earnings_beat_miss
  - Sector-tilt to EARLY themes (FORWARD_WATCHLIST.md) + froth-exit overlay
  - Two-stage stop + regime-scaled leverage
**#2 Track 1 finish:** validate live 0DTE, fix LOT_SIZE 65 vs 75, 30-day Angel paper run.
**#3 Multi-strat PROOF:** combine swing-equity + options-short-vol daily P&L.
**#4 Track 3 (new alpha):** OI surface NOW READY → H1 dealer-gamma + max-pain signals.
**Build order overall:** Risk OS + audit-as-default FIRST → then signals (other2/OPERATING_STANDARD_2026.md).

## ORIGINAL PLAN (the root spec — don't lose it)
Track 1 = the original mandate: intraday Nifty 50 options strategy, ₹1Cr, Kelly×0.25, synthetic
BS pricing, WFO, full Sections 1-10 deliverables. STATUS: COMPLETE & audit-clean — lead =
delta-hedged 0DTE+DTE1 short straddle, OOS Sharpe ~2.6-3.6, REPORT.md + 8 charts + AUDIT.md +
EXECUTIVE_SUMMARY.md all in intraday_options_strategy\results\. Tracks 2 & 3 are the expansion.

## THREE TRACKS

### TRACK 1 — Intraday options (MATURE + real-fill validated) → `intraday_options_strategy\PLAN.md`
Validated, audit-clean. **REAL-FILL RESULT (2026-06 session):** 261 NIFTY expiries 2021-26
from HF options-1m dataset. Naked straddle: -2.3% CAGR (expected, fat tails). Delta-hedged
(real IV from market prices): +1.3% CAGR unfiltered — IMPROVES SHARPLY with IV filter.
**KEY FINDING: trade ONLY when morning straddle >=0.45% of spot** (Rs.112 at Nifty 25k).
  Unfiltered 259 trades: CAGR+1.3%  MaxDD 17.7%  WR 58%  avg/lot +332
  IV-filtered 160 trades: CAGR+5.9%  MaxDD  5.0%  WR 64%  avg/lot +914 ← DEPLOY THIS
  All 6 years (2021-2026) positive with filter. Real Sharpe ~1.0-1.2 (synthetic was 2.6, bias).
Live runner: run_today_live.py. CHECK straddle >= 0.45% spot BEFORE deploying.
Real-fill script: run_realfill_deltahedged.py (results saved in results/realfill_deltahedged_nifty.csv).
Open: validate live m more weeks, lot size 65vs75, 30-day paper run (ONLY on IV-filter days).

### TRACK 2 — Low-capital multi-strategy small-cap machine (≤₹10Cr) → `swing_momentum\PLAN.md` + `swing_momentum\GOD_TIER_EXPANSION.md`
The user's priority "small-capital 100%+ CAGR" edge. CORE = Minervini/CANSLIM/VCP
leadership swing, REGIME-GATED. **GOD-TIER EXPANSION adds 10 capacity-limited dimensions
(D1-D10): D1 special-situations/event-driven, D2 IPO ecosystem, D3 microcap quality-momentum,
D4 PEAD/earnings-drift, D5 thematic megatrend (defense/power/EMS/energy-transition),
D6 pairs/market-neutral, D7 seasonality/forced-flow, D8 convexity catalysts, D9 insider/
promoter following, D10 ADR-local/ETF arb — + futuristic (tokenized/24x7, AI-herding).**
Philosophy: capacity-as-moat + asymmetry + concentration + multi-strategy low-corr +
ride 2026-40 India structural tailwinds + perpetual edge-renewal. Honest: compounding
many capped-risk asymmetric edges, NOT leverage/magic. START: Phase 1.1 (point-in-time
universe), then build order in GOD_TIER_EXPANSION §SEQUENCING. 7 phases + 10 dimensions.
**FRONTIER LAYER → `swing_momentum\FRONTIER_DIMENSIONS_2026_2040.md`: D11-D14 (only 4 of
54 generated ideas survived adversarial filter): D11 SLB borrow-fee-spike carry [16/20,
the one genuinely fundable Kite-native capped-risk edge], D12 demerger phantom-stub gap,
D13 Nifty forced-exclusion sell (post-Dec-2025 index rule), D14 Closing-Auction-Session
dislocation [research-only, NSE CAS from Aug-2026]. NOTE D12+D13 are ONE correlated
demerger bet not two. 7 ideas CUT (folklore/no-short-leg/crash-beta) — documented §5.**

### TRACK 3 — New-dimension alpha research → `alpha_research\PLAN.md`
The "next 10-year alpha." Lead dimension = model PARTICIPANT STATE & FRAGILITY (forced
flows of dealers/retail/passive), not price/value. 7 falsifiable hypotheses (H1-H7),
ranked, each a sub-plan with a kill-criterion. START: H1 (dealer-gamma/OI fields) —
DATA-READY today from our bhavcopy OI (2021-26). Research loop: frame→cheap test→
adversarially verify→kill or promote; log every kill.

## TOMORROW'S RECOMMENDED ORDER (token-aware, do in priority)
1. **TRACK 2 Phase 1** (user's stated priority): inventory data, build point-in-time
   universe + adjusted daily prices → the foundation everything else needs. Mostly
   data we already have on disk.
2. **TRACK 3 H1** (highest-conviction new dimension, data-ready): reconstruct Nifty
   OI/gamma surface from existing bhavcopy → GEX & zero-gamma flip → event-study price
   behaviour around it. One cheap test that could open a whole new edge.
3. Then iterate the research loop / swing phases as tokens allow; save state each session.

## DISCIPLINE (both new tracks)
Survivorship-bias-free; no-lookahead (prefix tests); realistic costs+slippage+liquidity
caps; small grids; one-shot OOS; deflated Sharpe/PBO; capacity-test (≤₹10Cr is fine,
but KNOW where the edge decays); economic WHY before believing any backtest; log kills.
