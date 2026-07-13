# MG05 — Expected number of distinct values (opus)

## Problem
Draw `n` times uniformly at random **with replacement** from `{1, 2, ..., n}`.
Let `D` = number of DISTINCT values observed. Find exact `E[D]` and `lim_{n→∞} E[D]/n`.

## Derivation (indicator method)
For each value `i ∈ {1,...,n}`, define the indicator
`X_i = 1` if value `i` appears at least once among the `n` draws, else `0`.

Then `D = Σ_{i=1}^{n} X_i`, so by linearity of expectation
`E[D] = Σ_{i=1}^{n} E[X_i] = Σ_{i=1}^{n} P(value i appears at least once)`.

Each single draw misses value `i` with probability `(1 - 1/n)`.
The `n` draws are independent, so value `i` is missed by ALL `n` draws with probability `(1 - 1/n)^n`.
Hence
`P(X_i = 1) = 1 - (1 - 1/n)^n`.

By symmetry this is identical for every `i`, so summing over the `n` values:

```
E[D] = n · [ 1 - (1 - 1/n)^n ]
```

## Limit of E[D]/n
```
E[D]/n = 1 - (1 - 1/n)^n
```
Since `(1 - 1/n)^n → 1/e` as `n → ∞`,
```
lim_{n→∞} E[D]/n = 1 - 1/e ≈ 0.632120558...
```

## Sanity checks
- `n = 1`: `E[D] = 1·(1 - 0) = 1`. Correct — one draw from `{1}` always gives 1 distinct value.
- `n = 2`: `E[D] = 2·(1 - (1/2)^2) = 2·(3/4) = 1.5`. Direct check: draws (1,1),(2,2) give 1 distinct; (1,2),(2,1) give 2 distinct; average = (1+1+2+2)/4 = 1.5. Correct.
- Ratio is monotonically decreasing toward `1 - 1/e ≈ 0.6321` (approached from above, since `(1-1/n)^n` increases up to `1/e`).

## FINAL ANSWERS (unambiguous)
- **Exact closed form:**  `E[D] = n · ( 1 − (1 − 1/n)^n )`
- **Exact limit:**  `lim_{n→∞} E[D]/n = 1 − 1/e`  (≈ 0.6321205588)
