# REGIME-STATE ML — predict the state, not the trade
**2026-07-30 · DESK-100 · 42,528 samples at 15-min granularity · 4 heads**

## The ask
Principal: *"CAN WE CREATE A ML WHICH INSTEAD OF PREDICTING ENTRY EXIT PREDICT 2-3 DIFF THING LIKE
EXPECTED CHOPPY/TRENDING/MEAN-REVERTING, VOLATILITY ETC ETC AND WHEN NOT TO TRADE INSTEAD OF WHEN
TO GENERATE ALPHA WITHOUT OVERFIT"*

## Headline: the instinct was right about volatility and wrong about direction

| head | what it predicts | OOS AUC | **held-out AUC** | placebo p99 | verdict |
|---|---|---|---|---|---|
| H3 vol3 | forward realised-vol bucket | 0.8528 | **0.8742** | 0.6570 | **STRONG, holds up** |
| H4 tradeable | can a 1:1.5 harvest win here | 0.6795 | 0.6917 | 0.5238 | real, but see below |
| H1 state3 | choppy / mixed / trending | 0.5356 | **0.5055** | 0.5091 | **collapses OOS** |
| H2 meanrev | forward mean-reversion | 0.5264 | 0.5309 | 0.5135 | marginal |

Held-out = from 2025-07-01, never touched by any fitting decision.

**You can predict HOW MUCH the market will move. You cannot predict WHETHER it will trend or chop.**
H3's held-out AUC (0.874) is *higher* than its walk-forward AUC — vol clustering is the most robust
effect available. H1 at 0.5055 held-out is a coin flip.

Top features by permutation importance:
- H3 vol: `rv_back60` (+0.144), `hhmm`, `atr_pct`, `rv_back15`, **`atr_consumed`** (+0.0136)
- H4 tradeable: `rv_back15`, `rv5_over_rv20`, **`or30_atr`**, **`atr_consumed`**
- H1 trend: `rv5_over_rv20` (+0.042), `vwap_dist_atr`, `conc_pe`

`atr_consumed` and `or30_atr` are the Saty ATR Levels core — see the levels note below.

## A correction to my own first result
The initial economic null showed the no-trade gate turning a −0.0589 ATR baseline into **+0.0089**
at 50% decline, p=0.000, held-out included. **That number was inflated ~17×** and I am withdrawing it.

`tradeable` was labelled `winnable(long) OR winnable(short)`, so the payoff was credited whenever
*either* side would have worked — a perfect direction choice the model never made. `direction_committed.py`
re-runs it with the side committed PIT before the window:

| arm | baseline | gated 50% | gated 80% | held-out 50% | held-out 80% |
|---|---|---|---|---|---|
| DIR_vwap (A6 logic) | +0.0114 | +0.0161 ✓p=.000 | +0.0194 ✓ | +0.0070 ✗p=.62 | **−0.0045** ✗ |
| DIR_trend | +0.0038 | +0.0074 ✓ | +0.0169 ✓ | +0.0032 ✗ | −0.0023 ✗ |
| DIR_coin (placebo dir) | +0.0017 | +0.0026 ✗p=.23 | +0.0019 ✗ | +0.0006 ✗ | +0.0074 ✗ |
| BEST-OF-BOTH (the inflated one) | +0.1902 | +0.2137 | +0.2310 | +0.2085 | +0.2282 |

Two things this establishes:
1. **The placebo direction gains nothing** (p=0.23). So the gate is not merely dodging high-vol
   windows — it needs a real direction rule to pay. That is a genuine validation.
2. **The gate does not survive held-out.** 2015-2025 it beats the random-decline null at every
   fraction; from 2025-07 onward it is indistinguishable from random and turns negative when
   aggressive. Same era-dependence as everything else in this book.

## Why the earlier regime work found nothing and this found something
REGIME_GATE_20260730 tested regime conditioning on MONTHLY sleeve P&L: 28 cells, 0 candidates,
22 dead, none clearing Bonferroni m=28. That was a power failure — n = 111 to 172 **months**.
Moving to 15-minute granularity gives n = 42,528. Same question, 250× the observations.

## Anti-overfit controls actually applied
1. **Purged expanding walk-forward** — train [start..T], 5-trading-day embargo (> the 2h label
   horizon), test (T..T+3mo]. Rolling.
2. **Label-permutation placebo**, 200 draws, shuffled within quarter so autocorrelation is
   preserved in the null. Every reported AUC clears its own p99.
3. **Economic null** — 1000 random-decline draws at matched fraction. The only test that matters.
4. **Placebo direction arm** — catches a gate that is really just a vol filter.
5. Shallow regularised trees (depth 3, min_leaf 120, L2 1.0); per-fold feature filter so the early
   folds are not fed all-NaN chain columns (chain data starts 2021-05, index starts 2015).
6. Label terciles cut on a **trailing expanding** quantile, not the full-sample distribution.

## Standing caveat: the Oct-2024 break hits the best feature
`STRUCTURAL_EDGES_20260730/effect8` measured PCR→forward-vol predictive t at **−13.48 pre-Oct-2024
and +0.09 post**. Chain Herfindahl halved (0.0558→0.0263, t=62, KS p≈1e-178) when SEBI tightened F&O.
So the chain-derived features that power the vol head are structurally weaker in exactly the era
the Principal cares about. H3 still scores 0.874 held-out because it leans on `rv_back60`
(price-derived vol clustering), not on PCR — which is why it survived and H1 did not.

## Where this is actually usable
Not as a gate for option buying — GATED_BUYING_20260730 shows buying is 0 for 87 regardless.
The vol head is usable for **position sizing** and for the **selling** book, where knowing the
forward vol bucket at AUC 0.87 is directly monetisable through strike and size selection.

## Files
`regime_ml.py` · `direction_committed.py` · `regime_ml_report.json` · `oos_predictions.parquet` ·
`direction_committed.csv` · `run_log.txt` · `dir_log.txt`
