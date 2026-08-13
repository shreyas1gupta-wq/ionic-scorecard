# PRE-REGISTRATION — Event-window premium SELLING (handoff from Arm B, 2026-07-31)
Owner: Aakash Jain (Structurer). Written BEFORE the placebo is run. Per D-035, no tuning after
results are seen.

## Question
Arm B (option buying) found three scheduled-event windows where BUYING an ATM straddle lost money,
and where the loss is NOT cost-dominated (gross edge exceeds the ~3.538-pt round-trip cost either
way) — meaning the reversal (SELL the straddle instead) is a legitimate candidate, not a friction
artifact. Does SELLING the ATM straddle into these three windows produce a real, placebo-beating
edge, honestly powered?

## Windows under test (Arm B's construction, reused verbatim — not re-designed)
1. **EVENT_BUDGET**: entry T-2 trading sessions before Union Budget day, exit T (event day) close.
   n=6 candidates (2021 excluded — before HF weekly-option coverage starts 2021-05-24).
2. **EVENT_FED**: entry T-2 sessions before FOMC decision day, exit T+1 session close (IST
   next-session reaction). n=36 (of 39 candidates; 3 dropped for no matching expiry/data).
3. **IV_TERM_CHEAP**: entry on the day INDIA VIX percentile (expanding, 10yr) <= q20 of the
   build-era AND monthly IV term-slope <= 0 (flat/inverted), 5-trading-day hold. n=6.

Structure for all three: STRADDLE_ATM_EOD_MULTIDAY (ATM CE+PE, EOD close-to-close mark, no
intraday stop/trail — hence `pathsafe` is NOT invoked: there is no path-dependent stop/trail being
resolved, only two known close-price marks per trade, so R2/R3 of the pathsafe protocol do not
apply; this is stated explicitly rather than silently skipped).

## Calendar verification (this desk's own pass, not inherited blindly)
Spot-checked the two highest-stakes, most-recent BUDGET dates against live web sources (not just
inherited from Arm B's calendar file):
- **2025-02-01**: confirmed Union Budget FY26, and confirmed NSE/BSE ran a SPECIAL SATURDAY session
  (regular hours 09:15-15:30) — an unusual trading day, flagged as a liquidity caveat below.
- **2026-02-01**: confirmed Union Budget FY27, and confirmed the date is a SUNDAY and NSE/BSE ran a
  special Sunday session — even more unusual; flagged as a liquidity caveat below.
- **2024-07-23** (full Budget FY25, post-election): confirmed via independent sources (capital-gains
  tax reform effective date cited as 2024-07-23 by multiple tax advisories) — matches Arm B's date
  exactly.
- FOMC 2026 dates spot-checked against federalreserve.gov press-conference pages: **2026-04-29**
  (confirmed, meeting 04-28/29) and **2026-06-17** (confirmed, meeting 06-16/17) both match Arm B's
  decision-day convention exactly (decision = LAST day of a 2-day meeting).
- Earlier years' Budget (2022/2023, both Feb-1) and the bulk of 2021-2025 FOMC dates were NOT
  individually re-verified against a live source this pass (time-budget tradeoff) — these are
  well-established, multiply-corroborated, standing calendar facts (Budget Feb-1 practice since
  2017; FOMC calendars published 1yr+ in advance and never observed to change) and were already
  sourced by Arm B from federalreserve.gov directly for FED. **Not independently re-fetched here —
  disclosed, not hidden.**
- **No RBI or ELECTION date changes proposed** — those windows are not part of this handoff's three
  cells; RBI's own verdict ("EVENT_RBI probably flat", -8.4pts t=-0.40 n=30) and ELECTION's verdict
  ("untested-and-fragile", single dominant 2024-06-04 trade, held-out 2026 flips to -171) both stand
  as reported by Arm B, unmodified.

## Placebo design (the missing control Arm B did not run)
For each of the three real cells, build a POOL of random (entry_day, exit_day) pairs with the SAME
hold length (2 / 3 / 5 trading sessions respectively), drawn from NIFTY trading days that fall
OUTSIDE a +/-5-trading-session buffer around every date in `events_scheduled.csv` (BUDGET+FED+RBI+
ELECTION) and outside every window in `earnings_clusters.csv` (>=3-of-top10-NIFTY-weight earnings
in a 5-day span) — i.e. genuinely "quiet" weeks, not just non-event days that happen to sit next to
an event. Extract REAL EOD ATM-straddle prices for the whole pool through the SAME chain.py
extraction pipeline Arm B used (RAM-gated via `chainlock.chain_slot`, one expiry at a time,
`cache_clear()+gc.collect()` between). One extraction pass serves all three cells (resampled after).
- Pool sizes drawn (seeded, `numpy.random.default_rng(20260731)`): 80 quiet-week candidates at
  2-day hold, 120 at 3-day hold, 80 at 5-day hold — every one actually priced from real data, not
  simulated.
- **Test statistic**: mean reversed-net-pts (= -gross_pts - 3.538, same cost convention as Arm B's
  `gross_reversal.py`, applied identically to real and placebo legs so the comparison is apples-to-
  apples).
- **p-value**: bootstrap resample n-sized subsets (n=6, 36, 6) from the matching-hold-length quiet
  pool, WITH replacement, 5000 draws; p = fraction of quiet-pool resampled means >= the real cell's
  mean (one-sided — the hypothesis under test is that the EVENT window is BETTER for a seller than
  an ordinary week, not merely different).
- **IV_TERM_CHEAP at n=6 with 100% profit concentration (one trade) is reported as an ANECDOTE, not
  promoted regardless of placebo outcome** — pre-committed here, before the placebo is run, per the
  coordinator's explicit instruction.

## Kill / promote criteria (fixed now)
- DEAD if placebo p >= 0.10 (one-sided; using a looser-than-usual 0.10 rather than 0.05 given the
  small-n regime deliberately allows EVENT_FED, the only cell with real power, a fair hearing rather
  than being killed by an underpowered threshold — but ANY promotion still requires clearing 0.05).
- **SUGGESTIVE ONLY** (never "certified", never sized) if 0.05 <= p < 0.10 at any n, or if p < 0.05
  but n < 10 (EVENT_BUDGET, IV_TERM_CHEAP both start under this floor by construction — flagged
  in advance, not discovered after the fact).
- EVENT_FED (n=36) is the only cell that COULD in principle earn "FORWARD-TEST CANDIDATE" this pass;
  the other two are pre-committed to at most SUGGESTIVE/ANECDOTE regardless of placebo result,
  because n=6 cannot support more than that under this book's own low-t power-aware convention
  (power != no-effect, but also n=6 != a tradeable frequency floor on its own).
- Concentration >30% single-trade share of profit is FRAGILE per the book's standing hard-kill list
  — EVENT_BUDGET (85.3%) and IV_TERM_CHEAP (100%) are ALREADY fragile by this rule before any
  placebo is run; reported as such regardless of placebo outcome.

## Tail statement requirement (fixed now, Budget window specifically)
Budget day and election-result day are flagged in the brief as the two highest gap-risk sessions on
the Indian calendar. This memo's tail statement must state, for a SHORT ATM straddle (not the
already-tested calendar/strangle structures elsewhere in this book): (a) the physical bound (max
loss on a naked short straddle is unbounded upside, strike-bounded downside), (b) what a genuine
Budget-day directional shock has historically done to NIFTY same-day, and (c) explicitly reference
the firm's own COVID finding (2x-credit stop does not survive a real gap) as the governing analogy
for why a Budget-week short straddle cannot be assumed stop-protected.
