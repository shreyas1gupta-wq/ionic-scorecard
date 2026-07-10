# S1-F — 0DTE NIFTY ATM Short Straddle (FROZEN SPEC, D-030)
**Status:** REGISTERED for paper forward test · **Frozen:** 2026-07-10 · **Forward clock starts:** first expiry ≥ 2026-07-14
**Owner:** Principal (personal trading line, D-031/D-032) · **Version:** 1.0 — any change = new version, restarted clock

## Strategy
On each NIFTY weekly **expiry day** (derived from live contract data, NOT assumed weekday):
1. **Entry 09:20** (first 1-min close ≥ 09:20): SELL 1× ATM CE + 1× ATM PE, strike = round(spot/50)×50, same-day expiry.
2. **Per-leg stop-loss 30%**: exit leg if its 1-min close ≥ 1.30× entry premium. Market order on breach (backtest fills at next 1-min close).
3. Surviving legs: **exit 15:25** (or let expire; backtest uses last print ≤ 15:25). Always flat EOD. No re-entry.

## Entry vetoes (skip the day entirely if ANY):
- **F1:** RSI(5) of daily NIFTY closes as of D-1 ≥ 80 or ≤ 20.
- **F2:** |D-1 close-to-close return| > 1.5%.
- (~55 skip-days/yr in-sample; vetoed day-types averaged negative.)

## Sizing (Principal capital ₹10L reference)
- Base: `lots = floor(0.75 × equity / ₹1.1L margin)` ≈ 6 lots per ₹10L (≈0.12-Kelly).
- **Crash rule:** HALVE lots when trailing 3-day realized vol (1-min) > 2× its 1-year rolling median.
- Never add size intraday. Lot size 75.

## Pre-registered forward-test kill criteria (frozen now)
- After 26 traded expiries: net expectancy ≤ 0 (at actual fills) → KILL.
- Paper max drawdown > 15% of allocated capital at spec sizing → KILL.
- Tracking: if realized fills persistently worse than backtest model (implementation shortfall > 3 pts/day avg over 13 expiries) → HALT & review at CIO.
- No parameter changes during the test (D-030). Shadow-track: S1 unconditional & S1b (ATM−50) at zero size.

## Evidence base (all files in 04_RND_LAB/results/SELLSIDE_20260710/)
- final_three/: +10.73 pts/day net (1% slip + TC), t=3.92, PF 1.79, both eras positive; robust under two cost models.
- s1_sensitivity/: 84-cell plateau (72/84 positive); ATM−50 gradient logged as challenger S1b.
- covid_backcast/: model-validated (corr 0.64); STRESS-IV 2020 ≈ flat, survives at spec sizing (maxDD ~−16%).
- s1_final_filters/ + s1f_final_graph/: F1/F2 adoption (bar pre-declared); ₹10L→₹35.3L / 28.8% CAGR / −9.9% maxDD in-sample.
- KNOWN LIMITS: no COVID-class day in real option sample; SL on 1-min closes (ticks worse); ~150 in-sample design cells on trials ledger → forward test is the arbiter.

## Paper procedure (daily, expiry days ~09:10)
Run `06_TRADING_DESK/paper/s1f_daily_runner.py` → prints GO/SKIP + order ticket (strike, legs, SL levels, lots) and appends the intent to `06_TRADING_DESK/paper/s1f_paper_log.csv` BEFORE market action (RESEARCH_SOP §12). Mark actual fills at 09:20 vs Angel quotes; mark exits when SL/close hits. Friday /paper reconcile.
