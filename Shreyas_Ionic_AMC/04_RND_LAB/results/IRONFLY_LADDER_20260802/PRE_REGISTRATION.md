# PRE-REGISTRATION — IRONFLY_LADDER_20260802
Written BEFORE any cell is run. NIFTY 50 index options only.

## Question
Does financing a long ATM straddle with a tight OTM short strangle (a defined-risk long iron
butterfly), laddered on a weekly roll, rescue option buying where the naked/unconditional version
was already killed (`OPTBUY_CONVEXITY_20260731`)? Does an entry-timing vol filter (IV vs 50d
realized vol, IV vs GARCH(1,1) forecast, IV percentile) help, where three different vol-cheapness
gates already failed on the naked straddle?

## Prior art (stapled per /prior-art convention — full detail: commits `64a100d`/`4dc8c9a`, 2026-07-31)
- `OPTBUY_CONVEXITY_20260731`: naked DTE-ladder (15/30/45/60/90d) ATM straddle, hold to expiry,
  killed at every DTE — fair-priced, t between -0.75 and +0.03, win rates track the ~42-46%
  fair-pricing null. DTE15 (closest to this idea's ~13d): n=221, win 43.4%, held-out 2026 -51.9 pts.
- All 3 tested vol-cheapness gates (VIX<=25pct, VIX>=75pct, RV20<=25pct — all at DTE60) FAILED
  placebo (p=0.75/0.48/0.45) and RV20 disagreed in SIGN with the VIX-level gate at similar n.
  Quoted verdict: "clean, non-ambiguous DEAD, not underpowered-unresolved."
- Mechanism: gamma/theta on ATM straddles 1.15 (pre-2019) -> 1.03 (2019-Sep2024) -> 0.83
  (Oct2024+) -> 0.90 (held-out 2026H1). Structural regime shift dated to the Oct-2024 SEBI break,
  monotonic in 4/5 DTE buckets. Tagged UNDERPOWERED-UNRESOLVED (thin post-break n=9-19) — direction
  solid, magnitude not.
- Partial-hold (50% of DTE) at DTE45 lost the same -10.8 pts as full hold — theta/gamma decay
  together, no front-loaded-gamma rescue from exiting early. Directly relevant since this ladder
  exits well before full expiry (~6/13 days).
- `OPTBUY_VOLEXPANSION_20260731`: even a VALIDATED forward-vol ML head (AUC 0.874 held-out) gating
  long gamma was statistically indistinguishable from random (Welch p=0.46).
- Prior work `SHARED_CONTEXT_20260729` killed 0-7 DTE buying at every gate tried.
- `OPTSELL_EXT_20260731`: 2x1/3x2 ratio spreads "REJECTED outright" on the selling side —
  independently supports this idea's 1:1 leg ratio (Principal-confirmed, not a 2:3 ratio).
- **Honest trial-count context**: the option-buying+selling family already stands at ~1,872 nominal
  cells / ~40-55 effective independent trials (`VALIDATION_DEBTS_20260731`). This grid's 32 cells
  are ADDITIONAL trials on top of that family, not a fresh independent search — any DSR/PBO or
  Bonferroni read here must be judged against the wider family, not just this grid in isolation.

## What is genuinely new here (not covered by the above)
1. The short OTM strangle financing leg — a defined-risk long iron butterfly, not a naked straddle.
2. The ~7-calendar-day weekly ladder roll (vs OPTBUY_CONVEXITY's hold-to-full-expiry or one 50%
   partial-hold test).
3. Two roll-mechanics variants: LAYER (overlapping rungs) vs REPLACE (single rung, forced early
   close) — neither tried before.
4. A GARCH(1,1) vol-timing filter and an IV-percentile filter (neither tried; VIX-level and
   RV20-percentile were).
5. Actual solved ATM straddle IV (vollib Black-Scholes/Jackel) as the "implied vol" side of the
   gate, rather than the VIX index level used previously.

## [INFERENCE] Pre-registered expectation (stated before running, per epistemic conduct)
The short strangle caps the payoff at the wing distance `d` (see payoff below) — the one thing
(a genuinely large move) that could otherwise offset the now-documented theta headwind gets capped
away. Expectation: this structure performs comparably to, or worse than, the already-killed naked
straddle — not better. This is a stated prior, not a result; the grid runs regardless and reports
honestly either way.

## Structure under test (defined-risk long iron butterfly)
At each scheduled roll date:
- BUY 1 ATM CE + 1 ATM PE, nearest common strike to spot (search offsets 0,+-50,+-100,+-150,+-200,
  first strike where both legs have CONTRACTS>0 same day — matches OPTBUY_CONVEXITY convention),
  expiry = nearest expiry to 13 calendar days out.
- SELL 1 CE @ ATM+d, 1 PE @ ATM-d, same expiry. d in {100,150,200,300} NIFTY points — exactly
  2/3/4/6 standard 50pt strikes away, so strike selection has no rounding ambiguity.
- **Payoff at expiry** (verified algebraically before coding): max LOSS = net debit paid, occurs
  at S = ATM strike. Max GAIN = d - net_debit, occurs at S <= ATM-d or S >= ATM+d (capped beyond
  the wings). `guards.assert_physical_bounds` enforces no trade's gain exceeds `d - net_debit`
  points — a data/logic-bug detector, not a market outcome.
- **Roll schedule**: a fresh rung is scheduled every ~7 calendar days (i.e. when the newest open
  rung reaches ~6 trading days to its own expiry). At each scheduled date, apply the entry filter
  (below); if it fails, SKIP that rung entirely (no position) and try again at the next ~7-day
  mark — no daily retry.
- **ROLL-MODE A "layer"**: the OLD rung (if any) stays open, exits at ITS OWN expiry via
  cash-settle-at-INTRINSIC from real spot close (never expiry-day SETTLE_PR — landmine #9).
  Steady state: ~2 rungs concurrently open.
- **ROLL-MODE B "replace"**: the OLD rung (if any) is force-closed the SAME DAY the new rung is
  added, marked at all 4 legs' option CLOSE (CONTRACTS>0 gated, fallback forward <=3 trading days
  else drop and log) — not intrinsic, since it is not that rung's own expiry. Only 1 rung ever open.
- No stops/trails/targets anywhere (pure calendar-scheduled entry/exit) — pathsafe's path-dependent
  machinery does not apply; every P&L is an exact close-to-close/intrinsic difference.

## Entry timing filter (applied at each scheduled roll date, gating the new rung only)
1. **UNCONDITIONAL** — always enter (baseline).
2. **IV_LT_RV50** — enter only if ATM straddle implied vol (annualized; solved via
   `vollib.black_scholes.implied_volatility`, Jackel method, from CE+PE close, spot, time-to-expiry,
   fixed r=6.5% [ASSUMPTION — IV solve is low-sensitivity to r at 13 DTE; disclosed, not fitted])
   < trailing 50-TRADING-day realized vol (close-to-close log-return std, annualized x sqrt(252),
   computed strictly BEFORE the entry date).
3. **IV_LT_GARCH** — enter only if ATM IV < GARCH(1,1)-forecast vol over the option's actual DTE
   horizon (expanding-window fit on daily log returns strictly BEFORE the entry date, refit at
   every entry decision via the `arch` package, annualized).
4. **IV_PCT_LOW** — enter only if ATM IV's own trailing/expanding percentile (min 252d history, cap
   504d window — matching the existing `spot_vix_daily.parquet` convention) is <=25th percentile.
   The "better way" candidate: same shape as the already-killed VIX-percentile gate, but on the
   actual solved option IV rather than the VIX index level.
All filters use ONLY data strictly prior to the entry date — no full-sample or lookahead percentile
or GARCH fit.

## Grid (pre-registered, 32 cells, ALL logged in cells.csv regardless of outcome)
4 OTM distances x 2 roll-modes x 4 filters = 32 cells.
Free-parameter count for Bonferroni/justification: **3 swept dimensions** (OTM distance, roll-mode,
filter) — DTE target (13d) and roll-trigger (~6TD) are FIXED by the Principal's original spec, not
tuned, so they do not count against the free-parameter budget.

## Method (non-negotiable, matches firm convention)
- Entry price = option daily CLOSE, CONTRACTS>0 gated (fallback forward <=3 trading days, else
  drop and log).
- Costs: 1.77 premium points round-trip PER LEG (COST_STANDARDS-derived; matches
  OPTBUY_CONVEXITY_20260731 exactly for direct comparability) x 4 legs = 7.08 pts per full round
  trip per rung, charged once per rung regardless of exit mechanism.
- Capital per rung = net debit paid (defined-risk structure, no separate margin — matches the
  existing "long option capital = premium paid" convention). If a cell ever nets to a credit,
  capital = max theoretical loss = d - net_credit instead; will be flagged explicitly if it occurs.
- Portfolio P&L series construction: each rung's net_pnl is attributed to its EXIT date (matches
  `debt1_dsr_pbo.py`'s date-grouping convention); daily portfolio P&L = sum of net_pnl for rungs
  exiting that day. MaxDD computed on the cumulative realized-P&L curve ordered by exit date — this
  is a realized-P&L curve, not a true intraperiod mark-to-market of open legs (consistent with how
  every prior arm in this codebase reports DTE-cycle P&L, not daily unrealized greeks).
- Split: pre-2019 / 2019-2024-09 / 2024-10+ reported separately. **2026 H1 HELD OUT** — reported,
  never selected on.
- Placebo for every gated cell: same-count RANDOM roll-date selection (matched on OTM-distance and
  roll-mode, not on the filter), repeated 500x, reporting percentile rank of the observed mean vs
  the null — matches `OPTBUY_CONVEXITY_20260731`'s exact placebo convention.

## Kill criteria (pre-committed, will not be softened after seeing results)
- **HARD KILL**: fails its own placebo; profit concentration >30% in one trade; maxDD >25% of
  average deployed capital (net debit); any lookahead (full-sample percentile/GARCH-fit, same-bar
  fill, expiry-day settle read as option price, replace-mode early-exit read as intrinsic);
  `guards.assert_physical_bounds` violation (signals a data/logic bug, not a market result).
- **SOFT** (sets tier, never kills): t-stat, Bonferroni/DSR/PBO, small-n. A low-t positive with a
  stateable mechanism is UNDERPOWERED-UNRESOLVED, not DEAD, per the Principal's standing ruling.
- **DSR/PBO bar**: computed against the HONEST wider family (this grid's 32 cells ADDED to the
  ~1,872 nominal / ~40-55 effective cells already run for option buying+selling this week) — not
  just this grid's own 32-cell count in isolation.

## Deliverable
`cells.csv` (all 32 cells), per-rung trades checkpointed to `checkpoints/`, `FINDINGS.md`
(mechanism, decomposition, verdict), lookahead audit report, DSR/PBO report.
