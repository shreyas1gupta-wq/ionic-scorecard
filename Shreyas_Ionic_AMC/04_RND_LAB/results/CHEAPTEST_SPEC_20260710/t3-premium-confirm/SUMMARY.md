# T3 — Option-premium confirmation filter (F8) — CHEAP-TEST RESULT

**Date:** 2026-07-10 | **Key:** t3-premium-confirm | **Verdict: KILL**

## Spec (per triage `ideas/20260710_principal_intraday_spec_triage.md`, T3)
- Events: 20260707 VOL_BREAKOUT_ATM campaign breakout entries, cell **BB10_EOD** (canonical cell, 1,036 events, both directions, 2021-05→2026-06).
- Decision time t0 = campaign entry bar (already 1-bar-lagged fill). **Confirmation uses only bars <= t0-1min** (window (t0-6, t0-1] min) — zero same-bar leakage; `guards.drop_preopen` applied to spot and options; contract identity validated by matching option quote at t0 to the campaign's `entry_prem` within 2%.
- Confirmation rule (single pre-registered trial, DSR ledger T3=1): ATM premium %move over 5-min window >= **+3%** AND 5-min option volume >= **70th causal percentile** of same-day rolling 5-min volumes (>=15 prior windows required).
- Primary metric: signed forward 30-min underlying move dir*(S[t0+30] - S[t0]), EOD-truncated at 15:25. Secondary: realized campaign trade net_pts.

## PRE-REGISTERED KILL THRESHOLD (frozen)
Spread < 4 pts OR t < 2 → KILL. Rejection >=80% → dead even if positive. PASS = veto only, never a buying reopen.

## Numbers
- n = 1,036 events → **936 usable** (100 NO_WINDOW: insufficient same-day pre-decision bars; 0 contract mismatches).
- Confirmed 538 / Unconfirmed 398 → **rejection rate 42.5%** (below the 80% scarcity bar — moot given kill).

| Metric | Confirmed | Unconfirmed | **Spread** | t (Welch) | **t (day-clustered)** |
|---|---|---|---|---|---|
| Fwd 30-min underlying pts (primary) | +2.50 | +0.95 | **+1.55** | 0.66 | **0.66** |
| Realized trade net_pts (secondary) | -2.64 | -3.62 | +0.98 | 0.29 | 0.29 |

**vs bar: spread 1.55 < 4 pts FAIL; t 0.66 < 2 FAIL.** Both legs of the kill condition trip.

### Era / year split (primary spread, pts)
| Era | n_conf/n_unconf | Spread | t_clust |
|---|---|---|---|
| 2021-22 | 177/134 | +4.37 | 1.15 |
| 2023-26 | 361/264 | **+0.15** | 0.05 |
| 2021 | 73/45 | +8.94 | 1.44 |
| 2022 | 104/89 | +1.62 | 0.33 |
| 2023 | 104/80 | +0.09 | 0.03 |
| 2024 | 110/76 | -0.17 | -0.03 |
| 2025 | 105/73 | +4.80 | 0.78 |
| 2026 | 42/35 | **-10.45** | -1.24 |

Whatever weak effect exists is 2021-loaded and **dead-to-negative 2023-26** (spread +0.15, t 0.05); 2026 is outright negative.

### Robustness (all reinforce KILL)
- **Within-day label-shuffle placebo: p = 1.00** — every within-day shuffle matches/exceeds the observed spread, i.e. the +1.55 is entirely day-composition (labels are near-constant within days); there is NO within-day information in the confirmation flag.
- **One-bar-lag test:** lagged confirmation gives spread +3.54 (t 1.47) — no collapse, but lag > unlagged means the "signal" is noise, not decision-time information.
- **Marginals** (report-only): premium-only spread +0.98 (t 0.42); volume-only spread **-1.09** (t -0.34) — high option volume at breakout predicts nothing or slightly worse follow-through.
- Secondary: even the confirmed bucket loses -2.64 net_pts/trade on the actual option trades — confirmation does not rescue buying (consistent with K-001).

## Verdict
**KILL** — F8 premium-confirmation fails the frozen bar on both spread (1.55 < 4) and t (0.66 < 2), placebo shows zero within-day content, and the effect is absent in the recent era. The triage's "top survivor candidate" does not survive its own cheap-test. No veto value demonstrated; do NOT fold into T2/T4 survivors. Resurrection only via a fundamentally different confirmation construct (order-flow/OI per T6), not premium %move/volume.

## Files
- Script: `t3_premium_confirm.py` | Per-event data: `t3_events.csv` (936 rows) | Full stats: `t3_results.json`
