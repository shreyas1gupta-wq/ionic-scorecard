# CHEAP-TEST F-FVG (fvg-flags) — VERDICT: KILL (both sub-tests)
**Date:** 2026-07-10 | **Owner:** quant engineer (solo cheap-test) | **Parent:** `ideas/20260710_principal_intraday_spec_triage.md` rows 14 (GLBS-A FVG half) & 18 (GLBS-E)

## Spec (frozen before run — see docstring in `fvg_cheaptest.py`)
- FVG = 3-candle imbalance: bullish low(c3)>high(c1), bearish high(c3)<low(c1); min gap 0.02% of c2 close; first-touch retest only; retest window 12 bars; sweep->FVG formation window 12 bars.
- Data: NIFTY spot 1-min via landmine-enforced `fno_game/server/data_loader.py` (tz->IST, >=09:15), 2021-05-24 -> 2026-06-03, 1,238 days. TFs: 1-min & 5-min (session-folded). Horizon 15 min (1m) / 30 min (5m); last entry 14:45.
- Effect = signed forward pts minus time-of-day-matched (30-min bucket) baseline; t = day-clustered (over day-mean excess).
- **Pre-registered kill (FROZEN): effect < 5 pts OR t < 2.5, each sub-test separately.**

## Results (pooled + era split)
| test | tf | n_events | n_days | effect (pts) | t (day-clust) | WR | verdict |
|---|---|---|---|---|---|---|---|
| (a) sweep+FVG reversal | 1m | 1,707 | 639 | **-4.56** | -4.92 | 0.427 | KILL |
| — era 2021-22 | 1m | 639 | 219 | -3.30 | -2.37 | 0.448 | |
| — era 2023-26 | 1m | 1,068 | 420 | -5.30 | -4.32 | 0.415 | |
| (a) sweep+FVG reversal | 5m | 977 | 532 | **+0.61** | -0.66 | 0.496 | KILL |
| — era 2021-22 | 5m | 334 | 185 | +2.01 | 0.03 | 0.485 | |
| — era 2023-26 | 5m | 643 | 347 | -0.12 | -0.78 | 0.502 | |
| (b) FVG-retest continuation | 1m | 28,597 | 1,235 | **-6.16** | -32.06 | 0.408 | KILL |
| — era 2021-22 | 1m | 11,920 | 399 | -5.31 | -23.40 | 0.413 | |
| — era 2023-26 | 1m | 16,677 | 836 | -6.77 | -25.12 | 0.405 | |
| (b) FVG-retest continuation | 5m | 8,035 | 1,228 | **+1.13** | +3.29 | 0.513 | KILL |
| — era 2021-22 | 5m | 3,085 | 398 | +1.19 | 2.08 | 0.509 | |
| — era 2023-26 | 5m | 4,950 | 830 | +1.09 | 2.63 | 0.516 | |

## Verdict
- **(a) GLBS-A sweep+FVG reversal: KILL.** No TF clears either threshold. 1-min is significantly NEGATIVE (reversal direction loses -4.6 pts, t=-4.9, both eras); 5-min is noise (+0.6 pts, t=-0.7).
- **(b) GLBS-E FVG continuation: KILL.** 5-min shows a real but tiny effect (+1.13 pts, t=3.3, era-stable) — 4.4 pts below the 5-pt floor and far below any option-buying breakeven (~10 pts stressed round-trip per T4 note). 1-min is strongly the OPPOSITE sign (-6.2 pts, t=-32): 1-min FVG retests continue INTO the gap (mean-revert), not out of it.
- Honest anti-flip note: the large negative 1-min t-stats invite a "trade the reverse" reading. That is a NEW, post-hoc, direction-mined hypothesis — not this one — and ~5-6 spot pts per 15 min does not survive option-vehicle costs (K-001 wall). Observation only; any resurrection requires its own pre-registered test.

## Files
- `fvg_cheaptest.py` — full frozen spec + code
- `events.csv` — 39,316 events (d, tf, test, dir, entry, fwd, baseline, excess)
- `results.csv` — the table above
