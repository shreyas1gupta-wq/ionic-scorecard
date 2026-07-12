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

