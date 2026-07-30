# PRE-REGISTRATION — VOL_SURFACE_20260731 (Arjun's vol-surface arm)
Written BEFORE any statistical test in run_tests.py is executed (extraction of the raw IV panel
itself carries no directional bias — it's just BS inversion of real traded prices, no signal choice
yet). Locks the cell list, horizons, placebo design, and kill criteria.

## Data construction (done, verified sane on a 2023 sample)
- `extract_surface.py`: EOD (15:15-15:29 last print) snapshot per (day, expiry, strike, type) from
  the 1-min chain, dte>=1 only (dte==0 / same-day-as-expiry snapshots excluded, T too small to invert
  reliably). BS-invert IV (r=0.065), compute delta, linearly interpolate the 25-delta call and put
  and the ATM (strike = round(spot/50)*50) IV. Also records the SAME contract's next-trading-day
  close price at the SAME strikes (close-to-close, no intraday path -> pathsafe's stop/trail rules
  do not apply; this is a timed exit, not a path-dependent one).
- `build_spot_features.py`: daily close, forward log returns (h=1,3,5,10,20 trading days), intraday
  realized variance at 5-min and 15-min sampling (overnight gap excluded, stated explicitly),
  trailing annualized RV (10/20d), and cumulative sums for O(1) forward-RV range queries.
- `build_daily_surface.py`: per day, FRONT = min-dte expiry available that day, NEXT = 2nd smallest
  dte (a DIFFERENT expiry, confirmed structurally present most days from overlapping weekly-file
  life). skew25 = iv25p-iv25c (positive = put-rich, the normal equity-index sign). butterfly25 =
  0.5*(iv25c+iv25p) - atm_iv. term_slope = next_atm_iv - front_atm_iv.

## Cells (fixed list — no cell added after seeing results)
1. skew_level -> fwd_ret (h=1,5,10), EXPANDING-percentile terciles of front skew25
2. skew_level -> fwd_vol (5min & 15min realized, horizon matched to front dte)
3. skew_change (1-day chg in front skew25, PIT lag) -> fwd_ret
4. skew_change -> fwd_vol
5. term_slope (next_atm_iv - front_atm_iv) -> fwd_ret
6. term_slope -> fwd_vol
7. term_inversion (slope<0) as a regime dummy -> mean fwd_vol conditional (inverted vs normal)
8. iv_rv_spread (front_atm_iv - trailing RV, 5min & 15min, 10d & 20d trailing) EXPANDING percentile
   -> fwd_ret (control; STRUCTURAL_EDGES/REGIME_ML found IV/RV-family signals carry vol content,
   not return content, so a null here is the EXPECTED, confirming result)
9. iv_rv_spread percentile -> fwd_vol (this is the B2 extension the brief specifically asks for)
10. VRP direct: front_atm_iv (annualized) vs matched-horizon forward realized vol (5min & 15min),
    by DTE band (front vs next) and era. Descriptive distribution + mean t-test vs zero.
11. PCA on [front_atm_iv, front_skew25, front_bfly25, next_atm_iv, next_skew25, next_bfly25]:
    loadings FIT ON PRE-OCT-2024 BUILD DATA ONLY, applied out-of-sample to the whole series (so
    the factor basis cannot itself be a lookahead artifact). PC1/PC2 score & 1-day change -> fwd_ret
    / fwd_vol.
12. STRUCTURE — sell the richer 25-delta wing, 1-day hold, close-to-close (entry EOD day T, exit EOD
    day T+1, same strike, same contract): net of cost (1.4 pt/leg round trip, mid of the firm's
    1.2-1.7 range). Conditioned on skew-richness tercile.
13. STRUCTURE — sell the CHEAPER wing (reverse control for #12): if #12 only works because "selling
    any option" harvests premium regardless of skew, #13 should show similar or better P&L; if #12
    beats #13 specifically, skew direction is doing real work.
14. STRUCTURE — sell both 25d wings (strangle), 1-day hold, conditioned on iv_rv-rich tercile
    (direct structural extension of B2, and the practical form of item 6's cross-sectional ask).
15. Cross-sectional: VRP magnitude (front vs next tenor) — is one tenor systematically richer.

## Method
- **Split** (mandatory, every cell): PRE = ..2024-09-30, POST = 2024-10-01..2025-12-31,
  HELDOUT-2026 = 2026-01-01... Selection/tuning only ever on PRE+POST (build); 2026 reported never
  selected on.
- **Regression**: OLS beta + Newey-West (HAC) t-stat, lag = the forecast horizon (overlapping-window
  correction), via statsmodels.
- **Placebo** (matches STRUCTURAL_EDGES convention): 500 reps signal-shuffle (seed=42) + 500 reps
  circular-shift; placebo_bar = max(95th pctile |t_shuffle|, 95th pctile |t_circshift|). A cell
  "clears placebo" iff |t_real| > placebo_bar in THAT era.
- **PIT discipline**: every percentile is an EXPANDING (past-only) rank, never full-sample. Skew
  CHANGE and any lagged feature is computed strictly from information available at or before the
  signal timestamp (EOD day T, used to predict day T+1 onward — never same-day).
- **Bonferroni**: this arm runs 15 pre-registered cells x ~3 eras x (return+vol targets) ≈ up to 90
  individual t-stats; combined with the firm's running cumulative trial count (~481+ before this
  session per SHARED_CONTEXT) the honest bar is well above t=3.8. State per-cell trial count in
  cells.csv; do not claim CERTIFIED on t alone.

## HARD KILL criteria (pre-registered, non-negotiable, per SHARED_CONTEXT 2026-07-30 framework)
1. Fails its own placebo (|t_real| <= placebo_bar) in the era being claimed.
2. Any lookahead: full-sample percentile, same-bar fill, or a feature computed with future information.
3. Profit concentration >30% of total P&L in a single trade/day (structure cells only).
4. maxDD > 25% (structure cells only).
5. Fills on zero-volume / unexecutable prints — N/A here structurally: every row is a real 1-min
   print (this chain file stores only actual trades, verified volume>0 for 100% of a sampled file).

## SOFT (sets tier, never kills): t-stat, Bonferroni, DSR/PBO.
Tier labels: CERTIFIED / FORWARD-TEST CANDIDATE / UNDERPOWERED-UNRESOLVED / DEAD.
A signal that clears placebo in only ONE era (pre XOR post-Oct-2024) is NOT promoted as general —
reported as an explicit "broken at the break" finding (like PCR->vol), not silently buried and not
inflated to a tradeable rule.
