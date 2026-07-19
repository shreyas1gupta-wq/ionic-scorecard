# 02 — Scoring Engine (how factors become a [-100,+100] conviction + probability)

## Design goal
Turn a heterogeneous bundle of factor readings into: a signed conviction score, a calibrated probability of a positive return, an expected-return distribution, and a win-rate — all **interpretable** (you can see which factors drove it) and **regime/horizon-aware**.

## Step 1 — Factor normalization (relative, never absolute)
For each raw factor `f` on stock `i`:
```
z_i = normalize(raw_i | comparison_set)
```
- **Comparison set** = sector-and-size peers ∪ the stock's own trailing history (choose per factor — valuation uses both peers and own-history; momentum uses cross-sectional rank).
- Method: robust z-score (median/MAD) or cross-sectional percentile rank; winsorize tails. Sign-adjust so **higher = more bullish** for the horizon.
- Missing data → **do not impute silently.** Flag, reduce `confidence`, and if the factor is load-bearing for the call, the agent asks the human (no ruinous fallback — per brief Q17).

## Step 2 — Theme aggregation (interpretable middle layer)
Group factors into 7 themes; each theme score = weighted mean of its factor z's:
`Momentum · Value · Quality · Growth · Sentiment/Flow · Catalyst · Forensic/Risk`.
Themes are the layer analysts reason about and the layer the red-team attacks.

## Step 3 — Horizon composite (regime-conditional weights)
```
composite_i = Σ_themes  w_theme(horizon, regime, sector, cap) · theme_score_i
```
- `w(...)` comes from the **weight book** (`weights/` YAML), one weight vector per (horizon × regime) cell, with sector/cap adjusters.
- Weights are **calibrated in Phase 6–7**, not hand-set for production. Hand-set values are only *priors* to seed the search. Store priors + learned weights + the evidence that moved them.
- Base weight priors (illustrative starting point — see `01` §2 table; final values are earned):

| Theme | 1M prior | 1Y prior | 5Y prior | Microcap prior |
|---|---|---|---|---|
| Momentum | 0.30 | 0.15 | 0.05 | 0.10 |
| Value | 0.05 | 0.25 | 0.25 | 0.20 |
| Quality | 0.05 | 0.15 | 0.25 | 0.20 |
| Growth | 0.05 | 0.20 | 0.30 | 0.25 |
| Sentiment/Flow | 0.25 | 0.05 | 0.00 | 0.05 |
| Catalyst | 0.25 | 0.10 | 0.05 | 0.05 |
| Forensic/Risk | 0.05 | 0.10 | 0.10 | 0.15 (gate-like) |

> Forensic is largely a **penalty/gate**, not additive upside — see Step 6.

## Step 4 — Regime classifier (drives which weight vector is used)
Regime = the tuple that most changes factor payoffs. Classify the *market* (and separately the sector) into:
- **Trend:** up / down / chop (price vs 50/200 DMA slope, breadth, ADX-like).
- **Volatility:** low / high (India VIX percentile, realized vol).
- **Valuation of market:** cheap / neutral / expensive (Nifty PE/PB/earnings-yield vs bond-yield — the "Buffett/earnings-yield-gap" read).
- **Rate/credit cycle:** easing / tightening; credit spreads narrow / wide (the "high-yield scare" switch that flips red-flag severity).
- **Liquidity/flow:** FII/DII net, DXY/US10Y risk-on/off.

The regime tuple → a lookup into the weight book. Regime also directly sets **red-flag severity multipliers** (Step 6). Start with a rules-based classifier; upgrade to an HMM/vol-state model in Phase 7 (ml-expert).

## Step 5 — Oversight cascade modifier (see `03`)
`composite' = cascade_adjust(composite, global, national, sector)` — can shift or cap the score; an override past a cap forces a written justification into `overrides[]`.

## Step 6 — Forensic / red-flag overlay (nonlinear, size- & regime-conditional)
```
penalty = Σ_flags severity(flag) · size_mult(cap) · regime_mult(credit, valuation, trend)
score_pre = composite' − penalty
if any(hard_veto flags active): score_pre = min(score_pre, HARD_CAP)  # e.g. capped ≤ −60, thesis notes it
```
- **Hard-veto list** (short, still nuanced by evidence): auditor resignation / adverse opinion, confirmed fraud / SEBI-ED fraud action, debt-covenant breach with going-concern doubt.
- **Heavy-penalty list** (long, context-scaled): promoter pledge trend, related-party bloat, CFO/PAT divergence, receivables > revenue growth, serial dilution, aggressive capitalization, governance flags. Severity ↑ when the name is overvalued, in a downtrend, in a credit-tight regime, and small-cap; severity ↓ when cheap, uptrend, easy-credit, large-cap (per brief Q11).

## Step 7 — Probability calibration (composite → P and win-rate)
Raw composite is monotonic-ish with forward return but not a probability. Calibrate on history (`11`):
```
p_up = calibrator_[horizon, regime]( score_pre )     # isotonic or Platt/logit
```
- Fit one calibrator per (horizon × coarse-regime) so the same score means the right probability in each regime.
- **win_rate** = realized hit-rate of the historical decile/bucket the stock's `score_pre` falls into (analog base rate).
- **E[return], return_dist** = the historical forward-return distribution of that bucket (regime-conditioned), reported as p10–p90.
- These come straight from the backtest's bucketed forward returns — no free parameters.

## Step 8 — Map to [-100, +100]
```
score = round( 200 · (p_up_adjusted − 0.5) )   # symmetric around 0
```
where `p_up_adjusted` blends `p_up` with an *edge-magnitude* term so that "70% chance of +2%" scores lower than "70% chance of +15%":
```
p_up_adjusted = 0.5 + (p_up − 0.5) · squash( |E[return]| / typical_move[horizon] )
```
`squash` = a saturating function (e.g. tanh) so huge expected moves don't blow past ±100. Final clip to [-100,100].

## Step 9 — Cross-horizon coupling
Scores are independent EXCEPT: a **large negative 1M** score taxes the 5Y (and 1Y) score — you like the business but the near-term setup is hostile, so entry timing costs you (per brief Q9):
```
if score_1M < −THRESH:  score_5Y −= λ · (−score_1M − THRESH);  # λ small, e.g. 0.15; floor the tax
```
Never the reverse (a great 1M does not inflate a 5Y compounding thesis). Document the tax in `overrides[]`.

## Step 10 — Confidence
`confidence = g(data_completeness, factor_agreement, regime_stability)`. Low completeness or themes disagreeing sharply → "low", which triggers the human-in-the-loop gate before the call is issued.

## Explainability (mandatory)
Every score ships with `top_drivers[]` = the factor contributions (SHAP-style additive decomposition over the linear-in-themes composite; for any ML weighting use TreeSHAP). If you can't explain why the score is what it is, it doesn't ship.

## What is calibrated vs fixed
| Element | Source |
|---|---|
| Factor definitions | R&D (literature + our tests) |
| Comparison sets | Rules (sector/size/own-history) |
| Theme grouping | Design (fixed, interpretable) |
| Theme weights per regime | **Calibrated** (Phase 6–7), priors above |
| Red-flag severities & multipliers | Priors + calibrated on default/blow-up history |
| Score→probability calibrators | **Fit on PIT backtest** (Phase 6) |
| Hard-veto list | Design + compliance/forensic judgment |
