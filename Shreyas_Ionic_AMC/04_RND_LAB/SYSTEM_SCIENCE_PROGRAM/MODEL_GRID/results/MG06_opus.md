# MG06 — Coupon Collector (4 suits): Expected draws to see all 4

## Answer

**E[T] = 25/3 ≈ 8.3333...**

## Setup

This is the coupon-collector problem with `n = 4` equally likely,
independent categories (suits). Let `T` = number of draws until all 4
distinct suits have appeared at least once.

## Derivation (stage decomposition)

Split `T` by how many distinct suits are already collected. Suppose you
currently hold `k` distinct suits (`k = 0, 1, 2, 3`). On any single draw
the probability the card is a *new* suit is

    p_k = (4 - k) / 4

The number of draws needed to go from `k` distinct to `k+1` distinct is
therefore Geometric with success probability `p_k`, whose expectation is
`1 / p_k = 4 / (4 - k)`.

Write `T = X_0 + X_1 + X_2 + X_3`, where `X_k` is the draws spent in
stage `k`. These stages are independent, and by linearity of expectation:

    E[T] = sum_{k=0}^{3} 4/(4 - k)
         = 4/4 + 4/3 + 4/2 + 4/1
         = 1 + 4/3 + 2 + 4

Combining over a common denominator of 3:

    E[T] = (3 + 4 + 6 + 12) / 3 = 25/3

## Equivalent closed form (harmonic number)

    E[T] = n * H_n,   with n = 4,  H_4 = 1 + 1/2 + 1/3 + 1/4 = 25/12
    E[T] = 4 * 25/12 = 100/12 = 25/3

## Result

| Quantity | Exact | Decimal |
|---|---|---|
| E[T] | 25/3 | 8.33333... |

Per-stage expected draws: 1 (first new suit, always), 4/3, 2, 4
(the last suit is the slow one, taking 4 draws on average).
