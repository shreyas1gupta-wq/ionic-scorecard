# SECTION 4 — DATA ESTATE & QUALITY REGIME

**Owner:** Kavya Reddy, Data Officer (05_DATA_OFFICE). **Governing rule:** *"If it's not in the DATA_CATALOG with path + range + bugs, it doesn't exist for research."* Every dataset the firm uses must have a catalog row, a verification status, and its known defects written next to it. This section inventories the full estate as of 2026-07-13, explains the verification gates that keep it honest, lists the standing capture jobs, and names every known hole with its fix plan.

**Key files:**
- `Shreyas_Ionic_AMC/05_DATA_OFFICE/DATA_CATALOG.md` — the single source of truth inventory
- `Shreyas_Ionic_AMC/05_DATA_OFFICE/DATA_QUALITY_RULES.md` — landmines + new-source protocol
- `Shreyas_Ionic_AMC/05_DATA_OFFICE/REMOTE_SOURCES.md` — fetch-on-demand registry + acquisition plans
- `Shreyas_Ionic_AMC/05_DATA_OFFICE/SCOUT_PRE2020_PIT_20260713.md` — pre-2020 PIT earnings scout report
- `Shreyas_Ionic_AMC/05_DATA_OFFICE/scripts/` — 27 puller/utility scripts (all resume-safe by design)
- `04_RND_LAB/lib/guards.py` — code-level guards that enforce the landmine rules inside backtests

---

## 4.1 Why the data office exists

The firm's entire research pipeline (idea → cheap test → backtest → forward test → paper) is only as honest as the data underneath it. The firm has been bitten repeatedly by data defects that produced *fake* backtest results — a 17-month option-data gap hiding behind healthy max-dates, a timezone bug that shifted every daily bar by one day, an expiry-day settlement field that silently recorded the *underlying's* level instead of the option price (−15,428 points of fake losses in one study). The response was institutional: a Data Officer role, a catalog-or-it-doesn't-exist rule, a mandatory verification gate for every new source (D-009), and a growing list of "landmines" that guard code (`guards.py`) enforces mechanically.

---

## 4.2 The India estate (core franchise data)

### 4.2.1 Equity prices — 26 years daily, 4+ years minute

| Dataset | Path | Granularity | Coverage | Status / notes |
|---|---|---|---|---|
| **PIT union panel v1.1 (CANONICAL)** | `datasets/derived/pit_union_panel_v1/close_panel_{price,return}_v11.parquet` | daily | 2005→2026; price basis 2,522 symbols, return basis 2,566 | THE equity close panels. Survivorship-complete: achievable NIFTY500 coverage 97–100% at every March snapshot 2014–2025 (2016/2024/2025 = 100.0%). Only 3 named residual gaps (SREINFRA — real NCLT discontinuity, quarantined; IISL — not a tradeable equity; UNKNOWN — data-entry artifact). v1 files frozen and md5-stable so audited runs stay reproducible; `_v11` is opt-in for all new work |
| pit_union_panel v1 (superseded) | same dir, `close_panel_{price,return}.parquet` | daily | 2005→2026; 2,511 / 2,556 symbols | Ground-truth-based (94.8% exact match vs official bhavcopy); 9 corrupt segments quarantined; use only to reproduce already-audited runs |
| **NSE bhavcopy daily (PERMANENT ground truth)** | `datasets/nse_bhavcopy_daily/close_all.parquet` | daily | 2013-01-01→2026-07-03; 5,569,110 rows, 3,716 symbols | Every NSE-listed stock's *official* close. Used as ground truth for splices and IPO dates (caught 14 bad membership-xlsx rows). Rule: any future "is symbol X in our data?" question ends here |
| Stock daily (HuggingFace) | `swing_momentum/data/hf_stock_minute/day/train-00000.parquet` | daily | → 2026-01-22 (**stale tail**) | Timezone landmine #1 applies; `asof()` after Jan-2026 returns stale prices; completeness degrades pre-2018 (see §4.6) |
| Stock 1-minute (HuggingFace) | `swing_momentum/data/hf_stock_minute/` | 1-min | 813M bars, 2022–2026 | Pre-open auction landmine #2 applies |
| Angel daily 2026 bulk | per RESUME_TOMORROW | daily | 477/500 names Feb–Jul-2026; 23 stragglers pending | Retry list held in RESUME_TOMORROW |
| Master wide matrix | `Nifty500_Master_Dataset_2005_2025.xlsx` (root, 33.7MB) | daily close-only | 5,363 days × ~1,200 tickers incl delisted | **RETURN basis** (dividend-adjusted) — never compare its levels to exchange prints |
| Delisted names | `Nifty500_Delisted_2005_2025.xlsx` (root) | daily | 239 names with histories | Feeds delisting-loss realization (V1→V2 of a momentum strategy halved CAGR once delisting losses were realized — a real lesson) |
| Raw delisted CSVs | `raw/nifty500/` | daily | 239 per-stock files, sampled windows | Union-panel input (count corrected 2026-07-04 from an earlier wrong figure of 1,905) |
| Legacy processed panel | `swing_momentum/processed/eq_close.parquet` + `membership.parquet` | daily | survivorship-safe panel behind MULTIBAGGER_STUDY | Read-only legacy; prime union-panel input |
| yfinance cache (Principal-contributed) | `stocks_data_cache.pkl` (root) | daily | 435 tickers 2020-06→2026-01, ADJUSTED, + shares outstanding + TTM fundamentals (378) + sectors | D-009 adjustment-verified on EICHERMOT/IRCTC ex-dates; source of TRUE market-cap weights for modern-era replication; useless pre-2018 |

**Universe membership (survivorship control):** `NIFTY500_TICKER_2005_2025_Final.xlsx` — 42 point-in-time snapshots 2005–2025 — is the ONLY permitted membership source (landmine #6). Supporting membership files: `NIFTY200_TICKER_2005_2025.xlsx` (monthly N200, 8,490 rows) and `Historical stock composition of Nifty 50 and Nifty Next 50.xlsx` (monthly, 2008→). Important as-of rule: N200/N500 PIT snapshots are **March/September**, not Jun/Dec.

### 4.2.2 Index & factor benchmarks

| Dataset | Path | Coverage | Verification |
|---|---|---|---|
| Official NSE all-indices (Angel-era) | `datasets/index_daily/nse_official_all_indices.parquet` | 246,597 rows, 174 indices, OHLC + P/E, P/B, div-yield, 2016-01→2026-07-03 | **D-009 triple-verified: 0.000% max diff vs factor_navs over all 1,365 overlap days.** Daily append via EOD task `ShreyasIonicAMC_IndexClose` |
| Factor NAVs (Principal-contributed) | `datasets/index_daily/factor_navs_principal.parquet` | 22 official NSE index NAV series daily 2005-04-01→2026-02-27 (5,189 days) — N200 Momentum 30 FULL, LowVol 30, Quality/Value/Alpha 30, N500 Mom 50/Value 50, etc. | D-009 verified 2026-07-04: LOWVOL30 2026-02-27 = 20495.0 exact match vs independent Angel series |
| NSE indices close (deep history) | `05_DATA_OFFICE/data/indices_close/indices_{yyyy}.parquet` | 3,535 days, 2011→today, all indices incl **India VIX OHLC** + P/E/P/B | Verified 2026-07-11: India VIX 2020-03-24 close 83.61 EXACT (record) |
| Sector/industry map | `datasets/derived/sector_industry_map.parquet` | ~976 symbols | **UNVERIFIED provenance** — Kavya to validate before any sector-tilt backtest quotes it |

### 4.2.3 Derivatives — 15 years of F&O daily + minute-level options

| Dataset | Path | Granularity | Coverage | Notes |
|---|---|---|---|---|
| Single-stock options, 210 F&O names | `intraday_options_strategy/datasets/raw/hf_index_options_1m/stocks_options/{SYM}/{expiry}.parquet` | **MIXED**: 1-min (HF) + daily (bhavcopy) | 2021-07→2026-06 **continuous** — the infamous Apr-2024→Aug-2025 gap was FILLED 2026-07-03; universe expanded 88→210 names (+122 new names 2024-07→2026-06 daily) | DUAL SCHEMA landmine (§4.5); untraded strikes carry 0.00 prices in daily files |
| NIFTY weekly options 1-min | same tree, index dirs | 1-min | 261 weekly expiries 2021→2026 | Accessor: `buying/chain.py` |
| NSE index-derivatives bhavcopy (15-year panel) | `05_DATA_OFFICE/data/fo_bhavcopy_hist/fo_idx_{2011..2026}.parquet` | daily | **2011-01→today COMPLETE** — 16 yearly files, 744 old-format + 501 UDiFF days, 0 errors | Weekly-era caveat: monthlies trade ~16 strikes near ATM (160 listed) — fine for ATM studies, thin for wings/spreads. Expiry-day SETTLE_PR landmine (§4.5 #9) |
| BSE F&O bhavcopy (SENSEX/BANKEX) | `05_DATA_OFFICE/data/bse_fo_bhavcopy/bse_fo_{2023..2026}.parquet` | daily | 2023-05→today, 622 days; 2026 alone: 92,087 SENSEX option rows / 34 expiries | Consumed same-day by the SX1 study |
| **Participant-wise OI** | `05_DATA_OFFICE/data/participant_oi/participant_oi_{2018..2026}.parquet` | daily | 2018-01→today; 2,101 days ok / 124 missing (holidays + unpublished) | FII/DII/Pro/Client positioning by instrument. Schema drift across years stored as raw strings — normalization map is a Kavya follow-up (`participant_oi_normalized.parquet` exists) |
| NIFTY + BANKNIFTY OI surface | `datasets/derived/nifty_oi_surface.parquet` (377,034 rows) + BANKNIFTY (256,187) + daily summary (1,276) | snapshots | **SPARSE**: NIFTY 402 distinct dates over 2021-06→2026-05 (~31% coverage, 3–16 day gaps); BANKNIFTY stale after 2024-07-04 | PARTIALLY READY for GEX work — no spot/IV/greeks columns; needs spot join + cadence fix before Track-3 gate |
| Live Angel forward capture | `intraday_options_strategy/datasets/angel_capture_2026/{day,minute}/{SYM}/{expiry}.parquet` | 1-day full contract life + 1-min front rolling | Jul-2026 → ongoing | ±10% strikes, 2 expiries; fed by the purge-defense task (§4.4) |

### 4.2.4 Fundamentals, earnings & ownership (PIT discipline mandatory)

Point-in-time (PIT) means: a backtest may only "know" a number on the date it became publicly available, never on the fiscal-period date. This is enforced dataset-by-dataset:

| Dataset | Path | Coverage | PIT status |
|---|---|---|---|
| **PIT quarterly earnings (THE join key)** | `datasets/earnings_pit/unified_quarterly_pit.parquet` | 86.2% exact `available_date` overall (2025: 95.3%, 2026: 98%) | PIT-safe from ~2021+. **Coverage landmine (2026-07-13):** rows with `available_date` are ~zero pre-2020 (2019: only 133) — see §4.5 #3 |
| **NSE quarterly-results announcements (second-precision)** | `nse_quarterly_results_pit.parquet` (imported 2026-07-13, Route 3B) | 2019-01→2026-07; 76,507 rows, ~2,300 symbols | `broadCastDate` to the SECOND (e.g. RELIANCE Q2FY20 = 18-Oct-2019 20:50:42, spot-check exact) + filing/dissemination times + XBRL links. Unlocks filing-TIME anomaly work and after-hours vs intraday PEAD classification. Pre-2019 still absent |
| Earnings calendar (historical) | `datasets/nse_earnings_dates/earnings_dates.csv` | 2020-01→2026-07 | Filter purpose = "Financial Results" |
| Forthcoming results | `datasets/nse_earnings_dates/forthcoming_results.csv` | rolling; refreshed via `nse_earnings_refresh.py` | NSE API, needs cookie warm-up |
| Board meetings cache | `datasets/nse_earnings_dates/board_meetings_all.json` | 78MB, 94,136 events | Candidate 2010-2018 PIT feeder — earliest-date audit pending (scout Phase 2) |
| Screener deep fundamentals | `datasets/screener_deep/` | BS 5,022 / CF 3,000 / PL 6,000 rows | **NO `available_date` column — naive use = lookahead.** Kavya to rule a stamping method before ANY signal use |
| Screener.in dump (Principal-contributed) | `datasets/screener_dump_20260704/` (347 companies extracted from a 984-file zip) | annual fundamentals Mar-2013→TTM, **including delisted names** (RELCAPITAL, ORIENTBANK…) | D-009 PASS (3/3 live samples) BUT **restated as-of-2026-07-04 → FORBIDDEN for event/earnings-reaction work; quality overlays only, minimum T+90 lag** |
| Beat/miss (SUE proxy) | `datasets/derived/earnings_beat_miss.parquet` | 31,891 rows | Revision-sleeve proxy |
| Shareholding changes | `datasets/derived/shareholding_changes.parquet` | 21,713 QoQ/YoY rows | FII/DII/promoter flow sleeve |
| Corporate actions | `datasets/derived/corporate_action_factors` | 613 events + cumulative adjustment factors | — |
| XBRL cache | `raw/xbrl_cache/` | 581 regulatory XMLs (~2019-2023) | Raw format, needs a parser; PIT cross-check candidate |
| Financial metadata | `raw/financial_metadata/` | 244 per-stock JSONs (~197 records each) | Schema audit pending |
| MC fundamentals | `india_fundamentals_mc/Train.parquet` | — | `annual_report` column corrupt at source — never read it (landmine #5) |

### 4.2.5 Commodities (ETF route), text & derived research sets

- **GOLDBEES daily** — `datasets/etf_gold_silver/goldbees_daily.parquet`, 1,357 rows 2021-01-10→2026-07-02. D-009 PASS 7/7 checks; split pre-adjusted; PIT-safe; UTC stamps (+5:30 for IST); Angel token 14428.
- **SILVERBEES daily** — 1,091 rows 2022-02-06→2026-07-02; D-009 PASS; token 8080.
- **India financial news** — `datasets/india_fin_news`, 125K docs tier-segregated (FinBERT target).
- **Earnings-call transcripts** — MiMIC set, 1,042 calls, prepared-remarks vs Q&A split, joins on `available_date`.
- **Multibagger winners** — `swing_momentum/multibaggers/winners_yearwise_50pct.csv` (1,677 rows, all ≥50% winner-years 2007-2025) + top-40/yr; SIG-12 validation set.
- **Strategy outputs (regenerable)** — IV/RV trades (3,468), FF calendar candidates (2,612), earnings-vol events (1,359), strangle shortlist (5,039), monthly portfolio — all under `intraday_options_strategy/buying/` with the generating script named in the catalog.
- **Reference/config** — Angel scrip master (`scrip_master.json`, 31MB, 153K instruments, refreshed daily by the capture task); Angel ETF token list.

---

## 4.3 The US / global estate (D-033 acquisition waves, 2026-07-11 → 07-13)

Built in three rapid waves plus follow-ups after D-033 (2026-07-11) authorized auto-fetch of reliable sources. Everything lives under `05_DATA_OFFICE/data/` and every entry was D-009 spot-verified against known values.

| Dataset | File(s) | Span | Source | Headline verification |
|---|---|---|---|---|
| SPX daily | `us_sp500_daily.parquet` | 1975→2026-07, n=12,988 | cdn.cboe.com | 2020-03-23 = 2237.40 exact; 2024-12-31 = 5881.63 exact |
| CBOE vol suite | `cboe_{vix,vix9d,vix3m,vix6m,vvix,skew}_daily.parquet` | VIX 1990→, VVIX 2006→, SKEW 1990→, term 2008-11→ | cdn.cboe.com | VIX 2020-03-16 = 82.69 exact |
| Fama-French 5 factors daily | `ff5_daily.parquet` | 1963-07→2026-05, n=15,833 | Ken French / Dartmouth | schema + span sane |
| FF momentum daily | `ff_mom_daily.parquet` | 1926-11→2026-05, n=26,152 | Ken French / Dartmouth | schema + span sane |
| Gold (XAUUSD) 1-min | `commodities_1m/XAUUSD_1m_{2009..2025}.parquet` | 2009→2025-12, ~5.9M rows | HF mirror of HistData MT4 | 2020-08 high 2075 OK. Caveats: **no 2026 file** despite dataset name; timezone is HistData EST, NOT IST |
| BTC/ETH 1-min | `crypto_1m/{BTCUSDT,ETHUSDT}_{yyyy}.parquet` | 2018-01→2026-06, 291MB / 18 files | data.binance.vision official dumps | BTC 2021-04 high 64,854 OK |
| **US stocks daily bulk** | `us_stocks_daily/train-*.parquet` (4 shards, 530MB) | 1962-01→2026-07-08; 25.8M rows, 7,693 tickers, adj_close present | HF paperswithbacktest | **LANDMINE: SURVIVORSHIP-BIASED** — see §4.5 #10 |
| US Treasury par yield curve | `us_treasury_yields_daily.parquet` | 2000-01→2026-07, n=6,634, 15 tenors | home.treasury.gov official | 2020-08-04 10Y = 0.52 exact (record low) |
| USDINR daily (FRED DEXINUS) | `usdinr_fred_daily.parquet` | 1973-01→today, 13,409 rows | fred.stlouisfed.org | Monotone, 0 dupes; within 0.6% of RBI ref — noon-NY basis, do NOT mix with RBI-ref series in one calculation |
| **S&P500 PIT constituents** | `sp500_constituents_pit.parquet` | 1996-01-02→2026-06, 2,712 change-rows | github fja05680/sp500 | TSLA Dec-2020 add exact; count 505 exact; Enron present as ENRNQ. Caveat: final/normalized tickers — map before joining prices |
| US daily 2023-09 vintage | `us_vintage_2023_09/` (277MB) | 1979-12→2023-09-08, 8.4M rows | HF chuyin0321 (no signup) | Only 1,500 symbols (S&P1500-class); recovers just 19/471 missing dead S&P names — minor cross-check layer only |

**Rejected/blocked routes (do not re-probe):** fabhaus US equities 5-min (~450GB — violates Principal size cap AND its remote APIs are broken); Stooq (JS anti-bot + office-IP ban — PoW solver exists, home-network job); FRED direct via proxy (connection reset — fredgraph.csv worked for USDINR); Yahoo (429); iShares ajax (HTML shell); histdata.com direct (JS token).

### Fetch-on-demand doctrine (REMOTE_SOURCES.md)

Principal directive 2026-07-11: *"if only api or url works we need not download it… save reference so that we can backtest without downloading all datas of very very large size."* The registry keeps live-tested URL patterns so backtests pull only the slice they need:

- **Verified working patterns:** CBOE index histories; Binance klines for ANY of ~2,000 pairs at any interval down to 1-second (never bulk-mirror beyond BTC/ETH 1m); NSE F&O bhavcopy (old format ≤2024-06, UDiFF after — the corrected UDiFF URL is documented after the old one 404'd); NSE equity bhavcopy; NSE participant OI; US Treasury; Ken French; HuggingFace file-resolve with HTTP Range (pyarrow can read parquet row-groups remotely without full download) and rows-slice API; HF dataset search for weekly discovery.
- **Standard access preamble** is documented (truststore inject, Mozilla UA, NSE cookie warm-up, HF bearer token).
- **Tested-and-dead list** prevents wasted re-probing; re-test only on network change.
- **Principal one-time unlocks queued:** (a) Kaggle API key, (b) Tiingo free signup, (c) click "agree" on gated HF paperswithbacktest pages (silver/copper daily), (d) home-network/VPN session for NSE /api endpoints (FII/DII, constituents) and Stooq.

### US survivorship acquisition plan (registered 2026-07-13, 4-scout sweep, all live-probed)

**Recipe: WIKI (pre-2018 deaths) + Tiingo (2018-26 deaths) + current dump (survivors). Entirely free; needs 2 free API keys from the Principal.**

1. **Quandl WIKI PRICES** (frozen 2018-03): 3,000+ US stocks incl then-delisted, EOD + dividends + splits 1962-2018. Route: Kaggle mirror (463MB, confirmed reachable, needs Kaggle key) or data.nasdaq.com WIKIP datatables API (live, needs free key).
2. **Tiingo free tier:** ticker master verified via proxy (107,460 rows) — 7,170 delisted US names with full ranges (AET 1977-2018, YHOO 1996-2017…). Free caps (500 unique symbols/month) fit our 471 missing S&P ever-members in ONE month. Known gap: 2008 bankruptcy shells (LEH, WAMUQ) absent — verify crisis names on first pull.
3. **Vintage dumps** as cross-checks only (tail-gap caveat: a dump carries a dead name only up to the dump date).
4. **Stooq** home-network job (office IP banned; PoW solver already written at scratchpad `stooq_full_probe.py`).
5. **Membership correction layers:** fja05680 (held), shardul0701 YAML wrapper 2004-2026, riazarbi iShares reconstruction (cross-check only).

### Russell 2000/3000 constituents (registered 2026-07-13, NOT fetched)

No free PIT dataset exists. Route A: Wayback-Machine iShares IWV/IWM holdings reconstruction (~half-day build, approximation). Route B (armed): snapshot current holdings NOW and append monthly — starts the clock. Route C: Norgate ~USD 30-40/mo, which would solve BOTH Russell membership AND the US survivorship problem at once, if a US program ever justifies paying. Decision: Route B armed; Route A deferred until a US strategy card actually needs it (D-033 gates on need).

---

## 4.4 Governance: gates, approvals, and standing capture jobs

### The D-009 verification gate (no new source enters unverified)

Every new dataset passes a 5-step protocol before research may touch it (DATA_QUALITY_RULES.md §New-source protocol):

1. **Propose** — source, URL/API, licence, cost, which edge it feeds.
2. **Sample approval** — Principal approves fetching a sample.
3. **Sample audit** — 100 rows: schema/dtypes/nulls/dupes/date-monotonicity/PIT-safety; **cross-check 5 values against an independent source** (this is the step that catches wrong data — e.g. VIX 2020-03-16 = 82.69, India VIX 2020-03-24 = 83.61, RELIANCE broadcast timestamp to the second).
4. **Verdict** USE/QUARANTINE + a draft catalog entry → go-live approval.
5. **Bulk ingest** only after that, with the update command documented in the catalog.

### D-033 standing approval (2026-07-11) — the accelerant

Auto-fetch of **RELIABLE** external sources (exchange archives, Stooq/FRED-class, official APIs) is now permitted without per-source Principal sign-off, **conditional on**: (a) D-009 sample verification before use, (b) a DATA_CATALOG entry, (c) resume-safe background jobs for big pulls. Sketchy/unverifiable sources still need explicit Principal approval. D-033 is what enabled ~20 datasets to land in three days (waves 1-3 + follow-ups) without governance debt — every wave row carries its verification evidence.

### Standing capture & refresh jobs

| Job | Schedule | What it protects |
|---|---|---|
| **`AngelDailyOptionCapture`** (script: `C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture\daily_capture.py`, kept outside the repo by design — credentials adjacency) | 15:45 / 20:00 / 23:00 IST daily, DESK-100 owns | **Angel purge defense:** Angel SmartAPI *deletes expired option contracts from its instrument master* — if a contract's data isn't captured before expiry, it is gone forever. Captures ±10% strikes, 2 expiries, day + minute bars into `angel_capture_2026/`; also refreshes the 31MB scrip master |
| `ShreyasIonicAMC_IndexClose` (EOD) | daily | Appends official NSE index closes to `nse_official_all_indices.parquet` |
| Freshness pings (99_OPS/EOD_ROUTINE.md) | daily | Critical sets pinged; stale > 2 sessions = flag in CURRENT_STATE. Rule: count PERIODS-PER-YEAR, not max(date) — the 17-month option gap hid behind a healthy max-date |
| `/factor-indices` skill (monthly, HOME NETWORK ONLY) | monthly | Official niftyindices.com factor closes (office proxy blocks this API) |

### The puller/utility scripts (`05_DATA_OFFICE/scripts/`, 27 files)

All acquisition scripts are **resume-safe** (per-year parquet checkpoints + done-date ledgers such as `done_dates.txt` / `done_months.txt`) so a token cut or network drop never loses a pull.

| Script | What it fetches / does |
|---|---|
| `pull_bhavcopy_full_archive.py` | Full NSE EQ bhavcopy archive 2013→today → the permanent `close_all.parquet` ground truth (370+ downloads proven through the proxy) |
| `bhavcopy_backfill.py` | Filled the Apr-2024→Aug-2025 single-stock option gap from NSE bhavcopy (daily parquets into `stocks_options/`) |
| `expanded_backfill.py` | Expanded the option universe 88→210 names (2 years daily, all expiries) |
| `fo_bhavcopy_backfill_2011_2021.py` / `fo_bhavcopy_extend_2021_2026.py` | The 15-year NSE index-derivatives daily panel (old DERIVATIVES format + UDiFF normalized) |
| `bse_fo_bhavcopy_backfill.py` | BSE F&O UDiFF 2023-05→today (SENSEX/BANKEX weeklies) |
| `participant_oi_backfill.py` | NSE participant-wise OI daily CSVs 2018→today |
| `indices_close_backfill.py` / `nse_indices_close_pull.py` | NSE ind_close_all daily CSVs 2011→today (all indices, India VIX OHLC, P/E-P/B) |
| `index_history_pull.py` | NSE index closes via Angel SmartAPI (proxy-proof route) |
| `nifty_indices_download.py` | Official niftyindices.com factor-index NAVs (Principal-contributed scraper, firm-adapted; home network) |
| `nse_earnings_refresh.py` | Refreshes the forthcoming-results calendar and merges into the earnings CSV |
| `import_nse_qr_pit.py` | Route 3B import: `quarterly_results_all.json` → the second-precision `nse_quarterly_results_pit.parquet` + board-meetings audit |
| `cboe_french_pull.py` | CBOE vol suite + Ken French factors |
| `treasury_yields_pull.py` | US Treasury par yield curve 2000-2026 |
| `usdinr_fred_pull.py` / `stooq_daily_pull.py` | USDINR from FRED (Stooq rejected — anti-bot) |
| `binance_crypto_1m.py` / `hf_xauusd_1m.py` | BTC/ETH 1-min (Binance official) / gold 1-min (HF HistData mirror) |
| `hf_us_stocks_daily.py` / `hf_us_vintage_2023_pull.py` / `sp500_constituents_pull.py` | US daily bulk (4 shards), 2023-09 vintage layer, S&P500 PIT membership |
| `to_md.py` | Token-saver: converts docx/xlsx/csv/parquet/pdf to lean Markdown digests |
| `execution_scanner.py` / `final_execution.py` / `conviction_scorer.py` / `backfill_blank_pe.py` | Execution-sheet builders (live Angel prices, conviction scoring, risk overlay) — arguably trading-desk tooling housed here; rehome candidate |

Catalog TODO acknowledged in the file itself: rehome the remaining scratchpad copies of the backfill scripts into the repo before scratchpad garbage-collection (partially done — the repo copies above exist).

---

## 4.5 The landmine registry (violating any = fake backtest)

These are hard-won, dated discoveries; each is enforced by rules and, where possible, code guards in `04_RND_LAB/lib/guards.py`. Numbered per DATA_QUALITY_RULES.md plus the two 2026-07-13 additions.

1. **HF timezone bug.** HuggingFace daily bars are stamped 18:30 UTC = *next-day* 00:00 IST. Every consumer must `dt.tz_convert('Asia/Kolkata').dt.date` or every bar is off by one day.
2. **Pre-open auction bug.** The 1-min "open" at 09:00 is the auction print; the real open is the first bar ≥ 09:15. Before the fix, ~94% of naive 2026 gap calculations were corrupted.
3. **PIT/earnings lookahead + the 2026-07-13 COVERAGE landmine.** Act only on `available_date`, never quarter-end. New discovery (P1-R card): unified_quarterly_pit rows *with* `available_date` are ~zero pre-2020 (2019: 133 rows; real coverage 2021+). TTM-YoY growth panels needing 8 quarters are effectively non-NaN only from ~2022 — **any "validated 2016-2024" claim on fundamentals-gated signals silently validated on 2022-2024 only.** New rule: check the event-date distribution against the claimed window BEFORE quoting a validate verdict. Unlock job queued: reconstruct pre-2020 dates as `quarter_end + 45d` (SEBI Rule 33 LODR deadline — conservative-late = PIT-safe) in a SEPARATE panel flagged `available_date_recon`, never overwriting exact dates.
4. **Option-data gap (FILLED, with residuals).** The 17-month gap is filled, but: backfilled files are DAILY not 1-min; untraded strikes carry 0.00 O/H/L (settlement still populated — filter volume>0); guard L6 now asserts *schema awareness*, not trade absence.
5. **Corrupt column.** `india_fundamentals_mc/Train.parquet` `annual_report` is corrupt at source — never read it.
6. **Survivorship (India).** Universe membership ONLY from the 42-snapshot PIT xlsx.
7. **Dual schema in `stocks_options/`.** HF 1-min files (tz-aware IST, open_interest column, 100k+ rows/file) vs bhavcopy daily files (naive 15:30 stamp, `settle` column, few-k rows/file). Consumers must branch on schema or use EOD-only accessors.
8. **Angel ONE_DAY candle stamping** (project CLAUDE.md #8): daily bars stamped 00:00 IST — a `fromdate` with an intraday time silently DROPS the first day's bar. Bit the firm 2026-07-10 (made 501 book legs look unfilled).
9. **Expiry-day SETTLE_PR** (project CLAUDE.md #9): F&O bhavcopy expiry-day option settle = the UNDERLYING's settlement level, not the option price (−15,428-pt fake losses, 2026-07-11). Cash-settle at intrinsic from the underlying. Related: far weekly expiries listed with model settles but CONTRACTS=0 — gate every leg on CONTRACTS>0 and fall back to the liquid expiry.
10. **US stocks daily = SURVIVORS ONLY (measured 2026-07-13).** 471/1,202 S&P500 ever-members (39%) have NO price history in the PWB dump — Enron/Lehman/WorldCom/YHOO/TWTR/SIVB all absent; only 2/7,693 tickers end pre-2025. Valid uses: current-universe screens, factor structure, regime/risk models, recent studies. **BANNED: long-horizon US stock-selection return claims** until delisted prices are sourced (§4.3 plan). A ticker-rename map would recover part — not built yet.

### Panel-level defect rules (from the D-029 benchmark build & forensics, 2026-07-04)

- **988 phantom calendar rows** in the union return panel (<100 non-null closes on a "trading day") — filter the calendar by minimum coverage before any daily-return computation.
- **Mid-quarter delisting NaN propagation** — require a valid price at rebalance AND fill AND period-end, or realize the delisting loss explicitly.
- **212 frozen/stale price runs** (bit-identical closes ≥20 sessions; worst: NKIND 2,949 days; JMFINANCIL pinned at Rs 0.14 for 44 sessions then jumping to Rs 31 = a fabricated >20,000% single-name return). **RULE: apply `datasets/derived/benchmarks_random/stale_mask.parquet` (0.90% of panel rows) in EVERY backtest on the union panels.** This trap fired exactly as pre-registered in smoke testing (a 72% p95 result) and was caught.
- **Pre-2018 depth rule:** the HF panel's completeness degrades backwards (N200 full-252d coverage: 2006 57.6% → 2018 83.5%), and the missing names are disproportionately later-delisted *losers* — so **pre-2018 ranking results on the HF panel are systematically OPTIMISTIC, not just noisy.** Early-era results must be re-run on the survivorship-complete union panel before certification. Post-2018 (90%+) is largely sound.
- **Price-basis verdicts (ground-truthed):** HF panel / Delisted xlsx / raw-nifty500 = PRICE basis (94.8% match vs bhavcopy); Master xlsx = RETURN basis. The earlier opposite hypothesis was inverted by ground truth — the lesson recorded: cross-source disagreement identifies *a* mismatch; only ground truth identifies *which* source is wrong.

---

## 4.6 Known holes and their fix plans (open items, prioritized as filed)

| # | Hole | Impact | Fix plan / status |
|---|---|---|---|
| 1 | **Pre-2020 PIT earnings dates absent** | Fundamentals-signal validation silently restricted to ~2022+ | SCOUT_PRE2020_PIT_20260713.md complete: Route 3B (NSE calendar, 2019+) imported; board_meetings_all.json earliest-date audit pending as a possible 2010-2018 feeder; else SEBI +45d reconstruction panel (`available_date_recon` flag). No free 2010-2018 exact-date source found — BSE 403, NSE XBRL timeout |
| 2 | **US survivorship** | US stock-selection backtests banned | Free 3-layer recipe registered (WIKI + Tiingo + survivors); blocked only on two free API keys from the Principal |
| 3 | **OI surface sparsity** | GEX/positioning research (Track-3) gated | Needs spot join + cadence fix; BANKNIFTY surface stale after 2024-07-04; the new `indices_close` + participant-OI panels partially substitute |
| 4 | Participant-OI schema drift | Cross-year analysis fragile | Raw strings kept per day; format-break normalization map = Kavya follow-up (normalized parquet started) |
| 5 | Screener sets lack `available_date` | Lookahead risk if misused | Stamping ruling pending (join unified_quarterly_pit or +6mo lag); dump usable for quality overlays at T+90 min lag only |
| 6 | HF daily stale tail (→2026-01-22) | asof() silently returns stale prices | Angel daily bulk covers Feb–Jul-2026 (477/500; 23 stragglers on a retry list) |
| 7 | sector_industry_map provenance unverified | Sector-tilt backtests can't quote it | Kavya validation queued |
| 8 | XBRL cache (581 XMLs) unparsed | PIT numbers cross-check unavailable | Parser needed; low priority per scout (format complexity). Note: Route 3B rows carry XBRL links — numbers not yet pulled |
| 9 | 23 Angel daily stragglers; XAUUSD missing 2026; silver/copper 1-min unfound | Minor coverage edges | Retry list; gated-HF unlock (Principal one click) gives silver/copper *daily* instantly |
| 10 | Russell membership | US small-cap work impossible | Route B (start the monthly snapshot clock) armed as ops candidate |
| 11 | NSE /api endpoints 403 at office (FII/DII flows, live constituents) | Flow-data freshness | Home-network/VPN session unlocks; participant-OI archive route already covers positioning history |

---

### Improvement opportunities

1. **Start the Russell Route-B clock NOW (near-zero cost, irreversible delay otherwise).** Every month without the iShares IWV/IWM holdings snapshot is a month of PIT membership lost forever. One tiny monthly cron writing a dated CSV; decision is already "armed" — it just needs scheduling.
2. **Close the two Principal one-time unlocks as a single 10-minute ask.** Kaggle key + Tiingo signup (+ the HF "agree" click) unblock the entire US-survivorship recipe and silver/copper daily. The plan is fully scouted; the only blocker is human. Batch the ask rather than dripping it.
3. **Build the `available_date_recon` panel (SEBI +45d) and the board-meetings earliest-date audit this week.** Landmine #3 currently invalidates any pre-2022 fundamentals validation claim; the fix is a queued 90-minute job (scout estimates it precisely). Highest research-unlock per hour of any open item.
4. **Automate freshness as code, not habit.** The freshness rules (periods-per-year, stale >2 sessions) live in prose. A single `data_health.py` run by EOD that walks the DATA_CATALOG, checks each critical path's periods-per-year against expectation, and writes a red/green table into CURRENT_STATE would have caught the 17-month gap and the HF stale tail mechanically. The catalog is nearly machine-readable already — consider a companion `catalog.yaml` so the checker and the human doc can't drift.
5. **Ticker-rename map for the US dump.** Cheap partial recovery of "missing" dead names that are really renames; also required anyway before joining `sp500_constituents_pit` (OTC-suffixed delisted tickers) to any price source. One reusable mapping table serves both.
6. **Participant-OI normalization completion.** `participant_oi_normalized.parquet` exists but the format-break map is unfinished; until then every consumer re-solves schema drift. Finish once, document the break dates in the catalog row.
7. **Rehome misplaced execution tooling.** `execution_scanner.py` / `final_execution.py` / `conviction_scorer.py` are trading-desk artifacts living in the data office scripts dir; move under 06_TRADING_DESK tooling (with the catalog's own TODO note resolved) so 05_DATA_OFFICE/scripts is purely acquisition/QA.
8. **Single-file backup risk on the crown jewels.** `close_all.parquet` (5.57M rows), the union panels, and `nse_quarterly_results_pit.parquet` are irreplaceable-effort assets living on OneDrive sync only; verify they're inside BACKUP_POLICY scope and add md5 manifests (v1 already proved the value of frozen-consumer md5s — extend the practice to v1.1 and the ground-truth file).
9. **OI-surface decision: fix or retire.** The catalog has flagged "needs spot join + cadence fix" since 2026-07-03 with BANKNIFTY stale for a year. Either schedule the fix (the new indices_close gives the spot join for free) or mark the surface QUARANTINED so no Track-3 card silently builds on 31%-coverage snapshots.
10. **Angel-purge defense monitoring.** The capture task is the only thing standing between the firm and permanent option-data loss; add an explicit EOD assertion ("today's capture wrote ≥N files for ≥M symbols") rather than relying on task-scheduler success, since a silent partial failure (login expiry, rate-limit storm) is the realistic failure mode.
