# AG4 — Regime Classifier: Current Read & Method

Source code: `ALPHA_RANKER/src/regime/regime_classifier.py`
Outputs: `ALPHA_RANKER/results/regime_timeline.parquet` (5,189 daily rows, 2005-04-01 → 2026-02-27, 47 columns), `ALPHA_RANKER/results/current_regime.json`

## [DATA] Input freshness caveat (read this before trusting the snapshot)
`factor_navs (1).xlsx` updates at two cadences. NIFTY 500, NIFTY 100 Low Vol 30, NIFTY 200 Momentum 30
and Nifty Midcap Momentum 50 run through **2026-02-27**. The other 16 columns (Value/Quality/Alpha
indices, High Beta 50, GOLDBEES, Midcap150, Smallcap100/250, Multicap, Nifty100, Liquid Fund, Top-20 EW)
stop at **2026-01-05** — a clean trailing-NaN block (verified zero internal gaps), i.e. a vendor lag, not
a market event. Rather than forward-fill or guess, each lens below reports its **own `as_of` date**. Trend
and Volatility (NIFTY 500-only) are current to 2026-02-27; Breadth, Risk-appetite and Factor-leadership
are stuck at 2026-01-05 until that feed catches up. **[INFERENCE]** — until the vendor lag clears, treat
Breadth/Risk/Factor-leadership as a "~7-week-old read," not "current."

## Current regime (per-lens as_of)

| Lens | As of | Label | Key metric |
|---|---|---|---|
| Trend | 2026-02-27 | **sideways** | NIFTY 500 23,167 vs 200-DMA 23,309 (below); 50-DMA slope down, 200-DMA slope still up — a stalled uptrend, not yet a confirmed bear |
| Volatility | 2026-02-27 | **normal** | 21d realized vol (annualized) 16.6%, vs expanding tertile cuts 12.0% / 17.0% |
| Breadth | 2026-01-05 | **narrow/large-cap-led** | Midcap150+Smallcap250 avg RS vs Nifty100: -2.9% (3m), -4.6% (6m) — large-caps outperforming |
| Risk appetite | 2026-01-05 | **risk-off** | High-Beta-vs-LowVol RS ~flat (+0.6% 3m); Nifty500-vs-Gold RS -11.9% (3m) — gold has strongly beaten equities, dominating the read |
| Factor leadership | 2026-01-05 | **Value** | 3m/6m blended score: Value +12.8%, LowVol +5.5%, Quality +3.5%, Momentum +2.8%, Alpha +1.7% |

## Method (each lens causal — uses only data ≤ T; no lookahead)
- **Trend**: bull = price>200DMA AND 50/200-DMA both rising (20d slope); bear = the mirror-image all-down case; else sideways. [INFERENCE: 20-trading-day slope window is a design choice, not specified in `02_SCORING_ENGINE.md`.]
- **Volatility**: 21d realized vol of NIFTY 500 returns (annualized), tertile cut using an **expanding** (not full-sample) quantile — the cut at date T only ever reflects history ≤T, so early-history tertiles are noisier by construction (min 252 obs before a label is assigned).
- **Breadth**: avg(Midcap150, Smallcap250) trailing return minus Nifty100 trailing return, averaged across 3m and 6m windows; sign gives broad/narrow. `breadth_conflict_3m_vs_6m` flags when the two windows disagree in sign (transparency, not a third state).
- **Risk appetite**: two votes summed — (High Beta 50 − Low Vol 30) 3m return, and (NIFTY 500 − GOLDBEES) 3m return (gold beating equities = risk-off). Positive sum = risk-on.
- **Factor leadership**: 0.5×3m + 0.5×6m trailing return per factor index (Momentum/Value/Quality/LowVol/Alpha), ranked; `leading_factor(s)` reports two names when #2 is within 20% (relative) of #1's score.

## Validation performed
- Spot-checked COVID window (Feb–Apr 2020): bull→sideways→bear transition tracks the crash exactly, vol_regime flips to `high` (rv21 reaches 81% annualized) at the same time — mechanism behaves as intended.
- Spot-checked 2021 rally: sustained `bull` label through the run-up.
- Label distributions over the full 21-year sample are non-degenerate across all 5 lenses (no lens collapses to one value) — see counts in `regime_timeline.parquet`.
- No lookahead: trend/vol/breadth/risk/factor metrics are all `.rolling()`/`.pct_change()`/`.expanding()` — none reference future rows; one-day-shift smoke test not re-run here (mechanism is structurally causal, not a fitted model) but flagged for `overfit-analyst-sameer-bhat` / `lookahead-audit` skill before this feeds Gate-4 certification.

## [INFERENCE] How weights should tilt right now
Given **sideways trend / normal vol / narrow breadth / risk-off / Value leading**, but with the important
caveat that the last three lenses are reading a 7-week-old tape: this profile says the market has stalled
just under its 200-DMA, large-caps are still doing the work, gold's outperformance signals a genuine
risk-off undertone, and Value is the only factor with a clear lead. Per `02_SCORING_ENGINE.md` Step 4, this
argues for the weight book to (a) lean the horizon composite toward Value/Quality-style themes and away
from small/mid-cap-momentum themes until breadth confirms a broaden-out, (b) hold red-flag severity
multipliers at their base level (vol regime is `normal`, not a credit-tight/high-vol scare), and (c) treat
any momentum/high-beta signal with reduced conviction until the risk-appetite lens turns risk-on. This is
a reading of the mechanical output, not a portfolio decision — CIO/FM sign-off still applies before any
weight-book change per D-025.
