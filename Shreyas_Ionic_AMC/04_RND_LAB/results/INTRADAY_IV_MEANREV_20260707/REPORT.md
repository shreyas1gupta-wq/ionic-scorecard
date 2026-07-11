# Intraday IV mean-reversion (short-vol), NIFTY weekly options — 2026-07-07
Agent chose not to write a separate report file (leaf-agent write-block workaround); content below is verbatim from its final report.

## Verdict: FAKE (no net edge)

Data: 261 weekly expiries 2021-05-27 to 2026-06-02 via `chain.py`; 1-min OHLCV+OI; guards enforced (>=09:15, minute-schema, no L1/L6 bugs). Causal IV computed as ATM straddle price / (0.7979 x Spot x sqrt(T)) (de-trends theta). "Elevated" IV = current IV >= the trailing-120-bar Nth percentile, using `.shift(1)` so only prior bars are used (causal). Fills have a 1-bar lag; no-fill = DROP (zero drops occurred — ATM plus 250-point wings were always liquid). Costs per APPROVED COST_STANDARDS. P&L booked at exit-day (intraday only, no cross-day spreading). Edge reported in POINTS and %-of-spot, never %-of-premium.

## Grid results

| Cell | N | win% | W/L | PF | net pts | %spot | Sharpe net | Sharpe gross | Sharpe @2x | worst day |
|---|---|---|---|---|---|---|---|---|---|---|
| straddle_70_1.5 | 1191 | 51.0 | 0.82 | 0.85 | -1.88 | -0.0089 | -0.73 | +0.60 | -2.04 | -578 |
| straddle_70_2.0 | 1191 | 52.3 | 0.80 | 0.87 | -1.59 | -0.0074 | -0.59 | +0.71 | -1.89 | -250 |
| straddle_85_1.5 | 1114 | 50.5 | 0.77 | 0.79 | -2.46 | -0.0124 | -1.08 | +0.33 | -2.47 | -578 |
| straddle_85_2.0 | 1114 | 51.7 | 0.77 | 0.83 | -2.02 | -0.0104 | -0.92 | +0.51 | -2.34 | -245 |
| ironfly_70 | 1191 | 31.2 | 1.11 | 0.50 | -5.40 | -0.0267 | -2.95 | +0.13 | -5.97 | -153 |
| ironfly_85 | 1114 | 28.5 | 1.13 | 0.45 | -5.78 | -0.0290 | -3.40 | -0.13 | -6.61 | -153 |
| REV_ironfly_70 (reversed, long) | 1191 | 18.2 | - | 0.51 | -5.95 | - | -3.24 | -0.13 | -6.35 | -130 |
| REV_ironfly_85 (reversed, long) | 1114 | 18.5 | - | 0.51 | -5.51 | - | -3.17 | +0.13 | -6.48 | -111 |

Both iron-fly cells breached the Sharpe < -2 standing-rule trigger, so their reversed (long) versions were run as twins: both still lose, and the fly's gross Sharpe is approximately zero in either direction — confirming the fly's loss is pure 4-leg transaction-cost bleed, not a directional mistake.

**Best combination: straddle_70_2.0** (net Sharpe -0.59, gross Sharpe +0.71, PF 0.87) — the least-bad cell, still a net loser, and fails both the 2x-cost stress gate and the basic sign gate.

## Tail-risk read
Worst single day was -578 points on 2024-06-04 (the election-result day) — the strategy sold an 859-point credit and the 1.5x stop gapped through on a lagged fill. The next-worst days were 2026-02-01 (Budget day, -331) and 2024-08-05 (a volatility shock day, -203). Every tail event lines up with a known macro-event day, not a random cluster.

Exit-reason breakdown for straddle_70_2.0: 772 "revert" exits average +6.73/trade (this is the real underlying edge), but 45 "stop" exits average -112/trade (summing to -5,062, which erases the entire revert-edge total) plus EOD exits contributing -2,027. The iron-fly structure bounds the tail (worst day only -153 vs the straddle's -578) but kills the edge entirely in doing so — the defined-risk wings cost more in round-trip friction than they save in tail protection.

## Degenerate-result check
The feared pattern — high win-rate masking a fat tail — did NOT fire here. The straddle cells are honestly close to a 50% coin-flip (51-52% win, W/L ratio ~0.8), consistent with cost drag on a real but small edge, not a hidden tail-seller. The iron-fly cells show the opposite shape (28-31% win) but for a different reason (structural cost, not tail-hiding). Only the generic "negative without top-5 trades" flag fired, which is expected and uninformative for an already-net-negative book. The result is negative in every year and every regime tested, which argues this is a robust "no net edge" finding rather than noise.

## Verdict and weakest assumption
A real gross mean-reversion edge does exist (the revert-exit trades are genuinely profitable on their own), but it dies to two-sided transaction cost (about 3.3 points round-trip against about 1.7 points of gross edge) plus an essentially uncontainable event-day left tail. The weakest assumption tested was the 0.25%-of-premium slippage floor, which is almost certainly optimistic on exactly the event days that create the worst tail losses — meaning the true net result is likely below what's shown here, not above it. **Do not advance.**

## Files
`Shreyas_Ionic_AMC/04_RND_LAB/results/INTRADAY_IV_MEANREV_20260707/` contains 8 `trades_*.csv` files (including the 2 reversed iron-fly runs), `_metrics.json`, `_reversal.json`, and an empty `_drops.json` (zero drops occurred). Engine and metrics scripts plus a frozen spec are in the agent's scratchpad (`ivmr_engine.py`, `ivmr_metrics.py`, `ivmr_finalize.py`, `ivmr_PROGRESS.md`).
