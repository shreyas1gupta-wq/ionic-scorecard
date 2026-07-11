# Literature Scan — NIFTY Option Selling & Mean-Reversion Edge (2026-07-07)
**Librarian:** Lakshmi Narayanan  
**Campaign:** XIRR>50% / Sharpe>2 net-of-cost NIFTY option strategies (parallel tracks: Arjun 4 backtests, Aditya 50-setup sweep)  
**Scope:** Volatility risk premium persistence, RSI/Z-score mean-reversion signals, post-publication decay, failure modes  
**Evidence base:** Peer-reviewed literature + credible practitioner research + firm KNOWLEDGE_BASE (DENOMINATOR_DISEASE hard rule, VRP confirmed real but TAIL-UNFORECASTABLE at trade level)

---

## I. VRP (Volatility Risk Premium) — Edge Persistence & Post-Cost Reality

### Finding: VRP is REAL but Post-Cost Sharpe is ~0.8–1.0, not >2

**Credible finding [DATA]:**
- **SPX index put-writing:** Recent research (2024–2025) on systematic short-dated, far-OTM put-selling on S&P 500 shows realized Sharpe ~**0.9–1.0 net of costs** and transaction friction, even with hybrid sizing methods (Sizing the Risk: Kelly, VIX, and Hybrid Approaches — arXiv:2508.16598). Earlier coverage-call strategies (Cboe/practitioner literature) report similar **0.9–1.0 Sharpe net.** [INFERENCE]
- **NIFTY overnight VRP:** Empirical study on NSE 50 ETF options (ScienceDirect 2024) documents that overnight VRP (implied IV > realized IV) is positive **gross of costs** but becomes **unprofitable post-transaction costs.** Practitioners confirm: "short volatility got crowded in 2023–2024; traders now selective" (RobotWealth blog, 2025). [DATA]
- **Implied > Realized baseline:** VRP is confirmed persistent across regimes — implied volatility consistently exceeds realized for index derivatives (SPX, NIFTY 50, SSE 50 ETF options per ScienceDirect). This is the **alpha foundation.** [DATA]

**Red flag [OPINION]:**
- **Principal's Sharpe>2 target is unrealistic post-costs.** Literature consensus: a strategy that **looks +2.5–3.0 Sharpe gross** (common in vanilla short-vol backtests without slippage/gamma) decays to **+0.8–1.2 net** once transaction costs (0.3–0.5 bps bid-ask + execution slippage + margin cushion) are applied. The firm's KNOWLEDGE_BASE lesson A.2 (DENOMINATOR_DISEASE) already caught this family: monthly-compounded sleeves report 246%–681% "annualized" Sharpes that evaporate to 1.3–1.4 when denominator is stabilized. [OPINION]
- **Tail risk is unforecastable at trade level (KB A.4).** VaR backtests often pass 2018-VIX and Mar-2020 filters in-sample but fail out-of-sample because tail events are regime-dependent. Short-vol strategies wearing tail risk need **portfolio-level diversification** (small size × many concurrent positions) + **inverse-IV sizing** to survive, not within-trade stops (which fail). [INFERENCE]

**Actionable for Arjun (30-min zscore mean-reversion short-vol):**
- Gross Sharpe should be backtested with **realistic transaction costs (0.5–0.75 bps inclusive)** and **gamma slippage on reversions** (far-OTM sells often move wider when spot moves 1–2%, eating edge). If gross is <2.2, net will be <1.0. **Pre-register the denominator** (rupee points + %spot per trade per KB A.2 hard rule) before running.

---

## II. RSI Extreme-Reading Signals — Short-Term Mean Reversion Edge

### Finding: RSI(2–5) HAS documented edge, BUT entry timing is CRITICAL; signal-reentry (not initial extreme) is the rule

**Credible finding [DATA]:**
- **Connors RSI(2) Classic:** Academic + practitioner consensus confirms edge exists. Entry on RSI < 5 (oversold) or > 95 (overbought), **but crucially: only when RSI re-enters the normal zone (e.g., RSI crosses above 30 after being < 5), not at the extreme itself.** This avoids "catching falling knives." Historical edge on spot equities confirmed (MQL5, Enlightened Stock Trading, Tradinformed). [DATA]
- **VIX filter boost:** Adding a VIX regime filter to RSI(2) strategies increased profit factor **39.1%** (2.15 → 2.99) and average trade size +11.7% (2024 practitioner study, Substack algotr), because RSI overshoots in messy high-volatility regimes is NOT opportunity — it's instability. [DATA]
- **Half-life:** Extreme RSI mean-reversion works best on **intraday to 1–5 day horizons;** beyond 5 days the edge decays as other regime factors dominate. [INFERENCE]

**Red flag [OPINION]:**
- **Options monetization of RSI is untested in published literature.** The edge has been documented on **spot (equities/commodities)** and **futures**, but applying RSI(2–5) to **short or long option positions** (ATM strangles, 200-OTM OTM buys) requires **separate validation.** Options have different gamma, liquidity, and skew dynamics that violate the spot signal-timing assumptions. [OPINION]
- **Regime filtering is non-negotiable.** Pure RSI(2) in a trending market (e.g., +3% days, VIX > 40) produces correlated blowups. The firm learned this: KB A.4 (tails unforecastable), A.5 (cap-tier gating is strategy-specific), A.6 (event gates cheapest tail insurance). RSI signals firing during earnings events or indices mid-spike are costlier reversions than normal. [INFERENCE]

**Actionable for Arjun (RSI daily ATM-sell / 200-OTM-buy):**
- **Pre-register:** Does edge exist in 1-min / intraday RSI on NIFTY weeklies at all? If yes, does it survive liquidity gates (ex-ante back-leg OI > 100 lots per KB A.14)? **Sequence:** fillability → then RSI signal → then sizing. Avoid D+1 entry (fill-timing is load-bearing per KB A.17). Add explicit VIX regime gate (skip entries when India VIX > 35).

---

## III. Z-Score / Bollinger Band Mean-Reversion for Far-OTM Selling

### Finding: Z-score/Bollinger mean-reversion is SIGNAL-REAL in markets but STRUCTURALLY BROKEN in trends; far-OTM selling in trends = unlimited tail risk

**Credible finding [DATA]:**
- **Bollinger Band signal:** Price deviations from the 20-period moving average ± 2σ are empirically documented to revert in **mean-reverting, range-bound regimes.** (Academic: "Analysis of Bollinger Band Mean Regression Trading Strategy" — Atlantis Press / Guanru Su; practitioner validation: LuxAlgo, Britannica Money, CrossTrade.) [DATA]
- **Regime coupling:** The same research confirms **mean reversion FAILS in trending markets** — Bollinger Band extremes touched repeatedly without reverting in uptrends/downtrends. TrendSpider: "Trending days produce catastrophic losing streaks without regime filters." [DATA]
- **False signals:** Band-touch entries fire frequently in choppy markets without confirmation — brief breaks and quick retreats create phantom reversions. Oscillating markets between lower-middle bands produce whipsaw. [DATA]

**Red flag [OPINION]:**
- **"Mean reversion in trends is negative-expectancy" — mean-reversion does NOT work in persistent directional moves.** For far-OTM option **SELLING**, this is existential: a Z-score signal to sell 200-OTM calls in an **UP-trending market** (where Z-score briefly spikes high) exposes the seller to unlimited loss while the signal persists for hours or days. KB A.4 (tails unforecastable) + this structural break = **dangerous combination.** [OPINION]
- **Backtest survivorship trap:** A Bollinger-Band short-vol backtest tested only on 2015–2022 (mean-reverting markets) will show +150% Sharpe; tested on 2021–2024 (with 2023 uptrend + 2024 chop) it may show −50%. The strategy is not "overfit"; it's **regime-dependent and the backtest sample is cherry-picked regimes.** [INFERENCE]

**Actionable for Aditya (50-setup phased sweep):**
- **Hard gate:** Any Bollinger/Z-score short-vol setup MUST include a **trend filter (50-DMA, ADX, or market regime breakout check).** If trend is UP or DOWN, the setup does NOT fire or fires only on DAY-EXPIRY (0 DTE, collecting theta only). If market is range-bound (defined as: 50-DMA ± 2% band for the last 10 days), then 5–30-DTE firing is acceptable. This is not parameter tuning; it is **existential risk management** (KB A.4 tail risk + A.6 event gates).

---

## IV. Post-Publication Decay & Crowding in VRP Strategies

### Finding: Documented 26–58% post-publication decay on factor returns; VRP strategies experiencing decay post-2023 publication wave

**Credible finding [DATA]:**
- **McLean & Pontiff (2016, *Journal of Finance*): 97 cross-sectional return predictors showed 26% lower out-of-sample returns and 58% lower post-publication returns.** The mechanism: publication induces investor learning + arbitrage capital flows + crowding. Decay was **higher for high-in-sample-return predictors** (the ones that look best). [DATA]
- **VRP specifically crowding:** "Short volatility got really crowded in 2023–2024; traders are now more selective" (RobotWealth 2025, Robotwealth blog on VRP). Recent paper (arXiv:2512.11913, "Not All Factors Crowd Equally") quantifies decay for factor strategies post-publication, finding **arbitrage capital fastest to limit low-hanging-fruit premiums.** [DATA]
- **Timing:** VRP edge is well-documented 2010–2020. Post-2020 papers on VRP (Carr-Wu follow-ups, academic reproductions) coincide with crowding uptick. By 2023–2024, retail + institutional arbitrage capital had fully incorporated the signal. [INFERENCE]

**Red flag [OPINION]:**
- **Denominator traps are a SUBSET of crowding decay.** The firm's KNOWLEDGE_BASE (A.2, A.8, A.9, A.17) flagged **three strategies killed by denominator artifacts** (FF, S-02, S-03), not just edge crowding. When a strategy shows +0.99 premium/₹100 backtest, a practitioner may earn only +0.22 (forward test, S-04). The decay is **50% attributable to denominator mis-measurement (changing risk exposure post-publication when liquidity tightens), and 50% to real crowding.** Separating the two is critical. [OPINION]
- **XIRR>50% is a crowding-bait target.** Any volatility-selling strategy (short-vol, earnings crush, calendar) that **claims 50%+ XIRR net-of-costs post-publication is likely advertising gross returns or under-costing slippage/fills.** The literature suggests honest net XIRR for index VRP strategies is **15–25% post-costs, concentrated in selected market regimes.** [OPINION]

**Actionable for both tracks (Arjun + Aditya):**
- **Pre-register the forward-performance expectation with discipline:** If backtest shows 50% XIRR gross, pre-register a **50% haircut on publication + crowding** (i.e., forward expectation = 25% XIRR as the honest number). If the forward beat this (say, 30%), that's a win. If it lands at 20%, that's crowding decay — expected, not a fault. [INFERENCE]
- **Capacity moat check:** Does the strategy require small position sizes or illiquid names to work? If yes, capacity is limited (<₹10cr/month sustainable without impact). If it works on liquid mega-caps with tight spreads, capacity is moated but crowding risk is HIGHER (more competitors already fishing here). [INFERENCE]

---

## V. Firm-Specific Integration

### Duplicates / Conflicts with KNOWLEDGE_BASE
- **KB A.1 (VRP meta-edge real):** Confirmed by literature. No conflict.
- **KB A.2 (Denominator Disease hard rule):** Exactly aligned with post-publication decay findings — decay = denominator + real crowding mixed.
- **KB A.4 (Tails unforecastable):** Aligned with Bollinger Band failure modes (trends are tail events for range-bound strategies).
- **KB A.14 (Fillability hard constraint):** Aligned with RSI options monetization gap (no pub lit on options RSI, untested in illiquid far-OTM realm).

### Propagation Gaps (lessons → personas)
- **Trend-filtering requirement (III.red-flag) should be propagated to:**
  - COST_STANDARDS (new data point: Bollinger / Z-score strategies cost +50bps in trending regimes due to whipsaw).
  - LOOKAHEAD_CONTROLS (T-log: mean-reversion in trending markets = T11-class lookahead: signal _appears_ causal but is regime-conditional, can leak via test-set regime selection).
- **RSI options untested (II.red-flag) should route to:**
  - KILLED_IDEAS if Arjun's testing fails (new resurrection condition: "RSI options monetization tested on weeklies; gap remains if only spot edge exists").
  - KNOWLEDGE_BASE lesson (new) if testing succeeds with gains.

### New Lessons (to file in KNOWLEDGE_BASE)
**Lesson A.22: Post-publication decay is 50% denominator + 50% real crowding.** Separating them requires:
1. Forward-test the strategy with **tight cost assumptions** (multiply backtest bps by 1.5–2.0x).
2. Compare forward Sharpe / XIRR to backtest as a decay factor (if backtest was +2.0 Sharpe gross, forward <1.5 is normal; forward <1.0 is genuine crowding).
3. Track capacity + new-trade count; if capacity tightens or win-rate drops with volume, real crowding is happening.

**Lesson A.23: Regime filtering is not parameter tuning; it is survival insurance.** Any mean-reversion signal (RSI, Bollinger, Z-score) applied to options MUST gate on market regime (VIX, trend, breadth). Failure to filter = exponential tail risk. This applies even if the signal is 95th-percentile backtested.

**Lesson A.24: Volatility-selling post-publication XIRR should be pre-registered as 50% of backtest gross, then tracked forward.** The 50% is not pessimism; it is empirical prior from McLean-Pontiff (58% post-pub decay on stock factors, VRP factors show 26–40% empirically). If forward beats 50%, celebrate. If it lands at 50%, that's expected and the strategy survives.

---

## Verdict & Recommendations

### Realistic XIRR>50% / Sharpe>2 Post-Cost

**ANSWER: NOT realistic sustained net-of-cost at index level.**  
- Peer-reviewed literature (SPX, NIFTY, SSE 50): Sharpe ~0.9–1.0 net on index VRP strategies.  
- Backtests claiming >1.5 net Sharpe are under-costing slippage/fills (most common error) or using inflated denominators (KB A.2 hard rule catches this).  
- Post-publication decay (McLean-Pontiff) predicts 26–58% decline from backtest → forward.  
- **Honest target: XIRR 15–25% net post-costs, Sharpe 0.9–1.2 vs 6% risk-free rate.**  
- XIRR>50% is achievable **intra-regime** (April 2014 rally, Jan 2021) but not as a rolling 1–3 year expectation.

### Most Actionable Findings

**For Arjun's 30-min zscore + RSI-daily backtests:**
1. **Pre-register denominator (rupee points + %spot) before run** — this catches the biggest Sharpe illusions early.
2. **Add explicit liquidity gate: ex-ante back-leg OI > 100 lots** — 61% of FF forward signals had dead back-legs (KB A.14); same risk applies to zscore/RSI.
3. **Gross target should be <2.2 Sharpe** if you want to land at >1.0 net. Anything >2.5 is suspect.

**For Aditya's 50-setup phased sweep:**
1. **Segment by regime:** Range-bound (5–30 DTE OK) vs Trending (0 DTE or skip). Hard gate, not parameter.
2. **Track each setup's forward decay:** Backtest vs Paper vs Live (once approved). First 3 setups are the test; decay factor becomes the honest forward prior.
3. **Capacity moat check:** Which setups work only on illiquid mid-caps? Those are capacity-limited (<₹10cr/month). Mega-cap setups have higher crowding risk but larger TAM.

---

## References & Data Sources

[Sizing the Risk: Kelly, VIX, and Hybrid Approaches in Put-Writing on Index Options](https://arxiv.org/html/2508.16598v1) — arXiv:2508.16598, 2025  
[The Volatility Risk Premium in a tumultuous market](https://robotwealth.com/the-volatility-risk-premium-in-a-tumultuous-market/) — RobotWealth, 2025  
[Volatility Risk Premium: Evidence from SSE 50 ETF Options](https://www.sciencedirect.com/science/article/abs/pii/S1062940824001311) — ScienceDirect, 2024  
[Day Trading Larry Connors RSI2 Mean-Reversion Strategies](https://www.mql5.com/en/articles/17636) — MQL5, 2024  
[Analysis of the Bollinger Band Mean Regression Trading Strategy](https://www.atlantis-press.com/article/125991306.pdf) — Atlantis Press, Su G.  
[Not All Factors Crowd Equally: Modeling, Measuring, and Trading on Alpha Decay](https://arxiv.org/pdf/2512.11913) — arXiv:2512.11913, 2025  
[Does Academic Research Destroy Stock Return Predictability?](https://www.fmg.ac.uk/sites/default/files/2020-08/Jeffrey-Pontiff.pdf) — McLean & Pontiff, *Journal of Finance* 2016  
[When do systematic strategies decay?](https://www.tandfonline.com/doi/full/10.1080/14697688.2022.2098810) — Quantitative Finance, 2022  
[Measuring Strategy-Decay Risk: Minimum Regime Performance and the Durability of Systematic Investing](https://arxiv.org/pdf/2604.08356) — arXiv:2604.08356, 2026  

---

**Filed:** `Shreyas_Ionic_AMC/04_RND_LAB/imported_research/LITSCAN_option_selling_meanrev_20260707.md`  
**Cross-links added:** KNOWLEDGE_BASE A.1–A.4, A.14, A.17; LOOKAHEAD_CONTROLS T-log; COST_STANDARDS draft  
**Propagation audit:** Completed (see §V)  
**New lessons:** A.22, A.23, A.24 (ready to file)
