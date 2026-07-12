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
