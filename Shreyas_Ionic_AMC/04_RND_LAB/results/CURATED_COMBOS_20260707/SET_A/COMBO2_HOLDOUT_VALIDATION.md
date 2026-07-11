# Combo 2 — Pre-registered era-holdout validation (Arjun Rao / Quant)
Date 2026-07-07. Spec FROZEN as originally run (15m / weekly / ATM+/-1 / EMA20 trend / 20-bar breakout / ATR-stop / VIX-band filter / vol-scale sizing), NIFTY weekly options 2021-05 to 2026-06. NO re-optimization — this is a formal split of the existing trade-level result, not a re-fit.

## Data lineage
- Source: `SET_A/C2_trades.csv` (199 trades, 200 lines incl. header) + `SET_A/stats_C2.json`. Same engine/marks as the 2026-07-07 curated run.
- Denominator-free: %spot = pnl_pts / entry_spot. Net = after approved costs (cost_pts); 2x = gross - 2*cost_pts. P&L is one atomic exit-booked number per trade (no cross-day spreading -> no fake-low-variance artifact).
- Era = ENTRY year (regime the signal fired in). Reconciles exactly to stats_C2.json yearly block: 2024 N=53, ex-2024 N=146. Full-sample rebuild = Sharpe 0.295 (~reported 0.30), total +5.32%, mean +0.0267% -> engine match confirmed.
- Sharpe annualized per era by that era's own trade frequency (tpy). CAGR = geometric compounding of per-trade %spot at 1x-spot notional/trade, single position, annualized over the era span (=XIRR for this rolling single-unit book).

## Three eras, reported separately (NO pooling)

| Metric | Era A 2021-2023 (DEV) | Era B 2024 | Era C 2025-2026-06 (HOLDOUT) |
|---|--:|--:|--:|
| N | 98 | 53 | 48 |
| win% | 26.5 | 28.3 | 18.8 |
| PF (net) | 0.93 | 1.85 | 1.09 |
| mean %spot net (1x) | -0.0176 | +0.111 | +0.0243 |
| total %spot net (1x) | -1.73 | +5.89 | +1.17 |
| mean %spot net @2x | -0.0248 | +0.105 | +0.0181 |
| total %spot net @2x | -2.43 | +5.56 | +0.87 |
| Sharpe (ann) | -0.22 | +1.32 | +0.21 |
| CAGR 1x (compounded) | -0.8% | +6.06% | +0.79% |
| CAGR 2x (compounded) | -1.1% | +5.72% | +0.57% |

Read: the "development window" (Era A) was outright NEGATIVE. 2024 (Era B) carries the entire result. The true forward holdout (Era C) is marginally positive but effectively FLAT — PF barely over 1, Sharpe 0.21 at N=48 (indistinguishable from zero), and it shrinks toward breakeven under 2x cost. Era C is an order of magnitude weaker than Era B (0.79% vs 6.06% CAGR); it is NOT consistent with Era B.

## Multiple-testing honesty (trials = 10)
This combo was 1 of 10 curated cells run 2026-07-07 (SET_A C1-C5 + SET_B C6-C10). It was NOT even the best: C9 posted net Sharpe +0.578 (PF 1.36) vs C2's +0.30 — 2 of 10 cells printed positive, the false-discovery rate you'd expect from noise.

purgedcv (Bailey & Lopez de Prado), var_sharpe from the 10 trials' per-observation Sharpes (0.00903):
- PSR vs 0 (no trial adjustment) = **0.748** — even ignoring the search, only 75% confidence the true Sharpe > 0.
- **DSR (n_trials=10) = 0.062** vs 0.95 bar. Observed per-obs SR 0.045 < deflated benchmark sr* 0.150 (expected max-Z of 10 noise trials = 1.57). effective_n_trials = 10 (independent cells, no autocorrelation discount).
- Interpretation: the FULL-SAMPLE +0.30 Sharpe (which already includes the 2024 windfall) does not clear the bar you'd expect from the best of a 10-cell search. It is a search artifact.

## VERDICT: NO-GO / FAKE-to-FRAGILE — does NOT survive proper validation
The edge does NOT persist into Era C in any economically or statistically meaningful way. Era C is flat (+0.024%/trade net, +0.018% at 2x, Sharpe 0.21, PF 1.09, N=48 — noise), the development window was negative, and 100%+ of the all-in edge is the single 2024 regime. DSR at the honest 10-trial count = 0.062 << 0.95. Do not pursue this combo further.

Single weakest assumption if anyone wants to defend it: that 2024's regime (whatever drove the +5.89%) recurs and is capturable at scale — unsupported by the two flanking eras, and untestable without a fresh, genuinely-unseen forward window.
