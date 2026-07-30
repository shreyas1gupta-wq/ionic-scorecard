# VERDICT — Intraday EMA-momentum NIFTY 50 option buying: **KILLED** (Stage-1 gate failed)

**Run:** 2026-07-29, DESK-100 | **Pre-registration:** `04_RND_LAB/ideas/20260729_intraday_ema_option_buying.md`
(kill criteria were fixed in writing BEFORE any data was touched — D-035)
**Data:** NIFTY 1-min spot, 463,826 bars, 2021-05-24 → 2026-06-03. Bars filtered to >=09:15
(pre-open auction landmine #2 — the raw file does contain 09:07 auction prints).
**Verdict:** `STAGE1_FAILED_kill_no_option_layer`. Stage-2 option P&L layer was NOT built,
per the pre-registered rule. Nothing here was tuned after seeing results.

## Stage 1 — does the signal predict a move big enough to pay for an option?
Signed forward move (sign = +1 bullish cross, −1 bearish cross), build 2021-05→2025-12.
Pass bar was **≥0.30%** (conservative low end of the documented ATM intraday option breakeven
band of 0.30–0.50%), t≥2.0, largest-day share ≤30%.

| cell | n (build) | best signed mean | vs 0.30% bar | NW t | hit rate | MFE / \|MAE\| | verdict |
|---|---|---|---|---|---|---|---|
| 5min EMA 9/21 | 4,305 | **+0.0052%** | **58x too small** | 1.18 | 50.2% | 1.018 | FAIL |
| 5min EMA 20/50 | 2,857 | **+0.0040%** | **75x too small** | 0.61 | 50.9% | 1.004 | FAIL |
| 15min EMA 9/21 | 2,333 | **+0.0101%** | **30x too small** | 1.28 | 51.3% | 1.011 | FAIL |

Three independent reasons this is dead, not merely weak:
1. **Magnitude:** the signal moves the index 0.004–0.010%. An ATM weekly option needs ~0.30–0.50%
   (≈60–100 NIFTY points) to break even intraday. The gap is 30–75x, not a tuning gap.
2. **Direction:** hit rate 50.2–51.3% — a coin flip. The EMA cross does not predict direction.
3. **No convexity:** MFE/|MAE| = **1.004–1.018**. Favourable and adverse excursions are
   symmetric, so no trailing-exit or convex-payoff trick can rescue it. An option buyer needs
   asymmetry and there is none.

Gate 3 (100-run randomized placebo) was deliberately NOT run on these cells: it can only ever
REJECT a cell, never rescue one, so spending ~1 hour of compute on already-failed cells would
change no conclusion. Disclosed rather than silently skipped.

**Independent corroboration:** MFE/|MAE| ≈ 1.00 reproduces the prior study's finding
(`intraday_options_strategy/buying/REPORT.md`, 2026-07-01) *via a different signal* — that study
measured ORB/breakout and daily-EMA triggers; this one measured intraday 5m/15m EMA crosses,
which were the one untested gap. Same answer. The family is now closed from two directions.

## Futures arm — the diagnostic that makes the kill unambiguous
Same signal traded delta-1 (NO theta, NO VRP drag — the cheapest possible way to express it),
mandatory flat 15:25, opposite-cross exit, ±0.4% stop variant, real retail futures costs.

| cell | n | gross pts/trade | net | PF | NW t | months + (net) |
|---|---|---|---|---|---|---|
| 5min EMA9/21 nostop | 4,305 | +1.63 | **−₹13.4L** | 0.82 | **−4.55** | 12/56 |
| 5min EMA9/21 stop | 4,305 | +2.13 | −₹13.4L | 0.84 | −4.13 | 12/56 |
| 5min EMA20/50 nostop | 2,857 | +1.25 | negative | 0.85 | −3.43 | 14/56 |
| 15min EMA9/21 stop | 2,333 | +2.17 | **−₹8.5L** | 0.88 | −2.47 | 18/56 |

**The arithmetic that settles it** (5min EMA9/21, 61 months):
gross **+₹8,13,867** — costs **₹21,49,351** = net **−₹13,35,484**. Costs are **2.6x the entire
gross edge.** Newey-West t on daily P&L is significantly NEGATIVE.

Cost check under both STT regimes (so the result is not an artifact of a harsh assumption):
futures round trip = **4.47 pts** at pre-Oct-2024 STT (0.0125%) and **5.97 pts** post-Oct-2024
(0.020%), +0.5pt slippage → **5.0–6.5 points**. Measured gross edge is **1.25–2.17 points**.
The edge is 2–4x too small **even in futures, where theta and VRP are zero.** Options are
strictly worse because they add both.

> **NOTE:** the futures CAGR/maxDD figures in `futures_report.json` print as `nan` / −468%
> because fixed 1-lot sizing on ₹3L capital drives equity below zero. Those two metrics are
> therefore UNDEFINED (the account is wiped), not "very negative" — reported here as net rupees,
> points/trade, PF and t instead. Flagged rather than quietly presented.

## The trap the Principal's brief walked into (the most useful finding here)
The ask was "consistent month-by-month positive returns." On the 5min EMA9/21 futures arm:
- **62.3% of months are positive on GROSS P&L**
- **24.6% of months are positive on NET P&L** (longest losing streak 14 months)

A backtest that under-modelled costs — or quoted gross — would have displayed almost exactly the
"consistently positive months" product that was requested. The requested output was achievable
only as an artifact. This is worth carrying forward as a standing check on any future
"consistent returns" mandate: **demand the gross-vs-net month table, not the headline curve.**

## Also confirmed: no amount of extra filtering fixes this
Confluence/filter stacking cannot help, because the deficiency is magnitude and symmetry, not
selectivity. Filters reduce n; they do not make a 0.005% move into a 0.30% move. (Being measured
formally in the concurrent `signal_budget/` run over Supertrend / vol-breakout / liquidity-sweep
/ S-R-confluence triggers.)

## Where this leaves the mandate
Directional intraday NIFTY option BUYING remains closed — now on three independent bodies of
evidence (2026-07-01 study, this intraday-EMA test, this futures diagnostic). The buyer pays
theta + VRP + spread + costs against a coin-flip signal with zero convexity.
The Principal's underlying intent (participate in trend, defined risk, compounding) is better
served on the vol-SELLING side, which is where this firm's repeatedly-validated edge sits —
see the concurrent covered-call design (`COVERED_CALL_NIFTY_20260729/`) and the option-buying
roadmap (`OPTION_BUYING_ROADMAP_20260729/`), which reframes the search toward the only niche
where a buyer can structurally win: conditions where realized vol systematically exceeds implied.

## Files
- `stage1_signal_test.py` / `stage1_report.json` / `stage1_log.txt` / `stage1_*_build.csv`
- `futures_arm.py` / `futures_report.json` / `futures_log.txt` / `futures_*_trades.csv`
