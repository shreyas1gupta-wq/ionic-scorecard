# G18 Phase-1 triage — OS-33 & OS-34 (Arjun Rao, Quant)
_Campaign OPT-SWEEP-50 · 2026-07-07 · FAST/CHEAP pass, rank-not-certify. NIFTY index options+spot, lot 75, costs @1x COST_STANDARDS._

## Verdicts
| Setup | Verdict | One-line |
|---|---|---|
| **OS-33** post-event vol-reset short strangle | **KILL (non-distinct)** | Post-event timing adds ZERO over a generic weekly strangle; the only uplift is a generic IV-rank filter = OVERLAPS-OS-04/S-04. |
| **OS-34** turn-of-month short strangle | **KILL** | Turn-of-month timing UNDERperforms the unconditional weekly strangle and cannot be validated in the post-Sep-2025 regime. |

## Data lineage
- Options: `intraday_options_strategy/datasets/raw/hf_index_options_1m/options/NIFTY/*.parquet` — 262 weekly expiries, 2021-05-27→2026-06-09, 1-min tz-aware.
- Spot: `.../hf_index_options_1m/index/NIFTY.parquet` (1-min, ≥09:15 auction guard applied).
- VIX: `datasets/index_daily/india_vix.parquet` (daily close 2016→2026-07-03; 252d rolling median for IV-rank).
- Events (OS-33): RBI MPC / FOMC / Budget dates **[INFERENCE] hardcoded from knowledge — verify home-net for Phase-2.** 77 event anchors.
- Trade tables: `os33_gated_trades.csv`, `os34_trades.csv` (this dir). Engine: `scratchpad/bt_g18b.py`.

## Conventions honored
Entry-fill = next-liquid-quote (first vol>0 bar ≥09:20 of entry session); same-day-close reported as optimistic bound. No-fill on zero-vol bars = DROP. Strikes ≈16Δ via σ = spot·(VIX/100)·√(DTE/365), rounded to 50. Exit = window/expiry close, **P&L booked in the exit period** (no spreading). Costs @1x (slippage 0.25% liquid-index/leg/side, STT 0.1% sell prem, exch 0.035%, brokerage ₹80/lot, GST, stamp). Edge in ₹-points + %-of-SPOT. Sep-2025 break not pooled for OS-34 timing.

## Results (net of 1x cost)
### OS-33 — the incremental-vs-base shuffle is the whole story
| Cut | N | net ₹-pts (mean/med) | net %-spot (mean/med) | win% |
|---|--:|--:|--:|--:|
| **Baseline** generic weekly-Mon strangle | 248 | 40.6 / 60.6 | **0.196 / 0.290** | 80.6 |
| OS-33 UNCONDITIONAL post-event (+2 sess) | 75 | 39.9 / 55.1 | **0.190 / 0.292** | 84.0 |
| OS-33 GATED (VIX≥med252 & RV3<0.85·VIX) | 19 | 51.5 / 73.1 | 0.256 / 0.378 | 84.2 |
| — GATED pre-Sep25 | 17 | 49.0 / 73.1 | 0.252 / 0.378 | 82.4 |
| — GATED post-Sep25 | 2 | 72.6 | 0.291 | 100 |
| — GATED same-day-close (optimistic) | 18 | 59.9 / 85.7 | 0.301 / 0.435 | 83.3 |

Reading: **unconditional post-event ≈ baseline to 3 decimals (0.190% vs 0.196%)** → the "sell 1–2 sessions after the event" thesis carries no incremental edge; a random weekly strangle earns the same VRP. The gated uplift (+0.06%/spot) comes entirely from an IV-elevated / realized-collapsed filter — i.e. a VIX/IV-rank gate, which is exactly **OS-04 / S-04**, not anything event-specific. N=19 (17 pre-break) is below the 30-trade/parameter bar.

### OS-34 — timing is a drag, not an edge
| Cut | N | net ₹-pts (mean/med) | net %-spot (mean/med) | win% |
|---|--:|--:|--:|--:|
| Baseline weekly-Mon (pre-Sep25) | 212 | 34.9 / 55.5 | **0.177 / 0.291** | 80.2 |
| OS-34 pre-Sep25 | 31 | 27.6 / 71.3 | **0.099 / 0.336** | 71.0 |
| OS-34 post-Sep25 | 1 | 190.2 | 0.756 | — |
| OS-34 same-day-close (optimistic) | 19 | 36.3 / 62.5 | 0.134 / 0.335 | 68.4 |

Reading: pre-break mean **+0.099%/spot is worse than the unconditional baseline +0.177%** — the ±3-session month-turn window is a *negative*-selection timing. Left tail dominates: 9 losers sum −1303 pts (worst −355), so mean (32.7) ≪ median (72.2). **47% no-fill drop (28/60)**; the surviving 32 are liquidity-biased (optimistic) yet still lose to baseline. **Post-Sep-2025 regime: N=1 — the day-of-month timing cannot be validated in the current regime**, which the kill design explicitly requires (no pooling across the break for OS-34).

## Kill-criteria audit
- **OS-33:** does not trip a *literal* hard kill (edge>0 both metrics, positive both eras, next-liquid-quote fill is conservative and still positive). **But fails the distinctness/incremental test** (governing lesson #1 + IC-1 incremental-vs-base): the distinct claim (post-event timing) = 0, residual edge = duplicate OS-04. → **KILL as a standalone family; do NOT consume a Phase-2 slot. Fold the IV-rank observation into OS-04's ledger.**
- **OS-34:** trips the regime-break kill (timing unconfirmable post-Sep-2025, N=1) and underperforms its unconditional parent; secondary flags = 47% no-fill and left-tail dominance. **KILL.** Matches OVERLAPS-expiry_seasonality → confirm-kill, route nothing new.

## Weakest assumption (single, per setup)
- **OS-33:** event dates are [INFERENCE] (memory, not exchange-verified). Even a ±1-day error is absorbed by the +2-session offset and does not rescue the verdict — the kill rests on unconditional-post-event = baseline, which is event-date-agnostic.
- **OS-34:** the 16Δ σ-proxy strike selection (no greeks in data). The 47% no-fill and liquidity-biased survivor set could *only* flatter OS-34; it still loses to baseline, so the proxy does not threaten the KILL.
