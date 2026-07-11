# VWAP+RSI intraday momentum via ATM NIFTY weekly options — 2026-07-07
Agent's own REPORT.md write was blocked by subagent policy; content below is verbatim from the agent's final report.

## Verdict: FAILED / KILL (cost-dominated buying loser)

Data: NIFTY spot 1-min (477,738 bars) plus 261 weekly option expiries, 2021-05 to 2026-06, 1,238 trading days processed with 0 dropped. Guards L1/L2/L5/L6/L7 plus fill-realism (no-quote = DROP) all enforced. Costs per APPROVED COST_STANDARDS (D-021).

## Grid (net and gross in premium points/trade; Sharpe annualized on daily %-of-spot)

| RSI threshold | Exit | Variant | N | win% | PF | net pts | gross pts | net@2x | Sharpe | maxDD %spot |
|---|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| 55/45 | EOD | Original | 1337 | 39 | 0.86 | -3.79 | -2.09 | -5.49 | -0.65 | -24 |
| 55/45 | EOD | Reversed | 1337 | 39 | 0.79 | -5.88 | -4.17 | -7.59 | -1.18 | -45 |
| 55/45 | target/stop | Original | 10058 | 42 | 0.77 | -2.01 | -0.25 | -3.77 | -4.90 | -99 |
| 55/45 | target/stop | Reversed | 10399 | 39 | 0.65 | -2.88 | -1.12 | -4.64 | -6.95 | -147 |
| 55/45 | trailing | Original | 2589 | 35 | 0.91 | -1.58 | +0.09 | -3.24 | -0.63 | -26 |
| 60/40 | EOD | Original | 1319 | 39 | 0.84 | -4.31 | -2.61 | -6.02 | -0.81 | -27 |
| 60/40 | target/stop | Original | 8513 | 42 | 0.75 | -2.22 | -0.47 | -3.98 | -4.91 | -92 |
| 60/40 | target/stop | Reversed | 8973 | 40 | 0.66 | -2.79 | -1.03 | -4.55 | -6.27 | -124 |
| 60/40 | trailing | Original | 2429 | 35 | 0.91 | -1.60 | +0.07 | -3.27 | -0.62 | -22 |
| cross-50 | EOD | Original | 1070 | 44 | 0.93 | -1.38 | +0.31 | -3.08 | -0.45 | -17 |
| cross-50 | target/stop | Original | 2343 | 42 | 0.77 | -1.90 | -0.20 | -3.60 | -2.41 | -23 |
| cross-50 | target/stop | Reversed | 2244 | 39 | 0.69 | -2.42 | -0.73 | -4.12 | -3.04 | -26 |

The remaining 6 cells net -1.5 to -6.6 points, all negative. Full 18-cell grid is in `grid_metrics.csv`.

**Best (least-bad) cell: cross-50 RSI trigger, EOD exit, original (non-reversed) direction** — net -1.38 points (-0.008% of spot), Sharpe -0.45. Still a net loser.

## Honest verdict

This is a cost-dominated options-buying loser, consistent with the firm's standing VRP prior. Gross P&L per trade straddles zero across the whole grid (-2.6 to +0.31 points), meaning the signal itself has no directional edge to speak of — the round-trip cost (roughly 1.7 points, about 1.38% of the ~123-point ATM premium) is what sinks every single cell.

Per the standing reversal rule, all six cells that breached Sharpe < -2 (the target/stop grid, labeled "Reversed" above) have their reversed versions reported: the reversed gross edge is worse or comparable and stays negative, confirming the loss is cost-driven, not a directional/sign error.

Every full calendar year from 2022 to 2025 is net-negative. The only nominally-positive net results occur in two partial-year windows (2021 from May onward, and 2026 up to June) — this is a partial-year sampling artifact, not real alpha. DSR/PBO/walk-forward validation is moot here since those tools exist to catch false positives, and there is no positive result to defend in the first place.

**Weakest assumption:** the "VWAP" component had to be approximated as an equal-weight average since spot-index volume is effectively zero/absent in the data, and the EOD exit rule is anchor-agnostic regardless. Neither of these approximations could plausibly manufacture the missing ~1.7 points of edge needed to close the gap — the verdict is unchanged by this limitation. **Do not advance.**

## Files
`Shreyas_Ionic_AMC/04_RND_LAB/results/VWAP_RSI_MOMENTUM_20260707/` contains `grid_metrics.csv`, `grid_metrics.json`, 18 per-cell trade CSVs under `trades/`, and the frozen `backtest.py`.
