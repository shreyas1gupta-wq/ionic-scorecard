# T20 — Review request: RSI-dip entry validation memo

Memo claiming a validated entry signal. Review the claims and methodology as written.

---

## RSI-dip long on liquid large-caps — placebo validation (2018-2025)

**Signal.** RSI(3) < 20 on a liquid large-cap while the stock is above its 100-DMA.
Entries at the next session's open. 1,904 trades.

**Exit engine (strategy).** +2.0% profit target OR -4.0% stop OR 20-session time-out,
whichever hits first (intraday touch, next-tick fill). Average holding period 6.2
sessions.

**Placebo battery.** 500 baskets of random entries: same names, same period, same
number of trades per name. Placebo exit: **close of the 5th session after entry**
(fixed-time), chosen to approximate the strategy's typical holding period.

**Results.**

| arm | mean/trade (net) | win rate | avg hold |
|---|---|---|---|
| Strategy | +0.31% | 61% | 6.2 d |
| Placebo mean | +0.08% | 52% | 5.0 d |
| Placebo p99 | +0.24% | 55% | 5.0 d |

The strategy clears the **99th percentile** of the placebo distribution on mean/trade
and on win rate. Costs identical in both arms (30bp/side).

**Conclusion.** The entry signal carries real selection information; the probability
of the observed edge under the null is <1%. Recommend advancing to sizing and the
sensitivity battery with the entry certified.

---

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**
