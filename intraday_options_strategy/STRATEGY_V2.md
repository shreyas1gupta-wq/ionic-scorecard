# STRATEGY V2 — Regime-Aware Multi-Sleeve Ensemble (design contract)

> Goal restated honestly: NOT "beat Jane Street" (their edge = flow + microstructure
> + colocation, structurally unavailable at retail). Goal = a portfolio of 3–5
> **uncorrelated, regime-gated sleeves** with positive after-cost expectancy,
> CAGR meaningfully above cash with max DD < 12%, that survives walk-forward and
> robustness tests, and is executable through Angel One (paper) → Kotak Neo (live).

## Why v1 failed (evidence, 19+ WFO folds)
Long-options-only signal chasing: forward WR 27–48% (target 55% never feasible
in ANY in-sample window), theta drag ~₹11–16/day/unit, costs ~0.9% of premium
per round trip, capital under-deployed (Kelly halts on negative edge). Lesson:
the retail-accessible edge in index options is mostly **short volatility,
harvested in the right regime, with hard risk caps** — long options only pay on
confirmed trend days.

## Sleeves (uncorrelated by construction)
| ID | Sleeve | Edge hypothesis | Regime gate | Default risk rules |
|----|--------|-----------------|-------------|--------------------|
| S1 | Momentum long options (v1, best WFO params) | trend continuation | ADX>25 + multi-horizon trend agree | SL 25–30% prem, partial book |
| S2 | Range-day short straddle (09:20→15:00) | intraday theta > realized move on range days | gap <0.3%, VIX 11–22, ADX<25, no event day, NOT expiry day | SL 30% of credit (combo), profit-take at 50% credit captured, hard 15:00 |
| S3 | 0DTE expiry-day short straddle (09:20→14:30) | expiry-day theta crush (gamma-aware) | expiry day, gap <0.4%, VIX<24, no event day | SL 25% combo, PT 60% captured, hard 14:30; half size vs S2 |
| S4 | Trend-day rider (ORB + regime) | fat-tail trend days pay convexity | ADX 5m >28 + ORB break + range expansion + horizon bias agree | partial book 50% @ +35%, trail 25% from peak on rest, SL 30% |

Notes:
- S2/S3 are SHORT premium: margin-based sizing (approx SPAN: 12% notional/leg
  minus credit, configurable), per-leg AND combo SL, both-legs-priced walk
  (straddle is convex in S → intrabar worst case at bar's H or L endpoints,
  best case at S=clip(K, L, H)).
- Weekly expiries did not exist for Nifty before 2019-02-11 (monthly only) →
  ExpiryCalendar v2 uses last-Thursday monthlies before that date; S3 runs
  only from 2019-02 onward. (v1 backtest pre-2019 weekly assumption = caveat.)
- Multi-horizon trend bias (user ask): daily closes → returns over 1d/1w/1m/
  3m/6m + EMA20/50/200 stack → bias score in {-2..+2}; S1/S4 direction filter,
  S2/S3 unaffected (delta-neutral entries).

## Portfolio allocation (regime + risk aware)
1. Day-type features at 09:20 (no lookahead): gap%, ORB15 width %ile, prior-day
   VIX close & 5d change, ADX(5m) at 09:20, expiry flag, horizon-bias score.
2. Regime suitability gates per sleeve (table above) — binary eligibility.
3. Capital weights among eligible sleeves: inverse 60d rolling sleeve vol
   (vol-parity) × rolling 60d sleeve hit-quality (Sharpe floored at 0; sleeve
   disabled if 60d Sharpe < -1 → alpha-decay guard) → normalize → cap any
   sleeve at 50% of day's risk budget.
4. Risk budget: base 0.6% of equity at risk per day (sum of sleeve max-loss
   estimates); fractional-Kelly cap on top (0.25×f* per sleeve from its own
   trailing 60d stats); **drawdown governor**: if 20d equity DD >4% → ×0.5
   budget, >8% → ×0.25, recovery hysteresis at half the trigger.
5. Hard caps: ≤10 lots/leg (freeze-qty realism), combined short-leg margin
   ≤ 60% of capital, total premium outlay (long sleeves) ≤ 10%.

## Execution policy (paper → live; cannot be backtested on OHLCV — measured in paper month)
- Maintain synthetic fair value (BS @ live VIX) per working strike; live chain
  quote vs fair value = disparity signal.
- ENTRY: limit at mid ± 0.1×spread (join, don't cross). If unfilled in 3s and
  signal still valid → cross half-spread; market order ONLY if spread ≤ 0.05%
  of premium (ATM weeklies usually 0.5–2 ticks) or on SL exits.
- EXIT: SL = market (certainty > price). Profit-take = limit at level, convert
  to market if breached by >0.3×spread. EOD square-off = market 15:18–15:19.
- Angel One paper month measures: realized slippage vs assumed 0.15%/leg,
  fill ratios of join-vs-cross, latency signal→ack. These FEED BACK into the
  backtest cost model (rerun robustness with measured numbers before Kotak Neo).
- Freeze qty (Nifty ~1800 qty/order): split orders above; never sweep.

## Anti-overfit discipline (binding)
- All sleeve params chosen from SMALL grids (≤4 values/param) via the v1 WFO
  framework reused per sleeve; OOS (post 2022-12-16) untouched until final.
- Deflated-Sharpe sanity: with ~648-point grids, demand OOS Sharpe > 1.0 and
  OOS/IS performance ratio > 0.5 before any live capital.
- Alpha-decay monitor in live: trailing 60d sleeve Sharpe < -1 → sleeve off.
- No parameter may be changed based on OOS results (one-shot evaluation).

## Synthetic-pricing caveats (carried into report)
BS @ VIX has no smile (sold strangles will look better than reality), no
spread-widening on crashes, no event-vol crush. Mitigations: ATM-only entries,
event-day filter, slippage stress ×2–6 in robustness, paper-month calibration.

## File map (v2 additions)
- features/horizon.py — daily multi-horizon trend bias + day-type features
- options/option_selector.py — monthly-expiry rule pre-2019-02-11 (edit)
- backtest/engine_v2.py — multi-leg positions, short margin, partial booking,
  trailing stops, combo SL/PT walk
- strategies/sleeves.py — S1..S4 signal/entry/exit configs
- portfolio/allocator.py — regime gates, vol-parity weights, Kelly cap, DD governor
- run_v2.py — sleeve backtests, correlation matrix, combined portfolio, report
