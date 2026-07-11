# G09 Phase-1 triage — OS-29 (jade lizard) + OS-15 (0DTE IC, regime-gated)
_Arjun Rao / Head of Quant · OPT-SWEEP-50 · FAST/CHEAP pass · 2026-07-07_
Engine: `bt_g09.py` · trades: `os29_trades.csv`, `os15_trades.csv` · log: `run.log`

## Data lineage
- NIFTY index options 1-min: `intraday_options_strategy/datasets/raw/hf_index_options_1m/options/NIFTY/` — 262 expiry files, 2021-05-27 → 2026-06-09.
- NIFTY spot 1-min: `.../index/NIFTY.parquet` (477,738 rows, 2021-05-24→2026-06-03).
- INDIA VIX daily: `datasets/index_daily/india_vix.parquet` (2,591 rows, 2016→2026-07-03).
- Costs: COST_STANDARDS.md @1x (broker ₹20/order, STT 0.1% sell + 0.125% exercise-intrinsic, exch 0.035%, GST 18%, slippage max(1 tick, 0.25% premium)). lot=75.
- Conventions honored: entry-fill = next-liquid-quote after 09:20 signal (first bar ≥09:20 with volume>0 per strike; no quote → DROP, D-031); 1-min ≥09:15; delta strikes via ATM-straddle-backed sigma (entry-time only); edge in ₹-points + %-spot; regime slice at 2025-09-01 (Tue-expiry break).

## Guards
PIT causal (all strike/flag inputs at entry only) ✔ · next-liquid-quote fill ✔ · no-fill=DROP ✔ · P&L booked in EXIT period (per-trade, expiry/close) ✔ · denominator-free ₹-points + %-spot (no return-on-premium) ✔ · regime split ✔. FAST pass: full DSR/PBO/walk-forward deferred to Phase-2.

---
## OS-29 — Jade lizard (short ~20Δ PE + short ~20Δ CE / long ~10Δ CE, credit ≥ call-spread width)
Entry ~4 sessions pre-expiry, hold to expiry (cash-settle). No-upside constraint enforced; if unbuildable → DROP.

| Slice | N | mean ₹pt | %-spot(mean) | median ₹pt | sd | pt-Sharpe | ann-Sharpe~ | win% | worst |
|---|---|---|---|---|---|---|---|---|---|
| ALL (pooled) | 152 | +8.09 | +0.038% | +52.9 | 125.6 | 0.064 | ~0.46 | 78.9% | −581.9 |
| PRE-Sep25 | 133 | +11.42 | +0.055% | +52.9 | 121.3 | 0.094 | ~0.68 | 80.5% | −581.9 |
| POST-Sep25 | 19 | **−15.18** | **−0.062%** | +49.1 | 153.8 | −0.099 | ~−0.71 | 68.4% | −357.8 |

Buildability: 258 weeks tried, **106 (41%) DROPPED** — the no-upside jade lizard (credit ≥ call-spread width) was unconstructable in low-VRP weeks; strategy only tradeable ~59% of cycles.

**Degenerate flags:** win 78.9% with **W/L ratio 0.325 (<0.5)** → TRIPS the "high-win / thin-payoff" short-vol detector. avg win +56.8 vs avg loss −174.7; worst-5 = −582/−495/−448/−401/−389 ₹pt. Classic naked-short-put tail (jade lizard caps upside only). One week = −582pt ≈ −23% of ~12%-notional margin.

**Verdict: FRAGILE → KILL-FOR-CAMPAIGN (does not advance).**
- Pooled edge is honestly positive (+0.038%/spot) but ~5× below the campaign bar (edge ≈ S-04 ⁄ 4; ann-Sharpe 0.46 vs bar 2; XIRR ≈ 15-16% on margin vs bar 50%).
- Trips kill criterion #2: edge is a PRE-Sep-2025 phenomenon (+0.055%); POST-break it is **negative** (−0.062%, N=19) — does not survive the regime break.
- Pure short-vol beta: correlated with S-04/S-05; incremental Sharpe over the existing short-vol book ≈ 0 (CIO book rule #1). Full left tail intact.
- Fill: results already ARE next-liquid-quote (criterion #3 baked in), so no further haircut — but 41% undroppable-to-no-upside is a real capacity limit.

---
## OS-15 — 0DTE iron condor, REGIME-GATED on an intraday IV-crush detector (K-005 resurrection)
I built a **minimal, honestly-causal IV-crush flag** (entry-time only, a-priori FIXED thresholds — no in-sample fitting):
`crush = prior-day INDIA VIX < 15  AND  opening gap < 0.30%  AND  first-15min realized range < 0.20%`.
0DTE IC = sell ~20Δ CE+PE / buy ~10Δ wings at 09:20, exit 15:10 quotes.

| Slice | N | mean ₹pt | %-spot | pt-Sharpe | win% | total ₹pt |
|---|---|---|---|---|---|---|
| ALL (ungated = K-005) | 259 | −2.38 | −0.011% | −0.087 | 68.0% | −616 |
| **CRUSH=TRUE (gated)** | 11 | **−3.40** | **−0.016%** | −0.210 | 54.5% | −37 |
| CRUSH=FALSE | 248 | −2.33 | −0.011% | −0.084 | 68.5% | −578 |

**Verdict: FAIL — K-005 STAYS KILLED (this detector).** The minimal causal detector fired 11× and the gated 0DTE IC was **negative and WORSE than ungated** — the gate destroys value, it does not create it. Ungated 0DTE IC re-confirms K-005 (−0.011%/spot, negative). Resurrection condition NOT met.
- Honest limitation: this falsifies ONE simple detector, not the whole hypothesis space. A detector with genuine predictive power for intraday realized-vol collapse (distinct from just selling calm days) remains the only — now still unmet — resurrection path. Treat as **BLOCKED-PENDING-A-VALIDATED-DETECTOR**; the cheap one doesn't work, so no Phase-2 slot.
- Detector spec for any future attempt: must predict, at 09:20 on expiry day, that the day's realized move stays inside the short strikes with a hit-rate that beats the unconditional 0DTE IC out-of-sample under walk-forward — using only pre-entry info (VIX term-structure, overnight/opening realized, morning straddle richness relative to trailing norm). My fixed-threshold proxy shows calm-morning gating alone has no edge.

## Weakest assumption (both)
Strike selection uses a single ATM-straddle-implied sigma (0.7979 approximation) rather than per-strike IV — fine for triage delta-bucketing, but Phase-2 must reprice with a real IV surface. For OS-29 the load-bearing risk is the un-hedged short-put tail (−582pt), which no Phase-1 metric rewards and which sizes with the whole short-vol book.

**Neither setup advances to Phase-2.** OS-29 = sub-bar, regime-decaying short-vol beta; OS-15 = detector fails, K-005 stays killed.
