# AG7 — Factor-benchmark loader, Oversight-Cascade scaffold, Master-dataset schema

Owner: quant-strategist session, 2026-07-16. Pilot: HDFCBANK, ASIANPAINT, NESTLEIND,
TATASTEEL, HINDALCO, MARUTI, TCS, INFY, GRAVITA, SHAKTIPUMP.

## 1. What was built

| File | Purpose |
|---|---|
| `src/lib/factor_bench.py` | Loader/unit-of-truth for `factor_navs (1).xlsx`. Tidy NAV levels + daily returns, `trailing_return()`, `relative_strength()`, `trend_state()` — all `asof`-gated, no lookahead. |
| `src/cascade/oversight_cascade.py` | Scaffold for `03_OVERSIGHT_CASCADE.md`: GLOBAL / NATIONAL / SECTOR / STOCK(passthrough) layers, each returns a `[-15,+15]`-point adjustment + written rationale, tagged `[DATA]` / `[INFERENCE/approx]` / `[PLACEHOLDER]`. Not a gate — additive score-point shift only, per spec. |
| `results/pilot_cascade_adjustments.csv` | Per-pilot-symbol global/national/sector/net adjustments + full rationale strings, asof 2026-02-27 (latest factor_navs date). |

Both scripts run standalone (`python factor_bench.py`, `python oversight_cascade.py`) and were verified end-to-end — see run output below.

## 2. `factor_navs (1).xlsx` — confirmed schema

Sheet1, 5189 rows (after dedup) x 22 series, `NAV Date` 2005-04-01 → 2026-02-27, daily.
Columns: NIFTY 50/100/250/500, Midcap 150, Smallcap 100/250, Multicap 50:25:25, Low Vol 30,
Quality 30, Value 30, Momentum 30, Alpha 30, Value 50 (500-univ.), Midcap Momentum 50,
Smallcap Quality Momentum 100, High Beta 50, GOLDBEES, HDFC Liquid Fund(G) (cash proxy),
Top 20 equal weight, BSE Midcap 150 Momentum 30 (last two have later inception, legitimate
NaN before start — not a defect).

## 3. `Nifty500_Master_Dataset_2005_2025.xlsx` — actual contents [DATA, verified by direct inspection]

**It is a single-field (price-level) daily panel, not a multi-sheet fundamental/sector dataset.**

- One sheet, one header row: `Date` + **1199 ticker columns** (NSE symbols), 5363 rows,
  2005-01-03 → 2025-12-05.
- Each column is a price level per date (spot-checked HDFCBANK/ASIANPAINT/etc. — values
  and ranges are consistent with historical close prices; the workbook does **not** label
  the field explicitly, so "adjusted vs. unadjusted for corp actions" is
  **[INFERENCE — unconfirmed, verify against a known split/bonus date before relying on it
  for return calcs across corporate actions]**.
- No sector, no fundamentals, no fields beyond price. It does **not** contain what its name
  implies ("Master Dataset") in the sense of a multi-factor panel — it is a **price-only
  panel**, comparable in kind to `factor_navs` but at single-stock granularity instead of
  index/factor granularity.
- Coverage is dense and correct for mainboard/pilot names: HDFCBANK, ASIANPAINT, NESTLEIND,
  TATASTEEL, HINDALCO, MARUTI, TCS, INFY all show 5167/5363 non-null rows spanning the full
  2005-2025 window (matches expected trading-day count net of holidays). GRAVITA correctly
  starts 2010-11-16 (its actual listing date) — no fabricated pre-listing history.
  **SHAKTIPUMP is absent from this panel** (not one of the 1199 columns) — gap noted.
- **Data-quality flag [INFERENCE — needs Data Officer verification, D-009]:** 109 of the
  1199 ticker labels appear **twice** as separate columns (e.g. `8KMILES`, `ABGSHIP`,
  `CADILAHC`, `CAIRN`, `CROMPGREAV`...). Spot-checked `8KMILES`: the two columns cover
  **non-overlapping short windows** (2015-01-01→2015-03-31 and 2020-01-06→2020-03-30, ~3
  months each) — i.e., these are NOT simple duplicate columns with the same data; they look
  like fragments from what may be two different pulls/merges, and the surrounding gaps mean
  the "duplicate" tickers likely have **sparse, non-continuous coverage**, unlike the dense
  pilot names above. Do not treat every column in this file as full-history without
  per-ticker density checks — this needs a proper D-009 pass before any non-pilot name is
  used from it.

### Does it supersede any piecemeal source?

- **Yes, for long-horizon stock price history.** Our `ALPHA_RANKER/data/prices/*.parquet`
  pulls (yfinance) only cover ~2 years (2024-07 → 2026-07). The Master dataset gives **21
  years of daily prices** for the 9 pilot names it contains — directly usable for 1Y/5Y-lens
  trailing-return, drawdown, and regime-conditioning work once corporate-action adjustment
  is confirmed. This is a material upgrade over the pilot yfinance data for anything beyond
  1M horizon.
- **No, for sector/fundamental data.** It carries no sector, financials, or forensic fields
  — `datasets/india_stock_metadata/india.csv` (name/ticker/market/sector) remains the only
  sector source, and screener.in (still blocked on Principal login per PROGRESS.md) remains
  the only path to fundamentals. The Master dataset does not unblock Phase 1.3-1.5.
  It also does not supersede `factor_navs` (index/factor level, not single-stock).
- **Universe caveat:** 1199 tickers is broader than "NIFTY 500" in the literal sense
  (includes delisted/renamed names via the 109 duplicate labels) — it should NOT be read as
  a clean point-in-time NIFTY-500 constituent list; continue using
  `NIFTY500_TICKER_2005_2025_Final.xlsx` for PIT universe membership per CLAUDE.md landmine #6.

## 4. Oversight cascade — design choices & what's approximated

Per `03_OVERSIGHT_CASCADE.md`, four layers, additive score-point shift (not a gate):

- **GLOBAL** `[INFERENCE/approx]`: true inputs (US10Y, DXY, Fed, VIX, crude, PMI,
  shipping, geopolitics) are not yet in `05_DATA_OFFICE` (PROGRESS.md blocker). Proxied
  from what `factor_navs` has: GOLDBEES trailing return (flight-to-gold headwind tell) and
  High-Beta-50 vs Low-Vol-30 RS (domestic risk-on/off tell). Both real series, but a partial
  substitute for the spec's full global-risk axis.
- **NATIONAL** `[DATA]+[INFERENCE/approx-breadth]`: NIFTY 500 trend state (price vs
  SMA50/SMA200) is a **direct** read; breadth is approximated as the fraction of the panel's
  11 cap/style indices with positive trailing return (stand-in for true advance/decline
  breadth, which needs constituent-level data we don't have). No credit/rate/FII-DII axis
  yet (blocked, same as Global).
- **SECTOR** `[INFERENCE/approx]`: no true sector index or full-constituent basket exists
  in-house yet. Approximated as an equal-weight composite of the **pilot's own** constituents
  sharing an `india.csv` sector, RS'd vs NIFTY 500. With only 10 pilot names, 5 of 7 sectors
  present are **singletons** (n_peers=1: Finance, Process industries, Consumer non-durables,
  Consumer durables, Producer manufacturing) — for those, the "sector" signal is really just
  the stock's own trailing return vs NIFTY 500, tagged accordingly in the rationale string.
  Only Non-energy minerals (TATASTEEL/HINDALCO/GRAVITA, n=3) and Technology services
  (TCS/INFY, n=2) have >1 peer. This will sharpen materially once full sector baskets exist.
- **STOCK** `[PLACEHOLDER]`: 0-point passthrough — `02_SCORING_ENGINE`'s bottom-up composite
  isn't built yet, so there's nothing for the cascade to shift. This layer exists only so the
  net-adjustment arithmetic is well-formed for when 02 lands.

`net_adj` = simple sum of the three active layers, per pilot symbol, asof 2026-02-27
(latest date in `factor_navs`):

| ticker | sector | n_peers | global | national | sector | net |
|---|---|---|---|---|---|---|
| HDFCBANK | Finance | 1 | -5.2 | +1.1 | -8.7 | -12.8 |
| ASIANPAINT | Process industries | 1 | -5.2 | +1.1 | -14.1 | -18.2 |
| NESTLEIND | Consumer non-durables | 1 | -5.2 | +1.1 | +6.2 | +2.1 |
| TATASTEEL | Non-energy minerals | 3 | -5.2 | +1.1 | +12.3 | +8.2 |
| HINDALCO | Non-energy minerals | 3 | -5.2 | +1.1 | +12.3 | +8.2 |
| MARUTI | Consumer durables | 1 | -5.2 | +1.1 | -3.4 | -7.5 |
| TCS | Technology services | 2 | -5.2 | +1.1 | -12.3 | -16.4 |
| INFY | Technology services | 2 | -5.2 | +1.1 | -12.3 | -16.4 |
| GRAVITA | Non-energy minerals | 3 | -5.2 | +1.1 | +12.3 | +8.2 |
| SHAKTIPUMP | Producer manufacturing | 1 | -5.2 | +1.1 | -15.0 | -19.1 |

Directionally coherent with PROGRESS.md's prior 1M factor read ("IT weakest, quality-momentum
strongest" — IT (TCS/INFY) is the worst cascade net here too; metals/minerals names are the
strongest). Full rationale strings (with every number's tag) are in the CSV, not repeated here.

## 5. Verification

Both scripts were executed directly (not just reviewed) via the project's Python
(`pythoncore-3.14-64`), against the real files — no fabricated output:
- `factor_bench.py`: loaded (5189, 22), printed NIFTY500 trend + HighBeta50/LowVol30 RS +
  GOLDBEES trailing return, all non-NaN.
- `oversight_cascade.py`: wrote `results/pilot_cascade_adjustments.csv` (10 rows x 13 cols),
  printed the table above to stdout.

## 6. Open items / next steps

- Confirm Master-dataset price-adjustment methodology (split/bonus handling) before using it
  for any return calc that spans a known corporate action — flag to Data Officer for D-009.
- Run the 109 duplicate-ticker check across all of them (only `8KMILES` was spot-checked) to
  scope how much of the 1199-column panel is fragmented vs. continuous.
- GLOBAL/NATIONAL layers need real macro pulls (FRED/Stooq, D-033-eligible) to replace the
  factor_navs-only proxies — currently the two layers share the same proxy limitation.
- SECTOR layer needs full NIFTY-500 sector baskets (beyond the 10-name pilot) to stop being
  self-referential for singleton sectors.
- STOCK layer activates once `02_SCORING_ENGINE.md`'s bottom-up composite exists.
