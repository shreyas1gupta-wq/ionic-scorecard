# WEB PACKET — BLIND GRID JUDGING (Firm S)

You are a strict, fair grader. For EACH answer below, score 0-10 on how well it meets the task's
rubric anchors (each anchor ~1 point; award partial credit; do not reward length or fluff).
You do NOT know which model wrote which answer — do not guess. Score only against the anchors.
OUTPUT (one line per answer, nothing else): `ID=<Gxxx> SCORE=<0-10> HITS=<n_anchors_met> NOTE=<=12 words`
Do each task's answers together for consistency. One pass, no revisiting.

============================================================
# TASK MG01 — rubric anchors:
  1. PIT index membership as-of (not today's list backward)
  2. no lookahead: available_date / adjusted-price awareness
  3. survivorship-complete panel incl delisted
  4. execution = next bar, NOT formation-day close (explicit)
  5. realistic costs: STT/impact/ADV cap (not flat bps)
  6. trade the delta / turnover, not full rebuild
  7. same-exit or random-basket placebo control
  8. lag-sensitivity test
  9. cost-stress 2-3x and/or regime split
  10. explicit pre-registered kill criteria

----- ANSWER G010 (task MG01) -----
# Backtest Specification — NIFTY500 Top-20 Six-Month Momentum, Monthly Rebalance (v1.0)

Status: frozen before first run. Any edit after the first run creates v1.1 and must be logged in the trial ledger (Section 10). All dates are NSE trading dates, all amounts INR, all returns total-return unless stated.

## 0. Fixed parameters

| Parameter | Value |
|---|---|
| Evaluation window | 2015-01-01 to 2026-06-30 |
| Raw data pulled from | 2014-01-01 (signal + liquidity lookback buffer) |
| Universe | NIFTY500, point-in-time membership |
| Signal | 6-month total return (no skip-month in base; skip variant required, C4) |
| Holdings | Top 20 by signal, equal weight 5.00% at rebalance |
| Rebalance | Monthly. Signal date T = last trading day of month m; execution date E = first trading day of month m+1 |
| Execution price (base) | Close of E |
| Base AUM | ₹10 crore (capacity stress at ₹100 crore, C11) |
| Benchmark (primary) | NIFTY500 TRI |
| Cash | Idle cash accrues daily at 91-day T-bill yield (FBIL/RBI series) |

## 1. Scope and hypothesis

Hypothesis: cross-sectional price momentum in Indian large/mid/small caps survives realistic Indian delivery-trading costs (which are dominated by STT) at small AUM. The backtest's job is to measure net-of-cost excess return versus honest benchmarks and to try to destroy the result via Section 8. This is long-only, cash equities, no leverage, no derivatives, pre-tax (but turnover must be reported so STCG drag can be estimated — every holding period here is <12 months, so all realized gains would be short-term).

## 2. Data requirements and point-in-time rules

### 2.1 Security master
- Key every security on a permanent internal ID mapped to (ISIN, NSE symbol, validity date range). NSE symbols change frequently (name changes are common in India); ingest NSE's symbol-change file and never join on raw symbol across time.
- Ingest the bhavcopy `SERIES` field daily (EQ, BE, BZ, etc.). BE/BZ = trade-to-trade segment; this is an eligibility input (Section 3).

### 2.2 Prices and corporate actions
- Daily OHLCV + traded value from NSE bhavcopies (unadjusted), 2014-01-01 onward. The trading calendar is defined as "dates a bhavcopy exists" — this automatically handles Muhurat sessions and special Saturday sessions (e.g., Budget-day sessions). Do not use a synthetic calendar.
- Build two adjusted series per stock: (a) price-return series adjusted for splits, bonuses, rights, demergers; (b) total-return series = (a) plus gross cash dividends reinvested in the same stock at ex-date close. Signals and NAV use the total-return series.
- Corporate-action adjustment factors from NSE/BSE CA files or a commercial vendor (Accord/Capitaline/CMIE/Refinitiv). Do **not** use Yahoo-style free adjusted data for India; its bonus/demerger handling is unreliable.
- India-specific CA rules a junior must implement explicitly:
  - Bonus issues are ubiquitous — treat exactly like splits via ratio factor.
  - Rights issues: apply the theoretical ex-rights price factor; assume non-subscription and credit **zero** for the entitlement (conservative; note the small downward bias).
  - Demergers: the parent gaps down on ex-date and will otherwise show a fake negative 6-month return. Adjust the parent's back-history by the ex-date factor (vendor-supplied or (cum price − implied spin value)/cum price). Portfolio holding of the spun-off entity: hold, then sell at close of its 5th trading day post-listing.
  - Mergers/buyouts: convert at swap ratio on ex-date; cash consideration credited to cash on payment date.
  - Suspension/delisting-for-cause: mark at last traded price; write down 75% after 60 calendar days of suspension, 100% after 180 days unless trading resumes.
- Point-in-time rule for all of the above: a corporate action affects the backtest only from its ex-date/effective date. Adjustment factors may be applied retroactively to the price series (that is standard and not look-ahead), but eligibility, membership, and signals must use only information public on or before T.

### 2.3 Index membership (the load-bearing item)
- Reconstruct monthly point-in-time NIFTY500 membership from NSE Indices' monthly constituent/market-cap-weightage file archives, supplemented by ad-hoc replacement announcements (mergers, delistings, demergers trigger intra-review changes). Do not hardcode the review schedule — ingest actual change events with their **effective** dates (announcement precedes effective date, so using effective dates is PIT-safe).
- Membership test at signal date T = "member per the latest membership state effective on or before T."
- Validation gate: membership must exist for every month 2014-06 to 2026-06 with 500 ± 10 names. If this cannot be assembled, see kill K1. Using today's constituent list backfilled is forbidden except as the deliberate bias-measurement arm of C1.

### 2.4 Auxiliary data
- Daily ASM/GSM surveillance lists (NSE publishes daily; GSM exists from Mar 2017, ASM from Mar 2018 — the related filters simply don't bind before those dates).
- Daily price-band data (2/5/10/20% bands; F&O-list stocks have dynamic bands). Needed for the circuit fill rule (Section 5).
- 91-day T-bill yields (risk-free and cash accrual); NIFTY500 TRI and NIFTY200 Momentum 30 TRI levels (note: Momentum-30 history before Aug 2020 launch is backfilled by NSE — label it as such); Agarwalla–Jacob–Varma (IIM-A) India factor series for the factor regression.

### 2.5 Data validation gates (run before any strategy code)
- G1: Reconcile daily adjusted total returns for 25 randomly sampled stock-quarters against a second independent source; >25 bps disagreement on >0.5% of stock-days fails the gate.
- G2: Spot-check known events end-to-end: RIL bonuses (2017, 2024), Eicher split (2020), IRCTC split (2021), Nestlé India split (2024), Reliance→Jio Financial demerger (2023), ITC→ITC Hotels demerger (2025). The adjusted series must show no artificial jump on ex-dates.
- G3: Flag every |daily return| > 30% with no same-day CA record; every one must be manually dispositioned (real move vs data error).
- G4: No stale prices — any stock whose close is identical for 10+ consecutive sessions with zero volume gets a data-quality flag and is treated as suspended for those days.

## 3. Universe construction (apply in this exact order, evaluated at each signal date T)

1. NIFTY500 member on T (PIT, per 2.3).
2. NSE series is EQ on T (excludes BE/BZ trade-to-trade).
3. Not suspended on T; traded (volume > 0) on T and on ≥ 90% of trading days in [T−6M, T].
4. Listed on or before T−7M (guarantees full signal window; mechanically excludes recent IPOs — intended, given India's 2021/2024 IPO waves and lockup cliffs).
5. Not in GSM (any stage) and not in ASM long-term Stage II+ on T. (These carry 5% bands / 100% margin / T2T settlement; treat as untradeable-in-size.)
6. 63-day median daily traded value (MDTV) ≥ ₹5 crore.

Ties in the momentum ranking are broken by higher MDTV, then lexicographic ISIN (determinism requirement). If fewer than 20 names survive the filters, hold the shortfall in cash — never relax filters to fill the book.

## 4. Signal and portfolio construction

- Signal: `R6(i,T) = TR(i,T) / TR(i, T−6M) − 1`, where TR is the adjusted total-return level and T−6M is the last trading day of calendar month m−6. If either endpoint falls on a non-traded day for the stock, use the nearest prior traded day within 5 sessions, else the stock is ineligible.
- Rank eligible names descending on R6; select top 20; target weight 5.00% each.
- No sector constraints, no buffers, no vol scaling in the base config (variants are C10).
- Between rebalances: no trading on drift; only forced CA events per 2.2. Dividends and CA cash go to the cash bucket.

## 5. Execution convention

- Signal computed strictly from closes up to and including T. First possible trade is E = next trading day. Base fill price = close of E. (Same-day T-close execution is look-ahead by construction and appears only as a labeled diagnostic in C3.)
- Circuit rule: if a buy target closes at its upper band on E (or a sell at its lower band), assume **no fill**; retry at the next day's close, up to 3 attempts; then abandon (buy → weight stays in cash; sell → hold to next rebalance). This matters: fresh momentum names in India are frequently band-locked.
- Participation cap: a single day's trade in a stock ≤ 10% of its MDTV; split larger orders across consecutive closes (relevant only in the ₹100 crore run).
- Shares are integers, lot size 1, round down, residual to cash. Settlement (T+2 → T+1 in Jan 2023) is assumed cash-neutral via same-day buy/sell netting at the custodian; state this assumption in the report.

## 6. Cost model (per side, on traded value, delivery segment)

| Component | Buy | Sell | Notes |
|---|---|---|---|
| Brokerage | 5.0 bps | 5.0 bps | Institutional discount assumption |
| STT (delivery) | 10.0 bps | 10.0 bps | Constant across 2015–2026; the dominant line |
| Stamp duty | 1.0 bps (<Jul 2020), 1.5 bps (≥Jul 2020) | — | Buy side only post-unification |
| Exchange txn + SEBI fee + GST | 0.5 bps | 0.5 bps | Lumped |
| DP charge | — | ₹15 per ISIN per sell day | Flat, near-zero at size |
| Impact + half-spread, by MDTV | ≥₹50 cr: 10 bps; ₹10–50 cr: 20 bps; ₹5–10 cr: 35 bps | same | Applied per fill |

All-in one-way cost is therefore ~27–52 bps. The report must show measured one-way turnover (defined as 0.5·Σ|w_target − w_drifted| per rebalance, annualized — expect roughly 350–600% one-way p.a. for this design) and the implied annual cost drag in percent. If that drag is 3–5% p.a., that is the honest hurdle; do not bury it.

## 7. Accounting, benchmarks, metrics

- Daily NAV from adjusted closes; trade blotter with per-trade cost decomposition is a mandatory output (holdings file, trades file, monthly returns CSV, tearsheet).
- Benchmarks, all net where applicable: (a) NIFTY500 **TRI** — never the price index; (b) the equal-weight eligible-universe portfolio run through the *same* execution and cost engine — this is the structural benchmark, because a 20-stock EW portfolio drawn from a 500-name universe carries a large size tilt that the cap-weighted index comparison flatters; (c) NIFTY200 Momentum 30 TRI as an external anchor, and, for 2021+, live momentum index funds' actual NAVs as a reality check on achievable alpha.
- Metrics: net and gross CAGR, vol, Sharpe (91-day T-bill), max DD and DD duration, monthly hit rate, skew, worst month, beta/alpha vs NIFTY500 TRI, market-cap-bucket exposure over time, monthly Spearman rank IC of R6 vs next-month return, and a 4-factor regression (MKT/SMB/HML/WML, AJV India series) — report the alpha *after* WML loading, since "alpha" that is pure WML beta is expected, not interesting.

## 8. Control experiments (all mandatory before any conclusion)

- **C1 Survivorship A/B.** Run PIT membership vs today's-list-backfilled. Report the gap; it doubles as a data-pipeline test (gap should be material — if it's ~0, suspect the PIT join is broken).
- **C2 Cost ladder.** 0×, 0.5×, 1×, 2×, 3× the Section 6 costs. Feeds K4.
- **C3 Timing ladder.** Fill at T close (look-ahead diagnostic), E open, E close (base), E VWAP-proxy (mean of O/H/L/C), E+1 close, E+2 close. Alpha that decays steeply across E→E+2 is microstructure, not momentum. Feeds K6.
- **C4 Parameter plateau.** Grid: lookback {3,6,9,12} months × top-N {10,20,30,50} × skip-month {0,1}. Chosen config must sit on a plateau. Feeds K7.
- **C5 Rebalance-date jitter.** Shift signal/execution by +1…+10 trading days; also run four weekly-staggered quarter-size tranches. High dispersion = turn-of-month luck.
- **C6 Random-portfolio null.** 1,000 paths: each month draw 20 names uniformly from the *same* eligible universe, same execution and costs. Report the strategy's percentile on net Sharpe and net CAGR. This isolates selection skill from the EW/size effect. Feeds K5.
- **C7 Signal-sanity pair.** Bottom-20 portfolio (long losers) and the top-minus-bottom spread, gross. If longs-of-losers ≈ longs-of-winners, the ranking carries no information regardless of what the headline shows.
- **C8 Subperiods and concentration.** Fixed windows: 2015–17, 2018–19 (mid/small-cap bear), Feb–Apr 2020 (crash and momentum whipsaw), 2020–21, 2022, 2023–24 (small-cap mania), 2025–H1 2026. Also: cumulative excess PnL contribution of the top 10 stock-months, and best-rolling-12-month share of total excess. Feeds K8.
- **C9 Fragility of edge cases.** Rerun with (a) worst-case −100% on all suspended/delisted-for-cause positions at suspension date, (b) ASM/GSM filter off. Conclusions must not flip.
- **C10 Construction variants.** Rank-weighted, inverse-63-day-vol weighted, sector cap of 6 names, and a hold buffer (incumbents kept while ranked ≤ 40, refill from top). The buffer variant's turnover/cost/alpha trade-off must be tabulated — it is the likely production design.
- **C11 Capacity.** Rerun at ₹100 crore with the 10% MDTV participation cap and multi-day fills. Report % of target rebalance value unfilled within 3 days, and net alpha. (Arithmetic to keep in mind: ₹5 crore per name needs ₹50 crore MDTV for a one-day 10%-participation fill — the NIFTY500 tail fails this.)
- **C12 Holdout.** Development sample: Jan 2015–Jun 2023. The Jul 2023–Jun 2026 window is untouched until the config is frozen, then run **once**. Every configuration ever executed (including all of C2–C10) goes into a trial ledger; report a deflated Sharpe ratio using that trial count.

## 9. Kill criteria (any single trigger kills or voids; no renegotiation after the fact)

- **K1 (void)** PIT membership cannot be assembled per 2.3's validation gate. Do not run; a current-list backtest is not a result.
- **K2 (void)** Data gates G1–G4 fail. Fix data; all prior runs void.
- **K3** Full-sample net (1×-cost) excess CAGR vs NIFTY500 TRI < +3.0% p.a., or net Sharpe < benchmark Sharpe + 0.15.
- **K4** Net excess CAGR ≤ 0 at 2× costs.
- **K5** Net Sharpe below the 95th percentile of the C6 random-portfolio null, or below the EW-eligible-universe benchmark net Sharpe + 0.10 — either way it's the size/EW effect wearing a momentum costume.
- **K6** Moving fills from E close to E+2 close removes > 40% of gross excess return.
- **K7** Median excess CAGR over the neighbor grid {5,6,7 months} × {top 15, 20, 30} × {skip 0, 1} < 60% of the chosen config's excess.
- **K8** Top 10 stock-months > 35% of cumulative excess PnL, or any single rolling 12-month window > 70% of full-period excess.
- **K9** Holdout (C12): net excess return ≤ 0, or net Sharpe < 50% of the development-sample net Sharpe.
- **K10 (per-AUM kill)** At ₹100 crore, >15% of rebalance value unfilled within 3 days in more than 25% of months — the strategy may still pass at ₹10 crore, but the ₹100 crore claim dies.

Additionally, an investability flag (not a kill): if net max drawdown exceeds the benchmark's by more than 20 points while K3's margin is under +5% p.a., the risk isn't being paid for; say so in the report.

## 10. Process discipline

- This document is hashed and committed before the first run; the engine reads one YAML config that mirrors Section 0; a single command reproduces every table from a versioned data snapshot.
- Trial ledger: every executed configuration (parameters, git commit, data snapshot ID, headline stats) is appended automatically. The deflated-Sharpe calculation in C12 uses this ledger's count — no forgetting inconvenient runs.
- The holdout is opened once. If v1.0 dies, v1.1 requires a new hypothesis note stating what changed and why *before* rerunning, and the holdout result of v1.0 is reported alongside.
- Unit tests required before first run: CA adjustment on the G2 event list, PIT membership join (a stock that left the index must vanish from eligibility the correct month), circuit no-fill logic, and turnover/cost reconciliation (sum of blotter costs = NAV cost drag to the rupee).

Sanity check performed: re-read the ask — all six requested elements are covered concretely (data + PIT rules in §2, universe in §3, signal timing and execution convention in §4–5, cost model with India-specific statutory lines in §6, twelve control experiments in §8, ten numeric kill criteria in §9), with every parameter given an explicit value so a junior quant can implement without follow-up questions.

result: Delivered a frozen, implementable backtest spec for a NIFTY500 top-20 six-month momentum strategy (2015–2026): point-in-time data rules, ordered universe filters, T-signal/E-close execution with circuit-lock handling, an STT-dominated Indian cost model (~27–52 bps one-way), 12 mandatory control experiments, and 10 numeric kill criteria.

----- ANSWER G004 (task MG01) -----
# MG01: Monthly 6-Month Momentum Portfolio — Backtest Specification
**Version:** 1.0 | **Date:** 2026-07-12 | **Universe:** NIFTY500 | **Period:** 2015-2026 | **Rebalance:** Monthly | **Signal:** 6-month price return | **Positions:** Top-20 long-only  
**Status:** SPECIFICATION (not yet run) | **Gate-4 Lookahead Check:** PENDING

---

## 1. DATA REQUIREMENTS & POINT-IN-TIME RULES

### 1.1 Equity Price Data
**Source:** Angel SmartAPI (via getCandleData API) or HF daily candles (fallback)  
**Granularity:** Daily OHLCV (Open, High, Low, Close, Volume)  
**Timezone handling:** 
- All timestamps stored as **date only** (YYYY-MM-DD) in IST, since we use only daily closes.
- If pulling from HF (which stamps data 18:30 UTC = next-day 00:00 IST per D-030): convert via `pd.to_datetime().tz_convert('Asia/Kolkata').dt.date`, then discard time component.
- Angel getCandleData for ONE_DAY bars returns 00:00 IST timestamp; safe to extract date directly.

**Frequency:** Every trading day (NSE calendar, ~252/year; exclude bank holidays, market-wide circuit closures).

**Lookback window:** 
- For signal date T (e.g., last trading day of month M), compute 6-month return using closes on days T and T−126 (approximately 6 months; exact calendar days don't matter, use nearest 126 trading days).
- This means we need **T−126 to T** daily closes for each ticker (minimum 127 days of data per ticker in the lookback window).

**Missing data handling:**
- If a ticker has <10 consecutive missing closes in the 6-month window: interpolate linearly (liquid large-caps may have rare gaps).
- If a ticker has >10 consecutive missing closes: mark as **insufficient data** for that signal date, exclude from rebalance.
- Do NOT forward-fill to fill gaps (can introduce lookahead).

### 1.2 Universe Membership & Survivorship
**Source:** `NIFTY500_TICKER_2005_2025_Final.xlsx` (42 PIT snapshots per CLAUDE.md D-030)  
**Rule:** On rebalance date T, use NIFTY500 membership snapshot valid on or immediately before T (not after T).
- If T = 2020-06-30, use the NIFTY500 snapshot dated ≤2020-06-30 that is most recent.
- If a ticker was delisted before T, it is **not eligible** for the rebalance on T.
- If a ticker entered NIFTY500 on T, it is **not eligible** for the current rebalance (we don't have 6 months of prior data); it enters the pool at the next rebalance.

**Minimum history requirement:** A ticker must have continuous daily data from at least T−126 to T to be eligible for signal computation. If it joined NIFTY500 after T−126, use its actual listing date as the start and note the **lookback period is short** in the output; do not exclude it, but flag it.

### 1.3 Corporate Actions & Adjustments
**Splits, mergers, bankruptcy:**
- If a ticker underwent a stock split in the 6-month lookback window: adjust all historical prices (before split date) by the split ratio so that returns are continuous (e.g., 1-for-2 split: multiply old prices by 0.5).
- If a ticker merged or was delisted before T, exclude it from the rebalance.
- **Data source responsibility:** Angel SmartAPI and HF candle data should already be split-adjusted; verify by checking for >10% price jumps unrelated to dividends. If found, manually adjust or flag the period.

**Dividends:** Do NOT adjust prices for dividends; use **price return only** (not total return). This matches Angel SmartAPI behavior and is standard for momentum (dividends inflate return estimates for value stocks, which would bias towards financials).

---

## 2. UNIVERSE CONSTRUCTION

### 2.1 Membership Filter
On each rebalance date T (last trading day of months Jan, Feb, Mar, ..., Dec):
1. Fetch the valid NIFTY500 membership snapshot ≤T.
2. Count of eligible tickers: typically ~500, but reduce to those with **full 6-month history and no lookahead data issues** (see §3.4).

### 2.2 Liquidity & Execution Filter
On rebalance date T, apply in order:
1. **Volume filter:** Ticker's 20-day avg volume (T−20 to T) ≥ ₹2 Cr/day. 
   - Rationale: We will simulate order execution; <₹2Cr is too thin and will incur >3x slippage (COST_STANDARDS.md).
   - If volume is below threshold, mark as illiquid; set return to NaN for this rebalance (exclude from ranking).

2. **Price filter:** Closing price on T ≥ ₹5. 
   - Rationale: Near-penny stocks are shell companies or highly distressed; exclude them.

3. **Data quality filter:** 
   - Closing price on T must be strictly positive (>0).
   - If CLOSE = 0 or CLOSE = NaN, mark as stale/delisted and exclude.

### 2.3 Post-Filter Count
After applying §2.1 and §2.2, document the count of eligible tickers. If <20, **cancel the rebalance for that month** (insufficient universe width). Do NOT rank and pick <20; wait for the next month.

---

## 3. SIGNAL TIMING & EXECUTION CONVENTION

### 3.1 Signal Computation Date
**Rebalance monthly on the last trading day of each month** (e.g., 2015-01-30, 2015-02-27, 2015-03-31, ..., 2026-12-31).

**Signal definition — 6-month return:**
```
Return_6M(T) = (Close[T] - Close[T-126]) / Close[T-126]
```
where T = rebalance date, T−126 ≈ 6 calendar months prior (126 trading days ≈ 6 months).

**Edge case — insufficient history at start:**
- For dates 2015-01-30 to ~2015-07-31 (first 7 months), we don't have 6 months of prior data. 
  - **Option A (chosen):** Use a **rolling lookback window** — for T in the first 6 months, compute return from T's actual earliest available data (after 2015-01-02) to T. Flag this in output as "short lookback". This allows backtesting to start earlier and find enough signal strength.
  - **Option B (conservative):** Start backtesting only after 2015-07-31 (first full 6-month window). 
  - **Decision for this spec:** Use Option A (rolling early lookback); document lookback length for each early month. This is not lookahead (we're not using future data), just a shorter history.

### 3.2 Ranking & Selection
On each rebalance date T:
1. Compute 6-month return for all eligible tickers (post-filter).
2. Rank by 6-month return, descending (highest return = rank 1).
3. **Select top 20 tickers** (ranks 1–20).
4. If fewer than 20 eligible tickers exist (post-filter), **cancel rebalance** (hold previous portfolio or go to cash; see §3.5).

### 3.3 Portfolio Construction
**Position sizing:** Equal weight, 5% per position (20 × 5% = 100% invested).

**Rebalancing rule:**
- On each rebalance date T, liquidate all positions not in the new top-20.
- Enter/scale to 5% in each of the new top-20.
- Cost: trading costs apply to all sells (old positions) and all buys (new positions). See §4.

### 3.4 Trade Execution Timing & Lookahead Prevention
**Execution window:** 
- Rebalance decisions are computed using close-of-day data on T (the last trading day of month M).
- Execution occurs at the **opening** on T+1 (first trading day of month M+1).
- We use the **opening price on T+1** for entry/exit execution (not close; this is more realistic for end-of-day signals arriving after market close).

**Rationale for T+1 open execution:** Momentum signals computed at close on T are stale 16+ hours by open on T+1. Open on T+1 is the earliest realistic execution (Principal's "no lookahead" rule D-028).

**Lookahead prevention:**
- Signal date: T (last trading day of month M, close of day).
- Execution date: T+1 (open of day, first trading day of month M+1).
- Return lookback for signal: uses T−126 to T (all data ≤T).
- Cost model uses prices on T+1 (entry/exit on open of T+1; we do not know intraday T+1 prices at time of signal, so we use open as a proxy).
- **No price information from T+1 is used in the signal itself** — signal is locked in at T close.

### 3.5 Edge Case: Insufficient Tickers After Filter
If after applying §2.2 filters, <20 tickers remain eligible:
- Do NOT execute a rebalance.
- Hold the current portfolio unchanged for one more month.
- Re-assess membership/filters at the next rebalance date (T+21 days).
- Document this in the backtest log with the count of tickers eliminated at each filter stage.

---

## 4. COST MODEL

### 4.1 Data Source
**Use:** `Shreyas_Ionic_AMC/06_TRADING_DESK/COST_STANDARDS.md` when it is CEO + CIO approved. Until approval, use **conservative defaults** (below).

### 4.2 Transaction Costs
**Slippage model (entry & exit):**
- Base slippage: 0.08% (8 bps) for liquid large-cap tickers (20-day avg volume ≥ ₹20 Cr/day).
- Scaled slippage for medium-cap: 0.10% (10 bps) for ₹2–₹20 Cr/day volume.
- Scaled slippage for thin: 0.15% (15 bps) for <₹2 Cr/day (excluded from universe anyway).
- **Application:** For each rebalance, we sell out of old positions and buy into new positions. 
  - Cost to exit a position: `slippage × position_size × exit_price`.
  - Cost to enter a new position: `slippage × position_size × entry_price`.

**Brokerage:**
- Flat ₹20 per leg traded (entry or exit).
- Negligible for large orders; captured separately for realism.

**Turnover cap:** After cost, if turnover on a rebalance date >90%, log a warning (sign of over-sensitive signal or high universe churn); do NOT skip the rebalance, but flag it.

### 4.3 Other Costs (Ignored)
- Exchange fees, stamps duty, etc.: <0.5 bps combined, negligible.
- Short-sale borrowing: not applicable (long-only).
- Margin/leverage: none (100% on equity).

### 4.4 Cost Deduction Timing
- Costs deducted from gross P&L at the time of execution (T+1 open).
- Cost is explicit in the ledger: `Net_Return = Gross_Return − Slippage − Brokerage`.

---

## 5. BACKTEST MECHANICS & OUTPUTS

### 5.1 Ledger Structure
For each rebalance date T, produce a row in the results table:

| Date | Count_Eligible | Top_20_Tickers | Turnover (%) | Entry_Slippage | Entry_Brokerage | Exit_Slippage | Exit_Brokerage | Net_Cash_After_Rebalance | Total_Value_After_Rebalance |
|------|---|---|---|---|---|---|---|---|---|
| 2015-01-30 | 450 | AAPL, ... | 15.2 | -450 | -40 | -2100 | -40 | 97370 | 100000 |

**Definitions:**
- **Count_Eligible:** # tickers passing §2.2 filters.
- **Top_20_Tickers:** Comma-sep list of 20 tickers selected (for audit trail).
- **Turnover (%):** Dollar value of sells + buys / portfolio value at start of rebalance (× 100%).
- **Entry_Slippage, Entry_Brokerage:** Costs incurred entering new positions.
- **Exit_Slippage, Exit_Brokerage:** Costs incurred exiting old positions.
- **Net_Cash_After_Rebalance:** Cash left over (should be ~0 if we rebalance to 100% invested; track rounding errors).
- **Total_Value_After_Rebalance:** Portfolio value immediately after execution (before any P&L).

### 5.2 Daily P&L Tracking
Between rebalances (T+1 to T+1_next_rebalance):
- For each day, compute mark-to-market P&L as: `sum(position_size × daily_return)` across all 20 holdings.
- Accumulate daily NAV: `NAV[t] = NAV[t-1] × (1 + daily_return)`.
- Do NOT rebalance intra-month, even if a position has extreme moves.

### 5.3 Return Metrics & Reporting
Compute for the full backtest (2015-01-30 to 2026-12-31):

1. **Total Return (%):** (Final NAV − Initial NAV) / Initial NAV × 100.
2. **CAGR (%):** ((Final NAV / Initial NAV) ^ (1 / N_years) − 1) × 100, where N_years = 11.92 (2015-01-30 to 2026-12-31 ≈ 11 years 11 months).
3. **Max Drawdown (%):** Largest peak-to-trough decline from any high-water mark.
4. **Volatility (annualized %):** Std dev of daily returns × sqrt(252).
5. **Sharpe Ratio:** (CAGR − 4%) / Volatility (using 4% as a risk-free rate proxy).
6. **Calmar Ratio:** CAGR / Max Drawdown (in absolute terms, e.g., 15% / 0.35 = 0.43).
7. **Win Rate (%):** # of months with positive returns / total months.
8. **Average Monthly Return (%):** Mean of all monthly P&L.
9. **Worst Month (%):** Minimum monthly return.
10. **Best Month (%):** Maximum monthly return.
11. **# Rebalances:** Count of non-cancelled rebalances.
12. **Avg Turnover (%):** Mean turnover across all rebalances.
13. **Total Transaction Costs (₹):** Sum of all slippage + brokerage.

Output as a summary table + time-series plot (NAV curve over time).

---

## 6. CONTROL EXPERIMENTS (KILL CRITERIA)

A strategy with this signal/universe **must pass all of the following** before we trust it:

### 6.1 Lookahead Test (D-028 / §1.4 mandatory)
**Experiment:** Run the same backtest, but delay signal **by 1 calendar day** after the close on T:
- Compute signal using close data up to T−126 to T.
- Delay execution to T+2 (instead of T+1).
- This creates a "signal-to-execution" gap and detects if we are accidentally using T+1 data in the signal (classic lookahead bug).
- **Kill criterion:** If delayed backtest **significantly outperforms** (>200 bps annualized CAGR gain), we have a lookahead leak. Reject and fix.
- **Expected:** Delayed backtest should have only minor differences due to overnight gap changes; CAGR should decline by <50 bps (less 1-day opportunity cost).

### 6.2 Subperiod Stability Test
**Experiment:** Run the backtest in three non-overlapping windows:
1. 2015-01-30 to 2018-12-31 (Period A: ~4 years, pre-demonetization aftermath).
2. 2019-01-31 to 2022-12-30 (Period B: ~4 years, COVID + taper tantrum).
3. 2023-01-31 to 2026-12-31 (Period C: ~4 years, recent regime).

**Metrics per subperiod:**
- CAGR, Max Drawdown, Sharpe Ratio, Win Rate.

**Kill criterion:** 
- If any subperiod has **negative CAGR**, the strategy is fragile (not robust to regime change). Investigate and kill.
- If Sharpe ratios vary by >2x across periods (e.g., 0.8 vs 1.8), the strategy is regime-dependent and unreliable. Do not trade.

### 6.3 Subsampling Test (Overfit Detection per D-030)
**Experiment:** 
1. Randomly remove 10% of trading days from the signal lookback window (T−126 to T).
2. Recompute returns on the remaining 90% of days and re-rank.
3. Repeat 100 times (Monte Carlo).
4. Compute robust return = median of 100 runs.
5. Compare robust return vs. original: if difference >200 bps CAGR, the edge is fragile (relying on 1-2 outlier days).

**Kill criterion:** If robust return drops by >1% CAGR (annualized), the signal overfits on outlier dates. Reject.

### 6.4 Parameter Sensitivity / Perturbation Test
**Experiment:** Vary the lookback window:
- 5-month return (instead of 6-month).
- 7-month return (instead of 6-month).
- Compute CAGR and Sharpe for each variation.

**Kill criterion:** If CAGR or Sharpe swing by >150 bps CAGR across ±1-month lookback, the momentum window is brittle. The 6-month window may be a local optimum (data-mining artifact).

### 6.5 Top-N Position Count Sensitivity
**Experiment:** Run the same backtest with different position counts:
- Top-10 (10% each).
- Top-20 (5% each, original).
- Top-30 (3.33% each).

**Metric:** CAGR and Sharpe for each.

**Kill criterion:** If Top-10 significantly outperforms Top-20 (>300 bps CAGR), the edge is concentrated in the top 10; concentration risk is high. 
If Top-30 outperforms Top-20 (>200 bps CAGR), we are picking noise (worse names have better 6-month returns). This is a sign of market mean reversion (anti-momentum), not edge.

### 6.6 Bull vs. Bear Market Split
**Experiment:** 
- Identify bull and bear market regimes using NIFTY50 index (e.g., bull = 20-month high; bear = 20-month low, or use SPY-equivalent).
- Compute strategy CAGR and Sharpe separately for bull and bear phases.

**Kill criterion:** 
- If strategy only works in bulls (CAGR > 0 in bull, CAGR < -5% in bear), it is a beta carry (not alpha). Reject.
- If it only works in bears (negative beta hedge), it may have merit for diversification, but label it accordingly.

### 6.7 Transaction Cost Sensitivity
**Experiment:** Run backtest with 2x cost assumptions (double slippage + brokerage).

**Kill criterion:** If CAGR drops by >300 bps with doubled costs, the edge is too small relative to execution friction. Reject.

### 6.8 Universe Membership Survivorship Bias Test
**Experiment:** 
- Run backtest using **current (2026) NIFTY500 membership** for the entire period (2015-2026), treating all 500 as "always" in the index.
- Compare CAGR to the PIT-adjusted backtest (§2.1).

**Kill criterion:** If survivorship-bias version has CAGR >500 bps higher than PIT version, the strategy is selecting winners-in-hindsight (dead tickers are excluded; we never held them and thus don't see their -100% returns). This is a massive lookahead trap. Reject and fix.

### 6.9 Information Ratio vs. Benchmark
**Experiment:** 
- Compute benchmark: NIFTY500 equal-weight monthly rebalance (same mechanics, but all 500 names post-filter, not top-20).
- Compute strategy's excess return (strategy CAGR − benchmark CAGR).
- Information Ratio = excess return / tracking error (volatility of strategy − benchmark).

**Kill criterion:** If Information Ratio < 0.3, the strategy's outperformance is not statistically significant (less than 0.3 is noise; >0.5 is interesting; >0.8 is strong). 

### 6.10 Forward-Test Freeze (D-030)
**Experiment:** 
- Once spec is locked and backtest is run, **do not tune parameters**.
- If you want to test a different lookback window or position count, that is a **new strategy version** with a new forward-test clock (old results stand untouched).

**Kill criterion:** Any post-hoc tuning to improve backtest result is a red flag (overfitting). Document the original run date and hash.

---

## 7. EXPECTED OUTPUTS & DELIVERABLES

### 7.1 Backtest Report
**Location:** `Shreyas_Ionic_AMC/04_RND_LAB/SYSTEM_SCIENCE_PROGRAM/MODEL_GRID/results/MG01_backtest_report.md`

**Contents:**
1. Summary metrics table (§5.3).
2. Daily NAV curve (plot).
3. Monthly P&L distribution (histogram).
4. Drawdown curve (plot).
5. Top 20 tickers selected in each rebalance (audit trail, 144 rebalances × 20 = 2880 entries; summarize by frequency).
6. Rebalance log (date, count_eligible, turnover, costs) — table form.
7. Lookahead test result (§6.1) — PASS/FAIL.
8. Subperiod stability (§6.2) — table of metrics per period.
9. Subsampling robustness (§6.3) — plot of robust return distribution.
10. Parameter sensitivity (§6.4) — CAGR vs. lookback window.
11. Position count sensitivity (§6.5) — CAGR vs. top-N.
12. Bull/bear split (§6.6) — returns in each regime.
13. Cost sensitivity (§6.7) — CAGR at 1x and 2x costs.
14. Survivorship bias check (§6.8) — PIT vs. full-history result.
15. Information Ratio vs. equal-weight NIFTY500 (§6.9).
16. **Kill Decision:** PASS (ready for paper trading) / FAIL (reject, reasons listed) / CONDITIONAL (pass if conditions met, e.g., "only long equities, not shorts").

### 7.2 Ledger File (CSV)
**Location:** `Shreyas_Ionic_AMC/04_RND_LAB/SYSTEM_SCIENCE_PROGRAM/MODEL_GRID/results/MG01_ledger.csv`

**Columns:** Date, Count_Eligible, Top_20_Tickers (semicolon-sep), Turnover_pct, Slippage_Entry, Brokerage_Entry, Slippage_Exit, Brokerage_Exit, Net_Cash, Portfolio_Value

### 7.3 Signal Data (for audit)
**Location:** `Shreyas_Ionic_AMC/04_RND_LAB/SYSTEM_SCIENCE_PROGRAM/MODEL_GRID/results/MG01_signals.csv`

**Columns:** Date, Ticker, Lookback_Days, Return_6M_pct, Rank, Selected_YN, Liquidity_Flag

---

## 8. IMPLEMENTATION CHECKLIST FOR JUNIOR QUANT

Before coding:
- [ ] Confirm NIFTY500 PIT snapshot file is available (`NIFTY500_TICKER_2005_2025_Final.xlsx`).
- [ ] Confirm daily OHLCV data source is set (Angel SmartAPI or HF fallback).
- [ ] Understand timezone handling (IST, 00:00 timestamp, §1.1).
- [ ] Understand T+1 open execution (no lookahead; §3.4).
- [ ] Understand rollfwd 6-month window for months 1–6 of backtest (§3.1).

Implementation steps:
1. Ingest daily OHLCV for all NIFTY500 tickers, 2015-01-02 to 2026-12-31.
2. Ingest NIFTY500 membership snapshots and map dates to membership.
3. For each rebalance date T (last trading day of each month):
   a. Filter to eligible tickers (§2.1, §2.2).
   b. Compute 6-month return for each (§3.1).
   c. Rank, select top-20 (§3.2).
   d. Simulate execution at T+1 open (§3.3, §3.4).
   e. Deduct costs (§4).
   f. Log rebalance details (ledger, §5.1).
4. For each day T+1 to next rebalance, compute daily P&L and NAV (§5.2).
5. Compute summary metrics (§5.3).
6. Run all control experiments (§6) and produce kill-decision (§7.1).

---

## 9. NOTES ON INDIA-SPECIFIC EDGE CASES

1. **NSE trading halts:** Some days are bank holidays (e.g., Independence Day, Diwali). Exclude these from the 126-day lookback and from daily P&L tracking. Use NSE calendar.
2. **Circuit limits:** If a stock hits an upper or lower circuit on a given day, it may not trade. In the backtest, assume we CAN liquidate at the circuit price on the next day. This is conservative (real execution might be worse). Do NOT assume a halt = forced holding.
3. **Budget limits:** If ₹5L rebalance costs are incurred, document this explicitly in the rebalance log.
4. **Earnings season:** Avoid earnings-related lookahead by not using earnings-adjusted pricing. Use raw closes (§1.3).

---

## 10. FINAL GATE CRITERIA (before paper trading or live)

- [ ] All control experiments pass (§6).
- [ ] Lookahead test passes (§6.1) — no future-data leakage.
- [ ] Subperiod stability test passes (§6.2) — robust across 2015–2026.
- [ ] Subsampling robustness test passes (§6.3) — edge does not rely on 1–2 outlier days.
- [ ] Information Ratio ≥0.3 (§6.9) — outperformance is not noise.
- [ ] Backtest report signed off by CIO + quant-head (Arjun Rao).
- [ ] Red team review passes (Nikhil Bose, §6 adversarial).
- [ ] TCA report approved (Tara Singh, §4 cost assumptions valid).
- [ ] **DECISION LOG entry:** Recorded in `Shreyas_Ionic_AMC/01_COMMAND_CENTER/DECISIONS_LOG.md` (date, decision, approver, reason).

---

**END OF SPECIFICATION**

**To implement:** Copy this file to your work directory, check off items in §8 as you code, run the backtest, produce outputs to §7 locations, and report results to this spec's §8 checklist. On completion, run the control experiments (§6) and produce the kill-decision (§7.1 item 16). Only then submit for CIO + quant-head approval.

----- ANSWER G007 (task MG01) -----
# MG01 — Backtest Specification: Monthly Momentum, Top-20 / 6-Month Return, NIFTY500, 2015–2026

**Status:** SPECIFICATION ONLY (design, not a run). Implementable by a junior quant without follow-up questions.
**Author model:** Opus 4.8 (MODEL_GRID cell MG01).
**Scope of edge under test:** cross-sectional price momentum in Indian large/mid/small caps, monthly rebalance.

---

## 0. One-paragraph statement of the experiment

Each month, on a fixed rebalance date, rank every eligible NIFTY500 constituent by its trailing 6-month total return (measured with a skip so the most recent bar is not used for the signal), buy the top 20 equal-weight, hold one month, repeat. The null hypothesis is that after realistic costs, survivorship-correct universe membership, and point-in-time signal construction, this portfolio delivers **zero** risk-adjusted excess return over the equal-weight NIFTX500 buy-and-hold. We only "believe" a positive result if it survives the full control battery in §8 and none of the kill criteria in §9 fire.

---

## 1. Data requirements and point-in-time (PIT) rules

### 1.1 Price data
- **Instrument set:** daily OHLCV for every stock that was ever a NIFTY500 member 2014-07 → 2026-06 (start signal lookback needs 6M + skip before first 2015 rebalance, so data must begin **2014-06-01**).
- **Granularity:** ONE_DAY bars only. No intraday needed for this design.
- **Adjustment:** two parallel series are mandatory and MUST NOT be conflated:
  1. **Total-return-adjusted close** (`adj_close`) — adjusted for splits, bonuses, dividends, rights, face-value changes. Used ONLY for signal (return) computation and for P&L on held positions.
  2. **Raw traded price** (`open`, `high`, `low`, `close`, unadjusted) — used ONLY for the execution price and for circuit/liquidity gating on the trade day.
  - Rationale: computing signal on raw prices injects fake jumps on ex-dates; executing at adjusted prices fabricates fills at prices that never traded. Keep them separate.
- **Corporate-action table:** dated split/bonus/dividend/rights factors with **ex-date**. Adjustment factors applied only to bars strictly *before* ex-date (PIT: on 2015-03-10 you must not know the 2015-06 bonus).
- **Volume + delivery:** daily traded volume and, if available, delivery quantity (for the liquidity screen and impact model). Store traded value (₹) = volume × VWAP or × close as fallback.
- **Circuit band:** per-stock daily price band (2%/5%/10%/20% / no-band) and the upper/lower circuit prices, OR reconstruct from `high==low==prev_close×(1±band)`. Needed for the no-fill-on-locked-circuit rule.

### 1.2 Universe membership (survivorship)
- **Source of truth:** `NIFTY500_TICKER_2005_2025_Final.xlsx` — 42 PIT constituent snapshots (per CLAUDE.md landmine #6). Extend past 2025 with NSE semi-annual reconstitution circulars for the 2025-09, 2026-03 rebalances.
- **PIT rule:** on rebalance date *t*, the eligible universe = the constituent set from the **most recent snapshot with effective date ≤ t**. Never the current (2026) NIFTY500 — that is the single largest source of fake momentum alpha (dropped names are gone, added winners appear retroactively).
- **Reconstitution handling:** NIFTY500 reshuffles semi-annually (effective late Mar / late Sep). A stock added at reconstitution enters the eligible set only from its effective date; a removed stock leaves the eligible set on removal but any *open position* in it is handled per §5.4 (do not silently teleport it out).

### 1.3 Delisting / suspension / corporate-death handling
- Every ticker in the historical universe must carry a **last-trading-date** and a **delist reason** (merger, acquisition, bankruptcy, voluntary, suspension). This table is mandatory; without it the backtest is survivorship-biased even with PIT membership, because a held stock that goes to zero must realize that loss.
- **PIT rule:** if a held name stops trading mid-hold, mark it per §5.4. Do not carry forward the last price as if liquid.

### 1.4 Benchmark data
- **Equal-weight NIFTY500 total-return** (primary benchmark — matches the portfolio's implicit equal weighting).
- **Cap-weight NIFTY500 TRI** and **NIFTY500 Momentum 50 TRI** (the published factor index) as secondary references. The published momentum index is the "is our replication even in the right direction" sanity check, not the benchmark to beat.
- **Risk-free:** daily 91-day T-bill / MIBOR series for Sharpe and for the cash leg on unfilled capital.

### 1.5 Data-quality gates (run BEFORE any backtest; hard-block on failure)
- No `adj_close ≤ 0`, no `NaN` inside a listed-and-trading window.
- Monotonic ascending dates, no duplicate (ticker, date).
- Spot-check ≥10 known corporate actions (e.g., a large split) resolve to smooth `adj_close`.
- Cross-check 5 random (ticker, date) closes against an independent source (Angel / NSE bhavcopy).
- Every held-eligible ticker resolves to a row in the delist table (even if "still listed 2026-06").
- Log a coverage report: for each rebalance date, count eligible names with complete 6M+skip history; if <400 of the ~500, investigate before trusting that month.

---

## 2. Universe construction (per rebalance date *t*)

Start from the PIT NIFTY500 membership (§1.2), then apply, in order:

1. **Listing age:** stock must have ≥ (126 + skip) trading days of history ending at the signal-observation bar (see §3). New listings without enough history are excluded, not zero-filled.
2. **Trading liquidity screen (PIT, no lookahead):** median daily traded value over the trailing 21 trading days (ending at the signal bar) ≥ **₹5 crore**. Rationale: top-20 equal-weight of a ₹10L–₹10cr book (D-031 capacity band) must be tradeable with limit-or-skip; illiquid microcaps are where fake momentum alpha concentrates. Record the screen; run a sensitivity at ₹2cr and ₹10cr (§8).
3. **Price floor:** raw close ≥ ₹10 on the signal bar (penny-stock / bad-tick guard).
4. **Not currently suspended / not in trade-to-trade (T2T/BE) segment** on the signal bar if that flag is available (T2T segment forbids intraday and caps fills).
5. **Circuit health:** exclude names that were circuit-locked on ≥ 5 of the trailing 21 days (chronically locked = un-exitable).

Resulting set = the **investable universe** for month *t*. Log its size each month.

---

## 3. Signal definition and timing

### 3.1 Calendar
- **Rebalance frequency:** monthly.
- **Rebalance date (RD):** the **last trading day of each calendar month** (use the exchange trading calendar, not calendar month-end; handle holidays). First RD = 2015-01-30 (or first month-end with full lookback), last RD = 2026-05-29 (or latest complete month), giving ~136 rebalances.
- **Signal-observation bar (SB):** the same last-trading-day close, i.e., signal is computed on data available *as of the RD close*.

### 3.2 Momentum signal (the "6-month return")
- **Formula:** `mom_i = adj_close[SB - skip] / adj_close[SB - skip - 126] - 1`
  - `126` trading days ≈ 6 months.
  - **skip = 21 trading days** (skip the most recent ~1 month) — standard 12-1 / 6-1 construction to avoid short-term reversal contamination. **This is a design parameter; the primary run uses skip=21, but skip∈{0,21} MUST both be reported** (skip=0 = raw 6M return; if the edge only exists at skip=0 it is likely short-term reversal/microstructure, not momentum).
  - Use `adj_close` (total-return) exclusively for this ratio.
- **Eligibility for ranking:** both `adj_close[SB-skip]` and `adj_close[SB-skip-126]` must exist and be from bars where the stock actually traded (not carried-forward). Missing → excluded from ranking that month.

### 3.3 Ranking and selection
- Rank the investable universe by `mom_i` descending. Select the **top 20**.
- **Tie-break:** higher 21-day median traded value first (prefer liquidity), then alphabetical ISIN for determinism.
- **Weighting:** equal-weight, 5% each (1/20). No volatility scaling, no signal-tilt in the primary spec (those are separate experiments, not this one).

### 3.4 The critical timing rule (lookahead firewall)
- Signal is observed at **RD close (SB)**.
- Trades are executed on the **next trading day (RD+1)** — you cannot trade on a close you are simultaneously using to rank. (Executing at the RD close is a lookahead: it assumes you knew the ranking before the market closed.)
- Concretely: rank at RD close → generate target book overnight → execute RD+1.
- **Mandatory one-day-lag audit (D-028 / T1–T10):** re-run the entire backtest with signal observation and execution BOTH pushed one extra day. Alpha must degrade *gracefully*, not collapse. A strategy that only works when execution == signal bar is a lookahead artifact and is killed (§9).

---

## 4. Portfolio construction

- **Book size:** notional ₹1 crore (mid of the D-031 ₹10L–₹10cr band). Fully invested target = 100% across 20 names, 5% each.
- **Cash leg:** any unfilled/unspent capital (from skips, circuit no-fills, odd-lot rounding) earns the daily risk-free rate.
- **No leverage, long-only, no shorting** (cash equity, delivery segment).
- **Rounding:** target shares = floor(0.05 × book / raw_open_RD+1). Residual cash to the cash leg. Track odd-lot drag.
- **Rebalance turnover:** compute the name-level and value-level turnover each month (names dropped/added, ₹ traded / book). Expected ~60–90% one-way monthly turnover for 6-1 momentum — this is the cost engine and must be reported, not hidden.

---

## 5. Execution convention

### 5.1 Fill price
- **Primary:** execute at the **RD+1 open** (raw, unadjusted). Justification: the signal is known before the open; the open is the first tradeable price. Do NOT use RD+1 VWAP as primary (VWAP assumes perfect participation across the day = optimistic).
- **Secondary robustness run:** execute at RD+1 VWAP and at RD+1 close; report the spread of results. If the edge exists only at the open, suspect open-auction / gap artifacts.
- **Pre-open auction guard (landmine #2):** for daily bars this is less acute, but confirm the "open" used is the regular-session open, not a stale/auction print.

### 5.2 No-fill rules (mandatory — D-031 limit-or-skip)
- **Circuit-locked at open:** if RD+1 opens at the upper circuit for a BUY (or lower circuit for a SELL) and stays locked, **no fill — skip the name** for that leg; do not assume a fill at the locked price. Roll the intended trade to the next day for up to 3 trading days; if still unfillable, drop the buy (allocate to cash) or hold the sell (carry the position).
- **Zero/near-zero volume:** if RD+1 traded volume < intended order size / participation cap, fill only the fillable fraction (see §6 impact); remainder rolls or drops.
- **Suspended/halted:** no fill; carry per §5.4.

### 5.3 Participation cap
- Single-day order ≤ **10% of that day's traded volume** in the name. If the target position exceeds 10% ADV, spread over consecutive days (record the multi-day fill) or cap the position. At ₹1cr book / 20 names (₹5L per name) against a ₹5cr+ ADV screen this rarely binds, but it MUST be enforced so results survive a book-size sensitivity (§8).

### 5.4 Held-name corporate events during the hold
- **Delist/bankruptcy:** realize the position at the last reliable traded price; if the reason is liquidation-to-zero, mark to **₹0** (or the actual delisting/settlement value if known). Never carry the last quote as recoverable.
- **Merger/acquisition:** convert at the announced ratio / cash terms on the effective date.
- **Suspension mid-hold:** freeze at last trade; attempt exit at each subsequent rebalance; if it resumes at a gap, take the gap.
- **Removed from NIFTX500 at reconstitution while held:** you may continue to hold until the next monthly rebalance decides its fate by signal (do not force-sell on index removal — that is an artifact of the index, not the strategy). Document this choice; run the alternative (force-sell on removal) as a sensitivity.

### 5.5 Sequencing at each rebalance
Sells first (free up capital) → then buys with realized cash. Both at RD+1 prices. Names in both old and new top-20 are held (no round-trip cost on the overlap — only trade the delta to re-equal-weight; report whether you re-balance overlaps to exact 5% or let them drift, primary = re-balance to 5%).

---

## 6. Cost model

Costs are applied on **every share traded** (buys and sells, including partial fills and re-weighting deltas). Use ONLY approved `06_TRADING_DESK/COST_STANDARDS.md` values once user-approved; until then this is DRAFT and results are marked provisional.

### 6.1 Explicit fixed/statutory costs (Indian cash-equity delivery, per leg unless noted)
- **Brokerage:** ₹0 (discount broker delivery) OR 0.03% — use the COST_STANDARDS value; do not invent. Model both bull/bear on brokerage in sensitivity.
- **STT:** 0.1% on buy + 0.1% on sell (delivery equity), on traded value.
- **Exchange transaction charge:** ~0.00297% (NSE) on traded value.
- **SEBI turnover fee:** 0.0001%.
- **Stamp duty:** 0.015% on buy side only.
- **GST:** 18% on (brokerage + exchange txn charge).
- **DP charges:** flat per-sell-scrip (~₹13–20) — include, it matters for a 20-name monthly book.

### 6.2 Impact / slippage (the part that kills naive momentum backtests — landmine #7b)
- **Base slippage:** half the modeled bid-ask spread. Model spread as a function of the name's liquidity bucket (by 21-day ADV): large-cap ~2 bps, mid ~5–8 bps, small ~15–25 bps half-spread. Use `lib/execution_realism.py` if available.
- **Dynamic component:** slippage scales 2–3× on thin-volume days and on the exact signal/rebalance day (momentum names are often already gapping on the day they qualify — buying strength costs more). Model impact ≈ `k × (order_size / ADV)^0.5` with k calibrated per COST_STANDARDS; floor at base slippage.
- **Gap-on-entry realism:** because top-20 momentum names frequently gap up at the RD+1 open on the signal, the primary run's open-fill already embeds some of this; do NOT additionally assume you buy at the prior close.

### 6.3 Cost reporting
- Report gross return, net return, and the full cost decomposition (statutory vs impact) as a % of book/yr. Momentum at ~70% monthly turnover pays a large impact bill; if net alpha is a small residual of two large numbers (gross − costs), flag it as fragile.

---

## 7. Accounting, metrics, and outputs

### 7.1 Daily NAV
- Mark the book daily at `adj_close` for held names (dividends already in adj_close; do not double-count) + cash leg accrual. Costs hit NAV on the fill day.
- Build a daily NAV series 2015→2026 for the strategy and for each benchmark.

### 7.2 Metrics (all net of costs, report gross alongside)
- CAGR, annualized vol, **Sharpe** (vs T-bill), **Sortino**, max drawdown + drawdown duration, Calmar.
- **Alpha & beta** vs equal-weight NIFTX500 (primary) and cap-weight NIFTX500 (regression of monthly excess returns; report t-stat of alpha).
- Monthly and annual return table; hit rate (% up months), best/worst month.
- **Turnover** (annualized), average holding period, average names traded/month.
- **Capacity note** (RP-14 style): at what book size does modeled impact eat >50% of gross alpha.
- Per-year attribution: is the whole edge from 1–2 years (e.g., 2017, 2021 momentum blow-offs)?

### 7.3 Deliverable format
- Internal: this spec + a results `.md` book + NAV/trade CSVs.
- Principal-facing (if it survives): Word doc with equity curve, drawdown chart, annual table, cost decomposition (per firm rule 4; never a bare .md pointer).

---

## 8. Control experiments demanded BEFORE believing any result

No positive result is reported, logged to the register, or shown to the Principal until ALL of these are run and pass. Each is a specific, falsifiable check.

1. **One-day-lag test (lookahead firewall).** Push signal+execution one extra day. Alpha must survive with graceful (not cliff) degradation. Cliff → lookahead artifact → KILL.
2. **Survivorship A/B.** Run once with PIT membership (§1.2) and once with the *current* NIFTY500. The current-universe run WILL look better; quantify the gap. If PIT-net-alpha ≤ 0 while current-universe looks great, the "edge" was survivorship — KILL.
3. **Delisting-inclusion test.** Run with the delist/bankruptcy table ON vs a naive version that drops dead names silently. The gap is the survivorship-of-losers bias. Report it; PIT+delist is the only believable number.
4. **Cost-sweep.** Re-run at 0.5×, 1×, 2×, 3× the modeled impact/slippage. Momentum must stay net-positive at ≥2× to be robust (it is turnover-heavy). Also toggle brokerage 0 vs 0.03%.
5. **Skip-parameter test.** skip ∈ {0, 21}. If alpha exists ONLY at skip=0, it is short-term reversal/microstructure, not 6-month momentum — reclassify or KILL as "not the stated edge."
6. **Lookback robustness.** Recompute with lookback ∈ {105, 126, 147} days and top-N ∈ {15, 20, 25, 30}. A real factor is a plateau, not a spike. A result that only works at exactly 126/top-20 is overfit (report the parameter surface; hand to §sensitivity / Dr. Bhat for DSR/PBO).
7. **Execution-price robustness.** Fill at open vs VWAP vs close. Large divergence (esp. open ≫ VWAP/close) = gap/auction artifact.
8. **Liquidity-screen sensitivity.** ADV floor ∈ {₹2cr, ₹5cr, ₹10cr}. If the edge lives only in the ₹2cr bucket, it is illiquid-microcap alpha that dies on impact at any real size — capacity KILL.
9. **Sub-period / regime split.** Split 2015–2019, 2020–2022, 2023–2026. Report per-regime Sharpe. Also mark 2018 (mid/small-cap crash) and Mar-2020 explicitly — momentum crashes on sharp reversals; the drawdown must be honestly shown, not smoothed.
10. **Benchmark honesty.** Compare to equal-weight NIFTX500 (matches the weighting), not just cap-weight. Much of naive "momentum alpha" in India is just the small/mid-cap and equal-weight premium. Alpha must be positive vs the equal-weight benchmark, and ideally vs the published NIFTX500-Momentum-50 index (are we even beating the free ETF?).
11. **Randomization / null test.** Replace the momentum rank with a random top-20 draw from the same investable universe, 100 seeds. The strategy's net Sharpe must sit clearly outside the random distribution (report percentile). If it's inside, the "edge" is just the universe/equal-weight tilt, not momentum.
12. **Transaction-count reconciliation.** Verify total ₹ traded ≈ turnover × book × months and that costs scale with it — a common bug is under-counting the re-weighting trades on overlap names.

---

## 9. Explicit kill criteria (any ONE fires → strategy killed or demoted, logged to KILLED_IDEAS with resurrection conditions)

Pre-registered BEFORE the run (D-028 discipline — thresholds fixed in advance, not tuned to the result):

- **K1 — Net alpha ≤ 0** vs equal-weight NIFTX500 over the full PIT+delist+cost run (t-stat of monthly alpha < 1.5). No positive net edge → dead.
- **K2 — Lookahead cliff:** one-day-lag test (§8.1) drops net CAGR by > 40% relative → result is an artifact → KILL.
- **K3 — Survivorship-dependent:** PIT+delist net Sharpe < 0.3 while current-universe Sharpe > 0.6 → the edge was survivorship → KILL.
- **K4 — Cost-fragile:** net return goes ≤ 0 at 2× modeled impact → not tradeable at real slippage → KILL (or demote to "paper-only, needs cost redesign").
- **K5 — Parameter-spike / overfit:** Sharpe collapses > 50% under the lookback/top-N grid (§8.6); DSR < 0 or PBO > 0.5 from Dr. Bhat's battery → overfit → KILL.
- **K6 — Not-the-stated-edge:** edge exists only at skip=0 (§8.5) → it's short-term reversal, not 6M momentum → reclassify, do NOT report as momentum.
- **K7 — Capacity fail:** edge exists only below the ₹5cr ADV floor, or modeled impact eats > 50% of gross alpha at ₹1cr book → no real capacity → KILL for the trading line (D-031).
- **K8 — Indistinguishable from random:** strategy net Sharpe inside the 5–95th percentile of the random-top-20 null (§8.11) → no momentum-specific edge → KILL.
- **K9 — Single-regime artifact:** all net alpha comes from one sub-period and the strategy is net-negative in the other two (§8.9) → regime-dependent, not a durable factor → demote, do not certify.
- **K10 — Doesn't beat the free ETF:** net-of-cost return below the published NIFTX500-Momentum-50 TRI (which is buyable at near-zero cost) → no reason to run the book → KILL for the product, keep only as research.

**Demote-not-kill zone:** if K1 passes but the result is borderline (t-stat 1.5–2.0, or fails one of K9/K10 only), route to forward paper test (D-030 freeze: pin git hash, freeze spec+params, restart forward clock) rather than certification. Any mid-test tuning voids the forward result.

---

## 10. Anti-lookahead checklist the implementer signs off (D-028)

Before results are quoted, confirm each in writing:
- [ ] Signal uses only bars ≤ SB; execution only bars ≥ RD+1. (T1 timing)
- [ ] Universe membership from PIT snapshot with effective-date ≤ RD. (T2 universe)
- [ ] Corporate-action factors applied only pre-ex-date; signal on adj_close, fill on raw. (T3 adjustment)
- [ ] Liquidity/circuit screens computed on trailing bars only, no forward look. (T4)
- [ ] Delisted/dead names present and losses realized. (T5 survivorship)
- [ ] No fill on circuit-locked/zero-volume bars; participation-capped. (T6 fill realism)
- [ ] Costs applied on every share, both legs, including re-weight deltas. (T7)
- [ ] Benchmarks are total-return and weight-matched. (T8)
- [ ] Random-null and one-day-lag both run and pass. (T9/T10)

Run `lib/lookahead_audit.py`; no result is quoted, no register entry made, and nothing goes to the Principal without a LOOKAHEAD AUDIT PASS.

---

*End MG01 spec. Data landmines referenced: survivorship (#6), circuit/thin-volume fills (#7b), lookahead taxonomy (#7/D-028), adjusted-vs-raw price separation, daily-bar timestamp hygiene (#8). Cost values pending COST_STANDARDS approval — until then all quoted numbers are DRAFT.*

----- ANSWER G016 (task MG01) -----
**Backtest specification — monthly top-20 momentum, NIFTY500, 2015–2026, India daily data**

**1. Data requirements & point-in-time (PIT) rules**
- Daily OHLCV per symbol, corporate-action adjusted (splits/bonuses back-adjusted; dividends handled separately — do NOT let a dividend-adjusted "total return" close silently double as the execution price, since you can't transact at an adjusted price).
- A *survivorship-complete* price panel: every symbol that ever traded in the window, including delisted/merged/renamed names, carried to its last traded price and de-listing date. Never build this from a live vendor feed queried today.
- NIFTY500 constituent history as a **snapshot series** (the index provider publishes semi-annual reconstitution files) — not today's constituent list applied backward. Universe on rebalance date *t* = the officially published constituent list in effect on *t*, looked up via `asof(t)`, never a static current-day download.
- Trading/holiday calendar from the exchange (NSE), circuit-limit flags, and a "tradable" flag (halted / ASM-GSM stage / no trades that day) so execution logic can no-fill correctly.
- Corporate-action calendar (ex-dates) so the 6-month return signal isn't computed across an unadjusted split/bonus.

**2. Universe construction**
- At each month-end formation date *t*: take PIT NIFTY500 membership as of *t*. Apply a minimum-history filter (≥ 126 trading days of price history, else momentum is undefined) and a minimum-liquidity filter (e.g., 20-day median traded value above a floor) computed using data available *strictly before t* only. Exclude names under a trading ban / circuit-locked on the signal date.

**3. Signal timing & execution convention**
- Signal = trailing 6-month return, computed using **only** closes through the close of the last trading day of the month (formation date *t*). Rank descending, take top 20.
- Execution: enter next trading session's VWAP or open (state which — VWAP is more realistic for names outside the top-50 by ADV), never the formation-day close. This is the single most common lookahead bug in momentum backtests — flag it explicitly to the junior quant.
- Hold until next rebalance; trade only the *delta* between old and new target weights, not a full liquidate-and-rebuild (this changes the cost estimate by 2–5x if done wrong).

**4. Cost model**
- Per-side: brokerage + STT + exchange transaction charge + stamp duty + GST (all known, deterministic — build a lookup table, don't guess a flat bps) **plus** a market-impact term as a function of order size / ADV (e.g., a square-root impact model, calibrated conservatively — 10–20bps for the top 100 names, materially more for the bottom of a NIFTY500-derived universe). Cap position size as a % of 20-day ADV; if a target position would breach that cap, either partial-fill over multiple days or exclude the name and disclose it.

**5. Control experiments required before believing any result**
- **Placebo/random-basket test**: same universe, same rebalance dates, same turnover, same cost model, random stock selection. The strategy must clear a stated percentile (report the actual percentile, not just "beats average").
- **Lag-sensitivity test**: shift the signal by one extra day; if the edge collapses, you have a lookahead bug, not alpha.
- **Cost-stress test**: 2x and 3x the assumed cost model — does the Sharpe survive?
- **Parameter-stability check**: vary top-N (15/20/25) and formation window (3/6/9/12 months); demand a plateau, not an isolated peak.
- **Era/regime split**: pre-2020 vs 2020–2022 vs 2023–2026; no single sub-period should carry the whole result.
- **Static-vs-PIT-universe test**: rerun with today's NIFTY500 list frozen backward — if the result changes materially, you had survivorship bias.
- **Capacity check**: what AUM does this support before impact costs eat the edge?

**6. Explicit kill criteria (pre-committed, not discovered after the fact)**
- Net-of-2x-cost Sharpe < 0.5, or the placebo-percentile < 90th, or the result fails the one-day-lag test (edge doesn't degrade gracefully — it dies), or the result is driven by <3 sub-periods / a handful of extreme trades (check contribution concentration; if top-5 trades explain >40% of PnL, kill), or the static-universe rerun changes CAGR by more than ~30% relative.

============================================================
# TASK MG02 — rubric anchors:
  1. exactly 5, materially distinct (not variants)
  2. mechanism: why the edge exists
  3. who is on the losing side
  4. cheapest kill-test per idea
  5. data is obtainable by a small team
  6. explicit kill result stated
  7. genuinely falsifiable
  8. avoids survivorship-blind / impossible-data ideas
  9. considers factor overlap (just momentum/size?)
  10. non-overlap across the five

----- ANSWER G023 (task MG02) -----
Approach: no tools needed — I'll reason from Indian market structure and pick five hypotheses with disjoint mechanisms, each killable with free/near-free data (NSE archives, exchange filings, one cheap broker API).

# Five falsifiable alpha hypotheses for Indian markets

The five mechanisms are deliberately disjoint: (1) mispriced insurance sold to lottery buyers, (2) mandated inelastic demand on a known date, (3) a regulatory constraint forcing unwinds, (4) contractual supply released into thin float, (5) hedging-flow feedback from expiry mechanics. Different instruments, different losers, different test designs.

---

## H1. Weekly Nifty options are overpriced relative to realized moves (behavioral vol premium)

**Hypothesis.** The premium of short-dated Nifty options (weekly ATM straddles as the cleanest proxy) systematically exceeds the subsequently realized move by more than transaction costs, and still does post the 2024-25 reforms.

**Mechanism & loser.** SEBI's own studies found ~93% of individual F&O traders lose money — roughly Rs 1.8 lakh crore cumulatively over FY22-24 and about Rs 1 lakh crore in FY25 alone — with losses concentrated in bought short-dated options. Buyers are paying for lottery convexity, not hedging; the losing side is literally measured by the regulator. Prop desks and FPI algos harvest it; a small team can sit on the same side. Open question: whether the Oct/Nov 2024 reforms (one weekly per exchange, tripled lot sizes, expiry-day margins) and seller crowding have compressed it to zero.

**Cheapest kill test.** From free NSE F&O bhavcopy: each week at the prior expiry's close, record the ATM weekly straddle premium; hold to expiry; payoff = |S_T − K|. ~50 observations/year, no intraday data. Compare mean premium vs mean payoff net of costs (STT 0.1% on sold premium, spread, slippage). Split pre/post Nov 2024.

**Data.** NSE F&O bhavcopy archive (free), Nifty closes, a cost schedule.

**Kills it.** Mean (premium − payoff − costs) ≤ 0, or t < 2 — especially if positive pre-reform but ≤ 0 in the post-reform subsample. That last result means the edge existed but has been regulated/arbitraged away, which is the answer that matters going forward.

---

## H2. Nifty reconstitution front-running (mandated passive demand)

**Hypothesis.** Announced additions to Nifty 50 / Nifty Next 50 earn positive abnormal returns between announcement and effective date (deletions negative), scaled by passive-demand-to-ADV, with partial post-effective reversal.

**Mechanism & loser.** Indian passive AUM (ETFs + index funds, including EPFO's ETF buying) has grown past ~Rs 10 lakh crore, concentrated in Nifty-family trackers. Index funds minimize tracking error by executing at the effective-date close regardless of price — inelastic demand on a pre-announced date, several days of ADV for big promotions. Loser: index-fund investors, who buy after the run-up by mandate. The US inclusion effect decayed to ~zero as arb capital caught up; India's passive share grew late and fast, so whether it is still alive here is genuinely open.

**Cheapest kill test.** Event study: announcement-to-effective CARs vs size/sector-matched controls, plus 20-day post-effective reversal, stratified by (index weight × tracked AUM)/ADV. NSE Indices press releases give exact announcement dates; Nifty 50 + Next 50 (+ Midcap 150 for sample size) over 10 years gives 100+ events.

**Data.** NSE Indices press-release archive, EOD bhavcopy prices/volumes, per-index passive AUM from AMFI/factsheets. All free.

**Kills it.** CAR indistinguishable from zero in the most recent ~3 years regardless of the older sample; or the run-up fully reverts so the round trip nets less than costs; or the effect survives only in tiny-ADV names where impact eats it.

---

## H3. F&O ban-list forced deleveraging (constraint-driven overshoot)

**Hypothesis.** Stocks entering the F&O ban (MWPL utilization ≥ 95%) see continued negative pressure and depressed futures basis while in ban, and abnormal positive reversal after exit (< 80%), because leverage can only come off, not on.

**Mechanism & loser.** Ban names are crowded, leveraged retail-long midcaps. In ban, no fresh derivative positions are allowed; cash shorting is nearly impossible for most participants (SLB is thin), so the constraint binds asymmetrically: leveraged longs become forced sellers while bargain hunters cannot lever in — a textbook limits-to-arbitrage overshoot. Loser: constrained leveraged speculators unwinding on a schedule they didn't choose, plus hedgers paying a distorted basis.

**Cheapest kill test.** NSE publishes the ban list and MWPL utilization daily (free archive; hundreds of episodes over 8-10 years). Event study on entry and exit dates vs momentum/size-matched controls: abnormal returns, basis path, and one naive rule (buy exit day, hold 5 days) net of realistic impact costs for these names.

**Data.** NSE ban-list/MWPL archives, cash and futures bhavcopy. Free.

**Kills it.** No abnormal return or basis pattern vs controls; or a pattern smaller than the (high) round-trip cost in these illiquid names; or sign instability across sub-periods, indicating crowding noise rather than the constraint mechanism.

---

## H4. IPO anchor lock-in expiries create dated supply pressure

**Hypothesis.** Mainboard IPOs earn negative abnormal returns around the 30-day and 90-day anchor unlock dates (and the 6-month pre-IPO holder unlock), increasing in unlock-size-to-float.

**Mechanism & loser.** Anchor allocations — names, quantities, and the exact lock-in end dates — are published at listing in exchange press releases. Post-listing float is thin because retail/HNI allottees flip early, so a dated, sized supply block hits a small float. The other side is retail momentum buyers who don't read the unlock calendar. Persistence is protected by limits to arbitrage: most fresh listings have no stock futures and negligible borrow, so professionals cannot short the pre-unlock run-up. Loser: post-listing retail holders through the unlock window.

**Cheapest kill test.** For 2023-2025 mainboard IPOs (200+), scrape anchor allocation PDFs, compute unlock dates and unlock/float, run CARs in [-10, +10] around each unlock vs market and listing-cohort controls, sorted into unlock-size terciles.

**Data.** Exchange anchor-allocation and basis-of-allotment documents, listing dates, EOD prices. Free; one week of scraping.

**Kills it.** CARs around unlocks ≥ 0 or insignificant even in the top unlock/float tercile; or the effect is real but exists only pre-unlock in unshortable names *and* there is no exploitable post-unlock dip-and-reversal — real but untradeable in both directions (pure avoidance is not alpha).

---

## H5. Expiry-day hedging signature on Nifty — with a built-in natural experiment

**Hypothesis.** Nifty intraday behavior on weekly-expiry days differs exploitably from non-expiry days — the close lands nearer the maximum-OI strike than chance (pinning), or late drift amplifies when price is far from it (short-gamma chase) — and, because the cause is expiry mechanics, the signature must have migrated when NSE moved the weekly expiry from Thursday to Tuesday in 2025 (and disappeared from Bank Nifty when its weeklies were discontinued in Nov 2024).

**Mechanism & loser.** Enormous 0-1 DTE open interest concentrates mechanical delta-hedging into the final hour; high-OI strikes act as magnets or accelerants depending on the sign of aggregate hedger gamma. Loser: expiry-day directional retail, whose losses in short-dated options SEBI has documented — they pay decay at pins and get whipsawed off them.

**Cheapest kill test.** 1-minute Nifty candles from a broker API (~Rs 2,000/month) plus free per-strike OI from bhavcopy. Metric 1: ATR-normalized distance of the 15:30 close to the nearest high-OI strike, expiry vs non-expiry days. Metric 2: last-75-minute drift conditional on 14:15 distance-to-strike. Then the diff-in-diff across the Thursday→Tuesday migration: the signature must appear on Tuesdays and vanish from Thursdays.

**Data.** Broker historical API, F&O bhavcopy, exchange circulars for exact change dates. A few thousand rupees total.

**Kills it.** Expiry and non-expiry distributions statistically indistinguishable; or the signature fails to migrate with the administrative change (then it was day-of-week seasonality, not expiry mechanics); or the effect is real but below index-futures round-trip cost (~2 bps + impact).

---

**Cross-cutting discipline for all five:** split every sample at Nov 2024 (the derivatives-reform regime break) and treat pre-reform-only results as dead; net everything of realistic costs including current STT; build all event lists point-in-time from free exchange archives to avoid survivorship; and pre-register the kill criterion before looking at returns.

Sanity check: re-read the ask and verified the deliverable — exactly 5 hypotheses, each with mechanism plus identified loser, a single cheapest kill test, a data list a small team can actually obtain (free NSE/BSE archives, exchange filings, one cheap broker API), an explicit kill criterion, and five mutually distinct mechanisms (behavioral premium, mandated demand, regulatory constraint, contractual supply, hedging feedback). No tools were used, per instruction.

result: Delivered 5 distinct, cheaply testable falsifiable alpha hypotheses for Indian markets — weekly option premium vs realized, Nifty reconstitution flows, F&O ban-list forced unwinds, IPO anchor-unlock supply, and expiry-day pinning with the 2025 expiry-migration natural experiment — each with mechanism, losing counterparty, cheapest kill test, data sources, and kill criteria.

----- ANSWER G015 (task MG02) -----
# Five Falsifiable Alpha Hypotheses: Indian Equity & Derivatives Markets
**Author:** Research Harness (Haiku-driven hypothesis generation)  
**Date:** 2026-07-12  
**Scope:** Small-team, cheaply-testable, materially-distinct mechanisms

---

## HYPOTHESIS 1: Pre-Open Auction Gap Mean Reversion (Intraday Microstructure)

**Mechanism:**  
NSE pre-open auction (09:00–09:15) clears overnight order imbalances at the equilibrium opening price. This creates a discrete gap vs. previous close. Real market participants (algos, hedgers, retail) then discover true liquidity on actual market open. Auction-induced gaps should experience mean reversion within 30 minutes as desperation orders clear and informed traders enter. **Losers:** retail traders buying market-on-open at the extremes; **Winners:** intraday scalpers with sub-minute fills.

**Cheapest Kill Test:**  
1. Split 500+ trading days into quartiles by gap magnitude: `gap % = (Open_09:15 – Close_prev) / Close_prev`
2. For each day, compute intraday return: `Ret_intraday = (High_09:30_to_10:00 – Open_09:15) / Open_09:15` (long high-gap days; measure reversal)
3. Run Spearman correlation: `corr(gap_magnitude, abs(intraday_reversal))`
4. Calculate Sharpe ratio of a zero-cost spread: long high-gap days, short low-gap days, flatten at 10:00 a.m.

**Data Needed:**  
- NIFTY 50 daily OHLC (have: NSE bhavcopy, HF dataset)
- Pre-open auction opening price (09:15 marked price; NSE publishes, or infer from first tick at 09:15)
- 1-min NIFTY bars 09:15–10:00 (have: HF, Angel API)

**Kill Condition:**  
- Spearman correlation |ρ| < 0.15 with p-value > 0.05, **OR**
- Sharpe ratio of mean-reversion trade < 0.4 (indistinguishable from noise), **OR**
- High-gap days do NOT show reversal by 10:00 (mean reversion return < 3 bps with t-stat < 1.2)

---

## HYPOTHESIS 2: Index Reconstitution Front-Run (Stock Flow Prediction)

**Mechanism:**  
Nifty 50 reconstitution is announced ~2 weeks before implementation. Added stocks face predictable inflows (index funds, passive trackers, smart-beta products). Removed stocks face redemptions. Smart money (mutual funds, hedge funds) who know the move front-run by 3–5 days ahead of the index committee announcement or implementation. **Losers:** passive index followers forced to buy at the peak or sell at the trough on implementation day; **Winners:** active traders who position 5 days pre-event.

**Cheapest Kill Test:**  
1. Collect all Nifty 50 reconstitution dates & lists (public; ~5–8 per year historically, ~15–20 over 3 years)
2. For each reconstitution event, compute **abnormal return** of:
   - Stocks added: return from (Day –10 to announcement) vs. (Day 0 to +10 post-implementation)
   - Stocks removed: same windows
3. Measure if **pre-announcement period shows statistically significant outperformance** for stocks-to-be-added
4. Compare to a null model: random-stock universes of same size, same dates

**Data Needed:**  
- Historical Nifty 50 constituent lists with dates (have: NIFTY500_TICKER_2005_2025_Final.xlsx in datasets)
- Daily close prices for all NIFTY 50 stocks (have: HF, Angel historical data)
- Reconstitution calendar (public; NSE website)

**Kill Condition:**  
- Mean abnormal return of added stocks in days –10 to –1 < 1.5% with t-stat < 1.5 (no consistent edge), **OR**
- No statistically significant difference between added/removed stock returns vs. random control samples (t-test p > 0.10), **OR**
- Outperformance disappears after accounting for market beta and sector rotation (alpha < 50 bps with t-stat < 1.2)

---

## HYPOTHESIS 3: Weekly Option Expiry Gamma Momentum (Derivatives Market Microstructure)

**Mechanism:**  
NIFTY 50 options expire every week (Friday 3:30 p.m. IST). Market makers carry large gamma positions (long from being net sellers to retail). As spot price moves, gamma sensitivity forces them to delta-hedge continuously. Near expiry (last 30 minutes), gamma becomes acute, creating **mechanical directional pressure** in spot as MMs frantically rebalance. This creates intraday volatility and momentum anomalies. **Losers:** retail long-gamma option buyers who get "gamed" by MMs; **Winners:** spot traders with millisecond-level execution.

**Cheapest Kill Test:**  
1. Identify all weekly NIFTY 50 option expiry Fridays (known calendar; 52+ per year)
2. Compute **intraday volatility** (realized vol 3:00–3:30 p.m. expiry hour vs. 12:00–1:00 p.m. non-expiry hour) for 100+ expiry days
3. Compute **directional returns**: mean return of NIFTY 50 in expiry hour vs. same hour on non-expiry days
4. Calculate **Sharpe ratio** of a simple momentum strategy: long spot if +2% move in prior 30 mins on expiry days; close in last 15 mins

**Data Needed:**  
- 1-min NIFTY 50 OHLC bars (have: HF, Angel API; need ~2 years = 100+ expiry days)
- Weekly expiry calendar (deterministic; every Friday)
- Option open interest by strike (optional, for validation; Angel API or NSE option chain)

**Kill Condition:**  
- Realized volatility in expiry hour NOT significantly higher than non-expiry hour (p > 0.10), **OR**
- Sharpe ratio of gamma-momentum edge < 0.4 (edge indistinguishable from luck), **OR**
- Directional bias (mean intraday return) in expiry hour < 2 bps with t-stat < 1.0 (no mechanical pressure)

---

## HYPOTHESIS 4: Bank Nifty RBI Policy Event Window Repricing (Macro Event Window)

**Mechanism:**  
RBI monetary policy decisions (bi-monthly; ~6 per year) and banking sector-specific announcements (stress tests, credit policy, liquidity operations) create hard repricing in Bank Nifty but option market does not fully anticipate the volatility magnitude. Option traders long volatility (straddles, strangles) are caught off-guard. Short-gamma dealers profit. **Losers:** retail option buyers betting on "normal" vol expansion; **Winners:** volatility sellers with correct vol forecasting.

**Cheapest Kill Test:**  
1. Collect all RBI policy announcement dates (6/year; ~18 over 3 years; public)
2. For each announcement, measure **implied volatility (IV) change** in Bank Nifty ATM 1-month call/put options:
   - Baseline IV: day before announcement, close
   - Event IV: day after announcement, close
   - Delta_IV = (IV_after – IV_before) / IV_before
3. Compare to **normal-day IV changes** (rolling 20-day moving average of |daily IV change| on non-announcement days)
4. t-test: mean Delta_IV on announcement days vs. mean IV change on normal days

**Data Needed:**  
- Bank Nifty option implied volatility, daily (1-month ATM put or call; have: Angel SmartAPI historical data or NSE option chain snapshots)
- RBI policy calendar (public; RBI.org.in)
- Bank Nifty daily close (have: HF, Angel API)

**Kill Condition:**  
- Mean IV change on announcement days < 0.7% in absolute terms with t-stat < 1.5 (no significant repricing), **OR**
- IV change on announcement days NOT statistically different from normal-day IV volatility (two-sample t-test p > 0.15), **OR**
- Volatility edge (ability to outperform by selling straddles before announcements and buying back after) has Sharpe < 0.3 over 3+ events

---

## HYPOTHESIS 5: Low-Liquidity Mid-Cap Momentum Slippage Trap (Execution Friction Filter)

**Mechanism:**  
Mid-cap stocks (NIFTY 250 \ NIFTY 50; ~200 names) show significant 20–30 day momentum in closing prices. Retail traders chase this momentum by buying at market. However, **effective spreads are 100–200 bps** (bid-ask + market impact). Traders overpay on entry and underprice on exit, losing all of the momentum alpha to slippage. Smart execution algorithms can capture this gap. **Losers:** manual retail traders, overconfident momentum followers; **Winners:** algorithms with execution edge.

**Cheapest Kill Test:**  
1. Rank mid-cap stocks (non-Nifty-50, 200–350 constituents) by **20-day momentum**: `mom_20d = (Close_t – Close_t-20) / Close_t-20`
2. Split into quintiles (Q1 = weakest, Q5 = strongest)
3. For Q5 (high momentum), measure **next 10-day gross return**
4. Estimate **execution slippage**: typical mid-cap bid-ask spread is 0.5–2% on entry; assume 1.25% round-trip slippage + 10 bps market impact
5. Compute **net alpha = gross return – slippage**
6. t-test if net alpha > 0 with 3+ years of data (250+ rebalance cycles)

**Data Needed:**  
- Daily OHLC for NIFTY 250 \ NIFTY 50 stock universe (~200 names, have: HF, Angel API)
- Bid-ask spreads (NSE bhavcopy includes bid-ask; or Angel API order book snapshots)
- Universe membership dates (have: NIFTY500_TICKER_2005_2025_Final.xlsx with PIT snapshots)

**Kill Condition:**  
- Gross momentum return in Q5 < 2.0% over 10 days with t-stat < 1.5 (weak momentum signal), **OR**
- Net return (after slippage) of high-momentum quintile < 0% annualized or < 50 bps Sharpe ratio (alpha fully extracted by execution friction), **OR**
- High-momentum midcap underperform market equal-weighted return after slippage (negative alpha with t-stat > 1.8)

---

## SUMMARY TABLE

| # | Hypothesis | Time Horizon | Asset | Test Cost | Data Sourcing | Kill Threshold |
|---|---|---|---|---|---|---|
| 1 | Pre-Open Gap Reversion | 30 min | NIFTY 50 (spot) | ⭐ Very Low | NSE OHLC, HF 1-min | Sharpe < 0.4 on 500 days |
| 2 | Recon Front-Run | 2 weeks | NIFTY 50 stocks | ⭐ Very Low | NSE recon dates, HF prices | Alpha < 50 bps, t-stat < 1.2 |
| 3 | Expiry Gamma | 30 min | NIFTY 50 (spot) | ⭐ Very Low | HF 1-min, expiry calendar | Sharpe < 0.4 on 100+ events |
| 4 | RBI Event Vol | 1 day | Bank Nifty (opts) | ⭐ Low | Angel API IV, RBI calendar | IV change < 0.7%, t-stat < 1.5 |
| 5 | Mid-Cap Slippage | 10 days | Nifty 250 (stock) | ⭐ Low | NSE OHLC, spreads, HF prices | Net return < 0%, Sharpe < 0.5 |

**Rationale for "Cheap" Designation:**  
- No live trading capital required (all backtests)
- Data sourced from public/in-house archives (NSE, HF, Angel API)
- Computational cost: Python scripts (corr, t-tests, ranking); no ML training or optimization
- Verification: hypothesis can be confirmed/killed in 2–5 days of work per hypothesis

---

## NEXT STEPS (Sequencing)

1. **Hypothesis 1 & 3 first** (same 1-min data infrastructure, fastest validation: intraday tests complete in hours)
2. **Hypothesis 4 next** (IV data might need Angel API warm-up; 18 events to analyze)
3. **Hypothesis 2 & 5 in parallel** (need daily data + longer backtest windows; ~2 weeks each)

**Expected rejection rate:** 3–4 of 5 killed; possibly 1–2 advance to Gate-2 (live paper trade validation).

----- ANSWER G019 (task MG02) -----
# MG02 — Five Falsifiable Alpha Hypotheses (opus)

**Author:** opus (MODEL_GRID cell MG02) · **Date:** 2026-07-13 · **Scope:** Indian equity + index derivatives, small-team-testable, cheap data only.

Design rule enforced: the five differ by *mechanism axis* and *losing counterparty*, not by parameter. Axes covered — (1) intraday/overnight seasonality, (2) derivatives risk premium, (3) fundamental information diffusion, (4) behavioural risk-preference factor, (5) India-specific positioning/crowding microstructure. Every test names a **single pre-registered kill number** so a null result ends it in one pass. Tags: [INFERENCE] = reasoning, [DATA] = source, [OPINION] = prior.

---

## H1 — Overnight drift owns the index risk premium; the intraday session is flat-to-negative

**Claim.** For NIFTY / BANKNIFTY, the close→open (overnight) return series has materially positive mean and Sharpe, while the open→close (intraday) series is ~zero or negative. Holding the index only overnight beats buy-and-hold on a risk-adjusted basis.

**Mechanism [INFERENCE].** Global cues (US close, SGX/GIFT, commodities, FX) and the compensation-for-holding-overnight-gap-risk are impounded in the opening auction, so the risk premium accrues while the cash market is shut. Intraday, leveraged and margin-financed participants must flatten before close (avoid overnight margin / MIS square-off), creating persistent close-side selling pressure and mean-reverting noise.

**Who loses [INFERENCE].** Retail/prop **intraday day-traders** (MIS/leverage products) who systematically exit into the close and are absent overnight — they forfeit the drift and pay the round-trip cost to avoid gap risk they are actually being paid to bear.

**Cheapest killing test.** Take NIFTY daily OHLC, build two return series: overnight `r_on = open_t/close_{t-1} − 1`, intraday `r_id = close_t/open_t − 1`. Compare cumulative product, mean, and annualised Sharpe of each. One script, minutes to run. (Note DATA LANDMINE #2: use the 09:15 real open, not the 09:00 pre-open auction print, if working from 1-min bars; from daily bhavcopy the official open is fine.)

**Data needed [DATA].** NIFTY / BANKNIFTY daily OHLC, 2010→now. Free (NSE index history / Stooq / Angel getCandleData ONE_DAY — mind LANDMINE #8, use `fromdate = date−1 00:00`). No option or intraday data required for the kill test.

**What kills it (pre-registered).** Overnight annualised Sharpe **< 1.25× intraday Sharpe**, OR overnight mean return **≤ 0 after a 3–5 bp per-side gap-execution haircut** (you cannot trade the auction print costlessly). Either → dead, because the effect must survive the fact that you must actually transact at/near the open.

**Prior-art caveat [OPINION].** Well documented in US/global indices; India-specific magnitude and post-2020-retail-boom persistence are the real questions. If real but shrinking, that is a decay finding, not a kill.

---

## H2 — Positive variance risk premium in NIFTY weekly index options (IV persistently exceeds subsequent RV)

**Claim.** ATM NIFTY implied volatility systematically prices above the realized volatility that follows over the option's life; a defined-risk short-vol structure (e.g. short strangle / iron condor) has positive expected P&L before the tail.

**Mechanism [INFERENCE].** Options are insurance. Structural, price-insensitive **buyers of protection** (portfolio hedgers) and **lottery-ticket buyers** (retail weekly-option punters, now a huge share of NSE volume) bid IV above the actuarially fair level. The premium is compensation for bearing crash/gamma risk that most participants pay to shed.

**Who loses [INFERENCE].** The **net option buyer** — retail weekly OTM buyers chasing convex payoffs and institutional hedgers paying for downside insurance. Their expected loss is the seller's premium.

**Cheapest killing test.** For each week, take ATM IV (invert Black-Scholes on the ATM NIFTY option settle, or use India VIX as the proxy) at entry, and compute the realized vol of NIFTY over the same forward window. VRP = mean(IV − RV_forward), annualised. No live trading, no greeks engine — just a paired IV-vs-realized comparison. **Critically weight by P&L, not by count**, so the few large-loss weeks are included honestly.

**Data needed [DATA].** India VIX daily history (free, NSE) OR NIFTY option bhavcopy for ATM IV (free NSE archives; respect LANDMINE #9 — never read expiry-day option SETTLE_PR as the option price, and gate on CONTRACTS>0), plus NIFTY spot for realized vol. All free.

**What kills it (pre-registered).** Mean(IV − RV_forward) **≤ 0**, OR the premium goes **negative once the worst-decile realized-vol weeks are P&L-weighted** (i.e. the tail eats the whole edge). Either → dead; a short-vol edge that only exists when you exclude the crash weeks is not an edge.

**Prior-art caveat [OPINION].** VRP is one of the most-published anomalies on earth and is crowded on NIFTY. The kill test's job is not "does VRP exist" (it likely does) but "does it survive tail-weighting after retail crowding compressed it post-2023." Treat a thin surviving margin as a fail for a *small, undercapitalised-for-tails* team.

---

## H3 — Post-earnings announcement drift (PEAD) in Indian mid/small-caps

**Claim.** Stocks with a large positive price reaction on the earnings-announcement day continue to drift in the same direction for 20–60 trading days; the effect is stronger in under-covered mid/small-caps than in large-caps.

**Mechanism [INFERENCE].** Slow information diffusion + limited analyst coverage of smaller names → investors underreact to the earnings signal and revise expectations gradually rather than instantly. Large-caps are efficiently priced; the edge lives where attention is scarce.

**Who loses [INFERENCE].** **Slow-updating and inattentive holders** of under-covered stocks who do not re-price on the print, and the market-makers who anchor to stale expectations.

**Cheapest killing test.** Using the PIT earnings dataset (`available_date`, avoids LANDMINE #3/#7 lookahead), proxy the surprise by the announcement-day (or announcement-window) abnormal return — no consensus-estimate data required. Sort event-stocks into quintiles by this reaction; measure the average 20/40/60-day forward return of Q5 (biggest positive reaction) minus Q1. One event-study script.

**Data needed [DATA].** PIT quarterly earnings with announcement dates (`datasets/earnings_pit/unified_quarterly_pit.parquet`, already held) + daily closes for the NIFTY 500 universe (survivorship-safe via `NIFTY500_TICKER_2005_2025_Final.xlsx`, LANDMINE #6). All in-house.

**What kills it (pre-registered).** Q5−Q1 40-day forward spread **not positive at t-stat ≥ 2**, OR the spread **fully absorbed by a 6-1 momentum control** (regress the spread on the stock's prior-6m return; if alpha → 0, it is just momentum in disguise). Either → dead.

**Prior-art caveat [OPINION].** Classic and durable globally; the India-specific, cheaply-testable twist is the large-cap-vs-small-cap coverage split. Must also clear the cost gate — small-cap PEAD is notoriously expensive to trade (impact/slippage), so pair any survivor with a `fill-audit` before excitement.

---

## H4 — Betting-against-beta / low-volatility anomaly in NIFTY 500

**Claim.** Low-realized-volatility (low-beta) stocks deliver equal-or-higher raw returns and materially higher risk-adjusted returns than high-vol stocks; a long-low-vol / short-(or-underweight)-high-vol tilt has positive alpha.

**Mechanism [INFERENCE].** Leverage-constrained investors (most retail, many mandates) who want more return cannot borrow, so they overpay for high-beta and lottery-like high-vol names to reach for return. This bids high-vol stocks to low expected returns and leaves low-vol stocks cheap on a risk-adjusted basis (Frazzini-Pedersen BAB).

**Who loses [INFERENCE].** **Leverage-constrained, return-reaching retail** crowding into high-beta / high-vol lottery stocks — a documented and growing Indian retail behaviour.

**Cheapest killing test.** Rank the survivorship-safe NIFTY 500 each month by trailing 12-month realized vol; form the bottom-decile (low-vol) and top-decile (high-vol) equal-weight baskets; compare next-12-month return and Sharpe. Cross-check against the official **NIFTY 100 Low Volatility 30 / Alpha Low-Vol** index vs plain NIFTY as a free external validation.

**Data needed [DATA].** Daily closes, NIFTY 500 PIT universe (in-house, LANDMINE #6). Optional validation: official niftyindices.com factor-index closes (free; the `factor-indices` skill fetches them — home-network only). No fundamentals needed.

**What kills it (pre-registered).** Low-vol decile forward Sharpe **≤ high-vol decile Sharpe**, OR the official NIFTY Low-Vol 30 index **fails to beat NIFTY on Sharpe** over 2010→now. Either → dead. (Raw-return underperformance alone does NOT kill it — the claim is risk-adjusted; only a Sharpe failure kills.)

**Prior-art caveat [OPINION].** Very well known; there is a tradable index, so a naive version is not proprietary alpha. Worth testing only as (a) a cheap sanity anchor that our data plumbing reproduces a known effect, and (b) a base to add a genuinely differentiated overlay later. Flag as low-novelty.

---

## H5 — F&O security-in-ban list flags crowded leverage; forward reversal after ban entry (India-specific)

**Claim.** When a single-stock derivative enters the NSE **F&O ban period** (market-wide open interest > 95% of the position limit), it marks extreme crowded speculative positioning; the underlying tends to **mean-revert / underperform** over the following days versus its pre-ban trend, and unwinding into ban-exit is exploitable.

**Mechanism [INFERENCE].** A ban-list entry is a hard, observable signal that leveraged directional positioning has maxed out — no *new* positions can be opened, so the marginal speculative buyer is removed and forced unwinds dominate. Crowded, over-leveraged momentum in that name is at its most fragile precisely when everyone is already in.

**Who loses [INFERENCE].** **Crowded, over-leveraged directional speculators** who piled into the F&O name late (chasing the move that drove OI to the limit) and must unwind as the ban forces position reduction.

**Cheapest killing test.** Scrape the daily NSE F&O ban list (published every trading day, free). For each name-entry event, measure the underlying's forward 1/3/5/10-day return, and compare to (a) its own prior 10-day trend and (b) a same-day sector/beta-matched control. One scraping script + one event-study. India-specific and essentially free.

**Data needed [DATA].** NSE daily "Securities in ban period" list history (free NSE archive / daily bhavcopy companion file) + daily closes for the banned names. Both cheap and obtainable; no OI-depth or paid feed required — the ban list *is* the pre-computed crowding flag.

**What kills it (pre-registered).** Post-ban-entry forward return (vs the beta-matched control) **not negative — i.e. no reversal — at t-stat ≥ 2 over the 1–5 day window**, OR any apparent reversal **vanishes after a realistic small/mid-cap round-trip cost + no-fill-on-circuit adjustment** (LANDMINE #7b — banned names are often circuit-locked, so many fills are fictional). Either → dead.

**Prior-art caveat [OPINION].** Under-published relative to H2/H4 and genuinely India-microstructure-specific, so the most likely to be *uncrowded* of the five. Biggest execution risk: banned stocks hit circuits and gap, so the fill-realism gate is where this most plausibly dies — build that into the very first test, not later.

---

## Summary matrix

| # | Edge | Mechanism axis | Losing side | Cheapest kill test | Kills it if |
|---|------|----------------|-------------|--------------------|-------------|
| H1 | Overnight index drift | Intraday/overnight seasonality | Intraday day-traders (flatten into close) | Split NIFTY daily OHLC into overnight vs intraday return series | Overnight Sharpe < 1.25× intraday, or overnight mean ≤ 0 after 3–5 bp gap cost |
| H2 | NIFTY VRP (short vol) | Derivatives risk premium | Net option buyers (hedgers + retail lottery) | Mean(ATM IV − forward RV), P&L-weighted | ≤ 0, or negative once worst-decile RV weeks weighted |
| H3 | Mid/small-cap PEAD | Fundamental information diffusion | Slow-updating holders of under-covered names | Event-study: Q5−Q1 fwd return by announcement-day reaction | 40-day spread t < 2, or fully absorbed by 6-1 momentum |
| H4 | Low-vol / BAB | Behavioural risk-preference factor | Leverage-constrained retail reaching for beta | Low-vol vs high-vol decile forward Sharpe; NIFTY Low-Vol 30 vs NIFTY | Low-vol Sharpe ≤ high-vol Sharpe (index cross-check fails) |
| H5 | F&O ban-list reversal | India positioning/crowding microstructure | Crowded over-leveraged speculators | Event-study on daily NSE ban-list entries vs beta-matched control | No negative fwd return t ≥ 2, or gone after circuit/cost realism |

**Ranking on novelty × cheapness × uncrowdedness [OPINION]:** H5 (most India-specific, likely least crowded) and H1 (cheapest to test, one data series) are the highest-priority first passes; H3 next (in-house PIT data, real coverage angle); H2 and H4 are near-certain to "exist" but are crowded/published, so treat them as data-plumbing sanity anchors and only pursue with a differentiated overlay. All five are killable with data already on the laptop or free from NSE — no vendor spend required.

----- ANSWER G002 (task MG02) -----
**5 falsifiable alpha hypotheses — Indian equity / index-derivatives, cheap to test**

1. **Post-earnings-drift long, positive surprise, mid/small caps.** *Mechanism*: sell-side and retail attention is slower for names outside NIFTY100; the market underreacts to genuine EPS beats vs a trend extrapolation, and drift closes over 5–10 sessions. Losing side: retail investors who don't update on the print, and index-hugging institutions with no mandate to react to a mid-cap beat. *Cheapest kill test*: is the "drift" indistinguishable from ordinary momentum/size factor exposure? Regress trade returns on contemporaneous size and 12-1 momentum factor returns; if the alpha t-stat drops below ~1.5 after controlling for those, it's dead. *Data*: quarterly EPS with true publication timestamps (not quarter-end), adjusted daily prices. *Kill result*: no residual edge after factor-neutralizing, or the edge doesn't survive a 1-day-lag test.

2. **Index-rebalance front-running (inclusion/exclusion in NIFTY50/NIFTY Next 50).** *Mechanism*: passive AUM tracking these indices must buy/sell on the effective date; a small trader can take the other side of that flow days before/at the event. Losing side: index funds forced to trade regardless of price (inelastic demand). *Cheapest kill test*: measure abnormal return in the announcement-to-effective window across all reconstitutions in the last 5 years — if it's not statistically distinguishable from the ordinary volatility of small/mid caps around random dates, dead. *Data*: index provider's reconstitution announcement history (public), free-float and estimated passive AUM tracking each index. *Kill result*: abnormal-return t-stat < 2 across ≥20 events, or the effect has decayed to near-zero in the last 2 years (a well-known effect that's been arbitraged away).

3. **Weekly-expiry pin risk / gamma-driven index drift into expiry.** *Mechanism*: dealer short-gamma hedging near large open-interest strikes on NIFTY weekly expiry days creates a mechanical pull of spot toward high-OI strikes in the final hours. Losing side: option buyers holding gamma into expiry who get pinned against their favor; dealers systematically hedge in a way that dampens realized moves. *Cheapest kill test*: on expiry days, is |close − max-OI-strike| systematically smaller than on a random matched non-expiry day, controlling for realized vol? *Data*: F&O bhavcopy OI by strike, index 1-minute prints. *Kill result*: no statistically significant pin effect vs matched control days.

4. **Overnight index drift conditional on the day's realized-vol regime.** *Mechanism*: overnight returns partly reflect a risk premium for holding gap risk; that premium is time-varying and higher when realized vol has been low (crowded short-gap positioning unwinds less). Losing side: intraday-only traders who are flat overnight and forgo the premium; nobody is "losing" in a zero-sum sense here — this is closer to a risk premium than an inefficiency, which is itself testable and falsifiable. *Cheapest kill test*: compare overnight return conditional on trailing 20-day realized-vol percentile vs unconditional overnight drift — matched-exposure random-night baseline must be beaten, not just "any overnight long." *Data*: daily OHLC only (cheapest of all five). *Kill result*: conditional edge collapses to the unconditional drift once you control for exposure (nights selected vs random nights of equal count).

5. **Quarterly-results-season liquidity discount on illiquid F&O names.** *Mechanism*: during peak results weeks, market-makers widen spreads/reduce depth on single-stock options with earnings risk; a liquidity-provision strategy selling that temporarily-widened spread (via calendar or vertical spreads, not naked) earns a rent for absorbing event risk that most participants avoid. Losing side: retail/small directional traders paying the wide spread to express an earnings view. *Cheapest kill test*: measure realized bid-ask spread and quoted depth in the 3 days around earnings vs a non-earnings baseline for the same stock; if the spread widening isn't several multiples of normal, the rent isn't there to collect. *Data*: F&O quote/trade data (need at least end-of-day best bid/offer, ideally intraday) for single-stock options — the one hypothesis here that needs data a small team may struggle to get cheaply; flag as the weakest on the "cheap data" criterion.

============================================================
# TASK MG03 — rubric anchors:
  1. resume-safe (ledger/done-marker)
  2. idempotent, no double-ingest
  3. atomic writes (.part rename)
  4. corrupt-download rejection
  5. checksum/schema validation gate
  6. alerts only on actionable failure
  7. new-machine takeover (state on disk)
  8. rate-limit/backoff handling
  9. concrete mechanisms not principles
  10. gap/partial-history detection

----- ANSWER G012 (task MG03) -----
Design doc below. Since no tools are allowed, my sanity check is a requirements re-read at the end mapping each of the four guarantees to the specific mechanism that enforces it.

# Resume-safe EOD ingestion pipeline

Example flavor: NSE-style bhavcopy zips posted ~18:00 IST; everything generalizes.

## 1. Disk layout (one filesystem, so renames are atomic)

```
data/
  incoming/                      # *.part downloads + *.meta.json (etag, expected size, url)
  raw/YYYY/MM/DD/file.zip        # immutable, verified originals (chmod 444 after landing)
  raw/YYYY/MM/DD/file.zip.sha256 # sidecar written at verification time
  quarantine/YYYY-MM-DD/         # failed verification + .reason.json, kept 30 days
  dataset/trade_date=YYYY-MM-DD/ # parquet partition + _SUCCESS marker containing the source sha256
  ledger/ingest.db               # SQLite (WAL) — rebuildable index, NOT the source of truth
  logs/YYYY-MM-DD.jsonl
```

Hard rule: `incoming/` and `raw/` are on the same mount so `rename()` is atomic. Nothing ever writes directly into `raw/` or `dataset/`; both are reached only by rename-after-verify.

## 2. Ledger

```sql
CREATE TABLE files (
  source TEXT, file_kind TEXT, trade_date TEXT,
  state TEXT CHECK(state IN ('PENDING','VERIFIED','INGESTED','HOLIDAY',
                             'QUARANTINED','WAITING_RETRY','NEEDS_HUMAN')),
  url TEXT, size INTEGER, etag TEXT, sha256 TEXT,
  attempts INT DEFAULT 0, last_error TEXT, next_retry_at TEXT,
  verified_at TEXT, ingested_at TEXT, operator_note TEXT,
  PRIMARY KEY (source, file_kind, trade_date));
CREATE TABLE alerts (key TEXT PRIMARY KEY, first_at TEXT, last_at TEXT,
                     count INT, resolved_at TEXT);
CREATE TABLE lease  (name TEXT PRIMARY KEY, owner TEXT, expires_at TEXT);
```

Two invariants that make this crash-safe:

- **The ledger records only durable facts, never in-flight status.** There is no `DOWNLOADING` state; a crash mid-download simply leaves a `.part` file, which the next run resumes. Attempt counts and `next_retry_at` are durable facts, so backoff survives restarts.
- **Filesystem first, ledger second.** File lands in `raw/` before the row says `VERIFIED`; the `_SUCCESS` marker lands before the row says `INGESTED`. Every crash window between the two is closed by `rebuild-ledger` (below), which re-derives state from disk — never by trusting a flag.

## 3. Work planning — absence is a first-class state

A versioned trading-calendar file (holidays, timezone `Asia/Kolkata`) expands into the expected set of `(source, file_kind, trade_date)` rows. Each expected file gets a `PENDING` row; holidays get `HOLIDAY`. This is what makes "nothing is ever lost" enforceable: a missing day is a visible non-`INGESTED` row, not silence. `pipeline gaps --since 2020-01-01` lists every unfilled trading day in seconds. An ad-hoc exchange holiday is resolved by a human with `pipeline mark-holiday 2026-07-14 --reason "..."` (recorded with operator note).

## 4. Download step (the unreliable-proxy defenses)

Per file, worker does:

1. `HEAD` (or `GET Range: bytes=0-0`) → capture `Content-Length`, `ETag`/`Last-Modified` into `incoming/name.meta.json`.
2. If `name.part` exists and stored ETag matches, resume with `Range: bytes=<part_size>-`. ETag mismatch or no `Accept-Ranges` → delete `.part`, restart from zero.
3. Stream in 1 MiB chunks. Timeouts: connect 15 s, read 60 s. **Stall watchdog:** if throughput < 20 KB/s averaged over 60 s, abort the attempt (equivalent to curl `--speed-limit 20480 --speed-time 60`) and retry immediately with a Range resume — a stall costs 60 s, not a hang.
4. **Retry schedule** on failure: 1 m, 5 m, 15 m, 60 m, then hourly, ±20% jitter, persisted in `next_retry_at` so restarts don't reset backoff. Honor `Retry-After` on 429/503.
5. **Block detection:** HTTP 403/429, connect-reset, or a 200 whose Content-Type/magic bytes are HTML instead of the expected zip (corporate proxies inject 200 block pages — never trust a 200). On block signature: back off 90 ± 30 min, force concurrency to 1, and keep a 3–8 s jittered politeness gap between requests on one keep-alive session. Default concurrency is 1 anyway — at 0.7 MB/s the link, not the loop, is the bottleneck, and parallelism only raises block risk.

## 5. Verification gate (corrupt bytes can't pass)

Runs on the completed `.part`, still in `incoming/`:

1. Byte size == Content-Length and == sidecar expectation.
2. Publisher checksum if the archive provides one.
3. Structural: zip CRC test of every member (`zipfile.testzip`), full gzip decode, strict-schema CSV parse.
4. Semantic hard-fails: zero rows; embedded trade date != requested date (catches "server served yesterday's file / an error page"). Soft warning (log only): row count outside 50–200% of the trailing 20-day median.
5. Compute SHA-256 → write sidecar → `fsync` file → atomic rename into `raw/YYYY/MM/DD/` → fsync directory → `chmod 444` → ledger row `VERIFIED`.

Failure → move to `quarantine/` with `.reason.json`, re-download from scratch (proxy mangling is the usual cause). Three failures with *identical* bad bytes → `NEEDS_HUMAN` (source-side problem). If a re-download of an already-`VERIFIED` date returns different bytes, never overwrite: store as `name.<sha8>.v2` and raise a RESTATEMENT alert for a human decision.

## 6. Ingestion — exactly-once by construction

Idempotency key: `(trade_date, file_sha256)`. Reads only from `raw/`.

- Parquet target: write to `dataset/_tmp/<uuid>/`, atomic-rename to `dataset/trade_date=YYYY-MM-DD/` containing `part-<sha8>.parquet`, write `_SUCCESS` (embedding the source sha256) last, then ledger `INSERT OR IGNORE` → `INGESTED`. The partition path is a pure function of the key, so re-running after any crash overwrites the same partition with the same bytes — replay converges, never duplicates. No appends anywhere (appends are how double-ingest happens).
- SQL target: `DELETE FROM eod WHERE trade_date=?; INSERT ...; INSERT INTO ingested(sha256, trade_date)...` in **one transaction**, with the idempotency table in the target DB itself.

Orphan `_tmp/` dirs and `.part` files older than 7 days are removed by a janitor step.

## 7. Scheduling and single-writer safety

systemd timer (or cron) runs the same idempotent command `pipeline run` at 18:30 IST, hourly until 23:00, and once at 07:00 next day for stragglers. Every run: acquire lease → plan → download → verify → ingest → alert-evaluate → heartbeat. The **lease** is a ledger row (`owner`, `expires_at`, heartbeat-refreshed every 60 s, stealable after 5 min stale) so an overlapping cron fire or a second machine can never double-run — critical during migration.

## 8. Alerting — silent unless a human must act

- **Never alerts:** retries, stalls, resumed downloads, a verification failure fixed by re-download, holiday skips. These go to JSONL logs and an optional daily digest line.
- **Alerts (Slack webhook + email fallback):** (a) any trading day not `INGESTED` by the SLA of T+1 09:00 IST — the only "data missing" signal a human ever needs; (b) 3× identical-bytes verification failure; (c) block signature persisting > 4 h despite backoff (means: call IT about the proxy); (d) RESTATEMENT detected; (e) disk < 10 GB, unwritable ledger, or lease conflict.
- **Dedup:** the `alerts` table keys each condition; re-fire only every 24 h while unresolved, and send an auto-resolve note when the condition clears. No repeats, no pager fatigue.
- **Dead-man switch:** the box that is down cannot alert about itself, so each successful cycle pings an external healthchecks.io-style URL with a 26 h grace period. Silence → external alert. This closes the "whole machine died quietly" hole.

## 9. New-machine takeover

`raw/` (plus its sidecars) is the only irreplaceable artifact — the ledger and dataset are both derivable from it — and it is rsync/rclone'd nightly to a second location along with a WAL-safe `sqlite3 .backup` snapshot.

Takeover: (1) install pinned code + config on the new box; (2) copy or mount the data dir (worst case: just `raw/`); (3) `pipeline rebuild-ledger` — every `raw/` file whose bytes match its sidecar hash → `VERIFIED`, every dataset partition with a `_SUCCESS` marker matching that hash → `INGESTED`, everything expected-but-absent → `PENDING`; add `--verify-all` to re-hash the whole copy after an untrusted transfer; (4) enable the timer. The first `pipeline run` resumes any `.part`, backfills the gap since the last file, and the lease guarantees safety even if the old machine wasn't stopped yet.

## Sanity check — requirement → enforcing mechanism

| Requirement | Mechanism |
|---|---|
| Nothing lost | Calendar-derived expected set makes absence visible; SLA alert + `gaps`; immutable append-only `raw/`; nightly offsite copy |
| Nothing double-ingested | `(trade_date, sha256)` idempotency key; rename-into-place partitions or single-transaction SQL; `INSERT OR IGNORE` ledger; no appends; lease against concurrent runners |
| Corrupt data never enters | Verify-then-rename gate (size, CRC, strict parse, embedded-date match, sha256) before anything touches `raw/`; quarantine; 200-with-HTML proxy-page detection |
| Alert only when actionable | Retries/stalls are silent; alerts only on SLA breach, persistent block, repeated identical corruption, restatement, ops faults; deduped with auto-resolve; dead-man switch for total silence |
| New machine mid-history | Self-describing `raw/` + sidecars + `_SUCCESS` markers; `rebuild-ledger`; lease steal; resumable `.part` files |

Crash-safety spine, restated in one line: durable facts only in the ledger, filesystem-before-ledger ordering, atomic renames on one mount, and idempotent re-checks to close every crash window.

result: Delivered a concrete resume-safe EOD ingestion design — staged-download/verify/rename flow with Range-resume and stall watchdog, sha256-keyed idempotent ingest, rebuildable SQLite ledger with lease, SLA-and-deadman-only alerting, and a rebuild-ledger takeover path for new machines.

----- ANSWER G018 (task MG03) -----
# MG-03: Resume-Safe Daily Exchange Data Ingestion Pipeline

## Design Intent
Pull end-of-day files from an exchange archive through a hostile proxy (0.7 MB/s, random stalls, IP blocks, timeouts) such that:
- **No data loss:** every file fetched is recorded; crashes/restarts resume exactly where they stopped.
- **No double-ingestion:** same file processed twice → idempotent outcome (not duplicate rows).
- **No corruption:** invalid/incomplete downloads are caught before entering the live dataset.
- **Minimal alerts:** humans notified only when recovery action is actually required.
- **Machine-independent:** new laptop takes over mid-history by reading the state ledger, no manual re-sync.

---

## Architecture: Five-Layer Pipeline

```
┌─ LEDGER LAYER (single source of truth for all state)
│  ├─ state_ledger.jsonl    [daily file status, hashes, ingestion timestamp, error log]
│  ├─ download_log.jsonl    [every GET attempt, proxy stall/timeout/IP-block events]
│  └─ alert_log.jsonl       [human-facing escalations with context+recommendation]
│
├─ DOWNLOAD LAYER (resumable, proxy-resilient)
│  ├─ Staging/quarantine/   [temp .zip/.csv files, in-flight or awaiting validation]
│  ├─ retry_queue.json      [files that need re-fetch, with backoff-state]
│  └─ (proxy retry: exponential backoff 1s→2s→4s→8s, max 12 attempts over 4h)
│
├─ VALIDATION LAYER (integrity check before live)
│  ├─ [Hash match: archive metadata SHA256 vs. downloaded file]
│  ├─ [Schema check: expected columns, row count sanity, timestamp ranges]
│  ├─ [Corruption signal: > N missing rows, timestamp gaps, repeated prices]
│  └─ [Quarantine verdict: PASS → promote to live, FAIL → alert + human review]
│
├─ INGESTION LAYER (atomic, idempotent)
│  ├─ Live/current/          [parquet/SQL table, single source of truth for analytics]
│  ├─ On ingestion: upsert-by-key (date, ticker, contract) so re-running same file = no duplicates
│  └─ Rollback-safe: pre-ingest snapshot + transaction log so recovery is procedural
│
└─ MONITORING LAYER (ledger-driven diagnostics)
   ├─ Daily health-check: count(PENDING) + count(FAILED_VALIDATION) + backoff-queue length
   ├─ Machine-takeover bootstrap: read state_ledger, find last INGESTED row, resume from next date
   └─ Proxy-failure pattern detection: IP block → escalate, repeated timeouts → alert ops
```

---

## State Ledger Schema (source of truth)

**File:** `state_ledger.jsonl` (one JSON object per line, one per date/file)

```json
{
  "date": "2026-07-11",
  "filename": "bhavcopy_11-07-2026.zip",
  "archive_url": "https://nsearchives.nseindia.com/content/historical/...",
  "status": "INGESTED",
  "download_attempts": 3,
  "download_start_utc": "2026-07-11T15:30:00Z",
  "download_complete_utc": "2026-07-11T15:32:15Z",
  "file_size_bytes": 2345678,
  "archive_sha256": "a1b2c3d4e5f6...",
  "downloaded_sha256": "a1b2c3d4e5f6...",
  "hash_match": true,
  "validation_checks": {
    "schema_ok": true,
    "row_count": 1523,
    "expected_row_count_min": 1400,
    "expected_row_count_max": 1700,
    "timestamp_coverage": "2026-07-11T09:15:00Z to 2026-07-11T15:30:00Z",
    "corruption_signals": []
  },
  "validation_status": "PASS",
  "validation_completed_utc": "2026-07-11T15:33:00Z",
  "ingestion_start_utc": "2026-07-11T15:33:05Z",
  "ingestion_complete_utc": "2026-07-11T15:33:45Z",
  "ingestion_status": "SUCCESS",
  "rows_ingested": 1523,
  "rows_duplicate_skipped": 0,
  "notes": "Proxy stall attempt 2; recovered with 4s backoff",
  "error_log": []
}
```

**File:** `download_log.jsonl` (append-only, one line per download attempt)

```json
{
  "timestamp_utc": "2026-07-11T15:30:00Z",
  "filename": "bhavcopy_11-07-2026.zip",
  "attempt": 1,
  "status": "TIMEOUT",
  "proxy_event": "read timeout after 45s (0 bytes received)",
  "bytes_received": 0,
  "retry_after_seconds": 1
}
```

**File:** `alert_log.jsonl` (append-only, one line per human escalation)

```json
{
  "timestamp_utc": "2026-07-11T16:45:00Z",
  "severity": "WARNING",
  "code": "VALIDATION_FAILED",
  "filename": "bhavcopy_11-07-2026.zip",
  "context": {
    "row_count": 523,
    "expected_min": 1400,
    "corruption_signal": "50% fewer rows than baseline"
  },
  "recommendation": "Manual download from archive; inspect for NSE maintenance window",
  "human_action_required": true,
  "escalation_channel": "ops-engineer-manoj-pillai"
}
```

---

## Download Layer: Proxy-Resilient Fetching

### Retry Strategy (Non-Negotiable)

1. **Exponential Backoff:** 1s → 2s → 4s → 8s → 16s → 32s → 64s → 128s (doubling, capped at 2min)
2. **Max Attempts:** 12 retries = ~21 min cumulative wait
3. **Timeout per attempt:** 120 seconds (no partial completion; if stall detected, abort immediately)
4. **Proxy event categorization:**
   - `TIMEOUT`: no bytes after 120s → backoff + retry
   - `PARTIAL_DOWNLOAD`: bytes received < file_size_bytes by >1% → backoff + retry (discard incomplete)
   - `IP_BLOCK`: HTTP 429 or 403 from proxy → alert ops, backoff 5 min, retry once
   - `SSL_ERROR`: proxy certificate issue → alert ops immediately
   - `CONNECTION_RESET`: proxy closed mid-transfer → backoff + retry

### Quarantine Directory Structure

```
Staging/quarantine/
├── pending/           # Files being downloaded
│   └─ bhavcopy_11-07-2026.zip.partial
├── validated/         # Files passed integrity check, ready to ingest
│   └─ bhavcopy_11-07-2026.zip
├── failed/            # Files failed validation, awaiting human review
│   └─ bhavcopy_11-07-2026.zip.FAILED_<reason>
└── archive/           # Successfully ingested files (kept for 90 days, then purged)
    └─ bhavcopy_11-07-2026.zip
```

### Download Flow (Pseudocode)

```python
def download_file(date, url):
    ledger_entry = read_ledger(date)
    
    if ledger_entry and ledger_entry.status in ["INGESTED", "VALIDATED"]:
        return  # Already done, skip
    
    if ledger_entry and ledger_entry.status == "DOWNLOADING":
        # Crash recovery: check if partial file exists
        if pending_file_exists():
            attempt_count = ledger_entry.download_attempts
        else:
            attempt_count = 0
    else:
        attempt_count = 0
    
    for attempt in range(12):  # Max 12 attempts
        try:
            backoff_seconds = min(1 * (2 ** attempt), 120)
            if attempt > 0:
                sleep(backoff_seconds)
            
            response = requests.get(
                url,
                timeout=120,
                stream=True,
                verify=False  # Corporate proxy cert issue
            )
            
            expected_size = get_archive_metadata(date).file_size_bytes
            
            # Stream download with size check
            bytes_received = 0
            with open(f"quarantine/pending/{filename}.partial", "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bytes_received += len(chunk)
                    
                    # Detect short-read stall (no data for 30s)
                    if time_since_last_byte() > 30:
                        raise TimeoutError("No data for 30s")
            
            # Check final size
            if bytes_received < expected_size * 0.99:
                raise ValueError(f"Partial download: {bytes_received}/{expected_size}")
            
            # Atomic rename to validated queue
            os.rename(
                f"quarantine/pending/{filename}.partial",
                f"quarantine/validated/{filename}"
            )
            
            # Log success
            log_download_event(date, "SUCCESS", bytes_received, attempt)
            update_ledger(date, status="VALIDATED", hash=compute_sha256(file))
            return
            
        except (requests.Timeout, ConnectionError, TimeoutError) as e:
            log_download_event(date, "TIMEOUT", bytes_received, attempt, str(e))
            if attempt == 11:  # Last attempt failed
                log_alert("DOWNLOAD_FAILED", date, f"12 retries exhausted: {e}")
                update_ledger(date, status="FAILED_DOWNLOAD", error=str(e))
        except Exception as e:
            log_alert("DOWNLOAD_ERROR", date, f"Attempt {attempt}: {e}")
            if "429" in str(e) or "403" in str(e):
                break  # Don't retry IP blocks; wait for ops to intervene
```

---

## Validation Layer: Corruption Detection

### Pre-Ingestion Validation Checklist

**Run immediately after download completes; before any database touch.**

1. **Hash Verification (against archive metadata)**
   - Download `bhavcopy_11-07-2026.zip` and read its SHA256 from NSE API/metadata endpoint
   - Compute SHA256 of downloaded file
   - If mismatch → move to `failed/` + log alert `HASH_MISMATCH`

2. **Schema & Structure Check**
   - Extract ZIP and check expected columns (SYMBOL, OPEN, HIGH, LOW, CLOSE, VOLUME, etc.)
   - If columns missing → `SCHEMA_INVALID`
   - If CSV encoding not UTF-8 → `ENCODING_ERROR`

3. **Row Count Sanity**
   - Load row count from file
   - Compare to baseline (e.g., ~1500 for NSE bhavcopy on a normal trading day)
   - If count < 1400 or > 1700 (outside normal range) → flag `ROW_COUNT_ANOMALY`
   - If count < 100 → automatic `VALIDATION_FAIL` (clearly corrupted)

4. **Timestamp & Time-Range Check**
   - Extract min/max timestamp from data
   - Should span roughly 09:15 to 15:30 IST (6h window)
   - If all timestamps identical → flag `TIMESTAMP_ANOMALY`
   - If spans < 1h or > 10h → flag `TIME_RANGE_ANOMALY`

5. **Price Sanity**
   - For each row: CLOSE should be within ±30% of OPEN (extreme single-day move = data error)
   - For NIFTY: should be between 10,000 and 30,000 (known range, adjust as needed)
   - Count rows with nonsensical prices (0, NULL, extreme outliers)
   - If > 5% of rows fail → flag `PRICE_CORRUPTION`

6. **Duplicate Detection**
   - Check for duplicate (SYMBOL, DATE, TIME) tuples
   - If found → flag `DUPLICATE_ROWS` (but do NOT fail; log for human review)

### Validation Outcome

**PASS:** All checks green → move file to `quarantine/validated/` → proceed to ingestion

**FAIL:** Any check red with `human_action_required=true`:
- Move file to `quarantine/failed/<filename>.FAILED_<code>`
- Log alert with severity=WARNING or ERROR
- Example: `bhavcopy_11-07-2026.zip.FAILED_HASH_MISMATCH`

**Examples of fail codes that require human intervention:**
- `HASH_MISMATCH` (file corrupted in transit or on archive)
- `SCHEMA_INVALID` (NSE changed format)
- `ROW_COUNT_ANOMALY` with < 100 rows
- `IP_BLOCK` (too many retries exhausted)

**Examples of fail codes that auto-retry or skip:**
- `TIMESTAMP_ANOMALY` on a holiday → log as INFO, skip date, move to next (ops can manually verify)

---

## Ingestion Layer: Atomic & Idempotent

### Pre-Ingestion Snapshot

Before touching the database:

```python
def ingest_file(date, filepath):
    ledger_entry = read_ledger(date)
    
    if ledger_entry.status == "INGESTED":
        return  # Already done, skip
    
    # Create rollback snapshot
    snapshot_file = f"backups/pre_ingest_{date}_v{int(time.time())}.parquet"
    existing_data = read_live_table().filter(date=date)
    existing_data.to_parquet(snapshot_file)
    
    # Upsert with idempotent key: (date, ticker, contract_code)
    new_data = read_quarantine_file(filepath)
    
    # Deduplicate: if same (date, ticker, contract) already in live table, replace
    live_table = read_live_table()
    live_table_minus_date = live_table.filter(date != date)
    
    combined = pd.concat([live_table_minus_date, new_data])
    combined = combined.drop_duplicates(subset=["date", "ticker", "contract"], keep="last")
    
    # Atomic write (SQL transaction or Parquet rewrite with atomic rename)
    combined.to_parquet(f"live_table_new.parquet")
    os.rename("live_table_new.parquet", "live_table.parquet")  # Atomic on NTFS
    
    # Mark as ingested in ledger
    update_ledger(
        date,
        status="INGESTED",
        rows_ingested=len(new_data),
        snapshot_file=snapshot_file
    )
```

### Rollback Procedure (if needed)

If human discovers corruption AFTER ingestion:
```python
def rollback_date(date):
    snapshot_file = read_ledger(date).snapshot_file
    snapshot_data = read_parquet(snapshot_file)
    
    live_table = read_live_table()
    live_table_minus_date = live_table.filter(date != date)
    
    restored = pd.concat([live_table_minus_date, snapshot_data])
    restored.to_parquet("live_table_new.parquet")
    os.rename("live_table_new.parquet", "live_table.parquet")
    
    update_ledger(date, status="ROLLED_BACK_MANUAL", notes="Human intervention: <reason>")
    log_alert("ROLLBACK_EXECUTED", date, f"Rolled back to {snapshot_file}")
```

---

## Resume Safety: Machine Takeover

### Bootstrap Procedure (new machine)

When a new laptop takes over:

```python
def bootstrap_new_machine():
    # 1. Read state ledger from network share
    ledger = read_state_ledger()
    
    # 2. Find last successfully ingested date
    last_ingested = ledger[ledger.status == "INGESTED"].sort_by("date").tail(1)
    next_date_to_fetch = last_ingested.date + timedelta(days=1)
    
    # 3. Check for stuck downloads (status == DOWNLOADING with timestamp > 24h ago)
    stuck = ledger[
        (ledger.status == "DOWNLOADING") &
        (now() - ledger.download_start_utc > timedelta(hours=24))
    ]
    for entry in stuck:
        # Clean up partial file and reset status
        os.remove(f"quarantine/pending/{entry.filename}.partial")
        update_ledger(entry.date, status="READY_TO_DOWNLOAD", notes="Resumed after crash")
    
    # 4. Check validation queue (status == VALIDATED)
    validated = ledger[ledger.status == "VALIDATED"]
    for entry in validated:
        ingest_file(entry.date, f"quarantine/validated/{entry.filename}")
    
    # 5. Start download cycle from next_date_to_fetch
    print(f"Resume from: {next_date_to_fetch}")
    return next_date_to_fetch
```

### New Machine Guarantees

- **No data loss:** every file that made it to `quarantine/validated/` will be ingested, even if old machine crashed
- **No double-ingestion:** ledger uniquely identifies each (date, file); re-ingesting same file is idempotent
- **No manual sync:** state ledger is single source of truth; new machine reads it and continues

---

## Alert Rules & Escalation (Concrete Thresholds)

**Alerts go to `alert_log.jsonl`; humans are notified only for these scenarios:**

| Condition | Severity | Action | Escalate To |
|-----------|----------|--------|-------------|
| Download fails 12 consecutive times (21 min elapsed) | ERROR | Manual re-download needed; check NSE status page | `ops-engineer-manoj-pillai` |
| Validation check fails (hash mismatch, schema invalid, row count < 100) | WARNING | File moved to `failed/`; human inspects NSE archive integrity | ops |
| IP block (HTTP 429/403) detected | ERROR | Pause all downloads; alert ops to contact proxy admin | ops |
| Consecutive 3 timeout events within 30 min | WARNING | Proxy is degraded; log pattern + recommend manual intervention | ops |
| Row count anomaly (< 1400) but ≥ 100 | INFO | Log as possible NSE maintenance; auto-skip, allow retry next day | (no escalation) |
| Timestamp anomaly on a holiday | INFO | Expected; skip date, proceed to next | (no escalation) |
| Pre-ingestion snapshot file missing | CRITICAL | Cannot guarantee rollback safety; halt pipeline | ops + cio-rajan-mehta |
| Ledger write fails (disk full, permissions) | CRITICAL | State machine broken; manual recovery needed | ops |

**Alert format (to be sent via Slack/email):**

```
[MG-03 ALERT] severity=ERROR | code=DOWNLOAD_FAILED
Date: 2026-07-11 | File: bhavcopy_11-07-2026.zip
Event: 12 download attempts exhausted after 21 minutes.
Proxy timeline: TIMEOUT (45s), TIMEOUT (2min), TIMEOUT (4min), ..., TIMEOUT (128s)
Last error: read timeout after 120s (0 bytes received)
Recommendation: Check NSE archive status; if available, trigger manual download.
Action: File placed in quarantine/failed/ for manual review.
Ledger: state_ledger.jsonl line 1523 (status=FAILED_DOWNLOAD)
```

---

## Monitoring & Diagnostics

### Daily Health Check (run at 16:30 IST)

```python
def daily_health_check():
    ledger = read_state_ledger()
    today = date.today()
    
    # Count files in each state
    status_counts = ledger.groupby("status").size()
    
    pending = ledger[ledger.status.isin(["READY_TO_DOWNLOAD", "DOWNLOADING"])].shape[0]
    failed = ledger[ledger.status == "FAILED_DOWNLOAD"].shape[0]
    backoff_queue = read_retry_queue()
    
    # Health dashboard
    report = {
        "date": today,
        "files_pending": pending,
        "files_failed": failed,
        "files_in_backoff_queue": len(backoff_queue),
        "status_breakdown": status_counts.to_dict(),
        "last_ingested_date": ledger[ledger.status == "INGESTED"].date.max(),
        "lag_days": (today - ledger[ledger.status == "INGESTED"].date.max()).days,
    }
    
    # Alert if lag > 2 days
    if report["lag_days"] > 2:
        log_alert("INGESTION_LAG", f"Data pipeline {report['lag_days']} days behind", "WARNING")
    
    return report
```

### Diagnostic Commands for Ops

```bash
# View recent alerts
tail -20 alert_log.jsonl | jq '{timestamp, severity, code, filename}'

# Find all failed validations
grep "VALIDATION_FAILED" state_ledger.jsonl | jq '{date, filename, validation_status}'

# Identify proxy patterns (IP blocks, timeouts)
grep -E "IP_BLOCK|TIMEOUT" download_log.jsonl | jq '{timestamp, attempt, status, proxy_event}' | sort | uniq -c

# Check retry queue backoff state
cat retry_queue.json | jq '.[] | {filename, attempt, backoff_seconds}'

# Recover from crash (find stuck downloads)
jq 'select(.status == "DOWNLOADING" and now - .download_start_utc > 86400)' state_ledger.jsonl

# List files awaiting human review
ls -la quarantine/failed/ | grep "FAILED_"
```

---

## Example: Complete 24-Hour Cycle

**Scenario:** Friday 2026-07-11, normal trading day. Proxy has 1 stall. File is valid. New machine takes over Saturday morning.

### Friday 15:35 IST (09:05 UTC) - Download Starts

```
Event: Daily scheduler triggers ingest_job.py
Action: Read ledger → find date=2026-07-11 not yet present
Action: Download bhavcopy_11-07-2026.zip (3.2 MB) from NSE
Attempt 1: Read timeout after 45s (0 bytes received) → log download_log.jsonl
Action: Exponential backoff = 1 second
Attempt 2: SUCCESS, 3.2 MB received in 5 minutes
Action: Atomic rename to quarantine/validated/
Ledger: { date: "2026-07-11", status: "VALIDATED", download_attempts: 2 }
```

### Friday 15:40 IST (09:10 UTC) - Validation Runs

```
Action: Schema check PASS (all columns present)
Action: Row count = 1523 (within 1400-1700 range) PASS
Action: Timestamp range 09:15 to 15:29 (normal) PASS
Action: Hash match PASS (SHA256 matches NSE metadata)
Action: Price sanity PASS (all NIFTY prices 17500-18100)
Ledger: { status: "VALIDATED", validation_status: "PASS" }
```

### Friday 15:45 IST (09:15 UTC) - Ingestion Runs

```
Action: Create snapshot: backups/pre_ingest_2026-07-11_v1689065100.parquet
Action: Read live_table.parquet (previous 500+ days)
Action: Deduplicate new data against live table by (date, ticker, contract)
Action: Atomic write to live_table_new.parquet (1523 new rows)
Action: Rename to live_table.parquet (atomic on Windows NTFS)
Ledger: { status: "INGESTED", rows_ingested: 1523, snapshot_file: "backups/pre_ingest_2026-07-11_v1689065100.parquet" }
Action: Move file to quarantine/archive/
```

### Saturday 09:00 IST - New Machine Boots Up

```
Event: Shreyas switches to new laptop with cloud-synced /state_ledger.jsonl
Action: bootstrap_new_machine() reads ledger from network share
Action: Finds last_ingested = 2026-07-11
Action: next_date = 2026-07-12 (today)
Action: Checks for stuck downloads → none found
Action: Checks for validated files awaiting ingest → none found
Action: Scheduler resumes download cycle for 2026-07-12
Guarantee: Zero data loss, zero double-ingest, zero manual re-sync
```

---

## File Checklist (All Required for Resume Safety)

| File | Purpose | Location | Format | Append/Overwrite |
|------|---------|----------|--------|------------------|
| `state_ledger.jsonl` | Source of truth for all files | `logs/` | JSONL | Append per date |
| `download_log.jsonl` | Every download attempt (diagnostic) | `logs/` | JSONL | Append per attempt |
| `alert_log.jsonl` | Human escalations only | `logs/` | JSONL | Append per alert |
| `retry_queue.json` | Files needing re-fetch (backoff state) | `state/` | JSON | Overwrite (atomic) |
| `quarantine/pending/<file>.partial` | In-flight download | `quarantine/` | Binary | Atomic rename on success |
| `quarantine/validated/<file>` | Passed validation, ready to ingest | `quarantine/` | ZIP/CSV | Atomic rename from pending |
| `quarantine/failed/<file>.FAILED_<code>` | Failed validation, awaiting review | `quarantine/` | ZIP/CSV | Placed by validator |
| `quarantine/archive/<file>` | Successfully ingested (90-day retention) | `quarantine/` | ZIP/CSV | Moved after ingest |
| `backups/pre_ingest_<date>_v<ts>.parquet` | Rollback snapshot for this date | `backups/` | Parquet | One per ingest |
| `live_table.parquet` | Current live dataset | `data/` | Parquet | Atomic rename after ingest |

---

## Edge Cases & Recovery

### Case 1: Machine Crashes During Download

**State:** `state_ledger.jsonl` has status=DOWNLOADING, partial file exists in `quarantine/pending/`

**Recovery (automatic on restart):**
1. Read ledger → find status=DOWNLOADING with timestamp > 24h ago
2. Delete `quarantine/pending/<file>.partial`
3. Reset ledger status to READY_TO_DOWNLOAD
4. Retry from attempt 0

### Case 2: Validation Fails; Operator Manually Fixes Source

**State:** File in `quarantine/failed/bhavcopy_11-07-2026.zip.FAILED_HASH_MISMATCH`

**Operator Action:**
1. Download file again from archive (or get from op who has it)
2. Copy to `quarantine/validated/bhavcopy_11-07-2026.zip` (overwrite)
3. Update ledger: `{ status: "VALIDATED", validation_status: "PASS", notes: "Manual fix by ops" }`
4. Scheduler re-runs ingestion

### Case 3: Proxy IP Block; Operator Waits, Then Retries

**State:** `alert_log.jsonl` has code=IP_BLOCK, ledger has status=FAILED_DOWNLOAD

**Operator Action:**
1. Contact proxy admin; IP block lifted after 30 min
2. Reset ledger: `{ status: "READY_TO_DOWNLOAD", download_attempts: 0 }`
3. Scheduler re-runs download from attempt 0

### Case 4: Holiday (NSE Closed); File Is Valid But Has 0 Rows

**State:** Validation detects row_count=0, timestamp_range invalid

**Logic:**
- Operator confirms NSE was closed that day
- Manually set ledger: `{ status: "INGESTED", notes: "Holiday (NSE closed)", rows_ingested: 0 }`
- Scheduler moves to next date

---

## Concurrency & Lock Safety

**Single-threaded guarantee:** Scheduler runs one date at a time; no parallel downloads.

**Ledger write safety:** All updates use `flock` (file-level lock) or database transaction:
```python
import fcntl

def update_ledger(date, **fields):
    with open("state_ledger.jsonl", "a+") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.seek(0)
        # Read all entries, update the one matching date, write back
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

**Live table write safety:** Atomic rename (Windows NTFS supports atomic-rename semantics):
```python
os.rename("live_table_new.parquet", "live_table.parquet")  # Atomic
```

---

## Compliance Checklist

- [x] **Nothing lost:** Every file fetched is recorded in state_ledger before touch
- [x] **No double-ingest:** Idempotent upsert by (date, ticker, contract); same file→same outcome
- [x] **No corruption:** Pre-ingestion validation (hash, schema, row count, price sanity); failed files isolated
- [x] **Minimal alerts:** Only 8 alert codes; auto-recovery for common failures (timeouts, row anomalies)
- [x] **Resume-safe:** Ledger + snapshots + retry queue allow new machine to take over mid-history with zero manual sync
- [x] **Concrete mechanisms:** Files, ledgers, checksums, retry logic, alert rules all specified with examples
- [x] **Operator diagnostics:** Health check, recovery commands, crash scenarios documented

---

## Implementation Roadmap

1. **Phase 1 (Day 1):** State ledger + download layer with exponential backoff
2. **Phase 2 (Day 2):** Validation layer (hash, schema, row count checks)
3. **Phase 3 (Day 3):** Ingestion layer (snapshot, upsert, atomic rename)
4. **Phase 4 (Day 4):** Bootstrap procedure + resume testing (simulate crashes)
5. **Phase 5 (Day 5):** Alert rules + operator playbooks + diagnostics
6. **Phase 6 (Day 6):** Production deployment + 2-week live burn-in

---

## References

- NSE Archive API: `https://nsearchives.nseindia.com/content/historical/`
- SHA256 Metadata: NSE provides in API response; verify before ingestion
- Proxy Config: Use `requests.Session()` with `truststore.inject_into_ssl()` (see CLAUDE.md §ENVIRONMENT)
- Holiday Calendar: Sync daily from NSE trading calendar (auto-detect 0-row files)

----- ANSWER G003 (task MG03) -----
# Resume-Safe Daily EOD Ingestion Pipeline

**Scope:** pull end-of-day exchange archive files (e.g. NSE bhavcopy zips) through an unreliable corporate proxy (~0.7 MB/s, random stalls, occasional IP blocks). Guarantees: no loss, no double-ingest across crashes/restarts, no corrupt file ever enters the dataset, human alerted only on genuine action, a fresh machine can resume mid-history.

The whole design rests on one idea: **the pipeline holds no state in memory.** Every fact about "what has happened" lives in files that survive `kill -9`. A crash is indistinguishable from a fresh start — both just read the ledger and continue.

---

## 1. On-disk layout (the state IS the filesystem)

```
data_office/eod/
├── manifest/
│   ├── expected.jsonl          # what SHOULD exist per trading day (the plan)
│   └── ledger.jsonl            # append-only event log (the truth)
├── work/                       # partial downloads, never read by consumers
│   └── <date>__<source>.part
├── raw/                        # verified, immutable exchange files
│   └── <yyyy>/<mm>/<date>__<source>.zip
├── raw/.sha256/
│   └── <date>__<source>.zip.sha256   # sidecar checksum, written with the file
├── curated/                    # parsed parquet, the dataset consumers read
│   └── <yyyy>/<mm>/<date>.parquet
├── locks/
│   └── ingest.lock             # single-writer lock (PID + hostname + mtime)
└── alerts/
    └── outbox.jsonl            # dedup'd alert queue
```

Rules that make this safe:
- **`raw/` and `curated/` are append-only and immutable.** A file appears there only after it is fully verified. Nothing is ever edited in place.
- **`work/` is disposable.** Anything in `work/` on startup is a half-download from a crash and is deleted (or resumed via HTTP Range — see §4).
- **Consumers only ever read `curated/`.** They never see `work/` and never see a `raw/` file mid-write.

---

## 2. The two manifests

### `expected.jsonl` — the plan (idempotent to regenerate)
One line per (trading_day, source), generated from the exchange trading calendar. Regenerating it is a pure function of the calendar, so it is safe to rebuild on any machine.

```json
{"date":"2026-07-13","source":"nse_bhav_sec","url":"https://nsearchives.nseindia.com/.../sec_bhavdata_full_130726.csv","required":true}
{"date":"2026-07-13","source":"nse_bhav_fo","url":"https://nsearchives.nseindia.com/.../fo130726.zip","required":true}
```
Trading-holiday days simply have no rows → nothing is "missing" on a holiday, so no false alerts.

### `ledger.jsonl` — the truth (append-only event log)
Every state transition is one appended line. **We never rewrite lines**; the current state of a file = the last event for its `(date,source)` key. Append-only + fsync makes it crash-atomic (a torn final line is detected by JSON-parse failure and dropped on read).

```json
{"ts":"2026-07-13T20:01:03Z","date":"2026-07-13","source":"nse_bhav_fo","event":"DOWNLOAD_OK","bytes":184322,"sha256":"9f...","attempt":2}
{"ts":"2026-07-13T20:01:05Z","date":"2026-07-13","source":"nse_bhav_fo","event":"VERIFY_OK","rows":184,"schema":"fo_v3"}
{"ts":"2026-07-13T20:01:06Z","date":"2026-07-13","source":"nse_bhav_fo","event":"INGEST_OK","curated":"curated/2026/07/2026-07-13.parquet"}
```

Event vocabulary (a file marches monotonically forward):
`QUEUED → DOWNLOAD_OK → VERIFY_OK → INGEST_OK` (terminal-success)
Failure branches: `DOWNLOAD_FAIL`, `VERIFY_FAIL`, `IP_BLOCKED`, `PERMANENTLY_MISSING`, `ALERTED`.

**Why this gives no-double-ingest for free:** before doing any work on `(date,source)`, the runner folds the ledger to that key's last event. If it's `INGEST_OK`, skip. This is the *"skip-completed rerun rule"* — a re-run, a cross-session resume, or a second machine simply re-reads the ledger and does nothing already done. (Firm history: cross-session resume that ignored this once re-ran and overwrote a subset — hence the append-only ledger fold is mandatory, never a "did the file exist?" check.)

---

## 3. Single-writer lock (no two runners collide)

`locks/ingest.lock` written atomically (`open O_CREAT|O_EXCL`) containing `{"pid":…,"host":…,"started":…,"heartbeat":…}`. The runner refreshes `heartbeat` every 30 s.
- On startup, if the lock exists **and** heartbeat is < 5 min old → another runner is alive → exit quietly (no alert).
- If heartbeat is stale (> 5 min) → previous runner died → **steal the lock** (log `LOCK_STOLEN`) and proceed. Because all real state is in the ledger, stealing is safe: the dead runner left at most a `work/*.part` file, which we discard.

This is what lets a **new machine take over mid-history**: point it at the same `data_office/eod/` (shared drive / synced folder / object store), it acquires or steals the lock, folds the ledger, and continues from the first non-`INGEST_OK` expected row.

---

## 4. Download stage — beating the flaky proxy

Per the environment: sequential `requests.Session()` only (threads stall behind the proxy), `truststore.inject_into_ssl()`, ~1.2 s spacing, cookie warm-up for NSE.

For each expected row whose ledger state is below `DOWNLOAD_OK`:

1. **Download to `work/<key>.part`, never to `raw/`.** Consumers can never see it.
2. **Streamed, resumable, stall-detected:**
   - `stream=True`, write in 64 KB chunks.
   - **Stall watchdog:** if no chunk arrives for `read_timeout = 45 s`, abort this attempt (this is the "random stall" case — a socket that hangs forever otherwise).
   - **HTTP Range resume:** on retry, if `<key>.part` exists and server sent `Accept-Ranges: bytes`, send `Range: bytes=<partsize>-` and append. Saves re-pulling MBs already through the 0.7 MB/s pipe. If the server ignores Range (200 not 206), truncate `.part` and restart clean.
3. **Retry policy (bounded, jittered exponential backoff):** delays `5s, 20s, 60s, 180s`, max 4 attempts. Each attempt logs `DOWNLOAD_FAIL` with the reason. Distinct handling:
   - Timeout / connection reset / `ChunkedEncodingError` → normal retry.
   - **HTTP 403 / 429 / connection-refused burst → treat as IP block:** log `IP_BLOCKED`, stop the whole run for that source, and back off long (see §7). Do **not** burn all attempts hammering a block — that deepens it.
4. On a complete download: compute SHA-256 of the `.part`, log `DOWNLOAD_OK` with bytes + sha.

Nothing is promoted out of `work/` yet — a byte-complete download is still not trusted.

---

## 5. Verify stage — corrupt files can never enter the dataset

This is the gate that makes "corrupt downloads never enter the dataset" true. A file passes **all** checks or it is deleted from `work/` and marked `VERIFY_FAIL`.

1. **Size sanity:** bytes > a per-source floor (e.g. bhavcopy zip > 20 KB). Catches proxy error-pages / truncation (a 4 KB "Access Denied" HTML page fails here).
2. **Content-type / magic bytes:** first bytes match the expected container (`PK\x03\x04` for zip; not `<!DOCTYPE html` / `<html`). Catches the proxy returning an HTML block page with HTTP 200.
3. **Container integrity:** `zipfile.testzip()` (or gzip CRC) returns clean — every entry's CRC matches. A partial/corrupt zip fails here even if byte-count looked plausible.
4. **Schema + row sanity (parse to staging):** open the inner CSV, assert expected columns present (per `05_DATA_OFFICE/DATA_QUALITY_RULES.md` schema helpers / `04_RND_LAB/lib/guards.py`), row count > per-source floor, date column == the expected date (no wrong-day file), no all-zero/empty frame.
5. **Domain spot-check (D-009):** a couple of known-value assertions — e.g. NIFTY/ RELIANCE row present, `CONTRACTS>0` gate for F&O legs, close within a sane band vs the prior curated day (a 10x jump = fat-finger/bad file → fail). This is the sample verification the firm requires before any new data is used.

Only on all-pass:
- Write sidecar `raw/.sha256/<key>.zip.sha256`.
- **Atomically publish:** `os.replace(work/<key>.part → raw/yyyy/mm/<key>.zip)` — `os.replace` is atomic on the same filesystem, so `raw/` never contains a half file even if power dies mid-move.
- Log `VERIFY_OK` with rows + schema version.

A crash between `DOWNLOAD_OK` and `VERIFY_OK` is harmless: on restart the ledger shows `DOWNLOAD_OK`, the `.part` is re-verified (checksum matches the logged sha → skip re-download), and it proceeds.

## 6. Ingest stage — atomic, idempotent parquet write

1. Parse verified `raw/` file → dataframe (with the firm's landmine guards: HF tz fix, pre-open filter, expiry-day settle handling, etc. as applicable to the source).
2. Write to `curated/yyyy/mm/<date>.parquet.tmp`, then `os.replace` to the final name — atomic publish again. Consumers reading `curated/` either see the old file or the complete new one, never a partial.
3. Log `INGEST_OK` with the curated path. This is the terminal state; the `(date,source)` key is now permanently "done" and will be skipped by every future run.

Idempotency guarantee: because the final ledger event, not the presence of a file, decides "done", re-running after `INGEST_OK` is a no-op; re-running after `VERIFY_OK` but before `INGEST_OK` re-parses the *already-verified* raw file (no re-download, no re-verify network cost) and republishes atomically — safe to repeat.

---

## 7. Alerts — only when a human must act

An alert fires **only** for states that automation cannot resolve on its own. Everything transient is retried silently. Alerts go to `alerts/outbox.jsonl` first (dedup key = `date|source|reason`), then a single delivery step drains the outbox (email/push). Writing to the outbox before sending means a crash during send doesn't lose the alert, and dedup means a 3-day proxy outage produces **one** alert, not 300.

Alert **only** on:
- **`IP_BLOCKED` persists** past the long backoff and the next scheduled window (i.e. the block is not clearing itself) → *"proxy blocking archive host; needs home-network/VPN run."* This maps to the known landmine: office proxy blocks some NSE endpoints → human switches network.
- **`PERMANENTLY_MISSING`:** a `required` file still absent N hours after the exchange's normal publish time and after all retries → *"NSE has not published fo-bhav for 2026-07-13, or URL pattern changed."*
- **`VERIFY_FAIL` that is not transient:** same file fails integrity/schema on 2 independent fresh downloads → the source file itself is bad or the schema changed → human inspection. (One-off verify fail just retries; it does not alert.)
- **`SCHEMA_DRIFT`:** columns present but changed vs the registered schema → dataset guard would break downstream → human must update the parser.

Explicitly **no alert** for: another runner already holds the lock, a holiday with no expected rows, a single timed-out download that then succeeds, a stale lock that was cleanly stolen. These are normal operation.

Each alert line logs `ALERTED` to the ledger so it is never re-sent; a matching later success logs `RESOLVED` and (optionally) sends an all-clear.

---

## 8. The run loop (what actually executes each day)

Scheduled via the firm's cron cadence (e.g. `AngelDailyOptionCapture`-style, 15:45 / 20:00 / 23:00 IST — multiple windows so a missed/blocked earlier window is picked up later, each idempotent).

```
1. acquire-or-steal lock (else exit quietly)
2. sweep work/ : for each .part, if its logged DOWNLOAD_OK sha still matches keep for resume, else delete
3. regenerate expected.jsonl from trading calendar (idempotent)
4. fold ledger.jsonl -> current state per (date,source)     # single pass, tail is enough with periodic snapshot
5. build worklist = expected rows whose state != INGEST_OK, oldest-first   # <-- backfill & mid-history resume fall out here
6. for each item, sequentially:
       download (§4) -> verify (§5) -> ingest (§6), appending ledger events, honoring IP_BLOCKED backoff
7. drain alerts/outbox.jsonl (§7)
8. release lock
```

Because step 5 walks **all** not-yet-done expected days oldest-first, the same loop does daily ingest **and** history backfill **and** post-outage catch-up — no separate code path. A new machine on day 400 of history runs the identical loop and simply finds days 1–399 already `INGEST_OK` in the shared ledger.

---

## 9. Ledger compaction & portability (so it scales and travels)

- **Snapshot:** nightly, fold the full `ledger.jsonl` into `ledger.snapshot.json` (current state per key) and truncate the appended log to events since the snapshot. Fold cost stays O(recent), not O(all-history). The snapshot + tail reconstruct full state; both are plain files.
- **Portability / new-machine takeover:** the entire `data_office/eod/` tree is self-describing — ledger + snapshot + raw + sidecar checksums. Copy/sync it (rsync, shared drive, S3) to a new box; it acquires the lock and resumes. To *audit* an inherited dataset, re-hash each `raw/*.zip` against its `.sha256` sidecar and confirm a matching `INGEST_OK` in the ledger; any mismatch is re-verified/re-ingested.
- **Backup:** `raw/` + `manifest/` are the irreplaceable state (curated is regenerable from raw). Back those up per `99_OPS/BACKUP_POLICY.md`.

---

## 10. Failure-mode matrix (the guarantees, made concrete)

| Failure | What survives it | Mechanism |
|---|---|---|
| `kill -9` mid-download | no partial in dataset | download goes to `work/`, atomic `os.replace` only after verify |
| `kill -9` mid-ingest | no partial parquet | `.parquet.tmp` + atomic `os.replace`; ledger fold re-drives |
| crash mid-ledger-write | torn line ignored | append-only + JSON-parse-drop of torn tail; prior events intact |
| re-run / double schedule | no double-ingest | ledger fold → skip `INGEST_OK`; single-writer lock |
| proxy stall (hung socket) | run continues | 45 s read-timeout watchdog aborts the attempt |
| proxy IP block | no wasted hammering, human told once | `IP_BLOCKED` state, long backoff, dedup'd single alert |
| proxy HTML block-page (HTTP 200) | corrupt file rejected | magic-byte + size + zip-CRC checks in verify |
| truncated download | rejected, resumed | size floor + zip `testzip`; HTTP Range resume next attempt |
| wrong-day / stale file | rejected | date-column assertion in schema check |
| schema change at source | human told, dataset unbroken | `SCHEMA_DRIFT` alert; parser never runs on unknown schema |
| exchange didn't publish | one alert after grace window | `PERMANENTLY_MISSING`, not treated as a bug |
| new machine takes over | seamless resume | shared `data_office/eod/`, lock steal, ledger fold, oldest-first worklist |

**Net:** the dataset (`curated/`) is a pure, monotonic function of verified `raw/` files, which are a pure function of the append-only ledger. Nothing enters `curated/` unverified, nothing is done twice, nothing transient wakes a human, and any machine with the folder can continue.

----- ANSWER G024 (task MG03) -----
**Resume-safe daily EOD ingestion pipeline over an unreliable proxy**

**Core invariant**: every file the pipeline ever accepts into the dataset is content-verified and recorded exactly once in an append-only ledger before it is considered "ingested." Nothing downstream ever trusts "the download succeeded" as a signal — it trusts the ledger.

**Mechanisms:**
1. **Manifest-first design.** A daily manifest lists every expected file (per segment/exchange) with its expected filename, and — once known — its expected SHA-256 and byte size, published by the exchange or captured from a prior successful pull. The pipeline's job each day is "make the on-disk state match the manifest," which is naturally idempotent and resumable.
2. **Download to a staging area, atomic promote.** Every file downloads to `staging/<date>/<file>.part`. Only after (a) the download completes without a truncated-connection error, (b) the byte size matches the manifest (or, if unknown ahead of time, is non-zero and stable across a re-stat 2 seconds later), and (c) a checksum/structural validation passes (see #3) — the file is `os.rename()`'d into `landed/<date>/<file>` (atomic on the same filesystem). A crash mid-download leaves only a `.part` file, which is simply ignored/deleted on next run; nothing corrupt ever reaches `landed/`.
3. **Content validation before acceptance, not just transport validation.** A file that downloaded "successfully" over a flaky proxy can still be corrupt (truncated mid-write by the proxy, or an HTML error page saved as if it were the data file). Validate structurally: for a CSV/bhavcopy, check expected header, expected row count within a tolerance band of a trailing-N-day median, and that it parses without exceptions. Files failing this go to `quarantine/<date>/<file>` with a reason string — never silently retried forever, never silently dropped.
4. **Ingestion ledger (append-only, e.g. SQLite/Postgres table, one row per file).** Columns: `date, filename, sha256, byte_size, status(landed/quarantined/ingested), ingested_at, ingested_by_host`. Ingestion into the actual dataset is a transaction that (a) checks the ledger for an existing `ingested` row with the same `(date, filename, sha256)` — if present, no-op (idempotent, handles restarts/reruns), (b) if a *different* sha256 exists for the same `(date, filename)`, that's an anomaly (vendor republished a file) — quarantine and alert, don't silently overwrite history, (c) otherwise writes the data and marks the ledger row `ingested`.
5. **Retry/backoff for the flaky proxy specifically.** Chunked/range-resumable downloads (`Range:` header) so a stall resumes from the last received byte rather than restarting; exponential backoff (say 5 attempts, 10s/30s/90s/5m/15m) per file; a circuit breaker per exchange segment — after N consecutive full-segment failures, stop hammering the blocked IP and escalate instead of retrying into a ban.
6. **A new machine takes over mid-history by reading the ledger, not local state.** The ledger is the single source of truth (kept off the flaky machine, e.g., in the shared DB/S3-compatible store); `staging/` and `landed/` are disposable local caches. A fresh machine's first action is "diff manifest vs ledger for the last N days" and only fetch what's missing — no assumption about what it, personally, has downloaded before.
7. **Alerting only when action is genuinely needed.** Alert on: (a) a file in `quarantine/` older than 2 hours with no automatic resolution, (b) the circuit breaker tripping (proxy/IP block), (c) a manifest entry with no corresponding file after the exchange's stated publish-by time + grace period, (d) a ledger anomaly (mismatched checksum for a previously-ingested date). Do NOT alert on ordinary retries, stalls that self-resolved, or routine backoff — that's noise that trains the human to ignore alerts.

============================================================
# TASK MG04 — rubric anchors:
  1. quantified tail (numeric scenario)
  2. names the real killer (gap thru strikes/vol spike)
  3. concrete pre-committed de-risk triggers
  4. honest on what can't be hedged cheaply
  5. liquidity/fill honesty in stress
  6. book-wide correlation in a spike
  7. margin-call / sizing path
  8. event-gate awareness (CB/budget)
  9. one-page, actionable
  10. specific, no platitudes

----- ANSWER G022 (task MG04) -----
**PRE-MORTEM RISK MEMO — Short Index-Options Book (Paper)**
From: Risk | Date: 14 July 2026 | Written as if: July 2027, the morning after our worst week ever

**Premise.** Last week contained the Union Budget and the RBI MPC decision. The book — short NIFTY premium: defined-risk credit spreads plus naked strangles — lost **~14% of NAV in five sessions**, erasing roughly six months of expected theta. This is what killed it.

**Working assumptions (scale linearly):** NAV ₹1 cr; NIFTY ≈ 26,000; lot 75. Six naked strangles at ±4% strikes (~200 pts credit each, ₹90k total); spreads with aggregate max loss ₹6L; opening margin ~18–20% NAV; book vega ≈ –₹10k per India-VIX point; expected P&L +0.4–0.7% NAV/week.

**The kill chain, in order**
1. **We were short the event, not the market.** Event-week IV looked rich (weekly straddle ~2.5%), so we sold the "post-event crush." Two events in one week meant no crush after event #1 — IV stayed bid for event #2, and theta's promise was repaid as vega.
2. **The gap did the damage before any rule could fire.** Budget tax shock: –3.4% opening gap. Strangle puts went 8-delta to 45-delta overnight. No intraday trigger protects against an open.
3. **We rolled instead of closing** ("vol mean-reverts"), then the MPC surprised two days later: another –4.2%. India VIX 14 → 27. Strangle gamma/intrinsic ≈ –6% NAV; spreads pinned near full max loss on the put side ≈ –5%; vega mark ≈ –1.5%. Note: defined-risk caps the loss, not the probability of realizing it.
4. **Liquidity and margin finished it.** Short options ballooning ITM plus an ad-hoc exchange margin hike pushed utilization past 85%; forced covering into spreads 8–15× normal width added ~1.5–2% NAV of pure slippage, with weekly-expiry gamma compounding it.

**Quantified tail** (paper fills; add 30–50% for live):

| Weekly scenario | Rough odds | Book P&L |
|---|---|---|
| Normal event week, IV crush | base | +0.4 to +0.7% NAV |
| ±1× implied move | ~1 in 3 | +1% / –1.5% |
| –6%, VIX ~25 (budget shock) | ~1 in 15 event-weeks | **–5 to –7%** |
| –9% over 2 sessions, VIX ~30 (Jun-2024 class: NIFTY –5.9% in a day) | ~1 in 30–50 | **–10 to –13%** |
| –13% day, VIX 60–80 (Mar-2020 class) | ~once a decade | **–15 to –22%, realized at forced-exit prices** |

Asymmetry: the plausible worst week is **20–40× the expected weekly gain**. The strangles are ~15% of deployed margin but drive over half the tail loss.

**Pre-committed de-risk triggers** (mechanical; pre-staged as basket orders; not debatable in the moment)
1. **T-2 rule:** by the close two sessions before the first event, zero naked short options — buy wings or close. Budget up to 30% of open credit for wings; pay it.
2. **Size caps:** event-week margin ≤ 35% NAV; aggregate defined-risk max loss ≤ 8% NAV; net vega no shorter than –₹10k/VIX pt.
3. **Strike rule:** no short strike inside 1.25× the straddle-implied move; if IV expansion pulls one inside, exit same session.
4. **VIX triggers:** India VIX > 18 close or +20% intraday → cut short vega 50%; VIX > 24 → flat all short premium.
5. **Spot triggers:** index touches any short strike → close that structure within 15 minutes, not at max loss; intraday move > 1× implied → halve the book.
6. **P&L circuit:** –2% NAV day → halve; –3.5% day or –5% week → flat, 10-session trading halt, written post-mortem before restart.
7. **Per-position stop:** any short structure marking ≥ 2.5× credit received → close.
8. **Margin rule:** utilization > 50% for any reason (including exchange hikes) → cut below 40% same session; never add capital to defend short options in an event week.
9. **Two-event rule:** if event #1 moves > 1× implied, no short gamma into event #2. Period.
10. **Halt protocol:** if index circuit breakers trip, exit 50% of remaining short gamma within 30 minutes of reopen via staged limits, the rest by close — decided now.

**What cannot be hedged at acceptable cost**
- **The overnight gap itself.** Wings sized for a 2020-class move cost 25–40% of gross theta; full protection ≈ no strategy. Sizing (trigger 2) is the only real control.
- **Post-shock liquidity.** First-30-minute spreads widen 5–20×; stops guarantee exit, not price. Tail slippage of 1.5–2.5× theoretical is budgeted, not hedged.
- **Trading halts.** Nothing lets us act during a halt; reopen risk is naked.
- **Vol-of-vol and put skew.** No liquid India-VIX derivative; a put ladder that truly caps skew blowout bleeds ~2–4% NAV/year — more than half the strategy's expected return. Above VIX 24 we exit rather than hedge.
- **Exchange/broker action.** Ad-hoc margin hikes and RMS auto square-off are external and uninsurable; only low utilization mitigates.
- **The paper-to-live gap.** Every figure above assumes mid fills that will not exist in the tail; assume live losses ≥ 1.3–1.5× paper.
- **Us.** The largest residual risk is overriding this memo mid-week. Hence pre-staged orders and a signature on this page before the week begins.

**Bottom line.** The events don't kill this book; naked gamma held through clustered events on the false premise of a single IV crush does. Triggers 1, 2, and 9 are the difference between a bad week and the worst week.

---

Sanity check: re-read the ask — pre-mortem voice (loss already happened, 12 months out), numeric tail, exact pre-commit triggers, and honest unhedgeables are all covered in one page; the scenario arithmetic (strangle point losses × lot 75 × 6 lots + spread max loss + slippage) reconciles with the table's NAV percentages.

result: One-page pre-mortem memo delivered — a Budget+RBI-week gap through naked NIFTY strangles drives a –5% to –22% NAV tail (20–40× weekly expected gain), with 10 pre-committed de-risk triggers and an explicit list of unhedgeable risks (overnight gaps, post-shock liquidity, halts, skew, paper-to-live slippage).

----- ANSWER G008 (task MG04) -----
# PRE-MORTEM: SHORT INDEX OPTIONS BOOK UNDER CB+BUDGET SHOCK
**Risk Memo — 12-month forward look (worst-case scenario)**
**Book: Defined-risk spreads (iron condors + put spreads, 65% notional) + naked index strangles (35% notional)**

---

## WHAT KILLED US: THE CASCADE (July 2026, worst week on record)

**Trigger sequence:**
- **D1 (Monday):** RBI Monetary Policy Committee signals 100bp cumulative hike over next 2 quarters. Market reprices in 15 minutes; NIFTY gaps +3.2% (+420 pts, close 13,550).
- **D2–D3 (Tue–Wed):** Overnight-held short 13,200/13,100 put spreads lose ₹4.2L to gamma on the Monday gap alone. Vega explosion: 30-day IV explodes 14 → 26 (implied Vol +86%), atomizing premium decay.
- **D4 (Thursday):** Union Budget announces capex boost + fiscal deficit miss (2.1% vs 1.6% target). 5-year bond yields spike 150bp in 45 min. NIFTY whipsaws: gaps DOWN 2.8% (−380 pts, close 13,170) — traps our short call spreads (13,600/13,700 sold) into max loss.
- **D5 (Friday):** Naked strangles (short 13,050 puts + 13,850 calls) both blow through stops. Assignment risk crystallizes: June-expiry puts forced into cash settlement at intrinsic (−₹4.1L), June-expiry calls assigned into physical delivery (margin spike ₹7.8L intraday; forced liquidation of 20% of long hedges to meet margin call, eating into exit liquidity).

**The pain in numbers:**
- Gamma P&L: −₹14.2L (two gap moves: +420 pts Mon, −380 pts Thu; short Vega cross-gamma acceleration on the down move).
- Vega P&L: −₹8.6L (IV expansion 14→26; short 2-week strangles + spreads bleed ₹5.9L/IV-point in normal vol, but gamma hedges were neutralized after D1 gap).
- Liquidity unwinding cost: −₹3.1L (25-lot condor unwinds hit 1.2% slippage on Thursday afternoon in rising-vol environment; bid–ask spreads widen 3–5 pts on NIFTY index options).
- Naked strangle assignment + forced-hedge liquidation: −₹2.8L (fees + rollover friction).
- **Total week loss: −₹28.7L (−6.3% of book notional, 450bp of annualized vol).**

---

## TAIL QUANTIFICATION: WHAT WE FACE

| Scenario | Probability (12m window) | P&L Impact | Trigger |
|----------|----------------------------|-----------|---------|
| Single gap move ≥300 pts (RBI shock) | 8–12% | −₹12–18L | IV jump 14→20+ in <1 hour |
| Dual-direction gap sequence (RBI up, Budget down, 48 hrs apart) | 2–3% | −₹25–35L | Gamma acceleration + vega crush |
| IV spike ≥200% of normal (macro announcement) | 4–5% | −₹6–10L | Each IV-point = −₹5.9L net short |
| Assignment on 2 naked strangles + forced unwind | 3–4% | −₹2–4L | Both legs ITM on Friday close; margin call forced |
| Liquidity collapse on unwind (bid–ask widens to 2–3 pts) | 6–8% | −₹2–5L | Forced exit of 20%+ position in afternoon |

**Combined tail (worst week): −₹25–35L at 95th percentile; −₹35–45L at 99th percentile.**
**Book size: ₹455L notional. Single worst week = 6–10% of annual expected return in 5 days.**

---

## DE-RISK TRIGGERS: HARD STOPS (PRE-COMMITTED)

All triggers measured daily at 16:00 IST (post-market close). Execution on next market open.

### Tier 1 (UNWIND 50% of position)
- **Single-day IV spike >200% of 20-day rolling average** (e.g., IV goes 14→21+ in one session). Unwind all naked strangles + 50% of spreads at market open next day. *Rationale: Vega unhedged; cost of carry becomes too high.*
- **Single-day NIFTY gap move >250 pts without previous warning.** Flatten all gamma-long hedges, reduce short deltas by 50% within 1 hour. *Rationale: Liquidity dries up on fast moves; hedges cost more to hold than their benefit after the move.*
- **Book delta (net short before hedges) breaches ±40 Dx.** Rebalance immediately to ±15 Dx. *Rationale: Convexity risk scales with delta size.*

### Tier 2 (EXIT BOOK)
- **IV remains >22 for 2 consecutive days.** Exit entire position, bank loss, sit in cash. *Rationale: Premium decay inverts; gamma loss > theta gain.*
- **Weekly loss >₹8L (>1.75% of book).** Immediate full unwind, no limit orders. *Rationale: Damage control; avoid Tier 3 scenarios.*
- **Naked strangle either leg breaches 50 delta ITM.** Close that leg at market within 30 min; keep the long hedge only. *Rationale: Assignment risk is real; roll cost >exit cost.*
- **Margin utilization >60% of available.** Force 30% position cut (flat naked strangles, keep spreads). *Rationale: Avoid forced liquidation spiral.*

### Tier 3 (EMERGENCY)
- **NIFTY gap move >400 pts + IV >24 + loss >₹15L in same day.** Alert CIO; liquidate 100% within 2 hours, no exceptions. *Rationale: Tail-risk feedback loop; liquidity evaporates.*

---

## WHAT CANNOT BE HEDGED AT ACCEPTABLE COST

1. **Dual-direction gap sequence (RBI up, then Budget down, 48 hrs apart).**
   - Cost to hedge both sides (OTM straddles or wide strangles): ₹3.8–5.2L upfront.
   - Expected payoff in tail: ₹8–12L.
   - But hedge gamma costs vega decay on non-event days (₹1.8L/day for 48 days = ₹86L leakage before the event). Uneconomic. *Acceptance: Book this tail; de-risk triggers mitigate.*

2. **IV spike without move (vol-only shock, no delta move).**
   - Can hedge with long straddles, but cost = 60–70% of current short vega P&L.
   - Better to accept the 2–3% loss and lean on Tier 1 triggers. *Acceptance: Rebalance on IV >22, don't buy protection.*

3. **Liquidity collapse on NIFTY index option unwinds >₹50L notional.**
   - Standard flow is ₹20L/min; anything larger moves mid 2–3 pts.
   - Can't hedge this without futures roll (introduces basis risk + funding cost).
   - *Acceptance: Cap position to ₹400L; keep 48-hour exit window always available.*

4. **Assignment + margin spiral + forced hedge liquidation.**
   - Cost to buy puts on our hedges: ₹1.2–1.5L for 1-week protection.
   - But we're already short premium; paying again is double cost.
   - *Acceptance: Avoid naked strangles >50L notional; enforce Tier 2 trigger at 50-delta ITM.*

---

## GOVERNANCE: ESCALATION & APPROVAL

- **Weekly risk review (Fridays):** Delta, gamma, vega, IV floor/ceiling vs. book position.
- **CIO pre-approval required** to add notional >20% during event weeks.
- **Desk head trigger authority:** Tiers 1–2 (CEO to be notified same day). Tier 3: immediate CIO call, no discretion.
- **Post-mortem debrief:** Within 48 hrs of any Tier 1 trigger, document exactly which scenario fired, P&L impact, and Lessons for next event week.

---

**Memo prepared: July 2025 (pre-event).**
**Worst-case book P&L: −₹35–45L over 1 week. De-risk triggers hard-coded.**
**This book survives 95th-percentile tail at an acceptable loss rate. Beyond that, it is CIO's capital-protection call.**

----- ANSWER G017 (task MG04) -----
# PRE-MORTEM RISK MEMO — Short Index-Options Book into an RBI + Budget Week

**Desk:** Short-vol paper book (defined-risk spreads + naked strangles, NIFTY/BANKNIFTY)
**Author:** Risk Office (pre-mortem, model-grid MG04) · **Date basis:** written as if 12 months forward, the morning after the worst week the book has ever printed
**Frame:** This is a *pre-mortem*. Assume the loss already happened. The job is to say *what killed it*, *how big the tail plausibly was*, *what triggers I pre-commit to now*, and *what I cannot hedge cheaply*. All figures are [INFERENCE] on a stated notional; scale linearly to actual book. Paper only, no live capital (firm rule).

## Reference book (so numbers are concrete)
Assume deployed margin **₹1.00 cr**, net short premium **₹6–8 L collected**, greeks at entry: **net short vega ≈ ₹40k/vol-pt**, **net short gamma**, delta ≈ flat, theta ≈ **+₹18k/day**. Roughly 60% of risk in defined-risk spreads (capped) and 40% in naked strangles (uncapped, ~15–18-delta legs). This is the book that blew up.

## What killed it (ranked cause chain)
1. **Event-vol double-count, then a gap through the short strikes.** IV was *already* rich into the week, so premium looked fat and the desk sized to the premium, not to the move. RBI surprised (or the Budget carried an off-consensus tax/borrowing line), NIFTY gapped **~4–6% in a session** and kept going intraday. The naked strangle's short leg went from 15-delta to ~55-delta; **short gamma turned the delta against us faster than we could hedge.**
2. **Vol-of-vol / vega on the crush that never came.** The classic short-vol prayer is "IV collapses after the event." It didn't — realized *exceeded* implied, and the term structure inverted (front IV +8 to +15 vol-pts). Short vega ₹40k/pt × +12 pts ≈ **−₹4.8 L** on vega alone, on top of directional loss.
3. **Liquidity evaporation at the exact moment of need.** Bid-ask on the OTM legs blew from ₹1–2 to ₹15–30 wide; the "defined risk" spreads were only defined *at expiry*, not intraday — marking-to-mid understated the real exit cost by **2–4x** (T7b/COST_STANDARDS dynamic-slippage regime). We could not roll or close the naked legs without paying the panic spread.
4. **Correlation-to-one / no true diversification.** Every position was the same trade (short NIFTY vol) wearing different strikes. "Spreads + strangles" felt diversified; under stress the book had **one factor** and it was short-gamma-short-vega. Margin (SPAN + exposure) spiked as scan-range widened, forcing de-risk into the worst prices — a margin-call feedback loop.

## Quantified plausible tail (numeric, stated notional)
| Scenario | Index move | Front IV Δ | Est. book P&L | Note |
|---|---|---|---|---|
| Bad-but-normal | −2.5% / +2.5% | +4 pt | **−₹1.5 to −2.5 L** | inside modeled worst-case |
| Severe (base tail) | −4.5% gap | +10 pt | **−₹6 to −9 L** | naked legs breached; ~1.0–1.5x collected premium lost |
| Worst-week-ever | −6 to −8% + follow-through | +12 to +18 pt | **−₹12 to −18 L** | 12–18% of deployed margin; **1.5–2.5x** premium collected |
| Left-tail / limit-down type | −10%+ | +25 pt, illiquid | **−₹25 L+** | naked strangle is effectively unbounded here; defined-risk legs cap ~₹6L of it |

**Headline:** worst-week loss ≈ **−12% to −18% of margin (base tail)**, with a fat, *non-symmetric* left tail where the naked strangle carries **theoretically unbounded** downside (practically ₹25L+ before we could flatten). Modeled 1-day 99% VaR pre-event probably read **~₹2.5–3 L**; the realized loss was **4–6x VaR** — the standard short-gamma signature (VaR is blind to jumps).

## Pre-committed de-risk triggers (decided NOW, mechanical, no discretion in the moment)
- **T-minus sizing cap:** into any RBI/Budget/Fed week, **cut net short vega by ≥50%** and **cap naked-strangle margin at ≤15%** of book (down from 40%) *before* the event. Pre-registered, not negotiable.
- **Naked → defined:** convert every naked strangle to an **iron condor / add long wings** (buy the 5-delta) by T-1 close. Caps the unhedgeable tail at a known, budgeted debit.
- **Loss trigger 1 (soft):** book MTM **−₹3 L (−3% margin)** intraday → stop adding, hedge delta to flat with futures, halve remaining naked exposure.
- **Loss trigger 2 (hard kill):** book MTM **−₹6 L (−6% margin)** *or* short-leg delta > **30** *or* margin utilization > **80%** → **flatten naked legs immediately at market**, accept the spread; keep only defined-risk. This is the circuit breaker; it fires on price/greek, not on opinion.
- **Vol trigger:** front IV rises **+8 vol-pts intraday** post-event (crush thesis is wrong) → de-risk regardless of P&L.
- **Liquidity trigger:** if OTM bid-ask > **10x** its pre-event width, do **not** average/roll; exit the closest liquid strike and stand down.
- **Event blackout:** no new short-vol entries in the **48h window around the announcement**; theta is not worth the gap risk.

## What CANNOT be hedged at acceptable cost (honest section)
- **The jump/gap itself.** Overnight/announcement gaps happen when the market is closed — no delta hedge fills through a gap. You pay for gap protection *in advance* via long wings, and that premium is a **permanent drag on the short-vol edge** (it eats most of the collected theta in quiet weeks). There is no free convexity.
- **Correlated liquidity + margin spike.** When you most need to hedge, spreads are widest and margin is highest — the hedge is most expensive exactly when required. Buying that insurance continuously makes the strategy uneconomic; accepting it means accepting the tail.
- **Vol-of-vol / term-structure inversion.** Cheap, liquid vega-of-vega hedges don't exist for a retail-scale NIFTY book; a VIX-style hedge is basis-mismatched and itself illiquid intraday here.
- **Model risk on "defined."** Defined-risk is only defined *at expiry*. Intraday, under stress, the max-loss can be touched *before* expiry via margin/liquidity, so the "capped" comfort is partly illusory.
- **The strategy's own DNA.** Short vol is *structurally* short the left tail. You can shrink it (wings, sizing, blackout) but you cannot remove it without deleting the edge. The only complete hedge is **not being in the trade** during the event — which is exactly what the sizing cap and blackout above encode.

## One-line verdict
The book died because it was sized to fat premium instead of to the gap, ran uncapped naked gamma into a scheduled shock, and discovered its "defined" risk and its liquidity were both conditional on the market staying calm. **Pre-commit the sizing cap + naked-to-condor conversion + the −6% hard kill; budget the wing premium as the honest cost of surviving the tail you cannot otherwise hedge.**

----- ANSWER G006 (task MG04) -----
**Pre-mortem risk memo — short-index-options book, one year forward, worst week ever**

**What killed it.** The budget/RBI week delivered a surprise policy combination (e.g., an unexpected rate move plus a fiscal-deficit/tax surprise investors read as negative) that moved the index ~5–7% intraday on the announcement day after weeks of compressed realized and implied vol — exactly the regime in which a short-strangle/short-premium book has maximum negative gamma and minimum cushion (IV had been sold down to multi-year lows going into the event, so premium collected was thin relative to the eventual move). The defined-risk spreads capped loss per structure but at multiples of the credit received (typical short vertical spreads lose 3–6x credit at max pain); the naked strangles have no cap and are the dominant tail contributor.

**Quantify the plausible tail.** If the book runs, say, ₹50cr notional-equivalent short gamma with a blended short strangle width of ~3% OTM each side and the index moves 6% against one side: a naked short strangle sized to a normal ₹1–2 lakh margin-per-lot regime can see per-lot losses of 15–25x the collected premium once the move breaches the short strike by several percent (payoff is roughly linear beyond the strike, and vega expansion on the surviving wing compounds it). A back-of-envelope for a book running ~₹8–12cr of naked strangle notional risk: a plausible single-week loss in the 25–45% of book-capital range is not extreme for this setup — that is the number that should trigger the pre-commitment below, not be discovered after the fact.

**De-risk triggers to pre-commit to (numeric, not vibes):**
- Reduce naked-strangle gross short vega by 50% at least 2 sessions before any pre-scheduled binary event (budget/RBI/election) — mechanical calendar rule, no discretion.
- If realized vol over the trailing 10 sessions is below the 20th percentile of trailing-3-year realized vol AND an event is inside 5 sessions, cap new naked-strangle sales entirely (compressed-vol-into-event is the precise setup that produces tail losses; this is exactly when premium looks "cheapest" and is most dangerous).
- Hard stop-loss at 3x credit received per naked structure, executed same-day, no averaging down / no "it'll mean-revert."
- Daily VaR/stress limit: book must survive a pre-specified index gap (e.g., ±7% overnight) within a pre-committed max drawdown (e.g., 15% of book capital) under a full-reval stress test — recompute weekly, not just at inception.

**What cannot be hedged at acceptable cost.** True tail protection for a scheduled, known-date binary event (buying far OTM protection specifically for budget/RBI week) is expensive precisely because everyone wants it into the same week — the IV term structure kinks up going into the event, so hedge cost eats a large fraction of the strategy's baseline edge if done every single time. The honest answer is: you cannot fully hedge this cheaply and still keep the strategy's baseline return; the correct response is *position sizing and gross-exposure reduction* going into known binaries, not "buy insurance every time," and an explicit acknowledgment that a genuine multi-sigma surprise on a scheduled event is a known, accepted, capital-at-risk scenario, not something the book was flawed for missing.

============================================================
# TASK MG07 — rubric anchors:
  1. known-value spot-checks vs independent source
  2. PIT test: announcement-date genuineness
  3. coverage-by-year/completeness check
  4. survivorship detection (delisted present?)
  5. schema/dtype/null/dupe checks
  6. date monotonicity / no future dates
  7. sampling plan (n, stratified)
  8. quarantine/acceptance pass-fail gates
  9. catalog/provenance entry
  10. cross-check values not just structure

----- ANSWER G009 (task MG07) -----
Here is the verification protocol I would run, written as an executable checklist. Design assumption throughout: the vendor is presumed guilty of (a) backfilling history from a current-view database, (b) stamping synthetic announcement dates, and (c) covering a survivorship-biased universe, until each is disproven. Everything below is code in the repo, re-run on every delivery — not a one-time exercise.

## Phase 0 — Quarantine and structural interrogation (before any statistics)

1. **Isolate.** Data lands in a `vendor_raw` schema, read-only, with no import path into research code. Nothing touches a backtest until promoted by the pipeline in Phase 6.
2. **Key census.** Test primary-key uniqueness on (entity_id, period_end, statement_basis [standalone/consolidated], audit_status, vintage). If there is **no vintage/first-reported dimension** — one mutable row per company-quarter with an announcement-date column stapled on — record that up front: the dates alone can never prove point-in-time-ness, and the burden shifts entirely to the Phase 3 tests.
3. **Vendor questionnaire with falsifiable answers:** (a) the exact date live capture began — everything before that is backfill *by construction*; (b) the source of pre-live announcement dates; (c) restatement policy (overwrite vs. append); (d) whether they can re-deliver historical snapshots ("the file as it existed on 2019-06-30"). Order two snapshots (e.g., as-of 2019 and as-of 2023) now — needed for test 3.5. Inability or refusal to produce snapshots is itself evidence about their live practice.
4. **Unit and convention probes.** Compare 10 mega-cap revenue figures against known magnitudes to catch lakh/crore/million scaling instantly (a 10x or 100x error is the classic Indian-data failure; banks historically filed in lakh, others in crore). Pin down: does "FY2016" mean year ending March 2016; are quarter labels fiscal or calendar; how are non-March fiscal years handled — pull **Siemens India (September FYE)** and a Dec-FYE MNC subsidiary, and specifically **Bosch's 15-month transition year to a March FYE (~2014-15)**.

## Phase 1 — Full-universe internal forensics (automated, all ~2000 companies × ~84 quarters)

1. **Accounting identities with tolerances:** PBT − tax ≈ PAT; EPS × share count ≈ PAT (flag >2%); assets = liabilities + equity where balance sheets exist; sum of four quarters vs. FY. Flag — but do not fail — exact Q4 = FY − 9M matches: Indian Q4 figures are explicitly "balancing figures," and the check is whether the vendor *knows* this (a derived-Q4 flag) rather than presenting Q4 as independently reported.
2. **Regulatory-impossibility scan (India-specific, high yield):** quarterly filings under Clause 41/LODR historically contained P&L only — balance sheets were **half-yearly**, cash flows **annual** (half-yearly only from roughly 2019), and consolidated quarterly reporting was optional until it was mandated around FY2019-20 (Kotak committee). So: non-null *quarterly* balance-sheet items in 2008, quarterly cash flows in 2012, or near-complete consolidated quarterly coverage in 2012 are synthesized (interpolated, forward-filled, or annual data restamped). Identify which fields these are; they get blocked in Phase 6. (Pin exact effective dates from SEBI circulars during implementation; the scan itself works empirically — look for field-coverage discontinuities and demand they map to a known regulatory change.)
3. **Staleness and duplication:** zero-variance runs of ≥4 quarters (forward fill); identical value-vectors across different companies (copy errors); mid-series jumps of exactly 10x/100x (unit regime change).
4. **Announcement-lag forensics.** Plot the full distribution of (ann_date − period_end) by quarter, by era:
   - **Floors/ceilings:** lag < 7 days is essentially impossible in India (TCS, the fastest large cap, reports ~10-12 days after quarter end); lag > 120 days gets individually explained.
   - **Regime shape:** mass inside 45 days (60 for Q4/audited annual), clustering in the final two weeks, and four seasonal waves (Jul, Oct-Nov, Jan-Feb, Apr-May).
   - **Fabrication signatures:** point-masses exactly at day 45/60; identical dates across large swaths of the universe; **zero weekend dates** — Saturday board meetings are routine in India (HDFC Bank habitually reports on Saturdays), so an all-weekday distribution means someone "cleaned" or generated the dates; zero late filers ever (real exchanges fine late filers every year — a tail must exist).
   - **The COVID litmus test:** SEBI extended the March-2020 (and June-2020) quarter deadlines well into mid/late 2020. The Mar-2020 quarter must show that fat tail of June-July 2020 announcements. A tidy 45/60-day distribution for that one quarter is near-proof the dates were synthesized from statutory deadlines.
5. **Coverage curves:** companies-with-data per quarter, split by exchange, size decile, and alive-today vs. dead. Look for the backfill cliff — a coverage jump in the year the vendor actually started operating.

## Phase 2 — External value verification

Ground-truth hierarchy: (a) **exchange XBRL Reg-33 filings** (bulk-downloadable from BSE/NSE, roughly FY2016 onward) — use as a *census*, not a sample; (b) original results PDFs from the BSE corporate-announcements archive (goes back to the mid-2000s) — for sampling the pre-XBRL era; (c) an incumbent database (Prowess/Capitaline/Ace/Bloomberg) as tie-breaker only — many Indian vendors share upstream provenance, so vendor-DB agreement is not independence.

1. **Post-2016 census:** machine-compare revenue, PBT, PAT, EPS — plus NII and gross/net NPA for banks — for *every* company-quarter against exchange XBRL. Metrics: exact-match rate, material discrepancy rate (|relative error| > 1%), sign flips. Proposed gate: material errors < 0.5%, sign flips ~zero unless explained by regrouping.
2. **Pre-2016 stratified hand-sample:** 60 company-quarters checked line-by-line against filing PDFs. Strata are mandatory, not proportional: era (2005-09 / 2010-15), size including micro-caps, sector cells that *must* be filled (bank, NBFC, IT, PSU, commodity), status (alive / delisted / merged mid-history), and ≥5 non-March-FYE names. Plus 400-800 semi-automated spot checks of revenue/PAT/EPS against a second database.
3. **Adversarial named set — inspected exhaustively, never sampled:**
   - **Satyam FY08-FY09:** the fraudulent as-originally-reported numbers should be present (that is *correct* for PIT); forensically restated figures under those quarters is a current-view tell.
   - **Yes Bank Q3 FY20:** results were delayed to mid-March 2020, far past the 45-day deadline — the vendor's date must reflect that.
   - **Vodafone Idea Q2 FY20:** the ~₹50,000 crore AGR loss must be present in full, not winsorized by an outlier filter.
   - **PNB Q4 FY18; CG Power's FY18 restatement (disclosed Aug 2019).**
   - **Tata Motors:** standalone vs. consolidated diverge wildly (JLR) — perfect test that statement_basis labels are trustworthy.
   - **A GST-boundary FMCG/manufacturer:** the gross-of-excise → net-of-GST revenue break at Q1 FY18 must be visible if data is genuinely as-reported.
   - **An Ind AS Phase-1 company's FY16 quarters:** must be the original Indian-GAAP figures, not the Ind AS restated comparatives republished in FY17 filings.

## Phase 3 — Point-in-time tests (the heart of the protocol)

1. **Date ground truth:** for 300-500 stratified company-quarters plus the entire adversarial set, pull exact board-meeting-outcome filing timestamps from the BSE archive. Compute exact-match rate and the (vendor − true) distribution. Interpret the *shape*: a systematic +1/+2 day bias suggests newspaper-publication dates (Reg 47 requires publication within 48h) — recalibratable; a heavy, irregular right tail suggests database-entry dates masquerading as announcement dates — disqualifying.
2. **Comparative-fingerprint test (the decisive, scalable one).** Every Indian quarterly filing republishes the year-ago quarter as a comparative, and regroupings/restatements/demergers routinely make that comparative differ from the original filing. From XBRL, assemble all cases where original(Q) ≠ comparative-of-Q-in-filing(Q+4). For each divergent pair, which value does the vendor store against Q? A true first-reported database matches the originals; a current-view database matches the later comparatives *while still stamping the original announcement date* — i.e., manufactured point-in-time. Run on every divergent case post-2016. Gate: ≥95% original-matching, or hard fail.
3. **IPO backfill probe:** for the 2021-22 cohort (Zomato, Paytm, Nykaa, LIC), pre-listing quarters only became public via the prospectus. If those quarters exist with announcement dates in 2019-20 (period_end + 45 days), the dates are fabricated. Also check Hexaware (delisted 2020, re-listed 2025) as a joint PIT and entity-continuity probe.
4. **Market-reaction event study — measures exactly what a backtest will consume.** For ~2,000 random company-quarters with clean price data, compute abnormal volume and |abnormal return| in event time around ann_date. Genuine dates produce a sharp t0/t+1 spike (t+1 because many Indian releases are post-close or on Saturdays); entry dates produce a smeared or lagged spike. Quantify: fraction of events whose max |abnormal return| within [-5,+5] falls on t0/t+1 (chance ≈ 18%), and the correlation of earnings surprise sign with t0/t+1 return. **Negative control:** rerun with all dates shifted +15 trading days and confirm the spike vanishes (proves the test has power). Run **separately by era** — backfilled years often fail while recent years pass, which feeds the tiering below.
5. **Snapshot diff:** using the two historical deliveries from Phase 0, diff a known restatement (CG Power) plus 50 random rows. The older snapshot must contain the older values.
6. **Forward shadow capture:** for the next one or two earnings seasons, scrape BSE announcements live and log our receipt time; when the vendor's update arrives, measure **vendor delivery latency** per record. Correct historical stamps do not make the feed tradable at those stamps — the simulator must use max(ann_datetime, ann_date + observed p95 vendor latency).
7. **Intraday convention:** if the vendor supplies date-only (no timestamp), fix the conservative rule now — signal usable at t+1 open at the earliest — and use the timestamp sample to measure how much that convention costs.

## Phase 4 — Coverage and survivorship

1. **Independent universe reconstruction** from exchange delisted/suspended lists and index-vendor archives (historical Nifty 500 / BSE 500 constituent snapshots).
2. **Index-snapshot recall:** for constituents as of 2007, 2010, 2014, 2018, 2022, the vendor must cover ≥99% of that quarter's Nifty 500, every gap individually explained. Repeat at the bottom of the cap spectrum with BSE SmallCap snapshots, where the real damage hides.
3. **Death-rate comparison:** "~2000 companies" is suspiciously close to NSE's *current* active count; distinct listed entities since 2005 across NSE+BSE number several thousand more. Compute distinct entities ever in the dataset, and the fraction of the vendor's FY2008 universe whose data terminates before 2016; compare against exchange delisting base rates. If nearly everything in the 2008 universe survives to today, history was backfilled onto a current universe — structural survivorship bias.
4. **Named dead-company checklist** (each must exist with sensible terminal quarters): Satyam/Mahindra Satyam through the 2013 merger, Kingfisher Airlines, Deccan Chronicle, Bhushan Steel through IBC, Amtek Auto, Gitanjali Gems, Manpasand Beverages, DHFL through 2021, Videocon, Jet Airways, RCom, Cairn India through the 2017 merger, **HDFC Ltd through July 2023**, and a sample of 20 from the ~331 suspected shell companies suspended in August 2017.
5. **Entity-mapping audit:** 50 corporate events sampled from exchange circulars — name/symbol/ISIN changes, mergers, demergers (RIL→Jio Financial 2023, Crompton 2016, Arvind 2019). Verify ID persistence, no duplicate entities, and no history grafted across demerger boundaries (restated pre-demerger financials stamped with pre-demerger dates is a PIT violation, not just a mapping bug).

## Phase 5 — Acceptance gates, tiering, quarantine mechanics

| Check | Proposed gate | Consequence if failed |
|---|---|---|
| Comparative-fingerprint (3.2) | ≥95% match to originals | **Hard reject as PIT source.** Values may be salvageable as current-view reference only |
| Date fabrication signatures (1.4), incl. COVID tail | No deadline point-masses; COVID tail present | Dates rejected; salvage path below |
| Date accuracy vs. exchange timestamps | ≥90% within ±1 trading day post-2010 | Dates quarantined for that era |
| Post-2016 XBRL value census | Material errors <0.5%, sign flips ~0 | Reject or field-level block |
| Index snapshot recall | ≥99% Nifty 500, gaps explained | Reject for cross-sectional backtests |
| Death-rate vs. exchange base rate | Within ~20% of base rate | Pre-live-capture era demoted to Tier B/C |
| Event study (3.4), per era | Clear t0/t+1 concentration; negative control clean | Era-level demotion |

**Tiering of what a backtest may touch:**
- **Tier A (backtest-approved):** eras and fields passing everything including the event study. Dates used with the conservative intraday rule plus measured vendor latency.
- **Tier B (research-only):** eras with verified values but unproven dates (typically the pre-live-capture backfill). Vendor dates are **discarded and replaced** with a synthetic conservative availability rule (period_end + era-specific statutory deadline + 5 trading days), and any strategy must survive a +15-trading-day lag sensitivity test before promotion.
- **Tier C (blocked):** fields failing the impossibility scan (e.g., pre-2015 quarterly balance sheets) — physically excluded from the promoted schema so nobody can "forget."
- **Salvage rule:** if values pass the fingerprint test but dates fail, rebuild announcement dates ourselves from the BSE archive (it is scrapeable for the full history). If values fail the fingerprint test, no date repair can save the dataset for PIT use.

**Quarantine mechanics:** promotion ETL writes `fundamentals_pit` with lineage columns (delivery batch, validation run id, tier). Every new delivery is diffed against the prior one; **any mutation of previously delivered historical rows halts promotion** until explained — legitimate restatements must arrive as new vintage rows, silent edits are an incident. Two full earnings seasons of shadow-capture probation before Tier A data feeds anything sized in production. Final artifact is a signed acceptance memo listing every check, its result, and the disposition of every failure — the memo, not a feeling of comfort, is what admits the data to backtests.

Rough effort: Phases 0-1 are a few days of engineering; the XBRL census and fingerprint test are the bulk of the build (1-2 weeks) and become permanent monitoring infrastructure; the hand-sample is 2-3 person-days; shadow capture runs in the background across a quarter.

result: Delivered a phased verification protocol for the Indian quarterly fundamentals vendor — quarantine and structural checks, full-universe forensics (regulatory-impossibility and COVID-deadline tests), XBRL census plus adversarial named-case sampling, four independent point-in-time tests (comparative-fingerprint, IPO backfill, event study, snapshot diff), survivorship audits against index snapshots and named dead companies, and concrete acceptance gates with tiered promotion rules.

----- ANSWER G011 (task MG07) -----
# Quarterly Fundamentals Dataset Verification Protocol (Gate-3)

**Version:** 1.0  
**Date:** 2026-07-12  
**Owner:** Data Officer (Kavya Reddy)  
**Approval Gate:** CEO + CIO joint (D-025) before first backtest use  
**Scope:** Third-party Indian equity fundamentals (2005-present, ~2000 co, announced dates)

---

## PHASE 1: INVENTORY & SCHEMA AUDIT

**Deliverable: VENDOR_SCHEMA.md (template below)**

1. **Request from vendor (in writing):**
   - Exact field list: revenue, EBITDA, PAT, EPS (basic/diluted), OPM, ROE, etc.
   - Timestamp fields: announcement_date, fiscal_year_end, report_date, data_refreshed_date
   - Timezone for all dates (assumed UTC or IST?)
   - Fiscal year convention (Indian FY = Apr-Mar? Company-specific?)
   - Consolidation level (standalone vs consolidated P&L?)
   - Accounting standard (Ind-AS vs AS? IFRS?)
   - Data refresh lag (e.g., "updated 1 week after announcement"?)
   - Known gaps or backfill periods
   - Delisting policy: does dataset include delisted companies?
   - Restatement policy: original or restated figures?

2. **Validate against firm standards:**
   - Cross-check: India-specific fiscal year handling in `05_DATA_OFFICE/DATA_QUALITY_RULES.md`
   - Confirm timezone: all dates must be convertible to IST for timestamp_to_date consistency
   - Flag any non-standard definitions (e.g., "EPS" that includes discontinued ops)

**GATE: REJECT if schema unclear on announcement_date source or if fiscal year convention not specified.**

---

## PHASE 2: STRATIFIED SAMPLING DESIGN

**Sample Size:** 30 companies × 8 quarters = 240 test rows (minimum)

**Stratification (10 companies per stratum):**

| Stratum | Selection | Rationale |
|---------|-----------|-----------|
| **Large Cap (Tier 1)** | TCS, Reliance, HDFC, ICICI Bank, Bajaj Finance, Infosys, ITC, LT, Maruti, HUL | Highest volume, best external validation available |
| **Mid Cap (Tier 2)** | Bajaj Auto, Cipla, Dr. Reddy's, Eicher, Grasim, SBI, Titan, Voltas, Biocon, Lupin | Smaller but still liquid; test coverage beyond top tier |
| **Small Cap + Delisted (Tier 3)** | 5 companies delisted/merged 2015-2025 (IL&FS, Vodafone-Idea, Jet Airways, Unitech, GMR Infra pre-restructure) + 5 never-in-NIFTY500 (to test universe boundaries) | Test survivorship bias and merger handling |

**Time Stratification (8 quarters per company):**
- 2 quarters from 2008-2010 (post-crisis)
- 2 quarters from 2016-2018 (normal)
- 2 quarters from 2022-2024 (recent)
- 2 quarters from 2024-Q1 onwards (most recent, highest lookahead risk)

**Cross-Check Datasources (in priority order):**
1. BSE/NSE regulatory filing archives (XBRL filings on bseindia.com)
2. Company investor relations websites (PDF annual reports, investor presentations with announcement timestamps)
3. Moneycontrol/Screener historical data (editorial, but timestamped)
4. ET Markets / LiveMint coverage (announcement coverage with dates)
5. Internal Angel SmartAPI cache of past earnings surprises (if available)

---

## PHASE 3: POINT-IN-TIME (PIT) VERIFICATION

**Goal:** Prove announcement_date in vendor data matches or is AFTER actual public disclosure (never before).

### 3a. Announcement Date Cross-Check (Critical)

**For each of 30 sample companies, last 8 quarters:**

1. **Extract from vendor:**
   - announcement_date (as provided)
   - revenue, EPS (extract for later use)

2. **Independently retrieve actual announcement date:**
   - Go to bseindia.com → "Corporate Announcements" → search company ISIN
   - Find the earnings announcement filing (BSE uses standardized format: "Pursuant to Regulation 33 of SEBI LODR, 2015")
   - Note: **Exchange filing date** (when auditors/company submit to exchange)
   - Go to company IR website, download PDF annual report, check cover page for "announced on" date
   - Note: **Public announcement date** (press release / earnings call)
   - Rule: use EARLIEST of the two as **ground truth**

3. **Calculate lag:**
   ```
   lag_days = vendor_announcement_date - ground_truth_announcement_date
   ```

4. **Threshold rules (STRICT):**
   - RED FLAG: lag < 0 (vendor has data from the future → lookahead → REJECT dataset immediately)
   - YELLOW: lag 1-5 days (acceptable editorial buffer)
   - YELLOW: lag 6-10 days (acceptable but note it; some vendors batch-process)
   - RED: lag > 15 days (stale data; may be backfilled without editorial review)

5. **Aggregate result:**
   - Compute: mean lag, stdev, min, max across 240 sample cells
   - If mean lag > 10 days AND vendor claims "real-time updates," reject for truthiness
   - If ANY lag < 0, REJECT immediately (do not pass Go)

---

### 3b. Lag Distribution Analysis

**Run for all 240 samples:**

```
Plot histogram: lag_days distribution
- X-axis: lag in days (-10 to +60)
- Y-axis: count
- Overlay: cumulative %

Expected (clean data):
  - >90% in 0-5 day range
  - 0% in negative range
  - tail >30 days is acceptable (backfilled disclosures) BUT must be <10% of sample

Reject if:
  - Any negative lags exist
  - Median lag > 7 days
  - >20% of samples lag > 15 days
```

---

### 3c. Earnings Surprise Lookahead Test (Gold Standard)

**Hypothesis:** If data includes future announcements, a simple earnings-surprise model will trade profitably BEFORE announcement dates.

**Test on: TCS, Infosys, Reliance (most liquid, best price data)**

1. **Setup:**
   - Get vendor's EPS data for last 12 quarters (Q1 FY2023 → Q4 FY2024)
   - For each quarter, calculate: actual EPS vs "consensus" (use vendor's reported EPS from same dataset as signal)
   - Define surprise: if EPS_actual > consensus_eps, signal = BUY
   - Historical consensus: Use average of 2-3 prior quarters as proxy

2. **Backtest entry rule:**
   - Signal day = vendor's announcement_date at 09:30 IST (30 min after market open; allow announcement time to hit price)
   - Entry: buy 1 share at 09:30 price on signal day
   - Exit: sell at close of day (hold 6.5 hours, capture intraday reversal)

3. **Expected results (no lookahead):**
   - ~50% win rate (earnings surprise is noisy)
   - Average return per trade near 0% (you're trading stale information by 09:30)
   - Max 10-15 bps avg profit (noise, not signal)

4. **Reject if:**
   - Average return > 30 bps per trade (statistically strong)
   - Win rate > 65% (suspicious consistency)
   - ANY profitable trades occur BEFORE announcement date (clear lookahead)
   - Sharpe > 0.5 on daily returns (too clean for a noise trade)

5. **Implementation:**
   - Use firm's existing `lib/lookahead_audit.py` (Gate-4 tool)
   - Generate backtest equity curve + trade log with entry dates + announcement dates side-by-side
   - Commit backtest results to git with commit msg: "MG07_PIT_audit_vendor_name_PASS/FAIL"

---

### 3d. Re-announcement / Restatement Test

**Goal:** Detect if vendor conflates preliminary vs final results or missing restatements.

1. **Identify companies with known restatements:**
   - YES Bank (2018-2020 earnings restatement due to auditor findings)
   - IL&FS (2019 defaults led to restatement)
   - Sample 3-5 cases from past decade

2. **For each case:**
   - Pull vendor data for the restated quarter
   - Compare to: (a) company's original filing, (b) company's restated filing
   - Check: does vendor use restated or original figures?
   - Rule: MUST use restated (original = lookahead)

3. **For quarterly filers that announce preliminary results + final results:**
   - Track if vendor captures both announcements or overwrites
   - Example: Company announces "preliminary Q3 results" on Jan 15, then "final audited results" on Jan 22
   - Vendor should show TWO entries OR timestamp as Jan 22 (final) only
   - Flag if vendor conflates them

**Threshold:**
- If vendor uses original (pre-restatement) numbers: REJECT (material lookahead)
- If vendor conflates preliminary/final without timestamp clarity: FLAG for manual review per company

---

## PHASE 4: COVERAGE & UNIVERSE ANALYSIS

### 4a. NIFTY 500 Membership Test

**Datasource:** Use `NIFTY500_TICKER_2005_2025_Final.xlsx` (42 PIT snapshots per CLAUDE.md)

1. **For each year 2015-2025 (11 years):**
   - Extract NIFTY 500 membership list from that year's snapshot
   - Count companies: should be ~500
   - Cross-match with vendor dataset: how many are present?
   - Calculate: Coverage % = (vendor companies in NIFTY500) / 500

2. **Acceptance thresholds:**
   - 2015-2020: minimum 70% coverage (acceptable; some M&A / delistings)
   - 2020-2025: minimum 85% coverage (data should be fresh)
   - Any year < 60% coverage: FLAG as potential data gap or vendor filtering

3. **Identify missing companies:**
   - Print list of missing companies per year
   - Manually check: are they delisted, merged, renamed, or vendor gap?
   - If >10 major companies (top 100 by market cap) are missing, REJECT

---

### 4b. Sector Completeness

**Stratify missing coverage by sector:**

1. **For 11 years, calculate:**
   - Coverage % by sector (IT, Banking, Pharma, Auto, Industrials, Consumer, Energy)
   - Variance: which sectors have lowest coverage?

2. **Reject if:**
   - Any sector < 50% coverage in 2020+ (suggests vendor bias or data gap)
   - IT sector (largest, most liquid) < 80% coverage (red flag)

---

### 4c. Company Age & New Listing Handling

1. **Identify companies that entered NIFTY 500 during study period:**
   - Count: should match IPO calendar (e.g., 5-10 new listings per year on average)
   - For each new entrant: does vendor have data from year 1 of listing, or delayed?
   - Rule: vendor should have data within 1-2 quarters of listing (companies file quarterly results immediately)

2. **Test delisted companies:**
   - Pull list of ~50 companies delisted 2015-2025
   - Cross-check: which appear in vendor dataset?
   - If < 30 / 50 delisted companies present, FLAG SEVERE SURVIVORSHIP BIAS

---

## PHASE 5: SURVIVORSHIP BIAS TEST

**Goal:** Detect if vendor only includes survivors (backward-looking bias).

### 5a. Delisted Company Coverage

1. **Obtain NSE/BSE delisted company list 2005-2025:**
   - Source: https://www.nseindia.com/listing/listdelisted.html (historical archive)
   - Count delisted: ~200-300 companies in last 20 years

2. **For 50 sample delisted companies (stratified across sectors + decades):**
   - Check: does vendor dataset include them?
   - If YES: does vendor have data up to delisting date? Or pre-delisting data only?
   - Expected: yes, full history up to delisting

3. **Acceptance rule:**
   - If < 40% of delisted companies in vendor dataset → REJECT (severe survivorship bias)
   - If 40-70% → CONDITIONAL ACCEPT with mandatory footnote: "results may understate volatility / tail losses" (delisted companies often had distress, high returns)
   - If > 70% → ACCEPT on survivorship dimension

4. **Specific case: IL&FS (2019 default, delisted 2021)**
   - Vendor should have IL&FS data 2005-2021
   - Should show declining profitability 2018-2019 and default period
   - If vendor's IL&FS data shows "clean" P&L or is missing → RED FLAG

---

### 5b. Merger & Acquisition Handling

**Test 10 major M&A cases (2010-2025):**
- HDFC + HDFC Bank merger (2023)
- TCS (various acquisitions)
- Vodafone + Idea merger discussions (2024; test incomplete deal handling)
- Grasim / Aditya Birla (structural reorganization 2023)

**For each case:**
- Does vendor have both parent + target separately, or consolidated?
- Are pre-merger financials attributed to correct entity?
- Rule: vendor should show both separately pre-merger, then combined post-merger (NOT retroactive consolidation)
- If vendor retroactively applies merged entity's name to historical parent data → RED FLAG (lookahead + restatement confusion)

---

## PHASE 6: CROSS-VALIDATION WITH PUBLISHED FIGURES

### 6a. Spot-Check 20 Specific Quarters

**Sample across all 30 companies, recent quarters (2023-2024):**

For each quarter, retrieve:
1. **Vendor data:** revenue, PAT, EPS
2. **BSE regulatory filing:** XBRL data (most authoritative for listed companies)
3. **Annual report PDF:** official P&L (may differ from quarterly filings due to Ind-AS interpretation)
4. **Screener.in / Moneycontrol historical:** editorial cross-check

**Comparison rules:**
- Revenue: must match within ±0.5% (rounding tolerance)
- EPS: must match within ±1% (can include dilution adjustments)
- PAT (Profit After Tax): within ±1%
- RED FLAG: systematic bias (e.g., vendor always 2% higher on revenue)

**Acceptance:**
- 18-20 / 20 matches within tolerance → PASS
- 15-17 / 20 → CONDITIONAL (investigate failures)
- < 15 / 20 → REJECT

---

### 6b. Metric Definition Audit

1. **Request vendor documentation:**
   - EPS: basic or diluted? Which dilution (ESOP, warrants, convertibles)?
   - Revenue: gross or net of discounts?
   - PAT: standalone or consolidated?
   - EBITDA: vendor-computed or company-reported?

2. **Cross-check 5 cases:**
   - For companies with material dilution (TCS, Infosys: large ESOP pools)
   - Verify: vendor's EPS matches company's reported basic EPS
   - Red flag: vendor uses non-standard definition

---

### 6c. Restatement Handling Verification

**For YES Bank (2019 restatement case):**
1. Pull vendor's EPS for FY2018, FY2019 (pre-restatement periods)
2. Cross-check to company's 2021 annual report (which shows restated FY2018-2019 figures)
3. Does vendor show restated or original?
4. RULE: vendor must show restated (original = time-travel data = lookahead)

**Acceptance:**
- If vendor shows restated figures → PASS
- If vendor shows original figures → REJECT

---

## PHASE 7: LOOKAHEAD META-TEST (Defense in Depth)

**Goal:** Comprehensive check that no subtle lookahead exists.

### 7a. Simple Earnings-Quality Strategy (Negative Control)

**Hypothesis:** Build a "quality" strategy using vendor's metrics. If data has lookahead, quality factors will be artificially profitable.

1. **Strategy:**
   - Universe: NIFTY 50 (most liquid)
   - Monthly rebalance (last day of month, T+1 trading logic)
   - Long only (no short-sale complications)
   - Signal: high ROE (>15%) + low debt (D/E < 0.5) + earnings growth >10% YoY
   - Hold: 3 months, equal-weight rebalance

2. **Backtest periods:**
   - Train: 2015-2018 (early data, vendor historical)
   - Test: 2019-2020 (out-of-sample)
   - Holdout: 2021-2023 (most recent, highest lookahead risk if present)

3. **Expected Sharpe ratio (no lookahead):**
   - ~0.4-0.7 (positive but modest, quality does have alpha, but not overwhelming)
   - Return: 8-12% annual (in-line with historical Indian equity returns)

4. **Reject if:**
   - Sharpe > 1.0 in holdout period (too clean, suggests lookahead)
   - Returns > 20% annual (equity returns on known quality factors should be <15%)
   - Drawdown < 15% in any 1-year rolling window (unrealistic for equity strategy)

---

### 7b. Forward P&L Timing Audit

**For any winning trades in Phase 3c & 7a:**

1. **Manual check:** 10 largest winning positions
2. For each position:
   - Entry date (per backtest)
   - Announcement date (per vendor data)
   - Price at entry
   - Price at exit
   - Company news on entry date (from news archives)
   - Rule: announcement must be public knowledge BEFORE entry, OR entry must be AFTER announcement
   - RED FLAG: entry price reacts to announcement (upward jump), but announcement timestamp shows AFTER entry

---

### 7c. Consensus vs Actual Test

**If vendor claims to have "consensus EPS" fields:**

1. Pull vendor's consensus_eps for 20 sample quarters
2. Compare to:
   - Reuters/Bloomberg consensus (if access exists)
   - Manual consensus from prior quarter EPS (as internal proxy)
3. Rule: vendor's "consensus" should be NOT from the future (obvious, but check)
4. Check: is "consensus" refreshed pre-announcement? (should be, it's forward-looking)
5. RED FLAG: if consensus appears to be "back-fitted" post-announcement

---

## PHASE 8: ACCEPTANCE / REJECTION DECISION MATRIX

**Decision rules (evaluated in sequence; first match wins):**

### IMMEDIATE REJECT (Any single item → dataset cannot be used):
1. Any lag < 0 days (data from future)
2. Vendor schema unclear on announcement_date source
3. Use of original (not restated) earnings figures
4. EPS/Revenue spot-check failures > 5 / 20 (>25% error rate)
5. Earnings surprise backtest shows +50 bps or higher average return
6. < 40% delisted company coverage (severe survivorship)
7. Delisted companies have incomplete data (missing pre-delisting quarter)
8. Mean lag > 15 days AND vendor claims real-time updates (lie detection)

### CONDITIONAL ACCEPT (Flag in data catalog, use with caution):
1. Coverage 60-80% NIFTY 500 (mask universes in backtest; use only NIFTY 100+ names)
2. Lag 6-10 days mean (note as editorial lag; acceptable for analysis, not for intraday)
3. 40-70% delisted coverage (add footnote: results may understate tail risk)
4. Earnings surprise backtest: +20 to +50 bps (weak signal, not strong lookahead, but note it)
5. Sector coverage variance > 15% (accept, but stratify tests by coverage per sector)
6. 1-2 major companies (top 50) missing per year (acceptable; manual investigation only)
7. Restatement audit: vendor has restated figures but manual spot-check found 1-2 old figures mixed in (acceptable if < 5% of sample)

### FULL ACCEPT (Can use freely, document):
1. All lags 0-5 days, no negatives, median < 3 days
2. Coverage > 85% NIFTY 500 across 2020-2025
3. > 70% delisted company coverage, complete pre-delisting data
4. All 20 spot-checks pass (within ±0.5% revenue, ±1% EPS)
5. Earnings surprise backtest: <+20 bps average, ~50% win rate
6. Restatement audit: 100% restated figures, no old data
7. Merge/acquisition handling: correct (parent + target separate, not retroactive)
8. All sectors > 70% coverage

---

## PHASE 9: DOCUMENTATION & APPROVAL

### 9a. Deliverables (commit to git):

1. **MG07_VENDOR_AUDIT_[VENDOR_NAME].md** (this template filled)
   - Executive summary (pass/fail + key findings)
   - Detailed results per phase
   - All plots & histograms inlined

2. **MG07_PIT_AUDIT_[VENDOR_NAME].csv** (240 rows × 8 cols)
   - company, quarter, announcement_date_vendor, announcement_date_ground_truth, lag_days, revenue_vendor, revenue_ground_truth, eps_vendor, eps_ground_truth

3. **MG07_LOOKAHEAD_TEST_[VENDOR_NAME].csv** (backtest trade log)
   - Columns: entry_date, exit_date, announcement_date, entry_price, exit_price, pnl_bps, pnl_dollars

4. **data_catalog.md entry** (append to 05_DATA_OFFICE/DATA_CATALOG.md)
   ```
   ### Vendor: [NAME]
   - **Status:** ACCEPT | CONDITIONAL | REJECT
   - **Coverage:** 85% NIFTY 500 (2020-2025)
   - **Lag:** Median 3 days (0-10 range)
   - **Delisted:** 75% coverage
   - **Last verified:** 2026-07-12 (MG07_VENDOR_AUDIT_[NAME].md)
   - **Usage notes:** [Free-text: sector bias, lookahead caveats, mask universes, etc.]
   - **Next re-audit:** 2027-Q1
   ```

### 9b. Approval Gate (D-025):

**Before any backtest using this dataset:**
- CEO + CIO JOINT sign-off on MG07_VENDOR_AUDIT_[NAME].md
- CIO sign-off on PIT test results (lookahead audit is risk responsibility)
- Data Officer adds dataset to DATA_CATALOG with "APPROVED" label

**Approval checklist (signed):**
```
[ ] PIT audit passed (no negative lags, median < 10 days)
[ ] Spot-checks passed (>17/20 within tolerance)
[ ] Lookahead test passed (Sharpe < 1.0, earnings model < +20 bps)
[ ] Survivorship bias assessed (% delisted documented)
[ ] Schema audit completed (Ind-AS confirmed, standalone/consolidated clear)
[ ] Restatement handling verified (only restated figures used)
[ ] Data catalog entry filed
[ ] Approved by: ____________ (CIO) and ____________ (CEO)
[ ] Date: __________
```

---

## PHASE 10: ONGOING MONITORING

**Post-approval checklist (quarterly):**

1. **Data freshness:** new quarters arriving on schedule?
2. **Coverage drift:** any companies suddenly dropping from dataset?
3. **Lag creep:** announcement dates shifting backward (vendor rushing)?
4. **Re-audit trigger:** if any backtest using this data shows anomalous results, re-run MG07_PIT_AUDIT on relevant quarters immediately

---

## IMPLEMENTATION TIMELINE

| Phase | Owner | Days | Gate |
|-------|-------|------|------|
| 1. Inventory | Data Officer | 2 | Schema clear? |
| 2. Sampling | Quant Head | 1 | 30 cos selected? |
| 3. PIT verification | Data Officer + Red Team | 5 | No negative lags? |
| 4. Coverage | Data Officer | 3 | >60% threshold? |
| 5. Survivorship | Quant Head | 2 | >40% delisted? |
| 6. Cross-validation | Quant Head | 4 | 17/20 spot-checks pass? |
| 7. Lookahead meta-test | Quant Head + ML Expert | 5 | Sharpe <1.0? |
| 8. Decision | CIO | 1 | Accept/Reject/Conditional? |
| 9. Documentation | Data Officer | 2 | Catalog + approval signed? |
| **TOTAL** | **All hands** | **~25 calendar days** | |

---

## APPENDIX: PYTHON IMPLEMENTATION SKELETON

```python
# MG07_vendor_audit_harness.py
# Implements Phases 3-7 above

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf

# Phase 3a: PIT Lag Calculation
def calculate_pit_lags(vendor_df, ground_truth_df):
    """
    vendor_df: {company, quarter, announcement_date}
    ground_truth_df: {company, quarter, actual_announcement_date}
    returns: merged df with lag_days column
    """
    merged = vendor_df.merge(ground_truth_df, on=['company', 'quarter'])
    merged['lag_days'] = (merged['announcement_date'] - 
                          merged['actual_announcement_date']).dt.days
    return merged

def check_pit_thresholds(lag_df):
    """Reject if any lag < 0 or mean > 10 days"""
    if (lag_df['lag_days'] < 0).any():
        return "REJECT: Negative lags detected (lookahead)"
    if lag_df['lag_days'].mean() > 10:
        return f"YELLOW: Mean lag {lag_df['lag_days'].mean():.1f} days (high)"
    return "PASS: Lags within threshold"

# Phase 3c: Earnings Surprise Lookahead Test
def earnings_surprise_backtest(vendor_eps, price_df, announcement_dates):
    """
    vendor_eps: {date, company, actual_eps, consensus_eps}
    price_df: {date, company, open, close}
    announcement_dates: {company, quarter, announcement_date}
    
    returns: PnL per trade + Sharpe ratio
    """
    trades = []
    for idx, row in announcement_dates.iterrows():
        company = row['company']
        ann_date = row['announcement_date']
        
        # Entry: next trading day at 09:30
        entry_date = ann_date + timedelta(days=1)
        entry_price = price_df[(price_df['company'] == company) & 
                               (price_df['date'] == entry_date)]['open'].values
        if len(entry_price) == 0:
            continue
        
        # Exit: same day close
        exit_price = price_df[(price_df['company'] == company) & 
                              (price_df['date'] == entry_date)]['close'].values
        if len(exit_price) == 0:
            continue
        
        pnl_bps = (exit_price[0] - entry_price[0]) / entry_price[0] * 10000
        trades.append({
            'entry_date': entry_date,
            'announcement_date': ann_date,
            'pnl_bps': pnl_bps
        })
    
    trades_df = pd.DataFrame(trades)
    sharpe = trades_df['pnl_bps'].mean() / trades_df['pnl_bps'].std() * np.sqrt(252)
    
    return trades_df, sharpe

# Phase 6a: Spot-Check Comparison
def spot_check_figures(vendor_df, bse_df, tolerance_pct=0.5):
    """
    Compare revenue & EPS within tolerance
    tolerance_pct: acceptable % difference
    """
    merged = vendor_df.merge(bse_df, on=['company', 'quarter'])
    merged['rev_error_pct'] = abs(merged['revenue_vendor'] - 
                                   merged['revenue_bse']) / merged['revenue_bse'] * 100
    merged['eps_error_pct'] = abs(merged['eps_vendor'] - 
                                   merged['eps_bse']) / merged['eps_bse'] * 100
    
    pass_count = ((merged['rev_error_pct'] <= tolerance_pct) & 
                  (merged['eps_error_pct'] <= tolerance_pct)).sum()
    
    return pass_count, len(merged), merged

# Phase 4a: NIFTY 500 Coverage
def coverage_analysis(vendor_df, nifty500_membership_df):
    """
    nifty500_membership_df: {year, isin, company_name}
    returns: coverage % per year
    """
    coverage_results = []
    for year in nifty500_membership_df['year'].unique():
        nifty_year = set(nifty500_membership_df[nifty500_membership_df['year'] == year]['isin'])
        vendor_year = set(vendor_df[vendor_df['year'] == year]['isin'])
        coverage = len(nifty_year & vendor_year) / len(nifty_year) * 100
        coverage_results.append({'year': year, 'coverage_pct': coverage})
    
    return pd.DataFrame(coverage_results)
```

---

## SUMMARY CHECKLIST

Before using ANY new quarterly fundamentals dataset:

- [ ] Phase 1: Schema audit (announcement_date defined, no gaps)
- [ ] Phase 2: Stratified 30 companies × 8 quarters selected
- [ ] Phase 3a: PIT lags calculated; no negative; median < 10 days
- [ ] Phase 3b: Lag distribution plotted; >90% in 0-5 day range
- [ ] Phase 3c: Earnings surprise backtest run; Sharpe < 1.0, avg return < +20 bps
- [ ] Phase 4: NIFTY 500 coverage > 70% (80%+ preferred)
- [ ] Phase 5: Delisted companies > 40% (70%+ preferred); IL&FS case confirmed
- [ ] Phase 6a: 20 spot-checks run; ≥17/20 pass within ±0.5%/±1%
- [ ] Phase 6c: Restatement audit (YES Bank case); vendor shows restated figures only
- [ ] Phase 7a: Quality meta-strategy run; Sharpe <1.0, returns <15% annual
- [ ] Phase 8: Decision matrix applied; outcome ACCEPT/CONDITIONAL/REJECT documented
- [ ] Phase 9: MG07_VENDOR_AUDIT_*.md + data_catalog.md entry + CEO+CIO signatures
- [ ] Phase 10: Quarterly re-validation scheduled

---

**Document created:** 2026-07-12  
**Next re-audit cycle:** 2027-Q1 (or immediately if any backtest using this data flags anomalies)

----- ANSWER G021 (task MG07) -----
# MG07 — Verification Protocol for a Third-Party Quarterly Fundamentals Dataset (Indian Equities)

**Author:** Opus (Model Grid MG07) · **Owner on adoption:** Kavya Reddy (Data Office) · **Gate:** D-033/D-009 new-source, JOINT CEO+CIO approval (D-025) · **Date:** 2026-07-13

**Vendor claim under test:** quarterly fundamentals, 2005-present, ~2000 Indian companies, *with announcement dates*.

**Governing rule:** No row of this data touches a backtest, a register entry, or a quoted number until it has passed every phase below AND a LOOKAHEAD AUDIT PASS (D-028, `lib/lookahead_audit.py`). Default posture = **QUARANTINED**. The burden of proof is on the vendor, not on us. We assume the announcement dates are wrong until proven point-in-time, because that is the single failure that silently manufactures alpha.

---

## Phase 0 — Intake, isolation, and schema audit (before any statistics)

**0.1 Physical quarantine.** Ingest to `05_DATA_OFFICE/quarantine/vendorQ_fundamentals/` only. It is NOT added to `DATA_CATALOG.md` as usable, NOT importable by any script under `04_RND_LAB/`. Add a guard in `lib/guards.py` that raises if any path under `quarantine/` is opened by a backtest module. It stays here through Phases 1-6.

**0.2 Freeze a vintage.** Snapshot the exact delivered files with a SHA-256 manifest (`manifest.sha256`) and the delivery date. All verification runs cite this hash. If the vendor re-delivers mid-verification, the clock restarts (mirrors D-030 freeze logic).

**0.3 Schema census (script, ~0 tokens to chat).** Emit a digest per file: row count, column list + dtypes, per-column null %, per-column distinct count, min/max, and the identifier scheme. Specifically resolve:
- **Identifier stability.** What is the primary key — a permanent security ID, ISIN, NSE/BSE symbol, or company name? Symbols and names get REUSED and REASSIGNED in India (ticker recycling, merger renames). If the key is a mutable symbol, that is a coverage/survivorship landmine flagged now.
- **The three critical date columns must all exist and be distinct:** (a) fiscal **period-end** date, (b) **announcement/result** date (board-approved results filed with the exchange), (c) vendor **ingest/last-modified** date if present. If the vendor ships only period-end and a single "date," treat announcement dates as ABSENT → this is the T3 earnings-lookahead landmine (CLAUDE.md #3) and the dataset is presumptively FAIL until they supply real filing dates.
- **Restatement handling.** Is there a vintage/version column, or does the vendor overwrite in place? Overwrite-in-place = restated numbers backfilled onto the original date = lookahead. Flag now, test in Phase 4.
- **Units and scale.** ₹ lakh vs ₹ crore vs ₹ mn; consolidated vs standalone; audited vs unaudited. Mixed scale within a column is a known corruption pattern.

**0.4 Corruption sniff.** Per the local landmine (CLAUDE.md #5, `india_fundamentals_mc` `annual_report` col corrupt at source): scan every text/blob column for encoding garbage, and every numeric column for impossible values (negative shares outstanding, revenue > ₹100 lakh cr, EPS with 6+ decimal noise). Quarantine any column that fails; do not silently drop rows.

**Phase-0 kill condition:** no genuine announcement-date column, or the primary key is an unstable symbol with no crosswalk → **REJECT** (or send back to vendor) before spending effort on later phases.

---

## Phase 1 — Value accuracy against independent ground truth

Goal: are the *numbers* right, before we even ask if the *dates* are right. Two wrongs (wrong number on wrong date) are indistinguishable from noise otherwise.

**1.1 Stratified sample of 120 (company × quarter) cells.** Not random-uniform — stratify to hit the failure surface:
- 30 large-cap, liquid, well-covered (NIFTY50 members at the time) — should be trivially correct; failures here mean systemic problems.
- 30 mid/small-cap (rank 200-500) — where vendors interpolate or guess.
- 20 across the **2008-09 and 2020 stress quarters** — where restatements and delayed filings cluster.
- 20 **early era (2005-2008)** — the thinnest, oldest, most-likely-fabricated coverage.
- 20 **corporate-action quarters**: bonus/split (per-share metrics), mergers, demergers, name changes (Wipro/Bajaj/L&T-family splits, PSU renames).

**1.2 Ground-truth sources, in priority order** (an independent human-checkable trail per cell):
1. The company's own quarterly result PDF / annual report (primary — the audited/board-approved filing).
2. BSE/NSE corporate-announcement archives (the exchange filing of the result).
3. Firm's existing PIT set `datasets/earnings_pit/unified_quarterly_pit.parquet` for overlap cross-check.
4. Screener.in / MoneyControl as a *tie-breaker only*, never as sole truth (they are themselves aggregators and carry the same restatement bias we are hunting).

**1.3 Cross-check fields:** Revenue, Net profit (PAT), EPS, total assets, total equity, shares outstanding — standalone AND consolidated matched to the right basis. Record exact-match / within-rounding / mismatch per field.

**1.4 Thresholds.**
- Large-cap stratum: ≥ 98% of fields exact-or-rounding match. Any *large-cap* PAT/Revenue mismatch > 1% is a **systemic-defect flag** → escalate, expand sample.
- Overall across strata: ≥ 95% match; ≤ 2% hard mismatch (> 5% value error); the rest explainable (consol/standalone basis, restatement, unit).
- Any single field that is *systematically* off (e.g., EPS always pre-split, revenue net-of-excise inconsistent pre/post-GST 2017) → quarantine that field, not the row.

---

## Phase 2 — Are the announcement dates genuinely point-in-time (the crux)

This is where fake alpha is born. A vendor can stamp the *right* number on a date *earlier than the market knew it*, and every earnings/quality/value backtest lights up. Four independent tests, all must pass.

**2.1 Direct filing-date reconciliation (n = 150 quarters).** For each sampled quarter, pull the **actual result-filing timestamp from the BSE/NSE corporate-announcement archive** (the exchange records the date/time the board-approved result was disclosed). Compare vendor announcement date to exchange filing date.
- Accept if `vendor_date >= exchange_filing_date` (same day or later) for ≥ 97% of the sample.
- **Any case where `vendor_date < exchange_filing_date` is a lookahead smoking gun** — the vendor "knew" before the market. Even ONE such case that is not a timezone artifact means the date column cannot be trusted; expand to n = 300 and quantify the leak distribution.

**2.2 The available-date lag distribution (sanity of the whole column).** Compute `announcement_date − period_end` for all ~2000 companies × all quarters and plot the distribution.
- Indian results legitimately land ~30-60 days after quarter-end (SEBI LODR limits: ~45 days for quarterly, ~60 for annual/Q4). A healthy column peaks in the 25-55 day band.
- **Red flags:** a spike at exactly period-end + N constant days for all names (the vendor *imputed* dates with a fixed offset — not real, this is the classic tell), lags of 0-5 days (impossible), or negative lags (announcement before quarter closes). Compare against our own PIT set's known 86.2%-exact-date profile as a reference shape.

**2.3 Imputation detection.** Count how many announcement dates fall on the **1st/last calendar day of a month, on weekends, or on national holidays / exchange-closed days**. Real result filings cluster on trading days and board-meeting days, essentially never on a Sunday. A high weekend/holiday rate ( > ~3%) proves dates are computed, not observed. Cross-check a subset of dates against `corporate-board-meetings` API results (NSE board-meeting archive is reachable per our environment notes) — the board-meeting date should precede/equal the filing date.

**2.4 The one-day-lag falsification (D-028, the decisive test).** Build the smallest possible earnings-drift or quality-rebalance backtest twice: once using the vendor announcement date as the point of availability, once using `announcement_date + 1 trading day`. 
- A *genuine* PIT dataset: results are near-identical (a 1-day lag barely moves a monthly/quarterly-rebalanced signal).
- A *look-ahead-contaminated* dataset: performance **collapses** when you add the lag, because the "edge" was really trading on information stamped before it was public. This is the same trap that has bitten this firm before; it is non-negotiable and runs through `lib/lookahead_audit.py`.

**Phase-2 acceptance:** all four tests pass. 2.1 or 2.4 failing = **REJECT the dataset for any timing-sensitive use** regardless of how good the numbers are.

---

## Phase 3 — Coverage and survivorship

Goal: prove the panel is not silently a survivors-only, backfilled fantasy — the #1 way a "2005-present, 2000 companies" claim inflates backtests.

**3.1 Point-in-time universe reconciliation.** Cross the vendor's *per-date* company list against our survivorship-safe membership: `NIFTY500_TICKER_2005_2025_Final.xlsx` (42 PIT snapshots, CLAUDE.md #6). For each snapshot date, compute: (a) how many then-index members the vendor covers, (b) how many vendor companies are *not* in any contemporaneous index (fine, breadth), and critically (c) **do delisted/merged/bankrupt names from 2005-2015 actually appear with data ending at their death, or are they simply absent?**

**3.2 The dead-company test (survivorship smoking gun).** Assemble a known list of names that delisted, were acquired, went bankrupt, or hit NCLT/IBC between 2005 and today — e.g., Kingfisher, Unitech, DHFL, IL&FS entities, Jet Airways, Reliance Communications, CG Power (near-death), Videocon, plus PSU/bank mergers (the SBI-associate banks, the 2019-20 PSB amalgamation, Vodafone-Idea merger, HDFC-HDFC Bank). 
- A survivorship-clean dataset **contains these names with fundamentals up to their last filing and then a clean terminus.**
- If they are missing, or their history was quietly re-mapped onto the surviving entity, the dataset is survivorship-biased → any long-horizon backtest on it overstates returns. **Quantify** the miss rate; > ~10% of a curated dead-list missing = FAIL for pre-2016 research.

**3.3 Coverage-count time series.** Plot distinct-companies-with-data per quarter, 2005→2026. Expect a **rising** curve (India's listed/covered universe grew; data quality pre-2010 is genuinely thinner). 
- **Red flag: a flat ~2000 from 2005 onward** — that means today's 2000 companies were backfilled to 2005, i.e., the early panel is exactly the set that survived to now = textbook survivorship + backfill. The honest shape is ~600-900 in 2005 climbing toward ~2000.

**3.4 Backfill / look-ahead-listing test.** For a sample of companies that IPO'd after 2005 (say 2015-2020 listings), confirm the vendor has **no fundamental rows dated before their listing/incorporation**. Pre-listing fundamentals = backfilled reconstruction = another lookahead vector.

**3.5 Field-level coverage holes.** Per column, per era, compute null %. A column that is 60% null in 2005-2010 but shipped as "available" will make any factor built on it a small-sample illusion in the early era. Map these holes explicitly so no one builds a 2005-start signal on a field that only densifies after 2012.

---

## Phase 4 — Restatement / vintage integrity

**4.1 Restatement direction test.** For companies with known material restatements (Yes Bank, DHFL, and any forensic-flagged names), check whether the value the vendor shows *on the original announcement date* is the **originally reported** number or the **later restated** number. If restated numbers are stamped on the original date, that is lookahead of the worst kind (the market did not know the restatement then). Real PIT data preserves the as-first-reported figure and carries the restatement as a *later* vintage.

**4.2 Point-in-time replay.** If a vintage column exists, reconstruct "what the dataset said as of date T" for three historical dates (e.g., 2012-06-30, 2018-06-30, 2022-06-30) and confirm it excludes anything filed after T. If overwrite-in-place (no vintage), we must treat EVERY value as potentially restated → the dataset is usable **only** with the announcement-date lag AND a documented caveat that restatements are baked in; flag to CIO for a use-restriction ruling.

---

## Phase 5 — Independent-source triangulation & internal consistency

**5.1 Accounting identities (free, whole-panel).** Programmatically test on 100% of rows: Assets = Liabilities + Equity (within rounding); EPS × shares ≈ PAT (basis-adjusted); consolidated ≥ standalone where both exist for revenue/assets; sequential quarters sum toward the annual figure. Rows failing identities → quarantine, tabulate the failure rate (a healthy vendor: < 0.5%).

**5.2 Overlap correlation with our PIT set.** On the intersection with `unified_quarterly_pit.parquet`, correlate PAT/Revenue/EPS. Expect ρ > 0.99 on matched basis. Systematic offsets (constant multiplier, sign flips, off-by-one-quarter alignment) surface exactly here and are the most common integration bug.

**5.3 Off-by-one-quarter alignment check.** A frequent vendor error: labeling Q1 data as Q2, or fiscal-year (Apr-Mar Indian FY) mislabeled as calendar. Verify the fiscal-period convention explicitly against 20 known filings; India's Apr-Mar year makes this a live trap.

---

## Quarantine → Acceptance decision rules

Each phase writes a pass/fail line + evidence file to `quarantine/vendorQ_fundamentals/verification/`. Final adjudication:

**REJECT outright if any of:**
- No genuine announcement-date column (Phase 0.3), or
- Phase 2.1 shows announcement dates predating exchange filings (non-timezone), or
- Phase 2.4 one-day-lag test collapses the toy backtest, or
- Phase 3.2 dead-company miss rate high / coverage curve flat-at-2000 (survivorship).

**CONDITIONAL ACCEPT (partial, scoped) if:** value accuracy passes and dates pass for the **modern era only** (e.g., dates reliable 2013→present but imputed pre-2013). Then the dataset is catalogued with a hard **use-window** (`min_reliable_date`) enforced in code, and pre-window rows stay quarantined. Common realistic outcome.

**FULL ACCEPT only if:** Phase 1 ≥ 95% (large-cap ≥ 98%), all four Phase-2 tests pass, Phase-3 coverage curve is honest + dead-list present, Phase-4 restatements handled as vintages (or documented+lagged), Phase-5 identities < 0.5% fail — **AND** a fresh `lib/lookahead_audit.py` PASS on a real candidate signal, red-teamed by Nikhil Bose.

**On acceptance:** add to `DATA_CATALOG.md` with: vintage SHA, `min_reliable_date`, standalone-vs-consol convention, known field-null eras, restatement policy, and the announcement-date-lag rule that MUST be applied (availability = announcement_date, never period-end). Add a `guards.py` helper so downstream code cannot read period-end as the availability date. Log the D-009/D-025 joint approval in `DECISIONS_LOG.md`.

**Ongoing (post-adoption):** monthly freshness ping (new quarters land within LODR windows); re-run the accounting-identity sweep on each delivery; any vendor re-delivery that changes historical rows triggers a restatement-audit before it overwrites our frozen vintage.

---

### One-line summary for the IC
Prove the *numbers* right (Phase 1), then prove the *dates* were knowable-then not known-now (Phase 2, especially the exchange-filing reconciliation and the one-day-lag collapse test), then prove the *panel isn't just survivors backfilled to 2005* (Phase 3). Anything less and we are buying manufactured alpha at data-vendor prices.

----- ANSWER G013 (task MG07) -----
**Verification protocol before a third-party quarterly fundamentals dataset (India, 2005–present, ~2000 companies, with announcement dates) is allowed near a backtest**

**1. Sampling and cross-checks against ground truth**
- Stratified random sample of 150–250 (company, quarter) pairs, stratified by market-cap decile, sector, and era (pre-2010 / 2010–2015 / 2015–2020 / 2020–present), since vendor data quality is rarely uniform across time or cap size.
- For each sampled row, pull the actual filed result (exchange filing / annual report / investor presentation) and diff every reported field: revenue, EPS, reported date. Track a field-level error rate, not just a pass/fail per row — some fields (revenue) are usually cleaner than derived ones (adjusted EPS, segment-level numbers).
- Cross-check a subset against a second independent source (a different data vendor, or the company's own investor-relations XBRL filing) to catch systematic vendor-specific errors that a single-source check would rubber-stamp.

**2. Testing that announcement dates are genuinely point-in-time**
- For the sampled rows, find the actual public disclosure date/time from the exchange filing system (NSE/BSE corporate announcements) and compare to the vendor's `available_date`/`announcement_date` field. Flag any row where vendor date is *earlier* than the true public filing date — this is the dangerous failure mode (it manufactures lookahead) versus vendor date being *later* (merely conservative/costly, not corrupting).
- Check for a suspicious pattern: is the vendor's announcement date suspiciously always "quarter-end + fixed N days" for every company (a strong tell they backfilled from a template/estimate rather than tracking the actual filing) rather than the genuinely variable real-world lag (which ranges roughly 15–60 days and varies company to company and quarter to quarter)?
- Explicitly test post-facto restatements: does the vendor overwrite a quarter's historical figures when a company later restates, losing the *originally reported* number? A backtest must use what was known at the time, not the eventually-restated "true" figure — verify the vendor exposes (or at least doesn't silently mutate) as-originally-reported values.

**3. Coverage and survivorship checks**
- Reconcile vendor company count and identifiers, quarter by quarter, against the historical NSE/BSE listed-universe count for that quarter — if the vendor's earliest years show materially fewer companies than the exchange's actual listed count for that period, that's a coverage gap concentrated in the past (classic survivorship signature).
- Explicitly check whether delisted/merged/renamed companies are present with their historical data intact, or whether they silently vanish from the dataset the moment they stop being "current" (query the vendor for 20–30 known-delisted names and confirm their historical quarters are still retrievable).
- Check for "look-ahead-friendly" gaps: quarters with suspiciously fewer NA/missing fields in early years than plausible given actual filing quality at the time (over-clean historical data is a red flag for backfilled/estimated figures).

**4. Quarantine / acceptance rules**
- Quarantine (do not admit to any backtest) any field/era/sector stratum where the sampled error rate exceeds a pre-set threshold (e.g., >2% of numeric fields materially wrong, or any confirmed instance of an `available_date` earlier than the true filing date).
- Accept only strata that pass both the value-accuracy check and the PIT-date check; document acceptance per (field, era, cap-bucket) rather than as a single dataset-wide yes/no, since it is normal for one vendor to be fine post-2015 and unreliable pre-2010.
- Re-run the full sampling check any time the vendor pushes a "data refresh" — a silent methodology change in a refresh is a common way clean data quietly becomes contaminated.

============================================================
# TASK MG08 — rubric anchors:
  1. overfitting / multiple-testing (DSR/PBO)
  2. costs & slippage under-modeled
  3. lookahead / PIT violation
  4. survivorship bias
  5. regime dependence / crowding decay
  6. capacity / market impact
  7. ranked by probability
  8. mechanism: HOW each inflates the number
  9. a specific check per failure mode
  10. mechanisms not buzzwords

----- ANSWER G020 (task MG08) -----
Answering from reasoning alone, as asked — no tools. One framing fact first, because it sets the prior: a 2.1 Sharpe over 14 years is a t-stat of ~2.1 × √14 ≈ 7.9, in the *hardest* modern regime for cross-sectional equity ML (post-2010, post-anomaly-decay), published for free. Honest first-shot academic ML long-short results in this era cluster around 0.5–1.2 gross. So the question isn't whether something inflates the number, but which mechanisms and in what order of likelihood.

## 1. The "out-of-sample" period isn't — test-set reuse / multiple testing (near-certain)
**How it inflates:** 940 features plus architecture, horizon, rebalance frequency, and portfolio-construction choices give thousands of researcher degrees of freedom. If any were selected because they looked good on 2010–2023 — across months of team iteration, this is almost unavoidable — the reported Sharpe is the *max of many correlated noisy trials*, not an estimate. With a Sharpe standard error of ~0.3–0.5 over 14 years, picking the best of a few hundred configurations manufactures 1–1.5 Sharpe units from a true zero.
**The check:** freeze the released code/config and run it once, untouched, on data the authors could not have consulted — 2024 through mid-2026. A real 2.1 process stays strongly positive; a mined one reverts toward zero. (Proxy if you can't wait: demand the trial count and compute the Deflated Sharpe Ratio.)

## 2. Look-ahead leakage in the features — point-in-time failures (very likely; one leak among 940 suffices)
**How it inflates:** fundamentals aligned to fiscal-period-end instead of filing date let the model trade earnings 45–90 days before the market saw them; restated rather than originally-reported values leak corrections. News sentiment is worse: vendor histories are backfilled and re-scored with models built *after the fact*, and any sentiment classifier fine-tuned on 2010–2023 labels encodes which words predicted returns over the test period itself. Full-sample feature standardization in the ML pipeline is the same bug in miniature. A flexible model finds the one leaking column and rides it — producing exactly the claimed signature: implausibly high *and* implausibly stable.
**The check:** lag every feature by a conservative availability buffer (fundamentals +90 days unless filing-dated, news +1 trading day) and rerun the frozen pipeline. A real signal decays mildly; a leak collapses discontinuously.

## 3. Gross-of-cost returns on a high-turnover book (near-certain to be present; often disclosed, still fatal to replication in dollars)
**How it inflates:** models mixing daily prices and news load on short-horizon signals with turnover of 50–200% of the book per rebalance. The reported numerator is gross alpha, much of which is compensation for crossing spreads and providing liquidity — costs a real trader pays, not earns. Add short-leg borrow fees and impact, and the published pattern is gross ~2 falling to ~0–0.5 net.
**The check:** compute annualized one-way turnover from their positions and apply a size-dependent cost curve (effective half-spread by cap decile + borrow fees on shorts); report the net Sharpe. If the paper can't even produce turnover, that is itself the finding.

## 4. The alpha lives in micro-caps and an unshortable short leg (likely, especially if equal-weighted)
**How it inflates:** cross-sectional ML predictability concentrates in the smallest deciles; equal-weighted decile spreads put half the book in names with tiny ADV, wide spreads, and hard-to-borrow or no-borrow shorts. Stale closes and bid-ask bounce in these names mechanically manufacture short-horizon "reversal alpha" that exists in the database, not the market. Capacity is a few million dollars.
**The check:** rerun value-weighted on a liquid universe (top ~1,000 by market cap, price > $5, borrowable shorts). The genre-typical result is a 50–80% Sharpe loss — the surviving number is the honest headline.

## 5. Same-bar execution — trading at prices that predate signal availability (moderately likely; a quiet engine bug)
**How it inflates:** signal built from day-t closes (or news published through 4:00 pm, or after-hours filings), fills assumed at the day-t close. The backtest captures the market's reaction to information at a price set *before* the information was actionable; with news sentiment this silently harvests the announcement-day jump itself. Vendor "story creation" timestamps, often backdated relative to true dissemination, compound it.
**The check:** delay all fills to the t+1 open (and require exchange-timestamped information strictly before each fill) and rerun. A drop much beyond ~20–30% flags the timing bug rather than genuine fast alpha.

## 6. Survivorship and merge-induced coverage bias — missing delistings (plausible, and specifically invited by this design)
**How it inflates:** inner-joining prices, fundamentals, *and* news coverage silently drops firms that died, delisted, or were too small for news coverage — the panel is conditioned on survival. Longs in distressed names show "recoveries" because the corpses are absent; positions in stocks that delist exit at the last stale price instead of the ~−30% average performance-delisting return. The ML model then learns and amplifies this biased conditional mean.
**The check:** count security deaths per year in their final panel against CRSP baseline delisting rates (~4–8% of listings/year) and verify delisting returns are applied in the P&L. A near-zero death count confirms the bias.

**Overall read:** items 1–3 are each individually close to certain in this genre and jointly sufficient to explain 2.1 → ~0.5 investable; 4–6 are the standard residual suspects a referee should clear in that order. The single highest-value replication act is the combination of checks 1+2: frozen pipeline, lagged features, post-2023 data — one run answers most of the list.

Sanity check against the ask: 6 items, ranked by probability, each with an explicit inflation mechanism and exactly one decisive check — covered, no tools used.

result: Ranked the 6 likeliest reasons the claimed 2.1 OOS Sharpe won't survive — test-set reuse, feature look-ahead, gross-of-cost reporting, micro-cap concentration, same-bar execution, survivorship — each with its inflation mechanism and one decisive verification check.

----- ANSWER G001 (task MG08) -----
# Analysis: Why 2.1 Sharpe on 940-Feature ML Model Will Not Survive Scrutiny

## Premise
Claimed: Machine-learning strategy on US equities, 2010–2023 out-of-sample, 2.1 Sharpe ratio, 940 features from prices + fundamentals + news sentiment.

---

## Rank 1: Multiple Testing / P-Hacking (Probability: ~95%)
**Mechanism:**  
With 940 features, the feature space is enormous. Even if 939 are noise, random walk returns will correlate with ~50 of them by chance (at α=0.05). The paper likely trained a model on the full dataset, selected top-performing features, then declared the result "out-of-sample" on a held-out period. But feature selection happened using the full history — the test set was implicitly contaminated during feature engineering.

**Single Check to Confirm/Clear:**  
Run the exact model on a *different stock universe* (e.g., Russell 2000, emerging markets, or a held-out 200 stocks never used anywhere) or a *later time period* (2024 forward). If Sharpe collapses to <1.0, the edge was noise.

---

## Rank 2: Look-Ahead Bias in News Sentiment (Probability: ~92%)
**Mechanism:**  
News sentiment feeds are notorious for timestamp confusion. A feature like "average sentiment of news published on day T" is often *forward-filled* or uses *publication date* instead of *true announcement time*. If sentiment was released at 3 PM but used to trade at 10 AM, or if the data vendor backfilled sentiment retroactively, the model sees future information disguised as day-T data.

**Single Check to Confirm/Clear:**  
Rebuild the strategy using *only* sentiment available at market open (e.g., sentiment from news published before 9:30 AM ET). If you cannot obtain truly real-time sentiment timestamps or the data vendor cannot confirm their methodology, discard the sentiment features. Retest the model on just prices + fundamentals.

---

## Rank 3: Fundamental Data Look-Ahead (Probability: ~88%)
**Mechanism:**  
Quarterly earnings, book value, and analyst estimates are *released* days or weeks after the period ends, yet the dataset stamps them with the *quarter-end date*. If the model uses "Q1 earnings available on quarter-end" but the company released them on day +45, the model traded on information not yet public. Point-in-time (PIT) data is rare; most fundamental datasets are contaminated.

**Single Check to Confirm/Clear:**  
Obtain a *point-in-time fundamental dataset* with explicit `available_date` or `announcement_date` for every data point. Lag all fundamentals by ≥45 days from quarter-end (or use the actual release date). Rebuild the model. If results degrade significantly, lookahead was the edge.

---

## Rank 4: Survivorship Bias (Probability: ~85%)
**Mechanism:**  
A backtest on "US equities 2010–2023" typically only includes stocks that *survived* to 2023. Companies that went bankrupt, delisted, or were acquired mid-period are excluded or assumed perfect survivor status. This inflates returns because the strategy avoids the catastrophic losses that actually occur in live trading. The true edge is selecting *winners*, not finding alpha — the losers are invisible in the backtest.

**Single Check to Confirm/Clear:**  
Backtest on a *fixed universe of stocks defined at 2010* (e.g., the S&P 500 constituents as of Jan 2010), including all bankruptcies, delistings, and mergers as they occurred (with the actual delisting return). Use a survivorship-bias-adjusted dataset (e.g., CRSP with delisting returns or Compustat with PIT membership snapshots). Sharpe will likely drop 0.3–0.8 points.

---

## Rank 5: Underestimated Transaction Costs & Slippage (Probability: ~82%)
**Mechanism:**  
A 940-feature neural network changes its predictions constantly, likely generating high turnover (e.g., rebalance daily or weekly). The backtest assumes frictionless trading (or 1 bps cost), but realistic costs are 5–10 bps per trade round-trip, plus market impact on large positions, plus bid-ask spread on illiquid names. For a high-turnover strategy, these costs can reduce net Sharpe by 0.5–1.5 points. News and sentiment data often signal short-lived mispricings requiring fast trades with high slippage.

**Single Check to Confirm/Clear:**  
Calculate the strategy's actual turnover (fraction of portfolio rebalanced per period). Rebuild the backtest with *realistic* costs: 5 bps per leg for equities, 2% slippage on prediction confidence (e.g., if the model predicts +2% return, realized return after costs is ~1.9%), and 50% market impact for the top 5% of trades. If the strategy turns over >50% monthly, increase costs further.

---

## Rank 6: Validation Set Contamination / Walk-Forward Overfitting (Probability: ~78%)
**Mechanism:**  
The paper claims "2010–2023 out-of-sample," but typical ML pipelines do walk-forward validation or nested cross-validation. If hyperparameters (model size, dropout, learning rate, feature scaling) were tuned using the "out-of-sample" 2020–2023 window, or if features were engineered using statistics from the full 2010–2023 period, the test set was implicitly used during model selection. This is not a true hold-out test.

**Single Check to Confirm/Clear:**  
Specify and freeze the exact model architecture and hyperparameters using *only* 2010–2019 data. Then test on 2020–2023 without any parameter tweaks. Re-run this model live (paper-trade) on 2024 data without retraining. If Sharpe on 2024 falls below 1.0 or the model was retrained post-2023, contamination occurred.

---

## Confidence Assessment
- **Ranks 1–3** are quasi-certain pitfalls; 2.1 Sharpe claims on 940-feature ML almost always fall to one of these.
- **Ranks 4–6** depend on the paper's methodology disclosure; if they explicitly address these (fixed universe, PIT data, true hold-out), risk drops but rarely to zero.
- **A credible 2.1 Sharpe would require:** published code+data, a fixed pre-registered analysis plan, independent replication attempt, and live forward-test track record >12 months. Claims without this should be assumed false until proven otherwise.

----- ANSWER G005 (task MG08) -----
# Why a 2.1 OOS Sharpe (ML, US equities, 2010-2023, 940 features) will not survive

Claim under test: ML strategy, US equities, **2.1 Sharpe out-of-sample, 2010-2023, 940 features** from prices, fundamentals, news sentiment.

Prior: a genuine, tradable, cost-net 2.1 Sharpe on liquid US equities over 13 years is roughly the top ~1% of all published equity strategies and is almost never reproduced by a third party. The base rate says the number is inflated by one or more of the mechanisms below. Ranked by probability that this is the/a killer.

---

## 1. Backtest overfitting on a window that is not truly out-of-sample (selection bias / multiple testing)
**Probability: very high.** This is the signature failure for a 940-feature ML paper.

**Mechanism (how it inflates):** With 940 candidate features plus ML hyperparameters (depth, learning rate, regularization, lookback, rebalance freq, universe cut), the effective number of trials is in the thousands. If features/architecture/hyperparameters were chosen — even informally, across paper revisions — by looking at performance over 2010-2023, then the "OOS" period has already leaked into model selection. The max Sharpe over N independent trials grows like `sqrt(2 ln N)`; at N in the hundreds you *expect* a best-of ~2.0 Sharpe from pure noise. What's reported is the winner of a search, not an unbiased estimate. Cross-validation on shuffled or randomly-split rows (instead of a strict forward split) also lets the model see future-distribution information.

**Single check:** Compute the **Deflated Sharpe Ratio (Bailey/Lopez de Prado)** / **PBO** using the authors' honest trial count and return autocorrelation; equivalently, demand a *pre-registered, never-touched* final holdout (e.g. train/tune only on 2010-2018, evaluate once on 2021-2023) and see whether the 2.1 survives that single untouched shot.

---

## 2. Point-in-time / lookahead leakage in fundamentals and news sentiment
**Probability: very high.** Fundamentals and sentiment are the two most leakage-prone feature families in existence.

**Mechanism:** Fundamentals dated to *fiscal-period-end* rather than the *filing/availability date* give the model quarter results 30-90 days before they were public (and restated/as-revised figures the market never saw at the time). News sentiment leaks when articles are timestamped by event date rather than publication-feed time, when the sentiment scorer was trained on the same period it scores, or when the ticker-to-article mapping uses the current (survivor) identifier set. Any of these lets the model condition on the future, and it will happily exploit it — this is the classic "the alpha vanishes when I lag the data by one day."

**Single check:** Rebuild every feature strictly PIT — fundamentals lagged to actual SEC filing date, sentiment lagged to feed-publication timestamp — then re-run with an added **uniform one-day lag** on all features. A real edge degrades gently; a leakage artifact collapses toward zero.

---

## 3. Transaction costs, turnover and market impact ignored (gross vs net Sharpe)
**Probability: high.** The single most common reason a real backtest doesn't survive scrutiny.

**Mechanism:** A 940-feature daily/weekly ML model typically produces high turnover (often 100-1000%+ annually). Sharpe reported on *gross* returns omits bid-ask spread, commissions, financing/short borrow, and price impact. On US equities, even a modest 10-20 bps round-trip against high turnover subtracts 1.0-1.5 from the Sharpe; short-borrow and impact on the fast-signal names take more. A 2.1 gross can be a 0.4-0.8 net — publishable, untradeable.

**Single check:** Ask for **reported annual turnover** and recompute net Sharpe with realistic costs (spread + commission + a square-root impact term sized to each name's ADV). If turnover isn't disclosed, treat the 2.1 as gross and discount accordingly.

---

## 4. Survivorship bias and illiquid / microcap concentration (untradeable alpha)
**Probability: medium-high.**

**Mechanism:** (a) Survivorship — if the universe is today's listed names or a CRSP pull without delisting returns, the model never buys the companies that went to zero, mechanically lifting returns and Sharpe. (b) Concentration — much cross-sectional ML alpha lives in small, illiquid, high-spread names where the *modeled* fill is impossible at any real size; the top-decile long-short is dominated by stocks you can't trade. Both make the paper number real on paper and unrealizable in a fund.

**Single check:** Restrict to a **liquid, survivorship-free universe** (e.g. survivorship-free CRSP *with delisting returns*, price > $5, top ~1000 by dollar ADV) and re-run. If the Sharpe halves, the edge was in the untradeable/dead tail.

---

## 5. Disguised factor/beta exposure and single-regime luck
**Probability: medium.**

**Mechanism:** 2010-2023 is essentially one macro regime — post-GFC QE bull market, secular low rates, mega-cap growth/quality/momentum leadership — with only 2022 as a real stress. A strategy that is net-long-biased, or that is a repackaging of momentum + quality + low-vol, earns those risk premia and a rising-market beta, then reports the total as "alpha." The 2.1 is partly compensation for known factor exposure, not a novel edge, and is conditional on a regime that may not repeat.

**Single check:** Regress the strategy's returns on **market + Fama-French 5 + momentum (and a short-vol proxy)**; report the *residual* alpha and its t-stat, and split the Sharpe across sub-periods (2010-15 / 2016-19 / 2020-23, isolating 2022). If alpha isn't significant after factors, or the Sharpe is carried by one sub-period, it's beta/regime luck.

---

## 6. Sharpe computation artifacts (autocorrelation, non-normality, annualization)
**Probability: medium-low, but a pure free win to check.**

**Mechanism:** Daily/monthly Sharpe scaled by `sqrt(252)`/`sqrt(12)` is overstated when returns are **positively autocorrelated** — which they are whenever positions are held in illiquid names or NAV is stale/smoothed (return smoothing depresses measured volatility and inflates Sharpe). Overlapping-window returns, an unrealistically low or omitted risk-free rate, or a strongly negatively-skewed / fat-tailed payoff (Sharpe rewards steady small gains and hides the rare large loss) can also flatter the ratio relative to the true risk.

**Single check:** Recompute with an **autocorrelation-adjusted (Newey-West / Lo) Sharpe**, verify the risk-free/excess-return convention, and cross-check internal consistency: a genuine 2.1 Sharpe over 13 years implies a shallow max drawdown (roughly < ~10-12%). If the reported max drawdown or return skew is inconsistent with 2.1, the ratio is a computation artifact.

---

### One-line triage order
Check in this sequence — each is cheaper than the last to falsify: **(6) recompute the ratio → (5) factor-regress → (3) net of costs/turnover → (4) liquid survivorship-free universe → (2) PIT + one-day-lag test → (1) deflated Sharpe / single untouched holdout.** In practice #1, #2, and #3 kill the large majority of headline ML equity Sharpes.

----- ANSWER G014 (task MG08) -----
**A published ML strategy claims 2.1 Sharpe out-of-sample, US equities, 2010–2023, 940 features (prices/fundamentals/news sentiment) — 6 most likely reasons the number won't replicate, ranked by probability**

1. **Look-ahead / leakage in the feature set (most likely).** *Mechanism*: with 940 heterogeneous features assembled from multiple vendors, at least some are very likely timestamped or point-in-time-adjusted incorrectly (a classic culprit: fundamentals keyed to fiscal period-end rather than public filing date; sentiment features built from data with a delayed/adjusted timestamp that doesn't match true availability). Any single leaking feature among 940 can single-handedly manufacture a large chunk of an inflated Sharpe. *Check*: rebuild the top 20 features by importance and manually verify the exact availability timestamp of each against the true public-disclosure time; re-run with every feature lagged one extra day and see if the Sharpe survives.

2. **"Out-of-sample" is not actually out-of-sample (feature/hyperparameter selection leakage across the split).** *Mechanism*: with 940 candidate features, if any feature selection, hyperparameter tuning, or even the choice of which 940 features to build was informed by looking at performance on data inside the "out-of-sample" window (common when a research team iterates for years before finalizing a paper), the OOS Sharpe is contaminated by implicit multiple-testing / overfitting to that window. *Check*: is there a genuinely separate, never-touched-during-development holdout (e.g., data after the paper's own analysis concluded) — if the OOS window is the same one used throughout years of iteration, that's the tell.

3. **Backtest doesn't reflect achievable trading costs/capacity.** *Mechanism*: a paper Sharpe of 2.1 on a broad ML strategy touching hundreds of features often implies meaningful turnover concentrated in smaller/less liquid names where the feature signal is strongest (classic ML-momentum-in-microcaps pattern); realistic market impact at any deployable size collapses the number. *Check*: report the strategy's actual capacity curve (Sharpe vs AUM) and the liquidity profile (average ADV%) of the positions actually driving the PnL — if this is absent from the paper, that's itself a red flag.

4. **Survivorship bias in the underlying universe/fundamentals panel.** *Mechanism*: 2010–2023 spans multiple bankruptcies/delistings; if the fundamentals/price panel used quietly drops delisted names or backfills identifiers, the strategy never "experiences" its worst-case losers, inflating Sharpe. *Check*: confirm the universe construction explicitly includes delisted names with realized terminal losses, not a current-day universe applied backward.

5. **Selection bias in what gets published (file-drawer / multiple-comparisons across many candidate models).** *Mechanism*: academic and practitioner research pipelines commonly try dozens of model/feature-set variants and publish the best one; a 2.1 Sharpe may be the max of many attempts rather than the expected performance of "the" method. *Check*: ask whether the paper reports a distribution of results across model variants tried (most don't) — if only the winning configuration is shown, treat the number as an order statistic, not an expectation, and apply a haircut consistent with the number of variants plausibly tried.

6. **Overlapping/autocorrelated return sequences inflate the Sharpe's implied statistical confidence (and sometimes the point estimate itself via return-compounding artifacts).** *Mechanism*: if the model rebalances frequently with overlapping holding periods across many names, naive daily-PnL Sharpe annualization (×√252) assumes i.i.d. daily returns; real strategy PnL is autocorrelated (through shared factor exposure and overlapping signals), so the annualized Sharpe overstates the true risk-adjusted return and — separately — small implementation quirks (mark-to-market timing, using close-to-close on names that don't all close simultaneously) can shift the point estimate directly. *Check*: recompute Sharpe using overlapping-adjusted (Newey-West style) variance and compare; also recompute using a coarser (weekly/monthly) return frequency, which should reduce but not eliminate the reported Sharpe if it's genuine — a large drop on de-frequencing is diagnostic of an inflated daily number.

======================================================================
# PART B

============================================================
# REMINDER: output only `ID=Gxxx SCORE=n HITS=n NOTE=...` lines. All 24 answers.