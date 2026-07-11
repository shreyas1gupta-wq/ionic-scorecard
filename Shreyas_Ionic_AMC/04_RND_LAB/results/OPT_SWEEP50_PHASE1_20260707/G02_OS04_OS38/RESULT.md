# G02 — OS-04 (VIX-pctile-gated short strangle) & OS-38 (VIX-sizing overlay)
Phase-1 FAST/CHEAP triage · Arjun Rao (Quant) · 2026-07-07 · campaign OPT-SWEEP-50
Verdict: **OS-04 = SURVIVE (fragile)** · **OS-38 = KILL**

## Data lineage (verified on disk, not from spec)
- NIFTY index options: `intraday_options_strategy/datasets/raw/hf_index_options_1m/options/NIFTY/*.parquet` — 262 expiry files, 1-min, cols {timestamp(tz-aware IST), o/h/l/c, volume, open_interest, strike, option_type CE/PE}. **NO delta/IV columns** → 16Δ approximated by 1-SD moneyness (K = spot·exp(±1·σ·√T), σ=INDIA VIX/100). Range 2021-05→2026-06.
- INDIA VIX: `datasets/index_daily/india_vix.parquet` (2591 rows, 2016→2026) → PIT trailing-252d percentile + min-max IV-rank (≥60d history required).
- NIFTY spot: `datasets/index_daily/nifty50.parquet` (2581 rows). Costs: COST_STANDARDS.md 1x (STT 0.1% sell, exch 0.035%, slippage 0.25% prem/leg, GST, ₹20/order).

## Conventions (pre-registered, held)
Signal from prior-close (S) VIX-pctile + spot → **fill = next-liquid-quote (D+1 first bar ≥09:15, vol>0)**; no-fill/zero-vol strike = DROP (D-031). **Exit-period booking** (one P&L per trade, never spread across holding days). Exit = 50% max-profit / 2× credit stop / expiry-intrinsic (OS-03: +21-DTE management close). Edge in ₹-POINTS + %-of-SPOT (never %-premium). Regime split at 2025-09-01 (Tuesday-expiry break) — not pooled-only. Engine: `scratchpad/bt_g02.py`; trades in `trades_OS01_weekly.csv`, `trades_OS03_monthly.csv`.

## Guards / degenerate detectors
- No same-day-close fill (A.17 optimistic bound avoided). Exit-period booking (my #1 lesson — no fake-low variance).
- Denominator-free %-spot (A.2/A.8). No net-debit denominator (strangle = credit).
- Win 73-78% with WL 0.42-0.44 = the STRUCTURAL short-strangle payoff (many small wins, few full-credit losses), **not** an artifact. No Sharpe>4, no R²>0.98 equity, no ADV/exercise leak. Index legs deep → sidesteps A.14 exitability wall.

## Validation battery (per-trade, 1x cost)
| Setup | N | ₹-pts/trade | %-spot/trade | Sharpe(ann) | Win | WL | pre-Sep25 ₹pts (N) | post-Sep25 ₹pts (N) |
|---|---|---|---|---|---|---|---|---|
| **OS-01 weekly [baseline]** | 261 | +4.56 | +0.0245 | 0.48 | 73.2% | 0.44 | +0.42 (223) | +28.82 (38) |
| **OS-03 monthly [baseline]** | 37 | +5.19 | +0.0259 | 0.32 | 62.2% | 0.86 | +5.38 (33) | +3.67 (4) |
| **OS-04 VIX-gate >60pct** | 96 | +14.4 | +0.0701 | **0.67** | 78.1% | 0.42 | +7.22 (81) | +53.16 (15) |
| OS-38 overlay on OS-01 | 261 | +5.59 | +0.0291 | 0.58 | 73.2% | 0.44 | +0.42 | +28.82 |
| OS-38 overlay on OS-03 | 37 | +3.68 | +0.0178 | **0.28** | 62.2% | 0.86 | +5.38 | +3.67 |

Frictionless↔1x: costs ~1.2-1.5 pts/trade — edge survives cost easily for all (cost is NOT the binding constraint). Frictionless OS-04 = +16.1 pts / +0.078% / Sharpe 0.74.

**Decisive diagnostic — weekly per-trade edge by VIX-percentile bucket (1x):**
| VIX pctile | N | ₹-pts | %-spot | std %-spot | win |
|---|---|---|---|---|---|
| <40 | 134 | +1.10 | +0.012 | 0.263 | 71.6% |
| 40-60 | 31 | -11.03 | -0.063 | 0.300 | 64.5% |
| 60-80 | 49 | +0.18 | -0.006 | 0.445 | 69.4% |
| **>80** | 47 | **+29.23** | **+0.149** | **0.537** | 87.2% |

## Verdicts

### OS-04 — SURVIVE (FRAGILE) → Phase-2 with mandate
Passes ALL pre-registered kills: (1) 1x edge >0 in BOTH ₹-pts (+14.4) and %-spot (+0.070); (2) beats parent OS-01 on risk-adjusted terms (Sharpe 0.67 vs 0.48, mean 3.2×); (3) NOT pooling-only — positive in BOTH regimes (pre +7.22, post +53.16); (4) already uses next-liquid-quote fill.
**Weakest assumption (why FRAGILE):** the ENTIRE uplift lives in the >80th-pctile bucket (+29.2 pts). The 60-80 slice — which the ">60" gate admits — is dead (+0.18 pts, -0.006%/spot). The gate is being *credited for a >80 effect*. That bucket is also the **highest-variance regime** (std 0.537 vs 0.263 baseline — 2×), i.e. exactly the CIO book-rule-#1 correlated left-tail, and effective N is small (47 useful trades), recency-tilted (15 of the best post-Sept-2025). Sharpe 0.67 is far below the campaign Sharpe>2 bar. **Phase-2 must:** re-cut the gate at >80 (drop 60-80), size PER-TRADE, and test INCREMENTAL Sharpe over the existing short-vol book (S-04/S-05) — standalone Sharpe here is largely high-VIX regime beta.

### OS-38 — KILL (A.19 overlay rule)
Linear IV-rank multiplier (0.5×–1.5×) **fails to beat its parent on OS-03** (Sharpe 0.28 < 0.32; mean 3.68 < 5.19 — it down-weighted the profitable monthly trades) and only **marginally** beats OS-01 (+0.10 Sharpe, inside noise for N=261 fat-tailed). An overlay that helps one mandated parent and hurts the other is not a robust uplift. Its only real signal is the same high-VIX VRP-richness tilt that OS-04 harvests more directly — **redundant + non-robust**. Killed.

## Caveats (Phase-1, not certification)
16Δ is a VIX-moneyness proxy (no delta in data); OS-03 uses a conservative 21-DTE close (understates monthly theta) and N=37 is thin; baseline OS-01 is itself marginal (Sharpe 0.48, edge concentrated post-break) — conditioner verdicts are relative (same engine, apples-to-apples). Sept-2025 post-window is only 15-38 trades. These are ranking numbers, not Gate-4.
