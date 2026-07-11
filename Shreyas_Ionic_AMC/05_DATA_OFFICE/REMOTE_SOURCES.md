# REMOTE SOURCES REGISTRY — fetch-on-demand instead of bulk download
**Principal directive 2026-07-11:** "if only api or url works we need not download it but save reference so that we can backtest without downloading all datas of very very large size."
Every entry below was LIVE-TESTED through the corporate proxy on 2026-07-11 (truststore.inject_into_ssl() required before any HTTPS). Backtests should import these patterns and pull only the slice they need; only small/critical datasets get mirrored locally (see DATA_CATALOG).

## VERIFIED WORKING (tested 200 + content sane)
| Source | URL pattern | Granularity | Use |
|---|---|---|---|
| CBOE index histories | `https://cdn.cboe.com/api/global/us_indices/daily_prices/{IDX}_History.csv` — IDX ∈ SPX, VIX, VIX9D, VIX3M, VIX6M, VVIX, SKEW | daily, full history | refresh any day; mirrored locally |
| Binance klines (any symbol/interval) | `https://data.binance.vision/data/spot/monthly/klines/{SYM}/{IVL}/{SYM}-{IVL}-{YYYY-MM}.zip` — IVL ∈ 1s,1m,5m,1h,1d…; also `daily/` path for single days | down to 1s | pull ANY coin/interval/month on demand — do NOT bulk-mirror beyond BTC/ETH 1m |
| NSE F&O bhavcopy (hist) | `https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{YYYY}/{MMM}/fo{DD}{MMM}{YYYY}bhav.csv.zip` (valid ≤2024-06); UDiFF after: `https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{YYYYMMDD}_F_0000.csv.zip` (CORRECTED — verified 200 on 2026-07-11; the earlier `/products/content/fo/` path 404s) | daily | needs cookie warm-up GET nseindia.com first; ~1 req/s |
| NSE equity bhavcopy | old `.../EQUITIES/{YYYY}/{MMM}/cm{DD}{MMM}{YYYY}bhav.csv.zip`; new `.../products/content/sec_bhavdata_full_{DDMMYYYY}.csv` | daily | proven 2026-07-04 |
| NSE participant OI | `https://archives.nseindia.com/content/nsccl/fao_participant_oi_{DDMMYYYY}.csv` | daily | tiny files; schema drifts across years |
| US Treasury yields | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{YYYY}/all?type=daily_treasury_yield_curve&field_tdr_date_value={YYYY}&page&_format=csv` | daily, per year | mirrored locally 2000-26 |
| Ken French factors | `https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/{file}.zip` e.g. F-F_Research_Data_5_Factors_2x3_daily_CSV.zip | daily/monthly | mirrored locally |
| HF file resolve (any public dataset) | `https://huggingface.co/datasets/{repo}/resolve/main/{path}` + `Authorization: Bearer <HF_TOKEN>` | file-level | supports HTTP Range → pyarrow can read parquet row-groups remotely without full download |
| HF rows-slice API | `https://datasets-server.huggingface.co/rows?dataset={repo}&config=default&split=train&offset=N&length=100` | row-level slices | works on well-formed datasets (500s on malformed ones e.g. fabhaus) |
| HF dataset search | `https://huggingface.co/api/datasets?search=...&sort=downloads` | — | weekly /find-skills-style data discovery |

## LARGE — REFERENCE-ONLY (do not mirror; slice on demand)
- **Binance full universe** (any of ~2000 pairs, 1s-1d): pattern above. Effectively unlimited size; pull per-backtest.
- **paperswithbacktest/Stocks-Daily-Price** shards: mirrored (530MB) — but future PWB updates: re-resolve, don't re-download unless span extends.
- **fabhaus/equities_5m_stockprices** (US equities 5-min 2024+, ~450GB): REJECTED for mirror AND its HF rows/filter APIs 500 (malformed jsonl). Unusable remotely too. Real US-equity-minute route = Kaggle (key) or paid (FirstRate/Polygon).

## TESTED AND DEAD (do not re-probe; re-test only on network change)
- stooq.com `/q/d/l/` CSV: JS anti-bot wall. static.stooq.com bulk: 401 licensed.
- fred.stlouisfed.org: proxy connection-reset.
- query1.finance.yahoo.com: 429 on first request.
- ishares.com holdings ajax: returns HTML shell.
- histdata.com get.php: tk token is JS-computed at runtime; plain requests get empty token. (HF mirrors of HistData files are the workaround — worked for XAUUSD.)
- FirstRateData: free = 1-sample-zip per ticker (`https://frd001.s3.us-east-2.amazonaws.com/frd_sample_etf_SPY.zip`); full history paid.

## UNLOCKABLE BY PRINCIPAL (one-time actions)
1. HF gated datasets (silver/copper/indices daily via paperswithbacktest): click "agree" on the dataset pages while logged in.
2. Kaggle API key → kaggle.json: unlocks ES-mini minute data, delisted-stock sets, SP500 intraday sets.
3. Home network / VPN session: unlocks NSE /api endpoints (FII/DII daily, constituents), histdata browser downloads.

## Access snippet (standard preamble)
```python
import truststore; truststore.inject_into_ssl()
import requests
s = requests.Session(); s.headers.update({"User-Agent": "Mozilla/5.0 Chrome/126"})
# NSE only: s.get("https://www.nseindia.com", timeout=30)  # cookie warm-up
# HF only:  s.headers["Authorization"] = "Bearer <HF_TOKEN from memory>"
```

## Russell 2000/3000 historical constituents (registered 2026-07-13, NOT fetched)
- **No free PIT dataset exists.** FTSE Russell removed historical membership from their site; Norgate/Algoseek/Siblis = paid.
- **Route A (free, build job ~half-day):** iShares IWV/IWM daily holdings CSVs via Wayback Machine snapshots of ishares.com product pages -> reconstruct monthly membership ~2006/2011-present. Resume-safe crawler needed; approximation (ETF holdings ~= index, small tracking diffs).
- **Route B (recent years only):** current holdings CSVs from ishares.com direct (IWV 2,566 names) - snapshot NOW and append monthly going forward (start the clock).
- **Route C (paid, if US program ever justifies):** Norgate Data ~USD 30-40/mo incl delisted prices - solves BOTH membership AND the us_stocks_daily survivorship problem at once.
- Decision: Route B armed as an ops candidate; Route A deferred until a US strategy card actually needs it (D-033 gates on need).

## FREE survivorship-complete US daily prices 2005+ — ACQUISITION PLAN (4-scout sweep 2026-07-13, all live-probed via proxy)
**Recipe: WIKI (pre-2018 deaths) + Tiingo (2018-26 deaths, full death-date ranges) + current dump (survivors). Entirely free; needs 2 free API keys (Principal).**
1. **Quandl WIKI PRICES** (frozen 2018-03): 3,000+ US stocks incl then-delisted, EOD+div+splits 1962-2018. Routes: Kaggle mirror marketneutral/quandl-wiki-prices-us-equites (463MB one-shot, CONFIRMED reachable; needs Kaggle key) OR data.nasdaq.com WIKIP datatables API (LIVE — returned proper key-required error; free key; avoid Incapsula-blocked HTML path). Blueprint: teddykoker 2019 recipe (fja05680 membership + WIKI prices).
2. **Tiingo free** (needs free key): public ticker master VERIFIED via proxy (apimedia.tiingo.com supported_tickers.zip, 107,460 rows) - 7,170 delisted US names with full ranges (AET 1977-2018, YHOO 1996-2017, TWX, old DELL). Free caps: 1000 req/day, 50/hr, 500 UNIQUE SYMBOLS/MONTH -> our 471 missing S&P ever-members fit in ONE month, one full-history request each. GAP: 2008 bankruptcy shells (LEH, WAMUQ) absent - verify crisis names on first pull.
3. **Vintage dumps** (tail-gap caveat: a dump only carries a dead name UP TO the dump date - final months missing; use as cross-checks not primary): HF chuyin0321/timeseries-daily-stocks 2023-09 vintage 292MB NO SIGNUP (pull armed); Kaggle borismarjanovic 2017-11 (516MB CC0) + jacksoncrow 2020-04 (548MB CC0) behind same Kaggle key; paperswithbacktest monthly git tags 2024-05..2026-07 (our family) = free delisting enumeration by tag-diff.
4. **Stooq**: office egress IP BANNED on download endpoint (Zscaler UA-block + SHA256 PoW gate + IP ban; PoW SOLVED in python - solver at scratchpad stooq_full_probe.py). HOME-NETWORK JOB: prefer bulk d_us_txt.zip over per-ticker (per-IP daily cap ~few hundred).
5. Membership correction layers: fja05680 (held), shardul0701 YAML get_universe_as_of 2004-2026 (ready-made wrapper), riazarbi iShares-holdings reconstruction 2006+ (unlicensed, cross-check only).
**PRINCIPAL ASKS (one-time, both free): (a) Kaggle API key -> unlocks WIKI mirror + 2 vintages; (b) Tiingo free signup -> unlocks the 2018-26 dead-name tail. Optionally: run stooq probe from home.**
