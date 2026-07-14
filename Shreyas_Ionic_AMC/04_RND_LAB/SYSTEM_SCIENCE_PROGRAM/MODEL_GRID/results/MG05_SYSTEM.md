# MG05 — E[D] for n draws with replacement from {1,…,n}

**CIO consolidated final answer (Rajan Mehta, E-001).** Draft by desk, adversarial review by Nikhil Bose (E-014). Verdict: **REAL / CONFIRMED** — deductive proof, no data lineage, no fragility. Draft was correct as written; below folds in the three robustness closures the Red Team flagged (the m=k=n contingency, the finite-n approach behavior, and the epistemic tag).

**Epistemic tag: [PROVEN]** (deductively certain mathematical fact — not [INFERENCE], per EPISTEMIC_CONDUCT).

---

## Problem
Draw n times, i.i.d. uniform **with replacement**, from {1,…,n}. Let D = number of **distinct** values observed. Give exact E[D] and the exact limit of E[D]/n.

## Derivation (indicator + linearity)
This is the classical **occupancy** problem: n balls into n bins, count non-empty bins.

For each value i ∈ {1,…,n} define X_i = 1 if i appears in at least one of the n draws, else 0. Then D = Σᵢ Xᵢ.

- A single draw misses i with probability (n−1)/n = 1 − 1/n.
- Draws are independent, so i is never drawn across all n draws with probability (1 − 1/n)ⁿ.
- Hence P(Xᵢ = 1) = 1 − (1 − 1/n)ⁿ, identical for every i by symmetry.

Linearity of expectation needs **no independence** among the Xᵢ (they are in fact negatively correlated), so:

**E[D] = Σᵢ E[Xᵢ] = n · [ 1 − (1 − 1/n)ⁿ ].**

## Exact closed form
```
E[D] = n ( 1 − (1 − 1/n)ⁿ )  =  n − (n−1)ⁿ / n^(n−1)
```
The two forms are **provably identical** (not an approximation):
n·(1−1/n)ⁿ = n·((n−1)/n)ⁿ = n·(n−1)ⁿ/nⁿ = (n−1)ⁿ/n^(n−1).

General occupancy statement (the assumption the elegance rides on): for **m** draws over **k** categories, E[D] = k·(1 − (1 − 1/k)^m). The result above is the special case **m = k = n**. Also assumes **with replacement** and a **uniform** distribution — a non-uniform law strictly lowers E[D] (Schur-concavity / Jensen).

## Verification (placebos)
- n=1: 1·(1−0) = **1** ✓ (only value 1 exists).
- n=2: 2·(1−1/4) = **1.5** ✓ (enumerate 4 outcomes).
- n=3 (non-degenerate — the real off-by-one test): 3·(1−(2/3)³) = 3·19/27 = **19/9 ≈ 2.111**. Full 27-outcome enumeration: 3 all-same→1, 18 two-distinct→2, 6 all-different→3 ⇒ (3·1+18·2+6·3)/27 = 57/27 = **19/9** ✓ exact match.

## Limit of E[D]/n
E[D]/n = 1 − (1 − 1/n)ⁿ, and (1 − 1/n)ⁿ → e⁻¹, so:

```
lim_{n→∞} E[D]/n = 1 − 1/e ≈ 0.6321205588…
```
(Not the 1/e ≈ 0.3679 complement trap — the draft avoided it.)

**Finite-n behavior (Red-Team closure).** (1−1/n)ⁿ increases to 1/e from below, so E[D]/n **decreases to 1 − 1/e from above** — every finite n exceeds 0.63212 (n=2: 0.75, n=3: 0.7037, …). With ln(1−1/n) = −1/n − 1/(2n²) − …:
```
(1 − 1/n)ⁿ = e⁻¹ ( 1 − 1/(2n) + O(1/n²) )
E[D]/n     = (1 − 1/e) + 1/(2e·n) + O(1/n²),   1/(2e) ≈ 0.18394
```
e.g. n=100 ⇒ ≈ 0.63212 + 0.00184 ≈ 0.63396.

---

## FINAL ANSWERS (unambiguous)
1. **Exact:** E[D] = n(1 − (1 − 1/n)ⁿ) = n − (n−1)ⁿ/n^(n−1).  *(= k(1 − (1 − 1/k)^m) with m = k = n.)*
2. **Limit:** lim_{n→∞} E[D]/n = **1 − 1/e ≈ 0.6321205588**, approached **monotonically from above** with E[D]/n = (1 − 1/e) + 1/(2e·n) + O(1/n²).
