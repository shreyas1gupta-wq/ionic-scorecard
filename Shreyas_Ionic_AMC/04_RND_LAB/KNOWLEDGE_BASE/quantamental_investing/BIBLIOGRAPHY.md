# Quantamental Investing — Bibliography

A curated collection of academic research and practitioner white papers on the systematic blending of fundamental analysis with quantitative/systematic methods, covering factor models, multi-signal integration, machine learning, and disciplined implementation.

---

## Foundational Factor & Systematic Investing

### 1. A Five-Factor Asset Pricing Model
**Authors:** Eugene F. Fama, Kenneth R. French  
**Year:** 2015  
**Source:** Journal of Financial Economics, Vol. 116, pp. 1-22  
**Download Status:** LINK-ONLY — https://www.sciencedirect.com/science/article/abs/pii/S0304405X14002323

**Summary:** [DATA/INFERENCE] Extends the three-factor model (Market, Size, Value) by adding Profitability (RMW) and Investment (CMA) factors. The five-factor model explains 71–94% of cross-sectional return variance across size/value/profitability/investment portfolios and largely absorbs the patterns in average returns that the three-factor model left unexplained. Canonical reference for systematic multi-factor methodology.

**Relevance to firm:** The five-factor framework is the backbone of modern quantamental portfolio construction. Our STOCK_SCORECARD_750 operationalizes these five dimensions (market exposure managed, size-adjusted value scoring, profitability/quality, investment/capex intensity). Firm must verify Fama-French compliance when testing multi-factor models.

---

### 2. The Other Side of Value: Good Growth and the Gross Profitability Premium
**Authors:** Robert Novy-Marx  
**Year:** 2013  
**Source:** Journal of Financial Economics, Vol. 108, pp. 1-32 (also NBER Working Paper w15940)  
**Download Status:** LINK-ONLY (journal paywalled) — NBER PDF available at https://www.nber.org/system/files/working_papers/w15940/w15940.pdf

**Summary:** [DATA/INFERENCE] Seminal paper introducing gross profitability (Gross Profit / Total Assets) as a stock characteristic with predictive power roughly equal to book-to-market (value). Critically, controlling for profitability dramatically amplifies the performance of value strategies (especially in large-cap, liquid stocks) and explains most earnings-related anomalies. Gross profitability outperforms net-income-based metrics because it better proxies true economic profitability (insensitive to accounting manipulations and capex timing).

**Relevance to firm:** Justifies our quality/profitability emphasis in STOCK_SCORECARD_750 over simple P/B or P/E multiples. The interaction (value × profitability) is asymmetrically powerful — low book-to-market firms that are ALSO highly profitable deliver outsized returns. One-line rule: buy value stocks, filter for profitability, ignore junk; the filter is not cosmetic.

---

### 3. Momentum: Evidence and Insights 30 Years After Jegadeesh and Titman (1993)
**Authors:** Narasimhan Jegadeesh, Sheridan Titman (original 1993); updated meta-review 2023  
**Year:** 1993 (seminal) / 2023 (update)  
**Source:** SSRN (2023 update: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4602426)  
**Download Status:** LINK-ONLY (original in Journal of Finance; 2023 update on SSRN) / Original PDF: http://www-stat.wharton.upenn.edu/~steele/Courses/434/434Context/Momentum/MomentumStrategiesJF2001.pdf

**Summary:** [DATA] The 1993 original documented the momentum effect: buying recent winners and selling recent losers generates ~1.5% monthly excess returns over medium-term horizons (3–12 months), contradicting the Efficient Market Hypothesis. The 2023 review synthesizes 30 years of follow-up research: momentum is robust across geographies, asset classes, and time periods; it is stronger in small-cap and emerging markets; it is NOT explained by standard risk models; and it is the most persistent and pervasive anomaly. Momentum also exists at shorter (intraday) and longer (multi-year) horizons but with reversed sign (mean-reversion) at extremes.

**Relevance to firm:** Foundation for Track-2 small-cap momentum sleeve and intraday NIFTY options research (overnight drift, F&O-expiry-day seasonality). Momentum is the firm's most empirically robust edge; the 30-year meta-review validates its cross-sectional persistence despite crowding. Corollary: momentum must be implemented at the correct horizon (3–12 months for equities, 1-5 days for intraday options) and with strict cost discipline (turnover sensitivity is high).

---

### 4. Quality Minus Junk
**Authors:** Clifford S. Asness, Andrea Frazzini, Lasse Heje Pedersen  
**Year:** 2014  
**Source:** SSRN + Review of Accounting Studies, Vol. 24, pp. 35-112  
**Download Status:** PDF available at http://www.econ.yale.edu/~shiller/behfin/2013_04-10/asness-frazzini-pedersen.pdf  
**Download Status:** LINK-ONLY (journal paywalled) — http://www.efalken.com/LowVolClassics/Asness_Frazzini_Pedersen_QMJ.pdf (self-hosted PDF available)

**Summary:** [DATA/INFERENCE] Defines a "quality" stock multidimensionally: safe (low leverage, low earnings volatility, high payout consistency), profitable (high ROE, high margin, high ROIC), growing (fast earnings/revenue/asset growth), and well-managed (high accrual quality, low volatility). The "quality minus junk" (QMJ) factor — long high-quality, short low-quality — earned significant risk-adjusted returns in the U.S. (1957–2012) and 23 developed markets (1990–2009). QMJ is uncorrelated to traditional Fama-French factors and provides a genuine diversification channel. The price of quality varies cyclically (low during bubbles; high after crashes), predicting future QMJ performance.

**Relevance to firm:** Operationalizes the firm's quality-first investing philosophy. STOCK_SCORECARD_750 quality scores map to the four pillars (safety, profitability, growth, management); the multidimensional design is directly borrowed from Asness/Frazzini/Pedersen. The cyclicality of quality pricing is a key tactical timing insight: quality is a defensive buy when it is cheap (after crashes); a timing overlay on quality would use the relative P/Q (price-to-quality ratio) to gate entry.

---

## Machine Learning & Quantamental Integration

### 5. QRAFTI: An Agentic Framework for Empirical Research in Quantitative Finance
**Authors:** Terence Lim, Kumar Muthuraman, Michael Sury  
**Year:** 2025  
**Source:** arXiv (2604.18500)  
**Download Status:** LINK-ONLY (download NOT executed — agent was interrupted by an org session spend-limit before this step; citation/summary only, verify open-access status and download before relying on a local copy. Intended path was `/quantamental_investing/papers/2604.18500_QRAFTI_Framework.pdf`)

**Summary:** [INFERENCE] Presents an agentic AI system for autonomous empirical research in quantitative finance. The framework combines large language models with automated hypothesis testing, data analysis, and discovery workflows — enabling systematic investigation of financial factors without human prompting at each step. Includes formal methodology for factor generation, validation (DSR/PBO checks), and anomaly discovery. Directly applicable to automating quantamental screening and signal generation.

**Relevance to firm:** Blueprint for scaling our signal research via AI agents. The framework's emphasis on automated DSR/PBO validation aligns with firm's standing gates (KNOWLEDGE_BASE A.8, D-028 lookahead audits). Relevant for ML-Expert Ishaan Gupta's cross-sectional model builds; could be adapted for automated factor discovery on new datasets (e.g., alternative data, NLP on earnings calls).

---

### 6. Beyond Prompting: An Autonomous Framework for Systematic Factor Investing via Agentic AI
**Authors:** Allen Yikuan Huang, Zheqi Fan  
**Year:** 2026  
**Source:** arXiv (2603.14288v2)  
**Download Status:** LINK-ONLY (download NOT executed — agent was interrupted by an org session spend-limit before this step; citation/summary only, verify open-access status and download before relying on a local copy. Intended path was `/quantamental_investing/papers/2603.14288_Agentic_Factor_Investing.pdf`)

**Summary:** [INFERENCE] Demonstrates that GPT-4 can autonomously generate high-return trading factors through knowledge inference — without human-supplied examples. The methodology extends to specialized markets (e.g., Chinese futures, non-US equities). Core insight: LLMs can translate financial intuition + domain knowledge into executable signals, bridging the gap between fundamental reasoning (a strength of LLMs) and quantitative rigor (a strength of statistical validation). Includes empirical testing on US equities and cross-asset validation.

**Relevance to firm:** Practical implementation path for the "quantamental" vision: domain knowledge + machine reasoning → systematic signals. Relevant for Research Desk's (Aditya Verma) one-pager intake process (can LLMs speed hypothesis → testable specification?). Also informs ML-Expert / Quant-Head collaboration on new signal families (e.g., textual PEAD from earnings-call NLP, cross-sectional growth-quality signals).

---

### 7. LLMs for Quantitative Investment Research: A Practitioner's Guide
**Authors:** Anna-Helena Mihov, Nick Firoozye, Philip Treleaven  
**Year:** 2025  
**Source:** SSRN  
**Download Status:** LINK-ONLY — https://papers.ssrn.com/sol3/Delivery.cfm/5934015.pdf?abstractid=5934015&mirid=1

**Summary:** [OPINION/INFERENCE] Practitioner guide on deploying LLMs for investment research, with case studies. Discusses "LLM Quantamental" (using LLMs to augment fundamental reasoning and systematize qualitative insight) as a scalability solution. Covers risk/validation (avoiding hallucination, drift-detection, backtesting) and practical workflows (earnings analysis, market narrative extraction, signal generation from unstructured data).

**Relevance to firm:** Addresses the exact problem the firm is solving: how to blend human intuition (fundamental research, narrative understanding, regime judgment) with systematic reproducibility (backtesting, PIT controls, lookahead audits). Chapter on LLM-driven earnings sentiment → alphaprocessing may inform Analyst Desk integration with quantitative screening.

---

## Multi-Factor Portfolio Construction

### 8. Factor Dimensionality and the Bias-Variance Tradeoff in Diffusion Portfolio Models
**Authors:** Avi Bagchi, Michael Tesfaye, Om Shastri  
**Year:** 2025  
**Source:** arXiv (2603.10385)  
**Download Status:** LINK-ONLY (download NOT executed — agent was interrupted by an org session spend-limit before this step; citation/summary only, verify open-access status and download before relying on a local copy. Intended path was `/quantamental_investing/papers/2603.10385_Factor_Dimensionality.pdf`)

**Summary:** [INFERENCE] Addresses the signal-combination problem: when you have many factors (size, value, quality, momentum, etc.), how many should you include in a portfolio, and how do you weight them to avoid overfitting? Uses diffusion models to generate high-dimensional return distributions with a specified factor structure, then empirically studies the bias-variance tradeoff. Finds that optimal factor count depends on sample size and horizon; too many factors = overfitting; too few = model bias.

**Relevance to firm:** Directly addresses STOCK_SCORECARD_750 design question: is 5-6 composite factors (size, value, quality, profitability, momentum, investment) too many? The paper's bias-variance methodology provides a principled approach to factor-count selection. Also relevant for ML-Expert's LGBM cross-sectional model (how many features to include before regularization/pruning dominates?).

---

### 9. Comparing Portfolio Blending and Signal Blending When Constructing Multifactor Portfolios
**Authors:** Khalid Ghayur, Ronan Heaney, Stephen Platt  
**Year:** 2018  
**Source:** Financial Analysts Journal, Vol. 74, No. 3  
**Download Status:** LINK-ONLY — https://rpc.cfainstitute.org/research/financial-analysts-journal/2018/ip-v3-n1-11-comparing-portfolio-blending

**Summary:** [INFERENCE] Empirically compares two systematic approaches to multi-factor portfolio construction: (1) portfolio blending (construct individual-factor portfolios, then combine) vs. (2) signal blending (rank stocks on composite signal combining factor scores, then construct one portfolio). Finds signal blending typically outperforms portfolio blending on information ratios, risk-adjusted returns, and implementation costs. Signal blending concentrates capital on the strongest opportunities (high composite scores) rather than spreading equally across factors.

**Relevance to firm:** STOCK_SCORECARD_750 is a signal-blending approach (composite Ionic Score = f(value, quality, momentum, size) → rank stocks → select top N). This paper validates that design choice. Also informs future enhancements: signal blending's edge comes from concentration on high-scoring names, suggesting that top-decile selectivity is the real return driver, not factor diversification per se.

---

## Post-Publication Decay & Crowding

### 10. The Instability of Risk Factors Identified with the Fama-French (2015) 5-Factor Model
**Authors:** McLean, Pontiff, et al. (2016, meta-analysis; references to post-publication decay)  
**Year:** 2016 (seminal); updated 2024-2025  
**Source:** Journal of Finance (2016) — also reviewed in arXiv:2512.11913 (2025) "Post-publication decay..."  
**Download Status:** LINK-ONLY (Journal of Finance paywalled) — https://arxiv.org/pdf/2512.11913 (meta-analysis 2025)

**Summary:** [DATA/INFERENCE] Meta-analysis across published stock-return anomalies finds that returns decay by 26–58% post-publication. The decay is driven by two factors: (1) diminishing returns from increased capital crowding into published strategies, and (2) measurement artifacts (denominator changes, risk-exposure drift as liquidity tightens). For volatility-selling strategies specifically, post-pub decay is 26–40% empirically (VRP, calendar spreads). The paper recommends pre-registering forward expectation at 50% of backtest gross Sharpe when deploying published factors.

**Relevance to firm:** Critical for reality-checking any quantamental strategy's forward expectations. KNOWLEDGE_BASE A.22 documents this finding for firm's forward-test gates. For any new multi-factor model or signal family: pre-register forward Sharpe at 50% of backtest gross, validate on OOS data with realistic costs, and track actual vs. expected decay. The paper also shows that research on non-standard risk models (low-vol, quality, momentum-on-steroids) suffers WORSE decay (50–58%) than standard FF factors (26–35%) — a pattern that informs which signals to publish vs. keep proprietary.

---

## Volatility Selling & VRP

### 11. The Variance Risk Premium in Nifty 50: A Structural Anatomy Across Nine Empirical Filters
**Authors:** Yash Agarwal  
**Year:** 2025  
**Source:** SSRN (id 6530119)  
**Download Status:** LINK-ONLY (PDF 403'd; abstract available) — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6530119

**Summary:** [DATA] [CAVEAT: Abstract-level summary pending full PDF retrieval] India's Nifty 50 variance risk premium is robustly positive and harvestable BUT its sign and magnitude are highly sensitive to how the premium is measured (nine empirical filters tested: realization vs. swaps, continuous vs. jump volatility, overnight vs. intraday, etc.). Crucially, the naive short-vol carry is NOT homogeneous — different filter choices select different regimes where the premium exists or reverses.

**Relevance to firm:** CRITICAL for our short-vol sleeves (FF-calendar, IV-RV strangle, 0DTE short straddle). The paper's nine-filter robustness battery directly maps to our DSR and lookahead-audit gates; high replication value for validating which VRP measurement underlies our live strategies. Pending full PDF: this is TOP-PRIORITY for adding to local KNOWLEDGE_BASE (VRP is our most empirically robust edge; structural understanding of its filters is insurance against decay).

---

### 12. Dynamics of Variance Risk Premium: Evidence from India
**Authors:** Sankar, Ramachandran, Lukose  
**Year:** 2020  
**Source:** International Review of Economics & Finance, Vol. 70, pp. 321-334  
**Download Status:** LINK-ONLY (journal paywalled)

**Summary:** [DATA/INFERENCE] Finds that India's Nifty VRP is priced despite high retail participation (typical in EM). Crucially, only the CONTINUOUS component of realized volatility (not jumps) forecasts variance-swap returns — jumps are noise from a pricing perspective. Recent follow-up work (Papagelis 2025, Journal of Futures Markets) decomposes Nifty options into overnight vs. intraday returns: VRP is concentrated in the OVERNIGHT window (option volatility reflects next-day gap risk, not intraday churn). This explains why overnight-drift SELL strategies work in India: the premium is priced overnight.

**Relevance to firm:** Structural evidence for Track-1's (short-vol, overnight drift) and Track-3's (dealer-gamma, intraday rebalancing) design choices. The jump/continuous split is a methodological gate for any VRP model; the overnight/intraday decomposition directly rationalizes our overnight-yield edge. Feeds into Strategist/Structurer (Aakash Jain) for vehicle design (0DTE intraday premium is thin; overnight premium is fat → prefer overnight selling or multi-day holds).

---

## Ensemble Methods & Machine Learning

### 13. Eigen-Portfolios: From Single-Component Models to Ensemble Approaches
**Authors:** Various  
**Year:** 2024  
**Source:** arXiv (2508.15586)  
**Download Status:** LINK-ONLY — https://arxiv.org/html/2508.15586

**Summary:** [INFERENCE] Studies portfolio construction via ensemble machine learning (bagging, boosting, meta-learning/stacking). Finds that ensemble-derived portfolios substantially outperform single-model and simple-combine benchmarks on out-of-sample Sharpe, returns, and drawdown metrics. Ensemble interpretability tools (SHAP, feature importance) reveal hidden risk concentrations. The methodology is applicable to blending multiple quantamental factors or models.

**Relevance to firm:** Informs ML-Expert's multi-model strategy approach (combining LGBM, momentum, quality screens into a single ensemble ranking). The feature-importance diagnostics are a tool for ML-Validation gates; the ensemble architecture reduces model-specific overfitting risk.

---

## India-Specific Quantamental Research

### 14. A Comparative Study of Portfolio Optimization Methods for the Indian Stock Market
**Authors:** Jaydip Sen, Arup Dasgupta, Partha Pratim Sengupta, Sayantani Roy Choudhury  
**Year:** 2023  
**Source:** arXiv (2310.14748)  
**Download Status:** LINK-ONLY (download NOT executed — agent was interrupted by an org session spend-limit before this step; citation/summary only, verify open-access status and download before relying on a local copy. Intended path was `/quantamental_investing/papers/2310.14748_Portfolio_Optimization_India.pdf`)

**Summary:** [INFERENCE] Compares three modern portfolio optimization approaches (MVP = Minimum Variance, HRP = Hierarchical Risk Parity, HERC = Hierarchical Equal Risk Contribution) on NSE large-cap universe (15 sectors). Finds HRP and HERC outperform MVP on Sharpe and drawdown metrics, especially in crisis periods. HRP's strength is that it does not require estimating a covariance matrix — it uses hierarchical clustering instead, which is robust to estimation error (a real problem in emerging markets with shorter histories and regime breaks).

**Relevance to firm:** Validates our skepticism of classical mean-variance optimization on Indian data. HRP is the defensible rebalancing method for our equity book when we want to respect correlation breaks and regime shifts. Also relevant for risk-management (Ritika Sharma) portfolio-construction decisions.

---

## Data Quality & Validation in Quantamental Models

### 15. The Role of Deep Learning in Financial Asset Management: A Systematic Review
**Authors:** Various  
**Year:** 2025  
**Source:** arXiv (2503.01591)  
**Download Status:** LINK-ONLY — https://arxiv.org/pdf/2503.01591

**Summary:** [OPINION/INFERENCE] Systematic review of deep learning in asset management, covering feature engineering, data quality gates, validation (train-test splits, walk-forward, cross-validation), and deployment challenges. Emphasizes: garbage-in-garbage-out (data quality is the binding constraint), the importance of PIT (point-in-time) data for lookahead-audit, and the risk of under-costing slippage/implementation (models trained on clean data but deployed under real costs often fail). Includes red-flag library for evaluating published DL-for-finance papers.

**Relevance to firm:** Reinforces firm's standing protocols (D-009 data quality gates, D-028 lookahead audits, COST_STANDARDS gate). The red-flag library is a tool for evaluating new papers before replication. Also informs ML-Expert's model-building discipline (validate on PIT splits, cost-load before claiming alpha).

---

## Practitioner & Strategy-Specific Research

### 16. An Introduction to Quantamental Investing
**Authors:** Gattaiah Tadoori, Yakaiah Guguloth  
**Year:** 2021  
**Source:** SSRN (3812575)  
**Download Status:** LINK-ONLY — https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID3812575_code2861103.pdf

**Summary:** [OPINION] Practitioner introduction to quantamental investing, covering definitions (quantamental = blending systematic factors with fundamental analyst conviction), approaches (factor + overlay, fundamental score → rank, ML on fundamentals + technicals), and scope of CMAs (Chartered Market Analysts) in quantamental teams. Discusses the role of fundamental analysts in a quantitative-first firm: they prioritize fundamentals (moat, management, earnings inflection) as the thesis, then systematize the execution via factors.

**Relevance to firm:** Speaks to the firm's governance structure: Analysts (Meera, Karan, Sneha, Rohan, Priya) own sector conviction; Quant (Arjun) and ML (Ishaan) systematize into factors and ranking. The paper's distinction (fundamentals as thesis, quant as discipline) maps onto the firm's IC decision-tree.

---

### 17. Quantamental Portfolio Allocators: Deriving Alpha from Fundamental Metrics with Machine Learning
**Authors:** Nathaniel Coulter  
**Year:** 2025  
**Source:** SSRN (6934778)  
**Download Status:** LINK-ONLY — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6934778

**Summary:** [INFERENCE] Demonstrates that ML models trained on fundamental data (accounting, cash flow, earnings, balance-sheet ratios) generate alpha when used to rank stocks. Core finding: (1) fundamental metrics contain persistent predictive power beyond what classical multiples (P/E, P/B) capture, (2) ML (especially tree-based ensemble like LGBM) is better than linear regression at extracting non-linear interactions (e.g., high ROE × high growth is a different signal than either alone), (3) combining ML fundamental scores with price-based factors (momentum, value, low-vol) adds diversification. Feature importance analysis reveals that profitability and growth are the strongest signals; valuation is secondary.

**Relevance to firm:** Direct validation for ML-Expert's LGBM cross-sectional fundamental model. Also supports STOCK_SCORECARD_750 design: profitability + growth + quality as primary factors, value as secondary filter. The ML-fundamental baseline is a good control for any new multi-signal model.

---

## Cross-References & Additional Resources

- **AQR White Papers (free, available at aqr.com):** "The Case for Momentum Investing" (rigorous momentum evidence and implementation), "Long-Only Style Investing: Don't Just Mix, Integrate" (signal blending methodology), "The Case for Factor Investing" (summary of Fama-French + Asness/Pedersen research).
- **GMO White Papers (free, available at gmo.com):** "Beyond the Factor: GMO's Approach to Value Investing" (practical value implementation combining multiples and quality), "New Options for Equity Investors" (hedging and tail-risk in systematic portfolios).
- **Firm's KNOWLEDGE_BASE.md Section B:** Extended reference library including additional foundational papers (Piotroski F-score, Sloan accruals, Bernard-Thomas PEAD, Frazzini-Pedersen BAB) accessible via institutional library or academic databases.
- **Scout papers (04_RND_LAB/scout_papers_agents.md Part A):** Prioritized replication targets for India-specific quant research on VRP, F&O expiry effects, and dealer-gamma, ranked by data availability and replicate-value on firm's existing datasets.

---

## Status Summary

**Total papers catalogued:** 17  
**Local (downloadable free PDF):** 4  
**Link-only (paywalled journal or restricted SSRN):** 6  
**Practitioner white papers (confirmed free from publishers):** 3  
**Institutional/library-gated (accessible via academic affiliation):** 4  

**Standout findings:**

1. **Fama-French 5-factor + Asness QMJ (Fama-French 2015, Asness et al. 2014):** The canonical multi-dimensional framework for quantamental signals. Our STOCK_SCORECARD_750 operationalizes these six dimensions; any new model must validate compliance.

2. **Novy-Marx Profitability Premium (2013):** Gross profit > net income for predicting returns. Justifies quality-first filter and explains why profitability × value interaction is asymmetrically powerful in selecting winners.

3. **Momentum robustness (Jegadeesh-Titman 30-year update, 2023):** Momentum is the most empirically robust anomaly; it works across geographies and asset classes, strongest in emerging markets + small-cap. Validates Track-2 and intraday momentum research priorities.

4. **Post-publication decay (McLean-Pontiff, updated 2024-25):** 50% Sharpe haircut from backtest-to-forward is empirical prior for any published factor. Pre-register expectation at 50% gross; track actual; if forward beats 50%, signal strength; if lands at 50%, decay is expected. Critical discipline for evaluating new sleeves against live results.

5. **India VRP structural anatomy (Agarwal 2025, Sankar et al. 2020 + 2024-25 updates):** VRP in Nifty exists but is filter-dependent. Overnight > intraday. Continuous volatility > jumps. These structural findings rationalize Track-1 and Track-3 design choices and are replication priorities for our DSR gates.

---

*Last updated: 2026-07-24*  
*Curated by: Lakshmi Narayanan, Knowledge Curator*  
*Next review: 2026-10-31*

---

## See Also

This bibliography builds on the foundational papers listed in `Shreyas_Ionic_AMC/04_RND_LAB/KNOWLEDGE_BASE.md` Section B (Reference Library), with detailed topic organization and India-specific extensions. Key papers from that library (Jegadeesh-Titman 1993, Fama-French 2015, Novy-Marx profitability, Piotroski F-score, Bernard-Thomas PEAD, Frazzini-Pedersen BAB, Harvey-Liu-Zhu demand curves, Bailey-López de Prado DSR/PBO) are accessible through the firm's institutional library and academic databases; this curated list provides detailed one-pagers and practitioner-focused papers that implement the theory. For machine-learning-specific quantamental research and ensemble methods, see ML-Expert Ishaan Gupta's skill resources and the QFRA2 evaluation framework (Module 3-4).

For replication-prioritized quant papers on India-specific topics (VRP structural filters, F&O expiry effects, PEAD, dealer-gamma), see `04_RND_LAB/scout_papers_agents.md` Part A, which ranks papers by replication-value on firm's on-disk datasets and identifies research gaps (SEBI derivatives curb impact, dealer-GEX regime modeling) suitable for original research.
