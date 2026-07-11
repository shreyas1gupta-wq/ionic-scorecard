# B2-CARD RESULTS — Air-pocket leg-buyback overlay on S1 (trio test #1)
**Run 2026-07-11 · spec frozen pre-run @ 9e82e72 · 259 expiry days, full bar-by-bar re-simulation with 3-bar-lagged OI · RUN_CARD.json + per-day CSV here**

## VERDICT vs FROZEN BARS: **KILL overlay** (all three bars failed)
| Bar | Required | Measured |
|---|---|---|
| (i) mean uplift | ≥ +1.0 pt/day | **−0.23** |
| (ii) worst-10 improvement | ≥ +15 pts | +5.9 (−86.1 → −80.1) |
| (iii) SL-hit-day improvement | > 0 | **−0.16** |

Baseline +8.02 pts/day (t=2.94) vs overlay +7.79 (t=2.87), same engine both arms. Triggers fired on 77/259 days (30%); on days with no stop event the overlay dragged **−1.87 pts/day** (buying back legs that would have decayed profitably).

## What this settles
- **The air-pocket lead (T6 control-group, +4.4 pts/30min t=3.94) fails its required pre-registered variant test.** The traverse effect exists as a *measurement* but early leg-buyback monetization is net-negative: premium surrendered on false triggers exceeds tail savings on true ones. The mechanism makes sense in hindsight — by the time price crosses a low-OI strike toward a leg that's ≥10% underwater, the 30% SL is close anyway; the overlay mostly just exits 20% earlier at a cost.
- Trio status: test #1 of 3 dead. The two remaining constructions (futures MFT at 2-pt hurdle; A-family timing) stay queued but the prior is now WEAKER — each requires its own frozen card and must beat the added-infrastructure hurdle honestly.
- Baseline S1 note: +8.02 pts/day here vs +10.7 in final_three reflects this engine's harsher symmetric cost handling — the overlay comparison is engine-internal and unaffected.

Trials ledger: +1. AST scanner pre-flight: 3 flags, triaged (cross-sectional snapshot median = point-in-time; reporting stats).
