# 08 — Forensics & Red-Flag Module (AMC-grade)

Purpose (brief Q18): behave like an AMC forensic desk — detect balance-sheet manipulation, revenue/earnings pre-recording, compliance/insider/related-party issues, and acquisition-driven obfuscation. Output a **forensic score + flag list** consumed by the scoring overlay (`02` Step 6). **No hard cutoffs** — severity scales with company size, regime, and the company's other strengths (brief Q11, Q13). Two lists: a short **hard-veto** list and a longer **heavy-penalty** list.

## A. Earnings quality & manipulation
- **Accruals (Sloan):** (Net income − CFO) / assets. High accruals → low-quality earnings → penalty.
- **CFO vs PAT divergence** over 3–5y: profits without cash = red flag (severity ↑ if persistent).
- **Beneish M-score** (8 ratios: DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA) → manipulation probability.
- **Montier C-score** (earnings-manipulation checklist) as a cross-check.
- **Piotroski F-score** used as a quality *support*, not a cutoff.
- Revenue-recognition flags: receivables growth ≫ revenue growth, unbilled/contract-asset spikes, quarter-end revenue bunching, channel stuffing (inventory-in-trade), round-number/too-smooth earnings.

## B. Balance-sheet integrity
- Debt structure: net-debt/EBITDA trend, interest-coverage, short-term/long-term mix, refinancing wall, hidden leverage (LC/bill-discounting/factoring, off-balance-sheet guarantees).
- **Contingent liabilities** vs net worth; corporate guarantees to group entities.
- Capex vs depreciation (gold-plating), **CWIP that never capitalizes** (perennial under-construction = cash siphon).
- Cash & investments reality (large cash + high debt = suspicious; cash parked in odd instruments/group entities).
- Goodwill/intangibles from serial acquisitions; impairment risk.

## C. Related-party & governance
- Related-party transactions: sales/purchases, loans & advances to promoters/group, rent/royalty/brand fees, as % of revenue/PAT and trend.
- Promoter **pledge** (level & trend), holding changes, preferential allotments/warrants to promoters at a discount.
- Auditor: quality/tenure, **resignation**, qualified/adverse opinion, frequent auditor changes, audit-fee anomalies, non-audit fees.
- Board: independence, related directorships, remuneration vs performance, key-management churn (CFO exits are a classic tell).
- Frequent equity dilution, complex holding structures, subsidiaries in odd jurisdictions.

## D. Compliance, insider & regulatory
- SEBI/ED/tax actions, class-action/major litigation, exchange penalties, ASM/GSM/surveillance stage.
- Insider trading (PIT disclosures), bulk/block deals, SAST — direction of promoter/insider/smart-money flow.
- Pledge invocations, credit-rating downgrades/watch, delayed filings.

## E. M&A / acquisition flags
- Serial acquirer with rising goodwill and no ROIC improvement.
- Acquisitions of related-party assets, overpayment, funding via dilution/debt, acquisitions that conveniently smooth or inflate reported growth.
- Reverse mergers, frequent restructurings, segment reclassifications that obscure trends.

## F. Anticipation / pre-recording
- Pre-recorded revenue/earnings patterns (pull-forward), aggressive capitalization of expenses, provision reversals timed to hit estimates, one-off "exceptional" items that recur every year.

## Severity model (context-scaled — the core of "no rigid rules")
```
flag_penalty = base_severity(flag)
             · size_mult(cap)          # microcap ≫ large-cap for the same flag
             · regime_mult(credit, valuation, trend)   # credit-scare/expensive/downtrend ⇒ ↑↑
             · offset(company_strengths)                # strong FCF/moat/cheap ⇒ ↓ (brief Q13)
```
- **size_mult:** a promoter pledge on a large, cash-generative leader ≠ the same pledge on a leveraged microcap.
- **regime_mult:** the mechanism behind "benign pledge in easy-credit uptrend → suicidal in a high-yield credit scare / overvalued / downtrend" (brief Q11).
- **offset:** genuine strengths can absorb a flag — but never a hard-veto flag.

## Hard-veto list (short; still evidence-checked, caps score deeply / forces ≤ −60)
- Auditor resignation or adverse/disclaimer opinion.
- Confirmed fraud / SEBI-ED fraud action / accounting restatement for fraud.
- Debt-covenant breach with going-concern doubt.
- (Microcap add) evidence of round-tripping / fabricated revenue.

## Heavy-penalty list (context-scaled, not fatal)
Promoter pledge trend, related-party bloat, CFO/PAT divergence, receivables/inventory anomalies, aggressive capitalization, serial dilution, CWIP-never-capitalizes, contingent-liability overhang, CFO/auditor churn, rating downgrade, governance weaknesses.

## Data & outputs
- Sourced from: screener.in (financials/shareholding/annual reports/concalls), BSE/NSE announcements & XBRL, annual reports (company sites), SEBI/exchange surveillance lists, rating agencies. See `09`.
- Emits per stock: `forensic_score`, `flags[] {flag, severity, veto|penalty, evidence, source}`. Consumed by `02` Step 6.
- Owner agents: **forensic/red-flag agent** + **compliance-farhan-qureshi** (firm) for regulatory reads; **red-team-nikhil-bose** stress-tests the "is this a fraud?" question on any high-conviction long.
