# RANDOM-BASKET BENCHMARK — APPROVED SET & RETIREMENTS (Principal ruling 2026-07-21)

Governs which random-basket (placebo) benchmarks a strategy is measured against under the D-029 standard.
Supersedes any prior use of the retired variants below.

## RETIRED — INVALID, do NOT use to pass/fail any strategy (Principal 2026-07-21)
These are removed on **validity** grounds (not difficulty). All three share a cherry-picked short
recent-bull window (2022-06→2025-06, 36 months of a strong small/mid-cap bull) AND survivorship bias
(universe = today's surviving stocks, no delisted losers), which jointly manufacture an abnormally high,
un-beatable bar. Retiring them fixes the real problem the Principal flagged: honest strategies were being
rejected against a fantasy yardstick.

| Retired | Why invalid |
|---|---|
| **v1** EW-25, survivorship, GROSS (CAGR 42.9%) | short bull window + survivorship + no costs (triple-inflated) |
| **v2** EW-100, wider + net cost (CAGR 37.8%) | short bull window + survivorship (still ~2.3x the honest long-run bar) |
| **v3** cap-weight 100, net (CAGR 30.1%) | short bull window + survivorship (cap-weight fixes only one of two flaws) |

## RETIRED — SUPERSEDED, not invalid (Principal 2026-07-21)
| Superseded | Reason |
|---|---|
| **v4** cap-wt 100, 2021-26, PIT-historical (CAGR 17.1%) | A valid benchmark, but the WEAKEST of the set on survivorship-completeness — it filters today's coverage to PIT membership and still cannot draw delisted-and-dropped names, whereas v6/v8 use the genuinely survivorship-complete panel over comparable/longer windows. Retired for consistency (dominated by v6/v8), NOT for difficulty. Note: removing v4 does **not** lower the bar — v8 (19.5% CAGR) is higher and remains primary. |

## APPROVED SET — the honest bar (use these)
Survivorship-complete universe, cost-loaded, full-cycle or medium window.
Compare a strategy against the **p05–p95 band** of the matching-horizon basket, not the mean:
above mean = strong; inside band = no demonstrated edge; below p05 = fail.

| Approved BM | Window | Universe basis | CAGR (mean) | MaxDD | Vol |
|---|---|---|---|---|---|
| v6 cap-wt 100 | 2014-26 | survivorship-complete panel | 13.8% | −41.7% | 19.4 |
| v6 cap-wt 50 | 2014-26 | survivorship-complete panel | 13.0% | −42.0% | 19.4 |
| **v8 cap-wt 100** (primary, full cycle) | 2005-26 | survivorship-complete panel | 19.5% | −61.9% | 26.3 |
| v8 cap-wt 50 | 2005-26 | survivorship-complete panel | 18.3% | −62.9% | 26.2 |
| Nifty-50 buy-hold (passive floor) | matched | index | 10.6–13.3% | −29.3 to −55.1% | 15.8–20.6 |

Notes:
- Prefer **cap-weight** rows for Sharpe/vol comparison; the long-window *equal-weight* baskets (v5/v7/v8 EW)
  carry unreal vol (up to 33%+, p95 >130%) from thin early-era microcaps and are not tradeable at size —
  keep them only as a wide-band sanity check, never as the deciding bar.
- Residual bias (disclosed): even the survivorship-complete panel can't draw a historical member since
  dropped from today's coverage (v5 note: 6.5% of 2025 members, 44% of 2015) → the approved bar is still
  *slightly* optimistic (a touch too hard, early years), which is the safe direction.

## GUARDRAIL (anti-benchmark-shopping)
Benchmarks are retired ONLY for a documented validity defect (survivorship, look-ahead, cost-asymmetry,
non-representative window). A benchmark is NEVER retired for merely being hard. The approved set deliberately
keeps a genuinely hard full-cycle bar (v8, −62% MDD, includes 2008 + COVID). Beating that is the real test.
