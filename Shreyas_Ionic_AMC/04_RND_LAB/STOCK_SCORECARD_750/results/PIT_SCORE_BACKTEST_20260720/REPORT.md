# PIT quant-only backtest of the STOCK_SCORECARD score — report (2026-07-20)

**Question (Principal):** hold top-10 by score (equal weight) and bottom-10, quarterly rebalanced, last 3/5y, vs Nifty 500, no lookahead.

## What was tested (and what could not be)
- **Signal:** the mechanical 3Y composite (`final_3y_adj`) reconstructed point-in-time. The **analyst layer** (forward growth, reverse-DCF, Sell/Hold override, Ionic forward adjustment) is present-day judgment and **cannot be reconstructed historically** — it is the score's main claimed edge and is out of scope for any backtest. So this tests the quant core only, and with the **regime tilt neutralized** (historical regime unknown).
- **No-lookahead controls:** universe = Nifty 500 members as-of the rebalance month (survivorship-safe); fundamentals = latest annual whose available_date (90-day lag) <= date, per symbol; price pillars from prices <= date; entry lagged +1 session; benchmark over identical dates.
- **Window:** Dec-2021 to Sep-2024, 8 quarterly rebalances (~2.75y). Annual PIT fundamentals refresh through FY2023; prices start Jul-2021. A clean 5y needs the PIT panel extended past FY2023 + earlier prices.
- **Documented deviations from the live engine (PIT data thinner than today):** Value uses PE only (no clean PIT book-value-per-share or FCF); sector-neutral Quality + sector Value bucket use a static current sector map.

## v1 was invalid — corrected in v2 (red-team catch, Nikhil, ADVERSARIAL_REVIEWS.md)
v1 read `mc_fundamentals_parsed.parquet`, stale from 2023-06 with a ~20% coverage gap **concentrated in quality compounders** (HUL, Marico, Cholamandalam...), skewing the universe to the PSU/cyclical cohort that led 2022-24 and producing a spurious "no edge / negative" read. **v2 uses the firm's mandated annual PIT panels** (`ratios_pit` ROE/ROCE, `yearly_balance_sheet_pit` D/E, `yearly_profit_loss_pit` revenue/EPS/interest — interest-coverage gate restored), per-symbol-latest-available. Coverage: mean universe 201 → **419**.

## Result (v2, corrected)

| Basket (equal-weight, quarterly) | CAGR | Sharpe | Max DD |
|---|---|---|---|
| **Top 10 by score** | **41.3%** | 1.28 | **−2.3%** |
| Bottom 10 by score | 32.4% | 0.89 | −12.6% |
| Nifty 500 (cap-weighted TRI) | 30.3% | 1.75 | −5.6% |
| Eligible universe (equal-weight) | 44.3% | 2.00 | −6.2% |

- Long-short (top−bottom): **+4.3%/yr** (total +8.8%), positive in 62% of quarters, but **Sharpe ≈ 0 (−0.04)** — high spread vol, −21.6% spread drawdown.
- Top vs equal-weight universe: **−2.8%/yr** — the score did NOT beat naive equal-weighting.
- **Placebo: top-10 at the 44th percentile of 2,000 random 10-name baskets** — return-selection indistinguishable from chance.
- Lag 0 vs 1 day: L-S +6.7% vs +4.3% — no same-bar artifact.

## Honest verdict
**Directionally encouraging, statistically inconclusive.** The top decile beat the bottom (+9pp CAGR) and the cap-weighted index (+11pp), and — the one genuinely interesting signal — did so with a **much shallower drawdown** (−2.3% vs −12.6%/−5.6%), consistent with the score's quality/value/low-leverage tilt giving downside protection. BUT: the selection is **not distinguishable from random** (placebo 44th pctile, L-S Sharpe ~0), and it **did not beat equal-weighting the universe** (the 2022-24 breadth/size effect dominated). n=8 quarters, quant-only, regime-neutralized, single style regime — underpowered.

**Defensible one-liner:** "Over a clean ~3y point-in-time window, the quant core showed a mild quality/downside tilt (top decile beat bottom by ~9pp CAGR at a fraction of the drawdown) but no statistically significant return-selection edge; the analyst overlay — the real product — is only testable forward."

## Next
1. Re-run **with the regime tilt on** (currently favours cyclicals/value — may have helped 2022-24).
2. Extend the annual PIT panel past FY2023 (Kavya) for a multi-regime 5y window.
3. Start the **forward paper test** of today's full Ionic Score — the only test that reaches the analyst layer.
4. v2 addresses both red-team fixes; a re-audit of v2 is advised before this is quoted externally.

Files: `bt_pit_quant.py`, `results/PIT_SCORE_BACKTEST_20260720/{metrics.json, nav.csv, baskets.csv, nav_chart.png}`.
