---
name: qfra1-rerun
description: Re-run the firm's SHORT-TERM / higher-churn mutual-fund recommendation method (the "capture-ratio overlay") — rank ALL funds in the category by 6M total capture ratio, apply the downside-capture filter after ranking, top-3 surviving ranks BUY; SELL on negative trailing-12M excess in quadrant 4 (the catch-all bucket — see §method). Use when the user asks to refresh/verify the MF Dashboard recommendations, run the short-term MF screen, or reconcile a category's Buy/Sell/Hold calls. Complements /qfra2-rerun (the long-term SIP engine).
---
# /qfra1-rerun — short-term MF capture-ratio recommendations
**Owner: MF desk. Verified against the live workbook 2026-07-25 (Sonnet reverse-engineering pass): smallcap 29/29 exact match, flexicap 36/37 (the 1 mismatch is the workbook's own blank-gate bug, §Known bugs).**

## Source of record
`C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\MF Dashboard.xlsx`
- Raw sheets `large / largemid / mid / flexi / multi / small`: daily NAVs (~900 cols) + benchmark via INDEX/MATCH on `Indices` (daily levels for NIFTY 100/250/500, Midcap150, Smallcap250, Multicap 50:25:25 + factor indices). `others`: per-fund attrs (AUM, category, inception).
- Engine sheets `<cat>2`: month-end anchors; **Recommendation = column QZ** (header row 4, funds from row 7). NOTE: `Q2` is NOT the recommendation cell — it is a fund-name header on the raw sheet.
- OneDrive dehydrates the file — copy to %TEMP% before opening with python.

## The method (as actually implemented, verified)
Per category, per month-end anchor:
1. **6M downside capture (FN)** = compound the fund's daily returns on days the *benchmark* fell over a true 6-calendar-month window, ÷ same for the benchmark.
2. **Filter**: exclude funds with FN > threshold `<cat>2!LO1` — **actual workbook values: large 0.9, mid 0.8, multi 0.9, flexi/small/largemid 1.0** (Principal quoted multi as 1.0; the sheet uses 0.9 — flagged, not changed).
3. **Total capture ratio (HC)** = 6M upside capture ÷ FN. Rank ALL funds by HC descending (IR) — the FN filter is applied AFTER ranking, never before.
4. **BUY** = rank < 4. **DESIGN INTENT (Principal, 2026-07-25): the rank runs over ALL funds in the category, not just cutoff survivors — deliberately.** A BUY must be top-3 on total capture against the whole field AND clear the downside filter; excluded funds "stealing" ranks is the feature, which is why a category can have fewer than 3 BUYs. **SELL** = trailing-12M excess return (CJ, month-end NAV ratio vs benchmark, already-realized so no lookahead) < 0 AND PK quadrant 4 — **which per the sheet's own formula is the CATCH-ALL else-bucket (neither HC>1&FN<1 nor HC<1&FN>1), NOT the losing quadrant. (HC<1 & FN>1) is quadrant 3 and can NEVER fire a SELL — audit 2026-07-26, almost certainly a numbering slip by the workbook author; escalated to the Principal for a ruling (intended vs bug: SELL on PK in {3,4}). Do not change behavior without that ruling.** Else **HOLD**.

## How to run
```
python Shreyas_Ionic_AMC/05_DATA_OFFICE/scripts/mf_capture_recomm.py --cats small flexi [--verify]
```
Supports all 6 categories; `--verify` diffs the recomputation against the sheet's cached QZ. Read-only — never writes to the workbook.

## Known workbook bugs (found 2026-07-25 — fix in Excel or trust the script)
1. **Blank-gate bug (material):** each fund's HC is gated on its CJ value 12 rows earlier, which needs NAV from ~24 months before eval — so funds aged ~6-24 months are silently forced to HOLD even with a full 6M window (e.g. TRUSTMF Flexi, launched Apr-2024, is rank-2 BUY on the real math but shows HOLD).
2. `PK` "Quartile" has an unreachable branch (same condition twice) and is a quadrant, not a quartile; `MG/NV` "1Y" windows actually span 11 months (not load-bearing for QZ); `KH1` cutoff-rank cell is decorative (IR<4 hardcoded). (Rank-over-all-funds is NOT a bug — see §method, Principal-confirmed design.)

## Relations
- **Long-term SIP recommendations** = `/qfra2-rerun` (frozen QFRA 2.0 engine) — different engine, do not mix.
- Factor/benchmark index closes = `/factor-indices` (niftyindices.com scraper; HOME NETWORK only).
- Pending from Principal: monthly NAV dump + formal scoring-method doc — when supplied, wire them here and into the NDPMS deck template's fund slides (`09_PRODUCT/pr_template/modules/funds_*.py`), which by design consume desk recommendations rather than re-scoring funds.

## Cadence & data automation (Principal 2026-07-26)
- **NAVs auto-refresh MONTHLY (1st, 08:10)** via `Shreyas_Ionic_AMC/05_DATA_OFFICE/scripts/mf_nav_refresh.py --digest` (AMFI NAVAll; month-end history accrues forever). Wired in OPERATING_CALENDAR §automatable; DESK-100 re-arms the cron each session. Verified current 2026-07-26 (13,958 schemes).
- **Model runs at APR-END + OCT-END (Principal 2026-07-26, per the anchor-pair study; changed from Dec/Jun; next run = Oct-end 2026).** Full-set saves go through `05_DATA_OFFICE/scripts/save_mf_recommendations.py` (all categories BUY/SELL/HOLD + QFRA-2 join + young-fund flags + coverage-aware anchor walk-back → `03_RESEARCH_DESK/MF_RECOMMENDATIONS/saved_<date>/`). One-time out-of-cycle save 2026-07-26 (Principal): anchors large=2025-05-31, rest=2025-01-31 — the workbook's newer large rows are mostly empty (1/30 ratable, plus a '13O' typo cell; parser now NaN-tolerant); a TRUE June-end set needs month-end NAV backfill Feb-2025→Jun-2026. Stocks re-score WEEKLY (Thu, else Fri, else Mon) via run_weekly_v1.py — separate cadence. Anchor-pair backtest (906 formations, 2012-2024, all 6 categories, median + 10% trimmed mean): Jun/Dec statistically tied with the best pair (Apr/Oct), clearly beats Jan/Jul — study: `04_RND_LAB/STOCK_SCORECARD_750/results/anchor_pair_study/ANCHOR_PAIR_STUDY.md`. Verified independently 2026-07-25: smallcap 29/29, flexi 36/37 (known workbook blank-gate bug).
- **Dual-framework rule (wording tightened 2026-07-26):** a client fund Sell requires BOTH frameworks independently at Sell; a BUY on either side VETOES the Sell; any disagreement defaults Hold. (The old "both non-Hold" phrasing was literally satisfied by BUY+Sell — never use it.) Focused/value have no sheet here -> qfra2-only Sells need FM sign-off.
- **[DATA] CRITICAL KNOWN ISSUE (audit 2026-07-26): the Dashboard's Indices sheet is PRI, not TRI** (NIFTY 500 = 21,580.9 on 2025-01-31 = price index; TRI ~33k). SEBI mandates TRI; QFRA-2 uses TRI. Effect: CJ 12M excess flattered by ~1.2-1.5%/yr, SELLs systematically suppressed, and the dual-framework legs sit on inconsistent bases. MUST be fixed before the Oct-end 2026 run: rebuild the Indices sheet from official TRI series (factor-indices skill / niftyindices, HOME NETWORK), D-009 spot-check, re-verify LO1 + QZ on a TRI recompute. Until then, treat SELL sets as understated.

## Out-of-cycle recompute runbook (state as of 2026-07-26)
To recompute recommendations at an anchor NEWER than the workbook's data cut:
1. **Fund month-end NAVs: DONE** — `datasets/mf_nav/nav_monthend.parquet` backfilled 2025-02..2026-06 (mf_nav_backfill.py, AMFI official, proxy-friendly, resume-safe).
2. **Benchmark DAILY levels (the blocker):** NIFTY 100/250/500, MIDCAP 150, SMALLCAP 250, MULTICAP 50:25:25 past 2025-01-31. niftyindices.com `Backpage.aspx/getHistoricaldatatabletoString` POST is INTERCEPTED by the corporate proxy (verified 2026-07-26, exact XHR shape returns the HTML shell) — run from HOME NETWORK: cinfo = "{'name':'<INDEX>','startDate':'DD-MMM-YYYY','endDate':'DD-MMM-YYYY','indexName':'<INDEX>'}" posted as {"cinfo": <that string>} with X-Requested-With: XMLHttpRequest after a cookie warm-up GET. D-009 vs the workbook's Indices sheet on the 2024-2025 overlap before use; confirm TRI vs PRI (SEBI filings mandate TRI benchmarks — verify which the Indices sheet holds).
3. **Fund DAILY NAVs** for the 6M capture windows: AMFI history endpoint per window (works through proxy), or the Principal's workbook refresh (note his hand-edits can carry typos — parser is NaN-tolerant since 2026-07-26).
4. Then either extend the workbook (Principal's call — engine treats it read-only) or compute from the side stores with value-based fund matching on an overlap month.
