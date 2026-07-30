# IDEA — Intraday EMA-momentum NIFTY 50 option BUYING (re-test of a killed family)

**Filed:** 2026-07-29 | **Desk:** DESK-100 | **Requested by:** Principal
**Status:** **KILLED 2026-07-29** — Stage-1 gate FAILED on all 3 cells; Stage-2 option layer
never built, per the pre-registered rule. Signed move 0.004-0.010% vs the 0.30% bar (30-75x too
small), hit rate 50.2-51.3% (coin flip), MFE/|MAE| 1.004-1.018 (zero convexity). Futures arm
(no theta, no VRP) also net-negative: costs 2.6x gross edge, NW t -2.4 to -4.6.
Full verdict + tables: `04_RND_LAB/results/EMA_INTRADAY_BUYING_20260729/SUMMARY.md`.
Originally filed as: Gate-3 cheap test, PRE-REGISTERED (written BEFORE any data was touched)

## Principal's ask
"Momentum trading strategy using EMA on NIFTY 50, option buying only (check futures also),
multiple steps/filters/indicators/price action — whichever gives best RAR, intraday only,
consistent month-by-month positive returns."

## Prior art — this family is already KILLED (disclosed to Principal before proceeding)
`intraday_options_strategy/buying/REPORT.md` (2026-07-01), ~14 structures, real 1-min data,
261 weekly expiries, build 2021-05→2025-12 / forward 2026-01→2026-06:
- Intraday directional buying (ORB/momentum/breakout): signed forward move +0.00%..+0.04% vs
  ~+0.30-0.50% option breakeven — signal 10-25x too weak. Triple-confirmed (endpoint returns,
  MFE/MAE ~1.00 = zero convexity, the one convex niche >2ATR is ~8 trades/yr and still sub-BE).
- Closest analogue to this ask: `emacross_ITM2` = DAILY EMA(10/20) + close>EMA50, 2-strike ITM
  weekly CE, hold <=4d. In-sample Sharpe 0.80 / PF 2.81 but **99.5% of profit from 4 of 22
  trades**; forward 2026 H1: **Sharpe -2.26, win rate 0%, PF 0.00, -1.9%**.
- Multi-filter MTF version (20DMA+200DMA+RSI+5min MTF) scored WORSE.
- Report's verdict: "~14 structures tested; every one net-negative. Question is exhaustively settled."
- Economic reason: NIFTY's real edge (VRP) is on the SELL side; buyers pay theta + costs + VRP.

**Principal was shown all of the above and elected to run an independent fresh test anyway.**
Recorded so this run is understood as a re-verification with strongly adverse priors, not a
fresh hypothesis. Any rosy result here must be treated as an overfitting suspect first.

## The one genuinely untested gap (what makes this NOT a pure repeat)
Every prior kill used either (a) DAILY-bar EMA signals held multi-day, or (b) intraday
ORB/breakout/RSI triggers. **An EMA crossover computed on INTRADAY bars (5-min / 15-min),
entered and squared off the same session, was never specifically tested.** That is the only
delta this test adds. It is a narrow gap, not a new economic mechanism.

## Hypothesis
H1: An intraday (5m/15m) EMA crossover on NIFTY 50 produces a signed forward index move
large enough to clear the long-option breakeven (~0.30-0.50% of spot over the hold) after
theta and realistic retail costs, within the same session.

## Stage 1 — cheap falsification (index-only, no option pricing; ~0 option compute)
Before simulating any option P&L, test whether the signal predicts ANY signed spot move.
If it does not, the option layer is arithmetically impossible and the idea dies here.
- Data: `hf_index_options_1m/index/NIFTY.parquet` (1-min NIFTY spot, naive IST via `chain.load_index()`).
- Landmine guards: bars filtered to >= 09:15 (pre-open auction bug, CLAUDE.md #2); tz handled
  by chain.py; entries restricted to 09:20-14:30 so every trade can be flat by 15:25.
- Grid (SMALL and fixed in advance, to keep the trials count honest): 3 cells only —
  5m EMA(9/21), 5m EMA(20/50), 15m EMA(9/21).
- Direction: bullish cross -> long-CE-equivalent (signed +1); bearish cross -> long-PE-equivalent (-1).
- Measure: signed forward spot return at +30m, +60m, +120m, and to 15:25; plus signed MFE/MAE.
- Placebo: 100 randomized-entry-time control runs matched to the signal's time-of-day mix.
- Split: build 2021-05→2025-12; forward 2026-01→2026-06 reported but NOT used to select anything.

### PRE-REGISTERED KILL CRITERIA (fixed now, before any run)
Stage 1 must clear ALL of:
1. **Magnitude:** best-horizon signed mean forward move >= **+0.30%** (conservative low end of
   the documented option-breakeven band). Below this, no option structure can be profitable.
2. **Significance:** Newey-West t >= **2.0** on the build set.
3. **Placebo:** signal's signed mean at >= **90th percentile** of the 100 randomized controls.
4. **Not one-trade-driven:** no single day contributes > **30%** of total signed edge.
Fail ANY -> **KILL, do not build the option layer.** Reported honestly to the Principal either way.

## Stage 2 — only if Stage 1 clears (not authorized unless it does)
Full option P&L on real 1-min weekly CE/PE fills, ATM, entry at signal bar's next-bar open,
mandatory flat 15:25, -35% stop / +100% target / opposite-cross exit. Costs = the SAME
`frictions.py` / `engine._costs` model as the prior study (brokerage Rs20/order, STT 0.0625%
sell-side, exch 0.0495%, GST 18%, stamp, SEBI, slippage 0.5%/leg) so results are directly
comparable and not flattered by a looser cost assumption.
Additional Stage-2 kill gates: sign must NOT invert on the untouched 2026 H1 forward set;
no single trade > 30% of total profit.

## Futures arm (Principal asked to "check futures also")
Same signal, traded as a delta-1 index-equivalent position (no theta, no VRP drag) with
intraday costs. Purpose: separate SIGNAL quality from INSTRUMENT drag. If futures also fail,
the signal itself is dead; if futures pass and options fail, the drag is the binding constraint.

## Honest note on the "consistent month-by-month positive returns" requirement
Flagged to the Principal at the outset: a trend/EMA system whipsaws in range-bound months and
will have losing months by construction. Tuning until zero red months appear IS overfitting
(D-035 epistemic conduct). Deliverable therefore reports true monthly win-rate whatever it is,
and optimizes for risk-adjusted return (Sharpe/Calmar), not for a zero-red-month curve.

## Outputs
`Shreyas_Ionic_AMC/04_RND_LAB/results/EMA_INTRADAY_BUYING_20260729/`
