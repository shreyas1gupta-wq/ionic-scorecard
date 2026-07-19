# EARN_MOM_SWEEP — long-only earnings-momentum sweep (30 combos)
Owner: DESK-100. Date 2026-07-16. **This is a cheap-test SCREEN, not a certifiable backtest** —
single PIT window, so walk-forward / DSR / PBO / era-split are NOT claimable (PIT exact dates are
dense 2020-2023, thin 2024-2026; price panel ends 2026-01-22). Goal: rank 30 long-only variants by
robust per-trade edge **net of a calendar-matched random-entry placebo**, flag artifacts, surface
the 1-3 survivors worth a real Gate-4 build.

## HARD RULES (this firm has been burned by every one of these)
- **PIT only.** Signal knowable at `available_date`. Entry = **D0+1 close** where D0 = first trading
  day ≥ `available_date`. NEVER use `quarter_end` as the action date. Assert with
  `lib/guards.assert_pit` and `assert_next_bar`.
- **No lookahead.** Run the `lib/lookahead_audit.one_day_lag_test` on the aggregate: shifting every
  entry one extra day must NOT collapse the edge to zero (if it does, the edge is same-bar leakage).
- **Placebo is the headline control.** Prior PEAD work proved the trailing-stop structure alone
  harvests ~+2.1%/trade of market drift. Every combo MUST report edge vs a random-entry,
  same-calendar placebo (K≥200 resamples): null mean and null 95th percentile. "Beat placebo 95th"
  is the bar that matters, not raw return.
- **Fat-tail / censoring honesty.** Report `mean_ex_top1`, `mean_ex_top2` (mean after dropping the
  1-2 biggest contributors) and `cens_pct` (% of trades still open at data-end = 2026-01-22, marked
  not realized). A mean carried by 1-2 censored names is not an edge.
- **Costs** from COST_STANDARDS: **0.67% round-trip (1x)** baseline; also report at **1.07% (2x)**.
- **No post-hoc tuning.** All 30 combos are frozen in `combos.py` BEFORE running. Report what runs.

## DATA
- Fundamentals PIT: `datasets/earnings_pit/unified_quarterly_pit.parquet`
  cols: symbol, company, quarter_end, available_date, date_source, sales, expenses, opm_pct,
  net_profit, eps, interest, depreciation, pbt, tax_pct, op_profit, source, year.
  (eps has NaNs — prefer net_profit; use eps only for the eps combo, dropna.)
- Prices (PRICE basis, correct for P&L): `datasets/derived/pit_union_panel_v1/close_panel_price.parquet`
  cols: date, symbol, close, source, spliced. **CLOSE-ONLY (no volume/OHLC)** → all price-action
  filters must be close-based (DMAs, momentum, close-to-close reaction). Range 2000→2026-01-22.
- Universe gate: `NIFTY500_TICKER_2005_2025_Final.xlsx` (Sheet1: Month-Year, Ticker; 42 snapshots).
  For each event, gate membership against the **most recent snapshot on/before `available_date`**
  (PIT membership, no lookahead). This is the liquidity gate — the original PEAD kill was illiquidity
  contamination, so it is mandatory.
- Guards lib: `Shreyas_Ionic_AMC/04_RND_LAB/lib/` (guards.py, lookahead_audit.py, execution_realism.py).

## SIGNALS (compute per event from PIT; YoY = same-symbol, same fiscal quarter, ~1yr prior)
- `np_yoy`  = net_profit YoY growth = (np_t - np_base)/|np_base|, base = np 4 quarters prior. Exclude
  base ≤ 0 from the pct signal (those go to `turnaround`).
- `eps_yoy` = EPS YoY (dropna eps).
- `sales_yoy` = sales YoY.
- `opm_delta` = op_profit/sales (this q) − (base q)  [OPM expansion; guard div-by-0].
- `qoq` = net_profit QoQ growth (prior quarter base, exclude base ≤ 0).
- `sue` = standardized unexpected earnings = (np_t − np_{t-4q}) / rolling-std of that seasonal
  surprise over the trailing ≥4 quarters (per symbol, ordered by quarter_end).
- `turnaround` = (np_{t-4q} < 0) AND (np_t > 0)  [boolean bucket].
- `accel` = np_yoy(t) > np_yoy(t-1q)  [earnings-momentum acceleration].
Quantile cuts are computed **cross-sectionally within a rolling/expanding window up to available_date**
(no full-sample quantiles — that peeks). Simplest PIT-safe cut: rank within the trailing 4 quarters
of events. If that is too sparse, rank within all events with available_date ≤ this event's date
(expanding). Document which you used.

## PRICE-ACTION FEATURES (close-based, as of D0 = entry-signal day, using data ≤ D0)
- `above_50dma`, `above_200dma`  (close vs SMA at D0)
- `ret_6m` (126td), `ret_12m` (252td) trailing returns at D0
- `reaction` = close(D0)/close(prev trading day) − 1  (announcement-window move)
- `near_52w_high` = close(D0) / rolling-max(252td) at D0  (≥0.85 = near high)

## EXECUTION / PORTFOLIO
- Entry: **D0+1 close**. Exit per combo `hold_spec`:
  - `fixed:N` → exit at close N trading days after entry (N ∈ {20,40,63,126}).
  - `dma:50` → exit first day close < 50DMA (trailing), cap at 252td.
  - `fixed:63+stop:8` → 8% hard stop from entry, else exit at 63td.
- Long-only. Equal-notional per position. Overlapping positions allowed.
- Per-trade net return = gross(entry→exit) − round-trip cost (0.67% baseline; also compute 1.07%).
- Portfolio NAV (secondary): daily portfolio return = equal-weight mean of active positions'
  close-to-close returns; entry-day return reduced by RT cost. → CAGR, Sharpe (ann, rf=0), maxDD.
- Positions still open at 2026-01-22 → mark at last close, flag censored (`cens_pct`).

## OUTPUT CONTRACT (every combo, one row appended to results.csv)
`combo_id, family, signal, cut, price_filter, hold, n_trades, win_pct, mean_net_pct, median_net_pct,
 t_stat, mean_ex_top1, mean_ex_top2, cens_pct, cagr, sharpe, maxdd, placebo_mean, placebo_p95,
 excess_vs_placebo_mean, beats_placebo95 (bool), mean_net_pct_2x`
Also write per-combo trade ledger to `ledgers/<combo_id>.csv` (symbol, avail_date, entry_date,
exit_date, gross_pct, net_pct, censored).

## COMBO REGISTRY (frozen — 30 combos, 3 families of 10)
### Family A — pure earnings momentum / PEAD (Agent A)
- A1  np_yoy top-decile · none · fixed:20
- A2  np_yoy top-decile · none · fixed:63
- A3  np_yoy ≥100% · none · dma:50
- A4  np_yoy top-quintile · none · fixed:40
- A5  sue top-decile · none · fixed:20
- A6  sue top-decile · none · fixed:63
- A7  sue top-quintile · none · dma:50
- A8  eps_yoy top-decile · none · fixed:63
- A9  np_yoy top-decile · none · fixed:63+stop:8
- A10 sue ≥2.0 · none · fixed:40
### Family B — earnings + price-action mixed (Agent B)
- B1  np_yoy top-quintile · above_50dma · fixed:63
- B2  np_yoy top-quintile · ret_6m>0 · fixed:63
- B3  sue top-quintile · above_50dma · fixed:40
- B4  np_yoy top-quintile · reaction>0 · fixed:20
- B5  np_yoy top-quintile · near_52w_high≥0.85 · fixed:63
- B6  sue top-quintile · ret_12m top-half · fixed:63
- B7  np_yoy top-quintile · above_200dma · fixed:63
- B8  np_yoy top-quintile · above_50dma · dma:50
- B9  np_yoy top-decile · reaction>3% · fixed:40
- B10 sue top-quintile · above_50dma & ret_6m>0 · fixed:63
### Family C — surprise-magnitude / turnaround / other (Agent C)
- C1  turnaround · none · fixed:63
- C2  turnaround · none · dma:50
- C3  sales_yoy top-decile · none · fixed:63
- C4  opm_delta top-decile · none · fixed:63
- C5  qoq top-decile · none · fixed:40
- C6  (np_yoy≥100% OR turnaround) · none · fixed:63
- C7  np_yoy top-decile · none · fixed:126   (long-drift)
- C8  np_yoy & sales_yoy both top-tercile · none · fixed:63  (quality growth)
- C9  accel · none · fixed:63
- C10 np_yoy top-decile · none · fixed:63 · surprise-weighted sizing (report both EW and SW)

## DELIVERABLES
- `engine.py` (shared), `combos.py` (registry), `run.py <ID...>` CLI.
- `results.csv` (all 30 rows), `ledgers/*.csv`.
- `FINDINGS.md`: leaderboard sorted by excess_vs_placebo (only beats_placebo95=True are "real"),
  artifact flags per combo, and the 1-3 survivors to escalate. HUMAN-format table.
