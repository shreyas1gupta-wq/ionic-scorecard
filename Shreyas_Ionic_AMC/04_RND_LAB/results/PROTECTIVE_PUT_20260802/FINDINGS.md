# FINDINGS — PROTECTIVE_PUT_20260802
NIFTY index, real 2016-2026 option data (includes actual COVID prices). All roll T-5, ~30D target.

| Structure | net_mean pts/rung | t-stat | Crash-window (20Feb-10Apr-2020) | Risk shape |
|---|---|---|---|---|
| PROT_PUT (buy 1x 5% OTM PE) | -19.66 | -0.69 | **+3,463 pts** (n=2) | uncapped upside, capped loss = premium |
| RATIO_1x2 (buy 1x 3% OTM + sell 2x 8% OTM) | -20.97 | -2.18 | -19.9 pts (n=1) | UNCAPPED tail beyond far strike (3/126 rungs breached it in-sample, worst breached rung was actually +274.9 — not yet catastrophic here, but structurally real) |
| **SPREAD_1x1** (buy 1x 3% OTM + sell 1x 8% OTM — Principal's actual "ratio" ask, corrected from 1x2) | **-43.17** | **-3.70** | -39.6 pts (n=1) | capped BOTH ways: max loss=net debit (~89pts), max gain=~672pts theoretical (reached at spot<=far strike, 3/126 rungs) |

## Correction note
Principal's mid-session "ratio" ask meant a 1:1 structure — a standard bear-put DEFINED-RISK debit
spread, not the 1x2 ratio spread originally built (which has uncapped risk beyond the short strike).
Rebuilt as `run_put_spread_1x1.py` / `trades_SPREAD_1x1.csv`.

## Honest read
The 1:1 spread is the SAFEST structure (genuinely capped both directions, no tail risk) but is also
the WORST performer of the three on raw cost (-43.17 pts/rung, t=-3.70 — the only one of the three
that is statistically significant as a pure drag, not just directionally negative). This is not a
contradiction: capping the gain at ~672 pts removes exactly the outsized payoff (+3,463 pts for the
uncapped long put in the real 2020 crash) that justified the pure long put's cost. Selling the far
leg lowers cost but throws away more value than it saves, in this specific 30D/T-5/3%-8%OTM
configuration. **The plain long put (PROT_PUT) remains the better hedge candidate of the three** —
cheaper AND keeps the tail payoff. Not re-parameterized (different strikes/tenors) without a further
Principal ask, to avoid an unprompted trial-count blowup on top of an already-large option-family
search history.
