# Scalping System V7 — NIFTY 50 STOCKS universe — 2026-07-07
Agent's own REPORT.md write was blocked by subagent policy; content below is verbatim from the agent's final report.

## Verdict: FAKE / NO-EDGE (losing system)

The signal is negative-expectancy **even gross of costs**, uniformly across all 50 stocks, both timeframes, all 3 variants, and every year 2022-2026. Costs then bury it further at approximately -0.26%/trade round-trip.

## Summary (net = after 0.259% round-trip cost; edge as %-of-price/trade, pooled denominator-free)

| TF | Variant | N | net-win% | PF | avg gross% | avg net% | ann.Sharpe | maxDD |
|----|---------|--:|--:|--:|--:|--:|--:|--:|
| 5m | V1 base | 206,000 | 11.6 | 0.11 | -0.012 | -0.271 | -57.8 | -268% |
| 5m | V2 +4H | 103,883 | 11.6 | 0.12 | -0.011 | -0.270 | -54.1 | -270% |
| 5m | V3 +Daily | 104,866 | 11.6 | 0.12 | -0.011 | -0.270 | -53.5 | -270% |
| 15m | V1 base | 65,406 | 19.7 | 0.26 | -0.008 | -0.267 | -30.9 | -259% |
| 15m | V2 +4H | 32,818 | 19.3 | 0.26 | -0.008 | -0.267 | -24.7 | -269% |
| 15m | V3 +Daily | 32,826 | 19.5 | 0.27 | -0.005 | -0.264 | -23.7 | -266% |

**Best (academic only): 15m V3** — "loses slowest." 15-minute beats 5-minute everywhere; the 4H/Daily higher-timeframe filters halve the trade count but add no edge (gross stays negative in every cell). The annualized Sharpe figures are enormous negatives because a signal-free book drips a fixed cost every day — the equity curve is close to a straight line down (R² approximately 1.0).

## Concentration check: none — the opposite

Zero of the 50 stocks are net-positive in any configuration. The top-5 stocks by absolute contribution account for only about 11% of total P&L. This is a broad, structural loss across the whole universe, not a handful of bad names dragging down an otherwise-working system.

## Cost is not the culprit

Even under an optimistic 16bps round-trip cost assumption, the system still loses about -0.17%/trade — and the gross (before any cost) edge is already negative. This weakest-assumption stress test does not change the verdict.

## Faithfulness flags (translation notes)
- The `longTrades`/`shortTrades` counters increment on every bar where the signal condition is true, not just on bars where a new position actually opens — replicated exactly per the original script's logic.
- The visual-only re-entry/continuation/warning plots (`reLong`, `reShort`, `longContinue`, `shortContinue`) do not affect position state — correctly ignored as non-tradeable signals.
- The script has no explicit EOD-flat rule, so about 15% of 15-minute trades held overnight, carrying real gap risk — flagged, but does not rescue the verdict (already negative intraday).
- The fixed 120-point "avoid chase" and 15-point "profit lock" thresholds were converted to %-of-price per stock (0.48% and 0.06% respectively) per instruction, since a flat point value cannot apply across stocks of very different prices.
- Stock data coverage ends 2026-01-21 (a stale tail in the HF dataset) — the backtest window runs up to that date.

## Files
`Shreyas_Ionic_AMC/04_RND_LAB/results/SCALPING_V7_20260707/STOCKS_UNIVERSE/` contains `trades_all.csv` (545,799 rows, all 6 configurations), `coverage.csv`, `summary_metrics.csv`. Engine script was written to the agent's scratchpad as `scalp_v7_stocks.py`.
