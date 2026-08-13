# NSE Structured Financial-Results Pull — D-009 Report
**Data Officer:** Kavya Reddy | **Date:** 2026-08-06 | **Status:** COMPLETE, VERDICT = USE WITH CAVEATS

## Task
Replace inferred PIT `available_date` values with REAL NSE filing dates, 2011-2026. Data only, no model files touched.

## What was built
| Artifact | Path |
|---|---|
| Puller (resume-safe) | `Shreyas_Ionic_AMC/05_DATA_OFFICE/scripts/nse_results_pull.py` |
| Consolidator | `Shreyas_Ionic_AMC/05_DATA_OFFICE/scripts/nse_results_consolidate.py` |
| Raw month files | `datasets/nse_results_pit/raw/{quarterly,annual}_{yyyy}_{mm}.json` (376 files) |
| Pull log | `datasets/nse_results_pit/pull_log.csv` |
| Raw consolidated (every field) | `datasets/nse_results_pit/nse_results_pit_raw.parquet` |
| Tidy PIT (keyed symbol+period_end) | `datasets/nse_results_pit/nse_results_pit_tidy.parquet` |

Source confirmed reachable per the Principal's brief: `https://www.nseindia.com/api/corporates-financial-results`, params `index=equities, from_date=DD-MM-YYYY, to_date=DD-MM-YYYY, period=Quarterly|Annual`. Warm-up quirk (403 on homepage GET, 200 on the filings-page GET, cookies set regardless) confirmed and used as-is. Both `Quarterly` and `Annual` period values are accepted — this was unconfirmed going in and is now verified [DATA].

**Resume-safety:** one raw JSON per (period, year, month); a file is written only after a successful parse; re-running skips every month already on disk. Verified empirically: a repeat run against an already-pulled 3-month range fetched 0 and skipped 3. A `MAX_CONSECUTIVE_FAILS=3` breaker aborts the run cleanly (rather than hammering NSE) if the server starts refusing mid-run; that never triggered in the full pull (376/376 months returned HTTP 200, zero errors, ~16 minutes end to end at 1.7s/call sequential).

## Row counts — HONEST, by period_end year (not pull-window year)
The Principal's probe sampled one July window per year; those were per-month filing counts, not annual coverage. Below is the real annual figure, from the consolidated tidy layer, grouped by the **period the results are FOR** (period_end), which is the number that matters for PIT usability:

| period_end year | rows | distinct symbols |
|---|---|---|
| 2010 (Q4 only, results filed Jan-2011) | 1,466 | 1,461 |
| 2011 | 6,078 | 1,584 |
| 2012 | 6,172 | 1,595 |
| 2013 | 6,245 | 1,604 |
| 2014 | 6,115 | 1,589 |
| 2015 | 6,143 | 1,598 |
| 2016 | 6,552 | 1,692 |
| 2017 | 6,553 | 1,679 |
| 2018 | 6,523 | 1,672 |
| 2019 | 6,486 | 1,685 |
| 2020 | 6,583 | 1,706 |
| 2021 | 6,876 | 1,823 |
| 2022 | 7,026 | 1,911 |
| 2023 | 7,752 | 2,023 |
| 2024 | 8,251 | 2,135 |
| **2025** | **0** | **0** |
| **2026** | **0** | **0** |

Totals: 94,821 (symbol, period_end) tidy rows, 2,709 distinct symbols, 186,990 raw disclosure rows (standalone+consolidated+corrections) before the tidy grouping, across 376 successfully-pulled (period × year × month) windows, zero pull failures.

**Earliest year with usable breadth: 2011** (1,584 symbols — matches the Principal's requested start exactly). Empirically the true API floor is even earlier: Jan-2009 returns 200/1,312 rows; Jan-2000 and Jan-1996 both return 200/0 rows — the real floor is somewhere in 2000-2009, out of scope for this pull but worth knowing if the window is ever extended [DATA].

## THE CRITICAL FINDING: a hard coverage cliff at period_end ~Mar-2025
This is not visible from max(date) or from the pull log (every month pull succeeded with HTTP 200) — it only shows up when the tidy layer is grouped by the period the results are FOR. Per the Lessons Learned discipline (periods-per-year, not just max-date): Feb-2025 filings are healthy (2,547 rows, mainstream names — FOSECOIND, SANOFI, KSB, SCHAEFFLER). Mar-2025 is already thin (106 rows). Apr/May/Jun-2025 collapse to 9/8/11 rows — for comparison, May-2024 (the equivalent point in the prior annual cycle) had 3,056 rows. The current week (25-Jul to 05-Aug-2026, re-checked live with a fresh session, right now, specifically to rule out a bulk-run artifact) returns 2 rows total, both from a single chronic-late filer (VSTTILLERS).

What the ~2025-2026 window actually contains is a small trickle of multi-quarter-late catch-up filings, from a mix of:
- **Confirmed delisted/suspended** (verified against our own ground-truth `datasets/nse_bhavcopy_daily/close_all.parquet`, i.e. trading actually stopped): EROSMEDIA (last traded 2024-10-24), ROLTA (2022-08-22), RELCAPITAL (2022-05-24), IL&FSTRANS (2019-03-29), AIFL (2019-02-21), ANSALAPI (2022-09-21), CMICABLES (2023-04-19), SECURCRED (2024-06-21).
- **Still actively trading, just chronically filing-delinquent**: RAJESHEXPO (traded as recently as 2025-12-24), VSTTILLERS, DSSL, KAVDEFENCE (all traded 2026-07-03, the last bhavcopy date on file).

Confirmed not a client-side bug: re-fetched with a brand-new session (independent of the bulk-pull run), tried both narrow (1-month) and wide (3-month) windows for Apr-Jun 2025 — 28 rows either way, consistent. **Cause is not established** [INFERENCE]: most likely this specific historical-archive endpoint has a >1-year processing lag before recent filings are folded into its from_date/to_date-queryable index, with NSE's live/current-quarter feed served through a different path (the existing `nse_earnings_dates/quarterly_results_all.json` cache, or the board-meetings route) — not confirmed, flagged as a follow-up if anyone wants to chase it.

**Consequence:** this pull fixes defect (a)'s pre-2020 hole completely and its 2024 hole (495→2,135 symbols) — but does NOT fix the 2025-2026 collapse. The firm still needs its existing (thin, ~490-symbol) sources for those two years.

## D-009 checks (each PASS/FAIL)
1. **Schema/dtypes/nulls** — PASS. 33 columns kept as-received, zero pre-filtering. 0% nulls on symbol/broadCastDate/filingDate/fromDate/toDate/isin/consolidated/audited/financialYear/relatingTo across all 186,990 raw rows. All symbols match a sane ticker pattern.
2. **Duplicates** — PASS. 44 exact full-row duplicates dropped at consolidation (harmless re-fetch overlap between Quarterly/Annual period calls). 0 duplicate (symbol, period_end) keys in the tidy layer.
3. **Date-monotonicity / PIT-safety** — PASS. **0 of 94,821 tidy keys have available_date before period_end.** This is the one that matters most and it is clean.
4. **Spot-check 5 known results vs actual announcement dates** — 3 PASS, 1 FLAGGED, 1 INCONCLUSIVE (not a failure, a search-coverage gap):
   - TCS, period_end 2011-03-31 (Annual): our date 21-Apr-2011. External web search independently confirms "TCS announced its Q4 FY2011 results on April 21, 2011." **EXACT MATCH.**
   - INFY, period_end 2014-06-30: our date 11-Jul-2014. Confirmed via SEC 6-K filings (Infosys ADR filer) dated 11-Jul-2014. **EXACT MATCH.**
   - RELIANCE, period_end 2019-09-30: our date 18-Oct-2019. Matches the prior Kavya session's already-independently-verified value from a different route (SCOUT_PRE2020_PIT_20260713.md: "18-Oct-2019 20:50:42"). **EXACT MATCH.**
   - TATASTEEL, period_end 2013-06-30 (Consolidated): our date (exchange broadCastDate) 19-Aug-2013. Tata Steel's own investor-relations press release for this exact quarter is a PDF explicitly dated "August 13, 2013" (tatasteel.com/media/1273/q1-fy13-14.pdf). **6-day gap, FLAGGED not failed** — verified this is not our pipeline (the raw rows show both standalone and consolidated NSE disclosures broadcast within the same second on 19-Aug, no earlier row exists on our side). Direction is PIT-safe (our date is LATER than the company's own release, i.e. conservative), but it means "exchange broadCastDate = first public disclosure" is not a universal identity — recorded as a landmine.
   - HDFCBANK, period_end 2012-12-31: our date 18-Jan-2013. Web search kept surfacing HDFC-the-housing-financier and other years' HDFC Bank Q3 results instead of confirming this specific date — **inconclusive, no independent source found either way**, not reported as a pass.
5. **Survivorship** — PASS, confirmed NOT current-listing-only. See delisted names above, each independently cross-checked against our own bhavcopy ground truth (not just presence in an older reference file — several of these, e.g. RAJESHEXPO/VSTTILLERS, are red herrings that turned out to still be listed, which is why the bhavcopy last-traded-date check was done rather than trusting name-recognition alone).
6. **Overlap test vs `unified_quarterly_pit`** (2020-2023 focus, but run across the full old dataset) — see below, this is the most consequential finding for how the firm should use this data.

## Overlap test: does this change what we thought we knew?
Matched 24,597 of 31,891 old rows (77.1%) to a (symbol, quarter_end) in the new tidy data. Critically, **the old dataset is not uniformly "inferred from a 90-day lag"** — it carries a `date_source` tag, and the true picture is:

| old date_source | share of old dataset | matched rows | diff vs new real date |
|---|---|---|---|
| `nse_broadcast` (already claimed real) | 77.0% (24,546 rows) | 24,533 | **0 days, every single row, 100% exact.** This tag was already trustworthy. |
| `conservative_lag_50d` (the actual guess — flat 50 days, not 90) | 13.8% (4,390 rows) | 54 | mean +52.5d, median +5d, **87% off by >5 days, max 992 days.** Where checkable, the guess was frequently wrong, sometimes by years. |
| `board_meeting` | 9.3% (2,955 rows) | 10 | median +1 day (board approval ≈ same-day broadcast), one 432-day outlier — small sample, largely fine. |

Read honestly: this pull's biggest service to the *existing* dataset is validating that its majority tag (`nse_broadcast`) was already correct — not fixing a widespread error. The genuinely risky tag (`conservative_lag_50d`) is confirmed unreliable when it can be checked, but the checkable overlap is thin: only 54 of 3,957 `conservative_lag_50d` rows in the new source's well-covered 2020-2023 window found an exact quarter match (48.5% of those symbols appear *somewhere* in the new data, just not on that exact quarter — per-symbol/quarter gaps remain even inside "good" years, concentrated in smaller-cap names). **This new source complements but does not fully replace the conservative-lag reconstruction — some quarters will still need a fallback rule.**

Symbol-coverage comparison, old vs new, by quarter/period-end year (the headline number):
| year | old symbols | new symbols |
|---|---|---|
| 2011-2019 | 0-78 | 1,584-1,692 |
| 2020-2023 | 1,850-2,245 | 1,706-2,023 |
| 2024 | 495 | 2,135 |
| 2025-2026 | 489-494 | 0 |

## Verdict: USE (with the coverage-cliff caveat), catalog entry filed
Full entry added to `DATA_CATALOG.md` (Fundamentals section) and a new landmine (#7) added to `DATA_QUALITY_RULES.md` covering the coverage cliff, the broadcast-vs-press-release lag, and the dead-XBRL-link-for-old-filings finding (xbrl field is present back to the empirical floor but the value is a placeholder `.../xbrl/-` for pre-~2017 rows, not a usable document link).

**Not done in this pass, by design:** merging these real dates into `unified_quarterly_pit.parquet` itself. That file is what strategies actually read; per the D-009 protocol ("Principal approves go-live" before bulk ingestion) and the task's "touch no model file" instruction, this report proposes the merge but does not execute it. Recommended merge rule for whoever approves it: prefer the new real date wherever a (symbol, quarter_end) match exists (especially replacing `conservative_lag_50d` rows), keep the old value otherwise, tag provenance so `nse_broadcast`-vs-`real_nse_broadcast` is still distinguishable later.

Backups: this dataset lives under the shared `datasets/` root, covered by the existing OneDrive continuous-sync layer (BACKUP_POLICY.md layer 1) automatically; it qualifies as a "critical derived set" for the weekly manual snapshot layer (layer 3) — flagging for inclusion in the next snapshot pass, not executed here (that is a recurring ops cadence action, not a one-time gate item).
