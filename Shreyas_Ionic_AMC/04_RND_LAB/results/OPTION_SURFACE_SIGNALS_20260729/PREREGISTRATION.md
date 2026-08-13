# PRE-REGISTRATION — Option-surface signals (skew / term-structure / OI / NIFTY-BANKNIFTY)
**Author:** Ishaan Gupta (ML). **Filed:** 2026-07-29, BEFORE any feature is computed or any result is viewed.
**Mandate:** Shreyas_Ionic_AMC/04_RND_LAB/results/SHARED_CONTEXT_20260729.md — new-idea exploration,
signals from the OPTIONS MARKET ITSELF (vol surface, skew, term structure, positioning), not price.

## Split (same discipline as the rest of today's mandate)
- **Build window:** 2021-05-24 .. 2025-12-31. All kill/pass decisions made ONLY on this window.
- **Held-out:** 2026-01-01 .. 2026-06-03. Reported once, never used to pick features/thresholds/horizons.
- Any number from the held-out window in this doc was written down at the SAME TIME as the build-window
  number (single script run) — never re-run after seeing the build result.

## Universal method
- Daily panel, one snapshot per trading day at **09:20-09:30 IST** (mean of trade prices in that window;
  well clear of the 09:15 open and the pre-open auction bug). This is the PIT information set: everything
  used is knowable by 09:30 the same day, before any next-bar entry could act on it.
  **ADDENDUM (2026-07-29, filed after the first raw-panel build, BEFORE any regression/predictive test
  was run):** the 09:20-09:30 window gave 0% missing on the E1 (front-weekly) leg but 74%/90% missing
  on the E2/monthly legs — verified by hand on 2022-03-15's E2 chain, where only ONE deep-ITM strike
  printed in that 10-minute window (next-week/monthly options are genuinely thin at the open; a real
  liquidity fact, not a bug). The window was widened to **09:15-11:00 IST**, applied UNIFORMLY to every
  leg (E1/E2/Em/BANKNIFTY/PCR/spot) for a same-epoch comparison — a coverage decision made by inspecting
  missingness only, before looking at any feature-target relationship, so it does not compromise the
  pre-registration.
- IV solved from real 1-min option close prices via `vollib.black_scholes.implied_volatility`
  (Jäckel), **r = 6.5% flat, q = 0**, T = calendar days-to-expiry/365 (intraday fraction ignored — sub-1%
  effect on T for DTE>=2). ATM strike = strike nearest the snapshot spot price.
- **IV sanity cap: drop/clip any solved IV outside (1%, 100%)** before it enters any feature (Lesson
  2026-07: the INFY IV=133% blow-up). A day where the required strike is missing/illiquid (no trade in
  the snapshot window) is dropped from that day's panel, not imputed.
- Targets (computed off the SAME 09:20-09:30 snapshot price, so target and feature share one timestamp):
  - **T_ret(h):** forward log return of NIFTY spot close, snapshot-time(d) -> snapshot-time(d+h), h in {1,3,5} trading days.
  - **T_rvgap(h):** forward h-day realized vol (annualized, close-to-close on 1-min-derived daily closes)
    MINUS the ATM IV at the signal snapshot (annualized). Tests whether the surface over/under-prices
    realized vol, independent of direction.
- **Regression:** OLS of target on standardized feature, **Newey-West HAC standard errors** (lag = h, since
  h>1 horizons overlap for daily-sampled signals) run on the BUILD window only.
- **Placebo (mandatory per signal):** same regression on (a) a trading-day-shuffled version of the feature
  (breaks any real time-alignment, keeps the feature's marginal distribution) and (b) the feature lagged by
  a random 20-60 day shift. Real |t| must exceed the **95th percentile of 200 placebo draws** AND itself
  clear |t|>=2, or it is not a signal.
- **Kill criterion (pre-set, applies to every candidate):** KILL if build-window |t| < 2 on ALL horizons,
  OR real |t| does not clear its own placebo distribution, OR usable sample is too thin to support a claim
  (see Candidate 3). A signal that clears build-window but does not exist in >=2 of 3 horizons in the same
  direction is DEMOTED to "suggestive, not confirmed" — not killed, not confirmed.
- **No model fitting in this pass** (no LightGBM/kitchen-sink). This is a linear/rank-correlation cheap
  test per FACTOR_LIBRARY rule — a linear baseline must clear costs/placebo before any ML variant is even
  considered. If a candidate survives here, THAT is the trigger for a follow-on ML pass, not this one.
- **Honest trials count:** 4 candidates x (up to 2 features each) x 3 horizons x 2 targets = up to 48 cells,
  enumerated exactly in RESULTS.md; every cell run is reported, none cherry-picked.

## Candidate 1 — OTM put-call skew
- `K_put` = strike nearest to 0.98 x spot_snapshot (~2% OTM put); `K_call` = strike nearest to 1.02 x
  spot_snapshot (~2% OTM call). Fixed-strike-distance proxy for 25-delta (chosen because true delta
  requires an IV that hasn't been solved yet — circularity the prompt allows us to avoid via fixed
  distance). ~2% OOM on a weekly (DTE 2-9) instrument at ~12-16% ann. vol locates roughly a 20-30 delta
  strike — checked post-hoc for reasonableness only, not tuned.
- Expiry used: `nearest_expiry(day, min_dte=2, max_dte=9)` (front weekly, rolled forward once DTE<2 so we
  are never pricing a 0-1 DTE option where BS/skew is degenerate).
- `SKEW_t = IV_put(K_put) - IV_call(K_call)`. Sign prior [OPINION]: positive (put pricier, crash-fear) is
  the normal equity-index resting state; a STEEPENING (more positive) is hypothesized to predict lower
  forward returns / higher forward realized vol; a FLATTENING or inversion predicts the opposite. Per the
  2026-07-04 lesson, no sign is assumed as ground truth — both directions are tested and reported honestly.

## Candidate 2 — IV term structure
- ATM IV computed for three legs at the same snapshot: `E1` = front weekly (`nearest_expiry(day,2,9)`),
  `E2` = next weekly (`nearest_expiry(day,10,16)`), `E_m` = the ~monthly-tenor expiry
  (`nearest_expiry(day,21,35)`).
- `TS_near_t = IV_ATM(E2) - IV_ATM(E1)` (near-term slope). `TS_far_t = IV_ATM(E_m) - IV_ATM(E1)`.
- Prior [OPINION]: inversion (TS<0, near-dated IV above the longer leg) is a classic stress/event signal
  -> hypothesized to predict higher forward realized vol and/or negative forward returns. Contango (TS>0)
  is the normal resting state and hypothesized to carry little directional content by itself.

## Candidate 3 — OI / PCR / max-pain
- **Before any headline number:** quantify `open_interest` coverage (% of strike-day-optiontype rows with
  OI not null and not zero) by calendar year on the front-weekly file set. If continuous usable coverage
  is <12 months OR <150 trading days with a valid full-chain OI snapshot, we report coverage ONLY —
  no PCR/max-pain t-stat/verdict is computed, per the explicit honesty constraint in the task.
- If coverage clears that bar: `PCR_t` = sum(OI, puts, front-weekly chain) / sum(OI, calls, same chain) at
  the 09:20-09:30 snapshot; max-pain = strike minimizing total option-writer payout across the chain.
  Same targets/horizons/placebo/kill rule as Candidates 1-2, WITH the sample-size caveat repeated in the
  verdict regardless of the t-stat (a thin sample cannot be "confirmed" no matter what the number says).

## Candidate 4 — NIFTY vs BANKNIFTY relative value (pre-registered as the NS-3 proxy)
- **Explicit limitation stated up front [INFERENCE]:** a genuine solved "implied correlation" index needs
  the constituent-weight variance decomposition (index var = sum w_i^2 var_i + sum_{i!=j} w_i w_j rho
  vol_i vol_j), which needs per-stock IVs and current BANKNIFTY weights. That full build is out of scope
  for this cheap test (it is a Gate-2/3 follow-on if this proxy shows anything). What IS tested here is a
  **two-leg IV-spread relative-value proxy**, honestly labeled as such, not as implied correlation.
- BANKNIFTY option files here are MONTHLY only (61 files, 2021-05..2026-05); each holds that expiry's
  full multi-day life, so daily density is comparable to NIFTY's weekly files.
- `IVSPREAD_t = IV_ATM_BANKNIFTY(E_bn) - IV_ATM_NIFTY(E_nifty)` where `E_bn` = BANKNIFTY's live expiry that
  day (DTE 0-35) and `E_nifty` = the NIFTY expiry with DTE CLOSEST to `E_bn`'s DTE that day (tenor-matched,
  not calendar-date-matched, since NIFTY is weekly and BANKNIFTY monthly).
- Targets: (a) `REL_h` = forward h-day log return of BANKNIFTY minus NIFTY (does the spread predict
  relative-performance reversion); (b) forward h-day realized correlation of NIFTY & BANKNIFTY minus the
  trailing 20-day realized correlation (does the spread predict a correlation regime shift). Same
  placebo/kill rule.
- If BANKNIFTY data is found insufficient/absent for a leg, that is reported plainly, not proxied further.

## What counts as a WIN worth escalating
Per the task's explicit priority: **orthogonality over headline strength.** A candidate that clears
|t|>=2, beats its placebo, AND is weak-to-moderate in magnitude is reported as a genuine (if modest) find
if it is clearly not a repackaged price-trend proxy. A candidate that is strong but collapses versus
placebo, or that turns out to be a restatement of realized-vol persistence (RV predicting RV, which is
already known and is NOT a surface-orthogonal finding), is called out as such explicitly.
