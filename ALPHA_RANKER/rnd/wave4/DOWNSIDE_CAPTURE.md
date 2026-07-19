# W6DC — Trailing Downside-Capture Ratio (Sensitivity Report)

Owner: Dr. Sameer Bhat (Overfit & Sensitivity Analyst). Principal request via ALPHA_RANKER.
Run: 2026-07-17. Panel: `rnd/panel/panel_long.parquet` (249 monthly dates, 969 symbols, 2005-04→2025-12).
Build script: `rnd/wave4/w6dc_build.py`. Honest-DSR follow-up: `rnd/wave4/w6dc_support/w6dc_honest_dsr.py`.
Cards: `rnd/cards/W6DC_dcr_{1m,3m,6m}_{1M,1Y,5Y}.json` (9 cards, family="W6DC", one code path = `rnd/lib/harness.py`).

## Construct [DATA/build, trailing-only, verified no lookahead]
At each monthly rebalance date d, using only trading days ≤ d: down-days = market
daily log-return < 0 within the trailing N-day window (N=21/63/126 for 1m/3m/6m).
`downside_capture = (compounded stock return over down-days) / (compounded market
return over down-days)`. Guards (pre-registered): ≥5 down-days in window, |market
down-cum| ≥ 0.5%, full trailing history present. Implemented as a vectorized
cumsum-diff (no rolling-window lookahead possible by construction — verified: every
window value at date d references only `cumsum[d] - cumsum[d-N]`).

**Sign convention**: raw factor = downside_capture (higher = amplifies downside).
Harness's reported `ic_mean`/`long_short` are on this raw factor (ascending
decile: top=high-DC/amplifying, bottom=low-DC/defensive). The **tradeable**
defensive trade is long-bottom/short-top = **−1× the reported long_short figure**.
IC is negative throughout → low downside-capture DOES rank-predict higher forward
returns (consistent with hypothesis), but see PBO/skew below before reading that
as a real edge.

## Per-window results (1M forward horizon, resid basis — headline; 1Y/5Y in cards, same pattern, stronger nominal IC, same PBO failure)

| window | IC_mean | IC_IR | lag_delta (≤0.25 pass) | placebo_IC (≤0.02 pass) | PBO (≤0.50 pass) | corr vs BAB | corr vs trailing-vol |
|---|---|---|---|---|---|---|---|
| 1m | −0.031 | **−0.267** | 0.444 **FAIL** | −0.001 pass | 0.983 **FAIL** | −0.43 (distinct) | −0.29 (distinct) |
| 3m | −0.057 | **−0.419** | 0.053 pass | 0.001 pass | 0.965 **FAIL** | −0.62 **REPACKAGED** | −0.39 (distinct) |
| 6m | −0.067 | **−0.446** | 0.057 pass | 0.001 pass | 0.883 **FAIL** | −0.75 **REPACKAGED** | −0.46 (distinct) |

At 1Y/5Y horizons IC_IR strengthens further (up to −2.28 at 6m/5Y) but PBO stays
0.72–0.99 at every single cell (9/9) — **direction-invariant** (verified by
recomputing PBO on the flipped tradeable series: identical to 9 decimal places,
confirming this is not a sign-convention artifact).

DSR: reported 0.000 in all 9 cards under the GLOBAL trial counter (666–674,
inflated by the rest of the research program — a documented harness distortion,
see `harness.py` CONSOLIDATION note). Recomputed with the honest **family-only**
trial count (n=9): still ≈0 (1e-22 to 1e-203). This is because the realized
per-period Sharpe here (0.09–0.76, unannualized) sits below the DSR formula's
expected-max-Sharpe floor even at only 9 trials (~1.52 in the same units) — DSR
is **structurally uninformative at this observation count/scale** regardless of
trial-count honesty; PBO is the decisive, non-artifactual failure metric here.

## Regime-conditional test (does it protect specifically in bear?)
`regime_trend` IC breakdown (1M horizon):

| window | bear | bull | sideways |
|---|---|---|---|
| 1m | +0.017 | −0.057 | −0.008 |
| 3m | −0.0002 | −0.083 | −0.034 |
| 6m | −0.002 | −0.095 | −0.042 |

**The effect is ~zero in bear regime and concentrated in bull/sideways** — the
opposite of the hypothesis. Answer to "protects in bear": **no**.

## Skew / crash-month / outlier concentration
Tradeable-direction (flipped) skew is strongly **positive** (1m: 1.22, 3m: 4.40,
6m: 5.37) with extreme kurtosis (26–51) — but tracing the actual extreme dates
shows the whole distribution is dominated by ~5 months, and **none of them are
2020 or 2022**: worst losses cluster at 2009-03/04 (post-GFC V-recovery, where
defensive names lagged hard) and 2011-12; best gains cluster at 2006-10, 2007-09,
2008-02/05 (pre-GFC/into-GFC). Named crash-month means (raw, i.e. −1× for
tradeable) are small: 2020 = −0.018/−0.007/+0.004 (1m/3m/6m), 2022 = −0.008/
−0.011/−0.011 — flipped to tradeable that's roughly +0.4% to +1.8%/month, modest
and mixed-sign at 6m/2020. **The headline skew/kurtosis is an early-history
(2006–2012, ~200–340-name universe) artifact, not COVID/2022 crash protection.**

Era-split IC (first/second half of the 249-date grid) keeps the same sign
throughout (e.g. 6m: −0.089 → −0.045) and drop-one-year IC is narrow-ranged —
i.e. the **rank-order (IC)** signal looks era-stable, but the **P&L magnitude**
is not: this is the mechanism split Sameer flags routinely — a stable IC can
still sit on top of a return series whose economic content is 5 extreme months.

## Orthogonality
1m stays under the 0.6 repackaging line vs both BAB and trailing-vol. 3m and 6m
cross 0.6 vs BAB (−0.62, −0.75) — **at longer lookbacks this is functionally the
existing defensive_BAB leg, not a new signal**. All three windows stay under 0.6
vs the independent trailing-vol construction.

## Verdict: **OVERFIT**
Reasons (Gate-4 automatic-FAIL criteria, ≥1 met at every window):
- PBO 0.72–0.99 (≥0.50 kill) at all 9 window×horizon cells, sign-flip-invariant
  (verified) — the single most fragile assumption: **the whole apparent edge
  reduces to ~5 extreme months in the 2006–2012 early-history/thin-universe
  period, none of which are the crash episodes (2020/2022) the hypothesis was
  actually testing for.**
- 3m/6m: corr vs BAB > 0.6 → repackaged, not incremental.
- 1m: lag-test fails at the 1M horizon (0.444 > 0.25).
- Regime-conditional test contradicts the hypothesis (protects in bull, not
  bear).
Recommendation: KILL as a standalone signal for ALPHA_RANKER. Do not promote;
do not size. If revisited, pre-register a purged/embargoed post-2012 subsample
test before evaluating, since the current full-history result is dominated by a
period the current 969-name/PIT-earnings-audited universe does not resemble.
