# S-04 Short Strangle (14-DTE, managed 50%) — Gate-4 Sensitivity Report

**VERDICT: PASS-WITH-FLAGS** (flags F1-F5 below; none individually fatal, F1+F2 jointly decide the paper review)

**Date:** 2026-07-04 | **Owner:** Dr. Sameer Bhat, Overfit & Sensitivity Analyst (E-027) | **Run:** `results/S-04/20260704_sensitivity/`
**Scope:** mandatory Gate-4 battery per RESEARCH_SOP (parameter perturbation, plateau, subsample stability, decay). DSR/PBO predate this task (unchanged, /oos-audit owns); this run adds **33 configurations to the S-04 family trials ledger** — count them in any future DSR.
**Basis:** all edges on the registered basis (gross minus 1x 2.1%/leg slippage, as baked in `strangle_managed`). The flat cost stack shifts every cell ~-0.021%/spot at the certified 2x stress (cost-cert arithmetic). Denominator rule: %/spot AND rupees per Rs.6,00,000 lot.

## 0. Reproduction (validity precondition)
Rebuilt the certified pipeline verbatim (same loaders, guards imported). Center cell (dte14/otm5/pt50): **bit-exact P&L on all 5,031 registered keys** (max |diff| = 0.000000%; common-key mean exactly +0.2241%). Rebuild n=5,084: the +53 extra trades are **T10 data drift** — Angel 2026 daily appends moved per-symbol `data_end`, so the L7 no-future-settlement guard now admits 53 Jan-Jun-2026 expiries it had correctly excluded at build time (their mean +0.7445%; none beyond the registered max expiry). Guard behaving as designed; drift documented in the D-028 lookahead audit. Grid below uses the n=5,084 rebuild.

## 1. Parameter perturbation — 27-cell grid (edge %/spot | Rs/lot)
Entry DTE {12,14,16} x OTM band {4%,5%,6%} x profit-take {40%,50%,60% of credit}. Full grid in `grid.csv`.

| | pt40 | pt50 | pt60 |
|---|---|---|---|
| **dte12** otm4 | +0.197 (1,183) | +0.171 (1,025) | **+0.127 (761) = worst cell** |
| dte12 otm5 | +0.208 (1,246) | +0.176 (1,055) | +0.137 (823) |
| dte12 otm6 | +0.208 (1,251) | +0.170 (1,022) | +0.139 (834) |
| dte14 otm4 | +0.274 (1,642) | +0.246 (1,476) | +0.207 (1,244) |
| **dte14 otm5** | +0.267 (1,605) | **+0.229 (1,377) = CERTIFIED** | +0.192 (1,152) |
| dte14 otm6 | +0.255 (1,527) | +0.218 (1,311) | +0.181 (1,085) |
| dte16 otm4 | **+0.327 (1,959) = best cell** | +0.321 (1,927) | +0.272 (1,631) |
| dte16 otm5 | +0.308 (1,850) | +0.286 (1,717) | +0.243 (1,456) |
| dte16 otm6 | +0.312 (1,870) | +0.276 (1,653) | +0.260 (1,557) |

- **27/27 cells positive. No sign flip anywhere.** Worst cell retains 55% of the certified edge.
- Sensitivity per dimension (at center of the other two): DTE 12/14/16 -> +0.176/+0.229/+0.286; PT 40/50/60 -> +0.267/+0.229/+0.192; OTM 4/5/6 -> +0.246/+0.229/+0.218. All gradients smooth and monotone.
- **Stop-loss dimension is a NO-OP: the certified config has no stop.** (Same trap class as the S-01 iv-cap no-op — a perturbation on a parameter that does not bind is not a trial.) Additive stop tests at center: stop@1.5x credit -> +0.192 (-16% edge); stop@2.0x -> +0.219; **stop@2.5x -> +0.230 (edge unchanged) while worst trade improves -27.8% -> -17.2% and std falls 17%.** Logged as a PRE-REGISTERED candidate for a paper A/B — adopting it post-hoc from this grid would be selection on the same data (see F5 logic).

## 2. Plateau check — PASS (both forms)
- **Certified cell vs its 26-cell +/-1-step neighborhood median: ratio 0.995** (+0.2295 vs +0.2306). The certified config IS the plateau median, not a spike. [DATA]
- SOP form (best cell dte16_otm4_pt40 = +0.327 vs its 7 corner-step neighbors, median +0.274): **ratio 1.193, inside the <=1.20 rule** — marginal, but it is a monotone boundary effect, not an isolated spike.
- **Honest read of the monotone-in-DTE surface:** dte16 beats dte14 in all 9 (otm,pt) pairs. Two implications, both true: (a) *robustness* — the certified point was clearly chosen by convention (Tastytrade-style mechanics), not fitted; a fitted config would sit at the surface peak. The gradient direction (more DTE, tighter strikes, earlier take = more vol premium harvested per trade) is exactly what a real short-vol risk premium looks like, not a data artifact. (b) *undersized DTE* — the surface rises to the grid boundary, so the DTE optimum is UNBRACKETED; 16 may not be the top either (per-day edge still favors it: 0.0179 vs 0.0164 %/spot/day). The correct response is a pre-registered dte16+ extension study, NOT a post-hoc swap to the best cell — chasing the boundary maximum from this grid is precisely the overfit move this report exists to prevent (and a T9 violation per LOOKAHEAD_CONTROLS).

## 3. Subsample stability — sign stable in 17/17 slices; worst = 2025
From `subsamples.csv` (center config, n=5,084):

| Slice | n | Edge %/spot | Rs/lot | Hit | Worst |
|---|---|---|---|---|---|
| 2021 / 2022 / 2023 | 86 / 337 / 440 | +0.714 / +0.473 / +0.439 | 4,284 / 2,837 / 2,632 | 88-94% | -8.7 / -16.8 / -12.7% |
| 2024 | 1,036 | +0.162 | 972 | 84% | -16.2% |
| **2025 (WORST)** | **2,018** | **+0.081** | **483** | 84% | **-27.8%** |
| 2026 | 1,167 | +0.362 | 2,174 | 87% | -20.3% |
| IV tercile low/mid/high (entry-credit proxy) | ~1,695 ea | +0.126 / +0.157 / +0.406 | 755 / 942 / 2,434 | 83-90% | — |
| Odd / even trades | 2,542 ea | +0.251 / +0.208 | 1,507 / 1,247 | 85/86% | — |
| Regime: 2022 rate shock / 2024 election / 2026 YTD | 337 / 177 / 1,167 | +0.473 / +0.605 / +0.362 | — | — | no catastrophic slice |
| Era: HF-minute / bhavcopy-daily | 1,717 / 3,367 | +0.413 / +0.136 | — | — | time-confounded with decay |

- **No sign flip in any slice** — the automatic-FAIL trigger does not fire.
- **F1 — 2025 is near-breakeven:** +0.081%/spot (Rs.483/lot). It survives the certified 2x-cost stress (~-0.021pp) by ~6bp but is ~zero at the punitive slippage band (-0.06 to -0.08pp). The most recent full year alone would not clear the promotion rule with headroom.
- Edge is concentrated in the high-IV tercile (+0.406 vs +0.126 low) — coherent with a vol-risk-premium mechanism (you get paid when premium is rich), and it argues for an IV-conditional entry filter as a *pre-registered* refinement, not a retrofit.
- Era split (+0.413 minute-era vs +0.136 daily-era) mostly re-expresses time decay (the daily-schema window is Apr-2024 onward); flagged, not independently interpretable.

## 4. Decay read — the honest extrapolation
Yearly edge (%/spot): 2021 +0.714 -> 2022 +0.473 -> 2023 +0.439 -> 2024 +0.162 -> 2025 +0.081 -> 2026 +0.362.

| Fit | Slope (pp/yr) | Edge hits zero |
|---|---|---|
| Build (+0.306, mid 2023-11) vs forward (+0.184, mid 2025-10) | -0.064 | **2028-09** |
| Yearly OLS, all years | -0.092 | **~2027.5** |
| Yearly OLS, excluding 2026 | -0.158 | **~2025.4 — i.e., already past** |

**F2 — the zero-cross ranges from "already dead" to "late-2028" and the spread is decided entirely by the 2026 datum (+0.362, n=1,167).** 2026 sits on the least-verified data (Angel-appended window; the cost cert flagged its credit spike — mean reconstructed credit 6.0% vs ~1.3% in 2023-25) and monotone decay through 2025 (+0.71 -> +0.08) is the base case a skeptic would take. If the linear ex-2026 trend holds, the live edge is ~zero today. If 2026 is real, the edge mean-reverts with IV regimes rather than decaying linearly. **Paper trading is the instrument that resolves this; do not size up before it does.**

## 5. Structural findings (not parametric — true in every cell)
- **F3 — crash-blindness is structural.** Worst trade -22.9% to -29.3% of spot in ALL 27 cells; early-exit rate 68-88% in all cells; no stop-loss exists. No parameter choice inside this family removes the naked left tail — it is the design. Compounding it: data begins 2021-07, so **no 2018/2020-class crash exists anywhere in-sample**; the tail-seller profile (high win rate, W/L < 1) has never been stress-tested by history in this backtest. Sizing must come from RISK_LIMITS / stress-replay, never from this grid's means. The stop@2.5x result (Section 1) is the cheapest structural mitigation on the table for paper A/B.
- **Fill honesty (measured):** buyback-print availability is NOT the problem — 99.0% of early-exit triggers used same-day prints; forcing same-day-only prints (variant_fresh) moves the edge -0.0002pp; requiring positive prints (variant_pos) changes nothing (zero-print contamination = 0 after the 2026-07-03 disk cleaning). What remains unmeasured is *fill-at-print realism*: EOD-close trigger vs a live resting limit (trigger direction conservative, fill-price direction optimistic) and thin-strike executability — sample audit of 300 entries: **2.3% priced off a print NOT from entry day (up to 12 days away = NO FILL under the new circuit rule) and 5.0% had a leg with zero traded volume on entry day** (~7% of entry fills suspect; exit-leg buyback volume not in the trades data — named gap, paper desk). **F4.**

## 6. Verdict detail
**PASS-WITH-FLAGS.** Plateau clean (0.995x), 27/27 cells positive, all 17 subsample slices sign-stable, bootstrap CI95 on the certified edge [+0.170, +0.287]%/spot excludes zero, reproduction bit-exact. The edge as backtested is not a parameter artifact.

| Flag | What | Owner action |
|---|---|---|
| F1 | 2025 subsample near-breakeven (Rs.483/lot; ~zero at punitive 2x band) | Paper desk: weight recent-period reconciliation |
| F2 | Decay zero-cross spans 2025.4-2028.9; hinges on flagged 2026 data | Monthly /edge-decay; no size-up pre-paper |
| F3 | Structural crash tail (-28%/spot), no stop, no crash regime in data | Risk office sizing; pre-registered stop@2.5x paper A/B |
| F4 | ~7% of entry fills suspect under circuit/thin-volume rule; exit-volume gap | **Paper desk measures FIRST** (below) |
| F5 | DTE surface monotone to boundary — optimum unbracketed | Pre-registered dte16+ study only; no post-hoc swap |

**Single weakest assumption (named, as pre-flagged): managed-exit fill optimism.** Refined by this run's evidence: it is NOT print availability (cleared, 99% same-day) — it is the assumption that a 4-fill strangle round-trip actually executes at those prints with only 2.1%/leg slippage on single-stock strikes where ~5-7% of entry-days show zero traded volume, using an EOD-close trigger as a proxy for a live resting buy-back order. **The paper desk's first measurement: realized buyback fill price vs the 50%-of-credit trigger level, and fill success rate on thin strikes, vs Angel quotes.**

## Files
- `results/S-04/20260704_sensitivity/sensitivity_S04.py` — battery engine (guards imported)
- `grid.csv` (27 cells + 6 variants) | `subsamples.csv` (17 slices) | `config.json` (plateau/decay/bootstrap/stale-print numbers)
- `trades_all_configs.parquet` (167k rows) | `verify_and_volume_sample.py` + `entry_fill_volume_sample.csv/.json` (reproduction proof + fill audit)
- Companion: `results/S-04/20260704_cost_cert/LOOKAHEAD_AUDIT.md` (D-028)

*Signed: Dr. Sameer Bhat (E-027), Overfit & Sensitivity Analyst, Risk Office — 2026-07-04*
