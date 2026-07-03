# S-03 FF-Calendar — Pre-IC Incremental Shuffle (D-M2 prep)

**Date:** 2026-07-04 · **Owner:** Arjun Rao · **Gate-5 deliverable for the S-03 IC.**

## Result
**VERDICT: FAKE (as a forward timing edge) — DO NOT advance to IC. Pre-registered KILL K3 fires.**

The registered +11.4% forward "return" is a **denominator artifact** (P&L normalized by the back-leg premium `CE_be`). Booked on **P&L points (denominator-free rupees per spread)**, the large-cap FF>=0.25 slice is **build +5.85 pts / forward −9.30 pts** — the forward book **loses money in rupees**. FF selection carried an edge in 2021-23 and has been net-negative in 2024-25 (the FF-decay already noted in firm memory), confirmed here on the ex-ante large-cap gate.

## Data lineage
| Item | Value |
|---|---|
| File | `intraday_options_strategy/buying/forward_factor_v2.parquet` |
| Rows | 4,585 total · 205 symbols · entry 2021-07-12 → 2026-05-08 |
| FF>=0.25 (full universe) | 1,494 rows [DATA — note: task said "2,612 candidates"; does NOT match this build, flagged] |
| Return formula | `filtered_portfolio.py` L59-60, CE-leg calendar, SLIP=0.015, denom = `CE_be` |
| Large-cap gate | symbols with a FF candidate before 2024-01-01 = **54 symbols** (ex-ante liquid, avoids retro-list lookahead) |
| Large-cap FF>=0.25 slice | **673 trades, 54 symbols** [DATA] |

## Decomposition

### (a) FF selection vs shuffle — booked on P&L POINTS (the honest metric)
| Null | Base pts | Null mean | Incremental | p | Reads as |
|---|---|---|---|---|---|
| N1 within-month FF shuffle | +1.36 | −9.04 | +10.40 | 0.003 | "adds" — **but build-period only** |
| N3 random-entry (no FF) | — | — | — | DEGENERATE | not testable on this file |

**N1 "adds" is misleading:** the within-month shuffle null goes deeply negative (−9.0 pts) because permuting FF re-selects trades that lose in the build period; the ACTUAL FF picks the build-period winners. This is in-sample selection skill that **does not carry forward** (see the forward split). N1 tests FF-VALUE reassignment, not the forward reality.

**N3 is degenerate (disclosed):** `forward_factor_v2.py::run_once` stores only the **peak-FF entry per (sym, cycle)** — each (sym, month) group has exactly one candidate, so "random entry per group" has zero variance (sd=0). The parquet does **not** contain the alternative within-cycle calendars, so a true random-entry-timing null is **not computable from this artifact**. To do it properly, the upstream engine must emit all candidate leads, not just the argmax-FF one. Flagged as a build requirement.

### (b) Per-year + build/forward (large-cap FF>=0.25 slice)
| Year | n | ratio ret% | **P&L points** | hit |
|---|---|---|---|---|
| 2021 | 27 | +13.8% | +6.84 | 67% |
| 2022 | 126 | +15.1% | +9.23 | 69% |
| 2023 | 120 | +25.9% | **+15.23** | 74% |
| 2024 | 196 | +8.9% | **−2.16** | 71% |
| 2025 | 176 | +12.5% | **−10.84** | 76% |
| 2026 | 28 | +7.3% | +3.05 | 61% |
| **BUILD** ≤2024-12-31 | 474 | +15.2% | **+5.85** | 71% |
| **FWD** >2024-12-31 | 199 | +11.4% | **−9.30** | 73% |

The **ratio metric says every year is positive; the points metric says 2024 and 2025 lose.** The 73% forward hit-rate with negative mean P&L is the classic short-premium asymmetry (many small wins, occasional large loss) — a calendar is net-short front vega, and 2024-25 realized/expiry paths punished it. Note also the "positive-every-year in ratio" is exactly the partial-data / metric-choice trap flagged in the firm lessons.

### (c) Trials ledger (DSR honesty)
The FF pipeline's visible sweep (`forward_factor_v2.py` __main__): **2 slippage × 2 structures × 5 FF thresholds = 20 configurations**, plus the 5-lead peak-FF entry scan (`CHECKPOINTS`) and the separately-chosen FF>=0.25 floor. **Honest family-trials ≥ 20** (arguably ≥25). The task's "6+ per pipeline" **understates** it — any DSR on this family must use n_trials ≥ 20, which makes the deflation far harsher. This alone is grounds to not advance without a clean OOS re-run.

## Degenerate flags
- **Denominator inflation [DATA]:** corr(1/CE_be, ret) = +0.097; 4 trades with `CE_be<2` show mean-ret +29.6% but essentially zero rupee P&L (+0.03 pts). The ratio metric structurally amplifies small-back-leg-premium trades. This is the debit-denominator lesson (2026-07) recurring on the *return* denominator. **Book FF on points or on spot-normalized P&L, never on back-leg premium.**
- P&L concentration: top symbol APOLLOHOSP only 7% of |P&L|, positive without top-5 → NOT concentrated (K4 pass). The failure is broad decay, not one name.

## Verdict vs pre-registered kills
| Kill | Result |
|---|---|
| K1 within-month selection adds | PASS in points (p=0.003) — but build-only, non-forward |
| K2 base not negative both build & fwd | PASS (build +5.85, fwd −9.30) |
| **K3 forward mean > 0 in points** | **KILL — fwd −9.30 pts** |
| K4 no P&L concentration | PASS |

**K3 is dispositive.** A pre-registered kill fired. S-03 FF-calendar does not advance to IC as a forward timing edge.

## Weakest assumption / single fix
**The registered edge was measured in the wrong units.** `pnl/CE_be` is not a stable, investable denominator — it inflates when the back-leg premium is small (which co-occurs with high FF) and it hides the sign of the rupee P&L. The single fix: re-book the entire FF family on **P&L points or spot-normalized P&L**, emit all candidate entry leads (so a real random-entry null is computable), and only then re-consider — but the current forward evidence (−9.3 pts) says the edge has decayed and should be shelved with a resurrection condition (forward points > 0 over a fresh 12-month OOS).

## Files
- `results/S-03/20260704_shuffle/PRE_REGISTERED_KILLS.md` — kills written before compute
- `results/S-03/20260704_shuffle/ff_shuffle.py` — ratio-metric shuffle (initial, superseded)
- `results/S-03/20260704_shuffle/ff_points_decisive.py` — decisive points-based analysis
- `results/S-03/20260704_shuffle/config_points.json`, `points_decisive_raw.txt` — points results
- `results/S-03/20260704_shuffle/config.json`, `shuffle_raw.txt`, `null_distributions.npz` — ratio-metric run
