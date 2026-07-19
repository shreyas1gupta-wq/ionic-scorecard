# CA-GRADE FORENSIC RED-FLAG FRAMEWORK — ALPHA_RANKER
**Owner: compliance-farhan-qureshi. Purpose: FORWARD per-stock screening by analyst agents (deep-dive/equity-head desk), NOT a backtest.**
We do not hold historical granular Indian-filing disclosure records (RPT schedules, CARO text, auditor
opinions, ageing schedules) in any dataset — this is a **reading framework for the analyst desk to apply to
each company's actual Annual Report / auditor's report at the time of a forward deep-dive**, plus the narrow
slice that genuinely is computable today on `MASTER_fundamentals_pit.parquet`.

**Builds on, does not replace:** `08_FORENSICS_REDFLAGS.md` (existing hard-veto/heavy-penalty lists, severity
model `penalty = severity × size_mult × regime_mult`), `rnd/FRAMEWORK_CATALOG.md` §8, and `rnd/wave4/FORENSIC_METHODS.md`
(the authoritative statement of what `MASTER_fundamentals_pit` can and cannot compute — 34 `metric_norm` values,
**no receivables/inventory/payables/current-split/cash/intangibles/goodwill/gross-block line exists**, CFO on
only 749/4,613 symbols = 16%). Every DATA-SCREENABLE claim below is checked against that enumeration, not assumed.

**Epistemic tagging:** [DATA] = citing an actual, named Indian disclosure standard/regulation/clause that
genuinely requires this disclosure (Companies Act 2013, Ind-AS, CARO 2020, SEBI LODR, SEBI ICDR, SAs). Statute/
regulation numbers are stated as best-recollection of a real, currently-operative requirement — an analyst
citing these in a memo should confirm the live clause text against the current CARO/LODR/Ind-AS text before
using it as the sole basis for a HARD-VETO, per D-035 (no fabrication, verify before claiming). [INFERENCE] =
my reasoning about the MODUS OPERANDI / why the disclosure catches the fraud. [OPINION] = my severity/tier
judgment call, explicitly labeled as such and open to CIO/FM override per the existing severity model.

Severity tiers (same three-tier structure as `08_FORENSICS_REDFLAGS.md`, extended):
- **HARD-VETO** — caps score deeply / forces ≤ −60 regardless of other strengths, once the underlying fact is
  confirmed (not merely suspected) from the filing. Short list by design (existing-framework discipline).
- **HEAVY-PENALTY** — context-scaled (`size_mult × regime_mult`), material but not by itself disqualifying;
  escalates toward hard-veto when it co-fires with a second flag (non-additive `max + 0.5·second` rule already
  used for W4F penalties in `FORENSIC_METHODS.md` §F — the same shape applies here).
- **WATCH-FLAG** — lighter weight, monitor/trend item; on its own rarely moves the score, but is a leading
  indicator the analyst should track quarter-to-quarter and re-weight if it clusters with other flags.

**DATA-SCREENABLE tag on every item:**
- **DATA-SCREENABLE (full/partial-proxy)** — computable now from `MASTER_fundamentals_pit.parquet` fields, at
  least as a coarse level/trend proxy, without reading any filing text.
- **FILING-READ-ONLY** — the mechanism requires reading actual disclosure text (RPT note, CARO clauses, auditor
  opinion paragraph, ageing schedule, board's report) that does not exist as a structured field anywhere in our
  data; this is analyst-agent (equity-head / sector-analyst / fundamental-FM) reading work, not automatable today.
- **BLOCKED** — a sub-case of FILING-READ-ONLY worth flagging separately where even a coarse numeric proxy is
  impossible because the underlying line item (receivables, inventory, intangibles, contingent liabilities,
  gross block, cash) simply does not exist as a `metric_norm` in the dataset (confirmed enumeration, `FORENSIC_METHODS.md` §B).

---

## TIER 1 — HARD-VETO (11 items)

### RP-02 — Related-party loans/advances/guarantees, overdue or interest-free, to promoter/group entities
- **What it is:** Loans, advances, or guarantees extended to related parties (as defined by Ind AS 24 — entities
  under common control/significant influence, KMP, promoter-owned entities) that are overdue, interest-free, or
  rolled over with no realistic repayment plan.
- **MO [INFERENCE]:** Direct siphoning channel — cash leaves the listed entity as a "loan" that funds promoter
  lifestyle/other ventures and is never genuinely intended to be recovered; often dressed up as "business
  advance" or "ICD" to avoid the optics of a related-party loan.
- **Where to find it [DATA]:** Ind AS 24 related-party note (loans/advances given, terms, balance outstanding) +
  **CARO 2020 clause (iii)** — auditor must specifically report the terms, repayment schedule, and any overdue
  amount for every loan/advance/guarantee/security given to related parties (Section 189-register parties under
  Companies Act 2013), and separately opine whether terms are prejudicial to the company's interest. Also
  Sections 185/186 Companies Act 2013 (statutory limits + board/shareholder approval for loans to
  directors/other body corporates).
- **Severity:** HARD-VETO once CARO clause (iii) discloses overdue/non-commercial terms to a related party;
  HEAVY-PENALTY (see RP-01) if merely disclosed at commercial terms with no overdue flag. [OPINION]
- **Data:** FILING-READ-ONLY — `investments`/`borrowings`/`other assets` metric_norms exist at aggregate level
  only; no counterparty-identity tag exists to isolate the related-party slice.

### RP-03 — Circular transactions / round-tripping to inflate revenue
- **What it is:** Sham sales/purchases routed through related or connected entities and back, or cash advanced
  out (as "investment"/"loan") that returns disguised as "revenue" from a shell/connected customer — no real
  economic substance.
- **MO [INFERENCE]:** Manufactures revenue growth to support a stock price, a loan covenant, or an IPO/QIP
  pricing window; frequently paired with FA-02 (fictitious receivables) since the "sale" needs a debtor.
- **Where to find it [DATA]:** Cross-read of the Ind AS 24 RPT note against unusually large sales/other-income
  growth with non-conversion to cash; auditor commentary under **CARO clause (viii)** (undisclosed
  income/transactions not recorded) and **clause (xi)** (fraud noticed/reported). Existing framework already
  hard-vetoes this "(microcap add) evidence of round-tripping/fabricated revenue" — this document's addition:
  **do not restrict the veto to microcap.** Large/mid-cap round-tripping (e.g., via cross-shareholding webs) is
  the same mechanism and equally veto-worthy; cap-size only changes the base rate of suspicion, not the
  consequence once confirmed. [OPINION]
- **Severity:** HARD-VETO once credibly established (auditor qualification, SEBI/forensic-auditor finding, or a
  documented pattern of matched buy-sell legs with a connected party).
- **Data:** PARTIAL proxy only — CFO/PAT divergence (existing leg) and W4F-02 clean-surplus gap are consistent
  WITH round-tripping but cannot themselves confirm it; confirmation is FILING-READ-ONLY.

### PT-06 — Evergreening of loans
- **What it is:** A stressed borrower's overdue loan is kept "standard" by extending a fresh loan (directly, via
  a related lender, or via a restructuring) whose proceeds repay the old loan, with no genuine improvement in
  repayment capacity.
- **MO [INFERENCE]:** Delays NPA recognition / debt-covenant trigger, keeps the stock's leverage optics clean
  while true solvency deteriorates; mirrors the banking-sector "evergreening" definition RBI itself uses for
  lenders, applied here to the borrower side.
- **Where to find it [DATA]:** **CARO 2020 clause (ix)** — auditor must state whether the company has defaulted
  in repayment of loans/borrowings, AND whether term loans were applied for the purpose for which they were
  obtained (a "diverted for other purposes" finding is the direct tell); cross-read against `borrowings`
  metric_norm trend and rating-agency commentary (credit-rating downgrade/watch, already in existing framework §D).
- **Severity:** HARD-VETO once CARO clause (ix) or a rating agency's own report confirms evergreening/purpose-diversion.
- **Data:** FILING-READ-ONLY — `borrowings` (FULL universe, 48,983 rows) is a level only, carries no
  purpose-of-use or lender-identity tag.

### FA-01 — Fictitious cash/bank balances alongside high-cost debt (the Satyam pattern)
- **What it is:** Large reported cash/FD balances that either never existed, or are pledged/diverted while
  shown as free cash, sitting alongside genuine, expensive external borrowing the company services in parallel
  — the signature Satyam (2009) construction (₹5,040cr of cash on the books that a bank confirmation showed
  did not exist).
- **MO [INFERENCE]:** Fabricated cash plugs a hole left by siphoned funds or fabricated profits (the cash
  "backs" the fictitious profits reported elsewhere on the balance sheet); the confirming tell is that reported
  interest/other income on the cash balance is far too low for the balance shown, because there is no real
  interest-bearing deposit behind it.
- **Where to find it [DATA]:** BS "Cash and cash equivalents" / "Bank balances other than cash equivalents" note
  vs P&L "Other income" (interest-income sub-line) vs "Finance costs"; the actual confirmation mechanism is the
  auditor's **SA 505 (External Confirmations)** procedure — direct bank confirmation of balances, which is
  exactly the audit step Satyam's auditors were found to have skipped/fabricated.
- **Severity:** HARD-VETO once bank-confirmation mismatch or auditor finding surfaces; the low-yield screening
  pattern below (Data col) is HEAVY-PENALTY pre-confirmation, not itself a veto. [OPINION]
- **Data:** PARTIAL, DATA-SCREENABLE (coarse, NOT previously built) — `other income` (FULL, 49,352 rows) yield
  against `investments` + the cash-containing portion of `other assets` (FULL, 49,280 rows), compared against
  rising `interest` expense (FULL, 49,352 rows), is a computable coarse proxy: large asset base + low
  investment/other-income yield + rising interest expense = flag worth a filing read. **Recommend as a new
  buildable gate item** for the quant desk (not yet in `FORENSIC_METHODS.md`'s 6 W4F candidates) — flagging to
  quant-head-arjun-rao rather than building it myself (outside compliance charter). Confirming actual fictitiousness remains FILING-READ-ONLY.

### FA-02 — Fictitious/unrecoverable receivables (auditor-qualified)
- **What it is:** Revenue booked against trade receivables that do not exist, or exist but are structurally
  unrecoverable (shell/connected debtor, disputed, aged beyond any realistic collection window).
- **MO [INFERENCE]:** The natural companion to RP-03 — a round-tripped/fabricated sale needs a debtor on the
  books; channel-stuffing produces the same receivable-quality problem without needing a connected party.
- **Where to find it [DATA]:** BS "Trade receivables" note — **Schedule III (2021 amendment) mandates an ageing
  schedule** (<6mo / 6mo–1yr / 1–2yr / 2–3yr / >3yr, disputed vs undisputed split) — the single best public
  window into this problem since the amendment; Ind AS 109 expected-credit-loss (ECL) provisioning note; the
  confirming audit step is **SA 505** external debtor confirmation, same as FA-01.
  Severity is HARD-VETO specifically when the **auditor's report itself is qualified on receivable
  existence/recoverability** (a modified opinion, SA 705) — ageing deterioration alone without a qualification
  is HEAVY-PENALTY (see the general receivables discussion under EQ-02/W4F-03).
- **Severity:** HARD-VETO (auditor-qualified case only, as above).
- **Data:** BLOCKED — no receivables/debtors `metric_norm` exists in `MASTER_fundamentals_pit` at all (confirmed,
  `FORENSIC_METHODS.md` §B fact 1). The only numeric proxy anywhere in our data is W4F-03 (`other assets` growth
  vs `sales` growth, a lumped and coarse construction). FILING-READ-ONLY for anything precise, ageing, or auditor-opinion-linked.

### AG-01 — Auditor resignation mid-term
- **What it is:** The statutory auditor resigns before completing/signing an audit cycle, rather than issuing a
  qualified/adverse opinion.
- **MO [INFERENCE]:** The auditor sees something they are unwilling to certify and exits rather than sign —
  functionally a refusal-to-opine, often worse than a qualification because no specifics are locked into a report.
- **Where to find it [DATA]:** Companies Act 2013 **Section 140(2)** + **Form ADT-3** (resigning auditor must
  file the reason with the Registrar of Companies within 30 days) and **SEBI LODR Regulation 30** (material
  event, disclosed to exchanges, with a 2019 SEBI-circular tightening requiring the DETAILED reason, not a
  generic "personal reasons"/"other commitments" line).
- **CA-grade nuance this adds beyond the existing hard-veto line item:** read the actual ADT-3/exchange-filed
  reason text. "Pre-occupation with other assignments" is a materially different (weaker) flag than "unable to
  obtain sufficient appropriate audit evidence" or "non-cooperation of management" — treat the latter category
  as an even harder veto and escalate to CIO immediately regardless of any other analysis in progress. [OPINION]
- **Severity:** HARD-VETO (already in `08_FORENSICS_REDFLAGS.md` L52/L110 — restated here with the citation +
  the reason-text nuance).
- **Data:** FILING-READ-ONLY — no auditor field exists in `MASTER_fundamentals_pit` at all.

### AG-02 — Modified audit opinion (qualified / adverse / disclaimer)
- **What it is:** The statutory auditor's report itself carries a qualified, adverse, or disclaimer-of-opinion
  conclusion on the financial statements (or a specific line item).
- **Where to find it [DATA]:** Auditor's Report, "Basis for Qualified/Adverse Opinion" or "Basis for Disclaimer
  of Opinion" paragraph under **SA 705** (Modifications to the Opinion), which must state the specific line item
  and, where practicable, the rupee quantification of the misstatement.
- **CA-grade nuance:** do not conflate this with an **Emphasis of Matter** paragraph (**SA 706**) — an EOM draws
  attention to a matter (e.g., ongoing litigation, a going-concern note management has adequately disclosed)
  WITHOUT modifying the opinion itself, and is a materially lighter signal (see AG-02-EOM below, WATCH-FLAG).
  Analysts conflating "auditor added a paragraph" with "auditor qualified the accounts" systematically
  over-flag EOMs and under-flag the rarer, much more serious true modification. [OPINION]
- **Severity:** HARD-VETO (already in `08_FORENSICS_REDFLAGS.md` — restated with the EOM-vs-modification distinction).
- **Data:** FILING-READ-ONLY.

### AG-07 — Going-concern material uncertainty (SA 570)
- **What it is:** The auditor concludes there is material uncertainty about the company's ability to continue
  as a going concern and includes a dedicated "Material Uncertainty Related to Going Concern" section in the
  audit report.
- **Where to find it [DATA]:** **SA 570 (Going Concern)** — a distinct, more severe signal than a plain EOM;
  Schedule III also requires management's own going-concern assessment disclosure in the notes, which should be
  cross-read against the auditor's independent conclusion (a management note that says "no material uncertainty"
  contradicted by an auditor's own going-concern paragraph is itself a governance red flag).
- **CA-grade broadening beyond the existing rule:** the existing hard-veto line is "debt-covenant breach with
  going-concern doubt" — this item is broader: an SA 570 material-uncertainty paragraph is a HARD-VETO on its
  own, independent of whether a covenant breach specifically triggered it (going concern can arise from
  cash-flow projections, recurring losses, or working-capital deficits with no covenant in sight). [OPINION]
- **Severity:** HARD-VETO.
- **Data:** FILING-READ-ONLY.

### AG-08a — CARO 2020 clause (xi): fraud noticed or reported by the auditor
- **What it is:** The auditor's CARO annexure explicitly states whether any fraud by/on the company was noticed
  or reported during the year, and whether a report under **Section 143(12)** (mandatory fraud reporting to the
  Central Government/Audit Committee above a threshold) was filed.
- **Where to find it [DATA]:** CARO 2020, clause (xi); Companies Act 2013 **Section 143(12)** and **Section 447**
  (punishment for fraud) as the underlying statutory machinery.
- **CA-grade point:** this is close to the auditor's own written confession that fraud exists — it should be
  treated as at least as serious as, and a more precise citation than, the existing generic "confirmed fraud /
  SEBI-ED fraud action" hard-veto line, because it comes from the STATUTORY AUDITOR under a specific reporting
  duty, not merely a regulator's later action. [OPINION]
- **Severity:** HARD-VETO.
- **Data:** FILING-READ-ONLY — CARO text is not captured anywhere in our fundamentals dataset.

### AG-08b — CARO 2020 clause (ix): default in repayment of borrowings to banks/FIs
- **What it is:** The auditor's CARO annexure discloses whether the company has defaulted in repayment of loans
  or borrowings to a bank, financial institution, or debenture holder, with the period and amount of default.
- **Where to find it [DATA]:** CARO 2020, clause (ix)(a)-(f) (also covers whether the company is a "willful
  defaulter" and whether term-loan proceeds were used for their stated purpose — the latter sub-clause is the
  direct evergreening tell, see PT-06).
- **CA-grade distinction from the existing rule:** the existing hard-veto is "debt-covenant breach with
  going-concern doubt" — a covenant breach is a technical trigger inside a loan agreement (can be waived/cured
  quietly); an actual CARO-reported repayment DEFAULT is a harder, more public fact and should hard-veto even
  absent an explicit going-concern paragraph. [OPINION]
- **Severity:** HARD-VETO.
- **Data:** FILING-READ-ONLY.

### CO-04 — Off-balance-sheet control evasion (consolidation-scope avoidance)
- **What it is:** An entity the company genuinely CONTROLS (per the Ind AS 110 control test — power over
  relevant activities + exposure to variable returns + ability to use power to affect those returns, which is
  broader than simple >50% ownership) is kept OUTSIDE consolidation as a mere "investment"/"associate," keeping
  its debt/losses off the group balance sheet.
- **MO [INFERENCE]:** Classic leverage-hiding construction (the 2008-crisis-era SPV playbook, and seen in
  several Indian group-company collapses) — debt sits in a technically-non-consolidated vehicle the promoter
  effectively controls via board composition, off-take agreements, or puttable/convertible instruments that
  Ind AS 110 was specifically written to catch.
- **Where to find it [DATA]:** Consolidated financial statements' "basis of consolidation" note (Ind AS 110 /
  Ind AS 111 for joint arrangements / Ind AS 28 for associates), and the mandatory Schedule III list of "entities
  not consolidated, with reasons" — the reasons stated there are the exact thing to interrogate against the
  actual control facts (board seats, guarantee exposure, offtake terms).
- **Severity:** HARD-VETO once control is evident from the facts (board/guarantee/offtake) but consolidation is
  avoided on a technical ownership-percentage argument — this is precisely the accounting-standard violation
  Ind AS 110 exists to prevent. [OPINION]
- **Data:** FILING-READ-ONLY entirely — requires reading the consolidation-scope note and the non-consolidated-entity list.

---

## TIER 2 — HEAVY-PENALTY (context-scaled, not fatal; 16 items)

### RP-01 — Related-party sales/purchases at non-arm's-length pricing
- **What/MO [INFERENCE]:** Revenue or cost shifted to/from promoter-owned entities at off-market prices to
  manage reported margins, or to extract value at the operating-line level rather than via an overt loan.
- **Where [DATA]:** Ind AS 24 related-party note (nature and amount of every RPT category: sale of goods,
  purchase of goods, rendering/receiving of services, rent, royalty/brand fees); **SEBI LODR Regulation 23**
  (RPT policy, materiality threshold — a material RPT is one exceeding 10% of the listed entity's consolidated
  annual turnover or ₹1,000cr, whichever is lower, and requires audit-committee + shareholder approval with
  related parties abstaining from the vote) and **Regulation 23(9)** (half-yearly RPT disclosure to stock
  exchanges in the prescribed format — richer than the annual-report note alone).
- **Severity:** HEAVY-PENALTY; escalates toward HARD-VETO (RP-03) if pricing evidence or matched-leg pattern
  suggests round-tripping rather than genuine (if related) commerce. [OPINION]
- **Data:** FILING-READ-ONLY.

### RP-04 — Related-party transactions as % of revenue/PAT — level and trend
- **What/MO [INFERENCE]:** A rising RPT ratio signals the extraction channel is widening even without proof of
  any single abusive transaction — trend matters more than any one year's level.
- **Where [DATA]:** Same Ind AS 24 note + SEBI LODR Reg 23(9) filing; Board's Report often carries the
  aggregate RPT figure too.
- **Severity:** HEAVY-PENALTY, size-scaled (a given RPT ratio is far more dangerous for a small/microcap than a
  diversified large-cap conglomerate with genuine intra-group commercial logic — consistent with the existing
  size_mult framework).
- **Data:** FILING-READ-ONLY (revenue/PAT exist in our data, FULL universe, but the RPT numerator does not).

### PT-01 — Inter-corporate deposits (ICDs) to group/unrelated entities
- **What/MO [INFERENCE]:** Cash parked with a group NBFC/shell/connected party as an "ICD," often never
  genuinely returned or perpetually rolled — the ICD label itself is sometimes chosen specifically to describe
  a transaction that would otherwise have to be disclosed as a related-party loan.
- **Where [DATA]:** BS "Loans" / "Other financial assets" note; Ind AS 24; CARO clauses (iii)/(iv) (Section
  185/186 compliance for investments/loans/guarantees to other body corporates beyond prescribed limits).
- **Severity:** HEAVY-PENALTY; escalates to HARD-VETO tier (RP-02-style) if overdue/unrecoverable.
- **Data:** PARTIAL DATA-SCREENABLE (coarse only) — `investments` metric_norm is FULL universe (49,277 rows);
  a rising investments/total-assets ratio is a computable proxy for "cash leaving the operating business into
  something," but WHO the counterparty is (related vs genuine treasury deployment) is entirely FILING-READ-ONLY.

### PT-02 — Investments in unrelated/unlisted/shell entities
- **What/MO [INFERENCE]:** Diworsification or outright value diversion disguised as "strategic investment";
  unlisted/unquoted holdings are far harder for outside shareholders to verify or value.
- **Where [DATA]:** BS "Non-current investments" note — Schedule III requires a quoted-vs-unquoted split and
  aggregate market value of quoted investments, making a rising UNQUOTED share itself a screenable-from-the-note tell.
- **Severity:** HEAVY-PENALTY.
- **Data:** PARTIAL DATA-SCREENABLE (coarse) — same `investments` proxy as PT-01; the quoted/unquoted split and
  entity identity are FILING-READ-ONLY.

### PT-03 — Capex gold-plating / CWIP that never capitalizes
- **What/MO [INFERENCE]:** Capex invoiced through a related/connected EPC or equipment vendor at inflated cost;
  cash leaves the company as "capex" while the asset is never commissioned, or is commissioned at a fraction of
  its invoiced cost — a classic and well-documented mid-cap siphon mechanism.
- **Where [DATA]:** **Schedule III (2021 amendment) mandatory CWIP ageing schedule** — the single best public
  window into this fraud since the amendment: how much CWIP is <1yr / 1–2yr / 2–3yr / >3yr old, PLUS a specific
  "CWIP whose completion is overdue compared to its original plan" disclosure. Before 2021 this had zero public
  visibility; it is now the CA-grade addition that goes beyond the existing (already-caught) "CWIP-to-assets
  that never capitalizes" ratio.
- **Severity:** HEAVY-PENALTY on ageing/overdue-completion alone; escalates to HARD-VETO when the ageing
  schedule shows multi-year overdue completion combined with a related-party vendor (co-firing with RP-01/PT-01
  — non-additive escalation, consistent with the existing "two-flag" rule). [OPINION]
- **Data:** PARTIAL DATA-SCREENABLE — `cwip` metric_norm is FULL universe (49,274 rows), so CWIP level/trend vs
  total assets is already computable (and already exploited as the base for W4F-01 dep-laxity); the AGEING
  BREAKDOWN and vendor identity are FILING-READ-ONLY and are the genuinely new CA-grade layer here.

### PT-04 — Preferential allotment / warrants to promoters at a discount
- **What/MO [INFERENCE]:** Promoters raise their stake cheaply and dilute minority holders; warrants are
  sometimes used as a near-free option (forfeit the 25% upfront if the price moves against them, exercise if it
  moves in their favor) — a repeated pattern of forfeiture across cycles is itself the tell of using the
  instrument as a lottery ticket rather than a genuine capital-raise commitment.
- **Where [DATA]:** **SEBI ICDR Regulations, Chapter V** (preferential-issue pricing formula — for
  frequently-traded shares, the higher of the average of weekly high-low of the 90 trading days, or of the
  average high-low of the 10 trading days, preceding the "relevant date"; warrant rules require 25% consideration
  upfront with the balance payable within 18 months, forfeitable to the company on default); stock-exchange
  filing / postal-ballot notice for shareholder approval; Board's Report.
- **Severity:** HEAVY-PENALTY generally (WATCH-FLAG if priced at/above the statutory floor with no forfeiture
  history); escalates with a repeated forfeiture pattern.
- **Data:** FILING-READ-ONLY entirely.

### PT-05 — Subsidiary/associate shenanigans
- **What/MO [INFERENCE]:** Either direction of asset/value transfer between the listed parent and an unlisted
  subsidiary/associate at non-market terms — losses parked downstream to keep the listed entity's optics clean,
  or (the more dangerous direction) profitable assets/contracts transferred DOWN into an unlisted entity where
  the promoter holds a larger private stake than in the listed parent.
- **Where [DATA]:** Consolidated FS notes (Ind AS 27/28/110/111); **SEBI LODR Regulation 24** — governance of
  "material" unlisted subsidiaries (at least one common independent director on the subsidiary's board; the
  subsidiary cannot dispose of assets amounting to more than 20% of its own assets in the preceding FY without
  prior approval of the LISTED parent's shareholders by special resolution); CARO commentary on subsidiaries/associates.
- **Severity:** HEAVY-PENALTY; escalates to HARD-VETO with documented below-fair-value transfer to a
  promoter-controlled unlisted entity.
- **Data:** FILING-READ-ONLY — would require comparing standalone vs consolidated statements line-by-line, not
  available in our (standalone-oriented) fundamentals dataset.

### FA-03 — Unverifiable intangibles/goodwill from acquisitions, never impaired
- **What/MO [INFERENCE]:** Overpaying for acquisitions creates large goodwill that functions as a receptacle for
  otherwise-unexplained value transfer to the seller (frequently a related party); management then avoids the
  P&L hit of impairment even when the acquired business demonstrably underperforms.
- **Where [DATA]:** **Ind AS 103** (Business Combinations — goodwill = consideration paid less fair value of
  net identifiable assets acquired, at the acquisition date); **Ind AS 36** (Impairment — goodwill is one of the
  few assets requiring a MANDATORY ANNUAL impairment test regardless of whether any impairment indicator
  exists); BS "Goodwill"/"Other intangible assets" note + impairment-testing note (discount rate, growth
  assumptions, headroom disclosed); CARO clause (i)(e) (revaluation of PPE/intangibles disclosure).
- **Severity:** HEAVY-PENALTY generally; escalates toward HARD-VETO when goodwill/net-worth is large AND the
  segment note shows the acquired business destroying value over multiple years with zero impairment booked
  (itself close to an audit-opinion-worthy fact pattern). [OPINION]
- **Data:** BLOCKED — no intangibles/goodwill `metric_norm` exists in `MASTER_fundamentals_pit` (confirmed,
  `FORENSIC_METHODS.md` §C: "Capitalization-of-expenses via rising INTANGIBLES" = BLOCKED-BY-MISSING-METRIC).
  FILING-READ-ONLY entirely.

### AG-03 — Small/unknown auditor for a large or complex company
- **What/MO [INFERENCE]:** Promoters shop for a compliant small/regional firm unlikely to push back, especially
  right after a large-firm resignation (AG-01) — the combination of the two events in the same year is one of
  the best-documented fraud-precursor patterns observed in Indian markets.
- **Where [DATA]:** Auditor's Report signature block (firm name + firm registration number, cross-checkable
  against ICAI's records and, where applicable, NFRA's list of firms under scrutiny).
- **Severity:** HEAVY-PENALTY standalone; escalates toward HARD-VETO when it directly follows a large/Big-4-style
  auditor's resignation in the same or prior year (co-fires with AG-01). [OPINION]
- **Data:** FILING-READ-ONLY.

### AG-06 — Independent-director and CFO churn
- **What/MO [INFERENCE]:** An ID or CFO resigning, especially with a terse "personal reasons" letter that
  market chatter contradicts, usually means they refused to sign off on something rather than a genuine
  personal-circumstance departure.
- **Where [DATA]:** Board's Report (directors' changes with stated reasons), Form DIR-12 (RoC filing), and
  **SEBI LODR Regulation 30** disclosure of the resignation with detailed reasons (the same 2019-circular
  tightening applied to director/CFO resignations as to auditor resignations under AG-01).
- **Severity:** HEAVY-PENALTY per instance; escalates with clustering (2+ exits within a short window is
  HARD-VETO-adjacent and should be escalated to CIO immediately per the compliance charter, even before the
  rest of the deep-dive is complete).
- **Data:** FILING-READ-ONLY.

### AG-08c — CARO 2020 clauses (vi)/(vii)/(xvii): cost records, statutory-dues arrears, cash losses
- **What/MO [INFERENCE]:** Clause (vi) — cost records not maintained where mandated; clause (vii) — arrears in
  statutory dues (PF, ESI, GST, income-tax, customs, excise, cess) outstanding for more than six months, a
  direct and fairly hard-to-fake cash-stress signal; clause (xvii) — cash losses incurred in the current and/or
  immediately preceding financial year.
- **Where [DATA]:** CARO 2020, clauses (vi), (vii), (xvii) of the auditor's annexure.
- **Severity:** HEAVY-PENALTY; statutory-dues arrears (vii) is the single most reliable of the three as a
  genuine distress signal (companies rarely risk PF/GST default without real cash stress) and should be
  weighted higher within this bucket. [OPINION]
- **Data:** FILING-READ-ONLY.

### AG-09 — Promoter pledge level/trend and traceable fund-use
- **What/MO [INFERENCE]:** Pledge itself (already in the existing framework) is a leverage/distress proxy; the
  CA-grade addition is tracing what the PLEDGE-RAISED funds were used for — the more dangerous pattern is
  pledge proceeds flowing into an ICD/RPT (co-firing with PT-01/RP-01), i.e., the promoter borrowing against
  the listed company's own shares to fund a related-party siphon elsewhere.
- **Where [DATA]:** **SEBI LODR Regulation 31** (promoter/promoter-group shareholding and encumbrance disclosed
  within 2 working days of any creation/invocation/release of pledge, plus a standing quarterly disclosure).
- **Severity:** HEAVY-PENALTY on level/trend (already in existing framework); escalates to HARD-VETO-adjacent
  on pledge INVOCATION (a forced sale by the lender is direct, confirmed evidence of distress, not a proxy) or
  where use-of-proceeds is traceable to an ICD/RPT. [OPINION]
- **Data:** FILING-READ-ONLY — no promoter-shareholding/pledge field exists in `MASTER_fundamentals_pit`.

### CO-01 — Ballooning contingent liabilities
- **What/MO [INFERENCE]:** Real liability exposure kept off the recognized balance sheet by continuing to argue
  the outflow is only "possible," not "probable" (the Ind AS 37 recognition threshold) — understates true
  leverage/risk even with full technical disclosure compliance.
- **Where [DATA]:** Schedule III-mandated "Contingent Liabilities and Commitments" note under **Ind AS 37**,
  split by category (disputed direct/indirect tax, guarantees given, claims not acknowledged as debts, other
  commitments); the CA-grade read is the note's TREND vs net worth, not the single-year level.
- **Severity:** HEAVY-PENALTY, escalating with size vs net worth and with adverse court/tribunal news-flow on
  the specific disputes named in the note.
- **Data:** BLOCKED — no contingent-liability `metric_norm` exists in the dataset. FILING-READ-ONLY.

### CO-02 — Promoter/group guarantees given by the company
- **What/MO [INFERENCE]:** The listed company's balance sheet guarantees an unlisted/promoter-owned entity's
  borrowing — effectively a hidden capital call on minority shareholders if the guarantee is ever invoked.
- **Where [DATA]:** Same Ind AS 37 contingent-liability note (guarantees given, disclosed separately) + CARO
  clause (iv) (Section 185/186 compliance — guarantees to related parties beyond prescribed limits need
  board/shareholder approval and specific disclosure of the terms).
- **Severity:** HEAVY-PENALTY; escalates to HARD-VETO tier when guarantee/net-worth is large AND the guaranteed
  entity is promoter/group-owned and independently known to be financially weak.
- **Data:** FILING-READ-ONLY.

### EQ-01 — Capitalized interest that should have been expensed
- **What/MO [INFERENCE]:** Excessive/aggressive capitalization of borrowing costs into CWIP (rather than
  expensing through the P&L) inflates current-period PAT; this is a distinct face of the same siphon story as
  PT-03 when the underlying capex never converts to a revenue-generating asset — interest capitalized on an
  asset that is never actually commissioned is money that never should have left the P&L.
- **Where [DATA]:** **Ind AS 23 (Borrowing Costs)** — interest on borrowings specifically funding a "qualifying
  asset" under construction must be capitalized, and the note discloses the quantum capitalized in the year.
- **Severity:** HEAVY-PENALTY; escalates when capitalized-interest/total-interest ratio is high AND CWIP
  conversion is stalled (co-fires with PT-03 — non-additive escalation).
- **Data:** BLOCKED — no separate capitalized-interest `metric_norm` exists; the `interest` field in
  `MASTER_fundamentals_pit` (FULL universe) is presumably the net P&L expense figure and cannot be
  disaggregated to recover the capitalized portion. FILING-READ-ONLY.

### EQ-02 — Aggressive revenue recognition (Ind AS 115 judgment areas)
- **What/MO [INFERENCE]:** Pulling revenue forward via aggressive percentage-of-completion / over-time
  recognition estimates (the highest-judgment area of Ind AS 115, concentrated in EPC/real-estate/long-contract
  businesses), or switching the recognition method/policy year-on-year without a compelling change in the
  underlying business (Ind AS 8 governs accounting-policy changes) — a policy switch timed near a weak quarter
  is itself a tell.
- **Where [DATA]:** **Ind AS 115** (5-step model: contract → performance obligations → transaction price →
  allocation → recognition on satisfaction), specifically the over-time-vs-point-in-time judgment disclosed in
  "significant accounting policies"; **Ind AS 8** for any disclosed change in accounting policy/estimate.
- **Severity:** HEAVY-PENALTY generally; escalates to HARD-VETO if the auditor specifically qualifies revenue
  recognition (folds into AG-02 in that case, not double-counted).
- **Data:** BLOCKED for the precise mechanism (no unbilled-revenue/contract-asset/percentage-of-completion
  field exists); the only numeric proxy anywhere in our data is the existing W4F-03 (`other assets` growth vs
  `sales` growth) — coarse and already built. FILING-READ-ONLY beyond that proxy.

---

## TIER 3 — WATCH-FLAG (lighter weight; monitor and re-weight on clustering; 5 items)

### AG-02-EOM — Emphasis of Matter paragraph alone (SA 706), no modified opinion
- **What/MO [INFERENCE]:** The auditor draws attention to a disclosed matter (litigation, a going-concern note
  management has itself adequately disclosed, a subsequent event) without modifying the opinion — a materially
  lighter signal than AG-02's true modification, but worth tracking because EOM topics repeated across
  consecutive years (e.g., the same litigation, never resolved) suggest the "possible not probable" judgment in
  CO-01/CO-03 may be stretched.
- **Where [DATA]:** **SA 706** (Emphasis of Matter and Other Matter Paragraphs).
- **Severity:** WATCH-FLAG; escalates only if the same EOM topic repeats 3+ years running or is later followed
  by an actual modification/going-concern paragraph.
- **Data:** FILING-READ-ONLY.

### AG-04 — Low or anomalous audit fee, non-audit-fee conflict
- **What/MO [INFERENCE]:** A fee too low for the scale/complexity of the audit implies a token/rubber-stamp
  engagement; the sharper cross-check is audit-fee vs NON-audit fee paid to the same network — a large
  non-audit fee alongside a small audit fee creates the exact independence conflict Indian audit-reform debates
  (post-Satyam, post-IL&FS) have repeatedly flagged.
- **Where [DATA]:** Board's Report / AGM notice "Remuneration to Auditors" note, which discloses the audit fee
  and separately the fee for other services to the same network.
- **Severity:** WATCH-FLAG standalone; HEAVY-PENALTY if non-audit fee exceeds audit fee to the same network.
- **Data:** FILING-READ-ONLY.

### AG-05 — Delayed/postponed quarterly or annual results
- **What/MO [INFERENCE]:** Repeated board-meeting deferrals to approve results usually signal a
  management-auditor standoff over a specific number, or a scramble to complete an internal/forensic/special
  audit before disclosure — a leading indicator that something is being contested behind the scenes.
- **Where [DATA]:** **SEBI LODR Regulation 33** (quarterly results due within 45 days of quarter-end, annual
  within 60 days of year-end) and **Regulation 30** disclosure of the reason for delay.
- **Severity:** WATCH-FLAG for a single, explained delay; escalates to HEAVY-PENALTY (and toward HARD-VETO) with
  a second consecutive delay or if it coincides with an auditor change (AG-01/AG-03).
- **Data:** FILING-READ-ONLY.

### CO-03 — Disputed tax demands, especially transfer-pricing-related
- **What/MO [INFERENCE]:** Not itself fraud, but a pattern of large, repeated disputed tax demands — especially
  transfer-pricing additions touching related-party pricing — mirrors the same aggressive-positioning mindset
  that shows up in aggressive revenue recognition (EQ-02) and RPT pricing (RP-01); worth tracking as a
  correlated tell, not a standalone flag.
- **Where [DATA]:** Same Ind AS 37 contingent-liability note, income-tax vs indirect-tax split; Ind AS 12
  (deferred tax) note may show a large unrecognized deferred-tax asset/liability tied to the same dispute.
- **Severity:** WATCH-FLAG generally; HEAVY-PENALTY specifically when transfer-pricing-related (ties directly
  to RP-01) or when demand size vs net worth is large.
- **Data:** FILING-READ-ONLY.

### EQ-03 — Other-income dependence (qualitative breakup read)
- **What/MO [INFERENCE]:** Propping up a weak operating quarter with one-off gains (asset sales, FX marks,
  investment write-backs) labeled "exceptional" each time despite recurring every year; the CA-grade point is
  to actually READ the other-income breakup note rather than trust the aggregate ratio, because a genuine
  treasury-income-heavy NBFC/holding company looks identical to this ratio without being a red flag at all —
  context (is the company an operating industrial business or a genuine investment holding company?) governs
  whether this fires at all.
- **Where [DATA]:** P&L "Other Income" note breakup — Schedule III requires the breakup (interest, dividend,
  profit on sale of investments/assets, FX gain, "miscellaneous") and a large unexplained "miscellaneous/other"
  residual is itself worth a specific question to management/IR.
- **Severity:** this mechanism is **ALREADY-COVERED at the quantitative level** by the existing W4-04 leg
  (OI/PBT level + ΔOI-share, `FORENSIC_METHODS.md` §C) — do not re-propose a new quant signal here. The
  WATCH-FLAG this document adds is purely the qualitative instruction: read the breakup note before trusting
  the ratio, and treat genuine investment/holding companies as an explicit exception rather than a false positive.
- **Data:** DATA-SCREENABLE (already running) for the quantitative leg — `other income` + `profit before tax`
  both FULL universe (49,352 rows). The breakup-note qualitative read remains FILING-READ-ONLY.

---

## Summary count (also see `forensic_checklist.json` for the machine-readable version)

| Tier | Items |
|---|---|
| HARD-VETO | 11 |
| HEAVY-PENALTY | 16 |
| WATCH-FLAG | 5 |
| **Total** | **32** |

| Data-screenability (per `forensic_checklist.json` `data_screenable` field) | Items |
|---|---|
| Y — fully screenable now, quantitative leg already running | 1 (EQ-03, = existing W4-04 leg) |
| PARTIAL — coarse level/trend proxy exists, confirmation still needs a filing read | 5 (RP-03, PT-01, PT-02, PT-03, FA-01) |
| N — FILING-READ-ONLY, no numeric proxy possible even coarsely | 26 |

**Note on the DATA-SCREENABLE count:** every "PARTIAL" item is screenable only as a coarse, un-confirmed LEVEL
or TREND proxy on aggregated fields (`investments`, `cwip`, `other assets`, `other income`, `interest`) — none
of them can confirm the actual fraud mechanism (related-party identity, ageing, purpose-of-use, auditor
opinion). Treat every "PARTIAL" tag as a lead for the analyst-agent's filing read, never as a stand-alone
verdict. This mirrors the exact caution already established in `FORENSIC_METHODS.md` for W4F-03 (asset-buildup
proxy) and W4-04 (other-income leg). Six items are BLOCKED even at the coarse-proxy level because the
underlying line item does not exist in `MASTER_fundamentals_pit` at all: FA-02 (receivables), FA-03
(intangibles/goodwill), CO-01 (contingent liabilities), EQ-01 (capitalized interest), EQ-02 (exact
recognition mechanism beyond the W4F-03 proxy), and CO-04 (consolidation-scope facts).

## Recommendation to the quant desk (compliance flagging, not building)
FA-01's low-yield-cash-vs-high-interest-expense construction is a genuinely new, buildable, full-universe
coarse gate item not currently in the 6 W4F candidates or in `FRAMEWORK_CATALOG.md` §8. I am flagging it to
**quant-head-arjun-rao** for consideration as a 7th forensic-lane candidate; building/testing it is outside
this compliance charter and must go through the normal Gate-3/cheap-test process before any score impact.

## Filed / distribution
This document + `forensic_checklist.json` live in `ALPHA_RANKER/rnd/forensic/`. Consumed by: equity-head
coordinating the analyst desk, fm-fundamental-sanjay-kulkarni (forensic-gated entries), and compliance
(this desk) for periodic audit that the analyst desk's deep-dives actually cite the checklist items rather than
generic "looks clean" assertions. No hard cutoffs are self-executing — every HARD-VETO still requires the
underlying fact to be genuinely confirmed from the filing, consistent with `08_FORENSICS_REDFLAGS.md`'s
"no rigid rules, severity scales with context" governing principle.
