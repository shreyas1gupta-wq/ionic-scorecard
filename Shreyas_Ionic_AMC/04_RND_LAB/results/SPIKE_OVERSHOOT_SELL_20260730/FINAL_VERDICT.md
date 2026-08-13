# FINAL VERDICT — the >100% CAGR / <25% MDD mandate. 13 structures tested 2026-07-30.
**Answer: NOT FOUND. And the question is now closed in a way that cannot be reopened on
"you used the wrong costs / wrong vehicle / wrong exit" grounds, because all three were the
Principal's own specifications.**

## THE COMPLETE SCOREBOARD (all ex-events, real 1-min prices, Rs25/lot/side, lot=65)
| # | structure | net edge | note |
|---|---|---|---|
| 1 | Sell spike-side option, **delta-hedged** | **+0.30 pts** | only positive survivor; +0.64 at 0.24Δ, **-0.25 at 0.40Δ** |
| 2 | Sell opposite-side, 0-1DTE only | +0.39 | PF 1.06, marginal, n-limited |
| 3 | Buy CHEAP option (overshoot<=-3) | +0.17 | median **-3.93**, fails Principal median>+5 |
| 4 | **Target+re-entry T70/P15 (ITM)** | **-0.31** | best RR of all (1.91) but median -26.67 |
| 5 | Sell opposite-side, all | -0.40 | median +1.93, mean negative = pennies/steamroller |
| 6 | **Conservative candle trail (ITM)** | **-0.46** | 5-bar low, honest fills |
| 7 | Sell spike-side, unhedged | -0.51 (+0.02 ex-ev) | vol crush cancelled by continuation |
| 8 | Delta-1 FOLLOW the spike | -1.59 to -2.72 | gross +2.83-3.83 vs ~5.5 futures cost |
| 9 | **Fixed-time endpoint (ITM)** | **-1.69** | exact measurement |
| 10 | Credit spread (200pt wide) | -2.39 | MY DESIGN ERROR - width far too wide |
| 11 | Buy RICH option | -2.63 | pay the overshoot, then it deflates |
| 12 | Delta-1 FADE the spike | -4.03 to -7.83 | spot CONTINUES, does not revert |
| 13 | ~~Fixed 25-pt trail (ITM)~~ | ~~+3.03~~ | **DISCREDITED - fill-convention artifact** |

## ★ THE DECISIVE TEST — AND IT KILLED MY OWN BEST RESULT
The ITM+trail result (+3.03 pts => 69% CAGR at -23.8% MDD, 3 lots) was the session's only path to the
mandate. It derived **100% of its edge from the trailing mechanism** (the fixed-time endpoint LOSES at
-1.69). My trail was simulated on 1-min bars using each bar's HIGH and LOW, resolving intra-bar
ambiguity FAVOURABLY.
Re-run with a **candle-structure trail** (stop = low of last N COMPLETED bars, so no intra-bar
sequencing assumption is possible) and a **conservative** convention (a bar breaking the trail stops you
out even if it also made a new high): **-0.46 pts.**
**The ~3.5-pt gap IS the fill-convention optimism. 69% CAGR is withdrawn.**
Corroborating: the candle version is WORSE post-Oct-2024 (-2.35) and WORSE on held-out 2026 (-2.12) —
the reverse of the fixed-trail pattern. Caveat on my own kill: the two runs differ in fill convention
AND trail type (fixed-distance vs N-bar low); a fixed-distance trail under conservative fills was not
isolated. Direction is unambiguous enough not to argue the flattering reading.
**Three honest measurements converge at -0.31 / -0.46 / -1.69. The one positive number had the one
favourable convention.** That convergence is what makes this conclusive.

## WHY 100% CAGR IS UNREACHABLE HERE — the arithmetic, not pessimism
Every real effect measured today is **2-5 points**; every vehicle costs **1.5-6 points**:
| effect | size | vehicle cost |
|---|---|---|
| premium overshoot (median) | **-0.16** (mean +2.12, 31% of events >=3) | option 1.45-1.67 |
| overshoot decay captured @60min | +1.77 gross | option 1.45 + hedge 1.33-2.22 |
| spot continuation after spike | +2.83 to +3.83 | futures **~5.5** |
| MFE/MAE ratio | **1.05-1.09 (symmetric)** | - no convexity to harvest |
Leverage cannot fix a 2-5pt effect against a 1.5-6pt cost: at the size needed for triple digits, one
bad day exceeds 25% MDD. **The binding constraint is effect-size-to-cost, not capital efficiency.**

## PRINCIPAL CRITERIA — scorecard
- **median profit > +5 pts: FAILED BY EVERY BUYING CELL.** Best is -3.93 (buy cheap). Arithmetically it
  needs a >50% win rate; buying runs 31-48%. At 34-48% win rates the median trade is a LOSS by definition.
- **RR >= 1.5: PASSED repeatedly** (target+re-entry 1.91, buy-cheap 1.65-1.88, candle trail 1.63).
  Option buying here genuinely has the payoff asymmetry wanted — it lacks the hit rate.
- **maxDD <= 25%: only satisfiable at sizes that give ~10-20% CAGR.**

## WHAT WAS RIGHT IN THE PRINCIPAL'S IDEAS (credit where due, all measured)
1. **Event avoidance — the cleanest risk win of the day.** Dropping 1-4% of trades (scheduled
   elections/budgets) cuts worst single trade 2.6-3.4x and worst DAY 3.9-7.6x, and flips two negative
   strategies positive. Election day 2024 unhedged was -33.6% of a Rs10L account in ONE day.
2. **"Trail dynamically" identified the real gap** — every earlier measurement was a fixed-time
   endpoint; MFE(60m)=53.9 vs endpoint 3.31. Trailing genuinely captures more. It just does not survive
   honest fills.
3. **Price-action magnitudes CONFIRMED**: 50-70pt moves in 26-52% of events, 150pt in 5-22%.
4. **The overshoot exists** (mean +2.12, 84% reverts in 60min, monotonic in richness, better post-2024).
5. **Post-2025 alpha decay CONFIRMED market-wide** — 5 unrelated strategies degraded simultaneously.
6. **ITM logic was mechanically sound** (extrinsic 35.8% of premium vs ~100% for ATM; ~20x capital
   efficiency) — the vehicle reasoning was right, the underlying edge was not there.
7. **Recency as an asymmetric screen** and **cost-stress instead of top-decile for high-frequency** were
   both methodological corrections I adopted.

## WHAT WAS REFUTED
- 10-30pt spot PULLBACK after a spike: **spot CONTINUES** (+2.83 to +3.83), it does not revert.
- Abnormal option move = institutional FOOTPRINT: continuation is **strongest where abnormality is
  ZERO** (near-fair t=3.16 vs rich>=14 t=0.77) => the abnormality carries no directional information.
- **3-min bars in the late session**: 3-min was the WORST bar size (-1.03); 15-min was best (+0.44) in
  exactly that window.
- Conviction scaling (1x/2x/3x by overshoot): raises total points 2.45x but drawdown 3.3x => ret/DD
  falls from 39.4 to 29.1. **Selection beats scaling.**

## GENUINELY STILL UNTESTED (honest odds)
1. **NARROW credit spread (50-100pt width)** — my 200pt version risked 157 pts to collect a small
   credit; that was a design failure, not a concept failure. Capital ~Rs5k/lot (30x efficiency) and a
   structurally capped tail. **Best remaining shot at the mandate.** Odds: moderate.
2. **Unified signal allocator** (pooled capital, signal arbitration) — spec at
   `results/UNIFIED_ALLOCATOR_SPEC.md`. Cannot manufacture edge, only allocate better; worth building
   only AFTER something works in 2025-2026.
3. Multi-day option holds on the overshoot signal. Odds: low.
4. Resting-limit entry (fill iff 1-min HIGH >= limit) — needs ~9 pts of improvement to move the median
   to +5; realistically delivers 1-3. Odds: low.

## THE ONE HONEST DEPLOYABLE THING FROM THIS ENTIRE LINE
**Sell the rich (overshoot>=3) 0-1DTE option, DELTA-HEDGED, skipping scheduled event days.**
+0.30 pts/trade at 0.30 delta (range +0.64 to -0.25 across the 0.20-0.40 band), ~24 trades/month,
better post-Oct-2024 (+1.54) and on held-out 2026 (+1.72). At 5% hedged margin that is roughly
**8-9% CAGR** — real, small, and NOT the mandate. It is within the error bars of the cost model and
should be treated as a FORWARD-TEST CANDIDATE, never sized as a certainty.
