# PRE-REGISTRATION — Long-dated / multi-week premium selling for income
Owner: Vikram Shah (FM, Derivatives & Short-Vol book). Written BEFORE the backtest runs
(queued to `BACKTEST_QUEUE_20260730/queue/111_longdated_selling.py`), per D-035. Do not tune
after seeing results — any change after this file is a NEW pre-registration.

## 1. Question
Does selling a LONGER tenor LESS OFTEN beat selling a SHORTER tenor MORE OFTEN, after real
costs, on a risk-adjusted (not raw-CAGR) basis? Secondary: naked-10%-margin vs hedged-5%-margin;
does the IV-percentile-high SELL gate (reversal finding from INVERSE_VRP_NICHE) genuinely help?

## 2. Data (verified today, [DATA])
- `Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist/fo_idx_{2011..2026}.parquet`. Filter
  `SYMBOL=='NIFTY' & INSTRUMENT=='OPTIDX'`. Columns used: EXPIRY_DT, STRIKE_PR, OPTION_TYP,
  CLOSE, SETTLE_PR (NEVER read as price — landmine #9), CONTRACTS, TIMESTAMP.
- **Underlying/spot proxy:** official `Nifty 50` daily close from
  `datasets/index_daily/nse_official_all_indices.parquet` for date >= 2016-01-01 (verified
  2,608 rows, 2016-2026). For date < 2016-01-01 (2011-2015, no official spot series on disk),
  proxy = NIFTY near-month FUTIDX close from the SAME bhavcopy file (always available, PIT-safe,
  same source as the options). **Validated basis 2016-2019 overlap** (futures near-month close
  vs official spot close, n=983 days): mean 0.179%, mean |basis| 0.194%, max |basis| 0.81%.
  [INFERENCE] this bounds the 2011-2015 proxy error to sub-1% on all but tail days — immaterial
  for strike selection several sigma OTM, minor for expiry-day intrinsic settlement in that slice
  only. Flagged, not hidden.
- **CONTRACTS>0 gate on every leg, every day** (41% of rows in a sampled year are listed-but-
  untraded model prices per SHARED_CONTEXT). A day/strike/expiry with CONTRACTS==0 is treated as
  NO PRICE (forward-filled from last valid print for path continuity, but NEVER used to trigger
  an exit rule — avoids phantom triggers off stale model prices).
- **Reused, not rebuilt:** `INVERSE_VRP_NICHE_20260729/daily_vol_series.csv` (1,238 days,
  2021-05-24..2026-06-03, real BS-backout ATM IV + expanding no-lookahead `iv_pct`/`rv_pct`).
  The IV-gate test is necessarily restricted to this window — stated as a limitation, not hidden.

## 3. Split (this arm's OWN split — different from the 1-min intraday split in SHARED_CONTEXT,
because a ~12-26 trade/yr strategy needs multiple YEARS of held-out data for real power, not months)
- **BUILD (selection allowed):** 2011-01-01 .. 2023-12-31 (13y).
- **HELD-OUT (report only, zero selection):** 2024-01-01 .. 2026-06-30 (2.5y) — includes the
  named 2024-09 stress window and the current period. Tail-event reporting (2015-16, 2018, 2020
  COVID) is DESCRIPTIVE (shown for both windows) and is not used to pick parameters — reporting
  is not selection, but this is stated explicitly so the distinction is auditable.
- Config selection (best tenor/delta/structure/management) is made on BUILD-window risk-adjusted
  return ONLY. The held-out number for that config is never used to re-pick.

## 4. Test grid (pre-registered, exact trials counted)
Core grid, run on BOTH build and held-out windows:
- **Tenor** (3): biweekly target DTE 12 (band 7-20), monthly target 30 (band 20-45),
  bimonthly target 60 (band 45-100) — bands match the SHARED_CONTEXT liquidity-verified table.
- **Strike/delta** (3): target |delta| 0.10 / 0.15 / 0.25. Delta is a MODEL delta: analytic BS
  delta solved for strike using **realized vol as the sigma input** (trailing 20-session
  annualized close-to-close RV of the underlying proxy, shifted 1 day, no lookahead), r=6.5% flat
  [INFERENCE, matches existing firm convention in build_iv_rv_series.py]. **Not a market-IV
  delta** — daily bhavcopy CLOSE on thin (low-CONTRACTS) far-OTM strikes is too noisy to invert
  reliably strike-by-strike across 16 years; this is disclosed, not hidden. Nearest strike with
  CONTRACTS>0 that day is chosen (search outward if the exact target strike is untraded).
- **Structure** (2): naked short strangle (margin = 10% x spot x lot, ONE figure per position —
  not doubled per leg, matching the firm's own ~12% strangle-notional convention in
  COST_STANDARDS and how real SPAN offsets opposing legs) vs iron condor / same-expiry hedged
  (buy a wing at short_strike +/- ~3% of spot, nearest available CONTRACTS>0 strike; margin = 5%
  x spot x lot, defined-risk). Both margins DYNAMIC (scale with spot at entry), never flat rupee.
- **Management** (3): hold-to-expiry (cash-settle at INTRINSIC from the underlying proxy, never
  from SETTLE_PR); buy back at 50% of credit captured; stop-out at 2x credit paid.
- Grid = 3 x 3 x 2 x 3 = **54 base configs**.

Overlays (applied ONLY to the single best base config by BUILD-window risk-adjusted return,
+3 more trials, kept lean rather than combinatorially exploding — an honest trials ledger, not a
hunt):
- **IV-percentile-high SELL gate** (the session's strongest reversal lead): enter only if
  `iv_pct >= 90` (top decile) on `daily_vol_series.csv`'s day, restricted to that file's coverage
  window (2021-05-24..2026-06-03) — baseline-vs-gated compared on the SAME restricted window.
- **Realized-vol regime skip**: skip entries where the strategy's own self-computed RV sits in
  its top decile (expanding no-lookahead percentile, min 60 prior obs, computed over the FULL
  2011-2026 underlying-proxy series — independent of the IV-gate's shorter window).
- **Both stacked** (IV-gate AND RV-skip together), on the IV-gate's restricted window.

**Total trials this arm: 57.** Logged to the firm trials ledger
(`OVERFIT_AUDIT_20260729/TRIALS_LEDGER.csv`) after the run — not before, since trials are
counted by what was actually evaluated, but the count itself (57) is fixed NOW, before results
exist, so it cannot grow post-hoc.

**Explicitly NOT tested, with reason (do not silently skip — say so):** `sweep_intraday_reclaim`
(t=-3.64 fade) as an entry filter. That signal was measured on 15-min INTRADAY bars predicting
next-few-bar continuation; there is no established transmission channel to a 10-60 DAY option-
selling entry decision, and force-fitting a daily-bar analog not actually measured anywhere would
be fabricating a result, not testing one. Flagged as a genuine follow-up candidate for the
biweekly tenor specifically (shortest hold, closest in spirit), not run here.

## 5. Costs (SHARED_CONTEXT mandate costs, authoritative for this arm)
- Rs 25/lot/side brokerage-equiv, applied per LEG per SIDE (strangle = 2 legs x 2 sides = 4
  leg-executions per round trip; condor = 4 legs x 2 sides = 8 — the extra legs of the hedged
  structure are charged for, this is exactly the cost/margin tradeoff being measured).
- Bid-ask slippage 0.4 pt/side (midpoint of the given 0.25-0.5 range), always AGAINST us (sell
  at close-0.4, buy at close+0.4), applied per leg-execution.
- **STT-on-exercise add-on** (COST_STANDARDS: "0.125% of intrinsic on exercise — avoid exercise;
  close positions"), applied ONLY to hold-to-expiry legs that finish ITM (intrinsic > 0), on top
  of the standard exit brokerage. This is a real, approved-rate cost the mandate's flat Rs25/lot
  figure does not capture and that a naive hold-to-expiry backtest would miss — reported BOTH
  with and without so its bite is visible, not buried in a caveat.

## 6. Margin & sizing convention (must be legible for later reproduction)
Return series = per-trade return on that trade's OWN dynamic margin, compounded sequentially
(NAV_i = NAV_(i-1) x (1+ret_i)) — standard convention for a fully-margin-deployed, cycled book,
and the same convention implied by S1-F's "corrected-margin sim" CAGR. A parallel FIXED-1-LOT
rupee P&L series is also kept purely for concrete tail reporting (worst day/month in rupees).

## 7. Kill / promote criteria (fixed now)
- KILL a (tenor,structure) pair if held-out NET Sharpe <= 0, or held-out NET CAGR <= 0, or
  held-out max single-month loss > 3x the build-window's worst month (regime break).
  Any statistically inconclusive but non-negative reading is a "resurrection candidate", not
  a kill nor a promotion (per the low-t power-aware re-screen convention) — will be labeled so.
- Nothing here is "certified" regardless of headline numbers — DSR/PBO on the 57-trial family
  and Red Team review are still owed before any IC promotion (2026-07-04 lesson: certification
  precedes sizing).

## 8. Reporting requirements (fixed now, cannot be softened after seeing numbers)
Gross AND net; monthly win-rate on both; CAGR/maxDD/Calmar/Sharpe/PF/NW-t on margin-based
returns; held-out block reported in full; worst single day and worst month in rupees AND as %
of margin capital; 2020 COVID / 2018 / 2015-16 / 2024-09 slices shown explicitly; comparison
table vs S1-F (12.57% CAGR / -4.44% MDD / Calmar 2.83 / Sharpe 2.15 / PF 2.21, itself NOT DSR/PBO
cleared); exact trials count (57) restated in the results.
