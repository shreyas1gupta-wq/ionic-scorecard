# DATA QUALITY RULES — landmines + new-source protocol (Data Officer owns)

## The landmines (violating any = fake backtest; guards in 04_RND_LAB/lib/guards.py)
1. **HF timezone:** daily bars stamped 18:30 UTC = NEXT-day 00:00 IST. Always `dt.tz_convert('Asia/Kolkata').dt.date`.
2. **Pre-open auction:** 1-min "open" at 09:00 is the auction print; real open = first bar ≥ 09:15. (~94% of naive 2026 gap calcs corrupted before fix.)
3. **PIT/earnings lookahead:** act only on `available_date` (earnings_pit; 86.2% exact). NEVER quarter-end dates. **COVERAGE LANDMINE (found 2026-07-13, P1-R card):** unified_quarterly_pit rows WITH available_date are ~zero pre-2020 (2019: 133; real coverage 2021+); TTM-YoY-growth panels (need 8 quarters) are effectively non-NaN only from ~2022 — any "validate 2016-2024" on fundamentals-gated signals silently validates on 2022-2024 only. Check event-date distribution vs window BEFORE quoting a validate verdict. Unlock job queued: reconstruct pre-2020 available_date = quarter_end + 45d (SEBI deadline, conservative-late = PIT-safe) as a SEPARATE panel (`available_date_recon` flag), never overwrite the exact dates.
4. **Option-data gap — STATUS UPDATE 2026-07-03: FILLED.** Apr-2024→Aug-2025 + Jun-2026 single-stock options backfilled from NSE UDiFF/legacy bhavcopy (1,408 sym-expiry daily parquets). Residual truths: (a) backfilled files are DAILY (EOD OHLC+settle+vol+OI), not 1-min; (b) untraded strikes carry 0.00 O/H/L (settlement still populated) — filter volume>0 for prints; (c) guard L6 now asserts SCHEMA AWARENESS not trade absence.
5. `india_fundamentals_mc/Train.parquet` `annual_report` column corrupt at source — never read it.
6. **Survivorship:** universe membership ONLY from `NIFTY500_TICKER_2005_2025_Final.xlsx` (42 PIT snapshots).

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

## Panel defects found by D-029 benchmark build (2026-07-04, Ishaan — Kavya to own fixes)
1. **988 phantom calendar rows** in the union return panel (<100 non-null closes on a "trading day") — filter trading calendar by min-coverage before any daily-return computation.
2. **Mid-quarter delisting NaN propagation** (2006Q2 bank-merger cluster etc.) — require valid price at rebalance AND fill AND period-end, or realize the delisting loss explicitly.
3. **212 symbols with FROZEN/STALE price runs** (bit-identical closes >=20 sessions; worst NKIND 2,949 days; JMFINANCIL pinned at Rs0.14 x44 sessions then jumping to Rs31 = fabricated >20,000% single-name return). **RULE: apply `datasets/derived/benchmarks_random/stale_mask.parquet` (0.90% of panel rows) in EVERY backtest on the union panels.** This was exactly the pre-registered "p95 too good -> check prices" trap — it fired in smoke-testing (72% p95) and was caught.
- **US stocks daily = SURVIVORS ONLY (measured 2026-07-13):** 471/1202 S&P500 ever-members (39%) have NO price history (bankruptcies/buyouts); current members 100% covered. Usable for regime/risk models; BANNED for US stock-selection return claims until delisted prices sourced (Norgate route in REMOTE_SOURCES). Ticker-rename map would recover part - not built yet.
