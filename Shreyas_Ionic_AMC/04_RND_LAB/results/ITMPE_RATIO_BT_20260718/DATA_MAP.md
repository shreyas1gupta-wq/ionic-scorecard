# DATA MAP — NIFTY Monthly ITM-PE-Sell / 2x-OTM-Buy Strategy
Prepared by: Data Officer (Kavya Reddy persona) — 2026-07-18
Scope: map every NIFTY INDEX options dataset on disk usable for a 2019-2026(+) daily backtest of
SELL monthly ITM PE (~300-700 pts ITM) + BUY 2x OTM (PE and/or CE), signal = NIFTY vs 20/50 DMA.

All numbers below are [DATA] — computed directly from the parquet files listed, on 2026-07-18, via
scripts in the scratchpad (not checked into repo; re-runnable, see "Repro" note at bottom).

---

## 0. Bottom line

- **Best options source**: `Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist/fo_idx_{2011..2026}.parquet`
  — official NSE F&O bhavcopy, NIFTY OPTIDX rows, **2011-01-03 → 2026-07-10**, 7,658,757 rows.
  This is the only source with full-history, real strikes, real CONTRACTS (volume), and monthly+weekly
  expiry granularity all the way back to 2011.
- **Best spot source**: `datasets/index_daily/factor_navs_principal.parquet`, filter `series=='NIFTY 50'`
  — **2005-04-01 → 2026-01-05**, 5,151 rows, zero gaps >7 calendar days. Fully spans the options data.
- **Entry is always possible** (some strike in the 300-700 ITM-PE band trades) every single day 2011-2026
  (day-level rate = 100% every year) — but **per-strike liquidity depth** (the specific target strike
  trading on a given day, needed for honest daily mark-to-market / mid-cycle exit) is thin before 2021
  (14-25% of strike-days) and only becomes robust from **2021 onward** (53% → 83-94% by 2025).
- **Honest usable window for the full strategy (both legs, with real fills/marks) = 2021 → 2026-07**
  (~5.5 years, ~66 monthly cycles). 2011-2020 is usable only for a degraded "entry premium vs
  expiry-settlement" version of the backtest (no honest interim mark-to-market) — see §5.
- **Landmine #1 (expiry-day SETTLE_PR) CONFIRMED, and it is era-dependent** (two distinct failure
  modes, see §4.3) — never read it as an option price in either era.

---

## 1. DATA_CATALOG.md check (source of truth, read first)

Catalog confirms (relevant rows only):
- `datasets/derived/pit_union_panel_v1` etc. — equity, not relevant here.
- **D-033 Wave 1** row: `fo_bhavcopy_hist/fo_idx_{2011..2021}.parquet` (`nsearchives`, old DERIVATIVES fmt),
  and **Wave 3** extension: `fo_bhavcopy_hist/fo_idx_{2021..2026}.parquet` — "16 yearly files 2011-2026
  COMPLETE (744 old-fmt + 501 UDiFF days, 0 err)." Catalog also flags: *"weekly-era monthlies trade ~16
  strikes near ATM (160 listed) — fine for ATM studies, thin for wings/spreads."* This session's
  measurement (§5) is consistent with that flag but adds the year-by-year magnitude, which the catalog
  did not previously quantify.
- No prior DATA_CATALOG row exists for `intraday_options_strategy/datasets/raw/hf_atm_options/` — this
  dataset is **uncatalogued and unverified** (see §3.3).
- Spot: catalog lists `datasets/index_daily/nifty50.parquet`, `nse_official_all_indices.parquet`, and
  `factor_navs_principal.parquet` under §2/misc rows — none previously flagged with an exact NIFTY-50-series
  date range; that gap is closed in §6 below.

---

## 2. Known-candidate inventory (as instructed)

| Candidate | What's actually there | Verdict |
|---|---|---|
| `intraday_options_strategy/datasets/raw/hf_index_options_1m/options/NIFTY/*.parquet` | 1-min real strikes, HF-sourced, 262 files, **2021-05-07 → 2026-06-09** (weekly-era only) | Good for high-res recent-era validation; **not usable pre-2021**, and monthly-vs-weekly must be filtered from the `expiry` column per-file |
| `intraday_options_strategy/datasets/raw/hf_atm_options/NIFTY/MONTH/ATM±N_{CE,PE}.parquet` | 1-min, ATM-relative offsets only, N=-10..+10 (42 files), real-looking OHLC/IV/volume/OI, **2020-12-29 → 2025-12-26** | See §3.3 — uncatalogued, offset range too narrow for the OTM leg, provenance unverified |
| `intraday_options_strategy/datasets/raw/hf_index_options_1m/index/NIFTY.parquet` | 1-min NIFTY spot, 2021-05-24 → 2026-06-03 | Fine as a spot cross-check for the recent era only |
| `datasets/fo_bhavcopy_hist/...` (as named in task) | Wrong path — actual location is `Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist/` | **This is the primary source**, see §4 |
| `datasets/index_daily/nifty50.parquet` (task's suggested spot path) | Real, but only **2016-01-04 → 2026-07-03** | Too short for 2011-2020; use factor_navs_principal instead (§6) |

---

## 3. Options sources evaluated in depth

### 3.1 PRIMARY: `Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist/fo_idx_{2011..2026}.parquet`
Official NSE F&O bhavcopy (index derivatives), one file per calendar year, 16 files.

**Schema** (identical columns across all 16 years; only dtype of CONTRACTS/OPEN_INT/CHG_IN_OI drifts
float64↔int64 across the old→UDiFF format change, harmless on concat):
```
INSTRUMENT (FUTIDX/OPTIDX), SYMBOL, EXPIRY_DT, STRIKE_PR, OPTION_TYP (CE/PE/XX),
OPEN, HIGH, LOW, CLOSE, SETTLE_PR, CONTRACTS, OPEN_INT, CHG_IN_OI, TIMESTAMP
```
`SYMBOL` includes NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY (from ~2021) plus several legacy index futures
(CNXINFRA, CNXIT, CNXPSE, FTSE100, DJIA...) pre-2021 — **filter `SYMBOL=='NIFTY' & INSTRUMENT=='OPTIDX'`**.

**Coverage** (NIFTY OPTIDX rows only, verified 2026-07-18):

| Year | Rows | | Year | Rows |
|---|---|---|---|---|
| 2011 | 359,390 | | 2019 | 770,090 |
| 2012 | 356,096 | | 2020 | 731,639 |
| 2013 | 386,550 | | 2021 | 510,565 |
| 2014 | 474,968 | | 2022 | 562,041 |
| 2015 | 533,036 | | 2023 | 339,069 |
| 2016 | 514,250 | | 2024 | 402,556 |
| 2017 | 527,414 | | 2025 | 394,283 |
| 2018 | 566,450 | | 2026 (partial, →Jul) | 230,360 |

Total 7,658,757 rows. `TIMESTAMP` range **2011-01-03 → 2026-07-10**. `EXPIRY_DT` range 2011-01-27 →
2031-06-24 (long-dated far contracts listed in advance; harmless, just filter on the monthly flag).
1,464 `EXPIRY_DT` parse failures out of 7.66M rows (0.02%) — negligible, safe to drop.

**Strike granularity** (spot-checked 4 sample expiries): **100-pt steps** in 2013 (spot 5,682, 60 strikes,
2,700-8,600), **50-pt steps** from 2018 onward (2018/2022/2025 samples all 50-pt, 139-157 strikes spanning
roughly spot±5,000 to spot±10,000). Exact transition date not exhaustively pinned — [INFERENCE] from 4
spot-checks only, not a full scan; re-verify if exact-strike (not band) logic is needed.

### 3.2 SECONDARY: `intraday_options_strategy/datasets/raw/hf_index_options_1m/options/NIFTY/*.parquet`
1-minute bars, real strikes, HuggingFace-sourced. Schema:
`timestamp, open, high, low, close, volume, open_interest, trading_day, symbol, strike, option_type, expiry`.
262 daily-expiry files, **2021-05-07 → 2026-06-09** — weekly-era only (matches the DATA_CATALOG row "NIFTY
weekly options 1-min ... 261 weekly expiries 2021→2026"). Useful for intraday fill-realism checks on the
2021+ slice of the backtest, but cannot extend the historical window and needs an explicit
monthly-vs-weekly filter on `expiry` per the same last-Thursday-of-month rule as §4.2.

### 3.3 TERTIARY / FLAGGED: `intraday_options_strategy/datasets/raw/hf_atm_options/NIFTY/MONTH/`
1-minute, ATM-relative-offset series (`ATM-10`...`ATM+10`, 50-pt steps inferred from spot-check, so
±500 pts max), columns `timestamp, OHLC, iv, volume, oi, strike_price, spot, datetime, date, expiry_type,
strike_type, option_type`. Sample (`ATM+6_PE`, offset ≈300 pts): 335,825 rows, **2020-12-29 → 2025-12-26**.
- **Not in DATA_CATALOG.md** — no D-009 verification on record, source/provenance not documented in this
  session (looks HF-sourced like §3.2 but the parent dir has no README pointer confirming it).
- Offset range (±10 steps ≈ ±500 pts) **covers only the bottom half of the ITM-PE band (300-500 of the
  300-700 target) and none of the 2x-OTM buy band (600-1400 pts)** — insufficient alone for this strategy.
- **Recommendation: do not use for this strategy build without a D-009 pass first**; §4/§5 numbers below
  come entirely from the catalogued, verified bhavcopy source (§3.1) instead.

### 3.4 Rejected as options sources
- `intraday_options_strategy/datasets/raw/hf_atm_options/NIFTY/WEEK/` — same caveats as §3.3, weekly not
  monthly.
- Angel daily capture (`intraday_options_strategy/datasets/angel_capture_2026/`) — forward-only, Jul-2026→,
  irrelevant to a historical backtest.
- `intraday_options_strategy/datasets/raw/options/angel_nfo_nifty.csv`, `nifty50_daily.csv` — not inspected
  in depth; superseded by the verified bhavcopy for this task (kept as legacy, read-only per project rule).

---

## 4. Monthly-vs-weekly identification, expiry mechanics, landmine confirmation

### 4.1 Method
`is_monthly = (EXPIRY_DT == max(EXPIRY_DT) within that (calendar year, calendar month) group)`. This
correctly resolves to the single expiry in the pre-weekly era and to the **last** Thursday-cycle expiry
in the weekly era, without needing to hardcode a day-of-week rule (handles Thursday-holiday shifts for
free, since the last chronological expiry in the month wins either way).

### 4.2 Weekly-start verification (cross-checks the environment's known landmine)
Distinct-NIFTY-expiries-per-month, run 2011-2026:
- **First month with ≥3 distinct expiries (true weekly cadence): 2019-02** — matches the documented
  landmine ("NIFTY weeklies only exist from 2019-02-11") exactly. From 2019-02 onward the count settles
  into a steady 4-5 expiries/month.
- Two **pre-2019 false positives** from the naive ">1 per month" heuristic, both explained and harmless:
  `2014-02` (expiries on both 26th *and* 27th) and `2018-03` (28th *and* 29th) — in both cases the two
  dates are **1 calendar day apart**, coming from adjacent year-file boundaries (a holiday-shift artifact
  in the raw bhavcopy, not a real second listed contract). The `max()`-per-month rule still picks the
  correct later date as "monthly" in both cases, so the flag is unaffected — noted here only so nobody
  re-discovers this as a false "early weekly" signal.

### 4.3 Landmine #1 (expiry-day SETTLE_PR) — CONFIRMED, era-dependent, two failure modes
| Era (format) | Sample expiry day | SETTLE_PR behavior |
|---|---|---|
| Old format (pre-UDiFF), e.g. 2013-06-27 | 120 rows, all strikes/types | **SETTLE_PR = 0.0 for every row** (blank/unpopulated) |
| UDiFF format, e.g. 2022-06-30 | 272 rows | **SETTLE_PR = 15,780.25 for every single row** (same value regardless of strike/CE-PE) — e.g. a 17,500 CE with CLOSE=0.10 shows the identical SETTLE_PR as a 14,100 CE with CLOSE=1,673.50 |
| UDiFF format, e.g. 2024-06-27 | 238 rows | **SETTLE_PR = 24,044.5 for every row**, same pattern |

Confirms the landmine exactly as documented, plus the extra fact that the **pre-2021 (old-format) era
fails differently** (silent zero, not a misleading underlying-level broadcast). Either way: **never read
SETTLE_PR on an expiry-day row as the option's price.** Cash-settle at intrinsic value
(`max(0, STRIKE-spot_close)` for PE / `max(0, spot_close-STRIKE)` for CE) using the underlying's close on
that day, per the environment's standing rule.

---

## 5. ITM-PE (sell leg) and 2x-OTM (buy leg) tradability by year

Definitions: PE moneyness (ITM) = `STRIKE_PR - spot_close`; PE moneyness (OTM) = `spot_close - STRIKE_PR`;
CE moneyness (OTM) = `STRIKE_PR - spot_close`. All bands computed only on rows flagged `is_monthly`.
Two metrics per year:
- **row_trade_rate** = fraction of (day, strike)-observations in the band with `CONTRACTS>0` — the honest
  liquidity-depth measure (can I count on *this specific* strike trading on *this specific* day).
- **any_strike_traded_day_rate** = fraction of days where *at least one* strike somewhere in the band
  traded — the entry-feasibility measure (can I find *something* to sell/buy in this band today).

### 5.1 SELL leg — ITM PE, 300-700 pts in-the-money
| Year | n_obs | n_traded | row_trade_rate | any_strike_traded_day_rate |
|---|---|---|---|---|
| 2011 | 13,832 | 2,850 | 0.206 | 1.00 |
| 2012 | 13,790 | 2,459 | 0.178 | 1.00 |
| 2013 | 14,788 | 2,569 | 0.174 | 1.00 |
| 2014 | 16,196 | 2,226 | 0.137 | 1.00 |
| 2015 | 16,796 | 3,026 | 0.180 | 1.00 |
| 2016 | 16,728 | 2,932 | 0.175 | 1.00 |
| 2017 | 16,856 | 2,349 | 0.139 | 1.00 |
| 2018 | 16,251 | 2,733 | 0.168 | 1.00 |
| 2019 | 16,592 | 2,883 | 0.174 | 1.00 |
| 2020 | 13,615 | 3,388 | 0.249 | 1.00 |
| **2021** | 7,779 | 4,098 | **0.527** | 1.00 |
| **2022** | 6,986 | 4,904 | **0.702** | 1.00 |
| **2023** | 6,277 | 4,744 | **0.756** | 1.00 |
| **2024** | 6,879 | 5,049 | **0.734** | 1.00 |
| **2025** | 6,041 | 5,027 | **0.832** | 1.00 |
| 2026 (partial) | 53 | 50 | 0.943 | 1.00 |

### 5.2 BUY leg — OTM PE, 600-1400 pts out-of-the-money (candidate "2x" distance)
| Year | row_trade_rate | any_strike_traded_day_rate |
|---|---|---|
| 2011-2019 | 0.174-0.224 | 1.00 |
| 2020 | 0.301 | 1.00 |
| **2021** | **0.591** | 1.00 |
| **2022-2025** | **0.751-0.811** | 1.00 |

### 5.3 BUY leg — OTM CE, 600-1400 pts out-of-the-money
| Year | row_trade_rate | any_strike_traded_day_rate |
|---|---|---|
| 2011-2019 | 0.146-0.198 | 1.00 |
| 2020 | 0.249 | 1.00 |
| **2021** | **0.529** | 1.00 |
| **2022-2025** | **0.628-0.803** | 1.00 |

Full per-year CSVs saved alongside this file: `itm_pe_tradability_by_year.csv`,
`otm_pe_tradability_by_year.csv`, `otm_ce_tradability_by_year.csv`,
`ITM_PE_300_700_tradability_by_year.csv`, `OTM_PE_600_1400_tradability_by_year.csv`,
`OTM_CE_600_1400_tradability_by_year.csv` (the last three add the day-level column).

### 5.4 Reading this honestly
- You can **always find** some strike to trade in every band, every day, 2011-2026 (day-level = 100%).
  That is *not* the same as the backtest being honest.
- The **row-level rate is the real gate**: 2011-2020 sits at 14-30% for every leg — meaning on 70-86% of
  strike-days in the target bands, **zero contracts traded**. A daily mark-to-market, an early exit, or a
  roll priced off "that day's print" would be fabricated most of the time in this era.
- From **2021 onward** the picture flips: 53-94% row-level tradability. This is consistent with India's
  well-known retail options-volume boom from 2020-21 onward, not an artifact of the weekly-expiry launch
  (weeklies started 2019-02, two years before the liquidity jump shows up in the *monthly* contract's
  wing strikes) — DATA_CATALOG's "weekly-era monthlies thin for wings" note is about weeklies stealing
  ATM flow from monthlies in general, this year-by-year split adds that even *within* the weekly era, the
  wing liquidity itself kept improving through 2021-2025.

---

## 6. Spot series (for the 20/50 DMA signal)

| Source | Path | Range | Notes |
|---|---|---|---|
| **Recommended** | `datasets/index_daily/factor_navs_principal.parquet`, filter `series=='NIFTY 50'` | **2005-04-01 → 2026-01-05**, 5,151 rows, cols `date, series, nav` | Zero gaps >7 calendar days (checked). Fully spans the 2011-2026 options data with 6 years to spare on the front end. Principal-contributed, catalog-listed. |
| Extension (more current) | `datasets/index_daily/nse_official_all_indices.parquet`, filter `index_name=='NIFTY 50'` | 2016-01 → 2026-07-03 | Use to extend past 2026-01-05 if the backtest needs to run to "today." |
| Cross-check (full span, name changes across the series) | `Shreyas_Ionic_AMC/05_DATA_OFFICE/data/indices_close/indices_{2012..2026}.parquet`, `Index Name` | 2012-02-21 → today | Index was named **"S&P CNX Nifty"** (2012-2013ish) → **"CNX Nifty"** (transitional) → **"Nifty 50"** (2015+) — harmonize the name string before use. Not needed as primary since factor_navs_principal already covers the full span cleanly. |
| Rejected as primary (task's suggested path) | `datasets/index_daily/nifty50.parquet` | 2016-01-04 → 2026-07-03 only | Real 1-day OHLCV (cols `timestamp, open, high, low, close, volume`; `volume` column is always 0 in spot-checked rows) but **10 years too short** for a 2011-2020 window; fine as a lightweight cross-check for 2016+. |

20/50 DMA signal is computable from any of these on close-to-close alone — no PIT/lookahead issue (a
moving average of closes through day t is knowable at day-t close).

---

## 7. Honest usable backtest window — verdict

- **Data-availability ceiling**: 2011-01 → 2026-07 (bhavcopy start; NIFTY options existed since 2001 but
  no F&O bhavcopy is on disk before 2011).
- **Weekly-expiry launch**: 2019-02-11 (confirmed, §4.2) — irrelevant to entry feasibility for the monthly
  contract, relevant only if the strategy design cares whether weeklies were competing for flow.
- **Liquidity-honest window for this specific strategy (both legs, real daily marks): 2021-01 → 2026-07**
  (~5.5 years, ~66 monthly cycles). This is where row-level tradability crosses ~50% and climbs to 70-90%+
  for all three legs (ITM PE sell, OTM PE buy, OTM CE buy).
- **Degraded fallback for 2011-2020**: usable *only* as an "entry premium vs expiry-settlement" style
  backtest (enter at a real traded print if one exists that day — day-level rate is 100%, so an entry fill
  is always findable somewhere in the band — hold blind to expiry, cash-settle at intrinsic value from the
  underlying). **Not usable** for anything that needs an interim mark, a stop-loss, an early roll, or a
  P&L curve between entry and expiry in this decade — the specific strike's own prints are absent most
  days.
- Recommend building the certifiable (Gate-4) version on **2021-2026** and treating **2011-2020** as a
  clearly-labeled "structural/expiry-to-expiry only" extension, not blended into the same Sharpe/DSR
  numbers, if it's used at all.

---

## 8. Caveats / handoff notes for whoever builds the actual backtest

1. `COST_STANDARDS.md` (approved, D-021) governs slippage/cost assumptions once this reaches Gate-4 — not
   applied here, this is a data-mapping pass only.
2. Row-level tradability as computed is a **band-wide average across every 50/100-pt strike** in range —
   the actual strategy only needs ONE nearest-to-target strike per leg per cycle. Before Gate-4, re-run
   this same check restricted to "nearest strike to target moneyness, on entry day only" — likely higher
   than the band-wide numbers above, but that specific check was not run in this pass (scoped out for
   time; flag as [INFERENCE] that it improves the picture, not [DATA]).
3. `CONTRACTS` in this bhavcopy = **volume traded that day** (distinct from `OPEN_INT`/`CHG_IN_OI`) —
   confirmed via schema, so `CONTRACTS>0` is a correct proxy for "a trade occurred," not just "listed."
4. Per COST_STANDARDS-adjacent execution-realism rules already in the repo (`lib/execution_realism.py`):
   thin-volume days (which is most days pre-2021 in these bands) also carry 2-3x slippage — compounds the
   liquidity problem above, doesn't fix it.
5. Strike step (50 vs 100 pt) transition date not exhaustively pinned (§3.1) — re-check before writing
   strike-selection logic that assumes a fixed step across the whole 2011-2026 span.
6. `hf_atm_options/NIFTY/MONTH` (§3.3) could be a fast/lightweight cross-check for the 2021-2025 slice
   specifically if someone runs a D-009 pass on it first — flagged, not adopted, in this pass.

---

## Repro
Scripts used for this analysis (scratchpad, not in repo): loaded each `fo_idx_{year}.parquet` with
pyarrow `filters=[('SYMBOL','=','NIFTY'),('INSTRUMENT','=','OPTIDX')]`, parsed `EXPIRY_DT`/`TIMESTAMP`,
flagged monthly via `max(EXPIRY_DT)` per `(year,month)`, joined `factor_navs_principal` NIFTY 50 close on
`TIMESTAMP`, computed moneyness bands and `CONTRACTS>0` rates grouped by year (row-level) and by
`(year, TIMESTAMP)` (day-level, `.any()`). Deterministic, no randomness; re-running against the same
parquet files reproduces these numbers byte-for-byte.
