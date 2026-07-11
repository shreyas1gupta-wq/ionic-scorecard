# B1b GATE-4 RESULTS — spread-flow q4 long, costed: **PASS (all 4 bars)**
**Run 2026-07-11 · spec frozen pre-run @ aebdaca · 372 trades / 1,803 days (21% deployment) · RUN_CARD + daily CSV here**

| Frozen bar | Required | Measured | |
|---|---|---|---|
| Net Sharpe (all days, ann.) | ≥ 1.0 | **1.15** | PASS |
| Net expectancy / trade | ≥ 8 bps | **+18.5 bps** (4.6× cost) | PASS |
| Max drawdown | ≤ 15% | **−11.5%** | PASS |
| Era split | both > 0 | +22.7 / +12.9 | PASS |

Total net return +94% over 7.4 years at 1× notional, 59% win rate, median +16 bps.

## Caveats that ride with the pass
1. **Era decay is visible** (+22.7 → +12.9 bps/trade): the edge is halving-ish across eras while remaining positive. If real decay (crowding), forward performance sits nearer 13 than 18 bps. Watch-item, not a kill.
2. **DSR (N=7 family): 0.84 tight / 0.11 wide** — survives modest deflation, not aggressive deflation. Consistent with "promising, unproven".
3. Execution proxy = index closes + 4 bps RT; real futures basis noise and MIS/NRML margin not modeled. D-031 rule applies at paper: limit-order-or-skip.
4. Same-sample warning from DSR_BASELINE applies less here (different dataset family from sell-side) but the participant-OI sample now carries 10 trial cells total.

## Pipeline (per frozen spec — NO autoadvance)
Next stage before any register entry: **red-team placebo battery** (signal shuffle ×200, extra-lag degradation, frequency-matched random-days control) + **sensitivity surface** (rank window, quintile edge, cost 4→8 bps, entry timing) — both scriptable; then IC review. Paper-first per firm law regardless.

Trials +1 (ledger).

## RED-TEAM + SENSITIVITY (same day, battery pinned in b1b_redteam.py header): **SURVIVED**
- P1 label-shuffle x200: real +18.5 bps at 100th pct (null 95th: +8.8).
- P2 extra-lag: -8.5 bps — signal decays with lag exactly as timely information should (artifacts persist).
- P3 frequency-matched random days x200: real Sharpe 1.15 at 100th pct (null 95th: 0.61).
- Sensitivity 18/18 cells net-positive (rank-window x edge x cost); worst +6.9 bps at [200d, top-25%, 8bps].
**Stream status: cheap-test PASS -> Gate-4 PASS -> red-team SURVIVED. Next per pipeline: IC review (CIO+FM, needs agent window) -> paper-first with pre-registered kills. NO autoadvance.**
