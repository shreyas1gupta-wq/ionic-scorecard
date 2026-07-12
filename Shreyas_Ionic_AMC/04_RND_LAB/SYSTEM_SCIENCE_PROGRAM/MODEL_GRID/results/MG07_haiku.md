# Quarterly Fundamentals Dataset Verification Protocol (Gate-3)

**Version:** 1.0  
**Date:** 2026-07-12  
**Owner:** Data Officer (Kavya Reddy)  
**Approval Gate:** CEO + CIO joint (D-025) before first backtest use  
**Scope:** Third-party Indian equity fundamentals (2005-present, ~2000 co, announced dates)

---

## PHASE 1: INVENTORY & SCHEMA AUDIT

**Deliverable: VENDOR_SCHEMA.md (template below)**

1. **Request from vendor (in writing):**
   - Exact field list: revenue, EBITDA, PAT, EPS (basic/diluted), OPM, ROE, etc.
   - Timestamp fields: announcement_date, fiscal_year_end, report_date, data_refreshed_date
   - Timezone for all dates (assumed UTC or IST?)
   - Fiscal year convention (Indian FY = Apr-Mar? Company-specific?)
   - Consolidation level (standalone vs consolidated P&L?)
   - Accounting standard (Ind-AS vs AS? IFRS?)
   - Data refresh lag (e.g., "updated 1 week after announcement"?)
   - Known gaps or backfill periods
   - Delisting policy: does dataset include delisted companies?
   - Restatement policy: original or restated figures?

2. **Validate against firm standards:**
   - Cross-check: India-specific fiscal year handling in `05_DATA_OFFICE/DATA_QUALITY_RULES.md`
   - Confirm timezone: all dates must be convertible to IST for timestamp_to_date consistency
   - Flag any non-standard definitions (e.g., "EPS" that includes discontinued ops)

**GATE: REJECT if schema unclear on announcement_date source or if fiscal year convention not specified.**

---

## PHASE 2: STRATIFIED SAMPLING DESIGN

**Sample Size:** 30 companies × 8 quarters = 240 test rows (minimum)

**Stratification (10 companies per stratum):**

| Stratum | Selection | Rationale |
|---------|-----------|-----------|
| **Large Cap (Tier 1)** | TCS, Reliance, HDFC, ICICI Bank, Bajaj Finance, Infosys, ITC, LT, Maruti, HUL | Highest volume, best external validation available |
| **Mid Cap (Tier 2)** | Bajaj Auto, Cipla, Dr. Reddy's, Eicher, Grasim, SBI, Titan, Voltas, Biocon, Lupin | Smaller but still liquid; test coverage beyond top tier |
| **Small Cap + Delisted (Tier 3)** | 5 companies delisted/merged 2015-2025 (IL&FS, Vodafone-Idea, Jet Airways, Unitech, GMR Infra pre-restructure) + 5 never-in-NIFTY500 (to test universe boundaries) | Test survivorship bias and merger handling |

**Time Stratification (8 quarters per company):**
- 2 quarters from 2008-2010 (post-crisis)
- 2 quarters from 2016-2018 (normal)
- 2 quarters from 2022-2024 (recent)
- 2 quarters from 2024-Q1 onwards (most recent, highest lookahead risk)

**Cross-Check Datasources (in priority order):**
1. BSE/NSE regulatory filing archives (XBRL filings on bseindia.com)
2. Company investor relations websites (PDF annual reports, investor presentations with announcement timestamps)
3. Moneycontrol/Screener historical data (editorial, but timestamped)
4. ET Markets / LiveMint coverage (announcement coverage with dates)
5. Internal Angel SmartAPI cache of past earnings surprises (if available)

---

## PHASE 3: POINT-IN-TIME (PIT) VERIFICATION

**Goal:** Prove announcement_date in vendor data matches or is AFTER actual public disclosure (never before).

### 3a. Announcement Date Cross-Check (Critical)

**For each of 30 sample companies, last 8 quarters:**

1. **Extract from vendor:**
   - announcement_date (as provided)
   - revenue, EPS (extract for later use)

2. **Independently retrieve actual announcement date:**
   - Go to bseindia.com → "Corporate Announcements" → search company ISIN
   - Find the earnings announcement filing (BSE uses standardized format: "Pursuant to Regulation 33 of SEBI LODR, 2015")
   - Note: **Exchange filing date** (when auditors/company submit to exchange)
   - Go to company IR website, download PDF annual report, check cover page for "announced on" date
   - Note: **Public announcement date** (press release / earnings call)
   - Rule: use EARLIEST of the two as **ground truth**

3. **Calculate lag:**
   ```
   lag_days = vendor_announcement_date - ground_truth_announcement_date
   ```

4. **Threshold rules (STRICT):**
   - RED FLAG: lag < 0 (vendor has data from the future → lookahead → REJECT dataset immediately)
   - YELLOW: lag 1-5 days (acceptable editorial buffer)
   - YELLOW: lag 6-10 days (acceptable but note it; some vendors batch-process)
   - RED: lag > 15 days (stale data; may be backfilled without editorial review)

5. **Aggregate result:**
   - Compute: mean lag, stdev, min, max across 240 sample cells
   - If mean lag > 10 days AND vendor claims "real-time updates," reject for truthiness
   - If ANY lag < 0, REJECT immediately (do not pass Go)

---

### 3b. Lag Distribution Analysis

**Run for all 240 samples:**

```
Plot histogram: lag_days distribution
- X-axis: lag in days (-10 to +60)
- Y-axis: count
- Overlay: cumulative %

Expected (clean data):
  - >90% in 0-5 day range
  - 0% in negative range
  - tail >30 days is acceptable (backfilled disclosures) BUT must be <10% of sample

Reject if:
  - Any negative lags exist
  - Median lag > 7 days
  - >20% of samples lag > 15 days
```

---

### 3c. Earnings Surprise Lookahead Test (Gold Standard)

**Hypothesis:** If data includes future announcements, a simple earnings-surprise model will trade profitably BEFORE announcement dates.

**Test on: TCS, Infosys, Reliance (most liquid, best price data)**

1. **Setup:**
   - Get vendor's EPS data for last 12 quarters (Q1 FY2023 → Q4 FY2024)
   - For each quarter, calculate: actual EPS vs "consensus" (use vendor's reported EPS from same dataset as signal)
   - Define surprise: if EPS_actual > consensus_eps, signal = BUY
   - Historical consensus: Use average of 2-3 prior quarters as proxy

2. **Backtest entry rule:**
   - Signal day = vendor's announcement_date at 09:30 IST (30 min after market open; allow announcement time to hit price)
   - Entry: buy 1 share at 09:30 price on signal day
   - Exit: sell at close of day (hold 6.5 hours, capture intraday reversal)

3. **Expected results (no lookahead):**
   - ~50% win rate (earnings surprise is noisy)
   - Average return per trade near 0% (you're trading stale information by 09:30)
   - Max 10-15 bps avg profit (noise, not signal)

4. **Reject if:**
   - Average return > 30 bps per trade (statistically strong)
   - Win rate > 65% (suspicious consistency)
   - ANY profitable trades occur BEFORE announcement date (clear lookahead)
   - Sharpe > 0.5 on daily returns (too clean for a noise trade)

5. **Implementation:**
   - Use firm's existing `lib/lookahead_audit.py` (Gate-4 tool)
   - Generate backtest equity curve + trade log with entry dates + announcement dates side-by-side
   - Commit backtest results to git with commit msg: "MG07_PIT_audit_vendor_name_PASS/FAIL"

---

### 3d. Re-announcement / Restatement Test

**Goal:** Detect if vendor conflates preliminary vs final results or missing restatements.

1. **Identify companies with known restatements:**
   - YES Bank (2018-2020 earnings restatement due to auditor findings)
   - IL&FS (2019 defaults led to restatement)
   - Sample 3-5 cases from past decade

2. **For each case:**
   - Pull vendor data for the restated quarter
   - Compare to: (a) company's original filing, (b) company's restated filing
   - Check: does vendor use restated or original figures?
   - Rule: MUST use restated (original = lookahead)

3. **For quarterly filers that announce preliminary results + final results:**
   - Track if vendor captures both announcements or overwrites
   - Example: Company announces "preliminary Q3 results" on Jan 15, then "final audited results" on Jan 22
   - Vendor should show TWO entries OR timestamp as Jan 22 (final) only
   - Flag if vendor conflates them

**Threshold:**
- If vendor uses original (pre-restatement) numbers: REJECT (material lookahead)
- If vendor conflates preliminary/final without timestamp clarity: FLAG for manual review per company

---

## PHASE 4: COVERAGE & UNIVERSE ANALYSIS

### 4a. NIFTY 500 Membership Test

**Datasource:** Use `NIFTY500_TICKER_2005_2025_Final.xlsx` (42 PIT snapshots per CLAUDE.md)

1. **For each year 2015-2025 (11 years):**
   - Extract NIFTY 500 membership list from that year's snapshot
   - Count companies: should be ~500
   - Cross-match with vendor dataset: how many are present?
   - Calculate: Coverage % = (vendor companies in NIFTY500) / 500

2. **Acceptance thresholds:**
   - 2015-2020: minimum 70% coverage (acceptable; some M&A / delistings)
   - 2020-2025: minimum 85% coverage (data should be fresh)
   - Any year < 60% coverage: FLAG as potential data gap or vendor filtering

3. **Identify missing companies:**
   - Print list of missing companies per year
   - Manually check: are they delisted, merged, renamed, or vendor gap?
   - If >10 major companies (top 100 by market cap) are missing, REJECT

---

### 4b. Sector Completeness

**Stratify missing coverage by sector:**

1. **For 11 years, calculate:**
   - Coverage % by sector (IT, Banking, Pharma, Auto, Industrials, Consumer, Energy)
   - Variance: which sectors have lowest coverage?

2. **Reject if:**
   - Any sector < 50% coverage in 2020+ (suggests vendor bias or data gap)
   - IT sector (largest, most liquid) < 80% coverage (red flag)

---

### 4c. Company Age & New Listing Handling

1. **Identify companies that entered NIFTY 500 during study period:**
   - Count: should match IPO calendar (e.g., 5-10 new listings per year on average)
   - For each new entrant: does vendor have data from year 1 of listing, or delayed?
   - Rule: vendor should have data within 1-2 quarters of listing (companies file quarterly results immediately)

2. **Test delisted companies:**
   - Pull list of ~50 companies delisted 2015-2025
   - Cross-check: which appear in vendor dataset?
   - If < 30 / 50 delisted companies present, FLAG SEVERE SURVIVORSHIP BIAS

---

## PHASE 5: SURVIVORSHIP BIAS TEST

**Goal:** Detect if vendor only includes survivors (backward-looking bias).

### 5a. Delisted Company Coverage

1. **Obtain NSE/BSE delisted company list 2005-2025:**
   - Source: https://www.nseindia.com/listing/listdelisted.html (historical archive)
   - Count delisted: ~200-300 companies in last 20 years

2. **For 50 sample delisted companies (stratified across sectors + decades):**
   - Check: does vendor dataset include them?
   - If YES: does vendor have data up to delisting date? Or pre-delisting data only?
   - Expected: yes, full history up to delisting

3. **Acceptance rule:**
   - If < 40% of delisted companies in vendor dataset → REJECT (severe survivorship bias)
   - If 40-70% → CONDITIONAL ACCEPT with mandatory footnote: "results may understate volatility / tail losses" (delisted companies often had distress, high returns)
   - If > 70% → ACCEPT on survivorship dimension

4. **Specific case: IL&FS (2019 default, delisted 2021)**
   - Vendor should have IL&FS data 2005-2021
   - Should show declining profitability 2018-2019 and default period
   - If vendor's IL&FS data shows "clean" P&L or is missing → RED FLAG

---

### 5b. Merger & Acquisition Handling

**Test 10 major M&A cases (2010-2025):**
- HDFC + HDFC Bank merger (2023)
- TCS (various acquisitions)
- Vodafone + Idea merger discussions (2024; test incomplete deal handling)
- Grasim / Aditya Birla (structural reorganization 2023)

**For each case:**
- Does vendor have both parent + target separately, or consolidated?
- Are pre-merger financials attributed to correct entity?
- Rule: vendor should show both separately pre-merger, then combined post-merger (NOT retroactive consolidation)
- If vendor retroactively applies merged entity's name to historical parent data → RED FLAG (lookahead + restatement confusion)

---

## PHASE 6: CROSS-VALIDATION WITH PUBLISHED FIGURES

### 6a. Spot-Check 20 Specific Quarters

**Sample across all 30 companies, recent quarters (2023-2024):**

For each quarter, retrieve:
1. **Vendor data:** revenue, PAT, EPS
2. **BSE regulatory filing:** XBRL data (most authoritative for listed companies)
3. **Annual report PDF:** official P&L (may differ from quarterly filings due to Ind-AS interpretation)
4. **Screener.in / Moneycontrol historical:** editorial cross-check

**Comparison rules:**
- Revenue: must match within ±0.5% (rounding tolerance)
- EPS: must match within ±1% (can include dilution adjustments)
- PAT (Profit After Tax): within ±1%
- RED FLAG: systematic bias (e.g., vendor always 2% higher on revenue)

**Acceptance:**
- 18-20 / 20 matches within tolerance → PASS
- 15-17 / 20 → CONDITIONAL (investigate failures)
- < 15 / 20 → REJECT

---

### 6b. Metric Definition Audit

1. **Request vendor documentation:**
   - EPS: basic or diluted? Which dilution (ESOP, warrants, convertibles)?
   - Revenue: gross or net of discounts?
   - PAT: standalone or consolidated?
   - EBITDA: vendor-computed or company-reported?

2. **Cross-check 5 cases:**
   - For companies with material dilution (TCS, Infosys: large ESOP pools)
   - Verify: vendor's EPS matches company's reported basic EPS
   - Red flag: vendor uses non-standard definition

---

### 6c. Restatement Handling Verification

**For YES Bank (2019 restatement case):**
1. Pull vendor's EPS for FY2018, FY2019 (pre-restatement periods)
2. Cross-check to company's 2021 annual report (which shows restated FY2018-2019 figures)
3. Does vendor show restated or original?
4. RULE: vendor must show restated (original = time-travel data = lookahead)

**Acceptance:**
- If vendor shows restated figures → PASS
- If vendor shows original figures → REJECT

---

## PHASE 7: LOOKAHEAD META-TEST (Defense in Depth)

**Goal:** Comprehensive check that no subtle lookahead exists.

### 7a. Simple Earnings-Quality Strategy (Negative Control)

**Hypothesis:** Build a "quality" strategy using vendor's metrics. If data has lookahead, quality factors will be artificially profitable.

1. **Strategy:**
   - Universe: NIFTY 50 (most liquid)
   - Monthly rebalance (last day of month, T+1 trading logic)
   - Long only (no short-sale complications)
   - Signal: high ROE (>15%) + low debt (D/E < 0.5) + earnings growth >10% YoY
   - Hold: 3 months, equal-weight rebalance

2. **Backtest periods:**
   - Train: 2015-2018 (early data, vendor historical)
   - Test: 2019-2020 (out-of-sample)
   - Holdout: 2021-2023 (most recent, highest lookahead risk if present)

3. **Expected Sharpe ratio (no lookahead):**
   - ~0.4-0.7 (positive but modest, quality does have alpha, but not overwhelming)
   - Return: 8-12% annual (in-line with historical Indian equity returns)

4. **Reject if:**
   - Sharpe > 1.0 in holdout period (too clean, suggests lookahead)
   - Returns > 20% annual (equity returns on known quality factors should be <15%)
   - Drawdown < 15% in any 1-year rolling window (unrealistic for equity strategy)

---

### 7b. Forward P&L Timing Audit

**For any winning trades in Phase 3c & 7a:**

1. **Manual check:** 10 largest winning positions
2. For each position:
   - Entry date (per backtest)
   - Announcement date (per vendor data)
   - Price at entry
   - Price at exit
   - Company news on entry date (from news archives)
   - Rule: announcement must be public knowledge BEFORE entry, OR entry must be AFTER announcement
   - RED FLAG: entry price reacts to announcement (upward jump), but announcement timestamp shows AFTER entry

---

### 7c. Consensus vs Actual Test

**If vendor claims to have "consensus EPS" fields:**

1. Pull vendor's consensus_eps for 20 sample quarters
2. Compare to:
   - Reuters/Bloomberg consensus (if access exists)
   - Manual consensus from prior quarter EPS (as internal proxy)
3. Rule: vendor's "consensus" should be NOT from the future (obvious, but check)
4. Check: is "consensus" refreshed pre-announcement? (should be, it's forward-looking)
5. RED FLAG: if consensus appears to be "back-fitted" post-announcement

---

## PHASE 8: ACCEPTANCE / REJECTION DECISION MATRIX

**Decision rules (evaluated in sequence; first match wins):**

### IMMEDIATE REJECT (Any single item → dataset cannot be used):
1. Any lag < 0 days (data from future)
2. Vendor schema unclear on announcement_date source
3. Use of original (not restated) earnings figures
4. EPS/Revenue spot-check failures > 5 / 20 (>25% error rate)
5. Earnings surprise backtest shows +50 bps or higher average return
6. < 40% delisted company coverage (severe survivorship)
7. Delisted companies have incomplete data (missing pre-delisting quarter)
8. Mean lag > 15 days AND vendor claims real-time updates (lie detection)

### CONDITIONAL ACCEPT (Flag in data catalog, use with caution):
1. Coverage 60-80% NIFTY 500 (mask universes in backtest; use only NIFTY 100+ names)
2. Lag 6-10 days mean (note as editorial lag; acceptable for analysis, not for intraday)
3. 40-70% delisted coverage (add footnote: results may understate tail risk)
4. Earnings surprise backtest: +20 to +50 bps (weak signal, not strong lookahead, but note it)
5. Sector coverage variance > 15% (accept, but stratify tests by coverage per sector)
6. 1-2 major companies (top 50) missing per year (acceptable; manual investigation only)
7. Restatement audit: vendor has restated figures but manual spot-check found 1-2 old figures mixed in (acceptable if < 5% of sample)

### FULL ACCEPT (Can use freely, document):
1. All lags 0-5 days, no negatives, median < 3 days
2. Coverage > 85% NIFTY 500 across 2020-2025
3. > 70% delisted company coverage, complete pre-delisting data
4. All 20 spot-checks pass (within ±0.5% revenue, ±1% EPS)
5. Earnings surprise backtest: <+20 bps average, ~50% win rate
6. Restatement audit: 100% restated figures, no old data
7. Merge/acquisition handling: correct (parent + target separate, not retroactive)
8. All sectors > 70% coverage

---

## PHASE 9: DOCUMENTATION & APPROVAL

### 9a. Deliverables (commit to git):

1. **MG07_VENDOR_AUDIT_[VENDOR_NAME].md** (this template filled)
   - Executive summary (pass/fail + key findings)
   - Detailed results per phase
   - All plots & histograms inlined

2. **MG07_PIT_AUDIT_[VENDOR_NAME].csv** (240 rows × 8 cols)
   - company, quarter, announcement_date_vendor, announcement_date_ground_truth, lag_days, revenue_vendor, revenue_ground_truth, eps_vendor, eps_ground_truth

3. **MG07_LOOKAHEAD_TEST_[VENDOR_NAME].csv** (backtest trade log)
   - Columns: entry_date, exit_date, announcement_date, entry_price, exit_price, pnl_bps, pnl_dollars

4. **data_catalog.md entry** (append to 05_DATA_OFFICE/DATA_CATALOG.md)
   ```
   ### Vendor: [NAME]
   - **Status:** ACCEPT | CONDITIONAL | REJECT
   - **Coverage:** 85% NIFTY 500 (2020-2025)
   - **Lag:** Median 3 days (0-10 range)
   - **Delisted:** 75% coverage
   - **Last verified:** 2026-07-12 (MG07_VENDOR_AUDIT_[NAME].md)
   - **Usage notes:** [Free-text: sector bias, lookahead caveats, mask universes, etc.]
   - **Next re-audit:** 2027-Q1
   ```

### 9b. Approval Gate (D-025):

**Before any backtest using this dataset:**
- CEO + CIO JOINT sign-off on MG07_VENDOR_AUDIT_[NAME].md
- CIO sign-off on PIT test results (lookahead audit is risk responsibility)
- Data Officer adds dataset to DATA_CATALOG with "APPROVED" label

**Approval checklist (signed):**
```
[ ] PIT audit passed (no negative lags, median < 10 days)
[ ] Spot-checks passed (>17/20 within tolerance)
[ ] Lookahead test passed (Sharpe < 1.0, earnings model < +20 bps)
[ ] Survivorship bias assessed (% delisted documented)
[ ] Schema audit completed (Ind-AS confirmed, standalone/consolidated clear)
[ ] Restatement handling verified (only restated figures used)
[ ] Data catalog entry filed
[ ] Approved by: ____________ (CIO) and ____________ (CEO)
[ ] Date: __________
```

---

## PHASE 10: ONGOING MONITORING

**Post-approval checklist (quarterly):**

1. **Data freshness:** new quarters arriving on schedule?
2. **Coverage drift:** any companies suddenly dropping from dataset?
3. **Lag creep:** announcement dates shifting backward (vendor rushing)?
4. **Re-audit trigger:** if any backtest using this data shows anomalous results, re-run MG07_PIT_AUDIT on relevant quarters immediately

---

## IMPLEMENTATION TIMELINE

| Phase | Owner | Days | Gate |
|-------|-------|------|------|
| 1. Inventory | Data Officer | 2 | Schema clear? |
| 2. Sampling | Quant Head | 1 | 30 cos selected? |
| 3. PIT verification | Data Officer + Red Team | 5 | No negative lags? |
| 4. Coverage | Data Officer | 3 | >60% threshold? |
| 5. Survivorship | Quant Head | 2 | >40% delisted? |
| 6. Cross-validation | Quant Head | 4 | 17/20 spot-checks pass? |
| 7. Lookahead meta-test | Quant Head + ML Expert | 5 | Sharpe <1.0? |
| 8. Decision | CIO | 1 | Accept/Reject/Conditional? |
| 9. Documentation | Data Officer | 2 | Catalog + approval signed? |
| **TOTAL** | **All hands** | **~25 calendar days** | |

---

## APPENDIX: PYTHON IMPLEMENTATION SKELETON

```python
# MG07_vendor_audit_harness.py
# Implements Phases 3-7 above

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf

# Phase 3a: PIT Lag Calculation
def calculate_pit_lags(vendor_df, ground_truth_df):
    """
    vendor_df: {company, quarter, announcement_date}
    ground_truth_df: {company, quarter, actual_announcement_date}
    returns: merged df with lag_days column
    """
    merged = vendor_df.merge(ground_truth_df, on=['company', 'quarter'])
    merged['lag_days'] = (merged['announcement_date'] - 
                          merged['actual_announcement_date']).dt.days
    return merged

def check_pit_thresholds(lag_df):
    """Reject if any lag < 0 or mean > 10 days"""
    if (lag_df['lag_days'] < 0).any():
        return "REJECT: Negative lags detected (lookahead)"
    if lag_df['lag_days'].mean() > 10:
        return f"YELLOW: Mean lag {lag_df['lag_days'].mean():.1f} days (high)"
    return "PASS: Lags within threshold"

# Phase 3c: Earnings Surprise Lookahead Test
def earnings_surprise_backtest(vendor_eps, price_df, announcement_dates):
    """
    vendor_eps: {date, company, actual_eps, consensus_eps}
    price_df: {date, company, open, close}
    announcement_dates: {company, quarter, announcement_date}
    
    returns: PnL per trade + Sharpe ratio
    """
    trades = []
    for idx, row in announcement_dates.iterrows():
        company = row['company']
        ann_date = row['announcement_date']
        
        # Entry: next trading day at 09:30
        entry_date = ann_date + timedelta(days=1)
        entry_price = price_df[(price_df['company'] == company) & 
                               (price_df['date'] == entry_date)]['open'].values
        if len(entry_price) == 0:
            continue
        
        # Exit: same day close
        exit_price = price_df[(price_df['company'] == company) & 
                              (price_df['date'] == entry_date)]['close'].values
        if len(exit_price) == 0:
            continue
        
        pnl_bps = (exit_price[0] - entry_price[0]) / entry_price[0] * 10000
        trades.append({
            'entry_date': entry_date,
            'announcement_date': ann_date,
            'pnl_bps': pnl_bps
        })
    
    trades_df = pd.DataFrame(trades)
    sharpe = trades_df['pnl_bps'].mean() / trades_df['pnl_bps'].std() * np.sqrt(252)
    
    return trades_df, sharpe

# Phase 6a: Spot-Check Comparison
def spot_check_figures(vendor_df, bse_df, tolerance_pct=0.5):
    """
    Compare revenue & EPS within tolerance
    tolerance_pct: acceptable % difference
    """
    merged = vendor_df.merge(bse_df, on=['company', 'quarter'])
    merged['rev_error_pct'] = abs(merged['revenue_vendor'] - 
                                   merged['revenue_bse']) / merged['revenue_bse'] * 100
    merged['eps_error_pct'] = abs(merged['eps_vendor'] - 
                                   merged['eps_bse']) / merged['eps_bse'] * 100
    
    pass_count = ((merged['rev_error_pct'] <= tolerance_pct) & 
                  (merged['eps_error_pct'] <= tolerance_pct)).sum()
    
    return pass_count, len(merged), merged

# Phase 4a: NIFTY 500 Coverage
def coverage_analysis(vendor_df, nifty500_membership_df):
    """
    nifty500_membership_df: {year, isin, company_name}
    returns: coverage % per year
    """
    coverage_results = []
    for year in nifty500_membership_df['year'].unique():
        nifty_year = set(nifty500_membership_df[nifty500_membership_df['year'] == year]['isin'])
        vendor_year = set(vendor_df[vendor_df['year'] == year]['isin'])
        coverage = len(nifty_year & vendor_year) / len(nifty_year) * 100
        coverage_results.append({'year': year, 'coverage_pct': coverage})
    
    return pd.DataFrame(coverage_results)
```

---

## SUMMARY CHECKLIST

Before using ANY new quarterly fundamentals dataset:

- [ ] Phase 1: Schema audit (announcement_date defined, no gaps)
- [ ] Phase 2: Stratified 30 companies × 8 quarters selected
- [ ] Phase 3a: PIT lags calculated; no negative; median < 10 days
- [ ] Phase 3b: Lag distribution plotted; >90% in 0-5 day range
- [ ] Phase 3c: Earnings surprise backtest run; Sharpe < 1.0, avg return < +20 bps
- [ ] Phase 4: NIFTY 500 coverage > 70% (80%+ preferred)
- [ ] Phase 5: Delisted companies > 40% (70%+ preferred); IL&FS case confirmed
- [ ] Phase 6a: 20 spot-checks run; ≥17/20 pass within ±0.5%/±1%
- [ ] Phase 6c: Restatement audit (YES Bank case); vendor shows restated figures only
- [ ] Phase 7a: Quality meta-strategy run; Sharpe <1.0, returns <15% annual
- [ ] Phase 8: Decision matrix applied; outcome ACCEPT/CONDITIONAL/REJECT documented
- [ ] Phase 9: MG07_VENDOR_AUDIT_*.md + data_catalog.md entry + CEO+CIO signatures
- [ ] Phase 10: Quarterly re-validation scheduled

---

**Document created:** 2026-07-12  
**Next re-audit cycle:** 2027-Q1 (or immediately if any backtest using this data flags anomalies)
