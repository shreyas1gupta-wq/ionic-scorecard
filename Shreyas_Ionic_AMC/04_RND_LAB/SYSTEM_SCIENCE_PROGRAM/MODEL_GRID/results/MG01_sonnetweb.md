**Backtest specification — monthly top-20 momentum, NIFTY500, 2015–2026, India daily data**

**1. Data requirements & point-in-time (PIT) rules**
- Daily OHLCV per symbol, corporate-action adjusted (splits/bonuses back-adjusted; dividends handled separately — do NOT let a dividend-adjusted "total return" close silently double as the execution price, since you can't transact at an adjusted price).
- A *survivorship-complete* price panel: every symbol that ever traded in the window, including delisted/merged/renamed names, carried to its last traded price and de-listing date. Never build this from a live vendor feed queried today.
- NIFTY500 constituent history as a **snapshot series** (the index provider publishes semi-annual reconstitution files) — not today's constituent list applied backward. Universe on rebalance date *t* = the officially published constituent list in effect on *t*, looked up via `asof(t)`, never a static current-day download.
- Trading/holiday calendar from the exchange (NSE), circuit-limit flags, and a "tradable" flag (halted / ASM-GSM stage / no trades that day) so execution logic can no-fill correctly.
- Corporate-action calendar (ex-dates) so the 6-month return signal isn't computed across an unadjusted split/bonus.

**2. Universe construction**
- At each month-end formation date *t*: take PIT NIFTY500 membership as of *t*. Apply a minimum-history filter (≥ 126 trading days of price history, else momentum is undefined) and a minimum-liquidity filter (e.g., 20-day median traded value above a floor) computed using data available *strictly before t* only. Exclude names under a trading ban / circuit-locked on the signal date.

**3. Signal timing & execution convention**
- Signal = trailing 6-month return, computed using **only** closes through the close of the last trading day of the month (formation date *t*). Rank descending, take top 20.
- Execution: enter next trading session's VWAP or open (state which — VWAP is more realistic for names outside the top-50 by ADV), never the formation-day close. This is the single most common lookahead bug in momentum backtests — flag it explicitly to the junior quant.
- Hold until next rebalance; trade only the *delta* between old and new target weights, not a full liquidate-and-rebuild (this changes the cost estimate by 2–5x if done wrong).

**4. Cost model**
- Per-side: brokerage + STT + exchange transaction charge + stamp duty + GST (all known, deterministic — build a lookup table, don't guess a flat bps) **plus** a market-impact term as a function of order size / ADV (e.g., a square-root impact model, calibrated conservatively — 10–20bps for the top 100 names, materially more for the bottom of a NIFTY500-derived universe). Cap position size as a % of 20-day ADV; if a target position would breach that cap, either partial-fill over multiple days or exclude the name and disclose it.

**5. Control experiments required before believing any result**
- **Placebo/random-basket test**: same universe, same rebalance dates, same turnover, same cost model, random stock selection. The strategy must clear a stated percentile (report the actual percentile, not just "beats average").
- **Lag-sensitivity test**: shift the signal by one extra day; if the edge collapses, you have a lookahead bug, not alpha.
- **Cost-stress test**: 2x and 3x the assumed cost model — does the Sharpe survive?
- **Parameter-stability check**: vary top-N (15/20/25) and formation window (3/6/9/12 months); demand a plateau, not an isolated peak.
- **Era/regime split**: pre-2020 vs 2020–2022 vs 2023–2026; no single sub-period should carry the whole result.
- **Static-vs-PIT-universe test**: rerun with today's NIFTY500 list frozen backward — if the result changes materially, you had survivorship bias.
- **Capacity check**: what AUM does this support before impact costs eat the edge?

**6. Explicit kill criteria (pre-committed, not discovered after the fact)**
- Net-of-2x-cost Sharpe < 0.5, or the placebo-percentile < 90th, or the result fails the one-day-lag test (edge doesn't degrade gracefully — it dies), or the result is driven by <3 sub-periods / a handful of extreme trades (check contribution concentration; if top-5 trades explain >40% of PnL, kill), or the static-universe rerun changes CAGR by more than ~30% relative.