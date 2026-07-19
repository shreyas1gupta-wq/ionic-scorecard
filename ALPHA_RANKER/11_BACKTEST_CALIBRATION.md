# 11 — Backtest & Calibration

Purpose: turn raw factor bundles into **calibrated probabilities**, prove each factor/weight earns its place, and defend against overfitting. This is where the "1000+ tests" R&D program (brief Q8; `13` Phase 7) lives. Calibration ≠ optimization — we fit the score→probability mapping and *validate* weights, we do not curve-fit weights to maximize a backtest Sharpe.

## Ground rules (firm-mandated)
- **PIT everything.** Universe membership from survivorship-free NIFTY-750 snapshots; fundamentals via `available_date`; no factor may use data unknowable at the decision date.
- **Lookahead audit mandatory** (`lib/lookahead_audit.py` + one-day-lag test) before any result is quoted — this is the T1–T10 taxonomy gate (firm D-028).
- **Walk-forward only**, purged & embargoed CV (purgedcv) to prevent leakage across the horizon window (a 5Y label leaks 5Y forward — embargo accordingly).
- **DSR & PBO** (Deflated Sharpe, Probability of Backtest Overfitting) reported for every strategy family; owner = overfit-analyst-sameer-bhat.
- Costs & fills realistic (`lib/execution_realism.py`, COST_STANDARDS): circuit/thin-volume no-fill, impact cost, limit-order-or-skip for microcap (no assumed fills in dead markets).

## Metrics per horizon
- **IC** (rank correlation of score vs realized forward return over the horizon), and **regime-conditional IC** (does the signal work in each regime?).
- **Decile/bucket spreads:** forward-return distribution by score bucket → this *is* the win-rate / return_dist the engine reports.
- **Hit rate** = P(return>0) by bucket → the calibrated `p_up`.
- Top-bucket Sharpe/CAGR net of costs, turnover, capacity (RP-14), max drawdown.
- **Calibration curve:** predicted P vs realized frequency (reliability diagram); fit isotonic/Platt per (horizon × coarse-regime).

## Horizon-specific design
| Lens | Label window | Sampling | Caveat |
|---|---|---|---|
| 1M | 21-trading-day forward | monthly rebalance, many samples | rich data → tight calibration; watch turnover/costs. |
| 1Y | 252-day forward | monthly overlapping (embargoed) | moderate n; regime-condition carefully. |
| 5Y | ~1260-day forward | quarterly overlapping, heavy embargo | **small independent-n** → wide bands, lean on cross-section + analogs; be honest, don't over-claim. |
| Microcap | 6–12m + event | survivorship + liquidity screen critical | delisting/suspension = realized −100%; model it, don't drop it. |

## The R&D loop (how a factor/weight earns production)
```
hypothesis ─▶ cheap falsification (firm cheap-test gate) ─▶ PIT backtest ─▶ IC + decile spread
   ─▶ ablation (does it add incremental IC over existing themes? orthogonality RP-17)
   ─▶ regime-conditional check ─▶ DSR/PBO ─▶ red-team + lookahead audit ─▶ promote to weight book (with evidence) or kill (KILLED_IDEAS)
```
- Weights per (horizon×regime) are set by **regularized fit / cross-validated search seeded by the `02` priors**, constrained to stay interpretable and monotone where theory demands (e.g. momentum weight ≥0 in uptrends). No black-box weight that can't be explained.
- Every promotion logs the evidence that moved the weight off its prior; every kill logs the resurrection condition.

## Calibration harness (deliverable, Phase 6)
- `results/calibration/<lens>/` — reliability diagrams, isotonic fits, bucket forward-return tables (these back the engine's `p_up`, `win_rate`, `return_dist`).
- `weights/<lens>_<regime>.yaml` — the weight book, versioned, git-hashed at freeze (firm D-030 forward-freeze discipline).
- Sanity-check against the firm's existing 12-year blue-chip return series and factor-index closes (`factor-indices` skill) as an external benchmark.

## Anti-overfitting discipline (hard)
- Track honest trial count (OOS-hygiene audit RP-19); deflate Sharpe by trials.
- Reserve a final holdout window touched ONCE at certification.
- Prefer fewer, theory-backed factors over many fitted ones. A factor with no economic story doesn't ship even if IC looks good.
