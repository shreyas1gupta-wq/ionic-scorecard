# PROGRESS — Full Nifty-750 quant re-score (TTM v7) + Screener refresh (DESK-100, 2026-07-21)

**Principal orders 2026-07-21:** (1) "fix scores of all nifty 750 stocks and data scrap screener
if needed specially if earning new"; (2) some Q1 FY27 results are out; (3) **"amend score to TTM"**
so the score reflects the latest quarter; (4) weekly cadence = **each Sunday, delta-scrape the
names that reported + refresh commentary, token-efficient** (NOT a full re-pull); (5) after
scoring, wind down softly — agent work (research workflow, top-250 book) deferred to a later
session (low tokens).

## WHAT'S RUNNING NOW
**bg task `b4m135jiv`** = self-finishing chain: `scrape --full` (resumes ~84/751 via _staging/
_done.json) → `promote_screener_staging.py --promote` (D-009 self-gated, backs up live) →
`build_full750_quant.py` (TTM re-score). Writes scores to disk even if my session runs out.
- Output tail file: tasks/b4m135jiv.output. Look for "=== PIPELINE COMPLETE ===".
- Result: `results/full750_scored.csv` (+ full750_quant_build_notes.txt).

## IF THE CHAIN DID NOT FINISH (resume) — re-run this ONE command (all steps resume-safe):
```
cd ".../NIFTY 500"; set PYTHONIOENCODING=utf-8
<py> 05_DATA_OFFICE/scripts/scrape_screener_750.py --full        # resumes from _done.json
<py> 05_DATA_OFFICE/scripts/promote_screener_staging.py --promote
<py> 05_DATA_OFFICE/scripts/build_full750_quant.py
```

## TTM AMENDMENT (v7) — exactly what changed (rest of frozen engine UNCHANGED)
- `revenue_growth_1y` -> TTM revenue YoY (last-4-q / prior-4-q - 1) from screener_quarterly_results.
- `pe_current` (value pillar) -> price / TTM EPS (sum last 4 q EPS).
- TTM-preferred, ANNUAL-FALLBACK (names with <8 q keep the frozen annual calc — no signal lost).
- Unchanged: ROE/ROCE quality, D/E, interest-cov, 3y CAGR, PB, FCF-yield, technicals, ownership,
  all pillar weights / regime tilt / gates / penalty / boost, run_engine ranking.
- **This amends FROZEN_METHODOLOGY v6.3 -> needs Arjun (quant) + Nikhil (red-team) sign-off before
  it's permanent v7; breaks strict comparability w/ the V0 annual track record (documented).**

## SCRIPTS (05_DATA_OFFICE/scripts/, all built + validated this session)
- `scrape_screener_750.py` — SOP scraper; PL/BS/CF + NEW quarterly; picks the variant with the
  most-recent data (fixes COLPAL-class dead-consolidated staleness); bank schema handled; float
  values match existing parquet to the rupee; polite/resume-safe; modes --test/--symbols/
  --symbols-file/--auto-missing/--full.
- `promote_screener_staging.py` — D-009 verify + REPLACE-BY-SYMBOL promote (backs up live; creates
  the new screener_quarterly_results.parquet).
- `build_full750_quant.py` — TTM re-score of all 751; staleness guard; -> full750_scored.csv.

## STATE BEFORE FIX
Universe 751. screener_deep 500 (445 current Mar-2026 / 40 zero / 10 stale / **251 absent**).
Root cause of stale = screener serves dead legacy *consolidated* series; live data on *standalone*
(COLPAL frozen Mar-2010). Fixed + verified (COLPAL/TATAELXSI/3MINDIA/AUBANK now Mar-2026).

## AFTER THE CHAIN COMPLETES (bank, then STOP — no agent work)
1. Sanity-check full750_scored.csv (rec split, coverage, TTM-used count, stale/zero lists).
2. DECISIONS_LOG: new D-xxx = TTM amendment (Principal-directed, pending quant/red-team sign-off).
3. DATA_CATALOG: screener_deep refresh row (2026-07-21, +~250 names to ~750, +quarterly parquet).
4. SCRAPING_SOP §4 refresh ledger: 2026-07-21 full refresh + scraper rehomed + variant-fix +
   weekly-Sunday delta cadence noted. FROZEN_METHODOLOGY: add v7 TTM addendum (pending sign-off).
5. SESSION_JOURNAL + CURRENT_STATE + memory. git commit. Then stop.

## PARKED (next session, has tokens)
- Research workflow (100 top-250 expansion names) — ~17+ pf_qual landed; per-stock saved, resumable.
- Top-250 V1 book assembly (seed pf_state w/ asymmetric clamp; client/analyst Excel). full750_scored
  is now the single quant-truth source for the book.
- Wire the Sunday cadence as an actual scheduled job (session-only crons don't persist).

## GUARDRAILS Sell/Hold/Trim only; quant score = SOLE source of Sell (V1 asymmetric); never
fabricate/label estimates; no real-money trades; MAX 3 parallel agents.
