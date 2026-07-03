# S-04 — Short-Strangle 2×-Cost Survival Certification (D-M1)

**Date:** 2026-07-04 · **Owner:** Arjun Rao (Quant Head) · **CEO decision:** NO full re-shuffle — certify survival only.

## Result
**VERDICT: SURVIVES (REAL).** The registered edge **+0.2241%/spot** (mean `strangle_managed`) remains **net-positive in 12/12 cells** across the 2%/3%/4% premium × {1.0%, 2.1%, 3.0%} 2×-slippage grid, and remains positive even under the most punitive double-count reading (worst cell +0.0194%/spot). Promotion rule (net-positive at 2× the full approved stack) is **met**.

## Data lineage
| Item | Value |
|---|---|
| Trade file | `intraday_options_strategy/buying/shortlist_shortvol.parquet` |
| Rows | 5,031 trades · 209 symbols · entry 2021-07-15 → 2026-06-16 · exp → 2026-06-30 |
| Registered-edge column | `strangle_managed` mean = **+0.2241%/spot** [DATA, verified] |
| Avg hold | 13.9 calendar days (~14 DTE entry, managed@50% TP) |
| Managed early-exit (hit 50% TP) | 79% of trades → blended buyback ≈ 0.52× credit |
| Empirical entry credit | reconstructed n=1,752 (1/3-symbol sample): mean 2.27%/spot, **median 1.30%/spot** [DATA] |
| Credit builder | `intraday_options_strategy/buying/shortlist_shortvol.py` |

## Critical lineage fact (the load-bearing subtlety)
`strangle_managed` **already carries 1× slippage of 2.1%/leg** — `SLIP = fr.slippage_pct("stock","near_otm") = 0.015 × 1.4 = 0.021`, applied as `(1±SLIP)` on every premium leg in `sell_pnl`/`buy_pnl` (shortlist_shortvol.py L36, L114-118). It does **not** carry brokerage / STT / exchange txn / GST / stamp / SEBI. So the registered 0.2241% = **gross − 1× slippage**, nothing else. An honest 2× test therefore adds back the baked 1× slippage to recover gross, then subtracts 2× [slippage + full transaction stack].

Note: the code's baked 2.1%/leg is *above* the COST_STANDARDS single-stock near-ATM floor (0.5–1.5%/leg); at 2× the approved band is 1.0–3.0%/leg — the tested grid — so 2.1% sits inside it.

## Arithmetic (all figures = % of spot; notional lot ₹6,00,000; 4 fills/trade)

**Why the cost stack is small in spot units:** slippage and STT/txn are charged on *option premium*, and premium is only 2–4% of spot. 2.1%/leg × ~3% credit ≈ 0.06%/spot per full round trip. The whole stack lands at ~0.05–0.20%/spot — below the 0.22%/spot edge. This is correct arithmetic, not an artifact.

### Survival grid (net edge after 2× full stack)
| Premium assumption | 2× slip 1.0%/leg | 2× slip 2.1%/leg | 2× slip 3.0%/leg |
|---|---|---|---|
| EMPIRICAL 2.27% | +0.243% | +0.205% | +0.174% |
| 2% credit/spot | +0.238% | +0.205% | +0.178% |
| 3% credit/spot | +0.254% | +0.203% | +0.162% |
| 4% credit/spot | +0.269% | +0.202% | +0.147% |

gross edge used = registered +0.2241% + add-back 1× slip (varies +0.064% to +0.128% by premium). **All 12 cells net-positive.**

### Robustness (self-red-team)
- **Reconciliation:** net = reg + 1×slip − 2×slip − flat-stack, exact match to engine (+0.2034% at 3%@2.1%). ✔
- **Buyback stress** (3% credit, 3% slip): even if held legs pay 1.0× credit to close → net +0.119%. ✔
- **Most-punitive double-count** (treat registered as already-net, then subtract a *full extra* 2× slippage + full stack): worst cell 4% credit @ 3% slip = **+0.0194%/spot, still positive.** ✔

## Guards
| Guard | Status |
|---|---|
| L7 no-future-settlement | PASS — builder drops `exp > data_end` per symbol (shortlist_shortvol.py L75) |
| L7b physical bounds | PASS — builder drops `strangle_managed > 6%/spot` corrupted marks |
| Exit-period booking | PASS — P&L booked in exit month (monthly() on `exp`), no spreading |
| Stable denominator | PASS — normalized by spot, not net-debit |
| Cost double-count check | PASS — baked 1× slippage explicitly identified and handled |

## Degenerate flags / caveats (must accompany the verdict)
- **[OPINION] Thin edge on a fat tail.** +0.22%/spot is a *mean* over a distribution with std 2.16%/spot, min −27.8%/spot. Survival of the mean certifies the **cost model**, NOT sizing. Per-trade Sharpe is modest; do NOT size off the monthly-averaged portfolio Sharpe (2026-07-04 IC-1 lesson: co-movement inflates portfolio SR by ~√N).
- **[DATA] 2026 credit spike.** Reconstructed 2026 mean credit = 6.0%/spot vs ~1.3% in 2023-25 — a fat right tail (95th pct 8.3%, max 39%) that inflates the *mean* credit to 2.27%. Likely far-strike/stale-print or the Angel-daily-appended window. The **median 1.30%** is the honest central credit; results are shown at 2/3/4% which bracket it conservatively. This does NOT affect the survival conclusion (higher credit → more slippage AND more edge headroom; all cells survive).
- **Scope:** this is a COST-SURVIVAL certification only, per CEO's no-reshuffle decision. It does NOT re-validate the edge's statistical reality (DSR/PBO/walk-forward) — that battery predates this task and is unchanged.

## Weakest assumption
**The 79% managed-early-exit rate and the buyback fraction (~0.52× credit).** If live fills fail to hit the 50% TP as often as the backtest assumes (fill optimism on the buy-back leg in single-stock options), realized edge compresses toward the hold-to-expiry number. Mitigated by the buyback stress above (survives to 1.0× credit), but this is the first thing to check in paper reconciliation.

## Files
- `results/S-04/20260704_cost_cert/cost_cert.py` — certification engine
- `results/S-04/20260704_cost_cert/config.json` — cost constants + survival summary
- `results/S-04/20260704_cost_cert/survival_grid.csv` — 12-cell grid
- `results/S-04/20260704_cost_cert/verdict_raw.txt` — full console arithmetic
