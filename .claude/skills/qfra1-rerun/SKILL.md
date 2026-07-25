---
name: qfra1-rerun
description: Re-run the firm's SHORT-TERM / higher-churn mutual-fund recommendation method (the "capture-ratio overlay") — 6-month downside-capture filter vs category benchmark, then rank survivors by total capture ratio, top-3 BUY; SELL on negative trailing-12M excess in the losing quadrant. Use when the user asks to refresh/verify the MF Dashboard recommendations, run the short-term MF screen, or reconcile a category's Buy/Sell/Hold calls. Complements /qfra2-rerun (the long-term SIP engine).
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
3. **Total capture ratio (HC)** = 6M upside capture ÷ FN. Rank survivors by HC descending (IR).
4. **BUY** = rank < 4. **DESIGN INTENT (Principal, 2026-07-25): the rank runs over ALL funds in the category, not just cutoff survivors — deliberately.** A BUY must be top-3 on total capture against the whole field AND clear the downside filter; excluded funds "stealing" ranks is the feature, which is why a category can have fewer than 3 BUYs. **SELL** = trailing-12M excess return (CJ, month-end NAV ratio vs benchmark, already-realized so no lookahead) < 0 AND quadrant 4 (HC<1 & FN>1). Else **HOLD**.

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
- **Model runs stay Dec-end + Jun-end.** Anchor-pair backtest (906 formations, 2012-2024, all 6 categories, median + 10% trimmed mean): Jun/Dec statistically tied with the best pair (Apr/Oct), clearly beats Jan/Jul — study: `04_RND_LAB/STOCK_SCORECARD_750/results/anchor_pair_study/ANCHOR_PAIR_STUDY.md`. Verified independently 2026-07-25: smallcap 29/29, flexi 36/37 (known workbook blank-gate bug).
- **Dual-framework rule:** a client fund Sell needs BOTH frameworks (this + qfra2-rerun) non-Hold; disagreement defaults Hold; focused/value have no sheet here -> qfra2-only Sells need FM sign-off.
