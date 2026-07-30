# PRE-REGISTRATION — Regime-conditional gate battery (Arjun Rao, 2026-07-30)
**Written and filed BEFORE any signal x sleeve cell is computed. Do not edit after results land.**

## Question
Is there ANY regime signal, computed real-time (expanding/trailing window only), that predicts a
sleeve's NEXT-month P&L out of sample, after (a) a block-permutation placebo and (b) multiple-testing
correction? Gate question for the Principal's regime-adaptive-weights ask.

## Trap this pre-registration exists to block
The flagship (SWEEP_E) has its worst year in 2025 (H2-2025 lost 6/7 months). Any regime rule
discovered by looking at 2025 and then "explaining" it is lookahead with extra steps. All signal
definitions and thresholds below are fixed NOW, before touching 2025 data, and every split threshold
inside a signal is itself computed on trailing/expanding data only (no full-sample percentiles).

## Sleeves under test (4 of the 5 dossier candidates)
1. **SWEEP_E** — liquidity-sweep reversal, 3-day swing, futures. `SWEEP_11YR_20260729/trades_E_swing3_trail60_1lot.csv`. Exit date reconstructed as `t + Timedelta(minutes=hold_min)` (verified exact inverse of `sweep_11yr.py` line 177: `hold_min = (exit_ts - entry_ts).total_seconds()/60`). Monthly target = sum(net_pts) in exit month.
2. **SWEEP_D** — same signal, overnight hold. `trades_D_overnight1_trail40_1lot.csv`, same reconstruction. Included as a coherence check: mechanically ~same entries as E (monthly corr 0.82), so a real regime effect on E should show up on D too; a "hit" on E only and not D is a red flag for noise.
3. **CALENDAR_1x1_3d** — ATM/ATM 1x1 calendar, exit 3 days before near expiry. `RATIO_CALENDAR_20260730/grid_a_trades_raw.csv` filtered `strike_struct=='ATM_ATM' & ratio=='1x1' & exit_variant=='3d_before'` (n=178). Has explicit `exit_day`; monthly target = sum(net_pts) by exit month.
4. **S1F** — certified 0DTE straddle, `STACKED_BOOK_20260711/book_daily_pnl.csv` column `s1f` (daily rupee P&L, nonzero 2022-01-06..2025-12-30, 208 days). Monthly target = sum(s1f) by month.

**Excluded: SWING_priorweek_f10** (`SWING_DELTA1_20260729`, cell `D_priorweek_sweep_long__fixed_10`,
n=54). Reason: already dossier-flagged PROVISIONAL/paper-only with its own DSR/PBO owed on a 45-cell
family; adding a 5th sleeve here would push the trial count past what this pass can honestly certify
in the time budget. Flagged as a follow-on, not silently dropped.

## Regime signals (7, all causal — computed with only data ≤ t)
Source for market signals: `Shreyas_Ionic_AMC/05_DATA_OFFICE/data/indices_close/indices_*.parquet`
(NIFTY 50 + INDIA VIX, daily, 2015-11-09 onward — this bounds how far back pre-2019 testing can go;
CALENDAR trades before 2015-11 are excluded from the regime test for signal-availability reasons, not
silently included with a missing state).

| # | signal | definition | state rule (no free parameter beyond the rule itself) |
|---|---|---|---|
| S1 | VIX level | `VIX.rolling(252).rank(pct=True)` — reuses the firm's already-tested VBT construction (`VBT_20260713/vbt.py`) rather than inventing a new one | state=1 if trailing pct ≥ 0.5 |
| S2 | Vol-of-vol | `VIX.diff().rolling(20).std()` | state=1 if ≥ its own expanding (min 252 obs) median to date |
| S3 | Realized vol | `NIFTY.pct_change().rolling(20).std()*sqrt(252)` | state=1 if ≥ its own expanding median to date |
| S4 | Trend sign | `NIFTY` vs `NIFTY.rolling(200).mean()` | state=1 if price > MA200 |
| S5 | Trend slope | `MA200.pct_change(20)` | state=1 if slope > 0 |
| S6 | Term structure | `iv_spread` (near−far ATM IV) from `RATIO_CALENDAR_20260730/term_structure.csv`, `expanding(min_periods=250).rank(pct=True)` | state=1 if expanding pct ≥ 0.5 |
| S8 | Own-drawdown | sleeve's own cumulative P&L (points or ₹, native units), running peak, `|drawdown|` vs its own expanding median to date | state=1 if currently in a deeper-than-typical drawdown |

**S7 (IV ratio, near/far) deliberately DROPPED before running** — it is ~collinear with S6 (both
derived from the same near/far IV pair); keeping both would inflate the trial count for no new
information. This is the only signal cut for that reason; noted here so it cannot be quietly added
back in if S6 fails.

**Valuation-band gate (Principal's 0-65/65-160/160+ rule): NOT TESTED.** Searched
`ALPHA_RANKER/`, `05_DATA_OFFICE/data/indices_close` (has raw NIFTY P/E and Div Yield, NOT the
composite band construction) and the firm's `.md` methodology docs — no on-disk daily NIFTY-level
valuation-BAND series (the actual 0-65/160 scale) exists, only the conceptual definition and raw P/E.
Per the standing instruction not to substitute a proxy for a specific named gauge, this signal is
reported as UNTESTED, not approximated. Flagged as an open item for whoever owns the ALPHA_RANKER
band construction to export a NIFTY-level daily series.

## Method (binding)
- **Monthly resolution.** State measured using data through month-end t (all inputs causal); target =
  sleeve P&L in month **t+1** (single pre-registered horizon — no horizon search).
- **28 primary trials** = 7 signals × 4 sleeves. Fixed now; no cell added or dropped after seeing results.
- **Test statistic:** `mean(P&L | state=1) − mean(P&L | state=0)` in month t+1, two-sided.
- **Placebo:** block-circular-permutation of the monthly state-label sequence (block=6 months, preserves
  regime persistence/autocorrelation), 1000 draws → null distribution of `|diff|`. Real `|diff|` must
  exceed the placebo 95th percentile (p<0.05 pre-correction) to even be a candidate.
- **Multiple-testing correction:** Bonferroni at m=28 → require p < 0.05/28 = 0.001786 (placebo-based
  p-value, i.e., real stat must clear roughly the placebo's 99.82nd percentile) before any cell is
  called real. This task's 28 trials will be appended to the firm's cumulative ledger
  (`OVERFIT_AUDIT_20260729/TRIALS_LEDGER.csv`); the cumulative bar is reported separately and is stricter.
- **Era split (descriptive, not separately significance-tested):** pre-2019 (bounded by data start
  2015-11), 2019-2024, 2024+. Reported for every cell; a sign-flip across eras is treated as evidence
  AGAINST the signal even if the pooled statistic passes, consistent with the firm's two-structural-break
  standing rule.
- **Fixed-weight control:** every cell's OOS regime-conditioned mean is reported next to the sleeve's
  unconditional (fixed-weight) mean P&L for the same window. A regime rule only earns adoption
  consideration if it beats this control OOS, post-correction, on the actual (non-placebo) side.
- **Vol/drawdown targets:** reported as descriptive companions to the same signal×sleeve cell (not
  separate discovery trials) — a return-null cell that shows an apparent vol or drawdown effect is
  flagged but NOT certified here; it would need its own fresh OOS pass.

## Kill criteria (pre-committed)
- A cell is **DEAD** if it fails the placebo (p≥0.05) — reported, not investigated further.
- A cell is **SUGGESTIVE** if it beats placebo (p<0.05) but fails Bonferroni at m=28 — reported as
  hypothesis-generating only, never "validated."
- A cell is **CANDIDATE** only if it beats placebo, clears Bonferroni at m=28, does NOT sign-flip
  across the three eras, and beats the fixed-weight control OOS. Even a CANDIDATE here is a lead for
  a dedicated follow-up study, not a certified sizing rule — one pass cannot replace a full Gate-4.
- If **zero cells reach CANDIDATE**, the verdict is a clean NO on regime-conditional weighting for
  these four sleeves, and the recommendation defaults to prediction-free sizing (drawdown budgeting,
  `DYN_SIZING_20260730`).

## Files
`121_regime_gate.py` (queued to `BACKTEST_QUEUE_20260730/queue/`) writes all outputs to this directory:
`cell_results.csv` (28 rows), `era_splits.csv`, `placebo_diagnostics.csv`, `run_log.txt`.
