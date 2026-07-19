# EXIT-TRIGGER LEG 4 (MINERVINI/WEINSTEIN TECHNICAL STOP/TRIM) — BUILD + HARD-GATE REPORT

**Builder:** technical-head-dhruv-kapoor (E-005). **Spec:** `EXIT_TRIGGER_SPEC.md` Section 3.5
(fm-fundamental-sanjay-kulkarni, E-017), read in full. **Context read in full before building:**
`EXIT_TRIGGER_BUILD_REPORT.md` (legs 1-3, quant-head-arjun-rao) and `EXIT_TRIGGER_HARDGATE_REPORT.md`
(legs 1-3 hard-gate battery, overfit-analyst-sameer-bhat — Leg 2 came back **FRAGILE**, sign-flips
under an alternative entry-date convention). Tags: **[DATA]**=on-disk verified, **[INFERENCE]**=
mechanical construction, **[MY CALL]**=judgment call, flagged.

## Files produced
- `ALPHA_RANKER/rnd/scorecard/build_exit_trigger_leg4.py` — build script (legs 1-3 untouched, read
  verbatim from the frozen `exit_trigger_flags.parquet` and re-written unchanged alongside the 4 new
  leg4 columns; run twice, byte-identical, see below)
- `ALPHA_RANKER/rnd/scorecard/exit_trigger_leg4_hardgate_battery.py` — the hard-gate battery script
- `ALPHA_RANKER/rnd/scorecard/exit_weights_v1.json` — extended with a new `leg4_technical_stop_trim`
  block (legs 1-3 keys untouched)
- `ALPHA_RANKER/rnd/scorecard/exit_trigger_flags.parquet` — extended in place: same 99,415 rows,
  legs 1-3 columns preserved exactly, 4 new columns added (`leg4a_hardstop`, `leg4b_trim`,
  `leg4c_stagebreak`, `leg4_escalated`), `composite_exit_flag`/`notes` recomputed to include leg 4
- `ALPHA_RANKER/rnd/scorecard/_build_exit_trigger_leg4_log.txt`, `_exit_trigger_leg4_hardgate_log.txt`
  — verbatim run logs

## What was built (spec Section 3.5, exact conditions)
- **leg4a_hardstop**: `close(t) <= entry_price × (1 − 0.075)` — 7.5% hard stop from cost (spec's
  literal condition; the VCP-pivot alternative for breakout entries was **not** implemented — this
  overlay has no breakout-entry classification on disk — so all entries use the entry-cost variant).
- **leg4b_trim**: `15-trading-day return ≥ 25%` OR (`1-day return ≥ 5%` AND `volume ≥ 1.5× 20d avg
  volume`) — climax-run / blow-off signature.
- **leg4c_stagebreak**: a 50d/150d MA cross-below **within the trailing 10 trading days** (not
  "currently below," which would misread a stale multi-year downtrend as a fresh break every day —
  [MY CALL], §5.6-adjacent, frozen) AND `close < ma50` on above-20d-average volume AND ≥4
  distribution days in the trailing 20 sessions.
- **leg4_escalated** = `leg4c_stagebreak AND (leg1_valuation_ceiling OR leg2_fundamental_deterioration)`
  — the spec Section 4 EXIT_NOW escalation condition, exposed as its own column.
- `composite_exit_flag` **recomputed** with the full Section 4 precedence (legs 1-3's own EXIT_NOW/
  TRIM/WATCH semantics unchanged): EXIT_NOW (leg1&leg2, or leg4c&(leg1|leg2)) → TRIM (leg1, leg2, or
  leg4c alone) → ADVISORY (leg4a or leg4b alone, no other leg fired) → WATCH (leg3 Stage-A pending)
  → NONE.

## Judgment calls / fidelity gaps (all flagged, all frozen in `exit_weights_v1.json`)
1. **Monthly-panel-grain evaluation.** `panel_pit.parquet`'s grain is ~monthly (249 dates); the cube
   files are daily. Leg 4 is evaluated at each monthly checkpoint via an as-of (backward) join onto
   the daily signal series. An intra-month stop-hit-and-recovery, or a climax run that fully unwound
   before month-end, can be **missed**. This is a real limitation of reusing `panel_pit`'s grain, not
   a native daily exit feed, and is the single biggest structural gap versus how Minervini's rules are
   actually meant to be applied (daily, not monthly).
2. **No intraday open-price data on disk.** `cube_close_long.parquet` has close only. `gap_open(t)`
   (spec's literal blow-off condition) is **proxied** by the close-to-close 1-day return — a real
   fidelity gap versus the spec's literal condition, not a silent substitution.
3. **`cube_volume.parquet` has NO history before 2021-07-16** (confirmed, matches the spec's own
   disclosed data floor) and covers only 604 of the 933 symbols with a simulated entry in this overlay.
   leg4b and the volume-dependent half of leg4c are therefore only evaluable 2021-2025 and only for
   liquid/F&O-eligible names — reported, not silently worked around.
4. **Discontinuity guard [MY CALL, added prudently]:** `cube_close_long.parquet`'s corporate-action-
   adjustment status is undocumented for this specific file (`PANEL_SCHEMA.md` only covers
   `panel_long.parquet`). Any symbol-day with `|1-day return| > 40%` is excluded from firing ANY leg4
   sub-trigger that day (271 symbol-days across the full universe) — an unconfirmed bonus/split could
   otherwise fake a >40% "hard stop breach" or "climax run" that is not a real price move.
5. **Liquidity thresholds re-calibrated, not the literal spec numbers [MY CALL].** `cube_volume.parquet`'s
   751 names are already NSE F&O-eligible — an absolute rupee-ADV floor calibrated for the spec's own
   ₹5–10L example essentially never fires here (checked: the 1st percentile of 20d rupee-ADV in this
   file is ~₹1.9Cr, two orders of magnitude above that example). `thin_adv` is therefore defined
   relative to this file's own cross-section (bottom decile of pooled 20d rupee-ADV = **₹7.74Cr**
   floor, computed from data, frozen) and `circuit_suspect` relative to each name's own recent volume
   (today's volume < 10% of its own 20d average, since no OHLC exists to detect true band-pinning).

## Determinism check
```
run1 sha256=7010e84426c3162537c421b16efdc729bb1167c06d23005efae38b02c57570df
run2 sha256=7010e84426c3162537c421b16efdc729bb1167c06d23005efae38b02c57570df
DETERMINISM: PASS -- byte-identical
```

## Incidence rates (held rows = date ≥ simulated entry_date, same population as legs 1-3: 39,126/99,415)

| Leg | Fired rows (held) | Incidence |
|---|---|---|
| leg4a_hardstop | 5,524 | 14.12% |
| leg4b_trim | 1,003 | 2.56% |
| leg4c_stagebreak | 1,446 | 3.70% |
| leg4_escalated (4c AND leg1/leg2) | 182 | 0.47% |

`composite_exit_flag` breakdown (held rows, all 4 legs combined): **NONE** 27,317 · **TRIM** 5,839 ·
**ADVISORY** 5,680 · **EXIT_NOW** 253 · **WATCH** 37. (Sanity check: EXIT_NOW 253 ≈ leg1&leg2 (72, per
B1's original report) + leg4c-escalated (182), minus a handful of rows where both conditions fire on
the same row — reconciles.)

### FM-lens liquidity contamination check (spec Section 3.5.2 points 1-2)
| Leg | On a circuit-suspect day | On a thin-ADV (bottom-decile 20d rupee-ADV) day |
|---|---|---|
| leg4a_hardstop | 1 / 5,524 (0.0%) | 232 / 5,524 (4.2%) |
| leg4b_trim | 0 / 1,003 (0.0%) | 10 / 1,003 (1.0%) |
| leg4c_stagebreak | 0 / 1,446 (0.0%) | 186 / 1,446 (**12.9%**) |

**Read honestly:** circuit-lock contamination is negligible in this specific incidence set (expected —
`cube_volume.parquet`'s universe is F&O-eligible, i.e. pre-screened for liquidity; circuit-frozen
names are much more of a risk in the broader small/microcap universe this overlay's `entry_thesis_type`
population does not fully represent). **Thin-ADV contamination is material for leg4c specifically**
(12.9% of stage-transition fires occur on a name's own bottom-decile liquidity day) — a stage-break
read on those names should be treated with extra caution: a single thin session can distort the
50/150-day MA cross timing and the distribution-day count. leg4a and leg4b are cleaner on this
diagnostic (1-4.2%).

## Hard-gate battery (lag-test, placebo-shuffle seed=42 n=5, alt-entry decile/+3mo-lag — identical
methodology and identical bar as B2's Leg-2 battery)

Reference effect = mean forward return of fired rows vs. the **same clean baseline B1/B2 used**
(`any_leg_fired==False`, now inclusive of leg 4), original top-quintile entry convention.

| Leg | Horizon | Ref diff | Lag-test | Placebo | Alt-entry (decile) | Alt-entry (+3mo) | Verdict |
|---|---|---|---|---|---|---|---|
| leg4a_hardstop | 1M | +0.40pp (p=0.053) | FAIL (Δ=0.32) | FAIL | PASS | PASS | **FRAGILE-TO-FAKE** |
| leg4a_hardstop | 1Y | **+11.48pp** (p<0.0001) | PASS (Δ=0.06) | FAIL | PASS | PASS | **FRAGILE-TO-FAKE** (fails placebo) |
| leg4b_trim | 1M | +0.80pp (p=0.096) | FAIL (Δ=0.93) | FAIL | PASS | PASS | **FRAGILE-TO-FAKE** |
| leg4b_trim | 1Y | **+14.52pp** (p<0.0001) | PASS (Δ=0.05) | **PASS** (z=4.45) | **PASS** | **PASS** | **REAL (conditionally)** — see caveat below |
| leg4c_stagebreak | 1M | +0.62pp (p=0.027) | FAIL (Δ=0.69) | PASS | FAIL | FAIL | **FRAGILE-TO-FAKE** |
| leg4c_stagebreak | 1Y | +2.16pp (p=0.25, n.s.) | FAIL (Δ=0.65) | FAIL (z=-2.24) | FAIL (sign-flips to -4.58pp) | FAIL | **FRAGILE-TO-FAKE** |
| leg4_escalated | 1M | -0.22pp (p=0.78, n.s., n=172) | FAIL (Δ=8.0) | FAIL | NOT_TESTED¹ | NOT_TESTED¹ | **FRAGILE-TO-FAKE** |
| leg4_escalated | 1Y | -3.61pp (p=0.61, n.s., n=94) | FAIL (Δ=0.78) | FAIL | NOT_TESTED¹ | NOT_TESTED¹ | **FRAGILE-TO-FAKE** |

¹ leg4_escalated's alt-entry re-derivation would require recomputing leg1/leg2 (legs 1-3's own logic)
under the alternative entry conventions too — out of scope for this pass, reported as an open gap, not
silently passed.

### The honest, non-obvious finding: leg4b_trim is statistically REAL but WRONG-SIGNED for an exit rule

leg4b_trim is the only leg4 sub-trigger that survives the full battery at 1Y (lag-test PASS, placebo
PASS with the real effect z=4.45 outside five random-reassignment draws, AND both alternative
entry-date conventions PASS — the exact test that broke Leg 2). But the **sign is positive**: names
that fire the climax-run/blow-off "sell into strength" signature went on to **outperform** the clean
baseline by +14.5pp over the next year, not underperform. This is Fisher's own warning
("the stock went up a lot is NOT a valid reason to sell") showing up empirically: in this dataset, a
climax/blow-off signature marks names with a genuine, continuing momentum edge more often than it
marks a blow-off top about to reverse. **Mechanically trimming on leg4b as spec'd would, on this
20-year record, have cut into the book's best-performing continuing winners far more often than it
would have avoided a real reversal.** This does not mean leg4b is useless — it means its validated
empirical use, if any, points toward a **momentum-persistence/re-entry signal for the equities desk**
(fm-equities-devika-menon / Track-2), not a de-risking trim for the exit-trigger overlay. Recommend
flagging this finding to devika-menon rather than shipping leg4b as a trim trigger.

leg4a (hard stop) shows the same wrong-sign pattern at 1Y (+11.5pp) and additionally fails its own
placebo test (the real effect sits inside the range random reassignment produces) — no validated
effect in either direction. **leg4c (stage transition)**, the leg the spec frames as "the more mature,
higher-conviction half of technical desk's toolkit," is the **weakest** of the three empirically: it
fails the lag-test and placebo at 1Y, and sign-flips under the top-decile alternative entry convention
(-4.58pp vs the reference's +2.16pp) — the identical fragility pattern that killed Leg 2. leg4_escalated
inherits leg4c's problems and adds a thin-sample problem (n=94-172).

## FINAL VERDICT: **FRAGILE-TO-FAKE across all four leg4 outputs as an exit/de-risking discipline.**

None of leg4a_hardstop, leg4c_stagebreak, or leg4_escalated shows an effect that survives this
program's own hard-gate bar in the intended direction. leg4b_trim is the one sub-trigger with a
statistically robust effect (survives every gate), but it is **robust in the wrong direction** — a
genuinely different and arguably more important finding than a simple non-result, because acting on
it as a "trim" per spec would systematically cut winners with room left to run, not protect capital.
**Per the task's own instruction not to let this be the leg that finally "works" just because it is
the last one tested: it does not work as an exit trigger.** It ships in `exit_trigger_flags.parquet`
exactly as spec'd (mechanical, frozen, overlay-only, per the "builder must not decide" convention —
recall composite_exit_flag is a downstream, not a scoring, field), but **NOT CERTIFIED** for any
ADVISORY/TRIM/EXIT_NOW action gate until the CIO/FM see this report. This is consistent with, and now
extends, `EXIT_TRIGGER_HARDGATE_REPORT.md`'s own finding that Leg 2 is FRAGILE — of the module's four
legs, only Leg 1 (borderline, p=0.057, not yet separately hard-gated) has anything resembling a
directionally-consistent, not-yet-falsified signal; Legs 2, 4a, 4c, and 4-escalated do not hold up, and
leg4b holds up backwards.

### Single most fragile assumption (per leg)
- **leg4a/leg4c/leg4_escalated:** the entry-date convention (same as Leg 2) — effects sign-flip or lose
  significance under the top-decile alternative, meaning what modest effect exists is partly an
  artifact of the specific top-quintile first-crossing entry rule, not a convention-independent one.
- **leg4b:** not the entry-date convention (it survives that) — the fragility here is **interpretive**:
  the signal is real but does not mean what the spec's "sell into strength" framing assumes it means
  in this firm's actual universe and history.

## What still needs to happen before any leg4 output can be certified
1. A native daily-grain evaluation (not this monthly-panel-grain proxy) to test whether the "missed
   intra-month move" limitation (judgment call 1) is hiding a real effect the monthly grid cannot see.
2. Full OHLC data (to replace the gap_open proxy and to build a genuine circuit-lock detector instead
   of the relative-volume proxies used here) before any Section 3.5.2 gating claim is trusted at face
   value.
3. Avoided-drawdown-vs-held-through paired simulation (spec Section 7's actual primary metric for this
   whole module) — this report, like B1's, used a mean-forward-return diff as an honest first-and-only
   pass, not the prescribed metric.
4. If leg4b's momentum-persistence read is pursued, it belongs with fm-equities-devika-menon /
   Track-2's momentum work, not this exit-overlay module — a resurrection candidate for a different
   desk, not evidence for the exit trigger.
