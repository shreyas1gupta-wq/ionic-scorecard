# CIO FINAL — Verification Protocol for a Third-Party Quarterly Fundamentals Vendor
**Indian equities, vendor-claimed 2005-present, ~2000 companies, with announcement dates**
Consolidated by: Rajan Mehta (CIO, E-001). Inputs: Arjun Rao (Head of Quant) draft protocol + Nikhil Bose (Red Team, E-014) adversarial review.
Filed: 2026-07-14.

---

## VERDICT
**REJECT-by-default → the dataset is QUARANTINED on arrival and the realistic terminal state is CONDITIONAL, not ACCEPTED-PIT.** Most Indian fundamental vendors ship a single-vintage snapshot with no separate knowledge/vintage date; per our own logic that caps them at CONDITIONAL forever, however clean the announcement dates look. ACCEPTED-PIT is reachable only if the vendor demonstrably carries a vintage dimension AND clears the full battery below including the five red-team flips. We plan around CONDITIONAL and treat ACCEPTED-PIT as the exception we have to be argued into.

**Rationale (3 lines):**
1. The draft is a sound skeleton that reliably catches the fakes that have already burned this firm (quarter-end dates as availability — landmine #3; celebrity-death survivorship) but fails-open on a competently constructed fake in five specific ways Nikhil identified. I adopt all five fixes as binding.
2. The two questions that decide everything are unchanged from the draft's self-named crux: (a) does `announcement_date` mark when the FIRST-reported number became public, not when a LATER-restated number was retro-stamped; (b) does the graveyard exist where it actually lives — the ~1500 small/micro-caps, not the 10 famous corpses.
3. Data-verification sign-off (Data Officer + Quant) is necessary but NOT sufficient: ADOPTING a source is a D-025 gate (CEO+CIO joint) and a red-team pass is a precondition for any backtest-eligible label.

**Tail-risk assessment (why the CIO cares about a data question):**
- *Worst single-day analogue:* none directly, but a lookahead-contaminated fundamentals feed manufactures phantom edge that sizes real capital into names with no true signal — the loss shows up later, all at once, correlated across every strategy that drank from the same well. This is a portfolio-of-strategies tail, not a single-position tail.
- *Worst-month / correlated-blowup scenario:* a survivorship-clean-looking-but-actually-biased CONDITIONAL set seeds biased HYPOTHESES that then get "confirmed" on a clean source and pass gates. Every value/quality sleeve built on it shares the same hidden bias and de-rates together. This is exactly our institutional failure mode (the FF debit-denominator and the 17-month gap that faked "positive every year") reappearing one layer upstream, in the data itself.
- *Unpriced left tail:* a 2-day-early or post-close-timestamped announcement date legalizes precisely the information a PEAD/earnings-drift strategy trades on. The backtest looks great; live it is a coin flip. That gap is the tail.

---

## THE PROTOCOL (consolidated — draft phases, red-team fixes baked in)

### PHASE 0 — INTAKE, IMMUTABILITY, STAGING (gate before anyone opens it)
- **0.1** Land the raw delivery in `05_DATA_OFFICE/_quarantine/<vendor>/<delivery_date>/`, no write access from research code, **no DATA_CATALOG entry yet** (uncatalogued = not backtest-eligible, by definition).
- **0.2** SHA-256 every raw file; manifest = file list, row count, byte size, min/max dates. This frozen artifact is what we test, and every future re-delivery is hash-diffed against it so silent vendor restatements of history are *detected, never absorbed*.
- **0.3** Vendor data dictionary in writing, answer before touching rows:
  - (a) **Is the panel bitemporal?** Is there a KNOWLEDGE/VINTAGE date distinct from fiscal-period-end and announcement date? *No vintage dimension ⇒ cannot be truly PIT for any restated field ⇒ CONDITIONAL ceiling.* This is the headline expectation, not a footnote (fixes the draft burying M6).
  - (b) Consolidated vs standalone, flagged per company-quarter?
  - (c) Per-share fields as-reported-at-the-time, or retro-adjusted for later splits/bonuses (itself a lookahead hazard)?
- **0.4** Schema/sanity sweep (scripted, ~0 tokens): dtypes, null map by column and by year, primary-key uniqueness. **Key must be ISIN or a permanent internal id — never the trading SYMBOL** (Indian symbols get reused on merger/rename → pulls the wrong company's history).

### PHASE 1 — VALUE ACCURACY — with the red-team's power + sector fixes
- **1.1 Sampling (RE-SPEC per R1/C2):** draw the accuracy sample **RANDOMLY, seeded, reproducible, and PRE-REGISTERED before any value is seen**, from the full key population — **not** 60–80 hand-stratified cells. Size it to the coverage claim: **n ≈ 250+ for a ±2% CI**. Keep era/size/sector as *post-hoc reporting strata* (so we can see where errors concentrate), not as the sampling frame. Report the error rate **with a confidence interval**. The old ">3% of ~70 cells" line had no statistical power — at n≈70 you cannot distinguish a 3% from a 6% true error rate.
- **1.2 Ground truth = primary source, weighted first (R8):** the NSE/BSE corporate-announcement / results PDF for that board meeting is the ONLY truly independent check (we have verified NSE-archive + board-meeting access, 370+ downloads). Compare sector-correct line items (see 1.4).
- **1.3 Our own PIT parquet is SECONDARY and possibly CIRCULAR (R8):** `datasets/earnings_pit/unified_quarterly_pit.parquet` shares likely upstream lineage (Capitaline/exchange/MCA) with the vendor; agreement is an echo, not corroboration. Use it only on its **exact-date subset** (it is 86.2% exact `available_date`); never demand ±2-day agreement against its 13.8% approximate dates.
- **1.4 Sector-correct line-item maps (R4/C-fix):** the manufacturer template (Revenue, PAT, EPS, Total Assets, Total Equity, Borrowings) is a category error for financials — which this very protocol over-weights as highest-risk. Use per-format maps: **bank** (Total Income = NII + other income, deposits ≠ borrowings, provisions, GNPA), **NBFC**, **insurance** (premiums, claims), **manufacturer**, **holding co** — each verified against the company's actual filed schedule.
- **1.5 Unit & sign traps:** one consistent unit (₹cr vs lakh vs mn) via magnitude/market-cap plausibility; a known loss quarter shows negative PAT; a known negative-net-worth name (stressed NBFC/telco) reports negative equity, not its absolute value.
- **1.6 Consolidated/standalone basis** matches the company's HEADLINE-reported basis; a silent mix fabricates every ratio time series.

### PHASE 2 — ARE THE ANNOUNCEMENT DATES GENUINELY POINT-IN-TIME (the crux)
- **2.1 Impossibility test (AUTO-REJECT):** any non-trivial count of `announcement_date < fiscal_period_end` = fabricated/placeholder date. Hard fail.
- **2.2 Quarter-end collapse / constant-lag test (AUTO-REJECT):** material share of `announcement_date == period_end`, or a perfectly constant lag for every row (always +45d, always the 15th) = synthetic (landmine #3). Hard fail.
- **2.3 Lag-distribution test — DEMOTED to supporting evidence (R5):** compute `announcement_date − period_end`; genuine Indian filings cluster ~30–60d post period-end, right-skewed, ~0 mass before ~15d (Q4/annual longer than Q1–Q3). Use the shape as evidence, not a gate — "the distribution shifts at LODR-deadline changes" is over-confident (companies file near, not at, deadlines) and can false-fail real data. **Replace the vague claim with ONE clean natural experiment:** the **COVID-2020 SEBI relaxation** extended Q4FY20/Q1FY21 deadlines ~45 days — genuine data shows a visible rightward blob mid-2020; constant-lag fabricated data will not. Test that specific window.
- **2.4 Calendar-realism test — corrected (R6):** cross announcement dates against the NSE trading/holiday calendar, but **flag only Sundays and gazetted exchange holidays above a mass threshold**. Indian companies legally hold and file on **Saturdays** (and exchanges have run Saturday sessions) — "weekend = fake" would false-fail real data.
- **2.5 Independent date cross-check — ASYMMETRIC tolerance (R2/R3/C3/C4):** compare vendor `announcement_date` to the exchange board-meeting/result-outcome filing date (primary) and to the parquet's exact-date subset (secondary).
  - **Early side: ZERO tolerance.** `vendor_date` earlier than the true filing date = lookahead = fatal. Even 2 days early is the entire PEAD edge.
  - **Late side: lenient.** Later than true filing = conservative/lossy = safe.
  - **Post-close / T+1 convention pinned explicitly:** results filed after market close on day T are tradable only at T+1 open. Determine and document whether the vendor's date means "known by close of announcement_date" or "known by next open," verify against a sample of known post-close filers, and **enforce a conservative T+1 gate in every backtest regardless of the vendor's claim.** This T-class leak hides inside any symmetric ±1–2 day band.
  - Frequency-dependent: a quarterly-rebalanced value screen can tolerate a day of lateness; anything trading the announcement cannot tolerate any earliness.
- **2.6 Field-availability granularity test:** P&L headline is in the quarterly result; full balance sheet / cash flow / segment / auditor notes usually arrive with the ANNUAL report — LATER. If every field on a quarterly row carries the SAME (early) availability date, the vendor is stamping later-available data as early-available. Genuine PIT gives BS/CF fields their own, later stamp.
- **2.7 RESTATEMENT-BLEED test — OPERATIONALIZED (M5), the definitive PIT test:** at the ORIGINAL announcement date, does the vendor carry the FIRST-reported number or the LATER restated one? **Connect this directly to the Phase-1.2 primary pull:** extract the AS-ORIGINALLY-REPORTED figure from the results PDF filed at the announcement date and compare to what the vendor carries there. Without that link the test is untestable. Targeted sub-samples with known first-vs-restated gaps: IND-AS transition 2016-17; **audited-Q4-vs-unaudited-Q4** and audited-FY vs unaudited-standalone divergences (M4 — Indian Q1–Q3 are unaudited/limited-review, Q4 often filed unaudited first); documented accounting restatements. If restated values appear at the original date, "PIT" is contaminated with the future. No vintage dimension (0.3a) ⇒ assume bleed until proven otherwise. **This test decides ACCEPTED-PIT vs CONDITIONAL.**

### PHASE 3 — COVERAGE COMPLETENESS — with denominator reconciliation (M1)
- **3.1 Universe-ramp test — CALIBRATED, not asserted (R7):** plot distinct companies per quarter 2005→present. A flat ~2000 across 20 years is a backfill/survivorship signature; genuine ACTIVE coverage ramps. BUT calibrate against a **known listed-count time series** — the ramp is real for NSE-active/reporting names, NOT for raw BSE listings (~4000+ in 2005, many illiquid/suspended). Do not flag a legitimately broad-but-illiquid 2005 panel, or excuse a backfilled one, from assumption.
- **3.2 Field fill-rate by era:** modern disclosures (segment, consolidated splits, ESG-adjacent) must be sparse pre-2010 and fill in; uniformly-high fill back to 2005 = backfilled/estimated, not filed.
- **3.3 Membership recall (large-cap floor only):** for each of our 42 PIT NIFTY500 snapshots, fraction of alive constituents with a contemporaneous-quarter row. Expect ≥95% large-cap. **This is a floor, not the survivorship test** — survivorship barely lives in the top 500 (R1/C1).
- **3.4 DENOMINATOR / row-count reconciliation (M1 — our recurring burn):** compute EXPECTED company-quarters = Σ over quarters (listed & active names, from an independent listing master) and compare to non-null vendor rows. **Report fill as a fraction of the theoretical panel.** "2000 companies since 2005" can be a 40%-empty matrix. This is the exact class of artifact behind the FF debit-denominator and the 17-month gap that faked "positive every year."
- **3.5 Per-company gap scan:** list quarters with no row while the company was listed and active; concentrated gaps by era/sector = fail.

### PHASE 4 — SURVIVORSHIP — FULL-UNIVERSE, not celebrities (R1/C1, the strongest attack)
- **4.1 Independent FULL-UNIVERSE delisting master (RE-SPEC):** build/obtain an independent PIT **listing+delisting master for all ~2000 names** — NSE/BSE historical listing master and/or MCA struck-off cross-reference — NOT a 500-name index and a ~10-name celebrity list. Real Indian survivorship bias is a **small/micro-cap** phenomenon: the 200+ obscure compulsory-delistings, SEBI suspensions and vanished SME/NBFC names of 2011–2019. A vendor that keeps its famous corpses (Kingfisher, Jet, IL&FS, DHFL, RCom, Yes Bank) to look legit while quietly dropping the small dead PASSES the old 4.1 and 3.3. This is the highest-impact miss.
- **4.2 Death-count test against the master:** each name must be present with data running up to its death, then stopping. Count securities whose last row precedes the present but NOT due to the data cutoff. A real 20-year Indian panel shows **hundreds** of such terminations, concentrated in small-caps. ~0 mid-history terminations = survivor panel = **AUTO-REJECT**.
- **4.3 Identity-continuity test:** track a name through a rename/merger/amalgamation — history continuous under one permanent id, not broken/duplicated. Broken identity = both survivorship AND reused-symbol lookahead.

### PHASE 5 — CORPORATE ACTIONS & UNITS — plus zero/null + fiscal-year (M2, M3)
- **5.1 Split/bonus test:** on a known split, does as-reported EPS/BVPS jump discontinuously (raw, acceptable for PIT if flagged) or is it back-adjusted? If back-adjusted, the factor must use ONLY splits up to the availability date — retro-adjusting old EPS by a FUTURE split is lookahead.
- **5.2 Reconciliation:** EPS × shares ≈ PAT; face-value/currency consistent across the split boundary.
- **5.3 ZERO-vs-NULL audit (M2 — fundamentals analog of the 0.00-price untraded-strike landmine):** audit every numeric field for implausible exact zeros; confirm **missing = null, not 0**. A silent 0 debt / 0 EPS fabricates a whole ratio series (P/E on EPS=0, D/E=0).
- **5.4 Non-March fiscal-year handling (M3):** banks, Dec-year-end MNCs, 15-month transition companies exist. Verify `period_end` is the COMPANY's true fiscal-period end and run ALL date tests (2.1/2.2/2.3, calendar) **conditional on it** — a mislabel against Mar-31 turns every date test to garbage or false fails.

### PHASE 6 — CANARY — DEMOTED to a placebo-pair diagnostic, NOT an acceptance gate (R1/C5)
The canary cannot discriminate a genuine date from a constant-lag fake: `period_end + fixed 45d` still withholds 45 days of drift versus gating at `period_end`, so a one-sided compare "passes" a synthetic date. Remove it from the ACCEPTED-PIT decision. Replace with the **D-028 placebo pair** (Sameer/Nikhil to run):
- (a) **One-day-lag test:** lag `announcement_date` +1 trading day; if the canary edge collapses, the edge lives on the announcement bar — timing-fragile / leak-prone.
- (b) **Date-shuffle placebo:** shuffle `announcement_dates` within each company to break the date↔value link; the edge must go to ~0. If it survives the shuffle, the "signal" isn't coming from the dates — something else is leaking (e.g. values ordered by future outcome).
The real discriminators remain 2.5 (independent primary-source cross-check, asymmetric) and 2.7 (restatement bleed). The canary is a necessary sanity check, never their equal. Diagnostic only — its output is never a quotable result and runs inside the sealed sandbox, still quarantined.

---

## QUARANTINE STATE MACHINE & ACCEPTANCE RULES

**States**
- **QUARANTINED** (default on arrival): staging only, no research/backtest read access, no catalog entry.
- **CONDITIONAL** (EDA/exploration only, banner attached, NEVER feeds a certifiable backtest or a quoted metric): passes Phase 0 + Phase 1 (powered accuracy) + Phase 3 (coverage) — but dates unproven or **no vintage dimension** (2.7 unresolved). *This is the expected terminal state for most vendors.*
- **ACCEPTED-PIT** (backtest-eligible): passes the FULL battery incl. Phase 2 (dates genuine, asymmetric tolerance met, T+1 pinned, no restatement bleed), Phase 4 (full-universe graveyard present), plus the Phase 6 placebo pair clean. Requires DATA_CATALOG entry (source, lineage, hash, coverage/denominator map, known limitations) AND the governance sequence below.
- **REJECTED:** any hard-fail; document reason, keep hashes, notify FM + CIO.

**HARD-FAIL / AUTO-REJECT (any one)**
- Any `announcement_date < period_end` (2.1).
- Material share of exact-period-end or perfectly-constant-lag dates (2.2).
- Restatement bleed: restated values at the original announcement date (2.7).
- **`vendor_date` earlier than true filing on ANY cell of the date cross-check (zero early-side tolerance, 2.5).**
- Survivor panel: known deaths absent from the FULL-universe master, or ~0 mid-history terminations (4.1/4.2).
- Value error-rate CI whose lower bound exceeds the acceptance threshold (1.1) — judged on the interval, not a point estimate.
- Silent zeros standing in for nulls that flow into ratios (5.3).

**NUMERIC ACCEPTANCE THRESHOLDS (for ACCEPTED-PIT)**
- Headline value match: error rate with a ±2% CI whose **upper bound ≤ 3%**, zero unit/sign errors, on the pre-registered n≈250+ random sample.
- Date agreement vs independent primary source: **zero early-side violations**; late-side within tolerance appropriate to the intended rebalance frequency, on ≥90% of the sample; T+1 convention pinned and enforced.
- Lag distribution 30–60d, right-skewed, ~0 mass ≤0d, and the **COVID-2020** window shows the expected rightward blob (supporting evidence).
- Large-cap recall ≥95% (floor); FULL-universe death count consistent with a real 20-yr panel (hundreds), every death present up to its death.
- Denominator fill reported as a fraction of the theoretical panel with era/sector gap map.

**GOVERNANCE SEQUENCE (G1, G2 — binding, corrects the draft)**
Verification is NOT adoption. Sequence:
1. Verification pass (Data Officer Kavya Reddy + Quant Arjun Rao) →
2. **Mandatory red-team pass** (Nikhil Bose runs the placebo pair + attacks the sample) — precondition for any backtest-eligible label →
3. **CEO + CIO JOINT adoption approval (D-025 gate; tie → Principal)** →
4. DATA_CATALOG entry (with git-pinned verification report) →
5. Only then ACCEPTED-PIT.
**CONDITIONAL-leakage firewall (G3):** no hypothesis whose plausibility depends on the CONDITIONAL data's biased dimension (coverage/survivorship/dates) may advance a pipeline gate without **independent re-derivation on a clean source.** A biased CONDITIONAL set generates biased hypotheses that then get "confirmed" — we do not let priors leak through the banner.

**ONGOING (post-acceptance)**
- Every re-delivery hash-diffed against the frozen manifest; any change to HISTORICAL rows = silent restatement = **re-quarantine that vintage, do not overwrite** (D-030 freeze for anything already in a forward test).
- Re-run 2.1 / 2.2 / 4.2 / denominator reconciliation on each refresh as cheap regression.
- Dataset acceptance does NOT exempt a strategy: any backtest citing it still passes its own LOOKAHEAD AUDIT PASS (one-day-lag test, LOOKAHEAD_CONTROLS T1–T10) and enforces the T+1 gate.

---

## SIZING RULING
Not applicable in the position-sizing sense — this is a data-adoption decision. The operative ruling is a **capital-exposure ruling**: no capital, paper or live, may be sized off any signal derived from this dataset until it is ACCEPTED-PIT via the full governance sequence. CONDITIONAL data may inform exploration and hypothesis generation ONLY, behind the G3 firewall, with a banner on every artifact.

## KILL CRITERIA + REVIEW DATE
- **Kill (reject the vendor):** any AUTO-REJECT above trips → REJECTED, hashes retained, FM+CIO notified.
- **Review date:** verification battery to complete within one delivery cycle of intake; re-verification regression on every re-delivery; full re-audit if the vendor changes upstream provider or schema.

## DISSENTS (recorded by name)
- **Nikhil Bose (Red Team, E-014):** protocol verdict FRAGILE, not FAKE — skeleton sound, self-named crux correct; flips to ADEQUATE only with all five fixes (powered/random/sector-correct accuracy sample; full-universe survivorship master; asymmetric date tolerance + T+1; canary demoted to placebo pair; denominator + zero/null + non-March-FY + CEO/CIO adoption + red-team gate). **CIO ADOPTS all five as binding** — no residual dissent; his refutations are now protocol clauses.
- **Arjun Rao (Head of Quant, E-):** authored the skeleton; agrees the crux (first-reported vs retro-stamped restated; no-vintage ⇒ CONDITIONAL) is the weakest assumption to attack first. No dissent on the consolidated version.
- No standing dissent remains. Data Officer + Quant + Red Team + CIO aligned; CEO co-approval pending at the adoption gate.

---
*CIO note for the file:* the single sentence to remember — **verification tells us if the data is honest; it does not make the data PIT.** Absent a vintage dimension, the honest label is CONDITIONAL, and we build the firm's fundamental research plan around that, not around the hope of ACCEPTED-PIT.
