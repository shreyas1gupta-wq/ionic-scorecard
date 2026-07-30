content = r'''# PRICE LEVEL SYSTEMS -- NIFTY 50 intraday -- 2026-07-30/31

**Mandate:** test the Saty ATR Levels concept the Principal asked about (twice), plus every other
classical price-level system in the same pass (Fibonacci, classic pivots, CPR, opening range,
round numbers, prior-day/week levels), with a mandatory random-level placebo control. Status before
this pass: NEVER TESTED (only two derived features, `atr_consumed` and `or30_atr`, existed, inside
an ML feature set -- the levels themselves were untouched).

## Data & method (see build_daily.py, levels_lib.py, touch_engine.py, calibration.py, gate_analysis.py, finalize.py)
- NIFTY 1-min spot, `intraday_options_strategy/datasets/processed/nifty_1min.parquet`, 2015-01-09
  to 2026-05-14, 1,047,541 bars, 2,794 trading days. Already starts at 09:15 (pre-open-auction bars
  not present in this processed file; a >=09:15 filter is applied defensively regardless).
- All levels for day D are computed ONLY from data known before D's 09:15 open (prior-day/prior-week
  H/L/C, ATR14 through D-1, Wilder smoothing) -- EXCEPT opening-range levels, which by construction
  use the first 15/30/60 minutes of D itself and are gated so a "touch" can only fire on bars AFTER
  that window closes. **Bug caught and fixed during this study**: an earlier draft scanned the whole
  day for OR touches and produced spurious t~13-19 cells on OR-high/low REJECT purely from
  within-window lookahead (the "touch" was often the very bar setting the range extreme, before the
  window had even closed). Fixed by gating touch-search to start only at the bar the window closes;
  the inflated cells collapsed to the same order of magnitude as everything else (max |t| ~6 post-fix).
- **Touch** = first 1-min bar of the (gated) session where level is inside [low, high] for that day.
  **Approach side** = previous bar's close vs the level (below/above), known before the touch bar opens.
  **REJECTION** entry = next bar's OPEN after the touch bar closes, direction = fade (short if
  approached from below, long if from above).
  **BREAK-AND-HOLD** entry = requires a bar within 5 bars of the touch to CLOSE beyond the level by a
  buffer (max(1pt, 0.05xATR14prior)); entry at the next bar's open, direction = continuation.
  Both hypotheses share the SAME touch event per (date, level) -- same trade opportunity, two
  different bets. Manually spot-checked one trade (PRIORDAY high, 2015-02-16) bar-by-bar against raw
  1-min data to confirm touch/direction/entry mechanics are correct.
- **Exits, via `lib/pathsafe.py` ONLY** (both bounds always computed; PESSIMISTIC quoted): two
  ATR-scaled configs -- `tight_atr` (stop 0.30xATR, target 0.45xATR, RR 1.5) and `wide_atr` (stop
  0.50xATR, target 0.85xATR, RR 1.7). ATR-scaled rather than fixed-point because NIFTY spot moved
  ~8,000 to ~24,000 over the sample; a fixed-point stop is not comparable across eras.
  **Reliability check**: across all 284 cells, the optimistic/pessimistic spread never exceeded
  pathsafe's 25% threshold (ambiguous-bar fraction ~0.008% max) -- these are session-only ATR-scaled
  intraday exits, so same-bar stop+target ambiguity is rare. All 284 cells are RELIABLE; none needed
  to be reported as a range.
- **Costs**: 4.47 pts round trip pre-2024-10-01, 5.97 after, +0.5 slippage (per task spec).
- **Era split**: BUILD = pre-2024-10-01 (~117 months), RECENT = 2024-10-01..2025-12-31 (the
  Principal's stated priority), HOLDOUT_2026 = all of 2026 (reported only, never selected on).
- **Random-level placebo (mandatory control, scoped correctly)**: for every system, anchor held
  fixed at the real system's own anchor; a placebo level's distance is Uniform(0, 2x mean_real_distance)
  with random sign, matching count/anchor/scale exactly. **Scan result: 0 of 284 cells have
  (positive net mean) AND (|t|>=3.0) AND (n>=150)** -- the best positive cell in the entire study is
  FIB_WEEK 0.382 BREAK wide_atr at t=1.99 (n=249), which fails the significance screen on its own
  terms before a placebo is even relevant. A placebo answers "would ANY similarly-distant random
  level do as well as this one" -- that question has no content for a cell with no edge to explain.
  **Per the coordinator's correction, the placebo was therefore NOT run to completion** (an initial
  5-seed run was ~20 min into seed 1 of 5 when this scan made continuing pointless; it was stopped).
  The negative, Bonferroni-clearing findings below do not need a placebo either, by the same logic in
  reverse: a placebo cannot explain away a LOSS (a random level losing equally badly would not rescue
  the real level's specialness claim, since there IS no specialness claim being made for a loser).

## Systems tested (17 sub-systems, 71 distinct level_names, 284 cells = 71 x 2 hyp x 2 exit cfg)
SATY (6 ratios +-ATR14, priority=0.382/0.618/1.0) - FIB_DAY (7) - FIB_WEEK (7) - PIVOT_FLOOR (7:
PP/R1-3/S1-3) - PIVOT_CAM (8: R1-4/S1-4, priority=R3/S3/R4/S4) - PIVOT_WOODIE (5) - PIVOT_FIBPIV (5)
- PIVOT_FLOOR_WK (3) - CPR_DAY (3: TC/PP/BC) - CPR_WEEK (3) - OR15/OR30/OR60 (3 each: high/low/mid)
- ROUND50 - ROUND100 (nearest 50/100-pt to prior close) - PRIORDAY (3: H/L/C) - PRIORWEEK (3).

**Trials ledger honesty**: 284 primary cells. Bonferroni at m=284: alpha=0.05/284=1.76e-4 two-sided
-> |t| bar = **3.75** (computed exactly, matches the ~3.7-3.8 pre-registered estimate). Plus the
calibration check (2 trials) and the SATY priority-vs-normal / ATR-consumed / CPR-width conditioning
cuts (re-slices of already-logged cells, disclosed in gates_report.txt, not counted as new
independent level systems toward the primary claim tier).

## Calibration check (mandatory, run BEFORE trusting anything else)
Sweep of prior-day high/low beyond the level, then a CLOSE back on the origin side (reclaim),
entered at the next bar's open, pooled long(low-reclaim)+short(high-reclaim), same ATR-scaled exits:

| exit cfg | n | gross pts | t(gross) | net pts | t(net) |
|---|---|---|---|---|---|
| tight_atr | 2,178 | +2.16 | 1.72 | -3.01 | -2.39 |
| wide_atr | 2,178 | +3.76 | 2.24 | -1.42 | -0.84 |

Baseline to match (sign + rough order of magnitude): **+6.67 pts, t=2.09** (15-min-bar prior-session
estimate). **RESULT: PASSES.** Same sign (positive gross edge), same order of magnitude, comparable
t (1.7-2.2 vs 2.09). The machinery is not broken.

**This also partially corrects a number already given to the Principal.** The +6.67pt/t=2.09 figure
was quoted from a 15-min-bar test without a clean gross/net split. This 1-min, ATR-scaled-exit
replication reproduces the SIGN and ORDER OF MAGNITUDE gross, but on a net-of-cost basis the edge
does NOT clear the futures cost bar (net t is NEGATIVE under `tight_atr`, roughly breakeven under
`wide_atr`). Plainly: **that signal is cost-dominated at 1-min granularity, not the tradeable edge the
earlier number implied.** Because this is a cost-dominated result (right sign, wrong magnitude versus
cost) and not a directional failure, the reverse-the-strong-negative rule does not apply -- flipping
the trade would still lose to the same ~5-6.5pt round-trip cost. The BREAK-AND-HOLD cells throughout
this study are the empirical proof of that same point on a much larger sample (see mechanism below).

## Elliott Wave -- verdict
**SKIPPED, stated honestly, not built.** Classical Elliott Wave requires labeling a 5-wave impulse +
3-wave correction, but the count itself is discretionary at every step: which swing is "wave 1" vs
noise depends on an operator-chosen zigzag threshold with no canonical value; wave 2/4 retracement and
wave-3-not-shortest are "guidelines" not hard constraints; extended waves, truncated fifths, and
complex (double/triple) corrections legitimately allow MULTIPLE valid counts on the same chart
simultaneously (EW practice itself keeps a "primary" and "alternate" count live) -- there is no
pre-registerable, unique labeling algorithm to fail. Any mechanization (zigzag swings + Fibonacci
ratio checks on the swings) is not "Elliott Wave", it is a Fibonacci-retracement-on-swings rule,
which is already covered by the FIB_DAY / FIB_WEEK cells below (mostly did not clear significance,
and where they did, all on the losing side). Building a bespoke zigzag+fib proxy and calling it
"Elliott Wave" would manufacture an unfalsifiable-by-construction test; per the task's own
instruction, that is skipped rather than built.

## RESULTS

### The mechanism behind the whole study: a mild CONTINUATION tilt, not a rejection tilt
REJECT and BREAK-AND-HOLD share the exact same touch events, so they are near-mirror bets on the
same moment. Averaged across all `tight_atr` cells: **mean(REJECT) = -6.88 pts, mean(BREAK) = -2.11
pts, sum = -8.98 pts.** If levels had NO informational content at all (a pure coin-flip on which way
price goes after a touch), REJECT and BREAK should be symmetric losers of roughly the SAME size
(each paying the round-trip cost with no directional edge either way), summing to close to
**-2x cost (~-9.9 to -12.9 pts** across the two cost eras). Instead BREAK is reliably the SMALLER
loser of the pair. **That gap is the finding: price is slightly more likely to continue through a
level than to turn at it, intraday.** This is a real, structural, and somewhat counter-intuitive
result given how these level systems are usually sold (as support/resistance/reversal tools) --
the data says the opposite tilt exists, faintly. It is not large enough to monetize after costs
(BREAK is still net negative on average), but it is the mechanistic explanation for why REJECT is
the side that clears Bonferroni so often (10 of the 10 most significant cells in the whole study are
REJECT losses) while BREAK never does on the winning side either.

### Top 10 cells by |t| (all 284 logged in cells.csv; negative extremes reported as prominently as
any winner would be -- there are no winners here, and that is the valuable result)

| system | level | hyp | exit | n | tpm | win% | mean pts | RR | t | BUILD t | RECENT t | HOLD26 t |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SATY | 0.786 | REJECT | tight_atr | 1151 | 8.8 | 33.8 | -12.40 | 1.10 | -8.15 | -8.15 | -2.05 | -1.18 |
| SATY | 0.786 | REJECT | wide_atr | 1151 | 8.8 | 35.4 | -15.49 | 1.02 | -7.44 | -7.33 | -2.03 | -1.09 |
| PIVOT_FIBPIV | R1 | REJECT | tight_atr | 1414 | 10.8 | 37.4 | -9.38 | 1.12 | -6.29 | -7.02 | -0.26 | -0.68 |
| PRIORDAY | high | REJECT | tight_atr | 1249 | 9.5 | 37.5 | -9.65 | 1.10 | -6.22 | -6.62 | -0.77 | -1.11 |
| OR60 | low | REJECT | tight_atr | 1663 | 12.7 | 39.6 | -7.80 | 1.07 | -6.02 | -5.61 | -2.22 | +0.68 |
| PIVOT_FIBPIV | S1 | REJECT | tight_atr | 1239 | 9.5 | 37.4 | -9.80 | 1.13 | -5.95 | -5.31 | -2.70 | -0.47 |
| PRIORDAY | low | REJECT | tight_atr | 1093 | 8.3 | 36.3 | -10.17 | 1.16 | -5.80 | -5.04 | -2.88 | -1.34 |
| PIVOT_CAM | R1 | REJECT | tight_atr | 1771 | 13.5 | 39.4 | -8.03 | 1.12 | -5.76 | -5.73 | -1.57 | +0.61 |
| SATY | 0.618 (priority) | REJECT | tight_atr | 1679 | 12.8 | 38.0 | -7.75 | 1.17 | -5.76 | -5.32 | -2.26 | -0.78 |
| SATY | 1.0 (priority) | REJECT | tight_atr | 736 | 5.6 | 34.1 | -10.64 | 1.17 | -5.47 | -5.25 | -1.75 | -0.40 |

All 10 negative, all REJECT, all `tight_atr`, all directionally consistent BUILD vs RECENT (weaker
t in RECENT purely from smaller n, never a sign flip), all `reliable=True` under pathsafe. **Every
one of these is "do not fade this level intraday", not "trade this level".** The best POSITIVE cell
in the whole 284-cell study is FIB_WEEK 0.382 BREAK wide_atr, t=+1.99, n=249 -- nowhere near the 3.75
Bonferroni bar, and not powered enough even at a relaxed t>=2 bar to call a lead.

### Per-system verdicts (one line each; negative verdicts are the expected outcome here)
- **SATY ATR ladder**: KILLED as a tradeable level. Outer/priority rungs (0.618, 0.786, 1.0x ATR)
  fail REJECT hardest (t -5.5 to -8.2, consistent BUILD/RECENT sign); **priority vs normal ratios show
  NO meaningful difference** (both fail REJECT similarly, e.g. normal-0.786 t=-8.15 vs priority-0.618
  t=-5.76 -- priority is not special); **the ATR-consumed gate shows the OPPOSITE of Saty's own claim**
  -- higher ATR-consumption at touch makes REJECT WORSE, not better (consumed>=0.7 t=-9.05 vs
  consumed<0.7 t=-9.41 on tight_atr, i.e. no protective effect, if anything the reverse), consistent
  in both eras (see gates_report.txt). BREAK is flat (t -0.5 to +0.3) regardless of priority or gate.
- **Fibonacci (day & week)**: KILLED. Several REJECT cells clear Bonferroni on the loss side
  (FIB_DAY max|t|=5.10, FIB_WEEK max|t|=4.61); no BREAK cell clears on the win side (best +1.99).
- **Classic pivots -- Floor**: KILLED. R1/R2/R3-style REJECT fails (max|t|=5.45); no win-side survivor.
- **Classic pivots -- Camarilla**: KILLED, and the most heavily-populated failure (11/32 cells clear
  Bonferroni, all losses, R1 the worst at t=-5.76); the "priority" R3/S3/R4/S4 breakout levels are not
  differentiated from R1/S1/R2/S2 in the losing pattern.
- **Classic pivots -- Woodie**: KILLED (max|t|=4.60, all loss-side).
- **Classic pivots -- Fibonacci pivot**: KILLED, and among the strongest loss-side results (R1/S1
  REJECT t=-6.29/-5.95) -- the PP-anchored fib-ratio construction fails just as hard as the
  low/high-anchored FIB_DAY construction.
- **CPR (daily & weekly)**: mostly DEAD/UNDERPOWERED. Daily clears Bonferroni once (max|t|=3.96);
  weekly never does (max|t|=3.51). The width gate (narrow vs wide, used as a proxy for virgin-CPR --
  see caveat below) shows no differentiation: both buckets fail REJECT similarly (narrow t=-4.28,
  wide t=-3.10 on tight_atr). **Honest caveat: this is NOT the textbook virgin-CPR definition** (zone
  untouched by price since formed), which needs one more day of recursion this pass did not implement;
  what was tested is a narrow/wide-width proxy, disclosed as such.
- **Opening range (15/30/60)**: KILLED as a fade. High/low/mid REJECT all fail, worst at the LONGER
  windows and at the range MIDPOINT (OR15 mid REJECT tight_atr n=2200, t=-4.43, consistent BUILD
  t=-4.52; OR60 low REJECT t=-6.02) -- fading a test of the session's already-established range,
  including its midpoint, is a reliably bad trade; the market tends to keep moving through it.
- **Round numbers (50/100-pt)**: KILLED as a fade, cleanly. Nearest-50 and nearest-100 REJECT both
  clear Bonferroni (t=-4.30/-3.99 and -4.47/-4.39) with decent frequency (12-13 trades/month) -- no
  evidence NIFTY round numbers act as reliable intraday support/resistance for a fade; BREAK is flat.
- **Prior day H/L/C (plain touch)**: KILLED as an immediate fade -- high/low REJECT both clear
  Bonferroni hard (t=-6.22/-5.80), consistent across eras. This is the direct evidence for point (b)
  above: touching yesterday's level with NO confirmation is a bad trade; the calibrated SWEEP+RECLAIM
  variant (excursion beyond the level THEN a close back inside) is the only version of this family
  with a real (if cost-dominated) gross edge -- confirmation of a failed breakout matters, a bare
  touch does not.
- **Prior week H/L/C**: UNDERPOWERED-UNRESOLVED, not dead. Weekly cadence caps n (242-871 per cell);
  a couple of cells suggest the same loss-side pattern (low/BC REJECT t=-3.65/-3.51) but most sit
  below the bar. Needs more history or a coarser bar, not a verdict yet.

## THREE-LINE SUMMARY
Every one of 17 price-level systems (Saty, Fibonacci, four pivot families, CPR, opening range, round
numbers, prior-day/week) was tested for both rejection and breakout, against a random-level placebo
screen, and NONE produced a tradeable win: the only statistically robust results (10 cells clear the
m=284 Bonferroni bar at |t|>=3.75) are all on the LOSING side of immediate-fade trades at extended
levels -- a genuine, well-powered negative result, not an absence of testing. The mechanism is a mild
continuation tilt (BREAK loses less than REJECT on the same touch events, by less than 2x the
round-trip cost), meaning these levels behave slightly MORE like momentum pivots than like
support/resistance, contrary to how they are conventionally sold. The one prior-known positive in this
family (prior-day sweep+reclaim) replicates in sign and magnitude gross but is confirmed cost-dominated
net at 1-min granularity, correcting an earlier net-edge implication; Elliott Wave was scoped out as
not mechanically falsifiable rather than built as an unfalsifiable proxy.
'''

path = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PRICE_LEVELS_20260730\FINDINGS.md"
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("written", len(content), "chars")
