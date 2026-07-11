# Curated combo strategies — Set B (combos 6-10) — 2026-07-07
Agent's own REPORT.md write was blocked by subagent policy; content below is verbatim from the agent's final report.

## Results (per-trade, net of 1x costs; edge = %-of-spot, denominator-free)

| # | Spec (TF/DTE/entry/exit/vol/size) | N | Win% | PF | Net %spot/tr | Gross %spot | Ann Sharpe | MaxDD %spot | Net@2x | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 6 | 10m/weekly/ORB/2xATR-stop/RV-regime/Kelly | 184 | 19.6% | 0.99 | -0.003% | +0.004% | -0.03 | -9.3% | -0.009% | FLAT |
| 7 | 5m/1DTE/pullback/ATR-trail/gap-filter/equal-risk | 206 | 30.6% | 0.52 | -0.012% | -0.007% | -1.63 | -2.5% | -0.017% | NEGATIVE (gross too) |
| 8 | 15m/weekly/BB-squeeze/30pct-target-50pct-stop/VIX-proxy/vol-scale | 157 | 52.2% | 0.83 | -0.029% | -0.022% | -0.51 | -5.6% | -0.036% | NEGATIVE (gross too) |
| 9 | 10m/0DTE/20-bar-breakout/EOD/RV-regime/Kelly | 119 | 39.5% | 1.36 | +0.040% | +0.045% | +0.58 | -1.7% | +0.035% | MARGINAL POSITIVE |
| 10 | 5m/weekly/ORB/2xATR-stop/gap-filter/equal-risk | 367 | 15.0% | 0.95 | -0.007% | -0.0004% | -0.12 | -10.0% | -0.013% | FLAT / cost-bled |

## Best cell, and why it should not be trusted yet

Combo 9 (0DTE Donchian breakout, 10-minute bars, EOD exit, realized-vol-regime filter, Kelly sizing) is the only positive combo and survives the 2x cost stress. But it is fragile, not a real edge: total return is +4.78% of spot, and the **top-5 trades alone contribute +5.08%** — remove them and the combo turns negative (-0.31%). It is also strongly regime-dependent: positive in 2021, 2022, 2025, 2026, but dead in the choppy 2023-2024 stretch.

Combos 7 and 8 lose even at the gross (pre-cost) level — an anti-predictive signal, not just a cost-drag problem. Combos 6 and 10 are essentially flat/cost-bled. None of the five combos breached the Sharpe < -2 standing-rule threshold, so no reversal build was triggered for this set.

## Data proxy notes (flagged honestly by the agent)
India VIX is not in the data catalog, so combo 8's "VIX regime" filter used a realized-volatility-percentile band as a proxy instead. Since spot data has no volume field, combo 9's "VWAP" concept was approximated with a daily-anchored typical-price mean rather than a true volume-weighted average. Options were priced through the full hold using actual 1-minute marks, so real theta decay is captured, not just entry/exit marks.

On the automated degenerate-result flags: "one symbol >30% of P&L" is a false positive here (it only separates call vs put categories, not distinct underlyings). "Negative without top-5 trades" is a real and meaningful flag for combo 9 specifically — its P&L profile is long-gamma/tail-dependent, consistent with the fragility noted above.

## Standing reminder from the agent
This set B (plus the parallel set A) was a hand-picked 5-cell draw from a menu spanning more than 10,000 possible combinations — not an exhaustive search and not a random sample. Nothing here is a certified finding. At most, combo 9's 0DTE breakout is a hypothesis worth a dedicated, pre-registered follow-up (fixed spec in advance, honest trial count, DSR/PBO, walk-forward validation, an untouched final out-of-sample slice) — and even then, only after its tail-dependence on a handful of trades is confronted directly, not glossed over.

## Files
`Shreyas_Ionic_AMC/04_RND_LAB/results/CURATED_COMBOS_20260707/SET_B/` contains per-combo trade CSVs (`trades_C6..C10.csv`) and full stats in `summary.json`.
