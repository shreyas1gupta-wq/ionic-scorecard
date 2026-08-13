# DATA QUALITY RULES — landmines + new-source protocol (Data Officer owns)

## The landmines (violating any = fake backtest; guards in 04_RND_LAB/lib/guards.py)
1. **HF timezone:** daily bars stamped 18:30 UTC = NEXT-day 00:00 IST. Always `dt.tz_convert('Asia/Kolkata').dt.date`.
2. **Pre-open auction:** 1-min "open" at 09:00 is the auction print; real open = first bar ≥ 09:15. (~94% of naive 2026 gap calcs corrupted before fix.)
3. **PIT/earnings lookahead:** act only on `available_date` (earnings_pit; 86.2% exact). NEVER quarter-end dates. **COVERAGE LANDMINE (found 2026-07-13, P1-R card):** unified_quarterly_pit rows WITH available_date are ~zero pre-2020 (2019: 133; real coverage 2021+); TTM-YoY-growth panels (need 8 quarters) are effectively non-NaN only from ~2022 — any "validate 2016-2024" on fundamentals-gated signals silently validates on 2022-2024 only. Check event-date distribution vs window BEFORE quoting a validate verdict. **PARTIALLY RESOLVED 2026-08-06 (Kavya):** `datasets/nse_results_pit/nse_results_pit_tidy.parquet` now carries REAL `broadCastDate`-derived available_date for 2011-2024 (1,584-2,135 symbols/yr) — use this instead of the +45d reconstruction plan for any (symbol, period_end) it covers. It does NOT reach every old row (77% match rate vs unified_quarterly_pit; the `conservative_lag_50d`-tagged rows specifically only match ~1.4% of the time even in well-covered years — per-symbol/quarter gaps remain in the new source too) — the +45d reconstruction is still the right fallback for genuinely unmatched quarters. See landmine 7 for the source's own coverage cliff.
4. **Option-data gap — STATUS UPDATE 2026-07-03: FILLED.** Apr-2024→Aug-2025 + Jun-2026 single-stock options backfilled from NSE UDiFF/legacy bhavcopy (1,408 sym-expiry daily parquets). Residual truths: (a) backfilled files are DAILY (EOD OHLC+settle+vol+OI), not 1-min; (b) untraded strikes carry 0.00 O/H/L (settlement still populated) — filter volume>0 for prints; (c) guard L6 now asserts SCHEMA AWARENESS not trade absence.
5. `india_fundamentals_mc/Train.parquet` `annual_report` column corrupt at source — never read it.
6. **Survivorship:** universe membership ONLY from `NIFTY500_TICKER_2005_2025_Final.xlsx` (42 PIT snapshots).
7. **fo_bhavcopy_hist date-string format is NOT uniform (found 2026-07-30, Arjun, STRUCTURAL_EDGES task):** `fo_idx_{year}.parquet` EXPIRY_DT/TIMESTAMP are strings, almost always `DD-Mon-YYYY` (11 chars, e.g. `27-Jan-2011`) — but `fo_idx_2012.parquet` has 1,467 rows (0.4% of that file) in `DD-Mon-YY` (9 chars, e.g. `31-May-12`). A single `pd.to_datetime(..., format="%d-%b-%Y")` crashes on these; a naive `format="mixed"` WITHOUT `dayfirst=True` can silently mis-parse. Verified fix (either works, cross-checked 0 disagreements across all 16 years / 7,670,250 NIFTY rows): dispatch on string length (11→`%d-%b-%Y`, 9→`%d-%b-%y`), or `pd.to_datetime(s, format="mixed", dayfirst=True)`. All other years/symbols checked clean (11-char only). Month abbreviation case also varies (`JAN`/`Jan`) — both formats above handle it.
7. **NSE `corporates-financial-results` API has a HARD COVERAGE CLIFF ~Mar-2025 (found 2026-08-06, Kavya, nse_results_pit build):** `https://www.nseindia.com/api/corporates-financial-results` (params index=equities/from_date/to_date/period=Quarterly|Annual) returns rich, clean, near-complete data for period_end 2010-03-31 through 2024-12-31 — but for period_end after that, through TODAY (checked live as late as 2026-08-05), it returns almost nothing: a trickle of years-late catch-up filings from a mix of delisted/suspended names (EROSMEDIA, ROLTA, RELCAPITAL, IL&FSTRANS, AIFL, ANSALAPI, CMICABLES, SECURCRED — all confirmed stopped trading well before 2026-07 via `datasets/nse_bhavcopy_daily/close_all.parquet`) and a few still-listed chronic-late-filers (RAJESHEXPO, VSTTILLERS). Confirmed NOT a pull bug: re-checked live with a fresh session, both narrow (1-month) and wide (3-month) windows, including the current week — same emptiness. **Do not assume "we pulled 2011-2026" means the whole span is populated — always check the period_end distribution, not just the pull's date-range parameter, before quoting coverage.** Cause unconfirmed [INFERENCE]: likely this specific historical-archive endpoint has a >1yr processing lag before recent filings are folded in; NSE's live/current-quarter results are served elsewhere (the existing `nse_earnings_dates/quarterly_results_all.json` cache or board-meetings route). Secondary finding: `broadCastDate` (exchange disclosure) can trail a company's own investor-site press release by up to ~1 week (TATASTEEL Q1-FY14: exchange 19-Aug-2013 vs press-release PDF dated 13-Aug-2013) — safe-direction (late, not early) for PIT gating, but do not assume same-day equivalence when cross-referencing external press coverage. Also: the `xbrl` field is present on every row back to the empirical floor, but for pre-~2017 filings the VALUE is a dead placeholder link (`.../xbrl/-`), not a real document — schema presence != usable content, check the value not just the key.

## Dual-schema warning (stocks_options/)
| Source | Granularity | Timestamp | Extra cols | Tell |
|---|---|---|---|---|
| HF 1-min (2021→Mar-24, Sep-25→May-26) | 1-minute | tz-aware IST | open_interest, symbol, expiry | 100k+ rows/file |
| Bhavcopy backfill (Apr-24→Aug-25, Jun-26, +122 new stocks 2yr) | DAILY | naive 15:30 stamp | settle, oi | ~few-k rows/file |
Consumers must branch on schema or use EOD-only accessors. `angel_capture_2026/` (day/ + minute/) = live forward capture, Jul-2026 onward.

## New-source protocol (D-009 verification, as amended by D-033 2026-07-11: reliable sources may auto-fetch)
1. Propose: source, URL/API, licence, cost, what edge it feeds. 2. RELIABLE sources (exchange archives, FRED/Stooq-class, official APIs) may fetch WITHOUT waiting (D-033); sketchy/unverifiable sources still need Principal approval before any fetch.
3. Sample 100 rows → schema/dtypes/nulls/dupes/date-monotonicity/PIT-safety; cross-check 5 values vs an independent source.
4. Verdict USE/QUARANTINE + draft DATA_CATALOG entry → Principal approves go-live. 5. Only then: bulk ingestion, with update command documented in the catalog.

## Freshness rules
- Count PERIODS-PER-YEAR (expiries, months, quarters), not just max(date) — the 17-month gap hid behind healthy max-dates.
- Critical sets get a daily ping via 99_OPS/EOD_ROUTINE.md; stale > 2 sessions = flag in CURRENT_STATE.

## HF daily panel: DEPTH rule (forensics 2026-07-04, results/factor_replication/20260704_data_forensics/)
- **Adjustment: CLEAN.** HF panel (train-00000) split/bonus-adjusted 14/14 audited events 2006-2018; Master xlsx 13/14 (one bad print: LT 2006 ratio 1.951 — do not trust Master LT around 2006-10).
- **Completeness: DEGRADES PRE-2018.** N200-members with full 252d history: 2006 57.6% -> 2010 71.9% -> 2014 79.7% -> 2018 83.5% (HF). The dump holds today's ~2,535 listed names with backfill; pre-dump delistings never appear (survivorship hole), plus old-ticker naming gaps.
- **RULE (upgraded, forensics round-2): pre-2018 ranking results on the HF panel are systematically OPTIMISTIC, not just noisy** — the missing names are disproportionately later-delisted losers a real screen would have picked and lost on. Bucket counts (2006): 80 missing = 76 recoverable on-disk + 1 naming (SSLT->VEDL) + 3 truly gone. Early-era selection results must NOT be certified until re-run on the survivorship-complete union panel. Post-2018 (90%+) largely sound.
- **D1 measured (round-2):** true mcap weights (pkl shares x close) cut modern-era TE 6.91% -> 6.50%; residual = free-float IWF + effective-date timing, not weighting.
- **Better early-era source (cached):** `results/factor_replication/20260704_data_forensics/_combined_master_delisted_close.parquet` — Master+Delisted union, 5,363 days x 1,204 names, close-only, adjusted. Use for early-era cross-sectional work; still misses ~70/200 of the 2006 index.
- stocks_data_cache.pkl (root, Principal): yfinance 435 tickers 2020-06->2026-01 ADJUSTED + shares outstanding + TTM funda (378) + sectors — modern-era mcap weights & quality overlay; useless pre-2018.

## PRICE BASIS verdicts (bhavcopy ground-truth, 2026-07-04 — pit_union_panel_v1/basis_ground_truth_check.csv)
- **HF panel / Delisted xlsx / raw-nifty500 = PRICE basis** (94.8% exact match vs official bhavcopy closes).
- **Master xlsx = RETURN basis (dividend-adjusted)** — 41.4% match, drift toward 1.0 near present. NEVER compare Master levels to exchange prints or price indices directly.
- Earlier same-day hypothesis (HF=dividend-adjusted) was WRONG — inverted by ground truth. Lesson: cross-source disagreement identifies A mismatch, only ground truth identifies WHICH source.
- Replication (HF, price basis) vs official price indices = consistent; dividend-inflation explanation for residual TE RETIRED. BT-11 on HF: price-basis backtest understates total return if dividends ignored — note, not a defect.
- **CANONICAL PANELS (datasets/derived/pit_union_panel_v1/): `close_panel_price.parquet` (2,511 sym) for replication/level work · `close_panel_return.parquet` (2,556 sym, ratio-spliced) for backtests.** symbol_aliases.csv = standing alias table. QUARANTINED segments (9, e.g. HINDZINC 57x internal jump in Master) in quarantined_segments_*.csv — never un-quarantine without a bhavcopy check. 159 index/ETF symbols excluded from HF "stock" space.
- **v1.1 UPGRADE (2026-07-04, Manoj — bhavcopy 2014+ recovery, BUILD_REPORT.md v1.1 section):
  `close_panel_price_v11.parquet` (2,522 sym) / `close_panel_return_v11.parquet` (2,566 sym)** —
  v1 + 127-name bhavcopy recovery, achievable N500 coverage 97-100% at every Mar snapshot
  2014-2025 (IPO-age names excluded from denominator with a named reason each). v1's original
  files are UNCHANGED (md5-verified, frozen-consumer-safe) — `_v11` is opt-in, nothing
  auto-upgrades. New permanent asset: `datasets/nse_bhavcopy_daily/close_all.parquet` (5.57M
  rows, 3,716 symbols, 2013-2026 official NSE EQ bhavcopy) — use this for ANY future "is symbol X
  in our data" question instead of re-pulling. 3 named residual gaps only: SREINFRA (quarantined
  — real 2021-22 NCLT restructuring discontinuity, not a data error), IISL (likely NSE's own
  unlisted index subsidiary, not a tradeable equity), UNKNOWN (membership-xlsx data-entry
  artifact, carried over from v1).
- **N200/N500 PIT snapshots are Mar/Sep** (not Jun/Dec) — membership as-of logic must use Mar/Sep dates.

## BENCHMARK INDEX BASIS ruling (2026-08-06, Kavya — Principal ruling, verbatim in the task)
Principal: "take whichever we can find tri non-tri and save using skills we had skill to scrap
from nse we have but be consistent i.e. same for all funds and same for all workflow." Consistency
across categories and across the workflow beats TRI purity — a clean PRI series used identically
everywhere beats a patchwork of TRI-for-some/PRI-for-others.
- **PRI is not a choice here, it is the only option.** Checked fresh this session, not assumed
  from old docs: (1) no index_name in `nse_official_all_indices.parquet` matches `TRI`/`Total
  Return`; (2) NSE's own live `https://www.nseindia.com/api/allIndices` (tested live 2026-08-06,
  200 OK, reachable at the office right now) returns PRI + PE/PB/DivYield fields only, same as our
  archive pull, no TRI field anywhere in the payload; (3) nothing named `*TRI*`/"Total Return"
  exists anywhere in `datasets/`. The only real TRI source is niftyindices.com, proxy-blocked at
  the office (factor-indices skill, unchanged). **RULING APPLIED: `basis`='PRI' on every row of
  `benchmark_index_levels.parquet`, structurally (a column, not a footnote) — see DATA_CATALOG.**
- **div_yield TRI-reconstruction, TESTED (task ask, not adopted into the panel):** compounding
  `nse_official_all_indices.div_yield` (trailing annual %, present 100% of days on all 6 core
  indices) as a daily multiplicative accrual on top of the PRI daily return reproduces the
  **independently-documented ~1.2-1.5pp/yr TRI-PRI drag** (qfra1-rerun skill / NEXT_WEEK_QUEUE.md
  2026-07-26 audit) closely: measured 1.13-1.32pp/yr on Nifty 500 across four windows (1y/2y/3y/
  10.6y) and 0.69-1.39pp/yr across all 6 core indices, full-history. Two independent derivations
  (a one-date level comparison vs. this session's daily-yield compounding) landing in the same
  ballpark is a real cross-check, not a coincidence. **BUT it cannot reproduce an absolute TRI
  LEVEL** — anchored at the source panel's 2016-01-01 start, it implies a 2025-01-31 pseudo-TRI/PRI
  ratio of 1.11 vs the documented real ratio of ~1.53 (21,580.9 -> ~33k), because it is missing
  1995-2016 dividend compounding, not because the method is wrong. **Verdict: usable as a RETURN-
  GAP estimator if TRI purity is later reprioritized over consistency, NOT usable as a level
  series today, and NOT adopted now regardless — div_yield only exists for equity indices, so
  using it for equity while debt/hybrid stays PRI would recreate the exact inconsistency this
  ruling forbids.** Test script + full numbers: this session's scratchpad
  (`test_tri_reconstruction.py` output), reproducible from `mf_benchmark_indices_build.py`'s
  inputs.
- **D-009 cross-check, 18/18 exact** (6 core indices x 3 dates spanning the window: 2025-01-31,
  2025-06-30, 2026-07-31) — fresh independent re-fetch of NSE's own `ind_close_all_DDMMYYYY.csv`
  vs `nse_official_all_indices.parquet`, 0.00 diff on every value. Confirms both the PRI-basis
  claim and the file's current accuracy, not just a historical 2026-07-04 pass.
- **A number in the Principal's ruling didn't match anything in the file it referred to, and DOES
  match an unrelated dataset from earlier the same day** — flagging so nobody chases it further.
  "2,709 symbols worth of benchmark names" in the ACE MF file: verified counts are 8,907 Direct-
  Plan rows / 8,870 unique ISINs / 374 unique `Benchmark Indices` names — no cut of the ACE file
  produces 2,709. That exact number IS the symbol count of `nse_results_pit_tidy.parquet` (see
  DATA_CATALOG, entry built earlier the same session/day) — an unrelated NSE-filings dataset. Read
  as a likely same-day cross-reference slip, not a hint about the ACE file; verified counts used
  instead of chasing the stated figure.

## Panel defects found by D-029 benchmark build (2026-07-04, Ishaan — Kavya to own fixes)
1. **988 phantom calendar rows** in the union return panel (<100 non-null closes on a "trading day") — filter trading calendar by min-coverage before any daily-return computation.
2. **Mid-quarter delisting NaN propagation** (2006Q2 bank-merger cluster etc.) — require valid price at rebalance AND fill AND period-end, or realize the delisting loss explicitly.
3. **212 symbols with FROZEN/STALE price runs** (bit-identical closes >=20 sessions; worst NKIND 2,949 days; JMFINANCIL pinned at Rs0.14 x44 sessions then jumping to Rs31 = fabricated >20,000% single-name return). **RULE: apply `datasets/derived/benchmarks_random/stale_mask.parquet` (0.90% of panel rows) in EVERY backtest on the union panels.** This was exactly the pre-registered "p95 too good -> check prices" trap — it fired in smoke-testing (72% p95) and was caught.
- **US stocks daily = SURVIVORS ONLY (measured 2026-07-13):** 471/1202 S&P500 ever-members (39%) have NO price history (bankruptcies/buyouts); current members 100% covered. Usable for regime/risk models; BANNED for US stock-selection return claims until delisted prices sourced (Norgate route in REMOTE_SOURCES). Ticker-rename map would recover part - not built yet.
