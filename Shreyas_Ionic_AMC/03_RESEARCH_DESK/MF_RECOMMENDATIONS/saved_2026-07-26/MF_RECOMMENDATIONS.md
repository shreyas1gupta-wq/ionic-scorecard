# MF Recommendations — saved 2026-07-26 (one-time out-of-cycle, Principal 2026-07-26)

**Standing cadence: full model re-run at APR-END and OCT-END only (next: Oct-end 2026);**
NAVs accrue monthly (1st). QFRA-1 = short-term capture overlay; QFRA-2 verdicts joined
where the fund is in its curated set (asof per column). Client-facing fund Sell needs
BOTH frameworks non-Hold (dual-framework rule).

## [DATA] Anchor honesty — a June-end set is NOT computable from the current workbook
Raw NAV data cut per category: {'large': '2026-05-29', 'largemid': '2025-01-31', 'mid': '2025-01-31', 'flexi': '2025-01-31', 'multi': '2025-01-31', 'small': '2025-01-31'}. The `large` sheet was extended to May-2026
but its new rows rate only 1/30 funds (mostly empty NAV cells + at least one typo cell
'13O'), so the engine walked back to the latest anchor where >=80% of funds are ratable.
Per-category anchors are in the CSV. To produce a TRUE June-end 2026 set: backfill the
dashboard's month-end NAVs Feb-2025 to Jun-2026 (AMFI history), then re-run this script.

**Walk-back notes:** large: latest anchor 2026-04-30 rated only 3% of funds (incomplete NAV rows) — walked back

## large  (n=30, anchor 2025-05-31)
- **BUY (1):** Motilal Oswal Large Cap Fund-Reg(G) (rank 1, HC 1.30, FN 0.87)
- **SELL (2):** Baroda BNP Paribas Large Cap Fund-Reg(G) (12M excess -0.5%); Tata Large Cap Fund-Reg(G) (12M excess -0.8%)
- HOLD: 27
- Young/new funds (<30 months of history — engine cannot rate; the workbook's blank-gate forces HOLD): Bajaj Finserv Large Cap Fund-Reg(G) (~21m); Motilal Oswal Large Cap Fund-Reg(G) (~28m)

## largemid  (n=29, anchor 2025-01-31)
- **BUY (0):** none
- **SELL (5):** Mirae Asset Large & Midcap Fund-Reg(G) (12M excess -3.0%); Navi Large & Midcap Fund-Reg(G) (12M excess -0.4%); Quant Large & Mid Cap Fund(G) (12M excess -2.6%); Tata Large & Mid Cap Fund-Reg(G) (12M excess -1.8%); Union Large & Midcap Fund-Reg(G) (12M excess -0.3%)
- HOLD: 24
- Young/new funds (<30 months of history — engine cannot rate; the workbook's blank-gate forces HOLD): Bajaj Finserv Large and Mid Cap Fund-Reg(G) (~11m); Helios Large & Mid Cap Fund-Reg(G) (~3m); ITI Large & Mid Cap Fund-Reg(G) (~5m); PGIM India Large and Mid Cap Fund(G) (~12m); WOC Large & Mid Cap Fund-Reg(G) (~13m)

## mid  (n=28, anchor 2025-01-31)
- **BUY (0):** none
- **SELL (2):** Mirae Asset Midcap Fund-Reg(G) (12M excess -4.0%); Quant Mid Cap Fund(G) (12M excess -4.9%)
- HOLD: 26
- Young/new funds (<30 months of history — engine cannot rate; the workbook's blank-gate forces HOLD): Bandhan Midcap Fund-Reg(G) (~30m); Canara Rob Mid Cap Fund-Reg(G) (~26m); JM Midcap Fund-Reg(G) (~26m); WOC Mid Cap Fund-Reg(G) (~29m)

## flexi  (n=37, anchor 2025-01-31)
- **BUY (2):** TRUSTMF Flexi Cap Fund-Reg(G) (rank 2, HC 1.18, FN 0.96); Parag Parikh Flexi Cap Fund-Reg(G) (rank 3, HC 1.17, FN 0.58)
- **SELL (2):** Mahindra Manulife Flexi Cap Fund-Reg(G) (12M excess -1.4%); Navi Flexi Cap Fund-Reg(G) (12M excess -3.7%)
- HOLD: 33
- Young/new funds (<30 months of history — engine cannot rate; the workbook's blank-gate forces HOLD): 360 ONE Flexicap Fund-Reg(G) (~19m); Bajaj Finserv Flexi Cap Fund-Reg(G) (~18m); Baroda BNP Paribas Flexi Cap Fund-Reg(G) (~29m); Helios Flexi Cap Fund-Reg(G) (~15m); ITI Flexi Cap Fund-Reg(G) (~23m); Mirae Asset Flexi Cap Fund-Reg(G) (~23m); NJ Flexi Cap Fund-Reg(G) (~17m); Sundaram Flexi Cap Fund-Reg(G) (~29m); TRUSTMF Flexi Cap Fund-Reg(G) (~9m)

## multi  (n=28, anchor 2025-01-31)
- **BUY (0):** none
- **SELL (2):** Mahindra Manulife Multi Cap Fund-Reg(G) (12M excess -1.9%); Mirae Asset Multicap Fund-Reg(G) (12M excess -1.1%)
- HOLD: 26
- Young/new funds (<30 months of history — engine cannot rate; the workbook's blank-gate forces HOLD): Bank of India Multi Cap Fund-Reg(G) (~23m); Canara Rob Multi Cap Fund-Reg(G) (~18m); DSP Multicap Fund-Reg(G) (~12m); Edelweiss Multi Cap Fund-Reg(G) (~15m); Franklin India Multi Cap Fund-Reg(G) (~6m); HSBC Multi Cap Fund-Reg(G) (~24m); LIC MF Multi Cap Fund-Reg(G) (~27m); Mirae Asset Multicap Fund-Reg(G) (~17m); Motilal Oswal Multi Cap Fund-Reg(G) (~7m); PGIM India Multi Cap Fund-Reg(G) (~5m); Samco Multi Cap Fund-Reg(G) (~3m); Tata Multicap Fund-Reg(G) (~24m); Union Multicap Fund-Reg(G) (~25m); WOC Multi Cap Fund-Reg(G) (~16m)

## small  (n=29, anchor 2025-01-31)
- **BUY (2):** Motilal Oswal Small Cap Fund-Reg(G) (rank 1, HC 1.18, FN 0.80); Invesco India Smallcap Fund-Reg(G) (rank 3, HC 1.16, FN 0.93)
- **SELL (5):** Aditya Birla SL Small Cap Fund(G) (12M excess -0.5%); Baroda BNP Paribas Small Cap Fund-Reg(G) (12M excess -0.2%); HDFC Small Cap Fund-Reg(G) (12M excess -1.0%); Quant Small Cap Fund(G) (12M excess -3.0%); Union Small Cap Fund-Reg(G) (12M excess -0.1%)
- HOLD: 22
- Young/new funds (<30 months of history — engine cannot rate; the workbook's blank-gate forces HOLD): Baroda BNP Paribas Small Cap Fund-Reg(G) (~15m); JM Small Cap Fund-Reg(G) (~7m); Mahindra Manulife Small Cap Fund-Reg(G) (~26m); Motilal Oswal Small Cap Fund-Reg(G) (~13m); Quantum Small Cap Fund-Reg(G) (~15m); TRUSTMF Small Cap Fund-Reg(G) (~3m)

## New-fund flags from QFRA-2 (curated set)
none flagged

_New NFO launches (post-data-cut) have no ratable record by construction; they are listed for awareness in the journal, never recommended without 3y history._
## New launches — NFO scan 2026-07-26 (awareness only, never rated without a 3y record)
Week of Jun 29 - Jul 3, 2026 saw multiple NFOs across hybrid / multi-asset / debt / passive /
large-and-mid equity: ICICI Prudential MF and TRUST MF schemes, Choice Overnight Fund
(debt, launched Jul 1), Motilal Oswal BSE Midcap 150 Momentum 30 Index Fund (passive
momentum, NFO Jul 3-17). None is ratable by either framework (no history); the engine-side
young-fund flags in the CSV cover in-universe funds under ~30 months. Sources: elitewealth.in
NFO week note; dhan.co / 5paisa / goodreturns NFO 2026 lists.
