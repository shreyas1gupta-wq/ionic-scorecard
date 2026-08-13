# PRE-REGISTRATION — MA/RSI sleeve conditioners (Part A) + Oct-2024 break diagnostic (Part B)
Arjun Rao, 2026-07-30. Written and filed BEFORE `122_ma_rsi_and_break.py` is run. Per D-035:
no tuning after seeing results; this file is the contract the run is graded against.
Direct extension of `REGIME_GATE_20260730/` (same placebo construction, same monthly resolution,
same sleeve set + one addition). Do not re-derive that battery; cite it.

## PRINCIPAL WINDOW INSTRUCTION (mid-task, applied here)
"check only from 2019 march and keep 2026 for forward test."
- **Part A**: evaluation window restricted to **target-month 2019-03..2025-12**. 2026 is held out
  entirely — reported descriptively per cell, never used to pick a signal/threshold/lookback.
  This shrinks n materially (SWEEP_E/CALENDAR_1x1_3d go from ~137/178 months to ~82 usable
  target-months; S1F was already 2022-2025 so is largely unaffected; SWING_priorweek_f10 has only
  54 trades total, further thinned). **A cell that cannot be resolved at this n is reported
  UNDERPOWERED, not as a null "no effect."**
- **Part B**: NOT restricted. Uses full history (pre-2019 / 2019-Sep2024 / Oct2024-2025 / 2026 YTD)
  because characterising a break needs long-run baselines. 2026 IS included in Part B (the
  flagship's 2026 YTD was book-level +4.12% after a negative 2025 — whether the flat stretch is
  ending is part of the verdict).

## PART A — signals, sleeves, trials, accounting

### Signals NOT re-run (already dead in REGIME_GATE_20260730/cell_results.csv, cite don't repeat)
- S1_vix_level (IV level) — DEAD/SUGGESTIVE, never Bonferroni-passes.
- S2_vol_of_vol — DEAD throughout.
- S4_trend_sign (price vs MA200) and S5_trend_slope (MA200.pct_change(20)) — these are the
  MA200 members of the Principal's requested MA set; re-running them with an identical
  definition would be a literal duplicate trial (inflates the cumulative count for zero new
  information). Cited, not repeated.

### New signals (14), all causal (trailing/expanding only, no full-sample percentile)
NIFTY source = same as predecessor: `05_DATA_OFFICE/data/indices_close/indices_*.parquet`,
"NIFTY 50" closing index value (methodology continuity with S4/S5).
| # | signal | definition | state rule |
|---|---|---|---|
| MA10_price_above | price vs MA10 | `close.rolling(10).mean()` | 1 if close>MA10 |
| MA20_price_above | price vs MA20 | `close.rolling(20).mean()` | 1 if close>MA20 |
| MA65_price_above | price vs MA65 | `close.rolling(65).mean()` | 1 if close>MA65 |
| MA10_slope_up | MA10 slope sign | `MA10.pct_change(20)` (same slope-window convention as S5) | 1 if slope>0 |
| MA20_slope_up | MA20 slope sign | `MA20.pct_change(20)` | 1 if slope>0 |
| MA65_slope_up | MA65 slope sign | `MA65.pct_change(20)` | 1 if slope>0 |
| MA20_gt_MA65 | crossover state | sign of MA20-MA65 | 1 if MA20>MA65 |
| MA65_gt_MA200 | crossover state | sign of MA65-MA200 | 1 if MA65>MA200 |
| RSI5_oversold | RSI(5) band | Wilder RSI, period 5 | 1 if RSI<30 |
| RSI5_overbought | RSI(5) band | " | 1 if RSI>70 |
| RSI14_oversold | RSI(14) band | Wilder RSI, period 14 | 1 if RSI<30 |
| RSI14_overbought | RSI(14) band | " | 1 if RSI>70 |
| RSI28_oversold | RSI(28) band | Wilder RSI, period 28 | 1 if RSI<30 |
| RSI28_overbought | RSI(28) band | " | 1 if RSI>70 |
RSI bands use the CANONICAL fixed 30/70 thresholds, not an expanding percentile — this avoids
the full-sample-percentile lookahead trap by construction (RSI is already bounded 0-100; 30/70
are not derived from this sample). "Neutral" (30-70) is the implicit complement, not a separate
trial.

### Sleeves (4; SWEEP_D deliberately excluded — see below)
1. SWEEP_E (unchanged from predecessor).
2. CALENDAR_1x1_3d (unchanged).
3. S1F (unchanged).
4. **SWING_priorweek_f10 (NEW)** — `SWING_DELTA1_20260729/all_trades.csv`, cell
   `D_priorweek_sweep_long__fixed_10` (n=54 trades total, 2021-06-21..2026-05-18). Monthly
   target = sum(net) by exit month. This is the sleeve the predecessor explicitly excluded on
   budget grounds; included now per this task's instruction.
**SWEEP_D excluded from this pass.** Reasons: (a) not in this task's sleeve list; (b) the
predecessor already flagged SWEEP_E/SWEEP_D as 0.82-correlated on the same entry signal — a
"hit" on both would be one observation, not two, so testing both here would silently double an
already-registered coherence trap rather than add information.

### Trial count and cumulative Bonferroni (BINDING)
14 signals x 4 sleeves = **56 new cells**. Predecessor used m=28 (bar p<0.05/28=0.001786).
This task's cells ADD to the firm ledger, not replace it: firm cumulative trials BEFORE this
task = **410** (`OVERFIT_AUDIT_20260729/TRIALS_LEDGER.csv` row 10: 382 baseline + 28 regime-gate).
**Cumulative AFTER this task's 56 cells = 466.** Binding Bonferroni bar for calling any Part-A
cell CANDIDATE = **p < 0.05/466 = 0.0001073** — not a fresh m=56. The shorter evaluation window
does not reduce the trials count (Principal instruction, explicit).

### Method (identical to REGIME_GATE_20260730, restated)
- Monthly resolution; state at month t (causal) -> target = sleeve P&L in month **t+1**.
- Test statistic: `mean(P&L|state=1) - mean(P&L|state=0)`, two-sided.
- Placebo: block-circular permutation of the monthly state sequence, block=6 months, n=1000
  draws -> null distribution of |diff|. p = P(|null diff| >= |real diff|).
- Fixed-weight control: unconditional mean P&L over the same eval window, reported alongside.
- Era sub-split within the eval window (2019-03..2025-12): **pre_Oct2024** (2019-03..2024-09)
  vs **post_Oct2024** (2024-10..2025-12) — a sign-flip here is evidence AGAINST the signal even
  if the pooled statistic passes (same standing rule as the predecessor's 3-era split, adapted
  to the shorter window since a genuine pre-2019 slice no longer exists in-sample for Part A).
- 2026 (held-out): reported per cell (mean P&L by state, n) but never used for verdict.

### Kill / keep criteria (pre-committed, unchanged in spirit from predecessor)
- **UNDERPOWERED** if n(eval)<12 or either state has <4 obs — reported as such, not as a null.
- **DEAD** if it clears n but fails placebo (p>=0.05).
- **SUGGESTIVE** if it beats placebo (p<0.05) but fails the cumulative Bonferroni bar (p>=0.0001073).
- **CANDIDATE** only if placebo-pass + cumulative-Bonferroni-pass + no sign-flip pre/post-Oct2024
  + beats the fixed-weight control. Even a CANDIDATE is a lead for dedicated follow-up, not a
  certified rule.
- If zero cells reach CANDIDATE: clean NO on MA/RSI regime-conditional weighting, same
  recommendation as predecessor (prediction-free sizing, `DYN_SIZING_20260730`).
- **Expected result (stated before running, per assignment): a NO.** MA/RSI are transforms of
  the same price series as the already-dead S4/S5; this is expected to replicate that null, and
  a clean NO here is the valuable result — it closes the price-derived-filter direction firm-wide.

## PART B — Oct-2024 structural break diagnostic (descriptive; NOT a discovery trial, no
selection penalty — this characterises a possible break, it does not pick a trading rule)

### Data
- `intraday_options_strategy/datasets/processed/nifty_1min.parquet` (11.34y, 2015-01-09..2026-05-14,
  1,047,541 bars, cols open/high/low/close) — the SAME file `sweep_11yr.py` used to build the
  SWEEP_E flagship. Filtered to real session (09:15-15:30, landmine #2).
- India VIX: `05_DATA_OFFICE/data/indices_close/indices_*.parquet` (for the VIX-vs-RV relationship
  only; 1-min VIX does not exist).
- Flagship trade ledger: `SWEEP_11YR_20260729/trades_E_swing3_trail60_1lot.csv` (n=4378,
  entry/exit price, lots, actual cost/net per trade, era-correct STT already applied).

### Eras (full history; 2026 INCLUDED per Principal instruction)
`pre_2019` (<2019-01-01) / `y2019_sep2024` (2019-01-01..2024-09-30) / `y_oct2024_2025`
(2024-10-01..2025-12-31) / `y2026_ytd` (2026-01-01..). A combined `post_Oct2024_all`
(=y_oct2024_2025 + y2026_ytd) is also reported to match the motivating fact's n=600/1.62y window.

### Measures (all descriptive, all pre-specified here before running)
1. **Sweep mechanism** — reuse `sweep_signals()`'s `priorday_reclaim` definition VERBATIM from
   `EMA_INTRADAY_BUYING_20260729/signal_budget/measure_signal_budget.py` (15-min bars, prior-day
   high/low sweep-then-reclaim-same-bar). Extended (metrics only, entry logic unchanged) to
   record: penetration depth (points beyond the prior-day level), bars-since-first-pierce within
   the day (reversal-speed proxy — this detector's reclaim is same-bar by construction, so bars-
   since-first-pierce measures how long price sat beyond the level before the reclaim bar fired),
   time-of-day of the trigger. Follow-through = signed forward return on DAILY closes at N=1/3/5
   trading days (N=3 matches the flagship's own swing-3 hold).
2. **Persistence**: lag-1 autocorrelation of daily returns and of intraday (within-day-only) 15-min
   returns; variance ratio VR(5), VR(10) (Lo-MacKinlay overlapping estimator, no small-sample
   correction — flagged as approximate); average run length of daily up/down streaks; average
   run length of the MA20/MA65/MA200 price-above state (persistence of trend state).
3. **RSI behaviour**: RSI(5/14/28) on the nifty_1min-derived daily close; % time oversold/
   overbought per era; mean forward 5d/10d return conditional on RSI<30 vs RSI>70 vs neutral
   (mean-reversion strength); percentile distribution of RSI per era.
4. **Vol structure**: realized vol (20d annualized) level; vol clustering (autocorr of squared
   daily returns, lag1); intraday range as % of close; overnight-vs-intraday variance split;
   India VIX level minus realized vol (VRP proxy). **Priority figure**: range-to-stop ratio =
   mean daily range (points) / 60 (the SWEEP_E trailing-stop distance), per era — tests whether
   a stop calibrated on an older, wider-range regime is now mismatched to a compressed one.
5. **Cost decomposition**: recompute `sweep_11yr.py::rt_cost` on the post-Oct-2024 trade subset
   with STT held at the OLD rate (0.0125%) vs actual NEW rate (0.020%), same trades/prices/lots —
   isolates the STT-hike-only contribution in rupees and index points per round trip, then
   expresses it as a % of the observed pre-vs-post per-trade net P&L gap.
6. **Power calculation (the priority figure)**: using `trades_E` per-trade net P&L in the
   `y2019_sep2024` era (pre-break reference, matches the motivating-fact era CAGR 15.46%/PF1.67)
   for mu, sigma; n=600 (actual post-Oct-2024-all trade count, verified against the file, not
   assumed); z = (observed_post_mean - mu)/(sigma/sqrt(n)); one-sided normal-CDF p. Cross-checked
   at monthly resolution (less exposed to within-trade autocorrelation from overlapping 3-day
   holds) using the Newey-West long-run variance already implemented in
   `EMA_INTRADAY_BUYING_20260729/stage1_signal_test.py::nw_tstat`. The iid assumption for the
   per-trade version is flagged explicitly as a simplification, not hidden.

### Verdict rule (pre-committed)
DECAYED = pattern intact (frequency/persistence/RSI behaviour stable) but follow-through/edge
gone. STRUCTURAL = the pattern itself measurably changed (frequency, persistence, or vol
structure shifted). COST = STT alone explains most of the gap. INCONCLUSIVE/NORMAL-VARIANCE =
the power calculation shows 1.62y/n=600 cannot statistically distinguish "edge unchanged" from
"edge gone" at conventional confidence. These are not mutually exclusive; report the dominant
one(s) with the power number as the tie-breaker.

## Output files (`MA_RSI_BREAK_20260730/`)
`partA_cell_results.csv`, `partA_era_splits.csv`, `partB_sweep_mechanism.csv`,
`partB_persistence.csv`, `partB_rsi_behavior.csv`, `partB_vol_structure.csv`,
`partB_cost_decomp.csv`, `partB_power_calc.csv`, `run_log.txt`.
Queued to `BACKTEST_QUEUE_20260730/queue/122_ma_rsi_and_break.py` per the mandatory queue
architecture (reads the full 1.05M-row 1-min file).
