# EXIT-TRIGGER OVERLAY — BUILD REPORT (Legs 1-3 only)

**Builder:** quant-head-arjun-rao (E-004). **Spec:** `EXIT_TRIGGER_SPEC.md` (Sanjay Kulkarni, E-017), read in
full 2026-07-18. **Scope confirmed:** leg 4 (technical stop/trim, spec §3.5) IS present in the spec as of this
read — added post-hoc by Dhruv Kapoor's workstream. Per task instruction, **leg 4 is noted but NOT implemented
this pass.** Only legs 1-3 are built here. Tags: **[DATA]** = on-disk verified, **[INFERENCE]** = mechanical
construction, **[MY CALL]** = judgment call, flagged.

## Files produced
- `ALPHA_RANKER/rnd/scorecard/build_exit_trigger.py` — the build script (run twice, byte-identical, see below)
- `ALPHA_RANKER/rnd/scorecard/exit_weights_v1.json` — every frozen threshold, versioned, no per-run refit
- `ALPHA_RANKER/rnd/scorecard/exit_trigger_flags.parquet` — 99,415 rows (one per panel_pit.parquet date/symbol)
- `ALPHA_RANKER/rnd/scorecard/_build_exit_trigger_log.txt` — verbatim run log (data lineage, row counts, both
  determinism-check passes)

## Data lineage [DATA] — row counts verified at read time
| File | Rows | Role |
|---|---|---|
| `rnd/panel/panel_pit.parquet` | 99,415 | base grain (date, symbol, sector, fwd_ret_1M/1Y_raw) |
| `rnd/panel/stock_valuation_pit.parquet` | 148,297 | PE per name, PIT |
| `rnd/panel/w5bv_stock_percentiles.parquet` | 148,297 | `expensive_pctile_PE` |
| `rnd/scorecard/absolute_scorecard.parquet` | 99,415 (1Y slice) | `PE_current`, `PE_fair`, `rerating` — verified horizon-invariant (0 rows differ across 1M/1Y/5Y for the same date/symbol) before taking the 1Y slice |
| `rnd/panel/sector_context.parquet` | 4,720 | `sec_earn_yoy` |
| `rnd/wave4/_w6fg2_scored.parquet` | 143,907 | `earnings_confirm_v2`, `composite_v2_confirmed`, PIT via `available_date` (spot-checked: `available_date <= date` on sampled rows, no lookahead) |
| `rnd/scorecard/rel_score_1Y.parquet` | 32,973 | `rel_score_1Y`, `quality_score` |
| `rnd/scorecard/rel_score_5Y.parquet` | 79,194 | `rel_score_5Y` |
| `results/universe_forensic_score.parquet` | 751 | `forensic_risk_score_0_100` — **STATIC, no date column** |
| `results/universe_forensic_flags.parquet` | 14,269 | per-flag badness — **STATIC, no date column** |

Merge preserved the panel_pit row count exactly (99,415 → 99,415) at every join step — asserted in the script.

## Guards / discipline followed
- No new data pulled. No leg redesigned. No thresholds fitted — all six frozen priors from the spec's §5
  judgment calls are in `exit_weights_v1.json`, read by the script, none hard-coded in logic.
- `_w6fg2_scored` PIT respected as delivered (spec's own claim that `available_date`-PIT is already resolved
  onto the grid date upstream) — spot-checked, not re-audited end-to-end; a full T1-T10 lookahead audit
  (`lib/lookahead_audit.py`) has **not** been run on this overlay and should be before certification.
- **Overlay discipline honored:** `rel_score_1Y/5Y.parquet` and `absolute_scorecard.parquet` were only READ,
  never written to. The output lives in a wholly separate file.

## Judgment calls made (all flagged, all one-line changes in `exit_weights_v1.json`)
1. **Entry-date simulation [MY CALL — not in the locked spec, task-specified]:** the spec designs a HOLDING-exit
   rule and deliberately leaves live entry-logging as a production/paper-ledger process (§1.4). For this
   historical backtest overlay, `entry_date(symbol)` = the first date the name's `rel_score_1Y` OR
   `rel_score_5Y` reaches the top quintile (`rel_score >= 60`, since `rel_score = 200·(rank_pct−0.5)` and top
   quintile is `rank_pct >= 0.80`). Where both horizons eventually cross, the **earlier** date is used ("first
   appearance"). 558/933 symbols (60%) ever reached this bar over 2005-2025; the rest never generate an
   entry and carry `entry_thesis_type=UNKNOWN` / all legs False for their entire history.
2. **Leg 3 static-snapshot handling [MY CALL, forced by data reality, not a spec ambiguity]:**
   `universe_forensic_score.parquet` / `universe_forensic_flags.parquet` are **live current-state snapshots
   with no date column** — there is no PIT forensic time series on disk. The spec's Stage-A "+20-point
   deterioration since entry" branch is **not computable** and was not implemented (would require fabricating
   history that doesn't exist). To avoid a straightforward lookahead violation (using today's score to flag
   2015's holding), the two computable branches (`score >= 70` OR a severe confirmed flag in the four
   highest-conviction categories) are applied **only to each symbol's last date in the panel** (i.e., "as of
   today"), never retroactively to history. This is the single biggest data limitation in this build — leg 3
   is effectively a live gate, not a backtestable PIT leg, and is reported as such rather than dressed up.
3. **`leg3_forensic_veto` column naming vs. actual semantics:** per task instruction, the column is named as
   requested but it holds the **Stage-A quantitative tripwire only**. It is NEVER auto-confirmed in this build
   (no analyst-read data exists on disk) — a companion column `leg3_requires_analyst_confirmation` is `True`
   wherever it fires, and `notes` spells this out per-row. `composite_exit_flag` correctly maps a Stage-A-only
   fire to `WATCH`, not `EXIT_NOW`, per the spec's own combination rule.

## Determinism check
Ran the full build twice end-to-end (including the 8-year rolling-percentile computation) in one process.
```
run1 sha256=a0b203dd8fe5b38c1e342f4c731fc342344ecb4689163d3fdb17d99b7492aa64
run2 sha256=a0b203dd8fe5b38c1e342f4c731fc342344ecb4689163d3fdb17d99b7492aa64
DETERMINISM: PASS -- byte-identical
```

## Incidence rates (share of "held" rows — i.e., date ≥ simulated entry_date)
Held rows total: **39,126** (out of 99,415 panel rows; the rest are pre-entry or never-entered).

| Leg | Fired rows | Incidence (of held) |
|---|---|---|
| Leg 1 — valuation-ceiling (Jain) | 4,147 | 10.60% |
| Leg 2 — fundamental-deterioration (Fisher) | 753 | 1.92% |
| Leg 3 — forensic Stage-A tripwire (last-date-only) | 62 | 0.16% |
| **Any leg fired** | 4,878 | 12.47% |

`composite_exit_flag` breakdown (held rows): NONE 34,248 · TRIM 4,744 · EXIT_NOW 72 (leg1 AND leg2 jointly) ·
WATCH 62 (leg3 Stage-A alone). Entry-thesis split at entry (one row/symbol): VALUE_GROWTH 308, MOMENTUM 231,
UNKNOWN 19 — consistent with leg 1's gate materially restricting its own eligible population (only
VALUE_GROWTH entries can ever fire leg 1).

## FM-lens evaluation: did flagged names subsequently underperform? — honest, mixed result
Compared forward returns (`panel_pit.fwd_ret_1M_raw`, `fwd_ret_1Y_raw` — already-built, non-overlapping-safe
forward return columns, not something this script computed) for held rows where `any_leg_fired=True` vs
held rows where it was `False`, Welch t-test:

| Horizon | Flagged mean | Not-flagged mean | Diff | t | p |
|---|---|---|---|---|---|
| **1M forward** | +2.16% | +1.92% | **+0.24pp (wrong sign)** | 1.32 | 0.19 |
| **1Y forward** | +24.87% | +27.36% | **−2.49pp (right sign)** | −2.52 | **0.012** |

Per-leg 1Y breakdown vs. a clean "no leg fired" baseline:
| Leg | 1Y mean fwd return | Diff vs baseline | t | p | n |
|---|---|---|---|---|---|
| Leg 1 (valuation-ceiling) | 25.29% | −2.07pp | −1.91 | 0.057 (borderline) | 3,459 |
| Leg 2 (fundamental-deterioration) | 22.73% | **−4.62pp** | **−2.56** | **0.011** | 551 |
| Leg 3 (forensic Stage-A) | 27.38% | +0.02pp (no signal) | 0.00 | 0.999 | 8 |

**Honest read, not oversold:**
- At the **1-month** horizon the trigger shows **no value and the wrong sign** — flagged names did marginally
  *better*, not worse, over the next month. This is not surprising on reflection (a valuation-ceiling fire
  usually means the name has been re-rating UP, which can carry a little further before it turns), but it
  means **this overlay is not a short-horizon timing signal** and should not be read as one.
- At the **1-year** horizon there is a real, modestly statistically significant effect in the intended
  direction: flagged names underperformed by ~2.5pp on average (`any_leg_fired`), driven mainly by **Leg 2**
  (Fisher-style fundamental deterioration, −4.6pp, p=0.011, the cleanest and most theoretically direct
  result) with **Leg 1** directionally consistent but only borderline (p=0.057, n=3,459 — a real sample, not a
  small-n artifact, so the borderline p is a genuine "modest, not absent" effect, not underpowered noise).
- **Leg 3 cannot be evaluated** — n=8-11 fired rows (a direct consequence of the last-date-only, non-PIT
  restriction above), no usable statistical power either way. It ships as a live gate, not a validated
  backtest leg.
- **What this does NOT show:** this is a single in-sample pass with no era-split, no lag-test, no
  placebo-shuffle (spec §7's own stated hard gates for certification) and no drawdown-avoidance framing
  (spec §7's stated PRIMARY metric — "avoided drawdown vs held-through", which needs a proper
  paired-portfolio simulation, not a mean-forward-return diff). What is reported here is a first-cut, honest
  directional check, not a certified result. **Verdict: FRAGILE, not REAL, not FAKE** — real theoretical logic
  (Fisher/Jain), a directionally-correct and partly-significant 1-year effect, but thin sample on the
  best-behaved leg (leg 2, n=551 fired) and a leg (leg 3) with no usable sample at all. Single weakest
  assumption: the entry-date simulation (judgment call #1) determines which rows count as "held" and
  therefore the entire denominator of this evaluation — a different reasonable entry rule would shift both
  the incidence rates and the forward-return comparison, and that sensitivity has not been tested.

## What still needs to happen before this can be certified (not done in this pass, scope-fenced by the task)
1. Full lag-test / placebo-shuffle battery per spec §7 (hard gates, not yet run).
2. Avoided-drawdown-vs-held-through paired simulation (spec §7's actual primary metric) — this report used a
   simpler mean-forward-return diff as an honest first pass, not the prescribed metric.
3. Era-split (2018/2020/2022/2024/2026 regime slices) and entry-rule sensitivity (judgment call #1) as
   robustness checks.
4. A proper PIT forensic score history (if one is ever built) would let leg 3 be evaluated with real sample
   size and retire the last-date-only restriction.
5. Leg 4 (technical stop/trim) integration once its thresholds are final, per task scope note.
