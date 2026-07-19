# 09 — Data Layer (sources, scrapers, contracts)

Priority order (brief Q4/Q5/Q12/Q14): **public scrape / free API first → HuggingFace → yfinance → screener.in premium (login) → Bloomberg terminal dump (semi-annual, LAST resort).** Never assume; verify every new source with the firm's **D-009 sample check** (spot-check known values, no lookahead, sane schema) and add a `DATA_CATALOG` entry. Respect firm environment (Python path, `PYTHONIOENCODING=utf-8`, `truststore.inject_into_ssl()`, corporate proxy = sequential `requests.Session()` only, ~0.7MB/s; NSE needs cookie warm-up).

## Source map (what each feeds)
| Source | Access | Feeds | Notes |
|---|---|---|---|
| **yfinance** (`.NS`) | free API | OHLCV, splits/div, basic financials/ratios | Verify India tickers; some fundamentals sparse/stale — cross-check. |
| **NSE archives** | scrape (cookie warm-up) | bhavcopy, **delivery %**, bulk/block deals, **insider (PIT/SAST)**, corp announcements, board meetings, results calendar, index constituents | `nsearchives.nseindia.com` + corp-board/event APIs work at office; FII/DII & some `/api` need home/VPN. |
| **BSE** | scrape | announcements, shareholding, **XBRL financials**, corp actions | XBRL = structured financials fallback. |
| **screener.in premium** | login session (Principal logs in) | full financials, quarterly, ratios, **shareholding trend**, **concall transcript links**, peer comps, documents/annual reports | Respect ToS + rate-limit; cache aggressively; store raw HTML/JSON to disk. |
| **Company websites / IR** | direct fetch | annual reports (PDF→md), **investor presentations**, **concall transcripts**, press releases | Primary source for forensics & concall rubric; `markitdown` PDFs before reading. |
| **moneycontrol / trendlyne / tickertape** | scrape | **estimate revisions**, analyst recs, concall summaries, results calendar | Estimates thin for small/microcap — flag coverage gaps. |
| **HuggingFace** | token (in memory `reference_hf_token`) | India equity datasets, earnings-PIT, fundamentals | Use `hf_chunked.py` (80MB segments) through proxy. Firm already has `datasets/earnings_pit/`. |
| **Macro: RBI / MOSPI / FRED / Stooq** | API/scrape | repo, liquidity, CPI/IIP/GDP, credit growth, G-sec, INR; global: US10Y, DXY, crude, **gold/silver**, S&P, VIX | Powers `03` cascade + regime classifier. Stooq/FRED = D-033 reliable-source auto-fetch OK. |
| **Bloomberg terminal** | manual dump (semi-annual) | see §Bloomberg below | LAST resort; only fields not reliably scrapable. |

## Bloomberg — exact screens to dump (only if scraping fails; semi-annual)
Request these precise exports so the terminal session is efficient:
- **`BEst` / `EEO`** — consensus estimates + **estimate-revision history** (EPS/Rev/EBITDA, fwd 1–2y) → the 1Y revision engine where moneycontrol/trendlyne coverage is thin.
- **`ANR`** — analyst recommendations & target-price dispersion.
- **`ERN`** — earnings history, surprise (beat/miss) track record.
- **`FA`** — financial analysis export (10y standardized financials, ratios) → forensic module cross-check vs screener.
- **`DRSK` / `CRPR`** — Bloomberg default-risk + credit ratings → forensic/leverage.
- **`HDS` / holders** — institutional ownership & changes.
- **`RV` / comps** — relative-valuation peer sheets (sector-consistent multiples).
- **`SPLC`** — supply-chain map (customer/supplier concentration for moat & microcap).
- **`SI`** — short interest (where available).
- **`ECFC` / `ECST`** — economic forecasts (macro cascade inputs).
- **`GP` / `GPO`** — clean adjusted price history if yfinance India quality is doubted.
Export format: Excel/CSV per universe slice. **Excel dump is the absolute last resort** (brief Q5) — prefer live scrape; dump only the fields above that scraping can't reliably deliver.

## Data contracts (the schema the execution session must define & freeze)
Define one Parquet/JSON schema per entity, PIT-stamped, and log in this file's appendix:
- `prices` — ticker, date, o/h/l/c, volume, delivery_qty, delivery_pct, adj_close, source, tz-safe IST date.
- `fundamentals_quarterly` / `_annual` — PIT with **`available_date`** (when the market could know it — NEVER period-end; firm landmine 3).
- `estimates` — ticker, date, horizon, metric, consensus, n_analysts, revision_delta.
- `shareholding` — promoter/FII/DII/public %, pledge %, quarter, available_date.
- `corp_actions` / `announcements` / `insider_deals` — dated events.
- `concalls` — ticker, quarter, transcript_path, guidance_items[], parsed by the concall agent.
- `macro` / `regime_state` — dated macro series + the classified regime tuple.
- `forensic` — ticker, as_of, flags[], scores.

## Hard data landmines (from firm CLAUDE.md — enforce in every loader)
1. HF daily timestamps 18:30 UTC → convert `tz_convert('Asia/Kolkata').dt.date`.
2. Pre-open auction: use bars ≥09:15, not 09:00.
3. Earnings lookahead: PIT with `available_date` only.
4. Options dual-schema (HF 1-min vs bhavcopy daily `settle`); use `lib/guards.py`.
5. `india_fundamentals_mc/Train.parquet` `annual_report` col corrupt — skip it.
6. Survivorship: universe from `NIFTY500_TICKER_2005_2025_Final.xlsx` PIT snapshots (extend to 750).
7. Circuit/volume no-fill; slippage 2–3× on thin days (`lib/execution_realism.py`).
8. Angel `getCandleData` ONE_DAY stamped 00:00 — `fromdate = date-1 00:00`.
9. F&O bhavcopy expiry-day option SETTLE_PR = underlying settlement, not option price; gate on CONTRACTS>0.

## D-009 gate (every new source, before use)
Spot-check ≥5 known values against an independent source, confirm no lookahead in `available_date`, confirm schema sanity per `05_DATA_OFFICE/DATA_QUALITY_RULES.md`, write a `DATA_CATALOG` entry. Big pulls run as **resume-safe background jobs**.

## Appendix — frozen schemas

### `prices` (FROZEN — Phase 0, yfinance path verified)
- Storage: `data/prices/<TICKER>.parquet`, one file per ticker, DatetimeIndex ascending.
- Columns: `Open, High, Low, Close, Adj Close, Volume` (yfinance `auto_adjust=False`).
- Source: yfinance `<TICKER>.NS`, `interval=1d`. Benchmark: `_NSEI.parquet` (^NSEI).
- Verified via `src/lib/pilot_validate.py`: OHLC integrity, no NaN/neg/dup, monotonic, ≤4-day gaps.
- **Caveat:** prices are forward of the assistant's knowledge cutoff → no external price-verification possible here; Principal or NSE-bhavcopy cross-check required for a true D-009 value spot-check. Ticker-mapping caveat: corporate actions (demergers) can invalidate a symbol (TATAMOTORS.NS 404'd) — maintain a symbol-remap table.

### `fundamentals_quarterly` / `_annual` — PENDING (screener login)
### `estimates`, `shareholding`, `corp_actions`, `concalls`, `macro`, `forensic` — PENDING
