# WAVE-4 — Coverage-gap hunt + new orthogonal hypotheses (Principal-directed 2026-07-17)

GOAL: find what the ~457-trial program MISSED, generate genuinely NEW orthogonal hypotheses (Fable),
test them (Sonnet), judge (Opus). Composition per Principal: 9 agents at a time = 2 Fable + 6 Sonnet + 1 Opus.

## HONESTY GOVERNOR (enforced in every prompt)
Model is PARKED on multiple-testing (457 trials, DSR≈0). MORE variant-trials worsen it. This wave is
justified ONLY by hunting DISTINCT, orthogonal mechanisms (≤1 refinement each — stop-condition). Any
survivor still needs the forward-test to escape multiple-testing; this wave cannot itself certify anything.

## PHASE A — analysis/generation (3 agents, running)
- [running] Fable/librarian → rnd/wave4/coverage_map.json + COVERAGE_MAP.md  (what's tested vs GAP vs DATA-BLOCKED)
- [running] Fable/rnd-head → rnd/wave4/hypotheses_w4.json + HYPOTHESES_W4.md  (15-20 new orthogonal ideas)
- [running] Opus/quant-head → rnd/wave4/FRONTIER_OPUS.md  (Q1: does more research help? + ranked top directions + DO-NOT-DO)

## PHASE B — testing (dispatch after I merge Phase A → TEST_QUEUE.json)
- 6 Sonnet testers: each takes a slice of TEST_QUEUE, uses rnd/lib/harness.py, writes cards to rnd/cards/.
  HARD GATES: one-day-lag (delta<=0.25) + placebo (|ic|<=0.02). Stop-condition: 1 test + ≤1 refinement, then PARK/KILL.
- 1 Opus judge: red-teams any survivor (regime sub-split, orthogonality vs 7 legs, is-it-real).
- 2 Fable: (i) fold results into coverage_map as they land; (ii) update wave4 checkpoint.

## MERGE RULE (main loop, cheap)
TEST_QUEUE = dedup(hypotheses_w4 ∩ Opus-endorsed ∩ not-already-covered), ranked by priority,
drop anything Opus flags as variant-spam. Cap the wave — do not queue 20 low-EV ideas.

## >>> OPUS FRONTIER VERDICT (2026-07-17) — GOVERNS THIS WAVE (FRONTIER_OPUS.md)
Q1: a LARGE wave HURTS — DSR deflation is monotone in trial count; more tests on the composite/variants
only make certification harder. Binding constraint = TIME on the frozen forward test (grades ~Dec 2026),
NOT ideas. Therefore: this wave is SMALL + ORTHOGONAL-ONLY, hunting NEW edge for a *NEXT SLEEVE* on its
OWN fresh forward clock. It must NEVER touch the freeze, and cannot itself certify anything.

RE-SCOPED MERGE RULE: TEST_QUEUE capped at the 4-6 most distinct, orthogonal, buildable-NOW mechanisms.
Each tested ONCE for INCREMENTAL IC over the 7-leg composite (candidate next-sleeve material). Data-blocked
high-EV items are NOT tested — they are flagged for the Principal's home-network pull.

Opus ranked top-5 (honest EV):
1. Promoter/insider (SAST) accumulation drift — ALREADY validated (IC_IR 1.33, clean); blocked only on a
   fresh data pull. Near-free EV. → DATA-BLOCKED, flag to Principal (do NOT re-search).
2. Gross profitability GP/Assets (Novy-Marx) — most robust orthogonal-to-value quality sub-signal; buildable
   NOW; test incremental over composite. → QUEUE.
3. Overnight-return premium (overnight vs intraday) — distinct return component; buildable from daily
   open/close; cost-sensitive. → QUEUE (if intraday/open data sufficient).
4. Leading regime classifier for SIZING — orthogonal but NOT #1: N≈5 bears caps certifiability, timing is
   the most overfit-prone axis. Validate LEAVE-ONE-BEAR-OUT or don't build. → cross-asset agent building it;
   Phase-B judge MUST apply leave-one-bear-out.
5. Analyst EPS-revision momentum — highest documented orthogonal factor, almost certainly DATA-BLOCKED;
   probe availability before any build. → probe, else flag to Principal.

## PHASE A: COMPLETE (all 8 agents done). Outputs in wave4/. ~37 ideas collated → TEST_QUEUE.json (7 distinct).
##   Cross-asset: 2 CANDIDATES (copper/gold 6m-Δ, gold-vs-equity mom) beat VIX on Sharpe/maxDD but FAIL
##   linear-IC lag gate → handed to overfit-analyst for era-split + leave-one-bear-out.

## PHASE B: RUNNING (5 agents)
- [running] S1 fundamentals tester → W4F-02 clean-surplus, W4-01 NOA, W4F-01 depreciation-laxity
- [running] S2 value/risk tester → W4B-02 distress, W4P-03 cyclical-normalized-EY
- [running] S3 price/combo tester → W4-08 Amihud, W4-12 momentum-within-quality double-sort
- [running] overfit-analyst → adversarial era-split + leave-one-bear-out on the 2 cross-asset candidates
- [running] LOW-POWER RE-SCREEN (Principal directive 2026-07-17) → rescue signals killed only for low t/DSR/PBO
  at small n (NOT structural). Keep lag/placebo hard. Output RESURRECTION_RESCREEN.md for Principal adjudication.
  See memory feedback-low-t-power-aware-rescreen.

## NEXT-QUEUE (Principal-requested, launch as agent slots free — currently at 9-cap):
- TECHNICAL PATTERNS pass (Principal 2026-07-17): test volume-profile, VCP, breakout+retest, down-channel
  breakout, flag, choppy/range, ladder — CLUBBED with fundamental/quantamental score (overlay, not standalone;
  prior-art: standalone technical ENTRIES mostly killed, trend+exits survived). Era-split (pre/post-2015
  manipulation), hard gates, low-t rule. Elliott-waves / cup-handle = overfit traps → rigidly-objective defs
  or advise-against. Data: cube_close_long, cube_volume. Output rnd/wave4/TECHNICAL_PATTERNS.md, cards W4TECH_*.
- (also pending: absolute-scorer prototype build — HELD until horizon-weights audit + Principal spec sign-off.)

## WAVE-4 COMPLETE (2026-07-17). All 8 Phase-A + 6 Phase-B agents done. Master synthesis = WAVE4_FINDINGS.md.
## Finds: clean-surplus + depreciation-laxity (new orthogonal quality legs, lift composite IR) + Amihud
## (data-limited) = forward-test candidates. Re-screen: 40 Tier-A momentum/trend families rescued from
## saturated-PBO false-kills (beta-adj momentum, MA-slope, vol-scaled = strongest by absolute return).
## 2 cross-asset regime signals PARK-needs-data (survived leave-one-bear-out). 179 structural-dead stay dead.
## Nothing promoted in-sample; all = fresh-forward-clock candidates, freeze untouched. 6 DATA-ASKS for Principal.
## Integrity fix: MACRO_XASSET FRED-fill claim didn't persist — annotated + flagged to data-officer.
