# S-03 / K-012 Resurrection — Leg 1 of 3: Parameter Sensitivity (Premium-Cap x FF-Threshold)
**Analyst:** Dr. Sameer Bhat (Overfit & Sensitivity, Risk Office) | **Date:** 2026-07-05
**Scope:** sensitivity grid ONLY (this is not a full Gate-4 battery). Perturbation/subsample/DSR
are explicitly out of scope here per the task brief — DSR/PBO recompute happens at CIO synthesis
once Nikhil's placebo leg and Tara's fill-audit leg also land.

## VERDICT: **PLATEAU**
The chosen point (3x premium cap, FF>=0.25) sits on a broad, smoothly-varying, sign-consistent
plateau. All 30 grid cells are forward-positive and build-positive; there is no sign flip, no
single-spike cell, and the chosen cell is **0.99% above its own cap/FF neighborhood median**
(effectively dead-center, not an outlier peak). This clears my charter's automatic-FAIL red flags
(no single-spike cell, no sign-flip across the surface, no "only passes at the exact registered
config"). **This PLATEAU verdict covers the sizing/threshold parameter surface only** — it does
NOT by itself clear K-012 for resurrection; see "What this does and doesn't tell us" below.
**UPDATE since landing:** Nikhil's parallel leg caught a T9-class non-causal entry-timing
lookahead in the underlying engine (`forward_factor_v2.py`, argmax-FF over a lookback window) —
see "CROSS-LEG UPDATE" section below. It does not change this PLATEAU verdict's shape but means
every absolute number in this memo is an optimistic ceiling pending a causal-entry re-run.

**Single most fragile assumption (not the parameters — the provenance):** the headline numbers in
`SIZING_RECHECK.md` (+Rs12.43/Rs100 build, +Rs9.91/Rs100 forward) were produced by a script that
was never checkpointed to disk. I reverse-engineered and validated a sizing formula that
reproduces `trading_brief_stats.json`'s pooled PF/win-rate/total/worst almost exactly (see
Reproduction below), and that formula is what the entire grid below is built on — but I could
NOT reproduce `SIZING_RECHECK.md`'s separately-quoted BUILD/FORWARD split (my own build/forward
split of the identical validated formula runs ~2.1x higher than the quoted figures, sign and
ordering preserved). The parameter surface itself is robust under my reconstruction; whether my
reconstruction is bit-for-bit the one that produced the original prose table is **unverifiable**
because the script is gone. That unverifiability, not any parameter choice, is the load-bearing
fragility in this leg.

---

## CROSS-LEG UPDATE (added after landing, D-028 duty — this is not siloed work)
Nikhil's parallel leg (`RED_TEAM_FF_RESURRECTION.md`, this directory) landed a **T9-class
non-causal entry-timing lookahead**: `forward_factor_v2.py` (L55-76) enters each cycle at its
**argmax-FF day** across a `[30,25,20,15,12]`-session lookback window — you cannot know a day was
the peak until later days have printed. This is a property of the `ff`/`entry` columns in
`forward_factor_v2.parquet` itself, i.e. of the **dataset my entire grid is built on**, not of any
choice I made. Two consequences for this memo:
1. **The PLATEAU verdict above is unaffected in shape.** The non-causal entry timing applies
   identically to every row in the parquet, hence identically to all 30 grid cells (same `entry`/
   `ff` values feed every cap x threshold combination). A uniform inflation does not manufacture
   a plateau where a cliff would otherwise be — the relative comparison across parameters that
   this leg exists to test still holds.
2. **The absolute levels in every table above (all "+Rs.../Rs100" and PF figures) are an
   optimistic ceiling, not a clean number.** Nikhil separately quantifies cost-fragility (survives
   2x costs, dies ~3.3x) on top of this. Until the engine is re-run with a causal entry rule
   (fixed-lead or earliest-FF-cross, per Nikhil's recommendation) and this grid is refreshed
   against that output, "PLATEAU" should be read as "robust *conditional on* the current
   (non-causal) entry engine" — necessary but not sufficient for resurrection. My independent
   read on my own charter's turf: this is a genuine FAIL-class lookahead finding (T9-class,
   argmax-over-lookback entry selection) and it should drive a formal D-028 T1-T10 audit of S-03
   before any capital ruling. **Correction while drafting this addendum:** I checked for an
   existing `LOOKAHEAD_AUDIT.md` ledger to log this against and none exists yet
   (`07_RISK_OFFICE/` currently holds only `LOOKAHEAD_CONTROLS.md`, the taxonomy reference, not a
   per-strategy ledger), and this task's write scope was explicitly restricted to
   `results/S-03/20260705_resurrection/`. I have NOT run the full T1-T10 battery here (that is a
   separate, larger piece of work than this sensitivity leg). This paragraph is the flag, not a
   completed audit: **a standalone `/lookahead-audit` on S-03, covering at minimum this T9 entry-
   timing catch, is an outstanding pre-resurrection gate** and should be scheduled explicitly
   rather than assumed done.

---

## Reproduction (reproduce-then-attack discipline)
No `.py` script survived in `results/S-03/20260704_shuffle/` for the Jul-5 04:xx recheck (only
`SIZING_RECHECK.md` and `trading_brief_stats.json` are dated that day; every script in that
directory is dated Jul-4). Methodology was reconstructed from `intraday_options_strategy/buying/
forward_factor_v2.parquet` (4585 rows) plus the CE-leg P&L formula in `ff_points_decisive.py`.
Reconstructed formula (full derivation + search log in `build_sensitivity_grid.py` docstring and
`build_sensitivity_grid_VALIDATION.txt`):

- Large-cap gate + FF>=FF_MIN slice, same as `ff_shuffle.py`/`ff_points_decisive.py` (n=673 at
  FF_MIN=0.25 — **matches register exactly**).
- `pnl_i = 2 * CE-leg-calendar-formula` (the x2 is a pure scale constant; raw-formula sum x2 =
  3497.27 vs registered BASE total 3497.0 — confirms the scalar, cancels in every ratio metric).
- `target = median(CE_be)` over the (large-cap, FF>=FF_MIN) slice, **build+forward combined**.
- `lots_i = min(target / CE_be_i, CAP_MULT)` — this is the parameter under test. CAP_MULT=inf =
  uncapped equal-premium.
- Aggregates are **ratio-of-sums** (`sum(rupee_pnl)/sum(deployed)`), never mean-of-ratios — this
  is the hard rule from the S-01/S-02/S-03 denominator-artifact history and is what the task
  brief calls "%-deployed denominators."

**Match quality at FF_MIN=0.25, CAP=3 (the registered point), full build+forward pool:**

| Metric | Register (`trading_brief_stats.json`) | This reconstruction | Match |
|---|---|---|---|
| n | 673 | 673 | EXACT |
| win rate | 71.8% | 71.8% | EXACT |
| profit factor | 2.24 | 2.24 | EXACT |
| total P&L | Rs 7,812.0 | Rs 7,812.1 | MATCH (<0.01%) |
| worst trade | -Rs 464.0 | -Rs 464.4 | MATCH (<0.1%) |
| BASE (equal-spread) total/worst | Rs 3,497.0 / -Rs 7,741.0 | Rs 3,497.3 / -Rs 7,741.3 | MATCH |

The scalar `cap=1201.7857142857142` recorded in the JSON does **not** equal 3x any median/mean of
CE_be I could construct from this parquet's columns (systematic search over 7 population slices x
5 columns x 18 multipliers logged in `build_sensitivity_grid_VALIDATION.txt` — closest miss was
~1 rupee off by coincidence, not a real match). It likely depended on an external reference (e.g.
per-symbol lot size / real liquidity data) not present in this file. This does not affect the
pooled reproduction above, which matches independently of what that scalar was built from.

---

## Parameter surface — P&L per Rs100 deployed (ratio-of-sums, denominator-safe)

**FORWARD (2025-26, the decisive test — this is what K-012 lives or dies on):**

| cap_mult \ FF_MIN | 0.15 | 0.20 | **0.25** | 0.30 | 0.35 |
|---|---|---|---|---|---|
| 1x | +17.16 | +20.04 | +19.66 | +19.39 | +24.62 |
| 2x | +18.61 | +21.16 | +21.17 | +21.14 | +25.88 |
| **3x (chosen)** | +18.85 | +20.95 | **+21.07** | +21.12 | +25.70 |
| 4x | +18.69 | +20.62 | +20.78 | +20.88 | +25.38 |
| 5x | +18.46 | +20.34 | +20.48 | +20.57 | +24.99 |
| uncapped | +18.50 | +20.39 | +20.45 | +20.54 | +24.92 |

**BUILD (pre-2025, in-sample):**

| cap_mult \ FF_MIN | 0.15 | 0.20 | **0.25** | 0.30 | 0.35 |
|---|---|---|---|---|---|
| 1x | +23.39 | +24.35 | +25.81 | +27.53 | +30.51 |
| 2x | +23.82 | +24.84 | +26.31 | +28.11 | +30.60 |
| **3x (chosen)** | +24.12 | +25.24 | **+26.72** | +28.56 | +30.91 |
| 4x | +24.61 | +25.79 | +27.33 | +29.26 | +31.58 |
| 5x | +24.72 | +25.92 | +27.48 | +29.46 | +31.76 |
| uncapped | +24.91 | +26.16 | +27.98 | +29.94 | +32.19 |

**Profit factor, FORWARD** (every cell, for reference — none touch 1.0):

| cap_mult \ FF_MIN | 0.15 | 0.20 | **0.25** | 0.30 | 0.35 |
|---|---|---|---|---|---|
| 1x | 1.78 | 1.94 | 1.88 | 1.82 | 2.14 |
| 2x | 1.90 | 2.06 | 2.01 | 1.95 | 2.27 |
| **3x** | 1.93 | 2.07 | **2.02** | 1.96 | 2.27 |
| 4x | 1.93 | 2.05 | 2.00 | 1.94 | 2.24 |
| 5x | 1.91 | 2.02 | 1.98 | 1.91 | 2.20 |
| uncapped | 1.91 | 2.02 | 1.96 | 1.90 | 2.18 |

**n trades (forward / build), by FF_MIN only (cap doesn't filter trades, only resizes them):**
FF 0.15: 247 fwd / 578 build · 0.20: 218/522 · **0.25: 199/474** · 0.30: 182/434 · 0.35: 163/400.

Full 60-row detail (total rupee P&L, worst trade Rs, maxDD %, deployed sum) for every cell:
`results/S-03/20260705_resurrection/sensitivity_grid.csv`.

### Plateau math at the chosen cell
Neighborhood = chosen cell's cap-axis (at FF=0.25) union its FF-axis (at cap=3x), forward per-100:
`{18.85, 19.66, 20.45, 20.48, 20.78, 20.95, 21.07, 21.12, 21.17, 25.70}`, median = **20.86**.
Chosen cell (21.07) is **+0.99% vs. neighborhood median** — i.e. it sits essentially on top of the
local median, not at a peak. (The neighborhood's single highest value, 25.70 at FF=0.35/3x, is
+23.2% above the median — but that is FF=0.35 outperforming, not the chosen FF=0.25 cell spiking;
see monotonicity note below. My charter's plateau test — "best cell <=20% above neighborhood
median" — is meant to catch the *chosen* cell being an outlier spike, and it manifestly is not.)

---

## Flags requested in the task brief

**(a) Uncapped equal-premium — does it stay positive or blow up?**
Stays positive, and does **not** blow up, at every FF threshold: forward range +18.50 to +24.92,
build range +24.91 to +32.19 (uncapped row above). This is an important structural finding: the
**sign flip from equal-spread to equal-premium happens with or without any cap at all** — going
from `BASE equal-spread` (forward loses, -Rs6.68 to -Rs9.30/pt per the Jul-4 kill and Jul-5
recheck) to `uncapped equal-premium` (forward +Rs18.50 to +24.92/Rs100) is the real lever. The
premium cap itself is a **second-order** adjustment on top of that: moving from uncapped to 3x
cap changes the forward number by at most ~3-8% at any given FF threshold, never changes sign,
and — see (b) — sometimes makes it slightly *worse* than uncapped, not better. **The cap is not
load-bearing for the sign of the result; the equal-premium sizing basis itself is.** That in turn
raises the priority of Nikhil's placebo question (is this genuinely FF-selection skill, or an
artifact of avoiding the largest, most-vega-exposed positions?) over the specific cap multiplier.

**(b) Monotonicity story**
Two different patterns, not one:
- **Across FF_MIN (fixed cap):** monotonically increasing in both BUILD and FORWARD as the
  threshold tightens 0.15->0.35 (e.g. cap=3x forward: 18.85 -> 20.95 -> 21.07 -> 21.12 -> 25.70).
  Clean, expected, no reversals.
- **Across cap_mult (fixed FF):** BUILD is monotonically increasing as the cap loosens toward
  uncapped (more capital allowed into cheap names always helps in-sample). FORWARD is **not**
  monotonic — it rises from 1x to a soft peak at 2x-3x, then gently *declines* through 5x and
  uncapped (e.g. at FF=0.25: 19.66 -> 21.17 -> 21.07 -> 20.78 -> 20.48 -> 20.45). The decline is
  small (~3% peak-to-uncapped) and never approaches zero, so it does not read as instability —
  but it does mean the "3x is the sweet spot" framing in `SIZING_RECHECK.md` is technically true
  on FORWARD (2x is marginally better, 21.17 vs 21.07, a rounding-level difference) while being
  slightly cap-adverse on BUILD (uncapped is best in-sample). This BUILD/FORWARD divergence in
  the *optimal* cap value, while both stay positive everywhere, is a normal soft-optimum pattern,
  not a red flag — but it means "3x" is a reasonable round-number choice near the optimum, not
  the identified optimum itself. No cliff in either direction.
- **Notable non-parameter observation:** FF=0.35 outperforms FF=0.25 (the chosen threshold) at
  every single cap value, on both build and forward (e.g. 3x forward: 25.70 vs 21.07). If FF=0.25
  had been picked by scanning forward performance and choosing the best, FF=0.35 would have been
  the pick, not 0.25. That it wasn't is a mild point *in favor of* FF=0.25 being a reasonable
  pre-specified choice (likely trading off the extra ~18% trade count at 0.25 — 199 vs 163 forward
  trades — against the smaller edge) rather than a cherry-picked one, but the desk should confirm
  this trade-off was made for a stated reason (capacity) and not simply left un-scanned.

**(c) Trial count for the family ledger**
This grid = **30 new trials** (6 cap values x 5 FF thresholds; BUILD/FORWARD reporting on each is
a breakdown of the same trial, not a second trial). Combined with `SIZING_RECHECK.md`'s own
declared **+3 trials** (equal-premium uncapped, 3x cap, 5x cap) from Jul-5, that is **33 new S-03
family trials in two days**, on top of whatever the Jul-4 kill investigation already carried (base
construction, N1/N2/N3 shuffle nulls x2 scripts, points-decisive re-booking). Qualitative
DSR/PBO read: a wide, sign-consistent, near-flat plateau across 30 honestly-counted trials is
structurally the *best case* for surviving a multiple-testing correction — spurious edges from
data-mining typically show up as isolated spikes, not 30-cell plateaus — but the enlarged trial
count still **raises the DSR hurdle**, and PBO must be recomputed via purgedcv on the **full,
updated** S-03 ledger (not just this leg's 30) before any capital ruling. I am not computing DSR/
PBO here per the task's own scope instruction; flagging it for CIO synthesis once Nikhil's and
Tara's legs land and the full trial count is known.

---

## What this does and doesn't tell us
This leg answers one question only: **given the reconstructed sizing formula, is the (3x cap,
FF>=0.25) point fragile to nearby parameter choices?** Answer: no, it is not — it is one of the
more boring, unremarkable cells in a uniformly positive 30-cell surface. It does **not** answer:
whether the reconstructed formula is the one that actually produced `SIZING_RECHECK.md`'s quoted
prose numbers (gap noted above); whether the underlying fills are achievable under circuit/volume
constraints on the cheap strikes that the equal-premium scheme up-weights (Tara's leg); or whether
the apparent skill survives a placebo that isolates vega/size effects from genuine FF-timing skill
(Nikhil's leg). The maxDD column (full CSV) also shows the BUILD period carries meaningfully more
tail risk than FORWARD at the tighter FF thresholds (e.g. FF=0.30-0.35, cap 2x-4x, BUILD maxDD
118-136% of average monthly deployed capital, vs FORWARD topping out at 93%) — this doesn't change
the sign verdict but is a genuine risk-sizing flag for Ritika/Tara, independent of this leg's
plateau-vs-cliff question.

## Lookahead note (D-028 self-flag)
`target = median(CE_be)` is computed on the **full build+forward pool** for each FF_MIN slice,
meaning the sizing constant used to size 2019-2024 build trades is informed by 2025-26 forward
premiums. This is a low-severity T-class lookahead artifact (it sizes a constant, not a signal —
it doesn't tell you which trades to take or when) but it is real, and it appears to be inherited
from the original (unrecoverable) methodology rather than introduced here (the reproduction match
above only holds under the full-pool target, not a build-only target — tested and logged in
`build_sensitivity_grid_VALIDATION.txt`). A full walk-forward-clean version (target fit on BUILD
only, applied out-of-sample to FORWARD) was spot-checked during reconstruction and is directionally
similar (same sign, same rough magnitude) but was not carried through the full grid since it would
no longer match the registered headline and this leg's job was to test the registered point's
neighborhood, not to redesign it. Recommend the eventual production spec (if K-012 resurrects) use
a rolling/expanding-window target, not a full-sample one.

---

## Files written
- `results/S-03/20260705_resurrection/sensitivity_grid.csv` — full 60-row grid (30 cells x
  BUILD/FORWARD), all requested metrics per cell.
- `results/S-03/20260705_resurrection/build_sensitivity_grid.py` — the grid builder, with full
  methodology docstring and validation block (checkpointed this time — this script will not
  disappear the way the Jul-5 recheck script did).
- `results/S-03/20260705_resurrection/build_sensitivity_grid_VALIDATION.txt` — line-by-line
  reproduction log vs `trading_brief_stats.json`, plus the cap-scalar search-miss record.
- `results/S-03/20260705_resurrection/SENSITIVITY_FF_SIZING.md` — this memo.
