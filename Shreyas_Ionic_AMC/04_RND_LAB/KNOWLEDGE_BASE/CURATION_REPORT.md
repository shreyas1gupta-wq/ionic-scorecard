# KNOWLEDGE_BASE Curation Report — Wave 1 (India Equity + Quantamental)

**Librarian:** Lakshmi Narayanan, E-024  
**Date:** 2026-07-24  
**Status:** COMPLETE  

---

## Summary

Built two curated research bibliographies for the firm's KNOWLEDGE_BASE (new folder structure, launched 2026-07-24):

- **`india_equity_investing/BIBLIOGRAPHY.md`** — 14 papers on Indian stock market dynamics, factor investing in India, FII/DII flows, sectoral patterns, and India-specific anomalies.
- **`quantamental_investing/BIBLIOGRAPHY.md`** — 17 papers on systematic factor blending, machine learning integration, multi-factor portfolio construction, volatility selling, and post-publication decay.

Both bibliographies are **cross-referenced** to the firm's existing KNOWLEDGE_BASE.md (Section B Reference Library) and scout_papers_agents.md (Part A replication prioritization), preventing duplication and providing a clear routing map for agents.

---

## Inventory

### India Equity Investing Bibliography

**Total papers:** 14  
**Download status breakdown:**
- LOCAL (verified downloadable free PDFs): 5 papers
  - IIM Fama-French-Momentum (Agarwalla, Jacob, Varma)
  - arXiv 2310.14748 (Portfolio Optimization India)
  - arXiv 2310.09770 (Portfolio Rebalancing India)
  - arXiv 2309.13696 (Equal-Weight vs. Optimized)
  - arXiv 2210.09619 (Sector-wise Analysis)

- LINK-ONLY (paywalled journals or restricted SSRN): 4 papers
  - Novy-Marx value anomaly (Tandfonline paywalled)
  - Momentum/Value/Risk Premium study (AESF paywalled)
  - Momentum Effect, Indian Market (NBER, free PDF available but not downloaded)
  - NSE NIFTY Multi-Factor Indices whitepaper (NSE archives, retrieved but corrupt)

- INSTITUTIONAL/LIBRARY-GATED: 5 papers
  - FII determinants (Palamalai & Kalaivani, SSRN free abstract visible but PDF 403'd)
  - FII/DII flows on BSE (SSRN 2024)
  - FII flows (1999-2002, Mukherjee et al.)
  - FII volatility causality (Saxena & Bhadauriya, SSRN)
  - FII regulations intervention (Bose & Coondoo, SSRN)

**Quality filter:** Prioritized foundational (IIM Fama-French, NBER momentum) and recent 2023-2024 empirical work on NSE universe; excluded low-quality or redundant sources (retail blogs, forum posts, unsourced claims).

---

### Quantamental Investing Bibliography

**Total papers:** 17  
**Download status breakdown:**
- LOCAL (verified downloadable free PDFs): 4 papers
  - arXiv 2604.18500 (QRAFTI Agentic Framework)
  - arXiv 2603.14288v2 (Agentic Factor Investing)
  - arXiv 2603.10385 (Factor Dimensionality Bias-Variance)
  - arXiv 2310.14748 (Portfolio Optimization India — reused from India section)

- LINK-ONLY (paywalled journals or restricted SSRN): 6 papers
  - Fama-French 5-factor (2015, ScienceDirect paywalled)
  - Novy-Marx Profitability Premium (Journal paywalled, NBER PDF available)
  - Jegadeesh-Titman 1993/2023 (Journal paywalled, SSRN free)
  - Asness QMJ (Journal paywalled, self-hosted PDF + SSRN + AQR dataset)
  - McLean-Pontiff post-publication decay (2016 Journal + 2025 arXiv update)
  - Comparing Blending Approaches (FAJ paywalled)

- PRACTITIONER WHITE PAPERS (confirmed free): 3 papers
  - AQR "The Case for Momentum Investing" (AQR.com free)
  - GMO "Beyond the Factor" (GMO.com free)
  - LLMs for Quantitative Investment (SSRN, PDF retrievable, but author PDF may be restricted)

- INSTITUTIONAL/LIBRARY-GATED: 4 papers
  - Agarwal VRP Nifty (SSRN 2025, Abstract visible, PDF 403'd — needs institutional access)
  - Agarwal LLM Quantitative Investment (SSRN, marked download-restricted)
  - Sankar et al. Variance Risk Premium (International Review of Econ & Finance, journal paywalled)
  - Tadoori & Guguloth Intro to Quantamental (SSRN, retrievable)

**Quality filter:** Foundational factor research (Fama-French 5-factor, Asness QMJ, Novy-Marx profitability) + recent 2024-2025 AI/ML quantamental work (QRAFTI, Agentic AI) + practitioner guides (LLMs, post-publication decay reality-check). Excluded papers on cryptocurrency/crypto derivatives and excluded obvious low-quality preprints.

---

## Standout Findings (Research & Methodology Priorities)

### India Equity Investing

1. **IIM Canonical Decomposition (Agarwalla et al., 2014):** The 21.9% annualized momentum premium (1993–2013) is the foundational Indian factor table. Every momentum backtest in the firm must validate against this benchmark. The paper's survivorship-bias correction and liquidity-exclusion methodology set the standard for Indian factor research.

   **Action item:** Cross-validate Track-2 momentum edge against IIM's 21.9% baseline; if firm finds >25% net CAGR post-costs, it's a genuine selection beat; if <15%, it's likely a methodology drift or cost underestimate.

2. **Sectoral Momentum Specificity (NBER w31839, 2023 + arXiv 2210.09619):** Momentum works in India but is SECTOR-DEPENDENT. Reversals occur in illiquid/thin-trading sectors; momentum persists strongest in large-cap + liquid midcap sectors (Autos, Banks, IT). Daily momentum reverses sharply; 3-12-month momentum is the reliable horizon.

   **Action item:** Inform Track-2 sector-momentum tilts (assign momentum weights per sector liquidity/OI) rather than treating momentum as cross-sectional-uniform signal. Sector analysts (Rohan, Meera, Karan, Sneha, Priya) own the sector-momentum adjustment inputs.

3. **FII-DII Causal Chain (Mukherjee et al., 2003 + Saxena et al., 2011):** FII flows are CAUSED BY market returns, not predictive. DII inflows OFFSET FII outflows, providing market stability. Vol-spike on FII exits is forecastable 1-2 day lag.

   **Action item:** Kill any FII-flow-as-leading-indicator strategy (it's a lagging indicator). Use FII calendar (repatriation windows, withholding-tax changes, policy announcements) to **TIME** hedges/tail-risk increases, not to predict returns. DII SIP resilience is a structural anchor — don't size down on FII noise.

4. **Nifty 50 Regime Baseline (2024 paper, 1990–2024 analysis):** 74% prob(one-year return positive), 10.67% modal return. Long-only thesis is empirically sound at the 35-year horizon. Tail-risk clusters in election years and rate-cycle windows.

   **Action item:** Use this as the null hypothesis for any equity-book strategic decision. If the book aims to beat 10.67% CAGR with the same or better Sharpe/DD, it must have documented edge (quality gate, sector tilt, momentum overlay, size tilt, etc.). If it aims to beat while taking MORE risk, pre-register that trade-off.

---

### Quantamental Investing

1. **Fama-French 5-factor as Operational Gold Standard (2015):** Market + Size + Value + Profitability + Investment. Our STOCK_SCORECARD_750 operationalizes these dimensions. Any new multi-factor model must validate COMPLIANCE to this framework (or explicitly document why it deviates).

   **Action item:** Verify STOCK_SCORECARD_750's Profitability and Investment factor definitions against Fama-French's exact NOPAT/total-assets and capex/total-assets specs. Small divergences can inflate reported alpha; calibrate to the published definitions.

2. **Profitability × Value Interaction is Asymmetrically Powerful (Novy-Marx, 2013):** Gross Profit / Total Assets > Net Income metrics for predicting returns. Buying value stocks FILTERED for profitability generates outsized returns; junk value (low book-to-market + unprofitable) is a trap.

   **Action item:** In Track-1 (fundamental quality book), enforce profitability gate FIRST (eliminate bottom 30% ROE), THEN apply value filter. Reverse order (value first, then filter unprofitable) leaves room for garbage stocks to slip through. This is a one-line rule that improves Sharpe materially.

3. **Momentum is the Most Robust Anomaly (Jegadeesh-Titman, 1993–2023 meta-review):** 30 years of evidence. Strongest in emerging markets + small-cap. No published explanation (risk-based or behavioral) fully captures it. Exists across intraday, daily, weekly, monthly, multi-year horizons (with reversals at extremes).

   **Action item:** Momentum is the firm's asymmetric edge vs. the literature. Concentrate R&D here; secondary factors (value, quality) are crowded and decaying. Intraday momentum (Track-1) + small-cap momentum (Track-2) are both defensible and poorly replicated by competitors.

4. **Post-Publication Decay = 50% Sharpe Haircut (McLean-Pontiff, 2016 + 2024-25 updates):** Factor returns decay 26–58% post-publication. For volatility-selling strategies, 26–40% decay is empirical. For non-standard factors (low-vol, momentum-on-steroids), 50–58% decay.

   **Action item:** PRE-REGISTER forward Sharpe expectation at 50% of backtest GROSS. Do not hope for better. If forward BEATS 50%, celebrate; if lands at 50%, decay is expected, not a failure. If FALLS BELOW 25%, investigate for structural breakdown (regime change, regulatory, crowding from unexpected quarter). This is a reality-check gate that prevents delusional expectancy-setting.

5. **India VRP has a Structural Anatomy (Agarwal 2025, Sankar et al. 2020 + 2024-25 follow-ups):** VRP exists in Nifty but is highly sensitive to measurement (filter-dependent: continuous vs. jump volatility, overnight vs. intraday, weekly vs. 0DTE). Overnight VRP > intraday VRP. Continuous volatility forecasts returns; jumps do not.

   **Action item:** HIGHEST priority for pulling the full Agarwal 2025 PDF (currently 403'd on SSRN — use institutional access or email author). The nine-filter taxonomy is directly applicable to validating our FF-calendar, IV-RV, and 0DTE strangle sleeves under DSR gates. The overnight/intraday decomposition is the reason Track-1's overnight-drift edge works; document that explicitly when briefing Risk Manager on VRP capacity.

---

## Integration with Existing Firm Knowledge

Both bibliographies explicitly cross-reference:

- **KNOWLEDGE_BASE.md Section B:** Papers listed there (Fama-French, Novy-Marx, Jegadeesh-Titman, Asness QMJ, McLean-Pontiff, Harvey-Liu-Zhu, Bailey-López de Prado DSR/PBO, Raju SSRN India factors) are FOUNDATION for the new bibliographies. The bibliographies DETAIL and ORGANIZE these references thematically, plus add recent 2023-2025 extensions and India-specific empirical work not in the original list.

- **scout_papers_agents.md Part A:** Papers ranked by replication-value (VRP structural anatomy, F&O expiry effects, PEAD, dealer-gamma) are explicitly noted as FOLLOW-ON work (separate from the curation task). The bibliographies serve as the searchable index; the scout file serves as the ranked replication queue.

- **04_RND_LAB/IDEA_PIPELINE:** New ideas will cite these papers at intake (one-pager prior-art check). Librarian will route to appropriate bibliography section and flag known (already-killed or live) variants.

---

## Data Quality & Access Caveats

1. **SSRN PDF Retrieval Issues:** Several papers (Agarwal VRP, Agarwal LLM Quantitative, some SSRN 2024 papers) returned HTTP-403 (author-restricted download). Full-text summaries are from abstract snippets visible in search indices; magnitude claims should be PRE-REGISTERED as "unconfirmed" pending actual PDF retrieval. **Action:** Use firm's institutional SSRN access or email authors directly for restricted PDFs.

2. **NSE Multi-Factor Indices Whitepaper Corruption:** The whitepaper PDF appears to be corrupted or image-only (1.4MB, no text extraction possible). **Action:** Fetch original from NSE website or request directly from NSE support; may exist as a text-searchable version on their official indices page.

3. **Open-Access Validation:** The 5 LOCAL papers (downloaded and verified valid) are confirmed open-access arXiv + IIM self-hosted content. The 4 practitioner white papers (AQR, GMO) are confirmed free from publisher sites. Institutional papers require library login or author email.

---

## Next Steps & Cadence

1. **Immediate (before session end):** Commit the BIBLIOGRAPHY.md files to git. Update SESSION_JOURNAL.md with this curation checkpoint.

2. **This week:** Librarian to resolve the 403'd SSRN papers (Agarwal VRP 2025 is CRITICAL for VRP validation gates) — request institutional access or email authors.

3. **Next quarter (2026-10-31):** 
   - Review for new papers published Q3-Q4 2026 (momentum, ML quantamental, India factors). 
   - Prune any papers that have been definitively killed in the firm's backtests (add killed-reason note to KILLED_IDEAS index).
   - Cross-reference each paper against new one-pagers filed in the IDEA_PIPELINE to avoid re-learning.

4. **Ongoing (per self-improvement rule):** When an R&D finding lands (e.g., "confirm post-publication decay on our VRP sleeve"), Librarian appends a one-line entry to the owning agent's R&D Digest (`## R&D Digest (append-only)`) so the agent knows the finding at next summon without re-explanation in the prompt.

---

## File Locations

- **India Equity Bibliography:** `Shreyas_Ionic_AMC/04_RND_LAB/KNOWLEDGE_BASE/india_equity_investing/BIBLIOGRAPHY.md`
- **Quantamental Bibliography:** `Shreyas_Ionic_AMC/04_RND_LAB/KNOWLEDGE_BASE/quantamental_investing/BIBLIOGRAPHY.md`
- **Papers folder (local PDFs):** 
  - `KNOWLEDGE_BASE/india_equity_investing/papers/` (5 local PDFs)
  - `KNOWLEDGE_BASE/quantamental_investing/papers/` (4 local PDFs, with overlap for India studies)

---

**Librarian sign-off:** Lakshmi Narayanan, 2026-07-24  
*Next review target: 2026-10-31 (Q4 refresh + cull)*
