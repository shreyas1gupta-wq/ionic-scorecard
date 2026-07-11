# C2-CARD RESULTS — Day-night decomposition of ATM short-straddle premium
**Run 2026-07-11 · card frozen BEFORE run (MASTER_PLAN §C2-CARD) · 2,452 segments (1,224 overnight / 1,228 intraday), 2021-06→2026-06, skips 20 prints · script + full CSV in this folder**

## VERDICT vs FROZEN BARS: **REFUTE — C2 CLOSED**
- Bar check (gross, full sample): overnight mean **+0.59 pts, t = 0.48** → t < 1.5 hits the REFUTE bar. (LEAD needed t≥2.5 AND overnight > intraday; intraday is +4.75, t=3.39 — the premium is concentrated INTRADAY on our data, the *opposite* of the Wiley claim.)
- n = 1,224 ≥ 400 → sample sufficient. Verdict is mechanical, no judgment applied.
- **Consequence: no overnight-hold variant enters intake. S1-F's intraday-only, flat-by-EOD design is vindicated by measurement.**

## Why the overnight premium fails (descriptive secondaries, per card)
| Cut (gross pts) | n | mean | t | win% |
|---|---|---|---|---|
| overnight ALL | 1224 | +0.59 | 0.48 | 64% |
| overnight ex-jump (\|gap\|>1%) | 1138 | **+6.17** | **9.70** | 67% |
| overnight weekend-only | 294 | **−6.36** | −1.75 | 60% |
| intraday ALL | 1228 | +4.75 | 3.39 | 68% |

- Textbook steamroller: sellers collect ~6 pts on 93% of nights (median +5.5) and the ~7% of >1% gap nights take it all back. The ex-jump cut is NOT tradeable (tonight's gap is unknowable at entry) — it only explains the mechanism.
- Weekend holds are outright negative even gross: weekend theta does not pay for weekend gap risk.
- DTE gradient: only DTE=1 overnight looks positive (+6.70, t=1.96, sub-bar); DTE≥4 negative.
- NET of calibrated costs (4 pts round trip): overnight −5.41 (t=−4.43) — decisively dead at retail costs regardless of gross sign.

## Bonus: in-house answer to refuted claim B.3 ("2026 VRP regime flip to −4.63")
2026 YTD on our data: overnight **+1.82** gross (n=94), intraday **+2.80** gross (n=96) — both POSITIVE, no sign flip. The claim is now double-dead: 0-3 adversarial citation vote AND contradicted by in-house measurement.

## Honest caveats
- The paper decomposes **delta-hedged** option returns; we measured the raw (unhedged) straddle — the tradeable-for-us variant, which is the decision-relevant question, but not an exact replication. A delta-hedged replication would isolate the vol premium from gap-direction exposure; not pursued (no trade we would take depends on it).
- Intraday ALL here is DTE≥1 unconditional (+4.75 gross, −1.25 net) — consistent with prior knowledge that unconditional intraday selling doesn't survive costs; S1-F's edge is specifically 0DTE expiry-day + SL, a different animal, unaffected by this result.
- Trials ledger: +1 registered trial (primary comparison). Secondaries are descriptive, not trials.
