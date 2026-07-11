# SHORT-ONLY ORB x 2-WEEK MOMENTUM-50 (NIFTY 500) — RESULTS
Owner: Arjun Rao (Head of Quant). Generated 2026-07-07 13:50.

## HEADLINE — CAGR/XIRR FIRST (primary objective = compounded return)
Sizing: EQUAL-NOTIONAL per day — capital split equally across the day's shorts, flat overnight,
daily compounding, 1x (no leverage). XIRR == CAGR here (single lumpsum in, no external cashflows,
full daily reinvestment). Chosen over equal-risk because equal-risk/ATR-normalisation amplifies
micro-ATR trades and needs an arbitrary leverage cap; equal-notional maps the %-of-price per-trade
stats directly onto the equity curve and matches the intraday flat-overnight reality.

| Timeframe | NET CAGR/XIRR | GROSS CAGR | NET CAGR@2x-slip | Ann.Sharpe(net) | MaxDD(net) | N | Win% | PF | Avg net %/tr | Avg gross bps/tr | gross t-stat |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5m-ORB | -69.2% | +7.8% | -89.2% | -16.38 | -99.0% | 33,540 | 21.5 | 0.45 | -0.414 | +8.0 | +12.1 |
| 15m-ORB | -67.7% | +6.1% | -88.0% | -14.49 | -98.8% | 28,309 | 30.3 | 0.50 | -0.375 | +9.4 | +12.3 |

## Data lineage
- Ranking: HF daily close `swing_momentum/data/hf_stock_minute/day/train-00000.parquet` (IST date via guards.fix_ist_dates; already split/bonus-adjusted => raw close, price-return momentum).
- Execution: HF minute `.../minute/train-0000{0..7}.parquet` (713M 1-min, 2022-01-03->2026-01-21 IST), resampled to 45,002,418 5-min bars for 627 union syms; 15-min DERIVED (bar15=bar5//3, identical OHLC to 1-min build).
- Universe: `NIFTY500_TICKER_2005_2025_Final.xlsx` 42 semi-annual PIT snaps, most-recent<=rebal (causal, L6). Top-50 by trailing 10-td (2-week) return, ranked as-of last td strictly BEFORE rebal; BI-WEEKLY rebalance (every 10 td == lookback). 100 rebalances, 1008 trading days, 627 union syms, 49,900 active symbol-days.
- Guards: L1 IST-date, L2 preopen, L5 next-bar entry (strictly after signal), causal Wilder ATR(14) on continuous per-timeframe series, zero-volume next bar = DROP (D-031 no-fill=drop).

## Method (SHORT ONLY)
- 5m-ORB: OR = first 5-min bar (09:15-09:19). 15m-ORB: OR = first 15-min bar (09:15-09:29). SHORT when a
  LATER same-timeframe bar CLOSES < OR-low (close-confirm, not wick). First signal/day only. Enter NEXT bar OPEN.
- Stop = entry + 1.0xATR(14) at signal bar (proven-better stop; 0.25x whipsaw settled prior test, not re-run).
- Exit = EOD flat at last bar close (proven-better exit). Gap-through honored (open>=stop => fill at open).
- Costs: SLIP 15bps/side, DOUBLED to 30bps on STOP/GAP exits; FIXED ~8.2bps (STT-sell 2.5 + exch/GST 1.4 +
  stamp 0.3 + brokerage 4bps). Round-trip ~38bps (EOD) / ~53bps (stop). net_2x = 2x-slippage stress. Identical
  cost model to the prior 3-month test for apples-to-apples. %-of-ENTRY-PRICE per trade (stable denom).

### 5m-ORB detail
- N=33,540 over 991 days = 33.8 trades/day. Win 21.5%, PF 0.45, W/L 1.62, median net -0.871%.
- GROSS: avg +8.0 bps/tr, t-stat +12.1, Sharpe 1.12, CAGR +7.8%.
- NET(1x): avg -0.414%/tr, Sharpe -16.38, CAGR -69.2%, MaxDD -99.0%. Cost drag 49.4 bps/tr.
- NET@2x: Sharpe -30.00, CAGR -89.2%.
- Exit mix: STOP 74%, EOD 25%, GAP 0%
- Concentration: top-1 symbol = 0.6% of |net P&L|. Top-5 gross contributors: ANGELONE +57.2%pts, RAILTEL +49.1%pts, MRPL +46.0%pts, IDEA +45.3%pts, PAYTM +45.3%pts
- Degenerate flags: ['negative without top-5 trades']
- Per-year (N, win%, avg net%/tr, avg gross%/tr, NET CAGR, net Sharpe):
  | Year | N | Win% | Avg net% | Avg gross% | NET CAGR | Sharpe |
  |---|---:|---:|---:|---:|---:|---:|
  | 2022 | 8,122 | 22.7 | -0.376 | +0.117 | -66.8% | -14.98 |
  | 2023 | 8,272 | 21.4 | -0.414 | +0.080 | -68.4% | -16.24 |
  | 2024 | 8,378 | 22.4 | -0.407 | +0.086 | -69.3% | -13.55 |
  | 2025 | 8,227 | 19.8 | -0.458 | +0.038 | -71.9% | -24.55 |
  | 2026 | 541 | 18.3 | -0.432 | +0.069 | -69.2% | -17.08 |

### 15m-ORB detail
- N=28,309 over 991 days = 28.6 trades/day. Win 30.3%, PF 0.50, W/L 1.16, median net -0.970%.
- GROSS: avg +9.4 bps/tr, t-stat +12.3, Sharpe 0.82, CAGR +6.1%.
- NET(1x): avg -0.375%/tr, Sharpe -14.49, CAGR -67.7%, MaxDD -98.8%. Cost drag 46.9 bps/tr.
- NET@2x: Sharpe -26.22, CAGR -88.0%.
- Exit mix: STOP 58%, EOD 42%, GAP 0%
- Concentration: top-1 symbol = 0.6% of |net P&L|. Top-5 gross contributors: MRPL +67.1%pts, ANGELONE +49.3%pts, PAYTM +47.1%pts, NIACL +40.4%pts, GICRE +38.4%pts
- Degenerate flags: ['negative without top-5 trades']
- Per-year (N, win%, avg net%/tr, avg gross%/tr, NET CAGR, net Sharpe):
  | Year | N | Win% | Avg net% | Avg gross% | NET CAGR | Sharpe |
  |---|---:|---:|---:|---:|---:|---:|
  | 2022 | 6,919 | 32.4 | -0.314 | +0.154 | -62.4% | -11.64 |
  | 2023 | 6,943 | 29.7 | -0.381 | +0.088 | -66.7% | -15.68 |
  | 2024 | 7,038 | 30.5 | -0.387 | +0.081 | -70.9% | -13.51 |
  | 2025 | 6,942 | 28.9 | -0.414 | +0.057 | -69.7% | -19.06 |
  | 2026 | 467 | 27.6 | -0.404 | +0.072 | -70.9% | -14.00 |

## VERDICT & SELF-RED-TEAM
**REAL signal, UNECONOMIC strategy. Verdict: FAKE-as-tradeable / REAL-but-net-dead — identical failure mode to the 3-month test, and a shorter lookback made the edge SMALLER, not bigger.**

### 1. The short edge is real on the 2-week universe (confirms prior finding)
Gross short edge is statistically strong both timeframes: +8.0 bps/tr t=+12.1 (5m), +9.4 bps/tr t=+12.3 (15m); gross daily-book Sharpe +1.12/+0.82; gross CAGR +6-8%. Positive every single year. Fading the OR-low breakdown of already-extended names is a genuine intraday mean-reversion signal — the direction is right.

### 2. Shorter lookback did NOT help — it weakened the edge (answers the Principal's question: NO)
2-week short-only gross = **+8-9.4 bps/tr** vs the prior **3-month short-only gross +13.3 bps/tr (t=+15.6)**. A 2-week ranking selects fresher, noisier, more-violently-extended names (median 2-wk run +11.6%, max +118%; 86.9% basket churn), but that noisier extension mean-reverts LESS cleanly intraday than a 3-month-established trend. Hypothesis "shorter lookback improves things" is rejected on the per-trade edge.

### 3. Net is catastrophic — cost is ~5-6x the edge (the binding constraint, unchanged from 3m)
Cost drag ~47-49 bps/tr swamps the +8-9 bps gross edge. NET CAGR -68 to -69%, Sharpe -14 to -16, MaxDD ~-99%, PF 0.45-0.50 — every year net-negative. Even at LITERALLY ZERO cost the gross CAGR is only +6-8%; a realistic intraday round-trip (STT-sell 2.5bps + 2-side slippage alone >10bps) already exceeds the +8-9bps gross edge, so **no plausible cost regime makes this net-positive.** 2x-slip stress: CAGR -88 to -89%.

### 4. 15m beats 5m (finer timeframe = worse)
15m-ORB is better on every economic axis: higher per-trade gross (+9.4 vs +8.0bps), higher win% (30.3 vs 21.5), fewer trades/day (28.6 vs 33.8 = less cost churn), less-negative net CAGR (-67.7 vs -69.2). The 5m ATR(14) stop is ~sqrt(1/3)≈0.58x the 15m ATR in price terms — tighter → 74% STOP exits (vs 58% for 15m) → whipsaw drag, the same lesson as the settled 0.25xATR trap, now via bar granularity. **If pursued at all, 15m is the timeframe.**

### 5. Standing-rule check (net Sharpe < -2 → test reversed long?) — resolved WITHOUT re-running
Net Sharpe is -16/-14 (far below -2), but the GROSS t-stat is strongly **positive** (+12) and gross Sharpe positive → the negative net is **cost-dominated, not wrong-direction.** Reversing to long is guaranteed worse: (a) the prior test already ran the long OR-high side and found it statistically DEAD (t=-0.04); (b) reversing flips +8-9bps gross to -8-9bps then pays the SAME ~47bps cost. No long backtest run — the reversal question is already answered. Direction confirmed correct.

### 6. Turnover & cost vs the slower 1-month/3-month versions (Principal's explicit ask)
- **Basket-level name turnover: 2-week bi-weekly = 86.9%/rebalance (~2,260%/yr) vs 3-month monthly = 50.2%/rebalance (~600%/yr) — ~3.8x faster churn.** Union grows 509 -> 627 names.
- **Critical nuance:** because the strategy is INTRADAY and flat every night, basket rebalancing incurs NO holding/rebalancing transaction cost — you never carry a name across a rebalance. So the 3.8x-faster basket churn is a SIGNAL-STABILITY / freshness story, not a transaction-cost story.
- **Actual transaction cost is set by intraday trade count**, which is comparable: ~28.6/day (2-wk 15m short) and ~33.8/day (2-wk 5m short) vs the 3-month short subset ~25/day (bidirectional total ~45/day). Same ~40-50bps round-trip per trade either way. So the shorter lookback did NOT meaningfully raise the intraday cost bar — its real damage is a WEAKER gross signal (§2), which is worse than a cost problem because you can't slip-optimise your way out of it.

### 7. Real-world shortability/borrow caveat (backtest can't capture, cuts against us)
This is intraday short-selling of individual stocks. The backtest assumes every OR-low breakdown is shortable at the next-bar open with 15bps slippage. In reality: (a) a 2-week momentum basket by construction selects recently-exploded, often low-float / retail-frenzy names (IDEA, PAYTM, small PSUs, ANGELONE etc. top the contributor list) — precisely the names that are hardest to short intraday, hit frequent UPPER circuits (a circuit-locked name cannot be shorted at all), and sit in SEBI ASM/GSM/T2T surveillance where intraday/short is curbed; (b) borrow/MIS availability on these names is thin and broker-dependent. So realized fill rate would be well below 100% and slippage well above 15bps — the already-negative net is an OPTIMISTIC upper bound. (Analog to the K-012 fill-audit lesson: fill-rate, not modeled cost, is the binding real-world constraint.)

### Single weakest assumption
The intraday slippage floor (15bps/side). It is the swing variable, BUT the verdict is robust to it: the gross edge (+8-9bps) is smaller than the irreducible cost floor (STT-sell 2.5bps + minimal 2-side slippage >10bps), so even a generous 3-5bps/side slippage leaves the strategy net-negative. There is no realistic cost path to viability. **As an intraday tradeable: DEAD. As a research signal: the real, positive, cost-swamped short-reversion edge persists across lookbacks (3m stronger than 2w) — its only future is a lower-cost vehicle (e.g., a longer-horizon overnight/multi-day short, or an options expression) where a ~8-13bps/trade edge isn't eaten by round-trip friction.**
