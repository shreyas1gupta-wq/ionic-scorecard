# MG07 — Verification Protocol for a Third-Party Quarterly Fundamentals Dataset (Indian Equities)

**Author:** Opus (Model Grid MG07) · **Owner on adoption:** Kavya Reddy (Data Office) · **Gate:** D-033/D-009 new-source, JOINT CEO+CIO approval (D-025) · **Date:** 2026-07-13

**Vendor claim under test:** quarterly fundamentals, 2005-present, ~2000 Indian companies, *with announcement dates*.

**Governing rule:** No row of this data touches a backtest, a register entry, or a quoted number until it has passed every phase below AND a LOOKAHEAD AUDIT PASS (D-028, `lib/lookahead_audit.py`). Default posture = **QUARANTINED**. The burden of proof is on the vendor, not on us. We assume the announcement dates are wrong until proven point-in-time, because that is the single failure that silently manufactures alpha.

---

## Phase 0 — Intake, isolation, and schema audit (before any statistics)

**0.1 Physical quarantine.** Ingest to `05_DATA_OFFICE/quarantine/vendorQ_fundamentals/` only. It is NOT added to `DATA_CATALOG.md` as usable, NOT importable by any script under `04_RND_LAB/`. Add a guard in `lib/guards.py` that raises if any path under `quarantine/` is opened by a backtest module. It stays here through Phases 1-6.

**0.2 Freeze a vintage.** Snapshot the exact delivered files with a SHA-256 manifest (`manifest.sha256`) and the delivery date. All verification runs cite this hash. If the vendor re-delivers mid-verification, the clock restarts (mirrors D-030 freeze logic).

**0.3 Schema census (script, ~0 tokens to chat).** Emit a digest per file: row count, column list + dtypes, per-column null %, per-column distinct count, min/max, and the identifier scheme. Specifically resolve:
- **Identifier stability.** What is the primary key — a permanent security ID, ISIN, NSE/BSE symbol, or company name? Symbols and names get REUSED and REASSIGNED in India (ticker recycling, merger renames). If the key is a mutable symbol, that is a coverage/survivorship landmine flagged now.
- **The three critical date columns must all exist and be distinct:** (a) fiscal **period-end** date, (b) **announcement/result** date (board-approved results filed with the exchange), (c) vendor **ingest/last-modified** date if present. If the vendor ships only period-end and a single "date," treat announcement dates as ABSENT → this is the T3 earnings-lookahead landmine (CLAUDE.md #3) and the dataset is presumptively FAIL until they supply real filing dates.
- **Restatement handling.** Is there a vintage/version column, or does the vendor overwrite in place? Overwrite-in-place = restated numbers backfilled onto the original date = lookahead. Flag now, test in Phase 4.
- **Units and scale.** ₹ lakh vs ₹ crore vs ₹ mn; consolidated vs standalone; audited vs unaudited. Mixed scale within a column is a known corruption pattern.

**0.4 Corruption sniff.** Per the local landmine (CLAUDE.md #5, `india_fundamentals_mc` `annual_report` col corrupt at source): scan every text/blob column for encoding garbage, and every numeric column for impossible values (negative shares outstanding, revenue > ₹100 lakh cr, EPS with 6+ decimal noise). Quarantine any column that fails; do not silently drop rows.

**Phase-0 kill condition:** no genuine announcement-date column, or the primary key is an unstable symbol with no crosswalk → **REJECT** (or send back to vendor) before spending effort on later phases.

---

## Phase 1 — Value accuracy against independent ground truth

Goal: are the *numbers* right, before we even ask if the *dates* are right. Two wrongs (wrong number on wrong date) are indistinguishable from noise otherwise.

**1.1 Stratified sample of 120 (company × quarter) cells.** Not random-uniform — stratify to hit the failure surface:
- 30 large-cap, liquid, well-covered (NIFTY50 members at the time) — should be trivially correct; failures here mean systemic problems.
- 30 mid/small-cap (rank 200-500) — where vendors interpolate or guess.
- 20 across the **2008-09 and 2020 stress quarters** — where restatements and delayed filings cluster.
- 20 **early era (2005-2008)** — the thinnest, oldest, most-likely-fabricated coverage.
- 20 **corporate-action quarters**: bonus/split (per-share metrics), mergers, demergers, name changes (Wipro/Bajaj/L&T-family splits, PSU renames).

**1.2 Ground-truth sources, in priority order** (an independent human-checkable trail per cell):
1. The company's own quarterly result PDF / annual report (primary — the audited/board-approved filing).
2. BSE/NSE corporate-announcement archives (the exchange filing of the result).
3. Firm's existing PIT set `datasets/earnings_pit/unified_quarterly_pit.parquet` for overlap cross-check.
4. Screener.in / MoneyControl as a *tie-breaker only*, never as sole truth (they are themselves aggregators and carry the same restatement bias we are hunting).

**1.3 Cross-check fields:** Revenue, Net profit (PAT), EPS, total assets, total equity, shares outstanding — standalone AND consolidated matched to the right basis. Record exact-match / within-rounding / mismatch per field.

**1.4 Thresholds.**
- Large-cap stratum: ≥ 98% of fields exact-or-rounding match. Any *large-cap* PAT/Revenue mismatch > 1% is a **systemic-defect flag** → escalate, expand sample.
- Overall across strata: ≥ 95% match; ≤ 2% hard mismatch (> 5% value error); the rest explainable (consol/standalone basis, restatement, unit).
- Any single field that is *systematically* off (e.g., EPS always pre-split, revenue net-of-excise inconsistent pre/post-GST 2017) → quarantine that field, not the row.

---

## Phase 2 — Are the announcement dates genuinely point-in-time (the crux)

This is where fake alpha is born. A vendor can stamp the *right* number on a date *earlier than the market knew it*, and every earnings/quality/value backtest lights up. Four independent tests, all must pass.

**2.1 Direct filing-date reconciliation (n = 150 quarters).** For each sampled quarter, pull the **actual result-filing timestamp from the BSE/NSE corporate-announcement archive** (the exchange records the date/time the board-approved result was disclosed). Compare vendor announcement date to exchange filing date.
- Accept if `vendor_date >= exchange_filing_date` (same day or later) for ≥ 97% of the sample.
- **Any case where `vendor_date < exchange_filing_date` is a lookahead smoking gun** — the vendor "knew" before the market. Even ONE such case that is not a timezone artifact means the date column cannot be trusted; expand to n = 300 and quantify the leak distribution.

**2.2 The available-date lag distribution (sanity of the whole column).** Compute `announcement_date − period_end` for all ~2000 companies × all quarters and plot the distribution.
- Indian results legitimately land ~30-60 days after quarter-end (SEBI LODR limits: ~45 days for quarterly, ~60 for annual/Q4). A healthy column peaks in the 25-55 day band.
- **Red flags:** a spike at exactly period-end + N constant days for all names (the vendor *imputed* dates with a fixed offset — not real, this is the classic tell), lags of 0-5 days (impossible), or negative lags (announcement before quarter closes). Compare against our own PIT set's known 86.2%-exact-date profile as a reference shape.

**2.3 Imputation detection.** Count how many announcement dates fall on the **1st/last calendar day of a month, on weekends, or on national holidays / exchange-closed days**. Real result filings cluster on trading days and board-meeting days, essentially never on a Sunday. A high weekend/holiday rate ( > ~3%) proves dates are computed, not observed. Cross-check a subset of dates against `corporate-board-meetings` API results (NSE board-meeting archive is reachable per our environment notes) — the board-meeting date should precede/equal the filing date.

**2.4 The one-day-lag falsification (D-028, the decisive test).** Build the smallest possible earnings-drift or quality-rebalance backtest twice: once using the vendor announcement date as the point of availability, once using `announcement_date + 1 trading day`. 
- A *genuine* PIT dataset: results are near-identical (a 1-day lag barely moves a monthly/quarterly-rebalanced signal).
- A *look-ahead-contaminated* dataset: performance **collapses** when you add the lag, because the "edge" was really trading on information stamped before it was public. This is the same trap that has bitten this firm before; it is non-negotiable and runs through `lib/lookahead_audit.py`.

**Phase-2 acceptance:** all four tests pass. 2.1 or 2.4 failing = **REJECT the dataset for any timing-sensitive use** regardless of how good the numbers are.

---

## Phase 3 — Coverage and survivorship

Goal: prove the panel is not silently a survivors-only, backfilled fantasy — the #1 way a "2005-present, 2000 companies" claim inflates backtests.

**3.1 Point-in-time universe reconciliation.** Cross the vendor's *per-date* company list against our survivorship-safe membership: `NIFTY500_TICKER_2005_2025_Final.xlsx` (42 PIT snapshots, CLAUDE.md #6). For each snapshot date, compute: (a) how many then-index members the vendor covers, (b) how many vendor companies are *not* in any contemporaneous index (fine, breadth), and critically (c) **do delisted/merged/bankrupt names from 2005-2015 actually appear with data ending at their death, or are they simply absent?**

**3.2 The dead-company test (survivorship smoking gun).** Assemble a known list of names that delisted, were acquired, went bankrupt, or hit NCLT/IBC between 2005 and today — e.g., Kingfisher, Unitech, DHFL, IL&FS entities, Jet Airways, Reliance Communications, CG Power (near-death), Videocon, plus PSU/bank mergers (the SBI-associate banks, the 2019-20 PSB amalgamation, Vodafone-Idea merger, HDFC-HDFC Bank). 
- A survivorship-clean dataset **contains these names with fundamentals up to their last filing and then a clean terminus.**
- If they are missing, or their history was quietly re-mapped onto the surviving entity, the dataset is survivorship-biased → any long-horizon backtest on it overstates returns. **Quantify** the miss rate; > ~10% of a curated dead-list missing = FAIL for pre-2016 research.

**3.3 Coverage-count time series.** Plot distinct-companies-with-data per quarter, 2005→2026. Expect a **rising** curve (India's listed/covered universe grew; data quality pre-2010 is genuinely thinner). 
- **Red flag: a flat ~2000 from 2005 onward** — that means today's 2000 companies were backfilled to 2005, i.e., the early panel is exactly the set that survived to now = textbook survivorship + backfill. The honest shape is ~600-900 in 2005 climbing toward ~2000.

**3.4 Backfill / look-ahead-listing test.** For a sample of companies that IPO'd after 2005 (say 2015-2020 listings), confirm the vendor has **no fundamental rows dated before their listing/incorporation**. Pre-listing fundamentals = backfilled reconstruction = another lookahead vector.

**3.5 Field-level coverage holes.** Per column, per era, compute null %. A column that is 60% null in 2005-2010 but shipped as "available" will make any factor built on it a small-sample illusion in the early era. Map these holes explicitly so no one builds a 2005-start signal on a field that only densifies after 2012.

---

## Phase 4 — Restatement / vintage integrity

**4.1 Restatement direction test.** For companies with known material restatements (Yes Bank, DHFL, and any forensic-flagged names), check whether the value the vendor shows *on the original announcement date* is the **originally reported** number or the **later restated** number. If restated numbers are stamped on the original date, that is lookahead of the worst kind (the market did not know the restatement then). Real PIT data preserves the as-first-reported figure and carries the restatement as a *later* vintage.

**4.2 Point-in-time replay.** If a vintage column exists, reconstruct "what the dataset said as of date T" for three historical dates (e.g., 2012-06-30, 2018-06-30, 2022-06-30) and confirm it excludes anything filed after T. If overwrite-in-place (no vintage), we must treat EVERY value as potentially restated → the dataset is usable **only** with the announcement-date lag AND a documented caveat that restatements are baked in; flag to CIO for a use-restriction ruling.

---

## Phase 5 — Independent-source triangulation & internal consistency

**5.1 Accounting identities (free, whole-panel).** Programmatically test on 100% of rows: Assets = Liabilities + Equity (within rounding); EPS × shares ≈ PAT (basis-adjusted); consolidated ≥ standalone where both exist for revenue/assets; sequential quarters sum toward the annual figure. Rows failing identities → quarantine, tabulate the failure rate (a healthy vendor: < 0.5%).

**5.2 Overlap correlation with our PIT set.** On the intersection with `unified_quarterly_pit.parquet`, correlate PAT/Revenue/EPS. Expect ρ > 0.99 on matched basis. Systematic offsets (constant multiplier, sign flips, off-by-one-quarter alignment) surface exactly here and are the most common integration bug.

**5.3 Off-by-one-quarter alignment check.** A frequent vendor error: labeling Q1 data as Q2, or fiscal-year (Apr-Mar Indian FY) mislabeled as calendar. Verify the fiscal-period convention explicitly against 20 known filings; India's Apr-Mar year makes this a live trap.

---

## Quarantine → Acceptance decision rules

Each phase writes a pass/fail line + evidence file to `quarantine/vendorQ_fundamentals/verification/`. Final adjudication:

**REJECT outright if any of:**
- No genuine announcement-date column (Phase 0.3), or
- Phase 2.1 shows announcement dates predating exchange filings (non-timezone), or
- Phase 2.4 one-day-lag test collapses the toy backtest, or
- Phase 3.2 dead-company miss rate high / coverage curve flat-at-2000 (survivorship).

**CONDITIONAL ACCEPT (partial, scoped) if:** value accuracy passes and dates pass for the **modern era only** (e.g., dates reliable 2013→present but imputed pre-2013). Then the dataset is catalogued with a hard **use-window** (`min_reliable_date`) enforced in code, and pre-window rows stay quarantined. Common realistic outcome.

**FULL ACCEPT only if:** Phase 1 ≥ 95% (large-cap ≥ 98%), all four Phase-2 tests pass, Phase-3 coverage curve is honest + dead-list present, Phase-4 restatements handled as vintages (or documented+lagged), Phase-5 identities < 0.5% fail — **AND** a fresh `lib/lookahead_audit.py` PASS on a real candidate signal, red-teamed by Nikhil Bose.

**On acceptance:** add to `DATA_CATALOG.md` with: vintage SHA, `min_reliable_date`, standalone-vs-consol convention, known field-null eras, restatement policy, and the announcement-date-lag rule that MUST be applied (availability = announcement_date, never period-end). Add a `guards.py` helper so downstream code cannot read period-end as the availability date. Log the D-009/D-025 joint approval in `DECISIONS_LOG.md`.

**Ongoing (post-adoption):** monthly freshness ping (new quarters land within LODR windows); re-run the accounting-identity sweep on each delivery; any vendor re-delivery that changes historical rows triggers a restatement-audit before it overwrites our frozen vintage.

---

### One-line summary for the IC
Prove the *numbers* right (Phase 1), then prove the *dates* were knowable-then not known-now (Phase 2, especially the exchange-filing reconciliation and the one-day-lag collapse test), then prove the *panel isn't just survivors backfilled to 2005* (Phase 3). Anything less and we are buying manufactured alpha at data-vendor prices.
