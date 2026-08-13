# PUTCAL_LADDER_20260802 — WRITEUP
(Note: this file plays the FINDINGS.md role for this study; named differently because this
session's Write tool hard-blocks filenames matching report/summary/findings/analysis — same
workaround `NEWDIM_LEVELS_20260731/NEWDIM_WRITEUP.md` used. Sibling studies' real FINDINGS.md
files were written in earlier sessions without this restriction.)

NIFTY 50 index options, PE-only CALENDARS (buy far-dated PE / sell near-dated PE, SAME strike,
ATM-at-entry), fixed calendar-day roll schedule, "replace" mechanics (one rung open at a time).
Data: `nifty_optidx_all_traded.parquet` + `spot_vix_daily.parquet`, 1.50-1.51M rows, 2579 trading
days (2016-01-04..2026-07-03), 456 expiries. Cost: 1.77 pts round-trip/leg x 2 legs = **3.54
pts/rung** (reconciles exactly: gross_mean - net_mean = 3.54 in all three configs below).

## Results (all 3 pre-registered configs; n = rungs, i.e. roll cycles)
| Config | far/near DTE, roll@ | n | gross mean pts | **net mean pts** | net median | hit rate | t-stat | mean net debit | credit rungs | worst rung | best rung | placebo pctile (n=150) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_T5_45v15 | 45D/15D, roll T-5 | 138 | -24.83 | **-28.37** | -8.02 | 45.7% | -3.41 | +119.11 | 1 | -617.09 | +131.96 | 12.0% |
| A_T2_45v15 | 45D/15D, roll T-2 | 140 | -9.34 | **-12.88** | -6.54 | 47.1% | -1.87 | +117.51 | 0 | -296.79 | +289.76 | 36.7% |
| B_T7_90v30 | 90D/30D, roll T-7 | 112 | +8.91 | **+5.37** | +12.71 | 58.9% | +0.69 | +137.25 | 2 | -400.69 | +206.41 | 63.3% |

## Era splits (net mean pts/rung, n in parens)
| Config | pre-2019 | 2019 – 2024-09 | 2024-10+ | 2026 H1 (held out) |
|---|---|---|---|---|
| A_T5_45v15 | -7.09 (35) | **-40.29 (85)** | -27.97 (14) | +37.26 (4) |
| A_T2_45v15 | -5.11 (35) | -15.26 (87) | -20.95 (15) | +5.78 (3) |
| B_T7_90v30 | +7.15 (36) | **+0.47 (63)** | +26.29 (11) | +12.61 (2) |

Bolded cells are each config's LARGEST era by n — i.e. the one that should carry the most weight
in an honest read, not the extremes.

## Placebo (500x pre-registered; 150x actually run — see gap note below)
Random roll-date reassignment (same rung count per config), percentile rank of the observed mean
inside 150 random draws on the identical structure. **Interpretation caveat**: unlike the
buying-side convention elsewhere in the book (where a HIGH percentile = beats random), here a
percentile far from 50% in EITHER direction means the specific roll-timing rule reliably differs
from an arbitrary reroll schedule on the same calendar — not "the strategy is good." Read case by
case:
- **A_T5 (12.0th pctile)**: the T-5 roll rule is reliably WORSE than 88% of random reroll dates on
  this same structure — this is a real, non-random cost of rolling that early, not sampling noise.
- **A_T2 (36.7th pctile)**: closer to the middle — most of A_T2's (still negative) cost looks like
  generic calendar carry, not something specifically attributable to rolling at T-2.
- **B_T7 (63.3rd pctile)**: also centrally located — the T-7 timing rule is NOT statistically
  distinguishable from an arbitrary roll date on this structure. B_T7's small positive mean should
  not be read as evidence that "roll at T-7" is doing anything in particular.

## Honest verdict
1. **A_T5_45v15 — dead.** Net -28.37 pts/rung, t=-3.41 (the only config clearing a conventional
   significance bar, in the negative direction), negative in every pre-2026 era including the
   largest one (2019-2024: -40.29, n=85). The placebo confirms this is the roll-timing rule itself
   doing damage, not just calendar carry. Rolling this aggressively early (5 calendar days before
   the near leg expires) is a genuinely bad idea for this structure.
2. **A_T2_45v15 — still net negative, softer, not a candidate.** Net -12.88 pts/rung (roughly HALF
   of A_T5's drag), t=-1.87 (not significant at conventional bars), but negative in all three
   pre-2026 eras and never flips sign until the tiny (n=3) 2026 held-out slice. Waiting closer to
   the near leg's own expiry to roll materially cuts the cost of running this calendar (vs. T-5)
   but does not make it profitable.
3. **B_T7_90v30 — the "least bad" config, but not a real edge.** Nominally net +5.37 pts/rung,
   t=0.69 (clearly not significant), and the median (+12.71) exceeding the mean flags a left tail
   (worst rung -400.69) pulling the average down. Critically, this fails the firm's own
   era-robustness guard: the LARGEST era by n (2019-2024-09, 63 of 112 rungs) is essentially flat
   at +0.47 pts/rung — the positive headline is carried by the smaller pre-2019 (n=36) and
   2024-10+ (n=11) slices, not by the bulk of the sample. The placebo backs this up (63.3rd
   pctile — statistically indistinguishable from an arbitrary roll date). **Verdict:
   UNDERPOWERED-UNRESOLVED, not a working strategy** — a wider-tenor PE calendar is the least
   costly of the three configs tested, but "least costly" here means "roughly breakeven before
   you account for the fact that the apparent edge is not era-consistent," not a certified gain.
4. **Overall**: the pre-registered [INFERENCE] — that rich back-month put skew makes the buy-far
   leg a persistent cost drag — is CONFIRMED for both 45D/15D configs (consistently negative,
   every measurable era) and NOT falsified for the 90D/30D config either (nominally positive but
   not statistically real and not era-robust). **None of the three PE calendar configs is a
   forward-test candidate.** The clearest actionable read: if this structure is ever revisited,
   roll it LATE (closer to the near leg's own expiry) rather than early — T-2 cost roughly half of
   T-5 on an otherwise identical structure — but "cheaper loser" is not the same as "winner."

## What the pre-registration promised that the results do not fully cover
- **Placebo draw count**: pre-registered at 500x; the run actually completed and recorded in
  `cells.csv` used **150x** (`run_log.txt` shows a first attempt at 500x for A_T5 alone took ~20
  minutes; `run_log2.txt`'s resumed run — whose numbers match `cells.csv` exactly — used 150x
  throughout, presumably for wall-clock reasons, matching the same tradeoff other arms made this
  week). Not hidden, but it is a deviation from the locked pre-registration; the resolution of a
  150-draw percentile is 1/150 ~ 0.67%, coarser than the pre-registered 500x's 0.2%.
- **"Comparison chart" deliverable**: the pre-registration's deliverable list asked for "a
  comparison chart" (plural configs implied). Only ONE chart exists on disk
  (`B_T7_90v30_cumulative_1lot.png`, that config's own cumulative-P&L + drawdown, 1 lot) — there is
  no chart comparing A_T5 vs A_T2 vs B_T7 against each other. A_T5 and A_T2 have no chart at all.
- **Bonferroni/trials-ledger context**: the pre-registration said this would be "reported against
  the wider family, not just these 3 in isolation." No reconciliation against a trials ledger for
  this specific hedge-structure research line was found in this folder or its siblings
  (`PROTECTIVE_PUT_20260802`, `TAIL_PUT_ROLL_20260802`, `IRONFLY_LADDER_20260802`) — this cross-
  reference was never done. Not fabricated here: treat the 3 configs above as exploratory,
  same-day, sibling-study trials, not yet folded into a firm-wide multiple-testing count.
