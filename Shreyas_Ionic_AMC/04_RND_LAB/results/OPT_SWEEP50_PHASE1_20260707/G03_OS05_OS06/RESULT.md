# G03 — OS-05 (inverse-IV-sized strangle) & OS-06 (delta-hedged strangle) — Phase-1 triage
_OPT-SWEEP-50 · Arjun Rao (Quant) · 2026-07-07 · FAST/CHEAP ranking pass, no DSR/sensitivity._

## Result (per-trade, NIFTY index weekly 16Δ short strangle, 1× COST_STANDARDS)
| Setup | N | Rs-points/trade (net) | %-spot/trade (net) | per-trade Sharpe | Win% | Worst trade | Verdict |
|---|---|---|---|---|---|---|---|
| **OS-01 baseline** (eq-wt, 50%/2×/expiry) | 261 | **+7.68** (median +23.9) | **+0.043%** (median +0.120%) | 0.11–0.14 | 78.5% | −539 pts (−2.06%) | benchmark (marginal) |
| **OS-05** inverse-IV sizing | 261 | edge ≡ OS-01 (overlay) | mean-of-book +0.035% | **0.122** | — | −2.45% (worse) | **KILL** |
| **OS-06** delta-hedged (±0.10 bands) | 261 | **−4.98** (median +10.2) | **−0.020%** | **−0.05** | 62.8% | −889 pts (−3.94%) | **KILL** |

Regime slices (Sept-2025 Thu→Tue expiry break): OS-01 +ve both (pre +6.35 / post +15.52 pts). OS-05 beats baseline ONLY post-break (Sh 0.27 vs 0.21, n=38); fails pre-break (0.10 vs 0.13) & pooled (Δ Sharpe **−0.017**). OS-06 negative pre-break, only +1.45 pts post-break (n=38).

## Data lineage
- Options: `intraday_options_strategy/datasets/raw/hf_index_options_1m/options/NIFTY/*.parquet` — 262 weekly expiries 2021-05-27→2026-06-09, 1-min OHLCV+strike/type/OI. 261 traded, 1 dropped (no-liquid).
- Spot `datasets/index_daily/nifty50.parquet`; IV `datasets/index_daily/india_vix.parquet` (both daily, →2026-07-03).
- Costs `06_TRADING_DESK/COST_STANDARDS.md` @1×. Trades: `trades_os01_os05.csv`, `trades_os06.csv`; `summary.json`.

## Guards passed
L2 auction filter (≥09:15); next-liquid-quote entry (first vol>0 bar), no-fill legs DROPPED (D-031); BS-Φ⁻¹ 16Δ strike selection from spot+VIX (r=0, flat-IV); per-trade booking at EXIT (IC-1 lesson, no variance fabrication); Sept-2025 regime NOT pooled; degenerate detectors run.

## Degenerate flags (OS-01)
- Tail-seller profile: win 79%, W/L 0.41 — as expected for short vol; mean is +ve, dominated by 50 stop-out tails. Annualized Sharpe ≈0.8–1.0 (NOT >2). Consistent with firm bar-realism prior.
- "One symbol >30% |P&L|" = artifact (grouping key = exit-reason; the 'stop' bucket carries the big losses). Not a symbol-concentration issue.

## Verdict + weakest assumption
- **OS-05 — KILL.** Inverse-IV sizing is a pure overlay (per-trade edge ≡ OS-01 by construction); it must earn its keep on risk-adjusted terms and does NOT — pooled Sharpe **−0.017 below** baseline, and it *worsened* the tail (−2.06%→−2.45%). Mechanism: high-entry-IV weeks were the *more* profitable ones (richest VRP); downweighting them diluted edge, while the fat tails arrived from *calm-IV* entries (spikes happen after entry), so entry-IV sizing does not dodge the left tail. Only positive signal is 38 post-break trades → regime-confined → fails campaign kill rule.
- **OS-06 — KILL.** Negative edge in **both** Rs-points (−4.98/trade) and %-spot (−0.020%), Sharpe −0.05 vs baseline +0.14. Delta-hedging a short-gamma book realizes negative gamma P&L (avg hedge_pnl −2.36 pts) plus hedge transaction cost, and *enlarged* the worst case (−539→−889 pts). Fails edge>0 AND fails-to-beat-baseline.
- **Single weakest assumption (both):** exit triggers detected on daily leg CLOSE, not intraday high/low — this UNDERSTATES stop frequency/slippage, so OS-01's baseline (and thus both conditioners' relative bar) is an *optimistic upper bound*. Since both conditioners fail even against the optimistic baseline, the kills are robust; the true edge is only lower.
