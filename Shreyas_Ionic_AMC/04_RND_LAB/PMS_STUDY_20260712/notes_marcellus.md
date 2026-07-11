# Marcellus Investment Managers (Saurabh Mukherjea) — Quality-Trap Case Study
Research notes, compiled 2026-07-11 by buy-side analyst subagent. Web research only (WebSearch + WebFetch over public sources: Marcellus own decks/PDFs/newsletters/helpscout FAQ pages, PMS AIF World, IME Capital, holisticinvestment.in, BusinessToday PMS tracker, screener.in community screens, X/Twitter data-commentary, TradingView/Moneycontrol). No SEBI/APMI raw disclosure filings were pulled directly (would require APMI portal access) — all performance figures below are as re-published by third-party aggregators citing SEBI-mandated disclosures; TREAT AS NEEDING ADVERSARIAL RE-VERIFICATION against primary APMI/SEBI PMS disclosure data before being used in any memo.

---

## 1. WHO / STRUCTURE

- Founded by **Saurabh Mukherjea** (ex-CEO of Institutional Equities, Ambit Capital) in 2018, alongside **Rakshit Ranjan** (fund manager, CCP) and other Ambit veterans. Intellectual lineage: the "Coffee Can Investing" philosophy (Mukherjea/Ranjan/Uchat book, and Ambit's original "Coffee Can PMS" launched Mar-2017, which Ranjan managed until Dec-2018 before moving to Marcellus). Coffee-can philosophy = buy quality, put it in a drawer, don't touch it (near-zero churn), let compounding do the work over a decade.
- Product suite (India equity, market-cap segmented):
  - **Consistent Compounders Portfolio (CCP)** — large-cap / market-cap-agnostic-in-theory flagship. Inception 1-Dec-2018.
  - **Rising Giants Portfolio (RGP)** — mid/small-cap "sustainable scalers." Inception Aug-2021.
  - **Little Champs Portfolio (LCP)** — small-cap. Inception 29-Aug-2019. Capped at ~Rs 300cr AUM, since closed to fresh inflows.
  - **Kings of Capital Portfolio (KCP)** — financials-only (banks/NBFCs/insurers/AMCs/brokers).
  - **Global Compounders Portfolio** — international sleeve (not in scope for our NIFTY500 codability work).
- AUM trajectory (important — see §5 Failure Modes): peaked ~**Rs 12,704 crore in Oct-2022** (source: X/Twitter market commentator Kanan Bahl, citing "latest disclosures" — likely SEBI/APMI PMS data, exact as-of date for the "current" figure in his post not confirmed by us). One aggregator citing figures around May-2026 (rendered from a BusinessToday-sourced PMS tracker page, exact primary date unconfirmed) shows combined AUM ~**Rs 2,514.82 crore**; another data point (X post, no confirmed date) cites Rs 4,734cr. Directionally: **50-64% AUM decline from peak**, consistent across sources even though exact numbers/dates disagree — needs primary-source reconciliation before quoting a single figure.
- CCP alone saw **Rs 1,160 crore of redemptions in a single 3-month window** (TradingView/Moneycontrol reprint), explicitly attributed by the reporting to underperformance-driven client exits.

## 2. PHILOSOPHY (as actually documented, not marketing copy)

Marcellus's stated process is an explicit **three-stage funnel** applied to a starting universe (500+ listed names for the mid/smallcap strategies):

1. **"Sustainability" quantitative screen** — thresholds on revenue growth, margin trend/improvement, working-capital and fixed-asset turnover, ROCE, and free-cash-flow generation. This stage **eliminates ~50%** of the starting universe (stated explicitly for Rising Giants; CCP's simpler public description is "double-digit YoY revenue growth AND return on capital above cost of capital, each year for 10 years running").
2. **Forensic-accounting / governance screen** — a proprietary 12-ratio framework explicitly modeled on Howard Schilit's *Financial Shenanigans* (see §3.8 below for the ratio list). This stage **eliminates ~40% of the remaining names** (i.e., roughly 40% of the 50% that survived stage 1) — Marcellus states this is to "stay away from companies with dubious financials."
3. **Bottom-up qualitative research** — conducted only on the surviving ~10% of the original universe: management meetings, channel checks, independent/expert-network views, capital-allocation track-record deep dives, and an assessment of "moat durability" via a two-layer framework: (a) structure/strength of the *current* moat, and (b) how the incumbent's strategic decision-making is likely to respond to emerging competitive threats.

The philosophical core, in Marcellus's own words (paraphrased across multiple decks): find businesses whose **ROCE consistently exceeds cost of capital AND that reinvest a high share of free cash flow at similarly high incremental returns** ("prudent capital allocation" — the sustainability of compounding depends on being ABLE to keep redeploying capital at high ROCE, which is explicitly flagged as the hard part / the thing that eventually runs out for any compounder). They favor "boring," essential-product category leaders (paints, cigarettes, baby formula, cooking oil, adhesives, commercial trucks) that have dominated their category for 20-30+ years, run by professional/institutional management (explicitly "not one-man shows" — a governance/succession-risk screen).

Portfolios are run as a **single model portfolio** — every client, regardless of when they opened their account, holds the same names in the same weights (operationally material: no client-specific tactical tilting).

Funds are **deployed within days of receipt** — Marcellus explicitly does NOT attempt market timing or hold meaningful cash calls, which matters for interpreting their returns (they are not claiming any market-timing alpha, only stock-selection + capital-allocation-quality alpha).

**Valuation is explicitly subordinated to quality** in the stated philosophy — this is the single most important fact for our quality-trap case study, and Mukherjea has since (Mar-2025) publicly conceded it was a mistake not to act on the valuation-related lessons he says the team had already identified (see §5).

## 3. MECHANICAL RULES — FULL LIST WITH SOURCES

1. **CCP twin quantitative filter (universe construction):** "double-digit YoY revenue growth AND return on capital [ROCE] higher than the cost of capital, EACH YEAR for 10 years in a row." — PMS AIF World summary of Marcellus CCP materials.
2. **CCP alternate/simplified public description:** ">=10% annual revenue AND profit growth over the past decade, ROCE above 15%, and low leverage on the balance sheet." — multiple press summaries.
3. **Community-replicated screener.in formula for "Consistent Compounders (Saurabh Mukherjea)"** (NOT an official Marcellus publication, but a widely-used practitioner proxy, useful as a codability starting point): `Sales growth > 15 AND Average ROE 10Y > 15 AND Average ROCE 10Y > 15 AND Market Cap > 10,000 [Rs cr]`. Screen returns ~71 names as of the query date (Titan, Bharat Electronics, Bajaj Auto, Coal India, Hind. Zinc, Eicher Motors, TVS Motor, Torrent Pharma, Solar Industries, Cummins India, BSE, Polycab, GE Vernova T&D, Zydus Life, Marico, Vedanta, Hero Motocorp, Laurus Labs, Dixon Tech, Persistent, Adani Total Gas, Nippon Life, NMDC, MCX, Uno Minda, +more).
4. **Little Champs — original 2018 founding backtest criteria** (historical, used to validate the small-cap concept, not necessarily the live current filter): (a) FY04-08 median ROCE = 20%; (b) FY03-08 earnings growth >= 15%; (c) FY08-end net-debt/equity <= 1x.
5. **Little Champs — current universe & construction:** market cap < US$500mn (community screener.in proxy translates this to roughly Rs 100cr-4,000cr band with ROCE 3Y>14%, 5Y>15%, 10Y>11%, each with soft upper bounds too — i.e., NOT unbounded "more ROCE is better," there appear to be sanity-check upper caps as well, likely to exclude one-off/statistical outliers); portfolio ~15 stocks; **target annual churn 20-25%** (materially higher than CCP); **minimum recommended holding horizon 3 years**; fund deliberately size-capped at ~Rs 300cr AUM specifically for portfolio-company liquidity reasons; closed to fresh inflows.
6. **Rising Giants — universe:** market cap US$500mn-10bn (~Rs 700cr-7,500cr per one source), ~450-name starting universe. **Stage 1** ("sustainability parameters" — revenue growth, margin improvement, working-capital/asset turns, ROCE, cash generation) eliminates ~50%. **Stage 2** (forensic accounting/governance) eliminates ~40% of the remainder. **Stage 3** (bottom-up, channel checks + management meetings) applied to final ~10%. Final portfolio **15-20 names**, scored on two axes: "Longevity" (moat durability, management "lethargy" risk, succession-planning risk) and EPS growth prospects.
7. **CCP portfolio construction:** **10-15 stocks** in the live model portfolio (also quoted elsewhere as "10-20" and, in a more recent refined description, "**12-15** ultra-high-quality stocks"), drawn from a **~30-name coverage universe** that Marcellus actively researches. **Target annual churn: no more than 5-8%** (i.e., materially LOWER turnover than Little Champs — market-cap segment appears to set the churn budget). **Average intended holding period: 8-10 years.**
8. **Kings of Capital construction:** **10-14 holdings**, financials-sector-only (banks, NBFCs, life insurers, general insurers, asset managers, brokers); selection criteria stated qualitatively as "good corporate governance, prudent capital allocation skills, high barriers to entry"; explicit strategic thesis = benefit from lending-sector consolidation + financialization of household savings.
9. **Forensic accounting framework — the 12 ratios** (adapted from Howard Schilit's *Financial Shenanigans*), grouped:
   - *Income-statement manipulation checks:* (1) CFO as % of EBITDA; (2) volatility in non-operating income; (3) provisioning for doubtful debts as % of debtors overdue >6 months.
   - *Balance-sheet checks:* (4) yield on cash & cash equivalents; (5) contingent liabilities as % of net worth; (6) change in reserves explained by P&L for the year + dividends (i.e., does the reserves roll-forward reconcile).
   - *Auditor-quality check:* (7) growth in auditor's remuneration vs. growth in revenues.
   - (Marcellus states there are 12 ratios total across these categories plus a qualitative governance checklist; only 7 were named explicitly in the sources found — the remaining ~5 were not itemized in the material we could access.)
   - Marcellus claims (self-reported, unverified by us) "strong correlation between accounting-quality results and investment returns" for this framework.
10. **Sell/exit discipline (discretionary, not mechanical/threshold-based):** (a) full exit when the research team's view of a company's moat strength/sustainability deteriorates; (b) full exit when a new candidate has HIGHER relative conviction and displaces an existing holding (relative-conviction rotation, not an absolute stop-loss); explicit sell triggers named elsewhere: weakening free-cash-flow growth, deteriorating competitive moat/pricing power, succession-planning concerns emerging. Partial trims are used to rebalance position sizes back toward target conviction weights after differential drawdowns across holdings (i.e., they DO rebalance mechanically for price-driven weight drift, even though the buy/sell decision itself is analyst-judgment-driven).
11. **No disclosed maximum single-position weight rule.** Independent review (holisticinvestment.in) of Rising Giants found the **top-4 holdings ~40% of the portfolio** at the review date — i.e., concentration is a real, undisclosed-limit feature, not a marketing description only.
12. **Fee structure** (structural facts, not alpha rules, but relevant to any capacity/backtest-vs-realized-return translation):
    - CCP: minimum ticket Rs 50 lakh; Fixed 1.5%/2.0% p.a. (direct/partner) no performance fee; OR Variable 20% profit share above 8% hurdle; OR Hybrid 0.75-1.0% p.a. + 15% above 12% hurdle. No lock-in, no exit load.
    - Little Champs: minimum ticket Rs 50 lakh; Fixed 1%/1.5% p.a. (direct/partner); Variable 20% above 10% hurdle; **exit load 3%/2%/1% for years 1/2/3** (i.e., LCP — despite being pitched as illiquid/long-horizon — has an explicit near-term-exit penalty structure CCP lacks); minimum recommended holding 3 years.

## 4. RETURNS CLAIMS — WITH EXACT PERIODS, FIGURES, SOURCES

| Strategy | Period | Return | Benchmark | Source |
|---|---|---|---|---|
| CCP | FY19-24 (5yr) | +17.4% CAGR (pre-fee) | vs own EPS CAGR of +17.8% over same period — i.e. ~0 multiple expansion | Mukherjea investor newsletter 12-Mar-2025, reported by BusinessToday 17-Mar-2025 |
| CCP | CY2023 (calendar) | +16% | Nifty50 TRI (~6pp better, i.e. CCP underperformed by ~6pp) | Marcellus Dec-2023 portfolio update newsletter |
| CCP | 1-Apr-2023 to 31-Dec-2023 | +28% | Nifty50 TRI (CCP marginally ahead) | Marcellus Dec-2023 newsletter |
| CCP | FY24 (Apr-2023 to Mar-2024) | +24% (net of fees/expenses) | Nifty50 TRI +30% (CCP underperformed) | Marcellus Mar-2024 "Portfolio Performance and Update on Fundamentals" |
| CCP | 1yr trailing, as of 31-May-2026 | -4.05% to -4.1% (two sources) | S&P BSE500 TRI -1.1% (also negative, but less so) | PMS AIF World live tracker; IME Capital rating page |
| CCP | 3yr trailing, as of 31-May-2026 | +5.4% CAGR | vs S&P BSE500 +12.2% CAGR | IME Capital rating page |
| CCP | 5yr trailing, as of 31-May-2026 | +4.3% CAGR | vs S&P BSE500 +11.0% CAGR | IME Capital rating page |
| CCP | Since inception (1-Dec-2018) to 31-May-2026 | +11.58%/+11.6% CAGR | Nifty50 TRI SI +12.14% CAGR (CCP behind its OWN named benchmark cumulatively, 7.5 years in) | PMS AIF World; IME Capital (both independently corroborate) |
| CCP | 1yr risk stats (to 31-May-2026) | Alpha -6.93%, Beta 1.07, StdDev 17.49% | — | PMS AIF World |
| Little Champs | 1-month / 3-month, to 31-May-2026 | +0.67% / +0.98% | — | PMS AIF World live tracker |
| Little Champs | 6-month, to 31-May-2026 | -6.06% | — | PMS AIF World |
| Little Champs | 1yr, to 31-May-2026 | **-6.77%** | S&P BSE500 TRI -0.07% (LCP much worse) | PMS AIF World |
| Little Champs | 2yr, to 31-May-2026 | +0.93% | — | PMS AIF World |
| Little Champs | 3yr, to 31-May-2026 | +1.96% | — | PMS AIF World |
| Little Champs | **5yr, to 31-May-2026** | **-0.74% CAGR (a literal 5-year net loss)** | — | PMS AIF World |
| Little Champs | Since inception (29-Aug-2019) to 31-May-2026 | +10.46% CAGR | — | PMS AIF World |
| Little Champs | AUM at 31-May-2026 | ~Rs 128.94 crore | (fund was capped near Rs 300cr at inception design) | PMS AIF World |
| Rising Giants | Since inception (Aug-2021) to 31-May-2023 | -15.7% cumulative | — | holisticinvestment.in independent review |
| Rising Giants | 1yr, to 31-May-2023 | -2.8% | — | holisticinvestment.in |
| Rising Giants | 6-month, to 31-May-2023 | -6.2% | vs BSE500 TRI (underperformed) and vs Nifty Next 50 ("underperformed by quite a big margin") | holisticinvestment.in |
| Rising Giants | concentration | Top-4 stocks ~40% of portfolio | — | holisticinvestment.in |
| Kings of Capital | Since inception (~15 months, exact start date not confirmed by us) | +34% annualized | Bank Nifty +54% annualized (KCP underperformed; Marcellus's own explanation: KCP is only ~40% banks vs Bank Nifty's 100% banks, KCP avoided "turnaround" stories, and there was a 48% Bank Nifty drawdown-then-recovery inside the window that mechanically favored the concentrated bank index) | Marcellus own newsletter "Why are we underperforming the Bank Nifty?" |
| Firm-wide AUM | peak Oct-2022 | ~Rs 12,704 crore | — | Kanan Bahl (X/Twitter), citing "latest disclosures" |
| Firm-wide AUM | "current" (exact date unconfirmed, likely ~early-mid 2025 based on thread context) | ~Rs 4,734 crore (one source) / ~Rs 2,514.82 crore (separate aggregator, dated ~May-2026 per our search context) | — a 50-64% peak-to-current decline either way | Kanan Bahl (X); BusinessToday-sourced PMS tracker |
| CCP redemptions | single 3-month window (exact months not confirmed, article context ~2024-2025) | Rs 1,160 crore net redemptions | CCP AUM at that point ~Rs 5,050 crore | TradingView reprint of Moneycontrol article |

**IMPORTANT CAVEAT FOR ADVERSARIAL VERIFICATION:** Multiple of the above figures come from third-party aggregator pages (PMS AIF World, IME Capital, BusinessToday) whose own "as of" date stamps were extracted by an AI web-fetch summarizer and could be stale/cached relative to the actual page-load date (2026-07-11). The AUM figures in particular have TWO materially different "current" values from two different sources/methodologies — before using any single number in a memo, pull the primary APMI/SEBI PMS monthly disclosure directly.

## 5. FAILURE MODES / CRITICISM — UNBIASED ASSESSMENT

This is the single most useful part of the Marcellus study for our purposes, because it is a **live, multi-year, real-money, real-redemption natural experiment in exactly the failure mode we need to guard our own quality-factor work against.**

**5.1 The core admitted failure — "quality with no valuation discipline" = beta-tracking, not alpha.**
Mukherjea's own words (12-Mar-2025 investor newsletter, reported by BusinessToday 17-Mar-2025): the CCP's FY19-24 return (17.4% CAGR) essentially just equaled the portfolio's own earnings growth (17.8% EPS CAGR) — meaning **zero net multiple-expansion contribution over five years**, and by extension, all of the "alpha" in the pre-2019 track record that made Marcellus famous was arguably a **quality-factor re-rating tailwind (2013-2021 broad market preference for quality/growth) rather than repeatable stock-picking skill.** When the market's factor preference rotated toward cyclicals/value/smaller companies post-COVID, Marcellus's rigid "hold moats regardless of valuation, minimal churn" discipline had no mechanism to participate, and Mukherjea explicitly says he recognized this "12 to 18 months" too late.

**5.2 Independent (non-Marcellus) rating corroboration.**
IME Capital — a third-party PMS rating shop with no stated affiliation to Marcellus — flags in its own review (not marketing copy) that CCP's "rigid adherence to quality criteria limits their ability to reposition portfolios" during cycle turns, and that as of their review date the fund was "amongst the worst performing schemes" in its category, with **negative alpha across the 1yr, 3yr AND 5yr trailing windows** simultaneously (see table above) — this is not a one-bad-year story, it is a multi-year pattern.

**5.3 The failure is common-mode across ALL FOUR India equity strategies, not one stock-picking mistake.**
- CCP (large-cap): underperforming its own named benchmark (Nifty50 TRI) cumulatively since inception, 7.5 years in.
- Rising Giants (mid-cap): -15.7% cumulative since inception at the 2023 review point, entry valuations as high as ~58x PE flagged as the proximate cause.
- Little Champs (small-cap): literal negative 5-year CAGR (-0.74%) as of May-2026.
- Kings of Capital (financials): underperforming Bank Nifty by ~20pp annualized, though Marcellus's own explanation here is more benign (index-composition + avoiding turnaround stories, not necessarily a valuation mistake).
When a "quality, low-churn, buy-and-hold" shop underperforms simultaneously across large/mid/small-cap and even its sector-focused sleeve, the parsimonious explanation is the SHARED design choice (no valuation discipline + minimal churn) rather than four independent stock-picking errors — this is exactly the "quality-at-any-price stagnation" style-trap named in our brief.

**5.4 Small-cap illiquidity as a SEPARATE, compounding failure mode (not just a valuation problem).**
Little Champs was deliberately AUM-capped (~Rs 300cr) and then closed to new inflows specifically because Marcellus itself judged portfolio-company liquidity "pitifully low" for a strategy of any meaningful scale. This is a rare case of a manager pre-emptively admitting non-scalability of its own edge — genuinely honest, but it also means the -0.74% 5-year return happened WITHIN a fund the manager had already de-risked for capacity, i.e., the underperformance is not an "we grew too big and impacted our own prices" story, it's a pure stock-selection/style-timing story on top of a liquidity-constrained universe.

**5.5 Concentration without a disclosed hard limit.**
Rising Giants' top-4-holdings-at-40%-of-book (independent finding, not self-disclosed by Marcellus) shows the "buy conviction, don't churn" philosophy has no circuit-breaker against a single deteriorating name becoming a large drag — the sell trigger is a discretionary analyst judgment call ("moat has deteriorated"), which is inherently slower and more return-path-dependent than a mechanical stop or rebalancing band.

**5.6 Real-money confirmation, not just a return-series story.**
The AUM decline (~50-64% peak-to-trough by whichever source) plus a confirmed Rs 1,160cr single-quarter redemption wave from CCP means sophisticated/HNI clients have been redeeming in size DURING the underperformance window — this is a stronger falsification signal than the returns alone, since it rules out "this is just noise that will mean-revert and clients are holding through it patiently" as Marcellus's own base case would predict for a coffee-can philosophy.

**5.7 Balance / counterpoint (for fairness).**
- Since-inception numbers, while underperforming benchmark, are NOT catastrophic in absolute terms: CCP +11.6% CAGR over 7.5 years, Little Champs +10.5% CAGR over ~6.8 years — an investor who bought at inception and held throughout is still up meaningfully in absolute rupee terms, just behind a passive index alternative net of PMS fees.
- We found NO evidence in this search of an accounting-fraud/governance blowup inside a Marcellus flagship holding — the forensic-accounting screen appears to have done its stated job of avoiding "dubious financials" companies; the failure mode here is a **valuation/style-timing/churn-discipline failure, not a stock-quality-assessment failure.** This is an important distinction: Marcellus's forensic-accounting layer (stage 2 of their funnel) seems to have worked as designed; it is the ABSENCE of any valuation/exit-discipline overlay on top of the quality screen that produced the underperformance.
- Mukherjea's own public admission of the mistake (rather than the more common asset-manager move of blaming the index/regime/"short-term noise" — which he also does elsewhere, see "Asset managers, please spare us your polyexcuses" title found in search, ironically) is at least evidence of an honest post-mortem culture, even if it came 12-18 months late by his own account.

## 6. CODABILITY — WHAT WE CAN AND CANNOT BUILD WITH OUR DATA

**Our data:** PIT quarterly fundamentals (Sales/NP/EPS/OPM, annual ROE/ROCE), daily OHLCV, NIFTY500 PIT universe (`NIFTY500_TICKER_2005_2025_Final.xlsx`, 42 snapshots).

**DIRECTLY CODABLE (quantitative funnel, stage 1):**
- **Twin filter (core CCP rule):** trailing-window (we likely have 5-8 years of PIT depth rather than a clean 10Y for all names — need to check `datasets/earnings_pit/unified_quarterly_pit.parquet` depth) revenue/EPS CAGR >= ~10-15% AND avg ROCE (or ROE substitute if ROCE unavailable per-name) >= 15%, computed PIT (i.e., using only data that would have been known as of each rebalance date — avoids the lookahead landmines already documented in our CLAUDE.md). This is literally reproducible as the screener.in community formula shows: `Sales growth > X AND avg ROE/ROCE(nY) > 15 AND MCap > threshold`.
- **Market-cap-band universe segmentation** (large/mid/small per Marcellus's own Rs-crore bands, or scaled-for-inflation equivalents) using our NIFTY500 PIT membership + daily-close-derived market cap.
- **Low-churn portfolio construction rule**: rebalance annually (or only on a rule breach) rather than monthly, holding 10-20 names ranked by a composite growth+ROCE score — directly implementable as a backtest portfolio-construction module.
- **Leverage/net-debt-to-equity screen** (e.g., <1x) — codable IF our fundamentals dataset carries a debt/equity or net-debt field; needs a quick check against `05_DATA_OFFICE/DATA_CATALOG.md` (not verified in this session — flag for Data Officer Kavya).
- **Position-count + conviction-weighting**: top-N by composite score, equal- or score-weighted — codable.
- **A systematic PROXY for the discretionary sell rule**: e.g., "exit if trailing-4Q ROCE falls below threshold for 2 consecutive quarters" or "exit if EPS growth turns negative for 2 consecutive quarters" — this is a reasonable, testable APPROXIMATION of "moat has deteriorated" but is explicitly NOT what Marcellus actually does (theirs is a discretionary analyst call, not threshold-triggered) — must be labeled as our own systematic approximation, not a replication of their actual process, if we ever build/report this.

**NOT CODABLE / DATA WE LACK:**
- **The forensic-accounting 12-ratio Schilit framework** — needs granular line items (contingent liabilities as % of net worth, growth in auditor's remuneration vs. revenue growth, provisioning for doubtful debts >6-months-overdue as a % of such debtors, yield on cash & equivalents, reserves-roll-forward reconciliation) that are NOT part of standard Sales/NP/EPS/OPM/ROE/ROCE fields. Possibly partially present in the raw `india_fundamentals_mc/Train.parquet` (per CLAUDE.md, though note the corrupt `annual_report` column caveat) but auditor-remuneration and contingent-liability granularity at this level is unlikely to be there — needs Data Officer verification before we claim this is buildable.
- **The qualitative "final 10%" bottom-up layer** — management meetings, channel checks, expert-network calls, "moat durability" / competitive-response judgment, succession-planning assessment. This is fundamentally unautomatable from numeric data and, notably, is exactly the part Marcellus claims is its actual differentiator/edge — meaning our systematic replica would at best capture their STAGE-1 QUANT FILTER, which per Marcellus's own admitted failure (§5.1) is the part that has NOT been generating alpha recently (it just tracks earnings growth without stock-picking or valuation-timing skill layered on top). In other words: **the part of Marcellus we CAN codify is exactly the part that (by their own admission) hasn't been adding value lately** — an important honesty flag for us if we're tempted to build a "Marcellus-replica" screen and expect it to outperform.
- **Discretionary, judgment-based exit discipline** — no mechanical proxy exists in their own stated process; any systematic version we build is our own invention, not a replication.
- **Position-sizing/rebalancing exact algorithm** — not disclosed with a formula (we only know outcomes, e.g. top-4 = 40% of RGP, from independent third-party review, not from a stated Marcellus rule).

**Strategic implication for our R&D:** Marcellus is best used NOT as a strategy to replicate, but as a **documented negative prior-art case for "quality factor without valuation/exit discipline in Indian largecap/midcap/smallcap equities, 2022-2026."** Before certifying any of our own ROCE/growth-based long-only equity screens (if we build any under Track-2/Track-3), we should backtest whether adding a valuation overlay (e.g., PE-vs-growth, PEG-style band) or a mechanical exit trigger (vs. Marcellus's discretionary one) would have avoided their multi-year, multi-strategy underperformance in the SAME data window — this gives us a concrete, real-world out-of-sample-ish comparison point rather than only comparing against our own backtest assumptions.

## 7. SOURCE LIST (for later adversarial re-verification)

- https://www.pmsaifworld.com/portfolio/marcellus-consistent-compounders-pms/
- https://www.pmsaifworld.com/portfolio/marcellus-little-champs/
- https://www.pmsaifworld.com/portfolio/marcellus-rising-giants-pms/
- https://marcellus.in/wp-content/uploads/2021/08/Marcellus_CCP_Regular.pdf (fetch failed — binary/image PDF, not text-extractable via WebFetch)
- https://marcellus.in/wp-content/uploads/product-decks/kcp-direct.pdf (fetch failed — binary PDF)
- https://marcellus.helpscoutdocs.com/article/30-marcellus-consistent-compounders-portfolio-ccp
- https://marcellus.helpscoutdocs.com/article/29-marcellus-little-champs-portfolio
- https://www.screener.in/screens/469372/consistent-compounders-saurabh-mukherjea/ (community proxy, not official Marcellus)
- https://www.screener.in/screens/218753/marcellus-little-champs/ (community proxy, not official Marcellus)
- https://www.holisticinvestment.in/marcellus-rising-giants-pms-good-bad-investment-review/ (independent critical review)
- https://imecapital.in/pms-scheme/marcellus-consistent-compounders (independent rating shop)
- https://www.businesstoday.in/markets/stocks/story/my-first-failure-saurabh-mukherjea-admits-valuation-gaps-dragged-marcellus-returns-468089-2025-03-17
- https://marcellus.in/newsletter/kings-of-capital/why-are-we-underperforming-the-bank-nifty/
- https://marcellus.in/newsletter/marcellus-erudite/marcellus-portfolio-performance-and-update-on-fundamentals/ (Mar-2024)
- https://marcellus.in/newsletter/marcellus-erudite/marcellus-portfolio-update-and-performance-snapshot-december-2023/
- https://marcellus-us.com/newsletter/little-champs/the-importance-of-accounting-quality/ (forensic accounting ratio list)
- https://x.com/BahlKanan/status/1900166684360794393 (AUM peak/decline claim — third-party, needs primary-source check)
- TradingView reprint of Moneycontrol article on CCP redemptions (Rs 1,160cr / 3 months)
- https://marcellus.in/wp-content/uploads/2023/03/Marcellus_Rising_Giants_PMS_June-2023_Direct_Final_compressed.pdf (not fetched directly — summarized via search snippet only)

**Sources found but NOT independently fetched/verified this session** (flagged so a future pass knows what's still open): pmsbazaar.com AMC page, businesstoday.in PMS tracker pages (multiple), sharescart.com, ipoplatform.com, aum13f.com — these could reconcile the AUM discrepancy in §4 if pulled directly.
