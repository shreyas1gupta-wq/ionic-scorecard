## Derivation

For each value $i \in \{1, \dots, n\}$, define the indicator $X_i = 1$ if value $i$ appears at least once in the $n$ draws, and $X_i = 0$ otherwise. Then $D = \sum_{i=1}^n X_i$.

A single draw misses value $i$ with probability $\frac{n-1}{n}$. The draws are independent, so value $i$ is missed by all $n$ draws with probability $\left(1 - \frac{1}{n}\right)^n$. Hence

$$E[X_i] = P(X_i = 1) = 1 - \left(1 - \frac{1}{n}\right)^n.$$

By linearity of expectation (which needs no independence between the $X_i$):

$$E[D] = \sum_{i=1}^n E[X_i] = n\left[1 - \left(1 - \frac{1}{n}\right)^n\right] = n - \frac{(n-1)^n}{n^{n-1}}.$$

For the limit, divide by $n$:

$$\frac{E[D]}{n} = 1 - \left(1 - \frac{1}{n}\right)^n \xrightarrow{\,n \to \infty\,} 1 - e^{-1},$$

using the standard limit $\left(1 - \frac{1}{n}\right)^n \to e^{-1}$.

**Sanity check.** For $n = 1$: $E[D] = 1(1 - 0) = 1$, correct. For $n = 2$: the four equally likely outcomes $(1,1), (1,2), (2,1), (2,2)$ give distinct counts $1, 2, 2, 1$, so $E[D] = \frac{3}{2}$, matching $2\left(1 - \frac{1}{4}\right) = \frac{3}{2}$.

## Final answers

- **Exact closed form:** $\displaystyle E[D] = n\left[1 - \left(1 - \frac{1}{n}\right)^n\right] = n - \frac{(n-1)^n}{n^{n-1}}$
- **Exact limit:** $\displaystyle \lim_{n \to \infty} \frac{E[D]}{n} = 1 - \frac{1}{e} = \frac{e-1}{e} \approx 0.63212$

result: E[D] = n[1 - (1 - 1/n)^n] exactly, and E[D]/n converges to 1 - 1/e as n approaches infinity.