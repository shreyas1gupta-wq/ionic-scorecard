# ALPHA_RANKER PIT Panel — Schema (`rnd/panel/panel.parquet`)

One row per (month-end rebalance date, symbol). Built by `rnd/lib/build_panel.py`.

## Columns

| Column | Definition | PIT note |
|---|---|---|
| `date` | month-end rebalance date (last trading day of the month on the market's own calendar, from `_NSEI.parquet`) | — |
| `symbol` | NSE ticker | — |
| `sector` | `Industry` column from `data/universe/nifty_total_market_750.csv`, joined on symbol | static, CURRENT industry classification applied to all historical rows (not PIT-tracked reclassifications) |
| `mktcap_log` | `ln(shares_proxy * AdjClose(t))`, `shares_proxy = current_MarketCap(Rs) / current_Price(Rs)` from `screener_live/<SYM>.json top_ratios` | **[INFERENCE]**: shares_proxy is a CURRENT snapshot (screener has no historical market-cap series), assumed constant across 2021-2026; ignores splits/bonuses/buybacks/QIP. Time variation in this column comes ONLY from AdjClose(t), not from actual share-count changes. Cross-sectional rank at a given date is more trustworthy than the level's time trend. |
| `regime_trend` | `trend_regime` from `results/regime_timeline.parquet`, nearest-PRIOR label as of t | merge_asof backward, no future leak |
| `regime_vol` | `vol_regime` from regime_timeline, nearest-PRIOR as of t | merge_asof backward |
| `regime_leader` | `leading_factor` from regime_timeline, nearest-PRIOR as of t | merge_asof backward |
| `beta_252` | rolling CAPM beta: OLS slope of stock daily return on `_NSEI` (Nifty 50) daily return, trailing 252 trading days ending at t (min 126 valid paired obs) | uses only data <= t |
| `vol_21/63/126/252` | annualized realized vol (`std(daily ret, ddof=1) * sqrt(252)`) over the trailing window ending at t; requires >= 80% of the window populated, else NaN | uses only data <= t |
| `idio_vol_252` | annualized std of residuals from the trailing-252d FF6 regression (see below) | uses only data <= t |
| `ff_beta_MKT/SMB/HML/RMW/CMA/WML` | rolling OLS betas (with intercept), stock daily return regressed on the 6 FF6-proxy factor returns, trailing 252d (min 126 valid obs) | uses only data <= t |
| `fwd_ret_{1M,1Y,5Y}_raw` | `AdjClose(t+h)/AdjClose(t) - 1`, h = 21/252/1260 TRADING days on the master calendar | strictly t -> t+h; NaN if t+h exceeds available history (never extrapolated) |
| `fwd_ret_{1M,1Y,5Y}_excess` | `raw - market_fwd` (same h, `_NSEI`) | same horizon rule |
| `fwd_ret_{1M,1Y,5Y}_resid` | `raw - beta_252(t) * market_fwd` — beta is the value **known at t**, never re-estimated with the forward window | no lookahead: beta and forward return use disjoint information (beta from data<=t, forward return from t->t+h) |

## FF6 proxy construction (built once, `build_ff_factors()`)

No India-native FF6 was built from our own universe within this pass; **[INFERENCE] proxy via `factor_navs (1).xlsx`** (through the existing `src/lib/factor_bench.py` loader):

- `MKT` = NIFTY 500 daily return − HDFC Liquid Fund(G) daily return (cash/Rf proxy)
- `SMB` = NIFTY SMALLCAP 250 return − NIFTY 100 return (spec-literal: small minus large)
- `HML` = NIFTY 200 Value 30 return − NIFTY 500 return (excess-of-broad-market)
- `RMW` = NIFTY 200 Quality 30 return − NIFTY 500 return (excess-of-broad-market)
- `CMA` = NIFTY 100 Low Vol 30 return − NIFTY 500 return — **weakest proxy**: no true investment-based (conservative-vs-aggressive capex) India index exists; low-vol is used as a loose stand-in and should not be trusted as a true CMA exposure
- `WML` = NIFTY 200 Momentum 30 return − NIFTY 500 return (excess-of-broad-market)

HML/RMW/CMA/WML are built as **excess-of-broad-market** (smart-beta index minus NIFTY 500), not raw index returns, deliberately — this orthogonalizes market beta out of the multi-factor regression (RESEARCH_PROTOCOL.md §2 neutralization principle); regressing on raw smart-beta index levels alongside MKT would be highly collinear (all these indices carry ~0.8-0.9 beta to the broad market) and produce unstable betas.

`beta_252` (the standalone CAPM beta) uses `_NSEI` (Nifty 50) as "the market" per the task's explicit INPUTS instruction, which is a **different** market proxy than `ff_beta_MKT`'s NIFTY 500 basis — documented, not a bug. Expect `beta_252` and `ff_beta_MKT` to be highly correlated (both are market-beta estimates) but not identical.

## Data staleness caveats (checked — do not re-discover)

- **`factor_navs (1).xlsx` has HETEROGENEOUS per-series staleness, not one uniform cutoff.** Verified directly against the workbook: `NIFTY 100`, `NIFTY SMALLCAP 250`, `NIFTY 200 Value 30`, `NIFTY 200 Quality 30`, and `HDFC Liquid Fund(G)` all stop updating at **2026-01-05**, while `NIFTY 500`, `NIFTY 100 Low Vol 30`, and `NIFTY 200 Momentum 30` continue through **2026-02-27**. Consequence: `MKT` (needs NIFTY500 + Liquid Fund), `SMB` (Smallcap250 + Nifty100) and `HML`/`RMW` (Value30/Quality30 + Nifty500) all go NaN after **2026-01-05**, while `CMA` (LowVol30 + Nifty500) and `WML` (Momentum30 + Nifty500) stay valid through 2026-02-27. The build logs the true effective cutoff as `ff_last_valid` = the last date where ALL SIX factor columns are simultaneously non-NaN (currently **2026-01-05**), which is what actually gates the FF6 regression (a design row needs all 6 factors non-NaN) — this is earlier than `regime_timeline.parquet`'s 2026-02-27 cutoff, and materially earlier than the naive "factor_navs runs through 2026-02-27" assumption. Price data (`data/prices/*.parquet`) runs through 2026-07-16. For rebalance dates after `ff_last_valid`, the rolling FF6 betas/idio_vol have progressively fewer trailing observations feeding the 252-window regression (right-truncated at the last jointly-valid factor date) until they fall below the 126-obs minimum and go NaN — they are NOT frozen/forward-filled. Check the per-column non-null% in `FND_panel.md` for the exact row count affected.
- **`regime_timeline.parquet` also stops at `2026-02-27`.** `regime_trend/regime_vol/regime_leader` for rebalance dates after that ARE forward-carried (nearest-PRIOR merge_asof, per spec) — i.e. the same last-known regime label repeats for ~139 calendar days' worth of rebalances. This is PIT-safe (no future info) but stale; do not read it as a fresh regime read for the most recent months.

## Survivorship caveat

Universe = `data/universe/nifty_total_market_750.csv` (751 symbols), a **CURRENT** constituent list, not a PIT snapshot series (unlike the AMC-side `NIFTY500_TICKER_2005_2025_Final.xlsx` with 42 PIT snapshots, which this panel does NOT use). Stocks that were in the broad market 2021-2026 but have since been removed from the current 750 (delisted, merged, demoted below the cutoff) are absent from this panel entirely — a real survivorship bias. Newly-listed stocks ARE correctly handled (rows only emitted from each symbol's actual first trade date, gated by `file_min`/`file_max` in `process_symbol`), so look-ahead from including "stocks that will IPO later" is not present; the bias runs the other way (missing names that dropped OUT of today's universe).

## Horizons

Measured in TRADING days on the master calendar (from `_NSEI.parquet`): 1M=21, 1Y=252, 5Y=1260. **Verified: the master calendar has only 1234 trading days total (2021-07-16 -> 2026-07-16), 26 trading days SHORT of the 1260-day 5Y horizon even measured from the very first rebalance date.** Consequence: `fwd_ret_5Y_raw/excess/resid` are 100% NaN in this build (0% non-null, confirmed) — not "sparse", entirely empty. This is honest (no fabrication/extrapolation past the data's end), but any 5Y-horizon research on this panel must wait for either more price history to accumulate or an explicit backfill of pre-2021-07-16 prices before the column is usable at all.


---

## ADDENDUM — Long-history companion panel (`rnd/panel/panel_long.parquet`)

Built by `rnd/lib/build_panel_long.py`. Same row grain (month-end rebalance date x
symbol) and same core columns as `panel.parquet` above, PLUS three added
diagnostic columns. Exists specifically so 1Y and 5Y horizons have REAL
(non-100%-NaN) forward returns — the short panel's master calendar
(2021-07-16 -> 2026-07-16, 1234 trading days) is 26 trading days short of the
1260-day 5Y horizon even from its first rebalance date, so `fwd_ret_5Y_*` is
100% NaN there. See `rnd/reports/FND_panel_long.md` for the confirmed
non-null 5Y % in this build.

### Price source (different from the short panel)

`Nifty500_Master_Dataset_2005_2025.xlsx` at the repo root — a daily Date x
~1199-ticker-column price panel, 2005-01-03 -> 2025-12-05. NOT
`ALPHA_RANKER/data/prices/*.parquet` (which only starts 2021-07-16).

### De-duplication (verified, logged to `rnd/panel/panel_long_dedup_log.csv`)

109 base tickers had >1 raw column (pandas auto-suffixed duplicates as
`.1`/`.2`/`.3` on load — up to 4 total columns for one ticker, e.g.
`AEGISCHEM`/`AEGISCHEM.1`/`AEGISCHEM.2`/`AEGISCHEM.3`). Each fragment covers a
short, NON-overlapping window (typically ~60-90 calendar days, clustered in
Q1 of 2005/2010/2015/2020 — consistent with the file being assembled from
periodic universe-snapshot re-exports rather than one continuous pull). Per
task spec, the SINGLE fragment with the most non-null observations was kept
per ticker; all others dropped (223 extra columns dropped total). Full detail
(every raw column, kept/dropped, coverage dates) in the dedup log CSV.

**Caveat the dedup does NOT fix**: for all 109 of these tickers, even the
*best* kept fragment only covers ~61-81 trading days total (median 80) — a
single quarter, not real multi-year history. These are near-universally
delisted/merged/bankrupt names (e.g. `ALBK`/`ANDHRABANK`/`CORPBANK`/`DENABANK`
— all merged into other PSU banks 2019-2020; `BHUSANSTL`, `ALOKTEXT` —
insolvency-resolution delistings). De-duplication removed the *technical*
duplicate-column problem; it did not and cannot manufacture history the
source file never captured for these names. Treat any panel_long row for
these 109 tickers as a single-quarter snapshot, not a time series.
Separately, ~61 further (non-fragmented, single-column) tickers also have
<300 non-null observations total — the same source-sparsity pattern, just
without the duplicate-column symptom. Full per-column non-null counts were
inspected before build; see `rnd/reports/FND_panel_long.md` for the summary.

### Split/bonus/data-error discontinuity guard (logged to `rnd/panel/panel_long_discontinuity_log.csv`)

Corporate-action adjustment in this file is UNCONFIRMED (per task brief).
Every ticker's daily return (post-dedup, on the master calendar) is checked
for `|1-day return| > 40%`. Flagged days are:
1. Logged verbatim (symbol, date, return, price before/after) — nothing
   silently dropped.
2. Excluded (set NaN) from the trailing-window INPUTS to `beta_252`,
   `vol_21/63/126/252`, `ff_beta_*`, `idio_vol_252` only — this is the same
   "don't let one bad tick blow up a rolling stat" guard philosophy as the
   rest of the codebase (`lib/guards.py`), applied here because we cannot
   confirm whether a >40% one-day move is a real adjusted return, an
   unconfirmed-adjustment artifact, or a data error, and a single such tick
   inside a 21-252-day OLS/std window can dominate it.
3. **NOT used to alter price LEVELS or forward returns** — `fwd_ret_*_raw`
   always uses the actual `AdjClose(t+h)/AdjClose(t)` from this file, exactly
   as documented, never adjusted or interpolated. Instead, three added
   columns record — per row, per horizon — how many flagged discontinuity
   events fall strictly inside that row's forward window:
   `disc_event_in_window_1M/1Y/5Y` (integer count, 0 if none, NaN if the
   horizon itself is NaN because t+h exceeds history). **Use these to filter**
   before trusting any 1Y/5Y forward-return statistic on a name that had a
   flagged event in its window — this panel deliberately does NOT pre-filter
   for you (a genuine, real, unflagged 1-day 40%+ move — e.g. a fraud
   discovery or a delisting-adjacent circuit stack — is legitimate data and
   silently dropping ALL >40% moves would be its own lookahead-adjacent bias
   toward smoother-looking history).

### Master calendar & market series (both DIFFER from the short panel — see build_panel_long.py module docstring for full verification detail)

- **Calendar**: this file's own Date column includes 189 market-holiday rows
  in its 2005-04-01..2025-12-05 span with only 1-3 stray non-null cells
  (verified, e.g. 2005-01-26 Republic Day has exactly 1 non-null ticker out
  of 1199) — using them as-is would corrupt every ticker's return on those
  rows. The master calendar used here instead is `factor_navs (1).xlsx`'s
  "NIFTY 500" NAV index (a verified clean trading calendar), intersected to
  this file's price range. Consequence: coverage effectively starts
  2005-04-01 (factor_navs' inception), not 2005-01-03 — a ~3-month loss,
  documented, not fabricated.
- **Market series**: this file has NO Nifty/Nifty500 column of its own
  (verified: zero column names match "NIFTY" case-insensitively). Per task
  instruction, `factor_navs (1).xlsx` "NIFTY 500" is used as THE market for
  BOTH `beta_252` AND forward excess/resid returns (unlike the short panel,
  which splits Nifty 50 for `beta_252` vs Nifty 500 for `ff_beta_MKT`).

### FF6 betas

Identical proxy construction and identical heterogeneous-staleness caveat as
the short panel (reused via `build_panel.build_ff_factors`) — see above. No
"early years uncovered" issue in practice: factor_navs starts 2005-04-01,
essentially the same start as this panel's own calendar.

### mktcap_log & sector

Reused as-is from `build_panel.py` (`load_mktcap_shares_proxy`,
`nifty_total_market_750.csv` sector join) — both are CURRENT-snapshot
sources (screener_live current market cap; current 750-constituent industry
classification), so both are NaN for any ticker not in the CURRENT universe
(delisted/renamed/merged names). See `rnd/reports/FND_panel_long.md` for the
exact hit-rate. `MASTER_fundamentals_pit.parquet` (long-format PIT
fundamentals) was checked for a shares-outstanding series that could give a
true historical (non-current-snapshot) market cap — it has none (only
"equity capital"/"preference capital" among cap-adjacent metrics, not shares
count) — so no improvement over the short panel's [INFERENCE] proxy was
possible here; documented, not silently skipped.

### Survivorship (the point of this panel)

Universe = ALL 976 tickers found in the master price file (post-
dedup), not the current-750 list. This DELIBERATELY includes names that have
since left the index (delisted, merged, bankrupt) — see the 109-fragment
caveat above for how much real history most of them actually contribute.
Newly-listed names are correctly gated by their own `[file_min, file_max]`
listing-life window (no fabricated pre-IPO rows). Net effect vs `panel.parquet`:
LESS survivorship bias on paper (delisted names are present), but a large
fraction of that "extra" coverage is only a single-quarter snapshot per the
caveat above — real, honest, but not as large a fix as the raw ticker count
suggests. `sector`/`mktcap_log` for these delisted names is NaN (current-
snapshot sources don't cover them) — a `symbol`-only fallback for research
that doesn't need sector/mktcap.

### Horizons

Same 21/252/1260 trading-day definitions, measured on THIS panel's own
5131-day calendar (2005-04-01 ->
2025-12-05) — long enough that fwd_ret_5Y is no longer
structurally 100% NaN. Exact non-null % confirmed in
`rnd/reports/FND_panel_long.md`.


---

## ADDENDUM 2 — Survivorship-free PIT panel (`rnd/panel/panel_pit.parquet`)

Built by `rnd/lib/build_panel_pit.py` (T5 remediation, LOOKAHEAD_T1T10.md,
2026-07-17). Same schema/row-grain as `panel_long.parquet`, filtered:

- Universe at each rebalance date t = membership from the NEAREST-PRIOR
  snapshot in `NIFTY500_TICKER_2005_2025_Final.xlsx` (42 semi-annual
  snapshots, 2005-03-31 -> 2025-09-30),
  backward merge_asof (no future snapshot ever used).
- Intersected with price availability: since panel_long rows only exist where
  a symbol already has a priced observation at t, this filter can only REMOVE
  rows, never add rows for un-priced names.
- 0 panel_long symbols have no exact match in the PIT ticker
  list and are dropped at every date (cannot be PIT-verified): []
- Net effect: 148297 panel_long rows -> 99415 panel_pit rows
  (67.0% kept). This is the FIRST panel in this codebase
  where the cross-section at a 2005-2015 date does not include names that
  only entered the CURRENT universe list years later, and correctly OMITS
  names not yet/no-longer index members at that date -- the direct fix for
  the T5_universe FAIL in `rnd/reports/LOOKAHEAD_T1T10.md`.
