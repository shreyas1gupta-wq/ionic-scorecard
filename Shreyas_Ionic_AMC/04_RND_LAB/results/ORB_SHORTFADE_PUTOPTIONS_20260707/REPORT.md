# ORB short-fade via buying puts (instead of shorting the stock) — 2026-07-07
Agent's own REPORT.md write was blocked by subagent policy; content below is verbatim from its final report.

## Verdict: FAKE-as-an-escape, DEAD vehicle

## Gating stat — F&O universe overlap
Only 184 of 509 momentum-universe names (36%) have listed single-stock options at all; across the full history, only 42.9% of the 2,450 basket-slots (name-months) are F&O-eligible (ranging 40-47% per year). The momentum-50 basket skews toward extended small/mid-caps that sit outside the roughly 210-name F&O list (examples absent from F&O: HINDCOPPER, IRCTC, ZEEL, even TATAMOTORS at points). About 57% of the opportunity set is untradeable via options before any cost is even considered.

## Executability funnel — the real killer
Of 25,384 short signals from the original cash-short test: 10,731 are in F&O-eligible names, but only 1,099 (4.3% of the original signal count) are actually tradeable as same-day puts. The other 8,849 drop because their option month sits on the DAILY-only schema (single-stock options in India are monthly, with no weekly series, and cannot be intraday-priced for a same-day trade in that schema) — the 1-min single-stock options data only exists for 2022 through March 2024 and September 2025 onward, leaving large gaps. This is roughly a 96% coverage collapse from the already-reduced F&O-eligible pool.

## Results (net; 3%-of-premium conservative option spread assumption)

| Variant | N | Win% | PF | Net %-spot | Sharpe | CAGR (%-of-spot basis) | CAGR (per-premium-deployed basis) |
|---|--:|--:|--:|--:|--:|--:|--:|
| ATM put | 1,072 | 23.9 | 0.50 | -16.2bps | -6.8 | -37.9% | -100% |
| 1-strike-OTM put | 952 | 23.2 | 0.55 | -10.1bps | -5.0 | -23.9% | -100% |
| cash-short (today, for comparison) | 25,384 | 31.7 | - | -33.6bps | -13.9 | -66% / -69% | n/a |

The signal itself is still known-good on the filled subset (underlying short-side edge +7.78bps, t-stat 2.67) — this result is a statement about the vehicle being wrong, not a re-refutation of the signal, so no reversal test was run (the standing rule doesn't apply meaningfully here since we already know the direction is correct).

## Why it fails even though it avoids the borrow/shortability problem
Even at ZERO option cost (no spread at all), the put only captures roughly 0% (ATM, actually slightly negative at -8%) to 3% (OTM) of the known 8bps intraday underlying edge. Monthly-only single-stock puts carry theta decay and sub-1.0 delta that simply cannot capture a fast, small (8bps) intraday move — the option barely moves in response to the underlying's intraday swing, so stop-loss exits get held on the option side while the underlying itself is already rallying back against the position. The put's apparently "less-negative" %-of-spot CAGR figures are an accounting artifact of trading 24x fewer times and deploying only about 2% of notional as premium — when measured honestly against the actual premium capital deployed (the return an options buyer really experiences), both variants show a full -100% wipeout.

## Bottom line
Buying puts trades one friction (cash-equity borrow/shortability) for a worse one (3%+ bid-ask spread plus theta decay) and simultaneously destroys most of the strategy's capacity via the coverage collapse. The weakest assumption tested (the 3% spread) is not load-bearing — the result is negative even at zero cost, meaning the structural mismatch between option sensitivity and the intraday move size is the real problem, not friction. **Recommendation: do not pursue.**

## Files
`Shreyas_Ionic_AMC/04_RND_LAB/results/ORB_SHORTFADE_PUTOPTIONS_20260707/` contains `trades_ATM_put.csv` (1,072 rows), `trades_OTM_put.csv` (952 rows), `trades_all_legs.csv` (includes drop-diagnostics for the executability funnel), and `metrics.json`.
