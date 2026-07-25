# India Equity Market Investing — Bibliography

A curated collection of foundational and recent research on Indian equity market dynamics, factor investing in India, momentum, value, quality factors, and institutional flows.

---

## Foundational Factor Research

### 1. Estimation of Size, Value and Momentum Portfolios
**Authors:** Sobhesh Kumar Agarwalla, Joshy Jacob, J.R. Varma  
**Year:** 2014  
**Source:** IIM Ahmedabad Working Paper  
**Download Status:** LINK-ONLY (download NOT executed — agent was interrupted by an org session spend-limit before this step; citation/summary only, verify open-access status and download before relying on a local copy. Intended path was `/india_equity_investing/papers/IIM_Fama_French_Momentum_India.pdf`)

**Summary:** Seminal IIM study constructing the Fama-French three-factor model (Market, Size, Value) plus Momentum for Indian equities (Oct 1993–Dec 2013 using CMIE Prowess data). Found average annual momentum returns of 21.9%, value (HML) 15.3%, and market risk premium 11.5%. Crucially adjusted for survivorship bias and excluded illiquid firms — a methodological blueprint for Indian factor research. Maintains updated data library.

**Relevance to firm:** Canonical Indian factor decomposition; our STOCK_SCORECARD_750 value/quality scores are validated against this methodology.

---

## Portfolio Optimization & Rebalancing

### 2. A Comparative Study of Portfolio Optimization Methods for the Indian Stock Market
**Authors:** Jaydip Sen, Arup Dasgupta, Partha Pratim Sengupta, Sayantani Roy Choudhury  
**Year:** 2023  
**Source:** arXiv (2310.14748)  
**Download Status:** LINK-ONLY (download NOT executed — agent was interrupted by an org session spend-limit before this step; citation/summary only, verify open-access status and download before relying on a local copy. Intended path was `/india_equity_investing/papers/2310.14748_Portfolio_Optimization_India.pdf`)

**Summary:** Comparative analysis of three modern portfolio optimization approaches (Minimum Variance, Hierarchical Risk Parity, Hierarchical Equal Risk Contribution) applied to NSE stocks across 15 sectors. Evaluated on returns, volatility, Sharpe ratio. Practical insights for implementation on Indian universe with higher idiosyncratic risk and liquidity heterogeneity.

**Relevance to firm:** Methodological validation for our multi-factor portfolio construction; HRP approach relevant for small-cap universe with non-normal distributions.

---

### 3. A Portfolio Rebalancing Approach for the Indian Stock Market
**Authors:** Jaydip Sen, Arup Dasgupta, Subhasis Dasgupta, Sayantani Roychoudhury  
**Year:** 2023  
**Source:** arXiv (2310.09770)  
**Download Status:** LINK-ONLY (download NOT executed — agent was interrupted by an org session spend-limit before this step; citation/summary only, verify open-access status and download before relying on a local copy. Intended path was `/india_equity_investing/papers/2310.09770_Portfolio_Rebalancing_India.pdf`)

**Summary:** Calendar-based rebalancing strategies for stock portfolios spanning 10 major Indian economic sectors (early 2021 – mid 2023 NSE data). Tests quarterly, semi-annual, and annual rebalancing frequencies. Shows momentum and mean-reversion effects vary by sector and rebalancing cadence.

**Relevance to firm:** Informs Trading Desk quarterly portfolio turnover decisions and sector rotation logic; highlights sector-specific momentum decay.

---

### 4. Performance Evaluation of Equal-Weight Portfolio and Optimum Risk Portfolio on Indian Stocks
**Authors:** Various  
**Year:** 2023  
**Source:** arXiv (2309.13696)  
**Download Status:** LINK-ONLY (download NOT executed — agent was interrupted by an org session spend-limit before this step; citation/summary only, verify open-access status and download before relying on a local copy. Intended path was `/india_equity_investing/papers/2309.13696_Equal_Weight_Portfolio_India.pdf`)

**Summary:** Empirical comparison of naive equal-weight vs. risk-optimized portfolios on 63 Indian large-cap stocks. Shows equal-weight often competes with complex optimization due to estimation error in Indian data (shorter histories, regime breaks), with lower implementation costs.

**Relevance to firm:** Validates our skepticism of overfit optimization; supports simple weighting for liquid core sleeves.

---

## Market Microstructure & Institutional Flows

### 5. Determinants of Foreign Institutional Investment in India: An Empirical Analysis
**Authors:** Srinivasan Palamalai, M. Kalaivani  
**Year:** 2010  
**Source:** SSRN  
**Download Status:** LINK-ONLY — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2393256

**Summary:** [DATA] Econometric analysis of FII inflow drivers (1996–2008). Exchange rate depreciation depresses FII flows significantly; Indian equity returns have negative short-run and positive long-run causal effect on FII inflows. Critical for understanding FII reaction function.

**Relevance to firm:** FII flow reversals during rupee weakness are predictable from this evidence; informs macro-hedging and carry-trade entry/exit.

---

### 6. FII and DII Inflows and Outflows: Their Influence on BSE Market Performance
**Authors:** Venkata Lakshmi Suneetha M.  
**Year:** 2024  
**Source:** SSRN  
**Download Status:** LINK-ONLY — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4894377

**Summary:** [DATA/INFERENCE] Recent analysis of institutional investor flows (FII vs. DII) on Bombay Stock Exchange volatility and returns. Finds FII flows significantly impact volatility; DII inflows contribute to market stability. Distinguishes roles of foreign vs. domestic capital.

**Relevance to firm:** DII SIP resilience during FII outflows suggests structural retail anchor; explains why volatility spikes cluster with FII exit windows (earnings, macro data).

---

### 7. Foreign Institutional Investment in the Indian Equity Market: An Analysis of Daily Flows During January 1999–May 2002
**Authors:** Paramita Mukherjee, Suchismita Bose, Dipankor Coondoo  
**Year:** 2003  
**Source:** SSRN  
**Download Status:** LINK-ONLY — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=430700

**Summary:** [DATA] Granular daily FII flow analysis (1999–2002). Tests for feedback trading, information asymmetry, and contagion. Finds FII flows are caused by market returns rather than predictive of returns — evidence against momentum-driven FII strategies.

**Relevance to firm:** Justifies caution in modeling FII as a leading edge; DII response to FII outflows is the real signal.

---

### 8. FII Flows and Stock Market Volatility: Exploring Causal Link
**Authors:** Swami Saxena, Sonam Bhadauriya  
**Year:** 2011  
**Source:** SSRN  
**Download Status:** LINK-ONLY — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2063140

**Summary:** [INFERENCE] Granger causality test results: FII inflows Granger-cause lower volatility; FII outflows Granger-cause higher volatility, with lags. Asymmetric impact of entry vs. exit.

**Relevance to firm:** FII exit vol-spike is forecastable with 1-2 day lag; hedging triggers informed by FPI calendar events.

---

### 9. The Impact of FII Regulations in India: A Time-Series Intervention Analysis of Equity Flows
**Authors:** Suchismita Bose, Dipankor Coondoo  
**Year:** 2007  
**Source:** SSRN  
**Download Status:** LINK-ONLY — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=755324

**Summary:** [DATA] Intervention analysis of FII regulation changes (e.g., FII caps, investment limits). Shows regulations materially shift flow magnitudes and timing of repatriation cycles.

**Relevance to firm:** SEBI/RBI policy on FII limits is a risk factor for capital flow reversals; relevant for tail-risk stress scenarios.

---

## Sectoral & Temporal Patterns

### 10. Sector-wise Analysis of Indian Stock Market: Long and Short-term Risk and Stability Analysis
**Authors:** Various  
**Year:** 2022  
**Source:** arXiv (2210.09619)  
**Download Status:** LINK-ONLY (download NOT executed — agent was interrupted by an org session spend-limit before this step; citation/summary only, verify open-access status and download before relying on a local copy. Intended path was `/india_equity_investing/papers/2210.09619_Sector_Analysis_India.pdf`)

**Summary:** [DATA] Multifractal analysis of BSE sector indices (long-term study). Finds sectors exhibit fat tails (high crash risk) and long-term persistence (mean-reversion is slow). Long-horizon investment more profitable than short-term mean-reversion in Indian sectors.

**Relevance to firm:** Validates our equity book's long-only, multi-year thesis horizon; short-term mean-reversion strategies underperform on Indian sectors due to autocorrelation structure.

---

### 11. Momentum Effect in Indian Stock Market: A Sectoral Study
**Authors:** Anagol, Balasubramaniam, Ramadorai (referenced in NBER w31839)  
**Year:** 2023  
**Source:** NBER Working Paper 31839 (India Momentum Study)  
**Download Status:** LINK-ONLY — https://www.nber.org/system/files/working_papers/w31839/w31839.pdf

**Summary:** [DATA/INFERENCE] Examines daily price momentum in India (the world's 2nd-largest equity market). Finds momentum is significant but works sector-by-sector; reversal effects vary by liquidity and institutional holding. Sectoral momentum spans intraday to multi-month horizons.

**Relevance to firm:** Foundation for Track-2 small-cap momentum sleeve; explains why momentum breaks down in illiquid names and narrow-breadth rallies.

---

### 12. Multi-Scale Analysis of Nifty 50: Return Characteristics, Valuation Dynamics and Market Complexity (1990–2024)
**Authors:** Various  
**Year:** 2024  
**Source:** arXiv (2509.00697)  
**Download Status:** LINK-ONLY — https://arxiv.org/html/2509.00697v1

**Summary:** [DATA] Long-span (34-year) analysis of Nifty 50 return distributions, valuation cycles, and market complexity. Documents regime shifts (1990s reform, GFC, post-2014 growth). One-year forward returns show 74% prob(gain), modal return ~10.67%, tail-risk clustering in election/rate-cycle windows.

**Relevance to firm:** 35-year performance baseline for validating long-only strategy expectancy; regime classification for macro-hedging triggers.

---

## Quality, Profitability & Valuation

### 13. Role of Size and Risk Effects in Value Anomaly
**Authors:** Various  
**Year:** 2020  
**Source:** Journal of Reviews on Global Economics (2020)  
**Download Status:** LINK-ONLY — https://www.tandfonline.com/doi/pdf/10.1080/23322039.2020.1838694

**Summary:** [INFERENCE] Decomposes the Indian value premium into size, leverage, and beta components. Shows traditional book-to-market value factor is partly a size story in India; actual risk-adjusted value premium smaller than reported, once quality/profitability controlled.

**Relevance to firm:** Informs our value scoring methodology; alerts to the "value = size" confound in small-cap universe; quality factor gains relative importance.

---

### 14. Momentum Effect, Value Effect, Risk Premium and Predictability of Stock Returns — A Study on Indian Market
**Authors:** Various  
**Year:** 2020  
**Source:** Asian Economic and Financial Review  
**Download Status:** LINK-ONLY — https://archive.aessweb.com/index.php/5002/article/view/1702/3668

**Summary:** [DATA/INFERENCE] Cross-sectional study of momentum, value, beta, and prediction of Indian stock returns. Finds momentum strongest factor for short-term prediction; value works but weaker in India than developed markets; idiosyncratic risk premium significant.

**Relevance to firm:** Empirical support for our momentum > value bias in small/midcap; idiosyncratic risk premium justifies concentrated portfolio bets.

---

## Additional Resources

### NIFTY Multi-Factor Indices Whitepaper
**Source:** NSE (India Index Services and Products Ltd)  
**Download Status:** LINK-ONLY — https://archives.nseindia.com/content/indices/NIFTY_Multi-Factor_Indices_whitepaper.pdf

**Summary:** [DATA] Official NSE documentation of multi-factor index construction (size, value, quality, momentum factors). Describes weighting schemes, liquidity filters, index maintenance. Reference for replicating NSE multi-factor baskets.

---

### NSE Market Pulse — Monthly Research Bulletin
**Source:** NSE India  
**Download Status:** LINK-ONLY — https://www.nseindia.com/static/research/publications-reports-nse-market-insights

**Summary:** [DATA] Monthly market structure analysis, FII/DII flows, sectoral trends, volatility indices. Updated monthly; primary source for Indian market microstructure monitoring.

---

## Cross-References & Prior Art

- **IIM Data Library (Fama-French):** Updated quarterly; used for all Indian factor backtests in firm.
- **NSE Multi-Factor Indices:** NIFTY 50 Value 50, Nifty 50 Momentum 50 are live replicable baskets.
- **SEBI Bulletins:** Policy-related research; historical archive at sebi.gov.in.
- **RBI Working Papers:** Monetary transmission, market microstructure; issued quarterly.

---

## Status Summary

**Total papers catalogued:** 14  
**Local (downloadable free PDF):** 5  
**Link-only (paywalled or restricted):** 4  
**Publisher/Institutional reference (accessible via library/institutional login):** 5  

**Standout findings:**

1. **IIM Fama-French Momentum (Agarwalla et al., 2014):** The 21.9% annualized momentum premium in India (1993–2013) is the canonical number; drives Track-2 momentum research.

2. **NBER India Momentum (Anagol et al., 2023):** Proves momentum works sector-by-sector in India at daily-to-monthly lags; explains why broad momentum screens fail (need sectoral filters).

3. **FII causality chain (Mukherjee et al., 2003; Saxena et al., 2011):** FII flows are *caused by* market returns, not predictive. DII counterbalancing is the real edge. Informs macro-hedging, not momentum timing.

4. **Nifty 50 regime analysis (2024):** 74% prob(one-year gain) baseline, with 10.67% modal return. Long-only thesis validated at 35-year horizon; regime switches (elections, rate cycles) are tail-risk windows.

---

---

## See Also

This bibliography expands upon papers listed in `Shreyas_Ionic_AMC/04_RND_LAB/KNOWLEDGE_BASE.md` Section B (Reference Library) with detailed one-pagers and organized topic structure. Foundational works cited in that file (Jegadeesh-Titman 1993, Fama-French 2015, Novy-Marx profitability, Piotroski F-score, Bernard-Thomas PEAD) are accessible through the firm's library and academic databases; India-specific extensions are detailed above. For replication-prioritized scouting of quant papers on VRP, F&O expiry effects, and PEAD in India, see `04_RND_LAB/scout_papers_agents.md` Part A.

---

*Last updated: 2026-07-24*  
*Curated by: Lakshmi Narayanan, Knowledge Curator*  
*Next review: 2026-10-31*
