# MG07 — Verification Protocol: Third-Party Quarterly Fundamentals Vendor (2005–present, ~2000 Indian companies, with announcement dates)

Model: Sonnet 5. Task: design a concrete pre-adoption verification protocol (not principles).

Owner if run for real: Data Officer (Kavya Reddy), gated by D-009 (new-source sample verification), sign-off requires CEO+CIO joint approval (D-025) before any Gate-4 backtest use, plus a mandatory LOOKAHEAD_CONTROLS T1–T10 pass and one-day-lag test before the data touches a strategy.

---

## Phase 0 — Intake & schema sanity (before any statistics)

1. Ingest raw vendor files into a quarantine path (`05_DATA_OFFICE/_quarantine/vendor_fundamentals_v1/`), never the live `datasets/` tree.
2. Schema dump: row count, column list, dtypes, null-rate per column, min/max per numeric column, distinct-value count per categorical column (company_id, exchange, sector).
3. Key uniqueness check: is (company_id, fiscal_period_end, statement_type) unique? Count and dump any duplicate keys — duplicates alone are a hard flag, not just a warning.
4. Unit declaration check: does the vendor state units (₹ crore / lakh / absolute) per column, and is it consistent across all rows of the same column? Cross-tab units-field vs order-of-magnitude of the values themselves.
5. Identifier mapping: build company_id → ISIN/NSE-symbol/BSE-code crosswalk; check it against our existing `NIFTY500_TICKER_2005_2025_Final.xlsx` PIT ticker snapshots and `india_fundamentals_mc/Train.parquet` identifiers. Log unmatched vendor IDs and unmatched firm-side IDs separately — both are informative (vendor-only names = coverage claim to test; firm-only names = potential coverage gap).

Exit gate for Phase 0: schema is well-formed and identifiers are mappable for ≥95% of rows, or the whole dataset is rejected before any sampling effort is spent.

---

## Phase 1 — Sampling design (three tiers, not one blanket sample)

**Tier A — Hand-picked "golden" set (n=30 companies, full history 2005–present, every quarter, manually reconciled).**
Composition, chosen to stress the exact failure modes we care about:
- 10 large, stable, well-covered names (RIL, TCS, HDFC Bank, ITC, Infosys, L&T, HUL, SBI, Bharti Airtel, ICICI Bank) — sanity baseline, easiest to verify against multiple public sources.
- 8 names with known corporate-action complexity: mergers (HDFC Ltd→HDFC Bank 2023, Vodafone-Idea 2018, Sun Pharma-Ranbaxy 2015), demergers (Reliance Industries→Jio Financial 2023), name changes.
- 7 names with known fraud/distress/delisting events: Satyam Computer Services (2009 fraud/restatement), Kingfisher Airlines (delisted 2013), DHFL (2019 default/restatement), IL&FS group entities, Jet Airways (2019), Reliance Communications (2019 insolvency), Yes Bank (2020 reconstruction).
- 5 recent-IPO names to test the "2005-present" claim honestly: Zomato/Nykaa/Paytm/Mankind Pharma/IdeaForge — first data row must not predate actual listing/first public filing.

**Tier B — Stratified random sample for automated cross-check, n=400 company-quarters.**
Stratify by: (a) market-cap decile at the time (using historical mcap, not current), (b) calendar year bucket (2005-09, 2010-14, 2015-19, 2020-25 — four eras), (c) sector (11 NSE sectors), (d) exchange listing status (still-listed vs delisted/merged/suspended). Draw proportionally, minimum 2 per (era × cap-decile) cell so thin cells aren't skipped. n=400 targets a ±5% margin of error at 95% CI for a binary accuracy metric on a population this size — enough to make an accept/reject call, not enough to certify every cell, hence Tier A fills the gaps Tier B statistically can't reach.

**Tier C — Full-population automated internal-consistency scan.** No external source needed; runs on every row. Described in Phase 4.

---

## Phase 2 — Cross-checks against independent sources (accuracy of the numbers themselves)

For Tier A (full history) and Tier B (sampled quarters), pull the SAME company-quarter from at least one independent source and diff on 5 anchor line items: Revenue, EBITDA, PAT, Total Assets, Shareholders' Equity.

Independent sources, in priority order (use whichever is actually reachable given our proxy/network constraints):
1. Actual filed result PDF / XBRL from NSE (`nsearchives.nseindia.com` corporate-announcements/financial-results archive) or BSE corporate announcements — the ground truth, used for 100% of Tier A.
2. Screener.in exported financials (public, free, widely cross-checked) for Tier B automation.
3. Our existing `india_fundamentals_mc/Train.parquet` (excluding the known-corrupt `annual_report` column) as a third opinion where overlap exists.

Procedure:
1. Compute `pct_diff = abs(vendor_value - reference_value) / abs(reference_value)` per line item per company-quarter.
2. Tabulate: % of rows within 1%, within 5%, within 10%, and >10% deviation, per line item, per era, per market-cap decile.
3. Flag and manually adjudicate every case >10% deviation — classify root cause: unit error (lakh/crore), restatement timing difference, consolidated-vs-standalone mismatch, or genuine vendor error.
4. Specifically test consolidated-vs-standalone confusion (a classic Indian-data trap): confirm the vendor's `statement_type` field is populated and consistent — silently mixing standalone and consolidated numbers across quarters for the same company is a fail even if each individual number is "correct."

---

## Phase 3 — Point-in-time announcement-date verification (the part that actually protects the backtest)

This is the highest-priority phase — a wrong number is a data-quality issue, a wrong date is a silent lookahead bug that fabricates alpha.

1. **Ground-truth timestamp pull.** For every Tier A company-quarter and the full Tier B sample (430 company-quarters total), pull the actual exchange filing timestamp (date, and time-of-day where the exchange archive provides it — NSE corporate-announcements does carry a submission time) for the "Financial Results" filing from `nsearchives.nseindia.com` / BSE corporate announcements archive.
2. **Exact-match test.** Compare vendor's `announcement_date` to the true exchange filing date.
   - `vendor_date < true_filing_date` → **hard fail, single-instance kill trigger.** This is definitionally lookahead: the vendor claims data was public before it was. Even one confirmed instance triggers full-dataset quarantine and a forensic re-audit of the vendor's entire date-generation methodology before any further sampling is trusted.
   - `vendor_date == true_filing_date` → pass.
   - `vendor_date > true_filing_date` by 1–3 trading days → soft flag (processing lag, not lookahead, but still means the vendor's PIT claim is imprecise — tag for buffer treatment).
   - `vendor_date > true_filing_date` by >3 trading days, or missing → coverage/date-quality fail for that row.
3. **Time-of-day / pre-market vs post-market test.** Where the exchange gives a submission time, classify each filing as pre-market-open, during-market, or post-market-close. If the vendor's field is date-only (no time), we cannot assume same-day availability for post-market filings — enforce a T+1 trading-day floor on that company-quarter regardless of what the vendor date says, consistent with our existing daily-candle stamping landmine (#8 in DATA_QUALITY_RULES).
4. **Fixed-offset pattern test (the classic vendor-cheat detector).** For every company-quarter in the full population (not just the sample), compute `offset_days = announcement_date - fiscal_quarter_end_date`. Group by offset value and look for suspicious mass clustering — e.g., if a large fraction of ALL companies across ALL sectors show `offset_days` exactly 45 or exactly 60 with near-zero variance, that is strong evidence the vendor is **computing** a placeholder disclosure date (regulatory deadline) rather than recording the real filing date. Real filing dates should show a wide, sector/company-specific, right-skewed distribution (SEBI's 45-day-from-quarter-end / 60-day-from-year-end are outer *deadlines*, not typical filing dates — most large-caps file well before the deadline). Threshold: if >10% of the population sits at a single fixed offset value with the exact same offset firm-wide, reject the date field outright even if individual sampled dates in Tier A happened to check out.
5. **Weekday / trading-holiday plausibility test.** Cross the `announcement_date` against the NSE trading-holiday calendar. Indian boards do genuinely meet on Saturdays sometimes, so Saturday dates aren't automatically wrong — but any `announcement_date` falling on a Sunday or a gazetted NSE holiday, with no evidence of an actual board meeting that day, is a red flag for an interpolated/estimated date rather than a real filing timestamp. Tabulate the rate of "impossible day" dates across the full population.
6. **Event-study confirmation test.** For the 30 Tier-A names plus a further ~50 large-surprise events pulled from the Tier B sample (biggest |PAT YoY surprise| quarters), compute abnormal return and abnormal volume in the window [-3, +3] trading days around the vendor's `announcement_date`, using the market model vs NIFTY 500. A genuinely point-in-time date should show the statistically significant reaction concentrated ON day 0 (or day 0/+1 for post-close filings), not before it. If abnormal reaction systematically precedes the vendor's stated date by 1+ days across many events, the true public disclosure date is earlier than what's recorded — meaning the field is unreliable in the direction that would make a backtest optimistic in a way that's easy to miss because it looks "safe" (the data would falsely seem to arrive later, not earlier — but it means the vendor's dates can't be trusted for precise event-window strategies either way).
7. **Restatement-lookahead test.** For Tier A distress/fraud names (Satyam, DHFL, IL&FS, Yes Bank) where financials were later restated, check whether the vendor dataset (a) preserves the originally-reported (pre-restatement) numbers under the original announcement date and separately versions the restated numbers under the restatement's own later announcement date, or (b) silently overwrites history with restated figures under the OLD date. (b) is a T-class lookahead bug per our taxonomy (the backtest would "know" restated truth before it was public) and is an automatic fail for those company-quarters, with a scan across the full population for any other known restatement events to check the same pattern isn't systemic.

**Numeric bar for this phase alone:** date exact-match rate must be ≥95% on the combined 430-row Tier A+B sample, zero confirmed vendor-date-precedes-true-date instances, fixed-offset clustering <10% of population, "impossible day" rate <2%, and the event-study test must show no systematic pre-announcement-date reaction. Any one of these failing outright routes to REJECT regardless of how good the number-accuracy results from Phase 2 were.

---

## Phase 4 — Coverage and survivorship-bias detection

1. **PIT-membership cross-check.** For every year 2005–2025, take the NIFTY 500 PIT constituent snapshot from `NIFTY500_TICKER_2005_2025_Final.xlsx` (42 snapshots) and check: for every ticker that was IN the index in year Y, does the vendor have at least one reported quarter for that ticker in year Y? Compute the miss rate per year. A rising miss rate in earlier years (2005-2012) is expected to be somewhat higher but should not exceed a hard ceiling (see acceptance rule below); a miss rate that's flat-zero in early years alongside a suspiciously complete company roster is itself suspicious (see check 3).
2. **Known-dead-company roster check.** Explicit list, checked by name: Satyam Computer Services, Kingfisher Airlines, Unitech, DHFL, IL&FS group (IL&FS, IL&FS Financial Services, IL&FS Transportation), Jet Airways, Reliance Communications, Reliance Capital, Videocon Industries, Bhushan Steel, Bhushan Power & Steel, Alok Industries, Amtek Auto — for each, confirm the vendor (a) has data up through the last quarter the company actually reported, and (b) does NOT forward-fill/carry-forward values after delisting/insolvency admission (a common lazy-vendor bug that fakes survivorship by pretending dead companies kept reporting flat numbers).
3. **Company-count time series.** Plot count of distinct companies with at least one reported quarter, by calendar year, 2005–2025. Expected shape: growing from a few hundred (~2005, reflecting the actual listed-and-covered universe of that era) toward ~2000 in recent years. Two failure shapes to specifically test for:
   - **Flat-high-count-from-day-one** (near 2000 companies already covered in 2005) → strong survivorship-bias signal: the vendor likely built today's universe of ~2000 currently-active companies and backfilled their history, silently excluding companies that existed and later died/delisted before the vendor's own universe was assembled. This is the single most damaging failure mode for backtests (it deletes exactly the bankruptcies and blowups a strategy needs to see) and should be checked with real teeth — cross the company-count series against actual historical NSE/BSE listed-company counts by year (public exchange fact sheets) to see if the vendor's curve tracks the real market's cross-sectional universe or just today's survivors projected backward.
   - **Sudden cliffs** at specific years (e.g., count halves in one year with no macro reason) → vendor onboarding/licensing gap, not a real universe change.
4. **IPO-boundary check.** For a sample of ~20 companies that IPO'd in the last 8 years (Zomato, Nykaa, Paytm, IdeaForge, Mankind Pharma, CarTrade, etc.), confirm the first vendor data row is at or after the actual listing date / first public filing — any data claimed before the company was a public reporting entity is fabricated by definition (private pre-IPO financials sourced through DRHP/prospectus have a wholly different, much-later public-availability timeline than "quarterly results" and must be date-flagged separately if included at all).
5. **Merger/demerger continuity check.** For the Tier A merger events (HDFC→HDFC Bank, Vodafone-Idea, Sun Pharma-Ranbaxy, Reliance-Jio Financial demerger), confirm the disappearing entity's series terminates correctly and isn't silently spliced into the surviving entity's numbers (which would corrupt both the disappearing entity's "death" and the surviving entity's organic growth history).
6. **Sector-count stability check.** Cross sector classification counts per year against known NSE sector-index histories; large unexplained sector-composition shifts point to a reclassification or backfill artifact rather than real market structure change.

---

## Phase 5 — Internal statistical consistency (runs on the FULL population, no external source needed)

1. Balance-sheet identity: `Total Assets ≈ Total Liabilities + Equity` within 1% tolerance; compute violation rate across all rows.
2. Cross-statement tie-out: quarterly net income vs implied change in retained earnings (adjusted for dividends/buybacks where disclosed) — flag gaps beyond a materiality threshold for manual review.
3. YoY and QoQ growth z-scores on Revenue/EBITDA/PAT per company; flag |z|>8 for manual adjudication (near-always a unit or consolidation-scope error, not real economics).
4. Units-plausibility cross-check: for each company, compare reported Revenue magnitude against that company's known market cap at the time (rough sales-to-mcap sanity band by sector) — catches lakh/crore mislabeling that a simple within-column check would miss.
5. Duplicate/conflicting-row detection: identical (company, quarter) keys with materially different values and no version/vintage flag distinguishing them.
6. Impossible-value scan: negative revenue, negative total assets, zero/negative shares outstanding, EPS inconsistent with PAT/shares-outstanding by more than rounding.

---

## Quarantine / Acceptance Rules

| Result bucket | Trigger conditions (ALL must hold for that bucket; any single hard-fail overrides everything) | Disposition |
|---|---|---|
| **ACCEPT (unrestricted)** | Date exact-match ≥95% (n≥430 sample); zero confirmed vendor-date-precedes-true-date cases; fixed-offset clustering <10% of full population; impossible-weekday rate <2%; event-study shows no pre-date reaction leakage; 5-line-item match to independent source ≥97% within 2% tolerance; balance-sheet violation rate <1%; PIT-membership miss rate <3% per year in every year from 2010 on (pre-2010 allowed up to 8% given genuinely thinner historical disclosure); all 13 known-dead names correctly terminate with no forward-fill; company-count curve tracks real historical listed-universe shape (no flat-from-day-one signature) | Promote out of quarantine into `05_DATA_OFFICE/`, write `DATA_CATALOG.md` entry (vendor, coverage, verification date, sample sizes, known caveats), run full LOOKAHEAD_CONTROLS T1–T10 pass + one-day-lag test before first backtest use, CEO+CIO joint sign-off logged (D-025) |
| **QUARANTINE (restricted, buffered use only)** | Date exact-match 85–95%, or PIT-membership miss rate 3–8% (post-2010), or line-item match 90–97%, or minor version/consolidation-flag inconsistencies found but explainable — and NO hard-fail condition present | Usable ONLY with a firm-wide mandatory T+2 (or T+3 if any post-close-timing ambiguity found) extra lag buffer stacked on top of the vendor's own date, tagged "restricted — buffered PIT" in DATA_CATALOG, restricted to research/exploration (no Gate-4 certification, no capital-adjacent use), scheduled re-audit in one quarter with a fresh independent sample |
| **REJECT (do not ingest / kill adoption)** | ANY of: one or more confirmed vendor_date < true_filing_date instances; fixed-offset clustering ≥10% of population; restatement silently back-dated for any tested distress name; company-count curve shows flat-from-day-one survivorship signature; any of the 13 known-dead-company checks shows forward-filling past actual death; balance-sheet violation rate >5%; line-item mismatch >15% vs independent source | Full dataset rejected, written up as a killed-adoption entry with reasons (so it isn't re-proposed without new evidence), vendor relationship not pursued further absent a vendor-side methodology fix and a fresh from-scratch re-sample |

Approval gate note: this is a new external data source under D-025 — quarantine-to-accept promotion requires CEO+CIO joint sign-off regardless of how clean the numbers look; the verification results above are the evidence packet that sign-off is conditioned on, not a substitute for it.

---

## Post-acceptance monitoring (don't stop after go-live)

1. Rolling re-sample: every quarter, pull a fresh random 50 company-quarters (not overlapping prior samples) and re-run Phases 2–3 at reduced scale — vendors silently change backfill/estimation methodology over time, and a one-time pass at intake doesn't catch that.
2. Any new confirmed vendor_date < true_filing_date instance found post-acceptance triggers immediate suspension of the dataset from all active backtests pending re-audit, not just a note for next quarter.
3. Log every quarterly re-check result in `DATA_CATALOG.md` under this source's entry so decay in vendor data quality is visible over time, same discipline as the existing edge-decay cadence for strategies.
