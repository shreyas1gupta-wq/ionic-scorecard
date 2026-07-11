# A1-CARD RESULTS — DTE richness (which expiry bucket pays sellers best per day)
**Run 2026-07-11 · card frozen BEFORE run (MASTER_PLAN §A1-CARD) · 1,793 obs (one per expiry×DTE, k=0..6), 259 expiries 2021-06→2026-06, 17 skips · CSV + raw table in this folder**

## VERDICT vs FROZEN BAR: **NO PREFERRED DTE — CARD CLOSED, no new vehicle**
Bar required: best per-day NET richness among buckets with t ≥ 2.5. Best achieved: k=2 (t=1.37), k=3 (t=1.22) — nothing near 2.5. All buckets n≈259 (sufficient). Verdict mechanical.

| k (trading DTE) | entry prem | gross pts | net pts | net/day | t (net/day) | worst-5 avg |
|---|---|---|---|---|---|---|
| 0 | 111 | +2.5 | −1.5 | −1.5 | −0.26 | −329 |
| 1 | 178 | +7.8 | +3.8 | +3.8 | 0.44 | −519 |
| 2 | 231 | +18.9 | +14.9 | +7.4 | **1.37** | −492 |
| 3 | 267 | +19.5 | +15.5 | +5.2 | 1.22 | −593 |
| 4 | 308 | +12.4 | +8.4 | +2.1 | 0.60 | −611 |
| 5 | 337 | +6.1 | +2.1 | +0.4 | 0.13 | −698 |
| 6 | 363 | +8.1 | +4.1 | +0.7 | 0.23 | −776 |

## What this teaches (descriptive, the real value of the card)
1. **Raw hold-to-expiry richness exists at every DTE (all gross positive) but is statistically invisible** — unhedged terminal variance (worst-5 runs −300…−776 pts) swamps a 2–19 pt mean. A naive "sell and hold" seller at ANY DTE is a coin flip with tail risk. This kills the naive-vehicle branch cleanly.
2. **The S1-F control experiment nobody planned:** k=0 here = S1's exact day and entry but NO stop-loss → −1.5 net pts/day, vs S1-F's +10.7 (t=3.9) with the 30% per-leg SL. **The ~12 pts/day edge is manufactured by the SL truncation of the left tail, not by the raw premium.** Structure > signal. Any future sell vehicle must carry equivalent convexity management before it deserves a backtest.
3. DTE 2–3 is where raw richness is least-bad per day (era-consistent, 2024–26 slightly better) — IF a future card designs a *managed* (SL/hedged) mid-DTE structure, start there. That is a design hint, not a finding.
4. Skew of outcomes: med/day >> mean/day in every bucket (e.g., k=1: median +33 vs mean +3.8) — same steamroller shape as C2's overnight result.

## Consequences
- No Structurer intake from A1. The "which DTE" question is answered: **none, as an unmanaged hold** — the premium is real but only harvestable with truncation structure (S1-F's mechanism, confirmed independently twice today).
- Trials ledger: +1 (bucket comparison). Program tally today: C2 REFUTED, A1 CLOSED-NO-PREFERENCE — both at ~zero agent tokens.
