# ALPHA_RANKER — PROGRESS CHECKPOINT

> Update this after EVERY step. Any session (this login or the $100 execution login, or a token-limit restart) must be able to resume from here alone.

## GOAL
Build a 4-lens (1M / 1Y / 5Y / MICROCAP) regime-aware probabilistic conviction engine for Indian equities (NIFTY 750 + microcap), outputting a [-100,+100] score + P(up) + expected return + win-rate + 1-para thesis per stock, guided by an oversight cascade and an AMC-grade forensic module, validated by a 1000+ test R&D loop.

## STATUS: FULL NIFTY-750 ENGINE LIVE. One-command rebuild `src/run_universe.py` (consolidate→technical→fundamental→forensic→cascade→fuse, ~3min) → `results/universe_final_scores.csv`. 750/751 scored all horizons, 746 full 6-theme. Scraper "+"-row bug FIXED (standalone fallback; 749/751 valid quarterly). Sector self-reference FIXED (real Industry sectors, median 24 peers). NEXT = Phase-6 calibration (ranks→probabilities) + human deliverable.
## MASTER FUNDAMENTALS FILE (single source, all companies, PIT-safe, quarterly-rebuildable)
`data/fundamentals/MASTER_fundamentals_pit.parquet` — builder `src/lib/build_master_fundamentals.py`. 1.09M rows, 4,613 companies, FY2002-2026, LONG (key_symbol,nse_symbol,company,fiscal_year,statement PL/BS/CF,metric,value,available_date,source,is_fresh). Backbone = earnings_pit yearly_profit_loss_pit + yearly_balance_sheet_pit (PIT available_date, but VERIFIED stale to 2023-11-30 — the "current/TTM" claim was WRONG; both PIT yearly files cap FY23). Fresh overlay = screener_live consolidated (fresh wins). 741 co reach FY>=2024 now; grows as the all-symbol scrape lands. NOTE: PIT nse_symbol only on 2,234/4,491 (26k nulls) — unmapped names carry key_symbol='NAME::<company>' and get PIT-only (no fresh overlay). Scrape of 1,606 mappable TODO IN FLIGHT (6 procs, symbols_all_4491.txt). Re-run consolidate+build_master after it lands.
## PRIOR STATUS (superseded): scaling in flight.
## SCALE-UP (in flight)
- Universe: `data/universe/nifty_total_market_750.csv` (751 rows, incl Industry→sector) from Principal's NSE URL. Refetch each quarter.
- Prices: `yf_batch.py` 3 procs × 5y daily → `data/prices/` (resume-safe, 621+/751 at last check).
- Fundamentals: `screener_scrape.py` 5 procs, PUBLIC pages (no login) → `data/fundamentals/screener_live/*.json` -- **DONE, 751/751**; consolidate via `consolidate_screener.py` → `consolidated/*.parquet` (751 symbols, re-run 2026-07-16 21:54).
- **NEW (2026-07-16, this session): Universe fundamental+catalyst engine built & run** — `src/factors/universe_fundamental.py` (reuses `factors_fundamental.py`/`fresh_catalyst.py` logic, upgraded to read live consolidated parquets + prefer screener's own TTM `top_ratios` (Market Cap/P-E/Book Value/ROCE/ROE) over the derived-shares fallback; explicit bank/NBFC schema branch: ROCE + all 3 Leverage factors -> N/A for 56 financial names). Outputs: `results/universe_fundamental_scores.parquet`, `results/universe_catalyst_scores.parquet`, `results/universe_fundamental_factors_raw.csv`, `reports/UNI_A_fundamental_catalyst.md`. Scored 697/751 (92.8%); cross-sectional percentiles over the 697 covered now, re-percentiles automatically as coverage grows.
- **DATA-QUALITY BUG FOUND (not yet fixed): 54/751 symbols have a `screener_scrape.py` HTML-parsing defect** — every financial-statement table ("+"-expandable rows: Sales+, Revenue+, Cash from Operating Activity+, etc) collapsed to one malformed key-value pair per row (label of the NEXT row instead of period:value data); `shareholding` (no "+" rows) parses fine for the same symbols, pinning the bug to the "+"-row table path specifically. Full list + example in `reports/UNI_A_fundamental_catalyst.md`. `universe_fundamental.py` correctly treats these as fully-missing (NaN), not fabricated/zero-filled — but they read as "unscraped" in a naive count when they are not. ACTION: patch `screener_scrape.py`'s "+"-row parser, re-scrape these 54, re-run consolidate + universe_fundamental for full 751 coverage.
## NEXT
> 1. Patch the 54-symbol scraper bug above, re-run consolidate+universe_fundamental for full coverage. 2. Build the remaining universe-scale themes (technical/momentum, flow, forensic, regime-cascade) the same way AG3/AG6/AG7 did for the pilot, reading the universe-wide sources. 3. Re-fuse → full-universe ranked table via `combine_scores.py` (adapt for universe scale). 4. Phase-6 calibration on 21yr `Nifty500_Master` panel. 5. Human-format deliverable.
## KEY CAVEATS: (1) most fundamental/flow/shareholding data stale ~2023-24 (only prices+factorNAVs current); (2) cascade sector layer self-referential for singleton sectors (discount ASIANPAINT 1Y/5Y); (3) SHAKTIPUMP no fundamentals (3/6 cover); (4) scores uncalibrated relative ranks. Combiner reconciliation done: flow→theme_flow_micro_current, cascade→net_adj, fundamentals→Quality/Growth/Value.

## DONE (this session)
- [x] **Phase 2 — Regime classifier** built from `factor_navs (1).xlsx` (2005-04-01 → 2026-02-27, 5,189 rows): `ALPHA_RANKER/src/regime/regime_classifier.py`. 5 causal, no-lookahead lenses: Trend (NIFTY500 vs 50/200-DMA+slope), Volatility (21d RV, expanding tertile), Breadth (Midcap150+Smallcap250 RS vs Nifty100), Risk appetite (HighBeta50 vs LowVol30, Gold vs Nifty500), Factor leadership (Momentum/Value/Quality/LowVol/Alpha 3m+6m blend). Outputs: `results/regime_timeline.parquet` (47 cols), `results/current_regime.json`, `reports/AG4_regime.md`.
- [x] Found + handled a real data-freshness split in the input: 4 columns (NIFTY 500, Low Vol 30, Momentum 30, Midcap Momentum 50) update to 2026-02-27; the other 16 stop at 2026-01-05 (clean vendor-lag trailing-NaN block, verified no internal gaps). Snapshot reports per-lens `as_of` date rather than forward-filling/guessing.
- [x] Sanity-validated on COVID crash (Feb-Apr 2020: bull→sideways→bear + vol_regime→high tracks the crash) and 2021 rally (sustained bull) — mechanism behaves as intended, non-degenerate label distributions across all 21yr / 5 lenses.
- [ ] NOT YET DONE: formal one-day-shift lookahead-audit pass (structurally causal by construction — rolling/pct_change/expanding only — but not run through `lib/lookahead_audit.py` / the `lookahead-audit` skill; do this before Gate-4/weight-book wiring).
- [ ] NOT YET DONE: wiring `current_regime.json` into the actual weight-book lookup (`weights/` YAML) described in `02_SCORING_ENGINE.md` Step 4 — this session only produced the classifier + snapshot, not the consumer.

## DONE (execution session, DESK-100)
- [x] Requirements locked via 20-question brief; full planning package (docs 00–13) written.
- [x] Env confirmed: Python 3.14.5; yfinance/pandas/numpy/requests/truststore/openpyxl/lxml/bs4 all present.
- [x] Folder tree built: `data/{prices,fundamentals,macro,concalls,universe}`, `src/{factors,themes,regime,cascade,forensic,scoring,agents,lib}`, `weights`, `results`, `reports`.
- [x] **yfinance works through the corporate proxy** — 10-stock pilot pulled clean (2y daily, 499 bars).
- [x] Pilot = HDFCBANK, ASIANPAINT, NESTLEIND (large-Q); TATASTEEL, HINDALCO, MARUTI (cyclical); TCS, INFY (IT); GRAVITA, SHAKTIPUMP (smallcap-proxy). TATAMOTORS.NS dropped (real-world demerger renamed listing) → MARUTI swapped in.
- [x] **D-009 schema-sanity PASSED** on all 10 (OHLC integrity, no NaN/neg/dup, monotonic dates, ≤4d gaps). NOTE: prices are forward of assistant knowledge cutoff → external price-verification deferred to Principal / NSE bhavcopy cross-check.
- [x] NIFTY (^NSEI) benchmark pulled for relative strength.
- [x] **Phase 1.1 + 1.6:** technical/momentum/mean-reversion factor library + relative-scoring core built & run → `results/pilot_1m_factors_raw.csv`, `results/pilot_1m_scores.csv`. Coherent output (IT weakest, quality-momentum strongest).
- [x] **Phase 1.2 (Catalyst/EarningsMomentum, 1M primary):** `src/factors/factors_catalyst.py` built & run on earnings_pit (PIT-gated on `available_date`) + earnings_dates/forthcoming_results calendars → `results/pilot_catalyst_factors.csv`, `results/pilot_upcoming_results.csv`, `reports/AG2_catalyst.md`. DATA VINTAGE CAVEAT: `quarterly_earnings_pit.parquet` financial figures cap at quarter_end 2023-09-01 (13 quarters back to 2020-09) for all 10 pilot names — growth/surprise factors use that latest-available quarter, NOT a live current print; the days-to/-since-result calendar factors DO use current 2026 dates (separate feed). Upcoming-1M-event (<=30d) flagged for HDFCBANK(18-Jul), NESTLEIND(22-Jul), INFY(23-Jul), HINDALCO(7-Aug); no forward date on file for ASIANPAINT/GRAVITA/MARUTI/SHAKTIPUMP/TATASTEEL/TCS (feed window only covers ~09-Jul to 10-Aug-2026; TCS's own date already passed). Theme scores (desc): SHAKTIPUMP 90, MARUTI 79.1, HDFCBANK 76.4, GRAVITA 62.1, NESTLEIND 60.6, INFY 43.6, HINDALCO 43.0, ASIANPAINT 40.5, TCS 38.5, TATASTEEL 18.4 (loss quarter Sep-2023).

## BLOCKS RESOLVED — data found on disk (Principal pointed to datasets/ + root xlsx)
Both prior blocks are GONE:
- **Fundamentals/forensic** — `datasets/screener_deep/{annual_pl,balance_sheet,cash_flow}.parquet` + `datasets/screener_dump_20260704/` (623 CSV + 360 xlsx) + `datasets/earnings_pit/{quarterly_earnings_pit(52k,PIT available_date), mc_fundamentals_parsed(146 cols)}.parquet`. NO screener login needed.
- **Factor/regime benchmark** — `factor_navs (1).xlsx` (daily 2005+ NAVs: NIFTY50/100/500, Midcap/Smallcap, Quality30/Value30/Momentum30/Alpha30/LowVol30/HighBeta50, GOLDBEES, liquid-cash). NO home-network needed.
- Also on disk: `nse_bhavcopy_daily/delivery_2022_2026.parquet` (delivery%), `nse_earnings_dates/` (forthcoming results), `india_earnings_calls/` (concall transcripts+links), `india_stock_metadata/india.csv` (sector), `Nifty500_Master_Dataset_2005_2025.xlsx`.

## IN FLIGHT — 7-agent fan-out (Principal directed 7 parallel, overriding D-023 default)
Agents building on the 10-stock pilot; each writes code+CSV+report to disk:
- AG1 fundamentals (Quality/Value/Growth/Leverage) → `src/factors/factors_fundamental.py`, `results/pilot_fundamental_scores.csv` [relaunched after stream-timeout]
- AG2 catalyst/earnings-PIT → `src/factors/factors_catalyst.py` [relaunched; all 10 pilot confirmed in PIT set]
- AG3 flow/delivery → `src/factors/factors_flow.py` [relaunched]
- AG4 regime classifier → `src/regime/regime_classifier.py`, `results/current_regime.json`
- AG5 concall rubric → `src/themes/concall_rubric.py`
- AG6 forensic red-flags → `src/forensic/forensic_checks.py`, `results/pilot_forensic_score.csv`
- AG7 factor-bench + oversight cascade → `src/lib/factor_bench.py`, `src/cascade/oversight_cascade.py`, `results/pilot_cascade_adjustments.csv`
NOTE: background agents are hitting intermittent API stream-idle timeouts under high concurrency; relaunch on failure with anti-stall guidance (small steps, filter big parquets, save partials).

## DONE beyond Phase-0
- [x] Phase-1.1/1.6 technical/momentum library + relative scoring (`src/factors/factors_technical.py`).
- [x] **Weight book** `weights/horizon_weights.json` (7-theme priors × 4 horizons + cross-horizon coupling + band thresholds), from `02` Step-3.
- [x] **Phase-5 scoring engine** `src/scoring/combine_scores.py` — fuses all theme CSVs → per-horizon conviction [-100,+100] + band + uncalibrated p_up; renormalizes over available themes; forensic penalty (size/regime hook); cascade points; 1M→1Y/5Y drag (Q9). Verified end-to-end on partial themes (`results/pilot_final_scores.csv`, `scoring_coverage.json`).

## NEXT
> 1. As each agent lands, re-run `combine_scores.py` → coverage rises from 2/6 to 6/6 themes → real multi-horizon scores.
> 2. Reconcile any column-name mismatches between agent CSVs and the combiner adapters (the `_pick` keyword lists).
> 3. Phase-6 calibration harness (11_BACKTEST_CALIBRATION.md) — map raw conviction → realized hit-rate/return on history; regime-conditional weight tilts.
> 4. Human-format deliverable (Principal order): Word/table per horizon, not .md.

## OUTPUT PATHS (fill in as built)
- Data: `ALPHA_RANKER/data/`
- Factor library: `ALPHA_RANKER/src/factors/`
- Scoring engine: `ALPHA_RANKER/src/scoring/`
- Backtest results: `ALPHA_RANKER/results/`
- Per-stock reports: `ALPHA_RANKER/reports/`

## DONE — Phase 4: Forensic / red-flag module (this session)
- [x] `src/forensic/forensic_checks.py` — 18 flags/symbol across accruals, earnings quality,
  Beneish components (DSRI/GMI/SGI/TATA computed; AQI + composite M-score insufficient-data,
  not fabricated), balance-sheet stress, promoter holding/pledge. Sources: `screener_deep`
  (BS/CF/PL), `datasets/earnings_pit/mc_fundamentals_parsed.parquet`,
  `datasets/derived/shareholding_changes.parquet`. No size/regime multiplier applied here —
  that's scoring engine Step 6's job; this module only emits (raw_signal, base_severity, note).
- [x] Outputs: `results/pilot_forensic_flags.csv` (180 rows), `results/pilot_forensic_score.csv`,
  `reports/AG6_forensic.md` (full coverage-honesty writeup).
- Key data-quality findings (see report for detail): SHAKTIPUMP has zero coverage in
  screener_deep/mc_fundamentals (score 0.0 = unmeasured, not clean); `shareholding_changes.parquet`
  stale firm-wide (max quarter_end 2023-12-01, ~2.5y old); HDFCBANK's -25.6pp promoter-holding
  drop is likely an HDFC-merger reclassification artifact, not organic selling; promoter PLEDGE %
  has no source anywhere checked (screener_dump_20260704/screener/excel_reports/ is empty) —
  insufficient-data hook left for D-033 ingestion.
- NEXT: wire `pilot_forensic_score.csv` into the scoring engine's Step 6 (size_mult/regime_mult
  application); if/when a pledge-disclosure source is found, fill that hook.

## OPEN DECISIONS FOR PRINCIPAL
- [ ] Screener.in login method: live session cookie vs periodic export? (default: live session, Principal logs in on request)
- [ ] Which 10 stocks for the pilot? (default: a spread — 3 large quality, 3 cyclical, 2 IT, 2 microcap)
- [ ] Bloomberg semi-annual dump: approve the screen list in `09_DATA_LAYER.md` §Bloomberg?
