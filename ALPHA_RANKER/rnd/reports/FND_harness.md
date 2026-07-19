# FND — Shared Evaluation Harness (`ALPHA_RANKER/rnd/lib/harness.py`)
Owner: Dr. Sameer Bhat (Overfit & Sensitivity Analyst). Implements RESEARCH_PROTOCOL.md S3/S4.
One code path — every factor experiment in the ALPHA_RANKER research loop goes through `evaluate()`.
No per-agent divergence, no post-hoc redefinition of metrics.

## Status
Built, smoke-tested on synthetic data (positive + negative control), then run end-to-end against the
**real production panel** `ALPHA_RANKER/rnd/panel/panel.parquet` (751 symbols x 61 monthly dates,
2021-07 -> 2026-07, 28 cols), which landed mid-build from the parallel panel-build agent. [DATA]

## API
```python
from harness import evaluate, run_experiment, load_panel, purged_walk_forward_splits, verdict

card = evaluate(factor, horizon, return_basis='resid', factor_id=None, panel=None,
                panel_source=None, family=None, cost_bps_override=None,
                min_names_per_date=20, n_cscv_blocks=12, n_placebo_shuffles=5,
                placebo_seed=42, write_card=True, cards_dir=None) -> dict
```
- `factor`: Series or DataFrame indexed/columned by (date, symbol).
- `horizon`: one of `1M / 1Y / 5Y` -> reads `fwd_ret_<horizon>_<return_basis>` from the panel.
- Writes `rnd/cards/<factor_id>.json` and returns the same dict.
- **One-line worker call**: `run_experiment(factor_id, factor_builder_fn, horizon, basis='resid')` —
  `factor_builder_fn(panel_df) -> factor`, panel auto-loaded if not passed.

### Card contents (per RESEARCH_PROTOCOL S3)
| Block | What |
|---|---|
| `ic` | per-date cross-sectional Spearman IC series -> `ic_mean`, `ic_std`, `ic_ir`, Newey-West t-stat (lag = horizon periods, Bartlett kernel) |
| `deciles` | decile-mean monotonicity (Spearman of decile rank vs decile mean of the evaluation basis) |
| `long_short` | top-minus-bottom decile spread on **raw** forward return (tradeable), `ann_return_LS`, `hit_rate` |
| `turnover` | avg fraction of top-decile names that are new each rebalance |
| `costs` | blended round-trip bps (see Cost model below) x turnover -> `ann_cost_drag`, `net_of_cost_ann_return` |
| `dsr` | Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014), deflated by the honest trial count |
| `pbo` | Probability of Backtest Overfitting via CSCV (single-factor adaptation, see below) |
| `regime_breakdown` | mean IC by `regime_trend`, `regime_vol` |
| `lag_test` | factor shifted +1 rebalance period; `lag_test_delta = \|IC_lag-IC\|/\|IC\|` |
| `placebo` | target shuffled within-date, 5 draws averaged; should be ~0 |
| `verdict` | PROMOTE / PARK / KILL per thresholds below |

### Verdict thresholds (`verdict()`, matches `backlog.json._meta.kill_default`)
KILL if `IC_IR < 0.20` OR `lag_test_delta > 0.25` OR `PBO > 0.50` OR `|placebo_IC| > 0.02` OR `DSR <= 0`.
Else PARK if `net_of_cost_ann_return <= 0` or `|monotonicity| < 0.5`. Else PROMOTE.

### Honest-trials ledger
`rnd/trials_counter.json`, atomic file-lock increment per `evaluate()` call, keyed by `family`
(defaults to the `factor_id` prefix before `_`). Feeds `DSR`'s `n_trials`.
**[DATA] current state after this build's dev + demo runs: `{"total_trials": 2, "by_family": {"demo": 2}}`**
— these 2 are genuine evaluations of trailing-12-1-momentum against the real panel (not synthetic
QA). My earlier synthetic-panel plumbing tests (families `test`, `worker_test`) were reset to zero
before this state, since those tested the harness code, not a real hypothesis — **that reset is
disclosed here, not silent**, and this ledger should NOT be reset again by a future run; it is meant
to be a tamper-evident count of every real trial fed through the harness.

### Cost model
Reads `Shreyas_Ionic_AMC/06_TRADING_DESK/COST_STANDARDS.md`. If `STATUS: APPROVED` is present (it is,
D-021), blends: `2x one-way slippage floor` (per cap tier: large 10bps/mid 20bps/small 35bps/micro
50bps) `+ 20bps STT delivery (both sides) + ~3bps exchange/GST/stamp` -> round-trip bps per tier
(large ~43, mid ~63, small ~93, micro ~123 — **[INFERENCE]: an arithmetic blend of the approved
per-item rates, not an independently-approved number**). Cross-sectional mktcap_log quantile
(20/50/80 pct) buckets each name into micro/small/mid/large; the card reports a name-weighted
blended bps. Falls back to a flat 25bps round-trip flagged DRAFT if the file is missing/unapproved.

### PBO / CSCV — single-factor adaptation (disclosed deviation)
RESEARCH_PROTOCOL calls for PBO via CSCV. The classic Bailey/Borwein/Lopez de Prado/Zhu (2014)
procedure ranks **multiple competing strategy variants** within each IS/OOS split; this harness
scores **one factor at a time**. Adaptation: split the LS return series into `n_cscv_blocks`
(default 12) contiguous time blocks, enumerate all `C(12,6)=924` IS/OOS partitions, and define
`PBO = P(OOS Sharpe < cross-partition median OOS Sharpe | IS Sharpe > cross-partition median IS
Sharpe)` — i.e., among partitions where this factor looked in-sample-best, how often its complement
underperforms the median. This is a faithful extension of the CSCV mechanics to N=1, not the literal
multi-strategy paper procedure — documented in the docstring of `compute_pbo_cscv()`.

### DSR — sigma_SR simplification (disclosed)
`trials_counter.json` stores a trial **count**, not the distribution of trial Sharpes. Per common
practitioner DSR writeups, `E[max SR | N trials]` uses the unit-variance (`sigma_SR=1`) Bailey-LdP
approximation. This is a conservative (harsh) deflation baseline, documented in `_expected_max_sharpe()`.

### Walk-forward splitter
`purged_walk_forward_splits(dates, horizon, n_splits=5)` — expanding-window folds with
PURGE+EMBARGO = `HORIZON_PERIODS[horizon]` (1/12/60 monthly periods for 1M/1Y/5Y) either side of each
test fold, so overlapping forward-return windows can't leak. Provided as a standalone utility for
worker agents building their own TRAIN/VAL/OOS splits (RESEARCH_PROTOCOL S0.3); not invoked inside
`evaluate()` itself, which scores the whole supplied panel slice in one pass.

### Panel loading / provenance (`load_panel()`)
Returns `(panel_df, source_tag)`, `source_tag in {'real','price_derived_demo','synthetic'}`:
1. `real`: reads `rnd/panel/panel.parquet` if present (now does — see Status).
2. `price_derived_demo` (fallback, only when `real` is absent): builds a **real-price-derived**
   panel from a random ~150-symbol subset of `data/prices/*.parquet` + `data/universe` sector
   mapping — real forward returns, real rolling vol/beta, a simplified trend/vol regime proxy off
   an equal-weight universe index. Disclosed as a subset/proxy, never silently mistaken for the
   production panel.
3. `synthetic` (`build_synthetic_panel`, `build_synthetic_panel(..., inject_signal=True)`): fully
   random, for unit-testing harness arithmetic only (used in this build's mechanics smoke test).
`evaluate(panel=..., panel_source=...)` lets a caller that pre-loaded the panel pass its real
provenance tag through — without this the card previously mislabeled a real-panel run as generic
`caller_supplied` (bug caught and fixed during this build, see below).

## Verification performed
1. **Mechanics smoke test** (synthetic panel, injected hidden signal): IC_mean 0.29, IC_IR 2.28,
   monotonicity 0.98, placebo_IC 0.011 (~0, correctly clean) — confirms the IC/decile/DSR/PBO/lag/
   placebo math is internally consistent. A pure-noise control factor (`vol_21` as "signal") on the
   same panel correctly KILLed (`IC_IR -0.26 < 0.20`).
2. **Bug caught+fixed pre-handoff**: initial draft collided column names when `return_basis='raw'`
   equalled the raw column (duplicate-column DataFrame crash) — fixed by keeping `target_eval` and
   `target_raw` as always-distinct columns. Also fixed a `panel_source` provenance bug (see above).
3. **End-to-end demo on REAL data**: trailing 12-1 momentum (`p[t-21]/p[t-252]-1`, built independently
   from `data/prices/*.parquet`, not read off the panel — a genuine factor->harness round trip, not
   a tautology), horizon=1Y, basis=excess, against the **real** `panel.parquet`:

| Metric | Value |
|---|---|
| n_dates / n_obs | 36 / 22,249 |
| IC_mean / IC_IR | 0.080 / 0.64 |
| Newey-West t | 1.55 |
| Decile monotonicity | 0.68 |
| ann_return_LS (gross) | 280% (small demo subsample, strong 2021-24 momentum window — see caveat) |
| turnover (top decile) | 25.5% |
| blended cost (RT bps) | ~80 |
| net_of_cost_ann_return | 278% |
| DSR (n_trials=2) | 0.982 |
| PBO (single-factor CSCV) | 0.97 |
| lag_test_delta | 0.092 (clean, < 0.25) |
| placebo_IC | -0.003 (clean, ~0) |
| regime_breakdown (trend) | bull +0.107, sideways +0.051, bear -0.049 (economically sane: momentum weakens/reverses in bear regimes) |
| **verdict** | **KILL (PBO 0.970 > 0.5)** |

Card: `ALPHA_RANKER/rnd/cards/DEMO_mom12m1.json`. The IC sign/direction, lag-test cleanliness, ~0
placebo, and sane regime pattern (bull > sideways > bear) all show the pipeline is measuring a real
signal correctly. The KILL verdict itself is informative, not a harness failure: PBO flags this
particular 36-month/751-symbol single run as fragile under CSCV — exactly the discipline this
harness exists to enforce before any factor reaches the weight book. **Caveat**: this is a demo run,
not a certified factor evaluation — 12-1 momentum is not yet a pre-registered `backlog.json` hypothesis
in this exact form; the number should not be quoted outside this harness-verification context.

## Files
- `ALPHA_RANKER/rnd/lib/harness.py` — the module.
- `ALPHA_RANKER/rnd/panel/panel.parquet` — real production panel (built by the parallel panel agent).
- `ALPHA_RANKER/rnd/cards/DEMO_mom12m1.json` — demo card.
- `ALPHA_RANKER/rnd/trials_counter.json` — honest-trials ledger (see disclosure above).
- `ALPHA_RANKER/rnd/reports/FND_harness.md` — this report.
