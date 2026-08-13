# PRE-REGISTRATION — SWING (multi-day) delta-1 NIFTY futures arm
Owner: Dhruv Kapoor (Technical). Written BEFORE any code ran. Per D-035: no tuning after
seeing results; this file is the contract the run is graded against.

## Universe / instrument
NIFTY delta-1 (index-equivalent futures), long AND short. Signal computed on DAILY bars
built from `intraday_options_strategy/datasets/raw/hf_index_options_1m/index/NIFTY.parquet`,
filtered `time>=09:15` (landmine #2, pre-open auction) before taking daily open/high/low/close.
Data span 2021-05-24..2026-06-03. Build = entry date <= 2025-12-31. Held-out = entry date
2026-01-01..2026-06-03, reported separately, selected on nothing.

## Signal families (4), computed strictly on data through day t's close; entry fills at
day t+1's OPEN (next session, never same-bar). All rolling windows use `.shift(1)`-safe
construction so day t's own bar never leaks into its own signal.

### A. Minervini trend template (index-level; ANALYST_CHECKLISTS.md §Minervini, adapted)
LONG (all must hold, transition-day trigger only i.e. day t true / day t-1 not-all-true):
1. close>SMA150 and close>SMA200
2. SMA150>SMA200
3. SMA200 rising: SMA200_t > SMA200_{t-22}
4. SMA50>SMA150>SMA200
5. close>SMA50
6. close >= 1.30 * min(close, trailing 252 sessions)   [>=30% above 52w low]
7. close <= 0.75... close within 25% of 52w high: close >= 0.75 * max(close, trailing 252)
**DROPPED for this index-level test, documented deviation, not silently skipped:**
- Criterion 8 (RS percentile >=70 vs NIFTY500 universe): no cross-sectional universe exists
  for a single index signal. [INFERENCE: cannot be computed here.]
- Criterion 9 (VCP volume signature): index `volume` column is 0/unusable per data notes.
  [DATA: column unusable, not a judgment call.]
SHORT = mechanical mirror (stage-4 decline): close<SMA150<SMA... reversed, SMA200 falling
>=22 sessions, close<=0.70*max(252) [>=30% below 52w high], close<=1.25*min(252) [within
25% of 52w low].
Exit "signal_reversal" for this family = any one of the long (short) criteria breaks.

### B. EMA20/50 regime + pullback
Regime: uptrend = EMA20>EMA50 and EMA50_t>EMA50_{t-5}; downtrend = mirror.
LONG trigger: uptrend AND close_{t-1}<=EMA20_{t-1} AND close_t>EMA20_t (pullback-to-rising-
20EMA, reclaim on day t). SHORT = mirror in downtrend.
Exit "signal_reversal" = regime flips (EMA20 crosses EMA50 the other way).

### C. 20-day / 50-day breakout (Donchian, PRIOR N sessions, excludes today)
rolling_high_L = high.rolling(L).max().shift(1); rolling_low_L = low.rolling(L).min().shift(1).
LONG (L in {20,50}): close_t>rolling_high_L_t AND close_{t-1}<=rolling_high_L_{t-1} (fresh
breakout only). SHORT mirror on rolling_low_L. 2 lookbacks x 2 directions = 4 sub-signals.
Exit "signal_reversal" = close falls back below (above) the breakout level.

### D. Daily analogue of sweep_priorday_reclaim -> PRIOR WEEK's swing high/low
Per ISO calendar week: week_high=max(high), week_low=min(low) over that week's sessions;
broadcast to the FOLLOWING week, shift(1) so only a fully-completed prior week is used.
LONG: low_t < prior_week_low AND close_t > prior_week_low (sweep then reclaim).
SHORT mirror on prior_week_high.
Exit "signal_reversal" = the opposite sweep-reclaim trigger fires.

## Exit grid (5 per signal x direction) — kept small, pre-registered
1. signal_reversal (family-specific rule above)
2. atr_trail: trailing stop at 3xATR14 off the highest(lowest) CLOSE since entry; this
   trailing level is ALSO the hard risk stop used for position sizing (see below).
3. fixed_5 / 4. fixed_10 / 5. fixed_20: exit at the OPEN of session (entry_index + N),
   i.e. exactly N full sessions held, regardless of signal/stop (see caveat below on the
   catastrophic floor).
For exit-configs 1/3/4/5, a FIXED (non-trailing) catastrophic stop = entry -+ 3xATR14 at
entry is ALSO active (charter: "the stop is decided before the entry") — if touched
intraday (checked against the day's high/low) it exits regardless of the primary exit
rule being tested. This is standard risk discipline layered under every config, not a
6th exit type.

## TRIALS COUNT (exact, pre-registered)
4 families -> A:2 dir, B:2 dir, C:4 sub-signals, D:2 dir = 10 signal-streams.
10 streams x 5 exit configs = **50 trials total.** No other cells will be run; if a 51st
cell appears in the output it must be explained, not silently added.

## Sizing (fixes the earlier negative-equity bug)
BOOK_EQUITY0 = Rs1,00,00,000 (RISK_LIMITS D-026 paper-book convention). LOT=75 (current
NIFTY lot, held constant through history as a stated simplification — same convention as
today's earlier futures_arm.py; true historical lot size varied, not re-derived here).
- risk_rupees = 1% of CURRENT equity (fixed-fractional, RISK_LIMITS "max risk/position 1%").
- stop_distance_pts = 3xATR14 at entry (same number as the catastrophic stop above).
- lots_risk = floor(risk_rupees / (stop_distance_pts * LOT))
- margin_rupees_per_lot = 0.15 * entry_price * LOT (15% of notional, task instruction).
- lots_margin = floor(0.5 * equity / margin_rupees_per_lot)  [single-position cap at 50%
  of equity in margin, leaving >=50% free — conservative single-name concentration cap]
- lots = min(lots_risk, lots_margin); lots=0 -> NO FILL, trade dropped (D-031: never
  assume a fill you can't size).
- Equity compounds trade-by-trade: equity += net_pnl_rupees. A single trade's realized
  loss is HAIRCUT-CAPPED at 3% of equity-at-entry (protects against an overnight gap-
  through on the stop; flagged in output if it ever binds) so equity can mathematically
  never go negative.

## Costs (Principal-supplied, SHARED_CONTEXT authoritative, era-correct)
Round-trip cost per lot, in index points: **4.47+0.5=4.97 pts if entry date < 2024-10-01**
(STT 0.0125%), **5.97+0.5=6.47 pts if entry date >= 2024-10-01** (STT 0.020%, post-hike).
Applied as cost_rupees = cost_pts * LOT * lots. NOT one flat rate across all years.

## Benchmarks
- S1-F: 12.57% CAGR / -4.44% maxDD / Calmar 2.83 / Sharpe 2.15 / PF 2.21 / n=204 / win 74%.
- Buy-and-hold NIFTY: same build/held-out windows, no leverage, no cost (one-time entry
  cost is immaterial to a multi-year hold and is excluded by convention).

## Kill / keep criteria (pre-registered, graded on BUILD only; held-out reported not selected)
- KILL a stream if NET Calmar <= 0 OR NW-t(daily net pnl) < 1.0 on build.
- FLAG (not kill) if net beats S1-F Calmar (2.83) or genuinely diversifies it — route to IC.
- FLAG concentration if max single trade > 30% of total net profit (FRAGILE tag, per gate).
- A stream that is GROSS positive but NET negative is the "trap" pattern from today's
  intraday run — always report gross-vs-net monthly table for every surviving stream.
