# Expected Distinct Values: n Draws from {1,...,n} with Replacement

## Problem
Draw n times uniformly at random **with replacement** from the set {1, 2, ..., n}. Let D = number of distinct values observed. Find E[D] and lim_{n→∞} E[D]/n.

---

## Derivation

**Indicator Variables:**
For each value i ∈ {1, 2, ..., n}, define:
$$X_i = \begin{cases} 1 & \text{if value } i \text{ appears at least once} \\ 0 & \text{otherwise} \end{cases}$$

Then: $D = X_1 + X_2 + \cdots + X_n$

**Expectation by Linearity:**
$$E[D] = E[X_1] + E[X_2] + \cdots + E[X_n]$$

**Probability Calculation:**
By symmetry, $P(\text{value } i \text{ appears}) = P(\text{value } 1 \text{ appears})$ for all i.

$$P(\text{value } i \text{ appears at least once}) = 1 - P(\text{value } i \text{ never appears})$$

$$= 1 - P(\text{all } n \text{ draws miss } i)$$

$$= 1 - \left(\frac{n-1}{n}\right)^n = 1 - \left(1 - \frac{1}{n}\right)^n$$

**Expected Value:**
$$E[X_i] = 1 - \left(1 - \frac{1}{n}\right)^n$$

Since all n indicators have the same expectation:
$$E[D] = n \left[ 1 - \left(1 - \frac{1}{n}\right)^n \right]$$

**Asymptotic Limit:**
Using the fundamental limit $\lim_{n \to \infty} \left(1 - \frac{1}{n}\right)^n = \frac{1}{e}$:

$$\lim_{n \to \infty} \frac{E[D]}{n} = \lim_{n \to \infty} \left[1 - \left(1 - \frac{1}{n}\right)^n\right] = 1 - \frac{1}{e} = \frac{e-1}{e}$$

---

## Final Answers

**Exact Closed-Form Expression for E[D]:**
$$\boxed{E[D] = n \left(1 - \left(1 - \frac{1}{n}\right)^n\right)}$$

Alternative form:
$$\boxed{E[D] = n \left(1 - \left(\frac{n-1}{n}\right)^n\right)}$$

**Exact Limit of E[D]/n as n → ∞:**
$$\boxed{\lim_{n \to \infty} \frac{E[D]}{n} = 1 - \frac{1}{e} = \frac{e-1}{e}}$$

Numerically: $\frac{e-1}{e} \approx 0.6321$

---

## Interpretation
When drawing n times with replacement from n values, we asymptotically observe a fraction $(1 - e^{-1}) \approx 63.21\%$ of all possible values. The remaining ~36.79% are never encountered in n draws.
