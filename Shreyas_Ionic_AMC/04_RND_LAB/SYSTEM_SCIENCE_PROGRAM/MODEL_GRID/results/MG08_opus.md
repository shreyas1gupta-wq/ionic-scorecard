# Why a 2.1 OOS Sharpe (ML, US equities, 2010-2023, 940 features) will not survive

Claim under test: ML strategy, US equities, **2.1 Sharpe out-of-sample, 2010-2023, 940 features** from prices, fundamentals, news sentiment.

Prior: a genuine, tradable, cost-net 2.1 Sharpe on liquid US equities over 13 years is roughly the top ~1% of all published equity strategies and is almost never reproduced by a third party. The base rate says the number is inflated by one or more of the mechanisms below. Ranked by probability that this is the/a killer.

---

## 1. Backtest overfitting on a window that is not truly out-of-sample (selection bias / multiple testing)
**Probability: very high.** This is the signature failure for a 940-feature ML paper.

**Mechanism (how it inflates):** With 940 candidate features plus ML hyperparameters (depth, learning rate, regularization, lookback, rebalance freq, universe cut), the effective number of trials is in the thousands. If features/architecture/hyperparameters were chosen — even informally, across paper revisions — by looking at performance over 2010-2023, then the "OOS" period has already leaked into model selection. The max Sharpe over N independent trials grows like `sqrt(2 ln N)`; at N in the hundreds you *expect* a best-of ~2.0 Sharpe from pure noise. What's reported is the winner of a search, not an unbiased estimate. Cross-validation on shuffled or randomly-split rows (instead of a strict forward split) also lets the model see future-distribution information.

**Single check:** Compute the **Deflated Sharpe Ratio (Bailey/Lopez de Prado)** / **PBO** using the authors' honest trial count and return autocorrelation; equivalently, demand a *pre-registered, never-touched* final holdout (e.g. train/tune only on 2010-2018, evaluate once on 2021-2023) and see whether the 2.1 survives that single untouched shot.

---

## 2. Point-in-time / lookahead leakage in fundamentals and news sentiment
**Probability: very high.** Fundamentals and sentiment are the two most leakage-prone feature families in existence.

**Mechanism:** Fundamentals dated to *fiscal-period-end* rather than the *filing/availability date* give the model quarter results 30-90 days before they were public (and restated/as-revised figures the market never saw at the time). News sentiment leaks when articles are timestamped by event date rather than publication-feed time, when the sentiment scorer was trained on the same period it scores, or when the ticker-to-article mapping uses the current (survivor) identifier set. Any of these lets the model condition on the future, and it will happily exploit it — this is the classic "the alpha vanishes when I lag the data by one day."

**Single check:** Rebuild every feature strictly PIT — fundamentals lagged to actual SEC filing date, sentiment lagged to feed-publication timestamp — then re-run with an added **uniform one-day lag** on all features. A real edge degrades gently; a leakage artifact collapses toward zero.

---

## 3. Transaction costs, turnover and market impact ignored (gross vs net Sharpe)
**Probability: high.** The single most common reason a real backtest doesn't survive scrutiny.

**Mechanism:** A 940-feature daily/weekly ML model typically produces high turnover (often 100-1000%+ annually). Sharpe reported on *gross* returns omits bid-ask spread, commissions, financing/short borrow, and price impact. On US equities, even a modest 10-20 bps round-trip against high turnover subtracts 1.0-1.5 from the Sharpe; short-borrow and impact on the fast-signal names take more. A 2.1 gross can be a 0.4-0.8 net — publishable, untradeable.

**Single check:** Ask for **reported annual turnover** and recompute net Sharpe with realistic costs (spread + commission + a square-root impact term sized to each name's ADV). If turnover isn't disclosed, treat the 2.1 as gross and discount accordingly.

---

## 4. Survivorship bias and illiquid / microcap concentration (untradeable alpha)
**Probability: medium-high.**

**Mechanism:** (a) Survivorship — if the universe is today's listed names or a CRSP pull without delisting returns, the model never buys the companies that went to zero, mechanically lifting returns and Sharpe. (b) Concentration — much cross-sectional ML alpha lives in small, illiquid, high-spread names where the *modeled* fill is impossible at any real size; the top-decile long-short is dominated by stocks you can't trade. Both make the paper number real on paper and unrealizable in a fund.

**Single check:** Restrict to a **liquid, survivorship-free universe** (e.g. survivorship-free CRSP *with delisting returns*, price > $5, top ~1000 by dollar ADV) and re-run. If the Sharpe halves, the edge was in the untradeable/dead tail.

---

## 5. Disguised factor/beta exposure and single-regime luck
**Probability: medium.**

**Mechanism:** 2010-2023 is essentially one macro regime — post-GFC QE bull market, secular low rates, mega-cap growth/quality/momentum leadership — with only 2022 as a real stress. A strategy that is net-long-biased, or that is a repackaging of momentum + quality + low-vol, earns those risk premia and a rising-market beta, then reports the total as "alpha." The 2.1 is partly compensation for known factor exposure, not a novel edge, and is conditional on a regime that may not repeat.

**Single check:** Regress the strategy's returns on **market + Fama-French 5 + momentum (and a short-vol proxy)**; report the *residual* alpha and its t-stat, and split the Sharpe across sub-periods (2010-15 / 2016-19 / 2020-23, isolating 2022). If alpha isn't significant after factors, or the Sharpe is carried by one sub-period, it's beta/regime luck.

---

## 6. Sharpe computation artifacts (autocorrelation, non-normality, annualization)
**Probability: medium-low, but a pure free win to check.**

**Mechanism:** Daily/monthly Sharpe scaled by `sqrt(252)`/`sqrt(12)` is overstated when returns are **positively autocorrelated** — which they are whenever positions are held in illiquid names or NAV is stale/smoothed (return smoothing depresses measured volatility and inflates Sharpe). Overlapping-window returns, an unrealistically low or omitted risk-free rate, or a strongly negatively-skewed / fat-tailed payoff (Sharpe rewards steady small gains and hides the rare large loss) can also flatter the ratio relative to the true risk.

**Single check:** Recompute with an **autocorrelation-adjusted (Newey-West / Lo) Sharpe**, verify the risk-free/excess-return convention, and cross-check internal consistency: a genuine 2.1 Sharpe over 13 years implies a shallow max drawdown (roughly < ~10-12%). If the reported max drawdown or return skew is inconsistent with 2.1, the ratio is a computation artifact.

---

### One-line triage order
Check in this sequence — each is cheaper than the last to falsify: **(6) recompute the ratio → (5) factor-regress → (3) net of costs/turnover → (4) liquid survivorship-free universe → (2) PIT + one-day-lag test → (1) deflated Sharpe / single untouched holdout.** In practice #1, #2, and #3 kill the large majority of headline ML equity Sharpes.
