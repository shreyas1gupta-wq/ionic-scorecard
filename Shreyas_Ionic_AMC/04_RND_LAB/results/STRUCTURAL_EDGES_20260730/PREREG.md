# PREREG — Structural / Calendar / Positioning Edges in NIFTY Options (2026-07-30)
Owner: Arjun Rao (Quant). Written BEFORE any result is inspected. Locks method, horizons, placebo
design and kill criteria per effect. Script implementing this exactly:
`Shreyas_Ionic_AMC/04_RND_LAB/results/BACKTEST_QUEUE_20260730/queue/113_structural_edges.py`
(queued per BACKTEST_QUEUE architecture — loops the full 16yr option chain + the 1.05M-bar 1-min file).

## Data
- Option chain: `05_DATA_OFFICE/data/fo_bhavcopy_hist/fo_idx_{2011..2026}.parquet`. Filter
  SYMBOL=='NIFTY'. TIMESTAMP/EXPIRY_DT are strings `DD-MMM-YYYY` (mixed case) → parse with
  `pd.to_datetime(x, format='%d-%b-%Y')`. Gate: OI-based metrics use OPEN_INT as-is (standing
  interest is real even if CONTRACTS==0 today); volume-based metrics (PCR_vol, CONTRACTS-weighted)
  filter CONTRACTS>0. Never read expiry-day SETTLE_PR as an option price (landmine #9) — this
  study never touches option CLOSE/SETTLE_PR at all, only OPEN_INT/CHG_IN_OI/CONTRACTS + EXPIRY_DT,
  so that landmine cannot bite here structurally.
- Underlying spot: `intraday_options_strategy/datasets/processed/nifty_1min.parquet` (1,047,541
  bars, 2015-01-09→2026-05-14, tz-naive IST, no volume col). Daily close = last bar per calendar
  day. This is the PRIMARY return series (cash index, no futures-roll noise) for effects 2/3/4/5/9/10.
  Coverage note: 2011-2014 has NO cash series here; those years are used ONLY for the chain-native
  effects (expiry-weekday history, OI concentration) that don't need a return series.
- Trading calendar: `.../processed/trading_calendar.csv` (2,794 sessions) for reindexing.

## Split (method law)
Build = 2011-01-01..2024-12-31 (chain-native effects) / 2015-01-09..2024-12-31 (return-series
effects). Held-out OOS = 2025-01-01..2026-06-03 (report, do not select on it — matches the
session's held-out convention). Oct-2024 regime-break test is evaluated on the FULL range by
construction (that is the point of the test) and reported separately from the build/OOS split.

## Effects, method, and PRE-REGISTERED kill criteria
1. **Expiry weekday history** — descriptive only, no kill criterion. Weekly-cadence expiries =
   consecutive distinct EXPIRY_DT with gap ≤8 days. Rolling-mode(window=9) of weekday; a "switch"
   = first date where the smoothed mode changes AND stays changed for the next 9 consecutive
   weeklies (filters single-holiday shifts, not real regime changes).
2. **Expiry-day realized |return| vs non-expiry days** — Welch t-test, mean|ret| expiry vs
   non-expiry. Also weekly-only and monthly-only subsets, and T-1/T/T+1 pattern around expiry.
   Placebo: 500 random relabelings of the expiry-day flag (fixed seed=42), same-count as real.
   KILL if |t_real| does not exceed the 95th pctile of the placebo |t| null.
3. **Weekly vs monthly expiry-day vol difference** — t-test between the two groups' expiry-day
   |return|. Descriptive comparison, reported alongside effect 2's placebo bar.
4. **PCR (OI-based & volume-based) as forward predictor** — daily PCR_OI = ΣPE_OI/ΣCE_OI and
   PCR_vol = ΣPE_contracts/ΣCE_contracts across the full listed chain that day. 252d rolling
   z-score as the stationary signal. OLS of forward h-day return (h∈{1,3,5,10}, close-to-close,
   PIT: signal known at close of day t, predicts t→t+h — a real backtest would need t+1-open
   execution, this measures CONTENT not P&L) and forward h-day realized |return| (vol proxy) on
   PCR_z, build-only. Two placebos per horizon: (a) full random shuffle of PCR_z, seed=42; (b) a
   126-day circular shift. Comparison bar = MAX(|t_placebo_a|, |t_placebo_b|) (hardest-to-beat
   convention). KILL a horizon if |t_build| ≤ that bar. A horizon that clears build must ALSO
   keep the same beta SIGN in the 2025-2026 holdout to be called a lead (not just noise that
   happened to clear one placebo draw).
   4×2 (return,vol) = 8 sub-trials for PCR_OI, ×2 for PCR_vol = 16 sub-trials total this effect.
5. **Max-pain gravitation** — per weekly expiry E, chain snapshot at T-2 (2 sessions before E) on
   that expiry's own strikes, OPEN_INT-weighted payout(S)=Σ_CE OI(K)·max(S-K,0)+Σ_PE OI(K)·max(K-S,0),
   mp=argmin. predicted_pull = mp − spot_{T-2}; actual_move = spot_E − spot_{T-2} (spot_E = cash
   index close on the expiry day, never option SETTLE_PR). OLS beta of actual_move on
   predicted_pull, one point per expiry event. Placebo: permute the predicted_pull vector against
   actual_move 1000x, seed=42, exact permutation null. KILL if |t_real| ≤ 95th pctile of the
   permutation |t| null.
6. **OI concentration (Herfindahl) — level & Oct-2024 regime break** — daily Σ(OI_k/ΣOI)² across
   near-week strikes. Welch t-test + KS test, pre-2024-10-01 vs post. Reported as part of the
   regime-break battery (effect 8), not independently killable (a level shift is a fact, not a
   trading claim).
7. **OI build-up/unwind sign (CHG_IN_OI) as directional signal** — sign(ΣCHG_IN_OI_CE) −
   sign(ΣCHG_IN_OI_PE) daily, same OLS/placebo/holdout structure as effect 4, h∈{1,3,5}. 3 sub-trials.
8. **Oct-2024 regime-break battery** — pre/post comparison (t-test+KS) of: PCR level & effect-4's
   build t-stat computed on each sub-period separately, OI Herfindahl (effect 6), expiry-day
   |return| (effect 2 subset), and whether an expiry-weekday switch (effect 1) brackets the date.
   Single synthesized verdict: BROKEN / NOT BROKEN / PARTIAL, plus the explicit implication for
   every pre-2024 backtest in the firm (including the session's own flagship sweep).
9. **Intraday seasonality** (nifty_1min.parquet, full 1.047M bars) — mean return & mean|return|
   per 5-min bucket, full sample (~75 buckets/session, day-internal pct_change so no overnight
   contamination). Split into 3 eras (2015-2018 / 2019-2022 / 2023-2026); STABLE if
   corr(era1 vol-profile, era3 vol-profile) > 0.7, else DECAYED. First/last 30min vs midday
   (11:00-14:00) |return| comparison. **Placebo (bucket-resampling, cheaper and cleaner than a
   within-day value shuffle, decided now before execution):** build the null by drawing 500 random
   6-bucket windows (=30min) as "fake first/last" and 500 random 36-bucket windows (=3h) as "fake
   midday" from the SAME 75-bucket profile (seed=42), comparing their count-weighted mean|ret| —
   this directly answers "would ANY randomly chosen window look this different from ANY other
   randomly chosen window," the right null for a time-of-day-specific claim, at a fraction of the
   compute of reshuffling 1.05M rows.
10. **Day-of-week / turn-of-month** — cash daily returns, weekday means (Mon-Fri) vs grand mean,
    t-test + 500-draw weekday-shuffle placebo. TOM = last trading day of month + first of next
    month (narrow, primary claim) vs a ±3-session window (secondary, separately counted sub-trial).
    Adverse prior stated up front: firm already killed a TOM-VIX overlay (0/4 cells, NOT ADOPTED,
    `results/TOMVIX_20260713/`) — that was a VIX-conditioned overlay, this is a plain direct-return
    test, a distinct but related trial, counted as such, not double-counted as the same trial.

## Honest trials count for this task
Effect1: 0 (descriptive) | Effect2: 1 main + 2 descriptive subsets = 3 | Effect3: 1 |
Effect4: 16 | Effect5: 1 | Effect6/8: descriptive, folded into regime-break verdict (not a
standalone claim) | Effect7: 3 | Effect9: 2 (era-stability + first/last-30min) + bucket-profile
descriptive | Effect10: weekday(1) + TOM-narrow(1) + TOM-wide(1) = 3.
**TOTAL new discovery sub-trials this task = 3+1+16+1+3+2+3 = 29.** To be appended to
`results/OVERFIT_AUDIT_20260729/TRIALS_LEDGER.csv` verbatim after the run, before any effect is
quoted elsewhere.

## What "worth a full backtest" means here
An effect only earns that recommendation if it clears its own placebo bar AND (for predictive
effects) keeps its sign out-of-sample in 2025-2026. Clearing a placebo is necessary, not
sufficient — RESEARCH_SOP's DSR/PBO/walk-forward battery still applies before any capital claim.
