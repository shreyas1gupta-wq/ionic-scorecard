# MG05 — Distinct Values Under Sampling With Replacement (Sonnet)

## Problem
Draw n times, uniformly at random with replacement, from {1, 2, ..., n}.
Let D = number of distinct values observed. Find E[D] in closed form and
lim_{n->infinity} E[D]/n.

## Derivation

For each value i in {1, ..., n}, define the indicator
    X_i = 1 if value i is observed at least once in the n draws, else 0.

Then D = X_1 + X_2 + ... + X_n, so by linearity of expectation:
    E[D] = sum_{i=1}^n E[X_i] = sum_{i=1}^n P(value i observed at least once).

For a single draw, P(draw != i) = (n-1)/n = 1 - 1/n. Since the n draws are
independent (sampling with replacement),
    P(value i never observed in n draws) = (1 - 1/n)^n.

Hence
    P(value i observed at least once) = 1 - (1 - 1/n)^n,

which is the same for every i by symmetry. Therefore:

    E[D] = n * [1 - (1 - 1/n)^n].

## Limit as n -> infinity

    E[D]/n = 1 - (1 - 1/n)^n.

Using the standard limit (1 - 1/n)^n -> e^{-1} as n -> infinity:

    lim_{n->infinity} E[D]/n = 1 - 1/e.

## Final Answers

- Exact closed form:  **E[D] = n [ 1 - (1 - 1/n)^n ]**
- Limit:  **lim_{n->infinity} E[D]/n = 1 - 1/e ≈ 0.6321**
