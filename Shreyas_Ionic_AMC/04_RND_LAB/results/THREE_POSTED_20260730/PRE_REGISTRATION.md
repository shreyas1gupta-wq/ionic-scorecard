# PRE-REGISTRATION — Three Posted Strategies (Principal-sourced, externally posted)
Aditya Verma (R&D), 2026-07-30, written BEFORE any measurement. Do not edit after results land —
amendments go in a dated addendum at the bottom. Supersedes nothing; builds on
`SHARED_CONTEXT_20260729.md` (binding evaluation framework) and the sister document
`results/SPIKE_OVERSHOOT_SELL_20260730/` (same-day, same cost stack, same landmines).

## The three specs, exactly as given
1. **MEAN REVERSION**: fade z-score extremes at the OPEN, |z|>1, 20-day rolling window.
2. **TREND**: EWM crossover + momentum + ATR-normalised breakout strength.
3. **SEMI-DIRECTIONAL**: overnight gap breakout above prior high / below prior low, >0.2 ATR confirmation.
Each expressed as (a) delta-1 futures, (b) naked long option buying, 0.40-0.80 delta band, no
spreads/hedge, hard SL. Target: >100% CAGR at <25% maxDD (Principal's own bar for these three).

## Priors going in (stated so a later reviewer can check I didn't p-hack toward them)
#1 is genuinely untested here — most effort goes here. #2 has a poor prior (it is a 3-way
confluence of price-derived transforms — the exact family that was shown 2026-07-30 morning to
buy appearance not significance: n 18,697->35, t never clears 2). #3 is partly related to
`sweep_priorday_reclaim` (10.03 pts, t=3.10, the session's best trigger) but is gap-anchored and
demands continuation, and today's spike-overshoot work found spot CONTINUES (does not revert)
after a large move — mildly supportive of #3's premise but that continuation (+2.83 to +3.83 pts)
did NOT clear the ~5.5pt futures cost bar in that context. Going in, I expect #2 = DEAD, #1 and #3
= genuinely uncertain with #1 the better shot given it is the least correlated with anything
already tested today.

## Data
- **Signal generation (futures leg, full history)**: `intraday_options_strategy/datasets/processed/
  nifty_1min.parquet`, 1,047,541 bars, 2015-01-09..2026-05-14. Verified: index already starts at
  09:15:00 (min bar time in the file), i.e. the pre-open-auction bug does NOT apply to this
  specific file (checked: `pd.Series(df.index).dt.time.min() == 09:15:00`, no 09:00-09:07 prints
  present). Daily bars built as open=first bar's open, high=max(high), low=min(low),
  close=last bar's close, grouped by calendar date.
- **Option pricing (options leg)**: `intraday_options_strategy/buying/chain.py` (reused, not
  edited) over the weekly 1-min tree, 261 valid expiries 2021-05-27..2026-06-02. **Consequence:
  the options leg is only measurable 2021-05-24 onward — states this every time, never implies
  the full 2015-2026 history for options P&L.**
- BS pricing hand-vectorized (numpy+scipy.stats.norm), anchor-verified against the same case as
  the sister doc (S=K=100,T=.25,r=5%,sig=20% -> price 4.6150, delta 0.5695 — reproduced exactly).
  r=6.5% flat [ASSUMPTION, not fitted, not varied by era]. IV solved once per event from the
  ATM option's own observed price (brentq), then applied FLAT across strikes to compute each
  strike's delta [INFERENCE/SIMPLIFICATION: ignores skew across the 0.40-0.80 delta band — stated,
  not hidden].

## Indicators (single pre-registered config per strategy — NOT grid-searched, to keep cell count
small per the Principal's own instruction on #2, and applied identically to #1/#3 for consistency)
- ATR(14): simple rolling mean of True Range over 14 days, `shift(1)` causal (uses data through
  yesterday to size today's threshold/stop).
- z-score (#1): `z_t = (open_t - SMA20(close)_{t-20..t-1}) / STD20(close)_{t-20..t-1})`. Both SMA
  and STD use ONLY prior days' closes (`close.shift(1).rolling(20)`); `open_t` is today's real,
  tradeable open print — not lookahead, it is the decision AND fill price, exactly as the spec
  says ("fade... at the open").
- EWM crossover (#2): EMA(20) vs EMA(50) of daily close, evaluated as of yesterday
  (`.shift(1)`) to decide today's entry. Momentum: ROC(10), sign must agree with the crossover
  regime (also as of yesterday). Breakout: yesterday's close vs the 20-day high/low computed
  through yesterday (`high.rolling(20).max().shift(1)`), a lagged Donchian channel.
  - ATR-normalised variant: breakout must exceed the channel by >= 0.25 x ATR(14).
  - RAW variant: breakout must exceed the channel by >= 20 fixed points (deliberately the same
    order of magnitude the flagship's stale 60-pt trail once was, to make the point that a raw
    threshold's effective strictness drifts as NIFTY's range roughly triples 2015->2026).
  - Exit: ATR trailing stop, `trail = max(close since entry) - 3xATR(14 as of entry, held fixed
    for the trade's life)`; RAW comparator uses a fixed 60-pt trail. Exit fill = `min(open_day,
    trail_level)` for a long (worse-of, i.e. a gap-through-the-stop fills at the worse open, never
    at the more favourable trail level) — same "never resolve intra-bar ambiguity in your favour"
    convention the sister doc used to discredit its own +3.03pt trail result.
- Gap breakout (#3): `gap = open_t - high_{t-1}` (long) or `low_{t-1} - open_t` (short).
  - ATR-normalised: gap >= 0.2 x ATR(14 as of yesterday) [Principal's own number].
  - RAW: gap >= 20 fixed points.
  - Entry = today's open (the breakout IS the open print, tradeable in real time).
- RSI(14): Wilder's smoothing on daily close, `shift(1)` causal.
- Realised-vol percentile (IV-percentile PROXY for the full-history futures leg — true IV
  percentile only exists 2021-05+; stated, not conflated): 20-day annualised close-to-close RV,
  percentile-ranked against its own trailing 252-day distribution, `shift(1)` causal.

## Primary exit per strategy (ONE each, to control trial count; see Trials section)
- #1: **same-day close** (intraday mean-reversion — matches "fade... at the open" literally).
- #2: **ATR/raw trailing stop**, multi-day (that IS the strategy).
- #3: **same-day close** (gap-and-go continuation, consistent with today's continuation finding).
Futures leg additionally reports a cheap secondary (vectorized, near-zero extra cost): #1 and #3
also computed with a 2-day hold, for robustness context only — not a separate pre-registered cell
for tiering.

## Vehicles
(a) **Futures, delta-1**: full 2015-2026 signal history. Cost: round-trip 4.47 pts pre-2024-10-01
    / 5.97 pts after, + 0.5 slippage (era-correct, from entry date).
(b) **Naked long option, 0.40-0.80 delta band**: restricted to 2021-05-24 onward (data
    constraint, stated). Strike selection: scan strikes from spot-1000 to spot+500 (50-pt steps),
    compute BS delta per strike at the event's solved flat IV; pick |delta| in [0.40,0.80]
    closest to 0.60; CE for bullish/long signals, PE for bearish/short/fade-short signals.
    Expiry: `nearest_expiry(day, min_dte=1, max_dte=10)` — 0DTE explicitly excluded (naked option
    buying at 0DTE is a different, already-killed animal: intraday EMA option buying, MFE/MAE=1.00).
    Entry fill: first bar with volume>0 within 10 min of the open; else DROP (report drop rate).
    **Hard SL** [ASSUMPTION, stated, not tuned after seeing results]: exit if premium <= 60% of
    entry premium (40% stop), checked via the option's own 1-min LOW during the hold, adverse-
    first (SL checked before any favourable EOD mark on the same day).
    Exit (if SL not hit): EOD, last available volume>0 print of the day.
    Cost: flat 1.67 premium points round-trip per lot (Rs25/lot/side, this mandate's own number),
    lot=65 [this mandate's stated convention, distinct from the sister doc's lot=75 for the
    earlier spike-overshoot mandate — both stated explicitly to avoid silent inconsistency].
    **#2 options leg**: only built out in full if the FUTURES-level signal for #2 clears its own
    (much larger) 5.0-6.5pt futures cost bar convincingly. #2's signal needs multi-day holds with
    likely 1-4 weekly-option ROLLS (1-min chain only carries ~0-10 DTE), which is expensive to
    build correctly; per "kill fast," if the directional signal itself is dead on the CHEAPER
    vehicle (futures), the options version (theta + roll costs on TOP of the same dead direction)
    is not separately built — this shortcut is stated, not hidden, and reversed if the futures
    read surprises positive.

## Margin / CAGR method
Dynamic margin per the firm ruling: naked 10% of notional. For a clean answer to ">100% CAGR at
<25% maxDD" that does not require picking an arbitrary lot count: for a flat (non-compounded,
same-direction, no-forced-deleveraging) exposure, both CAGR and maxDD scale ~linearly with
lots/leverage, so **CAGR/|maxDD| (Calmar) computed in PURE POINTS is leverage-invariant** — the
target (>100%/<25%) is exactly Calmar >= 4.0. I compute points-Calmar as the primary gate (no
capital base needed, no lot-count arbitrariness) and ALSO report one illustrative Rs CAGR/maxDD
pair at a stated lot count for concreteness, per instruction. Caveat stated where relevant: real
margin calls/gap risk can break the linear-scaling assumption at extreme leverage — the
points-Calmar answers "is it achievable in principle," not "is it safe to run at that leverage."

## Kill / tier criteria (binding, per SHARED_CONTEXT — restated here for this mandate)
**HARD KILLS**: fails its own placebo (see below); any lookahead/same-bar-fill (the open-print
entries are NOT lookahead — see z-score/gap derivation above, all inputs before `open_t` use only
`shift(1)` data); >30% of net profit in one trade; maxDD>25% of margin-capital; fills counted on
zero/thin-volume bars.
**PLACEBO**: for each strategy/variant, reassign the SAME COUNT of trigger days (matching the
long/short split ratio) to RANDOM eligible days, 500 iterations, same P&L formula and cost model;
p = fraction of null iterations with mean net pts >= the real mean (one-sided, since we have a
directional prior from the spec itself).
**FREQUENCY GATE**: n<100 -> top-decile-exclusion (best 5/10/20% trades removed, must stay
net-positive); n>=100 -> cost-stress (net at 1x/1.5x/2x/3x modeled cost + breakeven multiple).
**SOFT (tier only, never kills)**: t-stat, Bonferroni (firm cumulative bar currently ~0.000107 at
m=466; this mandate's ~12-20 new cells raise the bar further for everyone after), DSR/PBO.
Tiers: `CERTIFIED` / `FORWARD-TEST CANDIDATE` / `UNDERPOWERED-UNRESOLVED` / `DEAD`.

## Splits (mandatory)
Pre-2019 / 2019-Sep2024 / Oct2024-2025 eras (Break 1 does not bind for futures; DOES bind if any
option-leg convention accidentally required weeklies pre-2019 — it does not, options leg starts
2021-05 anyway). **2026-01-01 onward held out, reported, never selected on.**

## Regime conditioning (Principal ask — report ALL buckets with n, not just the good ones)
On the FUTURES trades (largest n, full history): price vs 20DMA (above/below, `shift(1)`), price
vs 50DMA (same), RSI14 bands (<30/30-70/>70, `shift(1)`), RV-percentile tertiles (proxy for IV
percentile on the pre-2021-05 span; true IV percentile only where the option chain exists). A
cell counts as a real finding only if it (a) states a mechanism, (b) holds in BOTH pre- and
post-Oct-2024 halves, (c) has adequate n.

## Trials count added by this mandate
3 strategies x 2 threshold variants (raw/ATR) x 1 primary exit x 2 vehicles = 12 cells, plus each
futures cell reports 4 regime-bucket cuts (not separately tiered, informational) and a 2-day-hold
robustness check for #1/#3 futures (cheap, informational, not separately tiered) = **12
tiered cells + ~16 informational cuts**. Added to firm cumulative (466 before this mandate).

## Tail
Worst single trade (pts & Rs) per cell, full loss distribution, named dates checked against
2021-11-26 (Omicron), 2022-02-24 (Ukraine), 2024-06-04 (election) and any other >2.5-sigma day
inside the sample.
