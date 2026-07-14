# MG06 — Coupon Collector (n=4): Expected draws to see all 4 suits

**CIO consolidated answer (Rajan Mehta).** Draft + Red-Team (Nikhil Bose) integrated. Headline ships as drafted; one ancillary number corrected per Red-Team; epistemic tag fixed.

---

## Answer

**E[T] = 25/3 ≈ 8.3333 draws** (exact fraction **25/3**; decimal 8.3̄).

## Derivation

This is the coupon-collector problem with n = 4 equally likely, independent coupons (suits).

Track the state by the number of DISTINCT suits already seen. Split T into the waits between milestones:

T = T0 + T1 + T2 + T3,

where Tk is the number of draws to go from k distinct suits to k+1. When you already hold k distinct suits, each new draw is "new" with probability p_k = (4 − k)/4, independently, so Tk ~ Geometric(p_k) with mean 1/p_k = 4/(4 − k).

By linearity of expectation:

E[T] = Σ_{k=0}^{3} 4/(4 − k) = 4/4 + 4/3 + 4/2 + 4/1 = 1 + 4/3 + 2 + 4 = 7 + 4/3 = **25/3**.

Equivalently, the standard identity: E[T] = n·H_n = 4·(1 + 1/2 + 1/3 + 1/4) = 4·(25/12) = 100/12 = **25/3**.

Two independent routes give the same value; linearity of expectation holds regardless of dependence, so there is no hidden independence assumption in the headline. This is a closed form, not a backtest — no lookahead, measurement, or selection surface. **The headline ships.**

## Dispersion (Red-Team-corrected)

The draft's desk note carried a wrong variance (12.9 / SD 3.6). Corrected and twice-verified:

**Var[T] = 130/9 ≈ 14.44, SD ≈ 3.80.**

Stage-by-stage, using Var[Tk] = (1 − p_k)/p_k²:

| k | p_k | Var[Tk] |
|---|-----|---------|
| 0 | 1   | 0 |
| 1 | 3/4 | 4/9 ≈ 0.444 |
| 2 | 1/2 | 2 |
| 3 | 1/4 | 12 |
| **Σ** | | **130/9 ≈ 14.44** |

Independent cross-check via the closed form: Var = n²·Σ_{k=1}^{n} 1/k² − n·H_n = 16·(1 + 1/4 + 1/9 + 1/16) − 25/3 = 22.778 − 8.333 = 14.444 = 130/9. Confirmed.

## Desk read (why the shape, not just the number, matters)

The last-suit wait (mean 4, variance 12) is the dominant contributor — **12 of 14.44 ≈ 83% of total variance sits in the final stage alone.** The distribution is right-skewed: the mean of 8.33 hides a fat right tail driven entirely by the wait for the last coupon.

This is the coupon-collector analogue of our per-trade discipline: the honest accounting unit is the sum of the four sub-waits, because collapsing them into one averaged number would conceal exactly where the risk lives (the tail-heavy final stage). The same "sum of geometrics" structure is why we judge strategies on per-trade edge + tail, never on a single collapsed headline — the last-stage wait is our analogue of the calm-looking-name blowup: low-probability per draw, dominant in variance.

## Epistemic tags

- Result and derivation: **[INFERENCE]** (closed-form, no dataset — the draft's original [DATA] tag was internally contradictory since it also states "no data dependency"; corrected).
- Desk read: **[OPINION]**.

## Audit trail

- Headline 25/3: VERIFIED (two routes, agree exactly).
- Variance 130/9: draft was FAKE (12.9/3.6, single arithmetic slip); corrected and cross-checked two ways.
- Both fraction forms given (E[T]=25/3, Var=130/9) to match the exact-fraction framing.
