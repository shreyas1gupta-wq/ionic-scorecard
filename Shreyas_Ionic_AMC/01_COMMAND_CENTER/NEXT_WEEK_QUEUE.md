# NEXT WEEK QUEUE — explicitly deferred by the Principal, 2026-07-26 (expanded round 2 same day)
Read this at session start alongside CURRENT_STATE.md until it's empty. Each item: DO NOT
EXECUTE until its stated timing; check off + move to SESSION_JOURNAL when done, don't delete
silently. Principal's own words are quoted where useful so intent isn't reinterpreted.

## Timing bands
- **NEXT WEEK** (week of 2026-08-03): items 1 (expanded: backtest+better-rule search for BOTH
  frameworks, contradiction check, analyst+FM escalation, CSV buy-readiness + random audit),
  2(code), 3, 6(7-month hard No-View floor, confirm round-4-vs-round-2 reading + graduation
  trigger), 6b(engine-level 6mo enforcement fix), 7, 8, 9, 10, 11
- **NEXT-TO-NEXT WEEK** (week of 2026-08-10, token budget permitting): item 5-bundle (a,b,c)

---

## 1. Complete the QFRA-1 + QFRA-2 Sell logic + integration [NEXT WEEK] (expanded 2026-07-26 round 2)
Principal (round 1): "qfra 2 we do not have backtesting for sell recommendations, save the
task for the sell task we will do it next week." Principal (round 2, same day): "can you
backtest that part or find a better qfra 1 and qfra 2 sell rule [add this task for next
week]... for qfra 2 make sure it is not the case that qfra 1 gives sell and qfra shows it as
A catg with high score contradictory, check if we can create qfra 2 sell rules and
backtests — lets complete qfra 1 2 integration and sell logics... use analyst+fm in case of
doubt for exception edge cases etc."

**Scope, five sub-tasks, all NEXT WEEK, none done yet:**

a. **Backtest the EXISTING QFRA-1 sell rule** (CJ<0 AND PK quadrant-4) properly — the anchor-
   pair study validated the BUY side (rank/HC) but the SELL side has never been independently
   backtested on its own hit-rate/forward-underperformance.

b. **Backtest QFRA-2's implied sell rule** (`loser_flags>0 OR qfra_score<40`, currently just
   an adapter-level invention with zero validation) — design a proper backtest (hit-rate,
   forward excess return, false-positive rate), same rigor as the QFRA-1 capture-ratio /
   anchor-pair studies.

c. **Explicitly try to find a BETTER sell rule for BOTH frameworks**, not only validate the
   current ones — e.g. test alternative thresholds/quadrant combinations for QFRA-1 (the
   PK=3 mean-reversion finding from round 1 already shows the naive "sell the worst quadrant"
   instinct is wrong — there may be other naive rules worth testing and rejecting/improving
   the same way), and test alternative QFRA-2 score/flag cutoffs against realized outcomes
   rather than assuming 40/loser_flags is optimal.

d. **Contradiction check across the two frameworks, mandatory going forward:** it must NEVER
   silently happen that QFRA-1 says SELL on a fund while QFRA-2 shows the SAME fund in a
   high-score/"A"-grade bucket (or vice versa) without that disagreement being surfaced. Build
   an explicit reconciliation step: for every fund with recommendations from both frameworks,
   flag any case where one side's Sell/low-score and the other side's high grade/Buy-equivalent
   materially disagree — do not just default silently to Hold (the current merge rule) without
   ALSO logging the disagreement somewhere visible (MF_RECOMMENDATIONS.md or a dedicated
   contradictions report) so a human notices the pattern, not just the individual fund.

e. **Genuinely ambiguous/edge cases → Analyst + FM, not silent auto-resolution.** Where the
   backtest/contradiction-check leaves a real judgment call (e.g. the two frameworks disagree
   and the data doesn't cleanly favor one side, or a fund sits right at a threshold), route to
   the Analyst (sector coverage) + FM sign-off layer — same governance pattern as the existing
   escalation mechanism for stock calls (`ESCALATIONS_FOR_PRINCIPAL.md` / pf_state
   `escalation: true`) — rather than letting an algorithmic default decide silently.

**Governance layering (keep separate, don't conflate):** the STANDING METHOD (whatever sell
rule the backtest validates, and the resulting QFRA-1/QFRA-2 merge logic) needs CEO+CIO D-025
ratification once validated. Individual CASE-BY-CASE ambiguous funds during actual runs go to
Analyst+FM, not CEO+CIO — that's a different, lighter-weight escalation for one-off exceptions,
not a change to the standing rule. Do not ship any NEW QFRA-2-driven Sell call to a client
until the standing rule lands (existing/ratified calls like RELIANCE are unaffected — that
came from the STOCK scorecard, not QFRA-2).

**Also folded in here (same integration work, Principal round 2):**
- The saved recommendations CSV (`save_mf_recommendations.py` output) **must always carry a
  populated set of BUY-rated funds for BOTH QFRA-1 and QFRA-2** ready to hand over — not just
  Hold/Sell — so the Principal can pull current buy candidates from either framework on demand
  without a fresh run. Verify this is already true (the CSV should already include BUY rows;
  audit whether both frameworks' BUY sets are complete/current) and keep it true going forward.
- **Random spot-check the CSV against the rule:** for a random sample of funds each save run,
  independently recompute (by hand or a small checker script) what the stated recommendation
  rule SHOULD produce, and confirm the saved CSV's recommendation actually matches — a
  lightweight recurring audit, not a one-time check, so a future silent rule/code drift gets
  caught.

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
Principal (round 1): "less than 1y funds but alpha>-1% can be added into Hold while <-1% can
be added as No View (if we want this No View in some stocks, like 15-30 stocks out of 750
stocks universe we can do that aswell)." Principal (round 2, same day): "<1y history keep it
basis alpha if >-1% alpha say hold else say noview but we have to check when they complete
1y or so. qfra 1/2 i think has higher threshold of 2/3y for buy recom but here we are just
giving hold/sell calls."

**Exact spec as given:**
**STATUS: rule tightened twice since first specified — round 4 (below) is CURRENT. Rounds
2-3 kept underneath for the reasoning trail; do not build from the round-2 alpha-branch
alone without reading round 4.**

### Round 4 (Principal, CURRENT RULE): a hard 7-month floor, universal, alpha-independent
Principal: "no mimimum 7 months keep it hard rule for any recommendation for MF, if less
than that keep no view if irrespective of QFRA 1/2."
  - **<7 months of track record → "No View", full stop.** Hard, unconditional: no alpha
    check, no branching. This applies to ANY MF recommendation (Sell/Hold/Buy alike) and
    is **irrespective of QFRA-1/QFRA-2** — i.e. it overrides whatever either engine's raw
    score/verdict would otherwise say; a fund under 7 months simply gets no house view.
  - **This is DIFFERENT from QFRA-1's own internal 6-month computational floor** (the FN/HC
    calculation's own window requirement, §method / item 6b below) — that's an ENGINE-level
    data requirement for the math to run at all; this 7-month figure is a separate, slightly
    stricter, CLIENT-FACING business floor for issuing any recommendation, applied uniformly
    across both frameworks regardless of each engine's own internal minimum.
  - **MY READING, FLAG IF WRONG:** this round-4 hard rule is read as SUPERSEDING round 2's
    alpha-branch (alpha>-1%→Hold, alpha<-1%→No View) for the sub-1-year gap — i.e. the
    simpler operative rule is now: <7mo → No View (hard, no alpha check); ≥7mo → normal
    QFRA-1/QFRA-2-driven Sell/Hold/Buy, with no separate 7mo-12mo alpha-gated tier. If the
    Principal instead meant the 7-month rule to be an ADDITIONAL absolute floor sitting
    UNDER the round-2 alpha branch (i.e. <7mo→No View hard; 7mo-12mo→ round-2's alpha check
    still applies; ≥12mo→normal), correct this line before building — zero cost to fix since
    nothing is built yet, but the two readings produce different code.
  - The recurring re-check / graduation requirement from round 2 (below) still stands
    regardless of which reading is correct — replace "1 year" with "7 months" as the
    graduation trigger if round 4 fully supersedes round 2.
  - The optional STOCK_SCORECARD_750 extension (15-30 of 750 names, round 1) is unaffected
    by this refinement — still optional, still needs a separate go-ahead.

### Round 2 (superseded by round 4 above unless flagged wrong): original spec, kept for trail
  - Fund/stock has <1 year of track record (engine already flags young funds under ~30
    months in `save_mf_recommendations.py`'s `young_fund_months` — the <1y threshold here
    was TIGHTER and MF-specific; round 4 replaces "<1y" with "<7mo").
  - alpha > -1% → Hold (young + not meaningfully negative = treat as a normal Hold).
  - alpha < -1% → "No View" (young + meaningfully negative = a NEW verdict, distinct
    from Sell/Hold/Trim/Exit — signals "insufficient record to call, watch it" rather than
    forcing a premature Sell or a falsely-reassuring Hold).
  - Optionally extend the same "No View" bucket to the STOCK_SCORECARD_750 universe for
    names with inadequate history/coverage — Principal estimates ~15-30 of 750 could
    qualify. Explicitly optional ("if we want this... we can do that as well") — needs a
    separate go-ahead before touching the stock engine.
  - **A recurring re-check, not a one-time tag.** A fund/stock tagged Hold or No View under
    the young-fund rule must be re-evaluated automatically once it CROSSES the age
    threshold, so it graduates into the normal Sell/Hold rules rather than staying frozen in
    the provisional bucket forever. Implementation idea: compute each covered name's age at
    every standing cadence event (MF: the monthly NAV refresh or the Apr/Oct QFRA runs;
    stocks: the weekly re-score once it's live) and flip any name that has now crossed the
    threshold out of the young-fund path into the standard verdict logic. Needs a concrete
    trigger point decided next week (which cadence event owns the re-check) — do not build
    the classification without also building this graduation check, or it becomes a silent
    second staleness bug exactly like the pf_state one this session just found.

### Round 3 (resolved facts, still true, informs round 4's reasoning above)
Principal: "qfra 1 requires minimum 6month of navs and qfra 2 has its score which prefers
>3y funds." Confirmed distinct mechanics, not the same kind of gate:
  - **QFRA-1 = a HARD data-availability floor at 6 months.** This is the SAME 6-calendar-
    month window already at the core of the method (§method step 1: "6M downside capture
    (FN)") — a fund literally cannot get FN/HC computed, and therefore cannot be ranked
    for BUY, without a full 6-month window. This is NOT the ~24-month blank-gate bug
    (that's a separate, unrelated defect further down the pipeline); it's the intended
    minimum for the core calculation itself.
  - **QFRA-2 = a SOFT scoring preference, not a hard gate, toward >3y funds.** Its score
    naturally tilts against younger funds (3y/5y-based metrics, statistical-significance
    effects of longer windows) without literally blocking a <3y fund from being scored —
    it just tends to score lower / not reach ACTIVE.
  - Round 4's 7-month client-facing floor sits slightly ABOVE QFRA-1's own 6-month engine
    floor (a small buffer beyond the bare data minimum before the firm puts a view in front
    of a client) and is applied even where QFRA-2 might already be soft-scoring a young fund
    low on its own — round 4 makes the outcome explicit and uniform (No View) rather than
    relying on QFRA-2's score happening to land low enough.

**Before building:** confirm (a) which reading of round 4 vs round 2 is correct (flagged
above), (b) whether "No View" needs its own pill color/kind in the NDPMS deck (verdict
vocabulary currently hardcoded to Hold/Trim/Switch/Redeem-to-Direct/Exit/Sell everywhere —
adding a 6th value touches slidekit + every fund module), (c) whether "No View" positions
should still render a scorecard slide or be silently excluded like a Hold, (d) the exact
graduation trigger point (7mo? 12mo? which cadence event owns the check), (e) whether "7
months" is calendar-days or trading-days from first NAV.

## 6b. QFRA-1's 6-month floor is INTENDED but not actually ENFORCED in code [NEXT WEEK]
Directly surfaced by confirming item 6's scope question. The Principal just confirmed the
6-month NAV window is a real, intended minimum for QFRA-1 (not incidental) — but the method
audit (2026-07-26, major finding) found the ENGINE does not hard-gate on it: `mf_capture_recomm.py`
computes FN/HC over whatever window exists, skipping individual NaN days (factor 1.0) rather
than requiring the full 6-month span end-to-end. A fund with only 2 of 6 months of real NAV
history currently gets FN/HC computed on a MISMATCHED window (fund partial, benchmark full),
which understates FN and can spuriously pass the downside filter — i.e. a fund thinner than
the Principal's own stated 6-month minimum can currently sneak into a BUY rank. Task: require
non-NaN fund NAV at the window's start (`apos[r-6]`) before computing FN/HC for that fund at
that anchor; emit blank/ineligible otherwise, matching what's now confirmed as the intended
rule rather than the current NaN-tolerant approximation.
**Relationship to item 6's round-4 rule:** this is QFRA-1's OWN 6-month engine-level data
floor (fixing how FN/HC is computed internally); item 6's 7-month rule is the separate,
universal, CLIENT-FACING "No View" floor applied on top, across both frameworks. Fixing this
does not replace building that — both are needed.

## 6c. QFRA-2 short-history overlay: score the 7mo-3y gap instead of dropping it [NEXT WEEK — confirm spec, do not build yet]
Principal (2026-07-27), reacting to the MERIT-grade explanation: "Override to D --> new fund
we can improve instead of giving a D rating, less than 7 month we already had hold vs no view
and for other we can have some view basis the fund manager track record and recent
performance etc and other metrics we were looking." Decided same session: build the manager-
track-record data now; spec the overlay mechanism first, build the scoring code later.

**CORRECTION to item 6 round 3's "resolved fact" — QFRA-2 is NOT a soft gate on <3y funds,
it's a hard one.** Round 3 above says "QFRA-2 = a SOFT scoring preference... without literally
blocking a <3y fund from being scored." Code reading of `final_model.py` line 98
(`if len(fr) < C.MIN_HISTORY_D: continue`, MIN_HISTORY_D = 756 trading days = 3y) shows a fund
under 3 years of return history is dropped BEFORE it ever enters the scoring table — it never
gets a `score`, `qfra_score`, `merit_grade`, or `sentinel` status; it is simply absent from
`FINAL_recommendations.csv` / `QFRA2_current.csv`. Consequently `gates.py`'s `history_tier()`
"<3y -> watchlist, ceiling Low" branch and the `new_fund`/`merit_grade='D'` override are
**unreachable dead code under the current pipeline** — nothing that reaches `apply_gates()`
can ever have n_obs < 756, because the upstream filter already removed it. Net effect today:
a fund between the firm's 7-month "No View" floor and QFRA-2's 3-year cut gets **nothing** —
not a D grade, not a Hold, just absence from the recommendation file. This is the actual gap
item 6c fixes, not a grading-severity complaint.

**Data check done this session — manager track record IS buildable, don't need a new source:**
`Mf_qfra2/data/fund_metadata_full.csv` (one level above the engine's own `mr_x_framework/data/`,
so it survives even when the engine dir is refreshed) has `Fund_Manager` + `Inception_Date`
complete for all 119 tracked funds (latest snapshot), 75 unique managers, **29 of them running
2+ funds already in our tracked universe** — enough overlap to build a real manager-quality
proxy without fetching anything new. Caveat: this only sees a manager's record on the ~119
funds QFRA-2 itself tracks (8 categories) — not their career at a prior AMC, not debt funds,
not anything outside our universe. A real but partial proxy, not a full career history; say so
wherever it's surfaced, don't oversell it as complete.

**Proposed mechanism (post-processing overlay — does NOT touch `config.py`/`final_model.py`,
so the "frozen, do not retune" rule stands; matches how item 6's own 7-month floor is meant to
sit on top of both engines' output rather than inside them):**
  1. Run the frozen engine as-is (`final_model.py` -> `qfra2_step4.py`), unchanged.
  2. Separately, for each fund with 7 months <= age < 3 years (from `Inception_Date`) that is
     therefore ABSENT from the engine's own output: compute the SAME core features it already
     uses (info_ratio, down_capture, calmar, mom_12_1) over whatever window the fund actually
     has, instead of the fixed 756-day alpha window — same idea QFRA-1 already applies at 6
     months, just reusing QFRA-2's own feature definitions instead of inventing new ones.
  3. **Manager-quality proxy = reuse the frozen engine's own validated output, don't build a
     parallel scorer.** If the fund's manager (from `Fund_Manager`) runs any OTHER fund that
     DID clear the 3y gate and has a real `qfra_score` in this run's output, use that other
     fund's score (simple average if more than one) as the manager-track-record signal. If the
     manager has no other qualifying fund, there is no manager signal for this fund — fall back
     to the fund's own short-window metric alone, flagged lower-confidence.
  4. **Bayesian shrinkage blend, continuous at the 3-year boundary:** weight the fund's own
     short-window metric by `w = min(1, n_obs / 756)` and the manager-proxy by `(1-w)` (when a
     manager signal exists; else the fund's own metric gets full weight regardless of `w`, just
     labeled low-confidence). At exactly 3y, w=1 and this MUST reduce to exactly what the frozen
     engine would compute on its own — no discontinuity at the handoff.
  5. **Output as a DISTINCT "Provisional" tier, never blended into the frozen QFRA 0-100 scale
     or the A-D MERIT letters** — e.g. `merit_grade='P'` with its own `qfra_score=None` (or a
     separately-labeled provisional score) so nobody mistakes a ~7mo-old fund's necessarily
     noisier read for the validated, OOS-backtested measurement the A-D grades represent.
     Conviction ceiling for anything in this tier should stay capped at Low regardless of how
     good the blended number looks — this overlay's own hit rate can't realistically be OOS-
     validated (the sample of "funds that were once 7mo-3y old with a known manager history" is
     small and survivorship-prone), so treat its output as a lean, not a score to act on size with.

**Before building — needs Principal confirmation (same class of open question as item 6):**
  (a) exact shrinkage weight formula above, or a different blend Principal prefers;
  (b) what happens when the manager has ZERO other qualifying funds — silent fund-only fallback
      (as drafted) or should THOSE funds stay "No View" until they age past 3y themselves;
  (c) does "Provisional/P" need its own pill color in the NDPMS deck (same slidekit/module-touch
      cost as item 6's "No View" pill did — this is a SEPARATE addition, not reuse of that one);
  (d) should a fund ever GRADUATE from Provisional to a real letter grade before the frozen
      engine itself picks it up at 3y, or is 3y the only graduation trigger;
  (e) confirm whether this fully supersedes today's silent-absence behavior for the whole
      7mo-3y band, or should only apply where a manager signal exists (drafted: applies either
      way, fund-only fallback covers the no-manager-signal case).

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
