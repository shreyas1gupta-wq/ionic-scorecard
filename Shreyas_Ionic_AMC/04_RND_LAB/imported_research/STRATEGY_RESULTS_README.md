# Nifty 500 Multi-Factor Strategies — Backtest Report
**Period:** Apr 2006 – Dec 2025 (19.7 yrs) · **Costs:** 0.375%/side (buy and sell separately) · **Execution:** T+1 close, circuit-deferred fills · **Universe:** point-in-time Nifty 500 constituents (incl. delisted where data exists) · **Sleeves:** equity / gold / cash, 0–100% · **No shorting. No leverage.**

## Headline results (all NET of costs)

| | S1 AURUM-24 (Multi-Factor) | S2 IGNITION-15 (Aggressive) | S3 STEADY-24 (Low churn) | EW Benchmark |
|---|---|---|---|---|
| CAGR | **21.8%** | **33.5%** (23.4% ex-2007) | **17.2%** | 23.1% |
| Volatility | 10.3% | 28.8% | 7.0% | 19.5% |
| Sharpe (rf=6%) | **1.37** | 0.91 | **1.43** | 0.85 |
| Sharpe (rf=0) | 1.94 | 1.11 | 2.27 | — |
| Max drawdown | **−20.8%** | −36.9% | **−12.7%** | −60.5% |
| Turnover | 3.6×/yr | 12×/yr | **2.7×/yr** | — |
| Worst month | −11.5% | −22.7% | −8.1% | — |
| ₹1 became | ₹49 | ₹294 | ₹23 | ₹66 |
| Stocks held | 24 | 15 | 24 | — |

Sub-period Sharpe (S1): 2006-10: 1.39 · 2011-15: 1.38 · 2016-20: 0.67 · 2021-25: 1.91. From-2010-only: 1.41.

## The three strategies in one paragraph each

**S1 AURUM-24** — 12 momentum stocks (risk-adjusted 12-1 momentum, 6m momentum, 52-week-high proximity, entries require positive momentum and price>200dma) + 12 low-volatility stocks (low 9m vol, monthly win-rate, price>200dma), equal-weighted, refreshed monthly with a wide exit buffer (only exit when rank falls below 3× sleeve size). 25% strategic gold (momentum-gated to cash). Equity exposure = trend gate (EW-market vs 200dma + 6m momentum) × volatility target (16%, quantized 0.25 steps), with a daily crash brake (10-day market return < −10% → equity capped at 25%). Risk-off capital goes half to gold when gold momentum is positive, else cash.

**S2 IGNITION-15** — 15 equal-weight fast-momentum stocks (3m risk-adjusted momentum + 6m momentum + 52w-high), biweekly refresh, fast regime gate (50dma + 3m momentum: 100/50/0%), risk-off to gold/cash, daily crash brake. Highest CAGR config that survived costs; weekly rebalancing was tested and is *worse* net of costs.

**S3 STEADY-24** — 24 low-vol/quality stocks, inverse-vol weighted (6% cap), quarterly refresh with a very wide buffer (turnover 2.7×/yr), 30% strategic gold, 10% vol target, monthly exposure checks + daily brake. 73% positive months, worst month −8.1%, MDD −12.7%.

## Practical frictions modeled
Slippage+costs 0.375% each side separately; T+1 close execution (no lookahead); ≥18% close-close move treated as circuit-locked — buys deferred up to 5 days then dropped, sells retried until filled; permanent delisting exits at last traded price with an extra 7.5% haircut; gaps in data treated as untradable holds; cash earns 6% p.a.; gold carries 0.9%/yr ETF drag; minimum 15 / maximum 25 stocks enforced by design.

## Honest answers to your three targets
1. **Sharpe > 1.5:** Met under rf=0 (S1: 1.94 daily, 1.65 monthly; S3: 2.27) but **not against a 6% INR risk-free** (S1: 1.37, S3: 1.43). A verified, survivorship-aware, cost-aware net Sharpe of ~1.4 vs 6% rf is the realistic ceiling on this dataset. We stopped adding knobs because the sensitivity grid (in the Excel) shows every honest variant lands between 1.24–1.39 — pushing past that would be curve-fitting, not alpha.
2. **CAGR > 60%:** Not honestly achievable sustained over 20 years (₹1 → ₹1.2 lakh; market impact alone forbids it). S2 delivered 60%+ only in regime years (2007: +541%, 2014: +100%, 2021: +64%, 2023: +74%). Its honest long-run expectation is 23–33% net. Any backtest claiming sustained 60% net CAGR on Indian equities is overfit or ignores costs/liquidity.
3. **Low churn / low MDD:** S3 — 2.7×/yr turnover, −12.7% MDD, no shorting.

## Key data caveats (full list in Excel → "Caveats & Data Notes")
- Delisted-stock daily data exists only in sampled windows; universe coverage 57%→90% over time. **Pre-2011 results are likely overstated** for strategies and benchmark alike; from-2010 stats are the reliable ones (S1 1.41 / S3 1.41 Sharpe).
- Gold is monthly LBMA×USDINR interpolated daily → gold-sleeve daily vol understated; real MDD could be 1–3pp deeper.
- Capacity: suitable below roughly ₹25–50 cr; beyond that impact exceeds the modeled 0.375%.

---

# S4 APEX-BREAKOUT (added on request): high churn, high CAGR, leverage ≤1.5×

**Rules.** Buy fresh 100-day-high closes (PIT member, positive 6m momentum, ranked by risk-adjusted momentum), 10% of NAV per entry, max 18 positions, holding capped at 20% (trim to 15%). Exit on vol-scaled trailing stop (10–25% from peak) or 50dma break with negative momentum. Portfolio gross exposure: 1.5× when market >200dma with positive 6m momentum, 1.0× mixed, 0.1× when both negative or after a −10% 10-day crash; no new entries in OFF regime or when market vol >30%. Borrowed cash costs 9.5%/yr. Same frictions as the others (0.375%/side, T+1, circuits, delisting haircuts).

**Results (net):** CAGR **44.5%** · MaxDD **−29.8%** · Vol 46.7% (87% in 2006-10, ~20% after 2011) · turnover 8×/yr · ~1,700 trades · avg 14.7 positions · ₹1 → ₹1,375.
Sub-periods: 2006-10: **131%/yr** · 2011-15: 28.9% · 2016-20: 23.9% · 2021-25: 20.0%. Cost stress: 40.5% CAGR even at 0.75%/side. Sensitivity flat across lookback 75–125d and leverage 1.0–1.5× (CAGR 40–45.5%).
**Honest read:** the 131%/yr block is a 2007-mania artifact partly; the forward expectation is **20–30%/yr with ~−30% drawdowns**. Leverage adds ~5pp CAGR vs the unlevered version (39.9%) at similar MDD.

## Data provenance & survivorship — measured, not assumed
- **Your folder's data starts 2005, not 2019**: `Nifty500_Master_Dataset_2005_2025.xlsx` = 5,363 trading days × 1,200 ticker columns from 2005-01-03 (377 names with data in 2005 → 770 in 2025). `raw/nifty500/` adds 239 delisted-stock files; membership files give point-in-time Nifty 500 composition (semi-annual snapshots Mar 2005–Sep 2025).
- **IPO lookahead: none** — names enter the panel at listing (DMART 2017-03, IRCTC 2019-10, PAYTM 2021-11, LICI 2022-05 ✓) and the universe only admits them after 200 trading days of history.
- **Big failures ARE included with full history**: UNITECH, RCOM, RPOWER, DHFL, JETAIRWAYS, YESBANK etc. have continuous data through their collapse/delisting. The gap is limited to 239 smaller names whose daily data exists only in sampled windows (2005-06, 2010-11, 2015-16, 2020-21).
- **Measured bias (Excel → "Survivorship Tests")**: running the breakout strategy inside those windows with the full universe vs survivors-only gives differences of +1.7 / −2.1 / +3.6 / +12.0 pp/yr — two-sided, because "dead" names include merged winners (HDFC, MINDTREE), not just failures. Net: **discount headline CAGRs by ~2–4pp/yr**; rankings and drawdown conclusions are unaffected.

## Files
- `Backtest_Results.xlsx` — summary, annual returns, sensitivity grids (S1+S4), survivorship tests, equity curves + chart, full rules, caveats
- `equity_curves/` — daily NAV series for all four strategies (CSV)
- `code/` — complete reproducible Python (data prep, engines, strategies, validation)
