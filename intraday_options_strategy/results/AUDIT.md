# AUDIT — Nifty 0DTE/DTE1 Delta-Hedged Short Straddle

_Synthesis of five dimension audits (leakage, cost model, option pricing, delta-hedge accounting, metrics/sizing, data integrity) reconciled against six independent code-level verification verdicts. This document gates real capital — findings are stated at the severity that survives verification, not the severity originally flagged._

---

## 1. Overall trust verdict on the headline

**QUALIFIED PASS — the arithmetic is clean, but the headline OOS Sharpe ~3.6 is a synthetic-IV artifact, not a validated live edge.** Every "CRITICAL" cost/pricing bug flagged by the dimension audits was independently **REFUTED** at code level (brokerage *is* netted, GST scope *is* correct, the IV-time "2x" is a misread of a dimensionless vol ratio). The engine mechanics, leakage controls, walk-forward split, and calendar-based annualization are sound. **But the 3.6 number is priced on an extrapolated IV multiplier m(0)=0.96; the project's own live calibration finds real m≈0.80, which collapses the edge to Sharpe ~1.65–2.0 with a thin, slippage-sensitive margin.** The single number that should be reported to a capital allocator is the m=0.80 figure, not 3.6. Not deployable until live m is validated and the pre-2021 extrapolation segment is reported separately.

---

## 2. Confirmed issues (survived verification) by severity

Severity reflects the *post-verification* reality. "Confirmed-material" = real defect with a plausible path to mis-stating reported edge or live risk. Line references are as cited by the audits; verify against current source before acting.

| # | Severity | Location (file:line) | Confirmed issue | Impact on headline / capital | Fix |
|---|----------|----------------------|-----------------|------------------------------|-----|
| 1 | **CRITICAL** | `backtest/engine_v2.py:87-97` (`default_iv_mult`) + `data/calibrate_iv.py:77` + `results/live_iv_calibration.csv` | Default IV multiplier `m(0)=0.957` is **log-linearly extrapolated** from EOD DTE≥1 bhavcopy; real intraday 09:20 multiplier is **m≈0.78–0.81** per live calibration (V3_FINDINGS). The headline uses the optimistic synthetic m. | **This is the headline risk.** OOS Sharpe ~3.6 is computed at m≈0.96. At validated m=0.80 the edge falls to **Sharpe ~1.65–2.0** — real but thin and sensitive to slippage. Reporting 3.6 as the deployable number materially overstates expected edge. | Report the **m=0.80** result as the headline. Default `iv_mult=0.80` (or read `live_iv_calibration.csv`) rather than the formula default. Re-validate live m on each new week before trading. |
| 2 | **HIGH** | `data/calibrate_iv.py:77` + `datasets/iv_calibration_points.csv` (date range) | IV multiplier calibrated only on **2021-05→2026** NSE bhavcopy (~2,673 ATM pts). Backtest spans **2015–2026**; ~48% of the sample (2015–2020, incl. COVID) runs on **out-of-sample, extrapolated m(DTE)**. | Edge attribution pre-2021 is unvalidated across a different vol regime. Aggregate OOS metrics blend a calibrated and an extrapolated era without disclosure — survivorship/regime bias of unknown sign. | **Segment and report separately**: (a) 2015–2020 synthetic m, (b) 2021–2026 real m. Ideally acquire 2015–2020 intraday bhavcopy to recalibrate. Do not quote a single blended Sharpe. |
| 3 | **MODERATE** | `analysis/metrics.py:49-51` | Sharpe annualization uses `std*sqrt(252)` over **in-dataset trading days only**, not full calendar with idle days = 0 P&L (~1.22x inflation on annual data). | **Does NOT touch the headline** — the lead strategy (`run_dte01.py`, `run_daily_dh.py`) correctly reindexes to calendar (verified). Affects only the V1 intraday-signals strategy in `REPORT.md`. Creates a cross-codebase inconsistency / footgun. | Reindex daily P&L to full calendar before annualizing in `metrics.py`, matching `run_dte01.py`. |
| 4 | **MODERATE** | `config.py:21` (`LOT_SIZE=75`) | LOT_SIZE hardcoded to 75; PLAN.md SESSION 5 notes Angel master shows **NIFTY lotsize=65** — unverified. NSE lot history is volatile (50→75→50→25→75). | If true lot ≠ 75, position sizes off by ~15%; 0.6% risk budget drifts to ~0.69%. Feeds `position_sizer.py` (Kelly) and `run_today_live.py` — a **live-sizing** error, not a backtest-Sharpe error. | Verify current NSE Nifty option lot from Angel master / NSE before sizing. Update `config.py` and document the assumed spec. |
| 5 | **MODERATE** | `backtest/engine_v2.py:378-379`, `302/314` (`FUT_SLIP_PTS=0.5`); `383-386` (band) | Delta-hedge is **drift-dependent** (Nifty 2015–26 up-drift contributes positive hedge P&L; down-drift would degrade it) **and** futures slippage is a flat 0.5pt that ignores open/close/high-vol spread widening; rebalance band is delta-symmetric and ignores 0DTE gamma spikes. | Drift-dependence and slippage realism are *risk-characterization gaps*, not accounting errors — the audit's "+371 mean hedge P&L proves drift edge" framing was **refuted** as single-leg double-counting (drift P&L nets between hedge and option legs). Residual risk: Sharpe could degrade 20–40% in a down-drift regime; hedge cost +25–50% on volatile days. | Stress drift via down-market subset / sign-scrambled bootstrap / mirror-drift synthetic. Run `FUT_SLIP ∈ {0.3,0.5,1.0,1.5,2.0}` and band `∈ {0.10,0.15,0.25}` Sharpe envelopes (runner already loops band). |
| 6 | **MINOR** | `run_today_live.py:106` | Max-loss-per-lot proxied as `0.25*straddle0*LOT_SIZE`; a gap > 0.25*premium realizes more than budgeted. | Live sizing tends **conservative** (undersizing), but tail loss can exceed the 0.6% cap on a gap day. No backtest impact. | Backtest the empirical 0DTE straddle loss distribution; derive the true 99th-pct loss factor. |
| 7 | **MINOR** | `features/regime_filter.py:40` | VIX `ffill` could carry stale VIX across a multi-day data outage (untested). No-lookahead is correct (`shift(1)`). | Negligible on Kaggle INDIA VIX (gaps are lunch breaks, not week-long). Defensive gap only. | Assert max VIX gap ≤ 1 trading day. |
| 8 | **MINOR** | `data/angel_calibrate_live.py:123-128` | Same-day invariant (`t0.date()==d.date()`) is undocumented; logic would break silently under a refactor that broke it. | **Zero current impact** — `t0 = d + 09:20` holds by construction (verified) and this standalone utility does **not** feed the Sharpe pipeline. Code-clarity nit only. | Add `assert t0.normalize()==d.normalize()` or restructure date-agnostically. |
| 9 | **MINOR (cosmetic)** | `analysis/metrics.py:138` | Reported "avg theta/day" mixes a `/365` theta with the 252-day time model → that printed stat is off by ~1.45x. | Display-only. `theta` never enters P&L or returns (verified: P&L is driven by repeated `bs_price` re-pricing; only `delta` is consumed, for hedging). | Standardize theta convention or annotate the stat as calendar-day. |

---

## 3. Refuted / negligible (flagged by audits, dismissed on verification)

These were raised — several as **CRITICAL** — by the dimension audits but **failed independent code-level verification**. They do **not** affect the headline and require no action.

| Claimed issue (severity flagged) | Why refuted |
|---|---|
| **`fixed_cost` (brokerage) not deducted from `pnl_per_lot`** in `simulate_orders:275`, `simulate_delta_hedged:405`, `simulate_multileg:552` — flagged **CRITICAL** by 3 separate audits, alleged 2–8% P&L overstatement. | **REFUTED.** The split is deliberate and documented (`engine_v2.py:12-13`): brokerage is per-*order*, not per-*lot*, so it is carried as a separate `fixed_cost` column and applied once. **Every** consumer subtracts it — `allocator.py:129,136` (the actual Sharpe path, which scales `pnl_per_lot` by lots while applying `fixed_cost` once — correct), `run_v2.py:47,68`, `run_dte01.py`, `run_delta_hedge.py:32`, and all other runners. Folding it into `pnl_per_lot` as "the fix" would **overstate** cost by a factor of `lots`. The audit's claim that "only `run_vrp_test.py` corrects it" is the exact inverse of reality. Headline Sharpe is net of brokerage. |
| **GST applied only to NSE charge, may understate by understating GST on STT/SEBI** (`engine_v2.py:273,548`) — flagged MODERATE. | **REFUTED.** GST is correctly levied on brokerage + exchange + SEBI fee and **not** on STT (a separate statutory tax) — applying GST to STT *would* be the bug, which the code rightly avoids. The only true defect is missing GST on the SEBI fee (₹10/cr) ≈ **₹0.004/lot** (~0.02% of linear cost, ~20x smaller than the audit guessed). Zero Sharpe impact. Cosmetic. |
| **2x time-to-expiry inconsistency: IV calibrated at EOD applied to intraday entry → theta priced 2x too slow → inflates Sharpe** (`engine_v2.py:146-151` vs `calibrate_iv.py:76-79`) — flagged **CRITICAL**. | **REFUTED.** `default_iv_mult` returns `m = ATM_IV/VIX`, a **dimensionless ratio of two annualized vols** — time-independent. The engine computes `sigma = VIX*m` then prices with its own consistent trading-time `tte_years`. IV level `m` and time `t` are separate BS inputs; the EOD calibration instant does not propagate into the engine's `t`. No double-count, no theta error. (The genuine, separately-tracked nuance — extrapolating m to 0DTE — is issue #1 above, a calibration-value risk, not a pricing-time bug.) |
| **`angel_calibrate_live.py` date logic fragile / could break across midnight.** | **REFUTED.** `t0 = d + 09:20` is a derived constant; same-day holds by construction, and the file does not feed the Sharpe pipeline. (Retained as MINOR clarity nit, issue #8.) |
| **Theta `/365` vs 252-day clock biases backtest P&L / inflates Sharpe** (`bs_pricing.py:74`). | **REFUTED.** Theta is consumed in exactly two reporting-only places (`engine.py:197`, `metrics.py:138`); it never enters returns. P&L decay comes from re-pricing via `bs_price` on the consistent trading-time clock. (Retained as cosmetic display nit, issue #9.) |
| **Hedge P&L "+371 mean proves a drift edge" baked into the m=0.80/Sharpe~1.65 number.** | **REFUTED** as stated. The m=0.80/~1.65 naked figure comes from `simulate_orders`, which has **no hedge term**. The "+371" cites one leg of a delta-neutral pair — drift P&L nets between hedge and option legs. (The legitimate residual — *drift-dependence as a forward risk* — is retained as issue #5.) |
| All leakage / lookahead checks (indicators, ADX 5-min `merge_asof`, ORB gating, VIX `shift(1)`, signal→entry t→t+1, walk-forward IS/OOS split, intraday gate timing). | **CONFIRMED CLEAN** by the leakage audit — no action. Entry strictly post-signal-bar; folds non-overlapping; OOS fully separate; IV multiplier deterministic on DTE only. |
| Black-Scholes correctness (put-call parity <1e-12, IV round-trip 1e-10), partial-booking cost treatment, slippage direction, futures-vs-option slippage separation, order counting, intrabar combo bounds, 0DTE expiry-day gating, Kelly warm-up, max-drawdown & profit-factor formulas, 70/30 IS-OOS split. | **CONFIRMED CORRECT** — no action. |

---

## 4. Prioritised fix list

**Before reporting any final backtest number or committing capital:**

1. **[CRITICAL — blocks the headline] Re-headline at validated m=0.80.** Switch `default_iv_mult`/runs to the empirically validated intraday multiplier (or read `live_iv_calibration.csv`). The deployable expected edge is **Sharpe ~1.65–2.0**, not 3.6. Every downstream report and risk number must use this. _(Issue #1)_
2. **[HIGH] Segment 2015–2020 (extrapolated m) from 2021–2026 (calibrated m)** and report separately; never quote a single blended Sharpe. _(Issue #2)_
3. **[HIGH — live gate] Validate live m and resolve LOT_SIZE (65 vs 75)** from Angel master before sizing any position. Both directly drive live capital-at-risk. _(Issues #1, #4)_
4. **[MODERATE] Stress drift-dependence and slippage:** down-market / sign-scrambled bootstrap for hedge drift; `FUT_SLIP` and rebalance-band Sharpe envelopes. Report the worst-case Sharpe, not the up-drift one. _(Issue #5)_
5. **[MODERATE] Fix `metrics.py` calendar annualization** to remove the cross-codebase inconsistency (affects V1 reporting, not the lead strategy). _(Issue #3)_
6. **[MODERATE] Backtest the empirical 0DTE loss distribution** to replace the `0.25*premium` max-loss proxy in live sizing. _(Issue #6)_
7. **[LOW / hygiene] VIX-gap assertion; `angel_calibrate_live` same-day assert; theta-stat convention; SEBI-GST micro-fix.** Cleanup only — no impact on results. _(Issues #7, #8, #9, and the SEBI-GST nit)_
8. **[Process] Pre-deployment gate** per EXECUTIVE_SUMMARY: live NSE option-price validation, small-grid WFO, 30-day paper run. **Not deployable until complete.**

---

_Bottom line: the engine is honest and the arithmetic survives scrutiny — but the marketed 3.6 is a synthetic-IV figure. The real, defensible edge is roughly half that and conditional on a thin, slippage-sensitive margin. Report 1.65–2.0, validate live m, and treat 2015–2020 as out-of-sample before risking capital._

---

## 5. Post-audit resolution (Session 5g follow-up)

**Issue #1 — FIXED.** `default_iv_mult` now returns the live-validated 0.80 (was
extrapolated 0.96). Headline reported at m=0.80: naked 0DTE ~1.8, delta-hedged
0DTE ~2.6, combined DTE0+DTE1 ~3.6 (diversification, corr -0.02).

**Issue #5 (drift-dependence) — RESOLVED FAVOURABLY** (`run_drift_stress.py`):
- MIRROR-PATH (drift sign flipped, vol preserved): OOS Sharpe 2.65 → 2.58,
  hedge P&L 464 → 459. **Edge is drift-INDEPENDENT** (theta/gamma VRP, not
  direction) — confirms the audit's refutation of the "drift edge" alarm.
- UP vs DOWN day regimes: 1.61 vs 2.14 — works in both, better on down-days.
- Slippage×band envelope: at band 0.25, holds Sharpe 2.13 even at 4x base
  futures slippage (2.0pt); 2.65 at base. Only tight-band+heavy-slip → 1.06.

**Net:** the delta-hedged 0DTE OOS Sharpe ~2.6 is robust to drift and execution
stress. Remaining gates before capital: validate live m over more weeks (#1),
resolve LOT_SIZE (#4), segment pre-2021 (#2), 30-day paper run.
