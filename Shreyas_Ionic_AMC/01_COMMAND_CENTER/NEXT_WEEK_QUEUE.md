# NEXT WEEK QUEUE — explicitly deferred by the Principal, 2026-07-26
Read this at session start alongside CURRENT_STATE.md until it's empty. Each item: DO NOT
EXECUTE until its stated timing; check off + move to SESSION_JOURNAL when done, don't delete
silently. Principal's own words are quoted where useful so intent isn't reinterpreted.

## Timing bands
- **NEXT WEEK** (week of 2026-08-03): items 1, 3(code), 5, 9(spec confirm), 10, 11, 12, 13, 14, 15
- **NEXT-TO-NEXT WEEK** (week of 2026-08-10, token budget permitting): item 6-bundle (6,7,8)

---

## 1. QFRA-2 Sell-recommendation backtest [NEXT WEEK]
Principal: "qfra 2 we do not have backtesting for sell recommendations, save the task for the
sell task we will do it next week."
Context: the deck's fund_ctx_adapter currently derives a client-facing Sell-lean from
QFRA-2 (`loser_flags>0 OR qfra_score<40`) with NO backtest behind it and no CEO+CIO
ratification — this is a business-rule invention, not a validated method (audit 2026-07-26
critical/major finding). Task: design + run a backtest of QFRA-2's implied Sell rule
(similar in spirit to the anchor-pair / capture-ratio backtests already done for QFRA-1),
then take the validated rule to CEO+CIO for D-025 sign-off. Do not ship any NEW QFRA-2-driven
Sell call to a client until this lands (existing/ratified calls like RELIANCE are unaffected —
that came from the STOCK scorecard, not QFRA-2).

## 2. Category-wise benchmark map SHOWN IN THE GRAPH (NDPMS deck) [NEXT WEEK — code]
Principal, re: the funds_equity.py screenshot showing "13" as an identical benchmark bar
for every fund: "we will need catg wise bm map and show in graph as well (not this time but
add in skills and from next time)."
**Note: the underlying DATA was already fixed in the 2026-07-26 session** (every fund is
scored vs its own SEBI category benchmark — large=N100, largemid=N250, mid=Midcap150,
flexi=N500, multi=Multicap 50:25:25, small=Smallcap250, hybrid=N50 Hybrid 65:35; the "13"
in the screenshot is from BEFORE that fix). What's still open is a VISUAL ask: show which
benchmark applies to which fund directly in the chart (not just in the source-line text) —
e.g. a per-bar label, x-axis subscript, or a small fund→benchmark legend table. Documented
in the ndpms-deck skill §PENDING. Build next time; do not touch this session.

## 3. TRI rebuild of the MF Dashboard's Indices sheet [NEXT WEEK]
Principal clarified: "note for the nav i needed (that was for different purpose) requires
only price nav, this tri you can use in MF later next week." → **FACTOR_NAVS.xlsx is
CORRECT AS-IS (price/PRI, different purpose, no change needed).** The TRI fix applies ONLY
to the MF Dashboard's `Indices` sheet (confirmed PRI 2026-07-26 audit: NIFTY 500 = 21,580.9
on 2025-01-31 = price index, TRI would be ~33k). Effect while unfixed: CJ 12M excess
flattered ~1.2-1.5%/yr, SELLs systematically understated across all 6 QFRA-1 categories.
Task next week: rebuild Indices from an official TRI series (factor-indices skill's
NSE-official layer already has these, or niftyindices from home network), D-009 spot-check,
re-verify LO1 + QZ on the TRI recompute. Must land before the Oct-end 2026 QFRA run
(qfra1-rerun skill has the full detail).

## 4. NSDL CAS sample for the intake parser [LEFT INDEFINITELY]
Principal: "leave that for now." No timing given — do not chase; resume only when a sample
CAS PDF is supplied.

## 5. Weekly stock re-score bundle: router patch + pf_state re-seed + earnings feed [NEXT-TO-NEXT WEEK — token budget]
Principal: "that weekly run we will run from next to next week, currently we are short of
tokens." Three sub-items, bundle together (all block the same Thursday cron):
  a. **run_weekly_v1.py patch** — still enforces the SUPERSEDED "Sell→Hold only" clamp
     instead of the ratified asymmetric 90/60 bars (Amendment 6); also hardcoded
     `as_of='2026-07-20'` defaults in 4 places and a documented-but-missing `apply_carry()`.
  b. **pf_state re-seed** — 125 stock JSON state files predate the 2026-07-25/26 recheck.
     RELIANCE.json still shows `analyst.rec: "Hold"` (stale; ratified verdict is now SELL,
     see item below) and 66/125 names have no quant baseline at all. Must re-seed from
     `pf_qual_*.json`'s `your_recommendation` field before the router runs, or it will
     silently keep serving stale positions including a stale RELIANCE Hold.
  c. **Earnings feed refresh** — `nse_earnings_dates/` is stale at max 2026-07-03, missing
     every known late-July reporter (BANDHANBNK, IDFCFIRSTB, SUMICHEM, BAJAJHFL, MARUTI,
     ITC, VBL, TMPV). The FULL research lane silently degrades to CARRY without this.
Do NOT run the Thursday weekly stock cron until all three land — currently blocking.

## 6. Young-fund (<1y record) verdict rule — Hold vs "No View" [NEXT WEEK — confirm spec, do not build yet]
Principal: "less than 1y funds but alpha>-1% can be added into Hold while <-1% can be added
as No View (if we want this No View in some stocks, like 15-30 stocks out of 750 stocks
universe we can do that aswell)."
**Exact spec as given:**
  - Fund/stock has <1 year of track record (engine already flags young funds under ~30
    months in `save_mf_recommendations.py`'s `young_fund_months` — the <1y threshold here
    is TIGHTER and MF-specific; confirm whether to use 12 months exactly or reuse the
    existing 30-month flag column with a new cutoff).
  - **alpha > -1% → Hold** (young + not meaningfully negative = treat as a normal Hold).
  - **alpha < -1% → "No View"** (young + meaningfully negative = a NEW verdict, distinct
    from Sell/Hold/Trim/Exit — signals "insufficient record to call, watch it" rather than
    forcing a premature Sell or an falsely-reassuring Hold).
  - Optionally extend the same "No View" bucket to the STOCK_SCORECARD_750 universe for
    names with inadequate history/coverage — Principal estimates ~15-30 of 750 could
    qualify. Explicitly optional ("if we want this... we can do that as well") — needs a
    separate go-ahead before touching the stock engine.
**Before building:** confirm (a) the exact age cutoff and whether it's calendar-days or
trading-days, (b) whether "No View" needs its own pill color/kind in the NDPMS deck (verdict
vocabulary currently hardcoded to Hold/Trim/Switch/Redeem-to-Direct/Exit/Sell everywhere —
adding a 6th value touches slidekit + every fund module), (c) whether "No View" positions
should still render a scorecard slide or be silently excluded like a Hold.

## 7. save_mf_recommendations.py polish [NEXT WEEK]
From the method audit (majors/minors, all mechanical):
  a. Carry `loser_flags` into the saved CSV (currently dropped) + add a derived
     `qfra2_call` column in Hold/Sell vocabulary — right now only the raw QFRA-2 verdict
     (ACTIVE/INDEX CORE) is joined, so the saved file can't itself evaluate the
     dual-framework Sell rule without re-deriving it.
  b. Footnote every BUY emitted at <100% coverage in `MF_RECOMMENDATIONS.md` (e.g. "rank
     computed over N of M funds") — or raise the BUY-emission gate from 80% to ~95%.
  c. Young-fund age should be computed to the CHOSEN (walked-back) anchor per category, not
     to the raw data cut — currently a fund young AT THE ANCHOR can go unflagged if the
     data cut is much later.
  d. Replace the bare `except Exception: continue` in the anchor walk-back loop with one
     that prints the actual exception before falling through — currently a benchmark rename
     or structural sheet change just surfaces as "no anchor with >=80% coverage" with no
     clue why.

## 8. Move QFRA2_current.csv into the firm tree [NEXT WEEK]
Both `fund_ctx_adapter.py` and `save_mf_recommendations.py` hardcode the absolute path
`C:\Users\Shreyas.1Gupta\Downloads\Mf_qfra2-...\QFRA2_current.csv` — outside the repo, outside
backup policy, not in DATA_CATALOG, and one Downloads cleanup breaks the whole MF
recommendation chain silently. Task: copy the file into `05_DATA_OFFICE/` (e.g.
`05_DATA_OFFICE/qfra2_outputs/QFRA2_current.csv`), add a DATA_CATALOG.md entry (source =
QFRA-2 engine output, owner, refresh cadence = tied to the Apr/Oct qfra2-rerun), and update
both hardcoded paths to the new location. Ideally becomes a standing copy-step at the end of
every qfra2-rerun.

## 9. Run --verify on all 6 QFRA-1 categories at production anchors [NEXT WEEK]
Current verification (mf_capture_recomm.py `--verify`) has only run label-level (QZ string)
diffs for 2 of 6 categories (small, flexi), at the anchors those categories used — never for
large/largemid/mid/multi, and never at the WALKED-BACK anchors `save_mf_recommendations.py`
actually used in the 2026-07-26 save (large=2025-05-31). Task: run `--verify` on all 6
categories at those exact anchors, plus one numeric FN/HC spot-check (not just the QZ label),
before the Oct-end 2026 production run.

## 10. Share the coverage walk-back between the deck adapter and the save script [NEXT WEEK]
`save_mf_recommendations.py` has the >=80%-coverage anchor walk-back; `fund_ctx_adapter.py`
(the deck's fund-call source) does not — it reads the raw latest anchor with no walk-back, so
on a given day the deck's fund calls and the saved recommendation file can silently disagree
on the same fund. Task: move the walk-back logic into `mf_capture_recomm.py` itself (shared
by both callers) so there's exactly one anchor-selection implementation.

## 11. Persona updates: Sanjay Kulkarni + sector analyst desk [NEXT WEEK]
  a. **fm-fundamental-sanjay-kulkarni.md** — owns the client-scorecard FM pass but his
     charter predates that whole duty. Add: the asymmetric 90/60 override bars (Amendment
     6), default-below-40-is-Sell + 40-50 watch zone, the dual-framework fund-Sell rule, the
     tax-inertia rule, and a pointer to the weekly Thu cadence (V1_METHODOLOGY.md).
  b. **analyst-industrials-rohan-deshmukh.md** (+ a shared line to all 5 sector analysts) —
     Rohan is the named owner of the commodity-cycle-lens duty (Amendment 2, ratified
     2026-07-25) but his persona has zero trace of it. Add the duty explicitly, plus a
     shared pointer for all analysts to ANALYST_KIT/SKILL.md + the Amendment 6 bars, since
     none of the five currently reference the pf_qual schema or override bars that bind
     their recommendations.

---
**Do not add new items to this file without a clear Principal instruction and a timing band.**
When an item completes, move its summary into SESSION_JOURNAL.md and delete the row here.
