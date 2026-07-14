# MG08 — CIO CONSOLIDATED VERDICT
## Claim under review: "ML strategy, US equities, 2010–2023, 940 features (price + fundamentals + news sentiment), 2.1 out-of-sample Sharpe"

**Author of record:** Rajan Mehta, CIO (E-001). Integrates Head-of-Quant draft + Red Team (Nikhil Bose, E-014) critique. One-pass consolidation.

---

## VERDICT: REJECT-until-proven (artifact prior)

Three-line rationale:
1. [OPINION] A **net, capacity-aware 2.1 Sharpe held for 13 years is roughly top-0.5% of all published equity strategies**; real-world net-of-cost equity factor strategies cluster at 0.3–1.0. The number is itself prior evidence of an artifact before any check is run — the base rate does the first 80% of the work.
2. [INFERENCE] A 940-feature ML pipeline over data that includes **news sentiment (notoriously backfilled/retro-rescored) and fundamentals (45–90 day availability lag)** is a near-textbook setup for two mechanical inflations: temporal leakage and selection overfitting. Either alone can manufacture 2.1 from zero true edge.
3. [OPINION] The single weakest assumption is that **the reported OOS window is genuinely untouched.** It almost never is. The most probable *concrete* mechanism is leakage (feature-PIT + cross-validation/preprocessing), not exotic overfitting.

**Adjudication note (where I overrode the draft):** I accept the Red Team's re-rank. The draft ranked transaction costs #2 and lookahead #3, then contradicted itself by naming lookahead a co-#1 cause in its verdict. For *this* claim, leakage is #1. I also split the draft's over-stuffed Rank 6, folded short-side costs into the cost item, folded P&L-concentration into the capacity item, and replaced the un-runnable "pre-register a holdout retroactively" check with **post-publication OOS + a window touch-count** — the one test the authors provably could not have peeked at.

---

## THE 6, RANKED BY PROBABILITY OF BEING *THE* REASON 2.1 DIES

### 1. Temporal leakage — feature PIT + label + cross-validation/preprocessing
[INFERENCE] The most mechanical and near-guaranteed failure in a 940-feature ML pipeline. Three sub-mechanisms, all of which leak the future into training:
- **Feature PIT:** sentiment vendor scores timestamped at article-write time or retro-rescored by a model trained on the full sample; fundamentals used before their filing/availability date, or restated (as-known-today) rather than as-first-reported.
- **Label leakage:** forward-return label window overlapping the feature as-of date; split/dividend adjustment using today's factors; delisting/bankruptcy return coded 0 or NaN instead of realized −100%.
- **CV/preprocessing leakage:** standardization/winsorization/PCA/target-encoding fit over train+test together (leaks future moments into every fold); k-fold or random CV on overlapping-horizon labels **without purge + embargo** (López de Prado) → train/test rows adjacent in time share information; the inflated CV Sharpe is then reported as "OOS."

**HOW it inflates:** any of these lets the model see outcome information at training time, raising in-sample hit rate that carries into the mislabeled "OOS" number.

**Single check:** shift **all** features +1 trading day (one-day-lag test) and refit **all** preprocessing *inside* each fold under **purged + embargoed walk-forward**; independently confirm every feature carries an `available_date` and that sentiment scores are PIT (not backfilled). **A real edge barely moves; a leakage edge craters.** Material drop = confirmed; no DSR math even needed.

---

### 2. Selection overfitting / OOS-peeking (multiple testing)
[INFERENCE] 940 candidate features × model configs × CV folds = hundreds-to-thousands of implicit trials. The reported "OOS" Sharpe is the **max over that search — an order statistic, not an unbiased estimate**; expected max Sharpe of pure-noise trials grows ~√(2·ln N). Compounded by peeking at the OOS window during feature/model selection, so it is not truly out-of-sample.

**HOW it inflates:** picking the winner of a large search guarantees an upward-biased Sharpe even when every underlying signal is noise.

**Single check:** recompute the **Deflated Sharpe Ratio at an HONEST trial count** (features screened × configs × folds × preprocessing choices), evaluated using the return series' length and higher moments (skew/kurtosis) — not trial count alone — plus **PBO via CSCV**. Then run the one test authors could not game: **score on genuinely post-publication data (2024–2025+)** and obtain a **touch-count of the final window** (code history / commit log / author interview). Adopted thresholds: DSR < 0.95 or PBO > 25% = dead; post-pub Sharpe collapse = confirmed.

---

### 3. Transaction costs AND short-side costs
[INFERENCE] Cross-sectional ML signals turn over fast across many names, and the alpha overwhelmingly concentrates on the **short leg** (expensive/junk names that are hardest to borrow). A gross 2.1 routinely falls below 1.0 once realistic half-spread + market impact at the strategy's *actual* turnover is charged — and further once **borrow fee, locate availability, and short-sale disruptions (e.g., 2020 bans)** are charged on the actual short book. Papers commonly report gross, or a flat 5–10 bps that scales with neither size nor liquidity, and assume free, unlimited borrow.

**HOW it inflates:** unpriced trading friction and free-borrow assumptions convert an untradeable gross signal into a headline net number.

**Single check:** obtain turnover / avg holding period; recharge net Sharpe with per-name spread + impact (at 2× stress) **and per-name borrow fees**, dropping names with no/low locate and excluding hard-to-borrow deciles; plot Sharpe vs cost-per-trade. If the edge dies at plausible costs, or the short leg carries the alpha, it is a gross-return artifact.

---

### 4. Survivorship / universe-construction bias
[INFERENCE] If the 2010–2023 universe is today's index membership or a database lacking delisted names and delisting returns, bankrupt/acquired losers are silently dropped — biasing returns up and understating vol on both counts.

**HOW it inflates:** removing the realized losers from the population mechanically lifts mean return and shrinks the tail, inflating the ratio numerator and denominator both in the favourable direction.

**Single check:** confirm point-in-time membership **including delisted names with delisting returns**; plot universe count per year (should fluctuate, not be a clean current list); compare Sharpe with vs without delisting returns.

---

### 5. Illiquidity / capacity + P&L concentration (tail concealment)
[INFERENCE] Two ways an aggregate 2.1 is a mirage: (a) the edge concentrates in **low-price, low-ADV, wide-spread microcaps** where mispricing is largest but real execution is impossible; (b) the Sharpe is carried by a handful of **names, days, or a single regime**, and aggregation hides that single-source dependence.

**HOW it inflates:** flat cost assumptions understate microcap friction so untradeable names dominate; and averaging conceals that removing a few contributors would collapse the number — the strategy has no breadth.

**Single check:** decompose P&L by liquidity/price/market-cap decile and re-run inside a tradable filter (price > $5, ADV > $1–5M, position capped at % of ADV); **then drop the top 1% of daily/position P&L contributors and re-score, and jackknife by calendar year** (is Sharpe > 1 in most years, or carried by 2020–2021?), plus a Herfindahl of P&L across positions. If the bottom-liquidity decile or the top-1% contributors carry the Sharpe, it will not replicate at size.

---

### 6. Factor/market beta mistaken for alpha
[INFERENCE] 2010–2023 is a historic low-rate bull run; a long-tilted or high-beta signal posts a high Sharpe that is really Mkt/size/momentum/quality **beta, not skill**. (Sub-check, demoted from the draft's over-stuffed slot: overlapping/monthly-averaged returns and wrong annualization understate variance and inflate the ratio.)

**HOW it inflates:** compensated risk premia earned in a favourable regime are relabelled as alpha; return-smoothing shrinks the denominator.

**Single check:** regress strategy excess returns on **Mkt + FF5 + momentum**; report the **alpha t-stat and net-of-factor Sharpe**, plus regime slices (2018, 2020 crash, 2022 drawdown). Recompute Sharpe on **non-overlapping realized P&L with Lo's autocorrelation correction**. Weak alpha t-stat, or a Sharpe that halves outside the bull years, = beta + smoothing, not edge.

---

## KILL CRITERIA (run in this order; each is cheap and decisive)
1. **One-day-lag + purged-embargoed refit** (Item 1) — cheapest, most likely to end the discussion.
2. **Post-publication OOS on 2024–25 + honest-trial DSR/PBO** (Item 2).
3. **Net-of-realistic-cost + borrow recharge** (Item 3).
Any one of these three collapsing the Sharpe toward the 0.3–1.0 base range = REJECT confirmed. Items 4–6 clean up whatever survives.

**Review date:** on receipt of the authors' code + data lineage (feature `available_date`s, turnover, universe file with delistings, CV scheme). No lineage → the claim stays REJECT and is not sizeable.

## Dissents
None. Head-of-Quant draft and Red Team converge on FAKE-until-proven; the only substantive disagreement — cost (#2) vs lookahead (#3) ordering — I have resolved in the Red Team's favour (leakage #1, overfitting #2, costs #3), correcting the draft's ranking-vs-verdict contradiction and swapping its un-runnable pre-registration check for post-publication OOS.
