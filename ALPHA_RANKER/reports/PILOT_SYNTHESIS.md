# ALPHA_RANKER — Pilot Synthesis (10-stock, methodology proof)

**Status:** end-to-end pipeline proven on live data. **These are NOT live buy/sell calls** — see Data-Vintage caveat. Scores are UNCALIBRATED relative ranks; probability calibration is Phase 6.

## What runs today
7 parallel agents → 6 additive themes + forensic penalty + oversight cascade + regime switch → Phase-5 fusion (`src/scoring/combine_scores.py`) → per-horizon conviction [-100,+100] + band + uncalibrated p_up.

| Layer | Module | Output | Freshness |
|---|---|---|---|
| Momentum/technical | `src/factors/factors_technical.py` | `pilot_1m_scores.csv` | LIVE (to today) |
| Value/Quality/Growth/Leverage | `src/factors/factors_fundamental.py` | `pilot_fundamental_scores.csv` | annual to ~Mar-2025 |
| Catalyst/earnings-PIT | `src/factors/factors_catalyst.py` | `pilot_catalyst_factors.csv` | **financials stale to 2023-09**; calendar LIVE |
| Flow/microstructure | `src/factors/factors_flow.py` | `pilot_flow_factors.csv` | micro LIVE; **delivery stale to 2024-06** |
| Forensic red-flags | `src/forensic/forensic_checks.py` | `pilot_forensic_score.csv` | mixed; shareholding stale to 2023-12 |
| Regime switch | `src/regime/regime_classifier.py` | `current_regime.json` | to 2026-02-27 |
| Oversight cascade | `src/cascade/oversight_cascade.py` | `pilot_cascade_adjustments.csv` | to 2026-02-27 |
| Concall rubric | `src/themes/concall_rubric.py` | (LLM-scoring stub) | transcripts to Nov-2024 |

## Provisional multi-horizon conviction (uncalibrated)
| Stock | 1M | 1Y | 5Y | cover | Note |
|---|--:|--:|--:|--:|---|
| HINDALCO | 5 | 15 | 12 | 6/6 | balanced |
| HDFCBANK | 15 | 15 | 13 | 6/6 | bank ratios partial (N/A leverage) |
| GRAVITA | 44 | 14 | 7 | 6/6 | strong 1M momentum, fades on horizon |
| MARUTI | 25 | 6 | 3 | 6/6 | |
| NESTLEIND | 21 | 3 | 8 | 6/6 | quality, rich P/E ≈78 caps value |
| SHAKTIPUMP | -9 | -7 | 10 | **3/6** | fundamentals ABSENT — low-confidence |
| TATASTEEL | -19 | -9 | -10 | 6/6 | Sep-23 loss quarter drags catalyst |
| INFY | -39 | -11 | 5 | 6/6 | IT momentum weak; fundamentals offset at 5Y |
| TCS | -25 | -24 | -15 | 6/6 | IT structural-headwind read |
| ASIANPAINT | -15 | -36 | -38 | 6/6 | **1Y/5Y largely a cascade self-reference artifact — discount** |

## Caveats (honesty gates — do not ignore)
1. **DATA VINTAGE — the headline limitation.** Only prices (yfinance) and factor NAVs are current. Quarterly earnings cap 2023-09, delivery 2024-06, shareholding 2023-12. The fundamental/catalyst/flow layers therefore describe ~2023-24, not today. **A D-033 data-refresh pass is the #1 next action before any score is tradeable.**
2. **Cascade sector layer is self-referential** for singleton sectors (n=1 peers in a 10-name pilot) — it double-counts the stock's own momentum and is as-of Feb. ASIANPAINT's negative 1Y/5Y is mostly this artifact. Fix: real sector indices or a full-universe sector composite.
3. **SHAKTIPUMP** has no fundamentals in any on-disk source → 3/6 coverage; its scores are low-confidence, not clean.
4. **No promoter-pledge source** anywhere on disk (forensic hook left open).
5. Scores are **relative ranks among 10 names + uncalibrated** — not probabilities, not cross-sectional vs the full universe.

## Next actions (priority order)
1. **D-033 data-refresh**: NSE delivery bhavcopy fwd from 2024-06; fresh quarterly earnings (2023-09→now); shareholding+pledge source. [Data Office]
2. **Phase-6 calibration** (`11_BACKTEST_CALIBRATION.md`): map raw conviction → realized fwd-return/hit-rate on the 21yr `Nifty500_Master` price panel (after corp-action check); regime-conditional weight tilts using `current_regime.json`.
3. **Scale universe** 10 → NIFTY-750 (fixes cascade self-reference; enables true cross-sectional ranks).
4. **Lookahead-audit pass** on every factor module before Gate-4.
5. **Human-format deliverable** (Principal order): Word/table per horizon.
