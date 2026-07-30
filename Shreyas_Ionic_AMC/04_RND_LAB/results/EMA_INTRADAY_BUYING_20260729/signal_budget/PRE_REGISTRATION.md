# Pre-registration — Signal Strength vs Cost Budget (Gate-3 measurement)
Owner: Arjun Rao (Head of Quant). Date: 2026-07-29. Status: written BEFORE running
`measure_signal_budget.py`. Any deviation discovered after seeing results will be logged
verbatim in SUMMARY.md, not silently absorbed.

## Why this test exists
EMA-cross intraday arm (stage1, this same folder) measured gross edge of +1.25 to +2.17
NIFTY points/trade against a futures round-trip cost of 5.0-6.5 pts, and a long-option
breakeven of ~0.30-0.50% (~60-100 pts). This test asks: is the EMA cross uniquely weak, or
is the ceiling on intraday NIFTY signed-move magnitude itself below the option breakeven
for ANY reasonable trigger family? Measurement only. No option pricing, no P&L engine.

## Data (verify before use)
- `intraday_options_strategy/datasets/raw/hf_index_options_1m/index/NIFTY.parquet`
- Confirmed by stage1 run: 463,826 1-min bars, 2021-05-24 09:15 .. 2026-06-03 15:30.
- Index `volume` column is 0/unusable (confirmed landmine) — no volume-based triggers here.
- Pre-open auction bars (09:00-09:07) dropped: filter time >= 09:15 (landmine #2).

## Windows
- BUILD: 2021-05-24 -> 2025-12-31. Select/rank/report headline verdicts on BUILD only.
- FORWARD (untouched-selection OOS): 2026-01-01 -> 2026-06-03. Reported separately,
  never used to pick a trigger or threshold.
- Entries restricted to 09:20-14:30 so every trade is flat by 15:25 (FLAT_BY).
- Entry fill = NEXT 1-min bar's OPEN after the signal bar CLOSES (no same-bar fill).
- Indicators (EMA/ATR/Supertrend/Bollinger/Keltner) computed PER DAY, reset each session.

## Triggers to measure (exact definitions — locked before running)
1. **Supertrend flip**, timeframes {5min, 15min}, params {(ATR10,mult3), (ATR7,mult2),
   (ATR14,mult3)}. Signal = trend flips from down->up (long) or up->down (short) that bar.
2. **Volatility breakout** (5-min bars):
   a. Keltner squeeze release: BB(20,2) inside Keltner(EMA20, 1.5*ATR10) = squeeze; signal
      fires the bar squeeze turns off, direction = sign(close - EMA20).
   b. ATR expansion: bar range (high-low) > 1.5x the PRIOR 14-bar average TR (excludes
      current bar to avoid circularity); direction = sign(close-open) on that bar.
   c. Opening-range breakout with vol filter: OR = 09:15-09:45 high/low; first breakout of
      OR high/low each day, gated on ATR(14) expanding vs its prior 14-bar level.
3. **Liquidity sweep** (15-min bars), levels = {prior-day H/L, current-day swing H/L
   established >=2 bars ago (PIT-safe proxy, no lookahead)}. For each level:
   - reclaim (reversal): bar sweeps beyond level (high>level or low<level) but CLOSES back
     inside -> signal opposite to sweep direction.
   - continue: bar sweeps beyond level AND closes beyond it -> signal same as sweep
     direction.
   -> 4 cells: {priorday,intraday} x {reclaim,continue}.
4. **Weekly/monthly S/R + round numbers** (15-min bars): prior COMPLETE week's H/L/C,
   prior COMPLETE month's H/L/C, nearest 100-pt round levels. For each level family:
   - breakout-through: close crosses the level between consecutive bars, direction = cross
     direction.
   - rejection-from: bar's high/low touches within 0.05% of level, close moves back away by
     >=0.05% -> direction = away-from-level.
   -> 6 cells: {week,month,round} x {breakout,reject}.
5. **Confluence stacking** (15-min bars): binary conditions C1=Supertrend(10,3) flip,
   C2=ATR expansion, C3=any sweep (reclaim or continue), C4=any S/R (breakout or reject).
   For every (bar,direction) pair, stack_count = number of C1-C4 agreeing on that direction
   at that bar. Bucket ALL such bar-direction events by stack_count in {1,2,3,4} and compute
   signed forward stats per bucket (dedup: a bar+dir counted once regardless of how many
   conditions fired, so no double-counting inflates any single bucket).

## Metrics computed identically for every cell (BUILD window)
- signed mean move at +15m/+30m/+60m/+120m and to 15:25, in % and in points (points computed
  directly as sgn*(exit-entry), not back-converted from %).
- signed MFE and MAE to 15:25, and MFE/|MAE| ratio.
- hit rate, Newey-West t-stat (lag 5), n.
- largest-single-day % of total signed edge (concentration).
- FORWARD (2026 H1) same metrics, reported not selected on.

## Pre-registered pass bars (locked)
- **G1 magnitude**: best-horizon signed mean >= 0.30% of spot (long-option breakeven bar).
- **G2 futures-cost bar**: best-horizon signed mean in points >= 6.0 pts (conservative
  post-Oct-2024 futures round-trip + slippage bar from stage1).
- **G3 significance**: Newey-West t >= 2.0 at the best horizon.
- **G4 concentration**: largest-day share <= 30%.
- A cell is PASS only if G1 AND G3 AND G4 all pass on BUILD (G2 reported alongside, not a
  gate — it is the cheaper/weaker bar; a cell can clear G2 without clearing G1).
- Anything below 0.30% is pre-declared arithmetically incapable of supporting long-option
  buying regardless of win rate or Sharpe dress-up.

## What would change my mind
If ANY cell clears G1+G3+G4 on BUILD, it becomes an overfitting SUSPECT (this is a wide
multi-trigger, multi-param search — dozens of cells, no multiple-testing correction applied
here since this is Gate-3, not certification) and MUST be forward-validated on the untouched
2026H1 window and red-teamed before any option-layer work proceeds. A pass here is not a
green light for capital; it is a green light for Gate-4.
