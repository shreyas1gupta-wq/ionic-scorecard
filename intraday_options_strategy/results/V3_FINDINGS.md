# V3 FINDINGS — the 0DTE short-vol edge (real-data validated)

> ### ⚠️ SESSION 5 CORRECTION (2026-06-15) — read first, supersedes headline
> The "Sharpe ~2.9-3.4" below used the EOD-extrapolated IV multiplier m≈0.96.
> We then pulled REAL intraday option candles via Angel SmartAPI
> (`data\angel_calibrate_live.py`) and measured the ATM IV/VIX multiplier
> **AT THE ACTUAL 09:20 ENTRY**: real m ≈ **0.78-0.81** (cleaner than the
> 15:30 EOD figure). Re-running S3 at the real m (`run_vrp_realm.py`):
> - **m=0.80, 2% slip → fund Sharpe ≈ 1.65 (IS 1.49 / OOS 1.85), WR 64%, PF 1.96**
> - m=0.80, 1% slip → Sharpe ≈ 2.0 ; m=0.85 → ~2.2 ; m=0.75 (pessimistic) → ~1.2
> **Revised verdict: the 0DTE edge is REAL and clears Sharpe>1.5, but the margin
> is THIN — ~1.6-2.0, not ~3 — and sensitive to (a) the true m (fails below
> ~0.75) and (b) execution slippage.** IS≈OOS throughout (not overfit). Caveat:
> live m is ONE weekly cycle (6 pts, off-ATM on early days); EOD bhavcopy (2,673
> pts) gave 0.90. True morning m likely 0.78-0.88 → need more expiries to pin
> down. Net: a genuine but marginal edge requiring tight execution + an iron-fly
> tail cap; NOT the slam-dunk the synthetic run implied.

Session 4 (2026-06-12). This supersedes the V2 "rejected" verdict, which was
an artifact of two modelling errors found and fixed here.

## The chain of reasoning (and the two bugs that hid the edge)

1. **Got real option prices.** NSE F&O EOD bhavcopy (UDiFF + legacy), 399 days
   2021-2026, 2,673 ATM points → `data\calibrate_iv.py`.

2. **Bug #1 — calendar vs trading time (CRITICAL).** The engine measured
   time-to-expiry on a 365x24 CALENDAR clock. Intraday variance accrues only
   in the ~6.25 market hours/day, so calendar-time UNDERSTATES a 0DTE premium
   by sqrt(8760/1575) ~ 2x. The seller was credited ~half the real premium →
   spurious losses. Fixed: `clock='trading'` (375 min/day, 252-day year) in
   `engine_v2.simulate_orders`. This is the standard practitioner clock for
   intraday options and the single most important fix in the project.

3. **Self-consistent IV calibration.** Re-ran calibration in trading-time:
   real ATM IV / VIX = m ~ 0.90 (DTE=1), fit m(DTE)=0.897-0.086*ln(DTE),
   ~0.96 extrapolated to 0DTE (09:20 entry). Wired into `default_iv_mult`.
   (Calendar-time gave a non-comparable ~1.1; the 1.5 "break-even" in
   V2_REPORT was a calendar-clock artifact — disregard it.)

4. **Independent cross-check (Agent study).** `analysis\realized_vol_study.py`:
   intraday realized move averages 0.52% vs VIX-implied 0.79% (realized =
   0.66x implied); a hold-to-close straddle seller wins ~80% of days, +39
   pts/day gross. CONVENTION-FREE confirmation of the VRP. The fixed engine's
   +30-35 pts/day net now MATCHES this — two independent methods agree.

5. **Bug #2 — Sharpe annualisation.** `perf()` annualised per-TRADE-DAY
   returns by sqrt(252) but S3 trades only ~31 expiry-days/yr → overstated
   Sharpe ~2.5x. Fixed: report (a) per-deployment Sharpe (sqrt of actual
   trades/yr) and (b) fund Sharpe over the full calendar (idle days = 0).

6. **Realistic execution stress.** Per-leg slippage 0.5/1/2%; SL exits modelled
   as gap-through fills at the bar's actual adverse price x stop-slip 3x.

## Result (real m, conservative costs) — `results\vrp_realistic.csv`

| sleeve | sl | slip | WR | PF | trd/yr | avg/lot | worst/lot | Sharpe(fund) | Sharpe(fund,OOS) |
|---|---|---|---|---|---|---|---|---|---|
| **S3 0DTE** | 25% | 0.5% | 76.1% | 4.60 | 31 | +2607 | -5005 | **3.35** | 3.76 |
| **S3 0DTE** | 25% | 2.0% | 75.7% | 3.52 | 31 | +2259 | -6256 | **2.91** | 3.24 |
| **S3 0DTE** | 40% | 2.0% | 78.4% | 3.18 | 31 | +2205 | -9766 | 2.67 | 2.83 |
| S2 weekly-intraday | 25% | 0.5% | 65.8% | 1.54 | 49 | +247 | -7973 | 1.04 | 2.03 |
| S2 weekly-intraday | 25% | 2.0% | 48.7% | 0.68 | 49 | -219 | -9985 | -0.86 | 0.08 |

**Verdict.**
- **S3 (0DTE expiry-day ATM short straddle, 25% stop, exit 14:30): a genuine
  edge.** Fund Sharpe ~2.9-3.4 even at 2% slippage + gap-through stops; IS and
  OOS Sharpe consistent (~3.1 vs ~3.2) → not overfit. Clears the >1.5 bar with
  margin. This is the "best of the best" survivor.
- **S2 (weekly straddle held intraday): rejected.** Marginal at best slippage,
  negative at realistic slippage, IS often <0. Weeklies hold too much time
  value intraday — the theta isn't there until expiry day.

## Why this is real (mechanism, not curve-fit)
The edge is the intraday variance risk premium: options imply ~0.79% daily
move, Nifty actually moves ~0.52% intraday → the gap is the seller's margin.
It concentrates on 0DTE because that's where almost all remaining value is
pure time premium that decays within the session (no time value left to give
back at exit). The 25% stop converts the fat left tail into a bounded loss;
1-min monitoring makes the stop realistic.

## REMAINING RISKS / caveats (must resolve before capital)
1. **Biggest unknown: true 0DTE-MORNING premium (m).** m=0.96 is EXTRAPOLATED
   from EOD DTE>=1; real 09:20 expiry-day IV needs INTRADAY option quotes to
   confirm. Edge has margin (survives to m~0.8) but this is the #1 validation.
2. **No smile/skew/pin-risk in synthetic pricing**; real near-expiry fills can
   be worse than even 2% slip on fast days.
3. **Tail:** worst day -6k to -10k/lot here, but a budget-day/global-shock gap
   could be multiples. ADD: hard event-day filter (have it) + DEFINED-RISK
   WINGS (iron fly) to cap the catastrophe; current test is a naked straddle.
4. **Capacity/correlation:** ~31 trades/yr single-instrument. Diversify across
   Nifty/BankNifty/FinNifty/Sensex expiries for ~daily deployment, but straddle
   P&L is highly correlated on trend days → diversification adds frequency, not
   tail protection. DD governor (built) is essential.

## Next steps
1. Acquire INTRADAY 0DTE option quotes (even a few months) → confirm m at
   09:20; re-run. 2. Add iron-fly defined-risk variant + re-test tail. 3. Build
   the multi-expiry/instrument portfolio via the allocator. 4. 30-day Angel One
   paper run to measure real slippage/fills. 5. Live on Kotak Neo only if paper
   slippage keeps fund OOS Sharpe > 1.5 and the iron-fly caps tail < 2% equity.
