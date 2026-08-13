# PRE-REGISTRATION — Vol-ML-gated short-premium sizing (Aakash Jain, Structurer, 2026-07-31)
Written BEFORE the sizing overlay's P&L is computed. Per D-035, no tuning after results are seen.

## Question
`REGIME_ML_20260730` certified an ML head (H3) that predicts the forward realised-vol TERCILE at
AUC 0.8528 OOS / 0.8742 held-out (2025-07 on) — the strongest, most robust effect measured in that
study, and explicitly flagged "usable for position sizing and the selling book," never implemented.
Does sizing the certified S1-F 0DTE short-straddle sleeve by this signal (sell MORE on predicted-LOW
days, LESS on predicted-HIGH days) improve risk-adjusted return over fixed-size, net of the
implementation constraint that a 0DTE straddle must size at/near market open?

## Signal construction (causal, no same-day lookahead)
- Source: `REGIME_ML_20260730/oos_predictions.parquet`, column `p_H3_vol3_HIGH` (walk-forward OOS
  probability of the forward-vol tercile being HIGH), 15-min bars, non-null from 2018-08-01 (first
  fold with enough trailing history), `hhmm` in {09:30..13:15} (model needs the opening-range
  features, so no prediction exists before 09:30 on a given day).
- **A same-day 09:30 reading CANNOT causally size a straddle that must be struck at/near 09:16
  market open** — using it would silently move the entry time, which is out of scope (S1-F's spec is
  D-030 FROZEN; this is a sizing overlay only, never a spec change).
- **Therefore the sizing signal used is the PRIOR trading day's LAST available prediction**
  (typically the 13:15 bar, sometimes earlier if that day's feed was short) — an unambiguously
  causal, pre-market-open read: "yesterday's close-of-session vol-regime estimate sizes today's
  straddle." This is a genuine implementation constraint, disclosed, not a design freedom.
- Tercile cut: **expanding, no-lookahead percentile** of `p_H3_vol3_HIGH` computed over the FULL
  2018-2026 daily series (all days, not just S1-F trade days, for better-powered thresholds), min
  250 prior observations before a cut is used.

## Sizing rule (one rule, fixed now)
- Predicted-LOW tercile (yesterday's close p_H3 in bottom third to date) -> size **2.0x**.
- Predicted-MID tercile -> size **1.0x** (baseline).
- Predicted-HIGH tercile -> size **0.5x** (reduce, not skip — a full skip is tested as a secondary
  variant, not the primary rule, since S1-F already carries its own crash-rule veto and stacking two
  independent kill switches is a separate question).
- Baseline for comparison: S1-F's actual realised daily P&L, sourced from the already-computed,
  already-vetted `STACKED_BOOK_20260711/book_daily_pnl.csv` column `s1f` (2022-01-04..2025-12-31,
  the real 4-sleeve book's S1-F contribution) — reused, not rebuilt, per firm convention. Non-trade
  days (s1f==0, expiry-day gaps/holidays) are excluded from both series identically.

## Method
- Join: for each S1-F trade date, take the prior calendar day's last `p_H3` reading (nearest prior
  date with a valid reading if the immediate prior day had none, e.g. after a holiday).
- NAV built by scaling that day's REALISED rupee P&L by the sizing multiplier (2.0/1.0/0.5) — this is
  a linear rescale of an already-realised outcome, not a new options fill, so no path-dependence and
  no `pathsafe` requirement (targets/stops are not being re-simulated here).
- Compare: baseline (always 1.0x) vs gated NAV. Report CAGR/maxDD/Sharpe/Calmar/PF, mean/day, t-stat,
  monthly win rate, on the FULL 2022-2025 span AND split at 2024-01-01 (build vs recent, since the
  book itself only spans 4 years — there is no additional held-out slice beyond what STACKED_BOOK
  already provides).
- **Placebo**: block-permute the tercile LABEL sequence (block=10 trade days, preserves
  autocorrelation) 500 draws -> null distribution of (gated CAGR − baseline CAGR). Real uplift must
  clear the placebo's 95th percentile to be called real, not luck of which specific days got upsized.
- **Trials**: this is ONE pre-registered rule (2x/1x/0.5x tercile) plus ONE secondary variant
  (HIGH-tercile -> skip entirely, 0x) = 2 trials, both entered in the ledger.

## Kill criteria (fixed now)
- DEAD if it fails its own placebo (real uplift < placebo p95).
- DEAD if maxDD does not improve (or worsens) alongside a CAGR gain — the whole point of a vol-based
  sizing lever is to trade CAGR for tail control or vice versa in a legible way, not to "win on both"
  by construction, which would be a red flag for a computation error.
- **UNDERPOWERED-UNRESOLVED, not DEAD**, if placebo passes but n is too thin to trust (S1-F trades
  ~41x/yr x 4yr = ~160-200 days; terciles split that further to ~55-65 days per bucket — flagged
  explicitly, per the firm's low-t power-aware re-screen convention, never silently dropped).

## What this is NOT
Not a new strategy, not a spec change to S1-F (D-030 untouched), not a claim that H1 (trend) is
usable (H1 collapsed to a coin flip OOS per REGIME_ML — only H3 vol is being spent here). If this
overlay works, it is a SIZING LEVER on the existing certified sleeve, to be proposed to Vikram Shah
(FM) and Ritika Sharma (Risk) for adoption on the live paper book, not a standalone signal.
