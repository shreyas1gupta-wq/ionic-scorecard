# G10 — OS-20 / OS-21 Phase-1 triage (Family D, conditional directional premium)
_Quant review · Arjun Rao · 2026-07-07 · campaign OPT-SWEEP-50 · FAST/CHEAP pass (rank, not certify)_

## Result (headline)
| Setup | N | Rs-pts/trade (net, per unit) | %-spot/trade | Win% | SR (per-trade) | Verdict |
|---|---|---|---|---|---|---|
| **OS-20** short PUT after NIFTY closes ≤ −1.0% | 119 | **+24.85** (≈₹1,864/lot) | **+0.1268%** | 84.0 | **0.37** | **SURVIVE (marginal)** |
| **OS-21** short CALL after NIFTY closes ≥ +1.0% | 120 | **+4.00** (≈₹300/lot) | **+0.0246%** | 83.3 | **0.08** | **KILL** |

`net` = premium points after 1× COST_STANDARDS (slippage max(1 tick,0.25% prem)/side + STT + exch + brokerage + GST). Per-lot = ×75. Neither clears the campaign's Sharpe>2 / XIRR>50% bar.

## Data lineage (verified on disk)
- NIFTY spot daily: `datasets/index_daily/nifty50.parquet` — 2,581 rows, max 2026-07-03; window used 2021-05-01→ (1,280 sessions).
- India VIX daily: `datasets/index_daily/india_vix.parquet` — 2,591 rows, max 2026-07-03 (σ input for Δ selection).
- NIFTY index options 1-min: `intraday_options_strategy/datasets/raw/hf_index_options_1m/options/NIFTY/` — 262 weekly expiries, 2021-05-27→2026-06-09.
- Signals: 123 down-days / 122 up-days ≤/≥ 1.0%; 121 attempted each after next-day/expiry availability; 119/120 filled (2/1 dropped for no liquid entry quote).
- **Effective window = 2021-05 → 2026-06** (option data start; NOT the 2016 VIX horizon — flagged for the campaign trials ledger).

## Guards / conventions honored
- Entry-fill = **next-liquid-quote** (T+1 first bar ≥09:15 with vol>0) after signal confirmed at T close — causal, no same-bar lookahead. This IS the strict fill; the setup already survives it (no optimistic same-day-close needed to pass).
- No-fill on zero-vol bars = DROP (3 total). σ = VIX close(T); entry spot = NIFTY open(T+1); r=6.5%. Strike = BS-Δ closest to 0.225 among OTM liquid strikes → realized mean |Δ| 0.226, mean DTE 6.5 (on-spec 20-25Δ, 3-7 DTE).
- Edge in Rs-points + %-of-SPOT only (never %-premium). Exit at fill/close (P&L booked at exit, no spreading).

## Validation battery (regime + year splits)
| Slice | OS-20 %-spot/tr (N) | OS-21 %-spot/tr (N) |
|---|---|---|
| Pre-2025-09 | **+0.1048%** (99) | +0.0362% (105) |
| Post-2025-09 (Tue-expiry regime) | **+0.2354%** (20) | **−0.0564%** (15) |
| 2021 | +0.250% | +0.049% |
| 2022 | +0.128% | +0.085% |
| 2023 | +0.052% | −0.079% |
| 2024 | −0.013% | +0.105% |
| 2025 | +0.185% | **−0.071%** |
| 2026 | +0.235% | **−0.064%** |

## Degenerate flags
- **OS-20**: high win% (84) but W/L = 0.50, skew −3.03, worst trade −356 pts (₹26.7k/lot) → textbook short-vol NEGATIVE SKEW, not an artifact. SR is honest (0.37, nowhere near a >4 fake). Edge is close to the firm's S-04 core (+0.22%/spot) → **likely mostly VRP + post-selloff IV-pop regime beta**; Phase-2 must test INCREMENTAL Sharpe over S-04/S-05, not standalone (CIO book rule #1).
- **OS-21**: win% 83 masks W/L 0.25, avgLoss −101.7 vs avgWin +25.1, skew −3.36 → the 83% win rate is a trap; pooled expectancy ≈ 0.
- Annualized SR figures (esp. post-2025-09 = 11×) are small-N artifacts — ignore; per-trade SR is the honest metric.

## Verdicts
**OS-20 → SURVIVE (marginal).** Positive in Rs-points AND %-spot; positive in BOTH regime halves and 5 of 6 years; clears every pre-registered kill criterion under the strict next-liquid fill. Economics sound: selling a put after a down day is paid twice — richer fear premium (mean P0=94 pts) AND equity upward drift both work FOR the short put. Advance to the Phase-2 pool, but rank it as a modest VRP-beta edge (SR 0.37), not a Sharpe>2 candidate; its Phase-2 test is incremental Sharpe over the short-vol book + tail sizing (worst −356 pts).

**OS-21 → KILL.** Pooled edge ≈ 0 (+0.025%/spot, SR 0.08) and it flips NEGATIVE post-Sept-2025 (−0.056%/spot) and in the two most recent years (2025, 2026) plus 2023. The tiny pooled positive lives entirely in the 2021-22 pre-break up-grind. Triggers two kill criteria: near-zero edge AND edge only in the pre-Sept-2025 regime. Economics: writing calls after an up day fights the market's structural upward drift (mean P0 only 53 pts — you collect less AND drift runs you over). Do not advance.

## Single weakest assumption
Profit-target exits are booked at exactly 0.5×P0 whenever the option's intraday LOW touches the target (assumes a resting buy fills at the level). Optimistic, but applied identically to both setups and dwarfed by the OS-20 vs OS-21 gap — it does not move the SURVIVE/KILL split. Secondary: BS-Δ strike selection uses ATM VIX as σ (ignores skew/term-structure); adequate for triage strike-picking, to be replaced with chain-implied Δ at Phase-2.

_Artifacts: `os20_trades.csv`, `os21_trades.csv` (per-trade ledger); backtest `scratchpad/g10_os20_os21.py`._
