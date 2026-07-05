# K-012 RESURRECTION — FINAL EVIDENCE LEG: v3 CAUSAL re-test
**Owner:** Arjun Rao (Head of Quant) · **Date:** 2026-07-05 · **Type:** PRE-REGISTERED SINGLE RUN (frozen spec; no parameter tuned after results).

---

## VERDICT

**The pre-registered test (c) FAILS. Forward per-Rs100-deployed is NOT > 0 at 1x costs: `-0.03` flat-100 (`-0.07` deploy-weighted), and `-2.36` at 2x-slippage stress.** Per the pre-registration there is no parameter shopping — **the number stands.** K-012 does not resurrect on this leg.

**REAL / FRAGILE / FAKE → the FF *signal* is REAL (Nikhil's placebos stand, 100th pctile); the *strategy as specified* is FAKE-as-tradeable.** The term-structure edge exists in IV space but cannot be harvested through a 2nd-forward-month single-stock CE calendar: once entries are causal and fills are honest (volume-gated, D+1, tiered slip), forward P&L collapses to **zero at 1x and negative at 2x**. This is an **execution/vehicle death, not a signal death.**

**Single weakest assumption (the one that most moves the verdict):** the **D+1 fill timing**. Its optimistic alternative — same-day-close fills (arguably implementable: FF is computable ~15:15 from live quotes, order by close) — lifts forward to only **+0.99/Rs100 at 1x (EXPLORATORY, below)**, still a straddle-of-zero band `[-0.03, +0.99]` at 1x, and **both bounds die at 2x**. Even the most favourable defensible fill does not clear the firm's 2x certification bar.

---

## 1. Data lineage (files · rows · max dates)
- **Trade universe:** `intraday_options_strategy/buying/forward_factor_v2.parquet` — 4,585 rows / 205 syms / entry 2021-07-12 → 2026-05-08 (read-only legacy).
- **Slice:** large-cap gate (sym's first FF entry < 2024-01-01) ∩ FF≥0.25 = **673 trades / 54 syms** (Tara's `build_slice()`, asserted in code). BUILD (causal entry ≤2024-12-31) = 474; **FWD (causal entry >2024-12-31) = 199.**
- **Raw px/vol:** `intraday_options_strategy/datasets/raw/hf_index_options_1m/stocks_options/<SYM>/<EXPIRY>.parquet` (dual schema HF 1-min / bhavcopy daily) via **Tara's fill_audit loaders, reused verbatim** (`load_file/day_table/classify/leg_eval/find_defer/settle_fallback`) + the `dispersion_strategy` pricer.
- **Deliverables (this dir):** `ff_v3_causal.py` · `causal_per_trade.csv` (673 rows × 66 cols) · `causal_run.log` · `causal_run_summary.json`.

## 2. Guards / PIT / cross-checks passed
- **Engine reproduces v2 exactly:** recomputed-argmax vs stored parquet = **strike_match 1.000 / price_match(<0.01) 1.000 over n=673.** My FF pipeline == the source engine.
- **Causal signal set = argmax signal set:** 673/673 stored FF≥0.25 cycles recompute to max-over-leads FF≥0.25 (proven: max≥0.25 ⇔ some lead≥0.25). **FWD signal count = 199 — matches Tara's 199 attempts exactly** (no wild divergence to diagnose).
- **Causality:** entry = FIRST lead (calendar order 30→25→20→15→12) with FF≥0.25 computed at D's close; **no argmax, no window peeking.** Fills at **D+1** (T3 same-bar). Sizing cap **pinned at 6.0** (not a full-sample median → no cap lookahead).
- **Denominator law:** per-Rs100-deployed / flat-100 only; **never pnl/back-premium.** Primary metric = flat-100 mean of pnl100 (drops→0), the same convention as Tara's +3.88 and the +10.04 headline; deploy-weighted ratio-of-sums shown alongside.

## 3. DECOMPOSITION LADDER (all rungs = CAUSAL entry; only frictions differ)
Metric = **flat-100 / Rs100-deployed** (drops counted as 0) · deploy-wtd in parentheses.

| Rung | Definition | BUILD (n=474) | **FWD (n=199)** |
|---|---|---|---|
| **Anchor: argmax ds flat-1.5%** | v2 peak-pick entry, ds prices @ D (reproduces headline) | +12.27 | **+10.04** |
| Anchor: argmax ds zero-slip | " , zero slippage | +16.77 | +14.86 |
| **Anchor: causal ds flat-1.5% (A3)** | first-cross entry, ds prices @ D | +11.19 | **+8.87** |
| Anchor: causal ds zero-slip | " , zero slippage | +15.68 | +13.65 |
| **(a) causal frictionless NO-GATE** | day_table D+1 fills, no drops, **zero slip** | +10.10 (+11.09) | **+8.75 (+9.14)** |
| **(b) causal GATED, zero-slip** | ex-ante gate + D+1 drop rule, zero slip | +1.38 (+4.15) | **+2.30 (+5.87)** |
| **(c) causal GATED + tiered 1x** | **THE VERDICT NUMBER** | **-0.51 (-1.52)** | **-0.03 (-0.07)** |
| **(c) causal GATED + tiered 2x** | firm 2x certification stress | -2.40 (-7.19) | **-2.36 (-6.02)** |

**Isolations (FWD):**
| Effect | Step | Cost |
|---|---|---|
| **T9 entry-timing leak** (peak-pick → causal) | argmax +10.04 → causal A3 +8.87 | **-1.17** |
| Frictionless-baseline consistency | causal ds-flat +8.87 ≈ (a) day_table-zero +8.75 | (D+1 timing ≈ the 1.5% slip removed) |
| **Fill-rate cost** (gate + drops) | (a) +8.75 → (b) +2.30 | **-6.45** |
| **Slippage cost** (tiered 1x) | (b) +2.30 → (c) -0.03 | **-2.33** |

**Filled-trade economics (c, 1x):** FWD survivors n=81, **win 51.9%, PF 0.99** (literal break-even), avg_win +11.60 / avg_loss -12.64, worst -40.26. BUILD survivors n=185, win 48.1%, **PF 0.84**, worst -56.45. **In-sample (BUILD) is itself negative at (c)** — there is no honest edge even before the OOS split.

## 4. PER-YEAR (causal entry year · flat-100 / Rs100 · drops→0)
| Year | n_sig | n_fill | (a) frictionless | (b) gated 0-slip | **(c1) VERDICT** | (c2) 2x |
|---|---|---|---|---|---|---|
| 2021 | 27 | 14 | +25.60 | +1.80 | **-0.98** | -3.75 |
| 2022 | 126 | 66 | +11.42 | +0.10 | **-2.34** | -4.77 |
| 2023 | 120 | 62 | +12.07 | +2.05 | **-0.13** | -2.31 |
| 2024 | 201 | 43 | +6.01 | +1.74 | **+0.48** | -0.78 |
| 2025 | 171 | 65 | +10.05 | +2.61 | **+0.59** | -1.43 |
| 2026 | 28 | 16 | +0.79 | +0.40 | **-3.81** | -8.01 |

At (c1) only 2024/2025 are positive and both are ≈0 (+0.48, +0.59); at 2x **every year is negative.** The headline's "all years positive" (Nikhil's frictionless per-year) was a property of frictionless fills + peak-pick entry, not of a tradeable strategy.

## 5. Reconciliation vs Tara's FILL_AUDIT (+3.88 fwd)
Both are gated+tiered, drops→0 over 199 fwd. Tara's convention = **argmax entry + same-day fill + post-hoc drop**; mine (c) = **causal entry + D+1 fill + ex-ante gate.** Decomposing the gap (all FWD, flat-100):

| Operating point | FWD /Rs100 |
|---|---|
| Tara: argmax + same-day + post-hoc-drop + tiered 1x | **+3.88** |
| EXPLORATORY: causal + ex-ante-gate + same-day + tiered 1x | **+0.99** |
| **(c) VERDICT: causal + ex-ante-gate + D+1 + tiered 1x** | **-0.03** |

- **Entry-rule + gate-policy change** (argmax+drop → causal+ex-ante-gate), same-day held fixed: **+3.88 → +0.99 = -2.89.** Of this, the *pure* peak-pick→causal timing effect is **-1.17** (§3 anchor); the remaining **≈-1.7** is the ex-ante gate *admitting* trades Tara's post-hoc drop threw away — those trades enter on later, fillable-but-weaker leads and are net-negative. **The liquidity gate does not rescue the strategy; it replaces "drop and book 0" with "enter worse and book a loss."**
- **Fill-timing change** (same-day → D+1), causal+gated held fixed: **+0.99 → -0.03 = -1.02.**
- Total Tara→(c): -3.91. ✓ (3.88 − (−0.03))

## 6. EXPLORATORY rung (label: EXPLORATORY · +1 family trial · CANNOT enter the verdict)
**causal + gated + SAME-DAY-CLOSE fills + tiered 1x.** Rationale: FF is computable ~15:15 IST from live option quotes and orders are placeable by close, so same-day-close is the *optimistic-but-arguably-implementable* bound; D+1 (the verdict) is the conservative bound.

| | BUILD | FWD |
|---|---|---|
| flat-100 / Rs100 | **+0.12** | **+0.99** |
| deploy-weighted | +0.31 | +2.48 |
| survivors (win / PF / worst) | 205 (48.8% / 1.03 / -76.70) | 84 (57.1% / 1.42 / -45.23) |
| same-day drops | **0 / 289** | — |

**Key mechanic:** same-day fills survive **289/289** gated cycles (0 drops) — because the ex-ante gate already guarantees the back leg traded on D, so filling on D itself is always possible. This is precisely why same-day is the optimistic bound. Even so the FWD optimistic number is **+0.99/Rs100 at 1x** — marginal, below any edge hurdle, and it would not survive 2x (per-year 2021 -2.51 / 2022 -2.41 / 2026 -2.31 already negative even at 1x).

## 7. Honest flags (what surprised me)
1. **Nikhil's T9 catch was real but small (-1.17), NOT the killer.** The `max(tdays1[-lead-1], m2_start)` clamp collapses most cycles to 1–2 distinct candidate days (the 2nd-forward month lists late), and FF usually first-crosses 0.25 *at* its peak — so causal ≈ argmax for ~92% of cycles. The decisive damage is **Tara's leg**: fill-rate (-6.45) + slippage (-2.33) = **-8.78**, which is exactly the full frictionless-(a)→verdict-(c) drop (+8.75 → -0.03).
2. **The ex-ante liquidity gate is counter-productive here (+3.88 Tara → +0.99 same-day-gated).** Forcing entry onto a lead where the back leg is liquid moves you to a weaker-signal / later day; those rescued trades lose money. Dropping was *better* than gating. Neither clears costs.
3. **No in-sample edge either.** BUILD (c1) = -0.51. The strategy is not "decaying" — it was never honestly positive, in or out of sample. This retires any "regime-carried edge" narrative for this vehicle.
4. **PF = 0.99 on FWD survivors** — the fillable trades are a coin-flip. The apparent +2.05–2.24 PF of prior legs lived entirely in frictionless fills / peak entry.
5. **The signal is not dead — the vehicle is.** FF's directional content (Nikhil: 100th-pctile vs matched placebos; inverted FF flips sign) is intact. If K-012 is ever revisited it must change the *instrument*: shorter back-leg tenor (near/next serial), index-level calendars, or a liquid-underlier-only universe — a Structurer (Aakash) problem, not a signal-research problem. Logged for KILLED_IDEAS resurrection conditions.

## 8. Verdict (memo format)
**REAL/FRAGILE/FAKE = signal REAL, strategy FAKE-as-tradeable.** Forward per-Rs100 at (c) = **-0.03 (1x) / -2.36 (2x)** — fails > 0 at 1x, fails hard at 2x. Pre-registered, single run, no re-tuning: **the number stands. K-012 stays killed on this vehicle.** Weakest assumption = D+1 fill timing; its optimistic same-day resolution (+0.99 fwd, EXPLORATORY) still fails the 2x bar. Recommend the resurrection be **closed on the calendar vehicle** and any future FF work re-open only with a liquidity-native instrument.
