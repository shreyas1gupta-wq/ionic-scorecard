This is the coupon collector problem with n = 4, answerable directly by decomposing T into geometric waiting times.

## Derivation

Write T = T₁ + T₂ + T₃ + T₄, where Tᵢ is the number of draws needed to see a *new* suit after i − 1 distinct suits have appeared.

While you hold i − 1 distinct suits, each draw is new with probability p = (4 − (i−1))/4, so Tᵢ is geometric with mean 4/(4 − i + 1):

- T₁: p = 4/4 → E[T₁] = 1
- T₂: p = 3/4 → E[T₂] = 4/3
- T₃: p = 2/4 → E[T₃] = 2
- T₄: p = 1/4 → E[T₄] = 4

By linearity of expectation:

E[T] = 1 + 4/3 + 2 + 4 = 4·(1 + 1/2 + 1/3 + 1/4) = 4·H₄ = **25/3 ≈ 8.3333…**

Sanity check: 4·H₄ = 4·(25/12) = 25/3, and the term-by-term sum 12/12 + 16/12 + 24/12 + 48/12 = 100/12 = 25/3 agrees; the decimal 8.3̅ matches the known coupon-collector value for n = 4.

result: Expected draws to see all 4 suits is E[T] = 25/3 ≈ 8.3333 (coupon collector, 4·H₄).