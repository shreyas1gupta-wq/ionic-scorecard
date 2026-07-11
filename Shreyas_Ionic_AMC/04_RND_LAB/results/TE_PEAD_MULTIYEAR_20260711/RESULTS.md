# T-E-CARD RESULTS — PEAD multi-year event study: **PARK** (verdict per frozen card text)
**Run 2026-07-11 · frozen @ b12264b · 1,235 trades (1,230 live / 5 censored), B1=933, B2=297 · RUN_CARD + events CSV here**

## Verdict reasoning (bar-by-bar, frozen text applied)
| Bar | Result | |
|---|---|---|
| excess-over-control t ≥ 2.5 | **+1.24%/trade, t=2.54** | PASS |
| n ≥ 300 | 1,230 | PASS |
| eras both positive | **UNTESTABLE** — era-1 has n=1 (PIT exact-date coverage effectively begins 2019; the 2015-20 half doesn't exist in the data) | not met, not conflicting |
| beat placebo 95th | real raw +3.48% vs null 95th +4.70% (null mean +2.14%!) | **FAIL** |

- **PASS requires all four** → no pass. **KILL requires t<1.5 OR era-sign conflict** → t=2.54 and no sign conflict (era-1 is empty, not negative) → no kill. **→ PARK.**
- Script's printed "KILL" was a code artifact (`nan>0` mishandled as a sign conflict) — verdict here follows the frozen card text. Logic flaw documented, not silently fixed post-hoc.

## What the numbers actually say
1. **The placebo is the story:** random stocks entered at random dates with the same DMA50-trail exit earned **+2.14% mean** — the trailing-stop structure harvests 2021-26 market drift. Most of PEAD's +3.48% raw is structure+beta, not information.
2. The event-conditioning residual (+1.24% excess over regime control, t=2.54) is a genuine but modest lead — consistent with v2's single-quarter hint, now on 1,230 events.
3. DMA20 secondary (+0.87% raw) is strictly worse — faster exits cut drift harvesting, confirming point 1.
4. **Effective sample is 2021-2026 only.** The "multi-year" prescription is unfulfillable with current PIT exact-date coverage; a genuine era test needs the 2015-19 earnings-date backfill (NSE announcements archive — data office intake).

## Park conditions (what would reopen this)
(a) 2015-19 available_date backfill → rerun the SAME frozen card with a real era split; or (b) a beta-hedged construction (excess-return entry vs sector/index short) as a NEW card — the +1.24% excess suggests the residual signal is what's worth isolating.
Trials +2 (B1/B2). Family total now 5 (v1, v2, this ×2 buckets + construction).
