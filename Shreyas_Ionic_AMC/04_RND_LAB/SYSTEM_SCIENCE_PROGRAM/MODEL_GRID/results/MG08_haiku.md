# Analysis: Why 2.1 Sharpe on 940-Feature ML Model Will Not Survive Scrutiny

## Premise
Claimed: Machine-learning strategy on US equities, 2010–2023 out-of-sample, 2.1 Sharpe ratio, 940 features from prices + fundamentals + news sentiment.

---

## Rank 1: Multiple Testing / P-Hacking (Probability: ~95%)
**Mechanism:**  
With 940 features, the feature space is enormous. Even if 939 are noise, random walk returns will correlate with ~50 of them by chance (at α=0.05). The paper likely trained a model on the full dataset, selected top-performing features, then declared the result "out-of-sample" on a held-out period. But feature selection happened using the full history — the test set was implicitly contaminated during feature engineering.

**Single Check to Confirm/Clear:**  
Run the exact model on a *different stock universe* (e.g., Russell 2000, emerging markets, or a held-out 200 stocks never used anywhere) or a *later time period* (2024 forward). If Sharpe collapses to <1.0, the edge was noise.

---

## Rank 2: Look-Ahead Bias in News Sentiment (Probability: ~92%)
**Mechanism:**  
News sentiment feeds are notorious for timestamp confusion. A feature like "average sentiment of news published on day T" is often *forward-filled* or uses *publication date* instead of *true announcement time*. If sentiment was released at 3 PM but used to trade at 10 AM, or if the data vendor backfilled sentiment retroactively, the model sees future information disguised as day-T data.

**Single Check to Confirm/Clear:**  
Rebuild the strategy using *only* sentiment available at market open (e.g., sentiment from news published before 9:30 AM ET). If you cannot obtain truly real-time sentiment timestamps or the data vendor cannot confirm their methodology, discard the sentiment features. Retest the model on just prices + fundamentals.

---

## Rank 3: Fundamental Data Look-Ahead (Probability: ~88%)
**Mechanism:**  
Quarterly earnings, book value, and analyst estimates are *released* days or weeks after the period ends, yet the dataset stamps them with the *quarter-end date*. If the model uses "Q1 earnings available on quarter-end" but the company released them on day +45, the model traded on information not yet public. Point-in-time (PIT) data is rare; most fundamental datasets are contaminated.

**Single Check to Confirm/Clear:**  
Obtain a *point-in-time fundamental dataset* with explicit `available_date` or `announcement_date` for every data point. Lag all fundamentals by ≥45 days from quarter-end (or use the actual release date). Rebuild the model. If results degrade significantly, lookahead was the edge.

---

## Rank 4: Survivorship Bias (Probability: ~85%)
**Mechanism:**  
A backtest on "US equities 2010–2023" typically only includes stocks that *survived* to 2023. Companies that went bankrupt, delisted, or were acquired mid-period are excluded or assumed perfect survivor status. This inflates returns because the strategy avoids the catastrophic losses that actually occur in live trading. The true edge is selecting *winners*, not finding alpha — the losers are invisible in the backtest.

**Single Check to Confirm/Clear:**  
Backtest on a *fixed universe of stocks defined at 2010* (e.g., the S&P 500 constituents as of Jan 2010), including all bankruptcies, delistings, and mergers as they occurred (with the actual delisting return). Use a survivorship-bias-adjusted dataset (e.g., CRSP with delisting returns or Compustat with PIT membership snapshots). Sharpe will likely drop 0.3–0.8 points.

---

## Rank 5: Underestimated Transaction Costs & Slippage (Probability: ~82%)
**Mechanism:**  
A 940-feature neural network changes its predictions constantly, likely generating high turnover (e.g., rebalance daily or weekly). The backtest assumes frictionless trading (or 1 bps cost), but realistic costs are 5–10 bps per trade round-trip, plus market impact on large positions, plus bid-ask spread on illiquid names. For a high-turnover strategy, these costs can reduce net Sharpe by 0.5–1.5 points. News and sentiment data often signal short-lived mispricings requiring fast trades with high slippage.

**Single Check to Confirm/Clear:**  
Calculate the strategy's actual turnover (fraction of portfolio rebalanced per period). Rebuild the backtest with *realistic* costs: 5 bps per leg for equities, 2% slippage on prediction confidence (e.g., if the model predicts +2% return, realized return after costs is ~1.9%), and 50% market impact for the top 5% of trades. If the strategy turns over >50% monthly, increase costs further.

---

## Rank 6: Validation Set Contamination / Walk-Forward Overfitting (Probability: ~78%)
**Mechanism:**  
The paper claims "2010–2023 out-of-sample," but typical ML pipelines do walk-forward validation or nested cross-validation. If hyperparameters (model size, dropout, learning rate, feature scaling) were tuned using the "out-of-sample" 2020–2023 window, or if features were engineered using statistics from the full 2010–2023 period, the test set was implicitly used during model selection. This is not a true hold-out test.

**Single Check to Confirm/Clear:**  
Specify and freeze the exact model architecture and hyperparameters using *only* 2010–2019 data. Then test on 2020–2023 without any parameter tweaks. Re-run this model live (paper-trade) on 2024 data without retraining. If Sharpe on 2024 falls below 1.0 or the model was retrained post-2023, contamination occurred.

---

## Confidence Assessment
- **Ranks 1–3** are quasi-certain pitfalls; 2.1 Sharpe claims on 940-feature ML almost always fall to one of these.
- **Ranks 4–6** depend on the paper's methodology disclosure; if they explicitly address these (fixed universe, PIT data, true hold-out), risk drops but rarely to zero.
- **A credible 2.1 Sharpe would require:** published code+data, a fixed pre-registered analysis plan, independent replication attempt, and live forward-test track record >12 months. Claims without this should be assumed false until proven otherwise.
