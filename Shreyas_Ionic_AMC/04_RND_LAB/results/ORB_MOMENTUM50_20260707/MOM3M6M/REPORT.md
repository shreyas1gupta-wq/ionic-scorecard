# ORB 15-min breakout — NIFTY500 momentum-50 (3m+6m combined ranking) — 2026-07-07
Agent's own REPORT.md write was blocked by subagent policy; content below is verbatim from the agent's final report.

## Verdict: FAIL — real gross signal, economically dead after realistic intraday cost

All 4 SL x exit combinations lose net, every year, by a wide and stable margin.

## Summary (base cost 0.35% round-trip; %/trade = %-of-entry-price)

| Combo (SL x exit) | N | win% | PF | gross%/tr | net%/tr | ann.Sharpe | maxDD |
|---|---|---|---|---|---|---|---|
| C1: 0.25xATR x EOD | 44,333 | 8.4 | 0.31 | +0.027 | -0.323 | -23.4 | -96% |
| C2: 0.25xATR x trail | 44,333 | 10.8 | 0.26 | +0.020 | -0.330 | -35.6 | -96% |
| **C3: 1.0xATR x EOD** | 44,333 | 26.6 | 0.59 | +0.075 | -0.275 | -10.4 | -94% |
| C4: 1.0xATR x trail | 44,333 | 25.5 | 0.46 | +0.040 | -0.310 | -18.4 | -96% |

**Best = C3 (wide 1.0xATR stop + EOD hold), best on every metric.** The 0.25xATR stop sits inside one 15-min bar's normal noise range and gets whipsawed out constantly (only 8-11% win rate); on a low-edge intraday drift, trailing exits also cut winners short and add extra cost. This confirms the brief's premise that a 0.25xATR stop is too tight for a 15-min ORB.

**But "best" only means "loses least."** The gross ORB drift is real — C3's gross edge is +0.075%/trade with t-stat 11.3, gross annualized Sharpe 2.47. The strategy's own break-even round-trip cost is only about 7.5 basis points. Realistic intraday-equity friction is roughly 35bps (20-30bps slippage plus STT/fees); even an optimistic 25bps round-trip leaves C3 at -0.176%/trade, and a 2x cost stress brings it to -0.575%/trade. The result is net-negative in all 5 year-slices (2022-2026), tightly clustered rather than concentrated in one bad year — this is a stable structural loss, not a regime artifact.

**This is the same shape as the firm's FF-calendar kill: signal real, vehicle dead on friction.**

## Concentration and turnover checks
No name concentration: the top contributing name accounts for only 0.24% of total |P&L| across 468 distinct names traded, at roughly 44 trades/day. Turnover-cost sensitivity is total — this is a 100%-turnover-cost-dominated result (44,333 intraday round-trips against a 7.5bps edge and ~35bps cost). The monthly basket-rebalance turnover is second-order next to the daily round-trip bleed. Degenerate-result detectors are clean (no Sharpe>4, no win-rate>75%, no R-squared>0.98 equity-curve artifact).

**Weakest assumption is the cost model itself — and it's where the strategy has the least room.** The gross edge sits below even the most optimistic conceivable friction estimate for this instrument/frequency.

## Combined (3m+6m) vs pure-3m basket overlap
The combined-momentum basket shares 38.6 of 50 names (about 77%) with the pure-3m basket on average, ranging 34-44 overlapping names per month. The 6-month leg adds steadier long-running trends and drops some 3-month spike names, but both baskets feed the identical ORB signal — since momentum-selection flavor doesn't change the underlying cost-vs-edge math, the parallel pure-3m run should be expected to hit the same cost wall.

## Files
`Shreyas_Ionic_AMC/04_RND_LAB/results/ORB_MOMENTUM50_20260707/MOM3M6M/` contains `trades_C1..C4_*.csv` (44,333 rows each: date, symbol, month, direction, entry/exit price, exit_reason, ATR, opening-range high/low, gross, net_base, net_2x) and `metrics.json`.
