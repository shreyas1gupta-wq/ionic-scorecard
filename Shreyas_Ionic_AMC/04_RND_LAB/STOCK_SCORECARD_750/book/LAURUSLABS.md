---
symbol: "LAURUSLABS"
company: "LAURUSLABS"
sector: "Healthcare"
universe: "universe750"
rec: "Hold"
quant_rec: "Hold"
growth_3y_pct: 17
escalation: true
holding_value_inr: null
updated: 2026-07-21
tags:
  - stock-note
---
# LAURUSLABS

> [!summary]
> Laurus Labs delivered a genuinely strong FY26 (revenue +23% to Rs6,813cr, margins up 6.7 points, profit roughly tripling) as its multi-year pivot from ARV-API dependence toward a CDMO-led model (now serving global majors like Amgen) gains traction, on a clean FDA record with no warning letters or import alerts across its plants. The business quality is real, but the stock trades at an extremely rich ~95-113x trailing earnings and ~97x book -- among the richest multiples in Indian pharma -- pricing in years of flawless execution of a CDMO transition that management itself says will take until FY28-29 to reach even half of revenue. We rate this a Hold per the quant score (we cannot override a quant Hold to Sell), but flag the valuation-versus-execution-track-record gap for portfolio-manager attention.

## Recommendation — Hold

Quant composite (final_score_3y 44.82, final_score_1y 63.46) resolves to Hold, and the underlying pillars make sense on inspection rather than looking like a data artifact: value_score is deliberately low (10.44/100) because the quant engine's own pe_current (94.63x, matching web-sourced trailing P/E of ~95-113x across sources) correctly prices this as one of the richest multiples in the pharma/healthcare set; growth_1y_score is high (75.4) on genuine FY26 execution (+23% revenue, margin expansion); growth_3y_score is low (22.6) because the 3-year CAGR (4.09%) is still dragged down by the 2022-24 ARV destocking trough -- and the row's own growth_divergence_flag=True confirms the quant engine already sees this 1y-vs-3y tension. Under the V1 asymmetric-override rule I cannot turn a quant Hold into a Sell; my own read is that the business case (clean FDA record, credible CDMO client roster, improving ROCE, clean balance sheet) supports Hold over Sell on operating merits, but the valuation is extreme enough (P/E ~95-113x, P/B ~97x) that I am not comfortable calling this a comfortable Hold -- hence escalation rather than either a forced Sell or a silent Hold.

## Bull case

The FDA/plant book is clean -- zero 483s at Hyderabad (Sep-2024), a single cleared observation at Atchutapuram (Jan-2025), no warning letters, no OAI, no import alerts on any source I checked, which meaningfully de-risks the single biggest tail-risk category in my sector coverage. The ARV-to-CDMO pivot is showing up in real numbers, not just a slide deck: CDMO revenue +43-50% YoY, quarterly CDMO run-rate roughly doubled in two years to Rs450-500cr, 110+ active projects and commercial shipments now flowing to top-15 global pharma names (Amgen cited by name), non-ARV FDF up sharply, and the legacy ARV book stabilizing at a guided ~Rs2,600cr run-rate rather than continuing to shrink. FY26 P&L converted this into ROCE recovering from 9.7% to 17.7%, EBITDA margin +6.7pts to 26.8%, and a Rs3,900cr multi-year capex program now largely behind the company rather than still consuming cash. Balance sheet is unstressed (D/E 0.475, interest cover >10x).

## Bear case

Valuation is the dominant risk and it is extreme by any cross-check: trailing P/E in the 95-113x range and P/B near 97x (multiple independent sources), richer than best-in-class CDMO comparables have historically commanded, for a company where two-thirds-plus of revenue still sits in the lower-multiple generic API/FDF/ARV business and management's own timeline has CDMO reaching only ~32% of revenue by FY28E. The quant engine's own growth_divergence_flag on this row is the tell: FY26's headline 23% revenue growth sits on a 3-year CAGR of just 4.09%, meaning a meaningful share of the 'growth story' currently being paid up for is a recovery off the 2022-24 ARV-destocking trough rather than a multi-year-proven secular CDMO growth line. Layer on my sector's structural risk -- FDA actions land with zero calendar warning (desk lesson, 2026-07) -- against a business now concentrating meaningful CDMO revenue with a small number of global-innovator clients, and a >90x multiple leaves almost no room to absorb an inspection surprise, a client-concentration shock, or simply a guidance miss against the 15-20% CAGR management itself has set as the bar.

## Valuation (reverse-DCF judgment)

RICH. At ~95-113x trailing earnings and ~97x book, the market is pricing Laurus as a hypergrowth CDMO pure-play years ahead of its own disclosed transition timeline (CDMO ~16% of revenue today, guided to ~32% by FY28E, ~50% ambition by FY29E). Even a generous decade-long 25% EPS CAGR (above management's own 15-20% revenue-CAGR guide, assuming margin-led EPS outgrows revenue) would take PAT from ~Rs889cr toward ~Rs8,300cr in ten years; discounted against a mature CDMO/pharma terminal multiple of ~25-30x, that path barely clears the current ~Rs84,000cr+ market cap and requires a full decade of uninterrupted execution with zero FDA disruption and zero client-concentration shock. ROE today (12.09% trailing, quant row) is not yet at a level that screams 'compounder' -- it is improving (ROCE 9.7%->17.7% YoY) but this is not a 25%+-ROE business today, so the >90x multiple is being paid for a transition story, not for demonstrated hypergrowth economics. Reasonable base case: multiple compression from here even if the operating guide (15-20% revenue CAGR, 28-30% margins) is delivered in full.

## Escalation

> [!warning] Escalated for Principal review
> Genuine Hold-vs-Sell tension the PM should personally weigh: operationally the business supports Hold (clean multi-year FDA record across all plants, credible and now-verifiable CDMO client wins including Amgen, ROCE inflecting up, clean balance sheet), but the stock trades at ~95-113x trailing earnings / ~97x book -- among the richest multiples in Indian pharma -- for a company whose 3-year revenue CAGR is still only 4.09% and whose CDMO mix-shift is management-guided to take until FY28-29 to mature. Combined with this desk's own lesson that FDA actions land with zero calendar warning, the asymmetry (a >90x multiple leaves essentially no cushion for an inspection surprise, a client-concentration event, or a guidance miss) is extreme enough that a valuation-driven Sell case is defensible even though I cannot force it under the V1 quant-Hold override rule. Recommend the PM decide whether position sizing/caps are warranted purely on valuation-risk grounds.

## Detailed rationale

[DATA] Laurus Labs is completing a multi-year pivot from a single-customer, PEPFAR/ARV-API-dependent generics business (which cratered on global ARV destocking in FY23-24) into a three-legged franchise: ARV APIs/FDF (management-guided run-rate of ~Rs2,600cr +/-200cr annualized), non-ARV generics/FDF (the fastest-growing sub-segment, +48% YoY in 9M FY26 FDF overall, with non-ARV FDF cited at +176% YoY in one broker note), and CDMO (small-molecule + Laurus Bio biologics, +43% YoY in 9M FY26 to ~Rs1,491cr, quarterly run-rate up from Rs220-250cr to Rs450-500cr over two years, 110+ active projects as of Mar-2025 including ramping shipments to Amgen). FY26 (Mar-2026 year-end, latest full-year print, matching the quant row's 'latest_qtr: Mar 2026') delivered revenue of Rs6,813cr (+23% YoY), EBITDA margin +6.7pts to 26.8%, and PAT of Rs888.79cr vs Rs233.67cr in FY25 (+280% by that math; one other source cites +148% for the same period -- the two do not reconcile and I flag this as a source discrepancy rather than resolve it by assumption). ROCE improved to 17.7% from 9.7% YoY per management's own release; the quant row's trailing ROE/ROCE (12.09%/18.84%) are in the same ballpark, difference likely a timing/basis artifact, not escalation-worthy. Q4FY26 (Rs1,811.57cr revenue, Rs282cr PAT) was a fourth straight sequential record quarter. Balance sheet is clean: D/E 0.475, interest coverage >10x, bs_flag GREEN -- a Rs3,900cr FY22-26 capex program (75% into API/CDMO capacity) is now largely behind the company and earning a return rather than a going-forward drag. Q1 FY27 (Jun-2026 quarter) has NOT yet been reported as of this write-up (2026-07-21) -- board meeting/results are scheduled for 2026-07-24, three days out; do not treat any pre-result stock-price commentary as an earnings print. FDA/plant record is clean for my sector's tail-risk lens: Hyderabad API unit cleared a Sep-2024 USFDA inspection with ZERO 483 observations; the Atchutapuram (Anakapalli) API Unit-4 inspection (27-31 Jan 2025) drew a Form 483 with ONE observation, since an EIR (Establishment Inspection Report) was issued for that facility -- no warning letter, no OAI classification, no import alert found in any source checked. A Dec-2023 inspection of a US-based Laurus arm drew 5 observations (stock -4% same day) but did not escalate to warning letter/OAI on any record found. Net: no repeat-site pattern, no active regulatory action -- a genuinely low-risk plant book relative to sector peers that have carried 483/OAI overhangs. Management's own forward guidance: 15-20% revenue CAGR over the next 2-3 years, 28-30% steady-state EBITDA margin, CDMO revenue share rising from ~16% currently to ~32% by FY28E and a stated ~50% ambition by FY29E.

## Sources

- Quant row: Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/results/full750_scored.csv (LAURUSLABS row, final_score_3y=44.82, final_score_1y=63.46, recommendation_overall=Hold)
- Laurus Labs FY26 full-year results press release - https://www.lauruslabs.com/Investors/PDF/PressReleases/PressRelease-Laurus-Labs-Announces-Full-Year-FY26-Results-Revenues-at-%E2%82%B96_813Cr_EBITDAat%E2%82%B91_826Cr_%2026.8_%20margins.pdf
- Laurus Labs Q4 profit rises to Rs279cr, FY26 revenue up 23% - https://www.indianpharmapost.com/news/laurus-labs-q4-profit-rises-to-rs-279-crore-fy26-revenue-up-23-20085
- Laurus Labs Q4 FY26: Margin Expansion Drives Strong Profit Growth - https://www.marketsmojo.com/news/result-analysis/laurus-labs-q4-fy26-margin-expansion-drives-strong-profit-growth-amid-volume-recovery-3972249
- Laurus Labs Q3 FY26: PAT Soars 388% - https://www.whalesbook.com/news/English/healthcarebiotech/Laurus-Labs-Q3-FY26-PAT-Soars-388percent-On-Robust-Revenue-Margin-Expansion/697a27c598511879499b056a
- Laurus Labs Surges on CDMO Momentum, But Valuation Concerns Linger - https://www.whalesbook.com/news/English/healthcarebiotech/Laurus-Labs-Surges-on-CDMO-Momentum-But-Valuation-Concerns-Linger/699fd6dccd95b9dc08f99fd6
- Laurus Labs: Scaling into a Global CDMO Growth Engine - https://www.fundsindia.com/blog/equities/alpha-laurus-labs-ltd-equity-research-desk/34319
- Laurus Labs bets big on CDMO as growth pushes margins higher in FY26 - https://www.businesstoday.in/amp/latest/corporate/story/laurus-labs-bets-big-on-cdmo-as-growth-pushes-margins-higher-in-fy26-528277-2026-04-30
- Laurus Labs zooms 53% in Q1FY27 (pre-result rally, Q1FY27 results due 2026-07-24, NOT yet reported) - https://www.business-standard.com/markets/news/laurus-labs-zooms-53-in-q1fy27-logs-sharpest-quarterly-rally-in-5-years-126063000621_1.html
- FDA CDER FOIA reading room, Laurus Labs Limited (Jan-2025 inspection/EIR) - https://www.fda.gov/drugs/cder-foia-electronic-reading-room/laurus-labs-limited-01312025
- Laurus Labs Hyderabad unit clears USFDA inspection, zero 483 (Sep-2024) - https://www.business-standard.com/markets/capital-market-news/laurus-labs-hyderabad-unit-clears-usfda-inspection-124091400506_1.html
- Laurus Labs' US arm receives Form 483 with one observation - https://www.bajajbroking.in/blog/laurus-labs-us-arm-receives-form-483-from-us-fda-with-one-observation
- Laurus Labs slips 4% as arm gets 5 observations post USFDA inspection (Dec-2023) - https://www.business-standard.com/markets/news/laurus-labs-slips-4-as-arm-gets-5-observations-post-usfda-inspection-123121300292_1.html
- Screener.in Laurus Labs consolidated financials (price/PE/EPS cross-check) - https://www.screener.in/company/LAURUSLABS/consolidated/

---
*Generated from `results/pf_qual_LAURUSLABS.json` — do not hand-edit; regenerate via `05_DATA_OFFICE/scripts/build_obsidian_book.py`.*
