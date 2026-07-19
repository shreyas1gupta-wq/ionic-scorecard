# EXIT-TRIGGER LEG-2 (FUNDAMENTAL-DETERIORATION) — HARD-GATE BATTERY REPORT

**Analyst:** overfit-analyst-sameer-bhat (E-027), risk office. **Target:** Leg 2 of the exit-trigger overlay (`ALPHA_RANKER/rnd/scorecard/exit_trigger_flags.parquet`), the only leg B1's first-cut check (`EXIT_TRIGGER_BUILD_REPORT.md`) found worth taking seriously (1Y: -4.62pp, t=-2.56, p=0.011, n=551). This report runs the hard gates B1 correctly flagged as missing: lag-test, placebo-shuffle, and entry-date-convention robustness (spec `EXIT_TRIGGER_SPEC.md` §7, discipline per `SCORECARD_BLUEPRINT.md` §2.4/§3.4).

Script: `ALPHA_RANKER/rnd/scorecard/exit_trigger_hardgate_battery.py`, run synchronously, no background execution. Determinism: rerun twice, identical console output aside from the seed=42 placebo draw, which is itself reproducible (single `np.random.default_rng(42)`).

## Reference effect (exact replication of B1's number, from frozen production output)

| Metric | Value |
|---|---|
| Flagged mean 1Y fwd return | 22.73% |
| Baseline (no leg fired) mean | 27.36% |
| Diff | **-4.62pp** |
| t | -2.56 |
| p | 0.0109 |
| n (fired) | 551 |

Matches B1's reported -4.62pp / t=-2.56 / p=0.011 / n=551 (small differences, if any, are from re-deriving the comparison directly off the frozen `exit_trigger_flags.parquet` + `panel_pit.parquet` join rather than re-trusting the prose).

## 1. Lag-test — shift firing date forward one period before measuring fwd_ret_1Y_raw

| Metric | Value |
|---|---|
| Lagged diff | -5.43pp |
| t | -2.99 |
| p | 0.0029 |
| n | 538 |
| delta = \|lagged-ref\|/\|ref\| | 0.174 (gate: <0.25) |
| **Result** | **PASS** |

## 2. Placebo-shuffle — 5 draws, seed=42, per-date stratified symbol reassignment

| Draw | Diff (pp) |
|---|---|
| 1 | 2.94 |
| 2 | -0.13 |
| 3 | 2.71 |
| 4 | 5.54 |
| 5 | 3.96 |
| **Real effect** | **-4.62** |

Placebo range: [-0.13, 5.54]pp, mean=3.00pp, std=2.08pp. **Result: PASS** — real effect is clearly outside (more negative than) the placebo distribution.

## 3. Alternative entry-date robustness (B1's own flagged weakest assumption)

| Entry convention | Diff (pp) | t | p | n | Verdict |
|---|---|---|---|---|---|
| Original (top-quintile, rel_score>=60) | -4.62 | -2.56 | 0.0109 | 551 | reference |
| Top-decile (rel_score>=80) | -1.34 | -0.52 | 0.6021 | 433 | FAIL |
| Original entry +3mo exec lag | 1.94 | 0.75 | 0.4509 | 571 | FAIL |

## Verdict

**FRAGILE -- survives lookahead/noise gates but is sensitive to the entry-date convention**

### Single most fragile assumption
The entry-date convention is the most fragile point exactly as B1 flagged: the effect does not hold up cleanly across at least one alternative, reasonable entry-date definition, meaning the -4.6pp is partly an artifact of the specific top-quintile, first-crossing entry rule chosen for this historical overlay rather than a convention-independent effect.

---
*Full run log follows (console output, verbatim).*

```
# EXIT-TRIGGER LEG-2 HARD-GATE BATTERY -- run log

[DATA] base merged panel rows=99415, symbols=933, dates=249 (2005-04-29 .. 2025-12-05, ~monthly)

## Step 0 -- baseline replication (sanity check against B1's report)

n_held=39126, leg2_fired rows=753
Replicated: 1Y mean flagged=22.73%, baseline=27.14%, diff=-4.41pp, t=-2.44, p=0.0149, n=551
(B1 reported: 22.73% vs baseline, -4.62pp, t=-2.56, p=0.011, n=551 -- checking match up to baseline-population definition: B1 compared vs a clean 'no leg fired at all' baseline; here baseline = held rows with leg2 not fired, which may include leg1/leg3 fires. See note below.)

Exact B1 replication (frozen exit_trigger_flags.parquet, baseline=any_leg_fired==False): diff=-4.62pp, t=-2.56, p=0.0109, n=551
This is the reference effect the battery below is measured against.

## Step 1 -- lag-test (firing date shifted forward one period before measuring fwd_ret_1Y_raw)

Fired rows with no next period available (dropped, at panel's last date): 17
Lagged: diff=-5.43pp, t=-2.99, p=0.0029, n=538
delta = |-5.43 - -4.62| / |-4.62| = 0.174 (hard gate: <0.25, same sign) -> PASS

## Step 2 -- placebo-shuffle (5 draws, seed=42, per-date stratified symbol reassignment)

draw 1: n_fired=753, diff=2.94pp, t=1.29, p=0.1989
draw 2: n_fired=753, diff=-0.13pp, t=-0.06, p=0.9532
draw 3: n_fired=753, diff=2.71pp, t=1.15, p=0.2517
draw 4: n_fired=753, diff=5.54pp, t=2.21, p=0.0274
draw 5: n_fired=753, diff=3.96pp, t=1.52, p=0.1302

Placebo diffs (pp): [2.94, -0.13, 2.71, 5.54, 3.96]
Placebo mean=3.00pp, std=2.08pp, min=-0.13pp, max=5.54pp
Real effect: -4.62pp
Real effect clearly more negative than every placebo draw (z-vs-placebo-distribution = -3.67) -> PASS

## Step 3 -- alternative entry-date robustness

### 3a. Entry = first date reaching top-DECILE of rel_score (>=80) instead of top-quintile (>=60)

n_held=26722, leg2 fired=610
Top-decile entry: diff=-1.34pp, t=-0.52, p=0.6021, n=433
-> FAILS to replicate (sign flip, loses significance, or n too thin)

### 3b. Entry = original top-quintile entry date + fixed 3-month execution lag

n_held=37458, leg2 fired=715
3-month-later entry: diff=1.94pp, t=0.75, p=0.4509, n=571
-> FAILS to replicate (sign flip, loses significance, or n too thin)

## Step 4 -- verdict

Reference effect (frozen production flags, exact B1 replication): -4.62pp, t=-2.56, p=0.0109, n=551
Lag-test:        PASS (delta=0.174)
Placebo-shuffle:  PASS (real=-4.62pp vs placebo range [-0.13, 5.54]pp)
Alt-entry (decile):     FAIL (diff=-1.34pp, p=0.6021, n=433)
Alt-entry (3mo lag):    FAIL (diff=1.94pp, p=0.4509, n=571)

**VERDICT: FRAGILE -- survives lookahead/noise gates but is sensitive to the entry-date convention**
```