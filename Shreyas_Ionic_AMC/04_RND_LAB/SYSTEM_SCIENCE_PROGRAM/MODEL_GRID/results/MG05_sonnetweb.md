Draw n times with replacement from {1,...,n}; D = number of distinct values observed.

**Derivation.** For each value i ∈ {1,...,n}, let I_i = 1 if i appears at least once in the n draws, else 0. Then D = Σ I_i, and by linearity of expectation E[D] = Σ E[I_i] = n·P(a fixed value appears at least once).

P(value i never drawn in one trial) = 1 − 1/n. Across n independent draws: P(never drawn) = (1 − 1/n)^n. So P(drawn at least once) = 1 − (1 − 1/n)^n.

**E[D] = n·[1 − (1 − 1/n)^n]** (exact closed form).

**Limit of E[D]/n as n→∞:** E[D]/n = 1 − (1 − 1/n)^n → 1 − e^{-1}, since (1 − 1/n)^n → e^{-1}.

**Final answers:**
- E[D] = n − n(1 − 1/n)^n, exactly.
- lim_{n→∞} E[D]/n = 1 − 1/e ≈ 0.6321.