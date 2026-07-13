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
