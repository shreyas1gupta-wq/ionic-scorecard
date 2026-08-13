# TAIL_PUT_ROLL_20260802 -- FINDINGS
5%-OTM long put / 10%-OTM short put (bear put spread), ~6M tenor, NIFTY. Three exit/management
rules on the IDENTICAL structure: EXPIRY (passive hold), ROLLOVER_3M (close+refresh every ~91
days), SIGMA3 (monetize the first day cumulative spot move breaches -3 sigma of entry-date
trailing-50d vol, else fall back to expiry). Monthly-only expiry table used throughout (a
BUGFIX -- first pass used the all-expiries table and picked thin, just-listed far-dated weeklies,
which silently skipped ALL of Jan-Jun 2020 and a 2.5yr 2023-2025 stretch; fixed by using the
monthly-only cache + multi-candidate-expiry search + wider strike-offset search).

## Results (10-year span, 2016-2026)
| Variant | n cycles | span | total net pts | ann. cost of carry |
|---|---|---|---|---|
| EXPIRY (passive) | 21 | 10.49yr | -189.7 | **-18.1 pts/yr** |
| ROLLOVER_3M | 34 | 10.24yr | -1221.7 | **-119.3 pts/yr** |
| SIGMA3 (monetize) | 22 | 10.19yr | -635.7 | **-62.4 pts/yr** |

**Rolling more often is NOT better here -- it's the worst of the three.** Naive expectation might
be "refresh the hedge quarterly to keep it current"; instead ROLLOVER_3M bleeds ~6.6x more per
year than just holding to expiry. Roughly half the gap is mechanical (rollover incurs the 3.54pt
cost ~4x/year vs expiry's ~2x/year, ~+7pt/yr difference) -- the rest is a real gross-edge
difference: frequent forced closes rarely let the position ride into a late-cycle payoff, and
each close realizes the spread at a point in its life where the SHORT leg still carries meaningful
time value working against you.

## Crash-window behavior (the actual point of a tail hedge)
- **COVID**: the cycle entered 2019-12-27 (11500/11000 strikes) spans the crash.
  - EXPIRY held to 2020-06-25: net **+445.21** pts -- hit its theoretical MAX gain exactly (both
    legs deep enough ITM at exit that gross_pnl = distance - net_debit, the structural cap).
  - SIGMA3 fired 2020-03-09 (z=-3.78) at net **+326.21** -- LESS than holding to expiry, because
    the -3-sigma bar breached before the true bottom (Mar 23-24) and NIFTY continued falling for
    two more weeks after this exit; the SAME entry, held longer, saw a LOWER exit spot in June.
    **Honest, somewhat counter-intuitive finding: "monetize the spike" can fire too early relative
    to the actual extreme in a fast-accelerating crash**, giving up further downside the passive
    hold would have captured.
- **Two more real triggers in SIGMA3**: Oct-2024 (entry 2024-09-27, z=-3.04, exited 10 days later,
  +121.36 pts) and a Mar-2026 decline (entry 2025-12-31, z=-3.46, exited after 72 days, **+868.06
  pts** -- the largest single payoff in the whole study). Both are genuine, fast NIFTY drawdowns,
  not artifacts.
- 3-sigma triggered in **3 of 22 cycles (13.6%)** -- rare by design, and each time it fired it was
  a real, identifiable drawdown, not noise.

## Structural point (carries over from IRONFLY_LADDER)
This is a DEFINED-RISK spread: max gain is capped at (long_K - short_K) - net_debit, i.e. roughly
the 5-to-10%-OTM band in points. **A crash beyond the 10% strike pays no more than that cap** --
COVID's ~38% peak-to-trough would have been fully captured by a NAKED 5%-OTM put but is capped
here at the ~5pp band. The short leg cuts the average bleed (vs. a naked put, per
`BOND_COLLAR_NIFTY_20260717`'s ~-1.6%/yr baseline) but gives up exactly the tail-beyond-10% payoff
that is usually the whole point of holding a crash hedge. This is a real design tradeoff to have
explicit sign-off on, not an oversight.

## Addendum 2: -18.1 pts/yr is a mean-vs-median artifact, not a stable expected cost (Principal catch)
-18.1 pts/yr on an avg spot of ~15,276 is -0.12%/yr -- implausibly cheap for real insurance, and
rightly questioned. Decomposition (`checkpoints/trades_spread_expiry.csv`):
- **Excluding just the 3 winning cycles** (1999-12-27 entry into COVID +445, 2021-12-31 +527,
  2025-12-31 +999.76), the other **18 cycles average -206.2 pts/yr** -- 11x more expensive.
- **Median single cycle: -99.8 pts** (~0.65% of spot for 6 months), close to the **mean debit paid
  at entry (117.6 pts, 0.79% of spot)** -- this is the realistic sticker price when nothing
  dramatic happens.
- **Tested whether this is a start-date-selection artifact**: shifted the cycle-start offset by
  30/60/90/120/150 days. All six offsets land in a tight **-15 to -24 pts/yr** band, median always
  ~-100 to -110 -- NOT fragile to the exact entry date. This is because COVID, a 2021-22 pullback,
  and the 2025-26 decline are each wide enough in calendar time that almost any 6-month phasing
  catches a piece of one.
**Conclusion**: the cheap headline is real FOR THIS SPECIFIC 10-year window (which happened to
contain 3 well-timed corrections), not a stable forward-looking expected cost. Quote the
median/ex-winners view (~100-200 pts/yr) for forward planning, not the realized mean, unless there
is a specific reason to expect the next decade to also contain 2-3 similarly-timed corrections.

## Honest caveats
- Fill quality varies with market stress: `long_otm_pct`/`short_otm_pct` range ~1.7-8% and
  ~8-13% respectively vs the 5%/10% targets -- widest divergence right after vol spikes (e.g. the
  2020-04-24 entry, 1.7% actual vs 5% target) when everyone wants the same far-OTM strikes at
  once. Matches `MIDCAP_OTM_PUT_20260717`'s identical, disclosed limitation.
- n=21-34 cycles per variant -- illustrative for cost-of-carry and crash-behavior, not a
  statistically-poweredhypothesis test (this is a hedge-sizing question, not an alpha search).
- Cost model: 1.77pts/leg round trip x 2 legs, matching COST_STANDARDS/prior arms in this session.
- The SAME entry-date cohort underlies all three variants' first ~10-15 cycles (identical entry
  logic) then diverges purely on the exit rule -- a genuinely controlled comparison, not
  different-population noise.
- 3-sigma threshold is fixed at ENTRY-date trailing-50d vol (no lookahead: doesn't update mid-hold
  to react to the crash itself) -- a deliberate, disclosed design choice; a mid-hold-updating
  version would behave differently (likely fire later/closer to the true extreme, trading off
  against reacting slower).

## Addendum 3: dynamic NIFTY + hedge rebalancing, 2015-present (MODELED, not real prices)
100 NIFTY lots (LOT=75, fixed simplification) + 5%-of-portfolio cash buffer, from 2015. Every 6M,
hedge the CURRENT lot count with a 10%-OTM put (modeled BS pricing off trailing-50d RV). On
settlement: hedge P&L -> cash; rebalance to the 5% cash TARGET (excess cash buys lots, shortfall
sells lots) -- the "profit buys back lots, loss sells lots to cover" rule operationalized as a
target-cash-fraction rebalance. Two variants, 22 cycles each, 2015-2025:

| Variant | Final lots | Final total value | CAGR | Cycle-level MDD* |
|---|---|---|---|---|
| PASSIVE (hold to 6M expiry) | 92 | Rs19.07cr | 10.19% | -10.0% (entry 2021-12-20) |
| SIGMA3_MONTHEND (2mo cooldown) | 104 | Rs21.59cr | 11.51% | -8.9% (entry 2019-12-23) |
| *(comparison)* unhedged 100-lot buy-and-hold | -- | Rs19.54cr | -- | not computed here |

*MDD computed on cycle-boundary (~6-monthly) snapshots only -- UNDERSTATES true intra-cycle max
drawdown, which would need daily mark-to-market of the option leg to compute properly. Treat as a
lower bound on drawdown, not the real figure.

**SIGMA3_MONTHEND beat both PASSIVE and the unhedged comparison** in this specific realized path,
but the trigger only fired in **1 of 22 cycles** -- almost the entire performance gap between the
two variants traces to that single decision point (when to monetize) plus its knock-on effect on
subsequent lots-held. This is a genuinely low-power comparison (n=22, 1 differing event); do not
read it as "month-end monitoring with a cooldown structurally beats passive holding" without more
cycles/paths to confirm. PASSIVE cost ~2.4% of terminal value relative to not hedging at all over
this specific mostly-bull 11-year window -- consistent with Addendum 2's finding that this period's
realized hedge cost is on the cheap end of what should be expected going forward.

## Addendum 4: VRP-adjusted (more realistic) rerun + proper DAILY MDD -- both worse than first shown
Two corrections requested and applied:
1. **More realistic cost**: v5 priced the modeled put off pure trailing-50d realized vol, which
   this session's own `VOL_SURFACE_20260731` work established UNDERSTATES real IV (a real,
   established variance risk premium). Added a conservative **+3 vol-point** addon (smaller than
   that arm's ~+6pt FRONT-tenor VRP, since VRP is typically thinner at 6M) -- [ASSUMPTION,
   disclosed, not fitted]. Result: avg premium paid rises 66.5 -> **111.5 pts** (+68%), final value
   Rs19.07cr -> **Rs17.88cr**, CAGR 10.19% -> **9.56%**.
2. **Proper DAILY mark-to-market MDD** (Addendum 3's MDD used only ~6-monthly cycle-boundary
   snapshots and explicitly flagged this as an understatement). Computed daily:
   - **Hedged (VRP-adjusted, passive): -36.5% on 2020-03-23** (the actual COVID bottom day).
   - **Plain NIFTY, same starting capital, unhedged: -38.4%, same day.**
   The hedge's real drawdown cushion is **~1.9 percentage points** -- nowhere near the ~34%
   relative MDD reduction the cycle-boundary snapshots implied. A single 10%-OTM put per 100
   lots, wherever it happens to sit in its 6-month life when the crash actually hits, is a
   comparatively thin protection layer against a fast, deep, single-month crash -- consistent with
   this session's repeated finding that CAPPED/partial hedges give back most of their apparent
   benefit once measured properly. **This is the headline number for MDD claims, not Addendum 3's.**

## Addendum 5: 1Y backspread, roll-before-expiry -- historical and Monte Carlo DISAGREE
Principal's hypothesis (matching the vega finding in Addendum on card 2): does rolling the 1Y
backspread out 1/2/3 months before its own expiry -- avoiding the low-vega tail -- beat holding to
expiry? Tested both ways on the SAME structure (sell 1x5% OTM, buy 2x10% OTM).

**Historical (real 2016-2026 data, n=10/variant):**
| Variant | ann. pts/yr | mean/cycle | t-stat | genuine-roll fill rate |
|---|---|---|---|---|
| Hold to expiry | 39.0 | 40.9 | 1.27 | -- |
| Roll 3mo before | **114.1** | 116.8 | 3.18 | 10/10 |
| Roll 2mo before | 82.3 | 85.0 | 1.59 | 9/10 (1 fallback to expiry, net -11.3) |
| Roll 1mo before | **121.1** | 126.0 | 3.84 | 8/10 (2 fallbacks to expiry, net +229.5 avg) |
All three roll variants beat hold-to-expiry. Fallback-to-expiry cycles (when the target roll date
had no fillable market price) are disclosed above -- they don't dominate the result, but roll_1mo's
number is partly lifted by 2 lucky fallback cycles.

**Monte Carlo (60,000 paths/scenario, constant-sigma GBM, paired across exit rules per path):**
| Scenario | Hold to expiry (mean) | Roll 3mo | Roll 2mo | Roll 1mo |
|---|---|---|---|---|
| A: bull/low-vol | -98.2 | -103.7 | -102.1 | -100.3 |
| B: sluggish | **+80.4** | +67.9 | +72.4 | +77.4 |
| C: bear/high-vol | **+847.8** | +681.6 | +730.8 | +787.8 |
**Hold-to-expiry has the HIGHEST MEAN in all 3 scenarios** -- the opposite ranking from the
historical result. BUT look at the tail: in scenario C, hold-to-expiry's 5th-percentile outcome is
**-785.7** (a real loss is possible) vs roll_3mo_before's 5th percentile of **+65.3** (100% win
rate in this scenario) -- rolling earlier sacrifices some mean return for a dramatically tighter,
safer distribution.

**Why they disagree (most likely explanation, not confirmed further here)**: the Monte Carlo uses
ONE constant sigma per path (no vol-crush dynamic) -- real markets typically see IV spike then
mean-revert down after a crash, so a position still open post-spike loses value on the vega side
even if the underlying move was captured. That dynamic isn't in this simplified GBM model but IS
in the real 2016-2026 data, which is the more likely reason historical data rewards early exit
more than the constant-vol simulation does. The historical n=10/variant is also small enough that
some of its edge could be sample luck.
**Read together**: rolling out before expiry looks like a reasonable, lower-tail-risk choice on
both lenses, even though they disagree on whether it raises or slightly lowers the AVERAGE -- the
tail-risk reduction (scenario C's P5 flip from -786 to +65) is the more robust, model-independent
part of the finding.

## Recommendation
If the goal is genuinely cheap, reliable crash protection: **hold to expiry, don't roll on a fixed
calendar**, and consider whether capping via the 10%-OTM short leg is worth giving up tail-beyond
protection -- a naked 5%-OTM put (no short leg) costs more to carry but keeps the full crash
payoff, which is usually the reason to hold the hedge at all. If monetizing early is wanted for
capital-efficiency reasons, the 3-sigma trigger is a reasonable rule but should be understood to
sometimes exit before the true extreme in a fast crash -- not a strict improvement over patience,
just a different (and cheaper, since it triggered in only 3 of 22 cycles) trade-off.
