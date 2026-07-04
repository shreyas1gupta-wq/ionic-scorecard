# RED TEAM — S-03 FF-Calendar Resurrection (K-012), leg 2 of 3
**Owner:** Nikhil Bose (Red Team) · **Date:** 2026-07-05 · **Charter:** kill the claim "the FF signal was always real; only the sizing was broken." The hypothesis I was told to prove: *the entire improvement is a sizing mechanic (down-weight expensive premium) that would rescue ANY entry rule.*

---

## VERDICT

**On the assigned question — is +Rs10/Rs100 a pure SIZING ARTIFACT? → NO. EDGE-BEYOND-SIZING (decisive).**
Under the IDENTICAL premium-capped sizing, the FF>=0.25 book beats every matched placebo at the **100.0th percentile**. Sizing applied to a random / premium-matched / trade-everything entry rule yields ~0. My assigned kill FAILED — the sizing-artifact charge is wrong.

**On the resurrection as a whole (my REAL/FRAGILE/FAKE) → FRAGILE.**
The FF signal is real, BUT the headline +Rs10/Rs100 is an **optimistic ceiling** for two reasons neither the kill nor the recheck flagged:
1. **Cost-fragile:** survives 2x costs (+5.48) but dies at ~3.3x (5% slip -> -1.26). The edge lives in cheap/mid strikes (CE_be Rs15-43) where flat 1.5% slippage is likely fiction.
2. **T9-class entry-timing LOOKAHEAD (NEW CATCH):** the engine enters each cycle at its *argmax-FF* day across a [30,25,20,15,12]-session window (`forward_factor_v2.py` L55-76). Not tradeable in real time; v1 used a causal "earliest-hit" rule, v2 silently switched to non-causal "peak-FF." Inflates the absolute number by an amount not measurable from the stored artifact.

**What flips FRAGILE -> REAL:** forward per-Rs100 > 0 on a fresh OOS under BOTH (a) realistic thin-strike slippage and (b) a CAUSAL entry rule (fixed-lead or earliest-FF-cross, engine re-run emitting all leads). The sizing verdict does NOT need this — it is already settled.

**Fraction of the +Rs10.5/Rs100 forward that survives each attack:**
| Attack | Survives | Note |
|---|---|---|
| Turnover-matched random (mandatory) | **~100%** | S at 100.0 pctile; random median -0.21 |
| Uniform random | ~100% | S at 100.0 pctile; random median -0.40 |
| Premium-avoidance (drop dear quartile) | replicates only **+1.10 (~10%)** | FF adds the other ~90% |
| CE_be-matched random (decisive) | **~100%** | S at 100.0 pctile; matched-premium median +0.10 |
| Inverted ff<0.25 | sign flips to **-4.76** | FF is directional |
| 2x costs | **52%** (+5.48) | binding constraint |
| ~3.3x costs (5% slip) | **0%** (-1.26) | dies |

---

## REPRODUCTION CHECK (SOP: reproduce before attacking)
Premium-capped rule reverse-engineered exactly (no sizing script was saved): `n_i = min(100/CE_be_i, 3*median(100/CE_be)=6) ; sized_pnl = n*pnl ; deploy = n*CE_be`. This is **mathematically the ratio metric** (sized_pnl ~= 100*pnl/CE_be = 100*ret) — i.e. the very denominator the kill flagged, re-expressed as sizing.

| Stat | Brief target | Reproduced | Match |
|---|---|---|---|
| n | 673 | 673 | exact |
| win% | 71.8 | 71.77 | exact (sizing can't change sign) |
| avg_win / avg_loss | 29.2 / -33.1 | 29.21 / -33.15 | exact |
| PF | 2.24 | 2.24 | exact |
| total rupees | 7812 | 7812 | exact |
| worst | -464 | -464 | exact |
| fwd per-Rs100 | +9.91 | +10.04 (flat-100) / +10.54 (deploy-wtd) | within convention (~7% denom nuance) |

Data: `intraday_options_strategy/buying/forward_factor_v2.parquet` (read-only legacy). L=large-cap (first entry <2024) = 2175 candidate cycles (one peak-FF row each); S=FF>=0.25 = 673 (474 build / 199 forward). Forward rupee total = +1998 over 199 trades.

---

## PLACEBO BATTERY (all under the identical premium-capped sizing, entry-date build/forward split)

| # | Placebo | Build /Rs100 | Fwd /Rs100 | Reads as |
|---|---|---|---|---|
| — | **S: FF>=0.25 (real)** | **+13.36** | **+10.54** | the claim |
| — | Trade-everything (ignore FF) | +0.04 | **-0.45** | sizing alone = nothing |
| 1 | Turnover-matched random (2000 draws) | — | median **-0.21** (p95 +3.69); S at **pctile 100.0**; only 46% of draws >0 | random doesn't turn positive |
| 2 | Uniform random (2000 draws) | — | median **-0.40**; S at **pctile 100.0**; 43% >0 | same |
| 3 | Premium-avoidance (drop top-CE_be quartile, ignore FF) | +2.31 | **+1.10** | avoiding dear premium recovers ~10% only |
| 4 | Inverted ff<0.25 | -6.28 | **-4.76** (PF 0.58) | FF is directional, sign flips |
| H | **CE_be-matched random** (match month-count AND premium quartile, 2000 draws) | — | median **+0.10** (p95 +3.80); S at **pctile 100.0**; 51% >0 | **FF is NOT a low-premium proxy** |

Placebo H is the decisive one: forcing the random book to carry the same premium profile AND turnover still leaves S at the 100th percentile. The improvement is **FF selection**, not the sizing/premium mechanic. Trade-everything (-0.45) proves the sizing rule manufactures nothing on its own.

## CONFIRMATION the forward +10.5 is not itself an artifact
- **Concentration:** top-5 fwd trades = 23% of fwd rupees; drop them -> +8.29. Drop top symbol (APOLLOHOSP, 12%) -> +9.52. Broad. PASS.
- **Denominator (CE_be quartile):** fwd/Rs100 = Q1_cheap +12.35 / Q2 +24.89 / Q3 +5.92 / Q4_dear -0.76. Edge is BROAD (Q1-Q3), peaks in Q2 (CE_be~43), NOT concentrated in the cheapest denominator bucket -> not a small-CE_be inflation. PASS.
- **Per-year (premium-capped):** 2021 +12.15 / 2022 +13.60 / 2023 +21.70 / 2024 +8.56 / 2025 +11.63 / 2026 +6.50. **All years positive** (vs kill's equal-weight points 2024 -2.16 / 2025 -10.84). PASS, mild fade in 2026 (n=28).
- **Bootstrap forward (5000x):** mean +10.54, **p5 +3.87 (>0)**, 99% of resamples positive. PASS.
- **FF gradient (fwd/Rs100):** FF<0 -9.27 / [0,.25) +5.11 / [.25,.5) +1.74 / [.5,.75) +14.86 / [.75+) +15.26. Real term-structure response; **the sharp edge is FF>=0.5** — the 0.25 floor is not the cleanest cut.
- **Lookahead on the cap:** full-sample median cap vs expanding-median PIT cap -> both +10.54, identical. Cap is a benign sizing parameter. CE_be (sizing input) is entry-time known. PASS.

## D-028 LOOKAHEAD ATTACK — 2 most suspicious surfaces
1. **In-sample cap median (T6-flavor):** TESTED — expanding-median PIT cap = full-sample cap = +10.54. **Clean.**
2. **Peak-FF entry timing (T9-class, NEW LEAK):** `forward_factor_v2.py` L55-76 keeps the **argmax FF** across leads [30,25,20,15,12] sessions-before-expiry (L75 `if ff > best[0]`). To pick the max-FF day you must observe the whole window -> future info decides the entry date. v1 (`forward_factor_strategy.py` L26) used a causal "earliest hit wins" rule; **v2 changed to non-causal peak-FF.** No perfect T1-T10 home (in-window optimal-entry selection) — flag for taxonomy. **Cannot be quantified from the artifact** (only the peak row is stored — same degeneracy Arjun flagged for the random-entry null). Common to S and all placebos, so it does NOT change the sizing verdict, but it caps the trustable level of the absolute +10/Rs100. **Gating fix: re-run run_once emitting all leads, book on a fixed-lead / earliest-FF-cross entry, re-test forward.**

## Files
- `RED_TEAM_FF_RESURRECTION.md` (this) · `placebo_distributions.csv` (P1/P2 draws) · `ce_matched_dist.csv` (placebo H) · `placebo_summary.json` · `confirm_summary.json`
