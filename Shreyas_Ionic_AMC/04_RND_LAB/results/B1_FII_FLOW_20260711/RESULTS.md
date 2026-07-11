# B1-CARD RESULTS — FII index-futures net-flow quintiles vs NIFTY forward returns
**Run 2026-07-11 · spec frozen in PRE-RUN commit b267854 (provability rule) · n=1,803 signal days 2019-01→2026-05 · RUN_CARD.json + panel CSV here**

## VERDICT vs FROZEN BAR: **KILL** (bar: top−bottom ≥10 bps/day AND t ≥ 2.5)
| k (days) | top−bottom | per day | t |
|---|---|---|---|
| 1 | +18.0 bps | +18.0 | **2.09** ✗ |
| 3 | +5.6 bps | +1.9 | 0.38 |
| 5 | −2.0 bps | −0.4 | −0.11 |

- Best case (k=1) clears the magnitude bar but fails significance (2.09 < 2.5). Mechanical kill.
- Structure is weak everywhere: quintiles non-monotonic (q2 is the *worst*, not the middle), signal fully decays by day 3, and k=5 flips sign across eras (−26 bps 2019-21 vs +15.6 bps 2022-26).
- Data honesty: 244 unparseable FII rows dropped (schema-drift vintages, reported); 252-day rolling-percentile ranks (no full-sample quantile leak); T+1 timing by construction.
- AST scanner pre-flight: 14 advisory flags, all triaged false-positive (forward-index hits = outcome measurement after the T+1 entry; mean/std hits = reporting stats).

## Resurrection condition (KILLED_IDEAS convention)
The k=1 effect (+18 bps/day, t≈2.1) is a *lead, not noise-level zero*. Worth revisiting ONLY if: (a) participant-OI schema normalization (Kavya's format-break map) recovers the 244 dropped days AND (b) a pre-registered variant with client-type SPREADS (FII minus Client net flow — the "smart vs dumb money" differential) is written as a NEW card with fresh bars. No parameter fishing on this dataset outside that.

Trials ledger: +3 (k = 1/3/5 as pre-declared sub-trials). First experiment with RUN_CARD.json emitted.
