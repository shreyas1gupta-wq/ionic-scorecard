# B1b-CARD RESULTS — FII-minus-Client spread flow (B1 resurrection variant): **PASS**
**Run 2026-07-11 · spec frozen pre-run @ 4d9c6f1 · n=1,803 signal days 2019-01→2026-05 · RUN_CARD.json + panel here**

## VERDICT vs FROZEN BAR: **PASS** (first alpha-stream pass of INDEX_PROGRAM_2026)
- Best k=1 (next-day): top−bottom **+21.8 bps/day, t=2.53** (bar: ≥10 bps/day AND t≥2.5).
- **Era-consistent and STRENGTHENING**: 2019-21 +14.4 bps → 2022-26 +27.6 bps. Not a decaying artifact.
- Beats plain FII flow (B1: +18.0, t=2.09 KILL) exactly as the smart-vs-retail differential thesis predicted — netting out Client (retail) positioning sharpens the signal.

## Honest caveats (carry into Gate-4, do not launder)
1. **t=2.53 vs bar 2.50 — razor-thin.** This is a cheap-test pass admitting the idea to Gate-4, NOT a strategy. A Gate-4 backtest with execution realism must clear its own bars.
2. **Selection across 2 pre-registered constructions** (B1 killed, B1b passed, B1b declared last) — 6 trial cells on this dataset family are on the ledger; DSR at Gate-4 must count them.
3. **One-day effect only** (dead by k=3, same as B1) and **non-monotonic quintiles** (q4 carries everything; q2 negative) — the tradeable expression is q4-conditional, ~20% of days, not a smooth factor.
4. Signal uses T+1 close entry; realistic future costs ~1-3 bps/side on NIFTY futures — edge plausibly survives but must be modeled, incl. the D-031 no-fill-drop rule.

## Next gate (pipeline, not run today)
Gate-4 spec: long NIFTY near-month futures at close(D+1) when spread-flow quintile = 4, exit close(D+2); include costs/slippage per COST_STANDARDS, DSR with full trial count, sensitivity (rank window, quintile edge), red-team pass. Owner: Arjun (design) + Sameer (overfit battery) + Nikhil (kill attempt) per pipeline.

Trials ledger: +3 (k sub-trials). Stream-B (participant flow) status: OPEN with one live candidate.
