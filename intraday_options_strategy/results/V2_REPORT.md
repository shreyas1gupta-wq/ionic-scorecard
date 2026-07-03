# V2 ENSEMBLE — first run findings (2026-06-11)

## Numbers (1-lot sleeve sims, research-prior parameters, NO grid fitting)
| sleeve | trades | WR | PF | avg P&L/lot | SL rate | note |
|---|---|---|---|---|---|---|
| S2 range short straddle | 552 | 40.2% | 0.28 | −₹508 | 4.5% | 95% exit EOD; PT(50% capture) never reached |
| S3 0DTE short straddle | 222 | 17.6% | 0.31 | −₹712 | **80.6%** | combo SL 25% far too tight at 0DTE gamma |
| S4 trend rider (long, partial+trail) | 227 | 46.7% | 0.98 | −₹18 | 23.8% | ~breakeven after costs; partial/trail works |

Daily P&L correlations: |ρ| ≤ 0.06 across all pairs — the diversification
thesis holds. Portfolio layer correctly de-allocated losing sleeves (Kelly
cap → 0), ending FULL period at −0.06% CAGR with 1.06% maxDD — the guards
work; there is simply no edge to size up *in this synthetic world*.

## THE core finding — synthetic pricing bias (read before tuning anything)
BS-at-VIX premiums are SYSTEMATICALLY CHEAP at short DTE:
1. Real short-DTE ATM IV trades ABOVE India VIX (event/smile pricing; expiry
   day commonly 1.3–2× VIX equivalent). Our sim sells at VIX → sellers start
   underpaid by construction.
2. VIX variance budget includes OVERNIGHT gaps; an intraday seller
   (09:20→15:00) bears only intraday realized vol but our BS decay credits
   only calendar-pro-rata VIX time. Measured intraday realized (~0.55%) >
   calendar-pro-rata (~0.43%) → simulated sellers lose ≈ the difference.
3. Conversely long-option sleeves get premiums slightly too cheap → v1/S4
   results are mildly OPTIMISTIC.
⇒ Short-premium sleeves (S2/S3) CANNOT be validated or rejected on this
dataset. They need REAL option prices.

## What this means for the project
- S4 is the only sleeve whose sim is conservative-ish and it's ~breakeven →
  candidate for small WFO (gates: ADX 25/28/32 × bias 0.67/1.0 × partial
  30/35/40) AFTER real-pricing calibration, not before.
- Next data milestone (HIGH VALUE): NSE F&O bhavcopy (daily EOD option
  prices per strike/expiry, free on nseindia.com archives; Kaggle mirrors
  exist — search "nifty options chain historical EOD bhavcopy"). Use it to:
  (a) measure real ATM IV vs VIX by DTE bucket (the "IV multiplier curve"),
  (b) re-price S2/S3 entries with calibrated IV: sigma_used = m(DTE) × VIX,
  (c) sanity-check our BS premiums vs actual traded premiums on overlap days.
- Until then: do NOT spend tokens tuning S2/S3 parameters — any result is an
  artifact of the pricing bias.

## BREAK-EVEN IV ANALYSIS (run_iv_sweep.py) — the decisive result
Instead of guessing, we swept the IV multiplier m = (real ATM IV / India VIX)
and re-priced every short-straddle entry+exit at sigma = m × VIX on the REAL
Nifty path. Break-even m = smallest m giving Profit Factor ≥ 1:

| sleeve | IS break-even m | OOS break-even m | PF @ m=1.5 (OOS) | PF @ m=1.8 (OOS) |
|---|---|---|---|---|
| S2 weekly straddle, intraday hold | >1.8 (off grid) | 1.80 | 0.93 | 1.41 |
| S3 0DTE expiry straddle | 1.50 | 1.50 | 1.19 | **2.61** (WR 61%) |

**Verdict — S2 REJECTED on fundamentals.** A 5–7 DTE straddle held only
intraday captures tiny theta but full intraday gamma; it needs IV ~80% above
VIX to pay. Real ATM weekly IV runs only ~5–15% above VIX → no plausible edge.
Holding a weekly overnight (not allowed here) is where its theta lives.

**Verdict — S3 (0DTE) is the PRIME CANDIDATE.** Break-even m ≈ 1.50, and
critically **IS and OOS agree (both 1.50) → not overfit**. Expiry-day ATM
options are well known to trade at IV far above the 30-day VIX (huge same-day
gamma/event premium); m in the 1.3–2.0 range is realistic. At m=1.8, OOS PF
2.6 / WR 61% — a real, sizable edge IF real expiry-day IV is that rich.

**This is the whole project's pivot.** The retail-accessible alpha in Nifty
options is expiry-day short premium (VRP harvesting), not intraday direction.
But it CANNOT be confirmed on synthetic prices — m_real must be MEASURED from
real option data before any capital. That is now the #1 task.

## Portfolio infrastructure validated
vol-parity weights, trailing-Sharpe kill switch, 0.25-Kelly cap, margin cap,
DD governor with hysteresis — all exercised and behaving correctly (they
zeroed exposure to negative-edge sleeves with no lookahead).
