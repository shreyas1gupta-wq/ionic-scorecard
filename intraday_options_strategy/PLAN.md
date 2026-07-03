# NIFTY 50 INTRADAY OPTIONS STRATEGY — MASTER PLAN & SESSION STATE

> **RESUME INSTRUCTIONS (read first in every new session):**
> 1. Read this file fully. It is the single source of truth — the original prompt is fully encoded here.
> 2. Check "CURRENT STATE" below for the last completed step and the exact next action.
> 3. Update CURRENT STATE + checkboxes at the END of every session before tokens run out.
> 4. Python: `C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe` (the `python` alias is broken — MS Store stub; always use full path or `py`).
> 5. Project root: `<NIFTY 500>\intraday_options_strategy\`. Data lands in `datasets\raw\`, processed in `datasets\processed\`.

---

## CURRENT STATE (update every session)

- **Last session:** 2026-06-11 (Session 2/3 — v1 Phases 1–3 COMPLETE, WFO running; **V2 ENSEMBLE built & first-run complete** — see `STRATEGY_V2.md` (design), `RESEARCH.md` (priors, web-verify pending), `results\V2_REPORT.md` (findings))
- **V2 state:** engine_v2 (multi-leg/short/partial-booking/trailing) + sleeves S2/S3/S4 + portfolio allocator (vol-parity, Kelly cap, DD governor) all built & validated. Sleeve correlations ~0 (diversification confirmed). **KEY FINDING: BS-at-VIX synthetic pricing is structurally biased against short-premium sleeves (real short-DTE IV > VIX; VIX includes overnight variance) — S2/S3 results are artifacts; do NOT tune them on this data. S4 ≈ breakeven (mildly optimistic sim).** Weekly expiries now correctly monthly before 2019-02-11 (option_selector fix).
- **TOKEN NOTE:** org hit subagent spend limit — NO multi-agent workflows; work single-threaded, save state every step. Research fan-out died; RESEARCH.md is from model knowledge, re-verify topics ONE PER SESSION with single WebSearch calls (topics list in RESEARCH.md header).
- **NEXT DATA MILESTONE (highest value): real option prices** — NSE F&O bhavcopy EOD (free archives / Kaggle mirrors: search "nifty options EOD bhavcopy"). Then: measure ATM-IV-vs-VIX multiplier by DTE bucket → re-price S2/S3 with sigma = m(DTE)×VIX → only then tune sleeves (small grids, WFO).
- **Status:** Full codebase built and tested. WFO at ~fold 9/126 (~2.7 min/fold). All folds so far `feas=False` (no combo meets WR≥55% ∧ PF≥1.5 ∧ DD≤20% in-window) — objective falls back to max-Sharpe. Pipeline-validation run (PROVISIONAL fold-1 params, NOT final): IS +6.6% total, OOS +6.2% total, WR ~41%, R:R ~1.6, PF 1.1, Sharpe negative (return < 6.5% rf because capital deployment is tiny: ~2.5 trades/day, Kelly halts on negative-edge stretches). Treat as plumbing validation only.
- **V1 COMPLETE (Session 3):** WFO 126/126 done; consensus f3/s34/o10 sl0.20 tg0.55 m10 (pct_feasible 0.8%). `main.py` ran → `results\REPORT.md`, 8 charts in `results\charts\`, robustness CSVs, `results\EXECUTIVE_SUMMARY.md`. V1 verdict: OOS +3.2% net, WR 40.7%, PF 1.14, R:R 1.66, Sharpe<0 (under-deployed). **WR≥55% target NOT met — long-option intraday has no edge.** Signal attribution: A1/A2 (trend) carry it OOS, A3 negative, mean-rev B1/B2 weak. Original-spec deliverables (Sections 8–10) ALL produced.
- **V2 DECISIVE RESULT (Session 3):** `run_iv_sweep.py` → break-even IV multiplier m=(real ATM IV/VIX): **S2 weekly-intraday straddle REJECTED (needs m≈1.8, reality ~1.1); S3 0DTE straddle is PRIME CANDIDATE (break-even m≈1.5, IS & OOS agree → not overfit; OOS PF 2.6/WR 61% at m=1.8).** Engine_v2 now has an `iv_mult` hook (per-DTE callable) = the real-data calibration point. See `results\V2_REPORT.md`.
- **REAL OPTION DATA ACQUIRED (Session 4, 2026-06-12):** NSE F&O UDiFF bhavcopy IS reachable (truststore + cookie-primed requests.Session; see `data\download_options_bhavcopy.py`). Bulk-downloading sampled 2021-06→2026-06 (step 3 bdays, ~435 days) filtered to NIFTY/BANKNIFTY options → `datasets\raw\options\fo_YYYYMMDD.csv`. UDiFF cols incl. UndrlygPric (spot), StrkPric, OptnTp, SttlmPric, XpryDt → enough to back out ATM IV per expiry. Added `implied_vol()` (Brent) to bs_pricing.py and `data\calibrate_iv.py` (computes m=ATM_IV/VIX by DTE bucket + log-extrapolates m(0DTE)). NOTE: EOD bhavcopy → DTE≥1 only (expiry-day EOD is intrinsic); m(0DTE morning) is EXTRAPOLATED from the DTE-curve (proxy; true value needs intraday quotes — caveat).
- **SESSION 4 BREAKTHROUGH — 0DTE short-vol edge VALIDATED. See `results\V3_FINDINGS.md`.**
  - Got real NSE option prices; found & fixed TWO modelling bugs: (1) CRITICAL calendar-vs-trading-time clock (calendar understated 0DTE premium ~2x → spurious losses); engine_v2 now `clock='trading'` default. (2) Sharpe annualised per-trade-day not per-calendar. Calibrated trading-time m(DTE)=0.897-0.086*ln(DTE) (~0.90@DTE1, ~0.96@0DTE) into `default_iv_mult`.
  - **VERDICT: S3 0DTE expiry-day ATM short straddle (25% stop, exit 14:30) = REAL edge. Fund Sharpe ~2.9-3.4 at conservative 2% slippage+gap-through stops, IS≈OOS (not overfit), WR ~76%, PF ~3.5, ~31 trd/yr. CLEARS Sharpe>1.5 with margin.** S2 weekly-intraday REJECTED (fragile). Cross-validated by `analysis\realized_vol_study.py` (realized 0.66x implied intraday).
  - Two agents used this session: code review (no critical bugs; engine trustworthy) + realized-vol study (independent VRP confirmation). Both findings folded in.
  - **SESSION 5 (2026-06-12) — data sourcing for intraday options. See `DATA_SOURCES.md`.** Declined dark-web/leaks (illegal/malware). Found & built legitimate layers: Angel One PUBLIC scrip master (`data\angel_scripmaster.py` → `angel_nfo_nifty.csv`, 1,776 NIFTY tokens, no auth) + ready-to-run SmartAPI fetcher/recorder (`data\angel_fetch_options.py`, needs user creds). `openchart` lib evaluated — its search returns only indices, not option contracts (dead end for option tokens). CONFIRMED: free historical EXPIRED intraday option data doesn't exist; only (a) Angel getCandleData for currently-tradable contracts, (b) forward live recording, or (c) paid (TrueData/GDFL). **Config flag: Angel master shows NIFTY lotsize=65, not 75 — verify before sizing.**
  - **SESSION 5b (2026-06-15) — REAL intraday m measured via Angel SmartAPI.** `data\angel_calibrate_live.py` pulled live 1-min ATM straddle candles for the 16JUN2026 weekly + real spot/VIX (Angel NSE index tokens 99926000 / 99926017). **Real ATM IV/VIX at 09:20 ≈ 0.78-0.81 (vs extrapolated 0.96).** Re-ran S3 at real m (`run_vrp_realm.py`): **fund Sharpe ≈ 1.65 (m=0.80, 2% slip), ~2.0 at 1% slip, IS≈OOS — clears 1.5 but THIN margin, sensitive to m (fails <0.75) & slippage.** V3_FINDINGS.md updated with this correction. NOTE: creds were used in shell this session → exposed in transcript; user says account is fund-less/disposable but rotate as hygiene.
  - **SESSION 5c (2026-06-15) — added & tested MORE strategies (see `results\STRATEGIES_COMPARISON.md`).** Extended engine for mixed long/short legs (`engine_v2.simulate_multileg`). Added iron fly (S5) + iron condor (S6) + tested trend rider (S4) combos. **Honest result: NONE beat the simple stopped naked S3 (Sharpe 1.79/OOS 2.01).** Iron fly worse (0.93 — wings cost > tail benefit when you can stop intraday); condor ~0; S4 negative-carry so blends DOWN. S3 gap/exit improvement sweep: baseline already near-optimal, worst day invariant to gap gate (irreducible intraday-trend tail). All short-vol variants 0.5-0.8 correlated = one trade; no other uncorrelated profitable edge found.
  - **SESSION 5d (2026-06-15) — DELTA-HEDGE BUILT & it's the winner.** `engine_v2.simulate_delta_hedged` + `run_delta_hedge.py`. Delta-hedged 0DTE short straddle (band 0.25, ~5 rebalances/day): **OOS Sharpe 2.74 (full 2.98), WR 79%, PF 4.65, maxDD/lot down 28% vs naked.** Hedge adds +464/lot (captures trend-day move the straddle loses). **LEAD STRATEGY = delta-hedged 0DTE short straddle, OOS Sharpe ~2.7.** See `results\STRATEGIES_COMPARISON.md`. Caveat: hedge P&L partly reflects Nifty up-drift 2015-26 → confirm on paper month; index used as futures proxy.
  - **SESSION 5e (2026-06-16) — NON-EXPIRY expansion. See `results\STRATEGIES_COMPARISON.md`.** Tested delta-hedged short straddle by DTE: only **DTE 0-1 work** (DTE0 Sharpe 3.15/OOS 2.72; **DTE1 day-before Sharpe 2.59/OOS 2.64, IS≈OOS robust**). DTE>=2 fails — non-expiry straddle is short VEGA, delta-hedge doesn't cover vega → IV-spike tail (-26k day). **COMBINED DTE0+DTE1 book: OOS Sharpe 3.61, ~75 deploy days/yr, corr -0.02 (diversifies, beats either alone).** `run_dte01.py`. Also ran today's LIVE 0DTE on real Angel prices (2026-06-16): net +Rs.66,061 (+0.66%), blotter in results\today_*.csv. **Session 5f BUGFIX: delta-hedge engine now charges the residual-futures unwind cost at exit (was closing it free; P&L was already MTM-correct/no-overnight, only the unwind slippage+brokerage was missing). Effect small: combined OOS 3.78→3.61. All delta-hedge numbers now post-fix.**
  - **SESSION 5g (2026-06-16) — backtest AUDIT (6-dim adversarial workflow) + option-buying tested. See `results\AUDIT.md`.**
    - **AUDIT = QUALIFIED PASS.** Engine arithmetic, lookahead/leakage, walk-forward, calendar annualization all CONFIRMED CLEAN. All 3 "CRITICAL" cost alarms REFUTED on verification (brokerage IS netted as separate fixed_cost per-order — folding into pnl_per_lot would OVERSTATE cost ×lots; GST scope correct; "2x TTE/theta" was a misread of a dimensionless vol ratio; theta is report-only, never in P&L). NO accounting bugs beyond the hedge-unwind one already fixed.
    - Confirmed-material issues: #1 default_iv_mult shipped 0.96 (optimistic) vs live 0.80 → FIXED (now returns 0.80). #2 IV calibrated only 2021-2026 but backtest spans 2015-26 → report OOS (2022-12+, within calibrated era) as headline, segment pre-2021. #3 metrics.py annualization (V1 only, not headline). #4 LOT_SIZE 65-vs-75 live-sizing. #5 delta-hedge drift-dependence → **RESOLVED FAVOURABLY** (run_drift_stress.py): mirror-path (flip drift) OOS Sharpe 2.65→2.58 = drift-INDEPENDENT (theta/gamma, not direction); works up-days 1.61 & down-days 2.14; holds Sharpe 2.13 at 4x futures slippage (band 0.25). Edge is robust.
    - **HONEST HEADLINE (m=0.80, validated live): naked 0DTE ~Sharpe 1.8; delta-hedged 0DTE ~2.6; combined DTE0+DTE1 ~3.6 (diversification). Not deployable until live-m re-validated over more weeks + drift stress + paper run.**
    - **OPTION BUYING tested (run_buying.py): REJECTED** — all variants negative CAGR (long 0DTE straddle -3.6%, mirror of seller's gain). Low capital + MDD<25% but no edge. **Low-capital+high-CAGR answer = iron fly (Rs.32k/lot, +25% CAGR-on-capital, MDD 17.8%, but Sharpe 0.74); proposed delta-hedged iron fly to get low-capital AND high Sharpe.**
  - **NEXT ACTIONS (priority order):**
    0. **Multi-instrument 0DTE/DTE1** — replicate the book on SENSEX (BSE Thu expiry) for ~2 more days/wk, low correlation → stacks. Needs BSE bhavcopy for backtest; live via Angel/Kotak fetcher.
    1. **Pin down m across more expiries** — run `angel_calibrate_live.py` weekly to accumulate 09:20 m (target 10-20 cycles). Lead strategy needs m≳0.78 at 2% slip; delta-hedge has more margin (Sharpe ~3 at m=0.80).
    2. Re-confirm delta-hedge hedge-P&L isn't drift-dependent: re-run on a detrended index path / both up & down sub-periods.
    3. 30-day Angel paper run (record real fills + real intraday m) → recalibrate → live on Kotak Neo if OOS Sharpe stays >1.5 after measured slippage.
    4. Fix config lot size 65 (not 75) before sizing.
    2. Add iron-fly DEFINED-RISK variant (buy OTM wings) to cap tail; needs engine_v2 signed/mixed-leg legs (currently single-side). Re-test tail vs naked straddle.
    3. Build multi-expiry/instrument portfolio (Nifty/BankNifty/FinNifty/Sensex 0DTE) via portfolio\allocator.py for ~daily deployment; mind trend-day correlation.
    4. 30-day Angel One paper run → measure real slippage/fills → feed back. Live on Kotak Neo only if paper keeps OOS fund Sharpe>1.5 and iron-fly caps tail <2% equity.
  1. **#1 priority — real option data.** Options to try (in order), save to `datasets\raw\options\`:
     - NSE official F&O bhavcopy archives — UDiFF format (2024+): `https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_YYYYMMDD_F_0000.csv.zip`; legacy (pre-2024): `https://nsearchives.nseindia.com/content/historical/DERIVATIVES/YYYY/MMM/foDDMMMYYYYbhav.csv.zip`. NOTE: NSE blocks bare requests — need browser-like headers + a prior GET to nseindia.com to set cookies; corporate proxy may still block. Has per-strike/expiry settlement price + OI (EOD only, no intraday).
     - kagglehub + truststore (worked before) — search slugs like "nifty options chain", "nse fno bhavcopy". Verify slug via one WebSearch first to avoid wasted downloads.
     - For 0DTE validation we mainly need EXPIRY-DAY ATM IV: even EOD settlement on expiry day + a few intraday option snapshots would calibrate m(0DTE).
  2. Measure real ATM IV vs India VIX by DTE bucket → fit `iv_mult(dte)` curve → replace `default_iv_mult` in `backtest\engine_v2.py`. Compare our BS premiums vs actual traded premiums on overlap days.
  3. Re-run `run_iv_sweep.py` + `run_v2.py` with the calibrated curve → confirm/reject S3. If S3 survives: small-grid WFO on S3 ONLY (gates: gap 0.3/0.4/0.5%, VIX cap 20/22/24, SL 20/25/30%, PT 50/60/70%), then add to portfolio allocator.
  4. 30-day Angel One paper run (execution policy in STRATEGY_V2.md) to calibrate real slippage/fills → feed back into cost model.
  5. Go-live gate (Kotak Neo): OOS PF > 1.25 after 2× cost stress on REAL prices.

---

## FULL SPECIFICATION (verbatim requirements — do not re-ask the user)

### S1. Objective & Constraints
- Rules-based intraday options strategy on Nifty 50. 10–30 trades/day (fewer OK if quality improves).
- Win rate ≥ 55%; Risk:Reward ≥ 1.5x net of costs; NO overnight positions — hard square-off 15:20 IST; no new trades after 15:20; strict SL on every trade; NO lookahead bias; validate OOS.
- Capital ₹1,00,00,000 (1 Cr). Sizing: Kelly × 0.25. Lot size 75 (adjust if data shows otherwise).
- Costs: brokerage ₹20/order flat; STT 0.0625% of premium (sell side); NSE txn 0.053% of premium turnover; GST 18% on (brokerage + txn charges); SEBI ₹10/Cr turnover; slippage 0.15% of premium per leg. Compute & print round-trip cost per lot explicitly.

### S2. Data
1. Kaggle 1-min Nifty 50 index OHLCV. Preferred: `debashis74017/stock-market-data-nifty-50-stocks`; else any Kaggle dataset with ≥3y of 1-min Nifty index data.
2. GitHub `https://github.com/debaonline4u/NSE-Data` — check for usable intraday CSVs.
3. India VIX daily (NSE CSV or Kaggle or yfinance `^INDIAVIX`); BankNifty 1-min if available (regime covariate); Nifty options chain historical if available on Kaggle.
4. Fallback: synthetic index proxy from top 10–15 Nifty constituents' 1-min data (equal- or float-weighted).
5. Print data audit: date range, #trading days, missing candles/gaps, quality issues, confirm no leakage.

### S3. Synthetic Options Pricing (no historical options data)
- Signal on bar close T → ATM/nearest strike CE (bullish) / PE (bearish). Strike = round(Nifty/50)×50.
- Weekly expiry (nearest Thursday); if <2 calendar days remain → roll to next week. DTE = calendar days.
- Black-Scholes: S = index at bar close; IV = India VIX (annualised; /√252 daily → per-minute as needed); if VIX missing → 20-day rolling realised vol (annualised). r = 6.5% p.a.; q = 1.2%.
- Compute BS premium at entry and exit/SL. Greeks at entry: Delta, Gamma, Theta/day, Vega. Report avg Delta & Theta-drag per trade.
- SL = entry premium × (1 − SL_pct); Target = entry × (1 + target_pct), target/SL ≥ 1.5. 15:20 hard close → exit at BS premium at 15:20 (reduced DTE).

### S4. Signals (compute on bars [t−n, t−1] + current CLOSE only)
- **A1** EMA(5)×EMA(21) cross on 1-min → CE/PE. **A2** VWAP cross (session-reset 09:15) with expanding volume. **A3** ORB: first 15 candles (09:15–09:29) high/low breakout + volume > 1.5× 20-bar avg.
- **B1** RSI(14) <30 → CE / >70 → PE, only when |price−VWAP| ≤ 0.5%. **B2** BB(20,2) touch (lower→CE, upper→PE), only when BB width in lower 30th percentile.
- **Mandatory filters:** C1 VIX>25 → no new trades (use prior day close if intraday missing). C2 ADX(14) on 5-min bars: >30 → trend signals only; <20 → mean-rev only; 20–30 → all signals at 0.5× size. C3 no trades before 09:30 or after 15:20. C4 skip RBI policy days & Union Budget days (hardcode/CSV).
- Combination: ≥2 confirming signals from different categories; composite score 0–3, trade only score ≥ 2.

### S5. Walk-Forward Optimisation
- 70% IS / 30% OOS (OOS untouched until final eval). Within IS: optimise 60 trading days → forward test 15 → step 15.
- Grid: SL_pct [0.20,0.25,0.30,0.35]; target_pct [0.35,0.45,0.55] (target/SL ≥ 1.5); EMA fast [3,5,8]; slow [13,21,34]; ORB minutes [10,15,20]; max trades/day [10,20,30].
- Objective: maximise (Net CAGR − 6.5%) / annualised daily-P&L vol, s.t. WinRate ≥ 55%, PF ≥ 1.5, MaxDD ≤ 20%.
- Report best params per fold + consensus params for OOS.

### S6. Position Sizing (Kelly × 0.25 on ₹1Cr)
- f* = (W×AvgWin − L×AvgLoss)/AvgWin from rolling 60-day fold stats (no lookahead). f_actual = 0.25×f*.
- C_risk = Capital × f_actual; Lots N = floor(C_risk / (BS_premium × 75 × SL_pct)).
- Min 1 / max 20 lots; total open delta notional ≤ ₹50L; premium outlay cap 10% of capital; re-estimate Kelly every 60 trading days.
- Log per trade: entry time, strike, CE/PE, expiry, entry premium, lots, capital at risk, delta, SL, target.

### S7. Backtest Engine
- Enter at NEXT bar open after signal (no lookahead). SL/target vs subsequent bars' high/low; both hit same bar → SL (conservative). 15:20 → exit at BS premium. One open position per signal type (CE+PE can coexist).
- P&L = (Exit−Entry premium) × 75 × lots − all costs. Compound capital. Daily equity DataFrame: [Date, Daily_PnL, Cumulative_PnL, Running_Capital, Daily_Trades, Win_Trades, Loss_Trades, Gross_PnL, Net_PnL_after_costs].

### S8. Metrics & Reporting
- Returns: total net P&L (₹,%), CAGR net, gross vs net CAGR. Risk: MaxDD (%,₹), DD duration, VaR 95/99 (historical), annualised vol. Risk-adjusted: Sharpe (rf 6.5%), Sortino, Calmar.
- Trades: totals (IS/OOS separately), trades/day (avg/med/min/max), win rate, avg win/loss ₹, profit factor, R:R, avg holding minutes, best/worst day, % profitable days.
- Costs: total ₹, % of gross, avg/trade. Attribution by signal (A1,A2,A3,B1,B2).
- 8 charts: equity curve (IS/OOS demarcated), underwater DD, daily P&L histogram + normal overlay, monthly heatmap, trades/day distribution, win-rate by signal, rolling 30d Sharpe, Kelly fraction evolution.

### S9. Robustness (on OOS)
- 9.1 slippage 0.25/0.50/1.00%. 9.2 costs ×2, ×3. 9.3 params ±10% → flag fragile if degradation >30%. 9.4 VIX>18 vs ≤18 regimes. 9.5 remove 10% trades randomly ×100 MC → median & 5th pct.

### S10. Code Structure (Python 3.10+, type hints, fixed seeds, no global mutable state)
```
intraday_options_strategy/
├── data/        download_data.py, data_audit.py, vix_data.py
├── features/    indicators.py, signals.py, regime_filter.py
├── options/     bs_pricing.py, option_selector.py
├── backtest/    engine.py, position_sizer.py, costs.py
├── optimisation/ walk_forward.py
├── analysis/    metrics.py, charts.py, robustness.py
├── config.py, main.py, requirements.txt
```
- BS implemented manually with scipy.stats.norm. pandas/numpy/scipy. vectorised engine preferred.
- Final: run main.py → full report + 8 charts + 300-word executive summary (edge, scalability, practical risks, next steps).

---

## PHASE ROADMAP & CHECKLIST

### Phase 0 — Setup, Plan, Data (Session 1, 2026-06-11)
- [x] Environment check (Python 3.14.5 at full path; pip OK; git OK; **Kaggle creds MISSING** — using anonymous kagglehub)
- [x] Project skeleton + this PLAN.md + config.py + requirements.txt
- [x] Download Kaggle 1-min data → **SUCCESS**: `debashis74017/nifty-50-minute-data` (834 MB, 680 files) → `datasets\raw\kaggle\debashis74017__nifty-50-minute-data\`. Required truststore SSL fix (corporate proxy MITM) + resumable retry loop (proxy resets long transfers; see data/download_kaggle_resume.py). Note: `debashis74017/stock-market-data-nifty-50-stocks` returns 403 anonymously (needs kaggle.json consent) — NOT needed now.
- [x] Clone/check GitHub NSE-Data repo → `datasets\raw\github\NSE-Data` — 48 files, **daily bhavcopy data from 2000 (NOT intraday)** — fallback only
- [x] India VIX daily via yfinance → `datasets\raw\india_vix_daily.csv` (2008-03-03 → 2026-06-11, 4474 rows) + `nifty50_daily.csv` (4521 rows) + `banknifty_daily.csv` (4536 rows); data/vix_data.py written (lagged no-lookahead mapping + realised-vol fallback)
- [x] Data audit → `datasets\DATA_AUDIT.md`. **PRIMARY: `NIFTY 50_minute.csv` — 1,048,738 rows, 2015-01-09 → 2026-05-15, 2809 trading days, median 375 bars/day, only 16 short days (Diwali Muhurat ~60-bar sessions + 2021-02-24 NSE outage — exclude these days in Phase 1), no bad values/duplicates.** Also: `NIFTY BANK_minute.csv` (regime covariate) and **`INDIA VIX_minute.csv` (1-min VIX, same span!)** — 136 index instruments total at 1/5/15/60-min + daily.
- [x] Update CURRENT STATE + memory pointer (memory: `nifty-intraday-options-project.md`)

**CRITICAL DATA CAVEATS (decided this session):**
1. **All index files have volume=0** (indices don't trade). Adaptations: VWAP → equal-weight session-anchored mean of typical price (TWAP-style); A2 "expanding volume" + A3 "volume > 1.5× 20-bar avg" → **range/ATR expansion proxy** (bar true-range > 1.5× 20-bar avg TR). Document as deviation from spec (spec allows: "adjust if data shows otherwise").
2. **Intraday 1-min India VIX available** → upgrade over spec C1 fallback: use prior-bar intraday VIX for the C1 filter and BS IV input (lag 1 bar, no lookahead). Daily VIX (yfinance) kept for cross-validation.
3. Data ends 2026-05-15; weekly expiry day changed Thursday→Tuesday in 2025 — option_selector must use Thursday ≤2025-08-29 era and handle the switch (verify exact NSE switch date in Phase 2 before coding).
4. Short sessions (Muhurat) + 2021-02-24 outage day → drop days with <300 bars in Phase 1 cleaning.

### Phase 1 — Data pipeline & cleaning — **COMPLETE (Session 2, 2026-06-11)**
- [x] `data/build_dataset.py` → `processed\nifty_1min.parquet` (1,047,541 bars, 2794 days, 2015-01-09 → 2026-05-14), `vix_1min.parquet` (99.96% same-minute coverage), `banknifty_1min.parquet`, `trading_calendar.csv`
- [x] Session filter 09:15–15:29; dup-drop; dropped 5 days <300 bars (2021-02-24 outage, 2024-03-02 & 2024-05-18 special sessions, 2025-10-21 Muhurat, truncated 2026-05-15); Muhurat evening sessions auto-excluded by session filter
- [x] VIX: 1-min intraday used (lag-1-bar in filters); daily VIX fallback in data/vix_data.py
- [x] Synthetic proxy NOT needed (real index 1-min data acquired)
- NOTE: console is cp1252 — avoid unicode arrows in print(); set PYTHONIOENCODING=utf-8

### Phase 2 — Features & options pricing — **COMPLETE (Session 2, 2026-06-11)**
- [x] features/indicators.py (EMA, Wilder RSI, BB+width pctile rank, TR/ATR, session TWAP, ADX(14) on 5-min buckets labelled by SCHEDULED end — prefix-test caught & fixed a partial-bucket lookahead bug)
- [x] features/regime_filter.py (C1 lag-1-bar intraday VIX, C2 ADX regimes, C3 window, C4 via `datasets\event_dates.csv` — best-effort RBI/Budget list 2015–2026, refine if needed)
- [x] features/signals.py (A1–A3, B1–B2; volume conditions → TR > 1.5×ATR20 expansion per caveat 1; composite score = fire + strong-regime-agree + second-same-direction-signal, trade @ ≥2)
- [x] options/bs_pricing.py + options/option_selector.py (Thursday→Tuesday expiry switch 2025-09-01, holiday roll-back via actual trading calendar, min-DTE 2d roll)
- [x] tests_smoke.py — **ALL PASS** (BS parity 1.8e-12, Greeks sane, expiry rules, 4 no-lookahead prefix tests, signals 14.3/day on 2023H1: A1 807/A2 111/A3 16/B1 390/B2 421)

### Phase 3 — Backtest engine — **COMPLETE (Session 2, 2026-06-11)**
- [x] backtest/costs.py (round-trip @ premium 150 × 1 lot = ₹102.06 ≈ 0.91% of premium value)
- [x] backtest/position_sizer.py (Kelly×0.25 on trailing-60-trading-day closed trades; warm-up <30 trades → 1 lot; f*≤0 with history → SKIP trades — by design Kelly halts on negative edge)
- [x] backtest/engine.py — validated on 2023: 3565 events → 232 trades in 2.2s; exits SL/TARGET/EOD all exercised; Kelly engaged (1–8 lots); sample trades eyeballed sane. **Bugfixes found in validation: (1) parquet datetime index is [us] not [ns] — engine forces .as_unit("ns"); (2) exit walk now uses bar-wise live VIX (sig_walk), EOD exit uses 15:20-bar VIX**
- [x] run_sample.py kept as regression check

### Phase 4 — Walk-forward optimisation — **RUNNING (launched Session 2)**
- [x] optimisation/precompute.py → `processed\filters.parquet`, `vix_on_bars.parquet`, 27× `processed\events\ev_f{F}s{S}o{O}.parquet` (~34–50k events each, ~1 min total)
- [x] optimisation/walk_forward.py: IS = first 70% (2015-01-09..2022-12-15, 1955d); OOS starts 2022-12-16 — UNTOUCHED. 126 folds × 648 combos (27 variants × 8 valid SL/TG × 3 maxTPD), feasibility-first modified-Sharpe objective, 10 procs, **checkpoint = results\wfo_folds.csv (restart-safe: rerun same command to resume)**
- [ ] WFO run complete → consensus in `results\wfo_consensus.json` (auto-written at end; if interrupted, rerun walk_forward.py to finish remaining folds)

### Phase 5/6 modules — **WRITTEN (Session 2), not yet run**
- [x] analysis/metrics.py (full S8 suite), analysis/charts.py (8 PNGs), analysis/robustness.py (9.1–9.5), main.py orchestrator
- [ ] After WFO done: `python main.py` → REPORT.md + charts + robustness (needs wfo_consensus.json)
- [ ] Executive summary (300 words) → results\EXECUTIVE_SUMMARY.md (write after seeing OOS results)

### Phase 5 — OOS evaluation, metrics, charts
- [ ] analysis/metrics.py + analysis/charts.py (8 charts) ; run consensus params on OOS
- [ ] Full report (S8) saved to `results\` (CSV + PNG)

### Phase 6 — Robustness + executive summary
- [ ] analysis/robustness.py: 9.1–9.5
- [ ] main.py orchestrator; full pipeline run; 300-word executive summary → `results\EXECUTIVE_SUMMARY.md`
- [ ] Final PLAN.md state update

---

### Phase 7 — STRATEGY V2 (regime-aware multi-sleeve ensemble) — started Session 3 (2026-06-11)
- [x] STRATEGY_V2.md design contract (sleeves S1–S4, allocation, execution policy, anti-overfit rules) — READ IT FIRST
- [x] options/option_selector.py: monthly expiry pre-2019-02-11 (Nifty weeklies didn't exist), min_dte param (0DTE support)
- [x] features/horizon.py (multi-horizon bias 1d/1w/1m/3m/6m/3y + EMA stack + day-type features at 09:20)
- [x] backtest/engine_v2.py (multi-leg uniform-side, short margin, combo SL/PT, partial booking + trailing, per-lot economics for portfolio scaling)
- [ ] strategies/sleeves.py (S2 range short straddle, S3 0DTE, S4 trend rider) ← NEXT
- [ ] portfolio/allocator.py (vol-parity + regime gates + DD governor) + run_v2.py (sleeve backtests, correlation, combined portfolio)
- [ ] v2 WFO for sleeve params (small grids) after v1 WFO finishes (CPU contention)
- [!] **RESEARCH workflow FAILED — org monthly spend limit.** Re-run when tokens available: script saved at `~\.claude\projects\...\workflows\scripts\options-edge-research-wf_c5c48a52-f8d.js`, resume id wf_c5c48a52-f8d. Until then STRATEGY_V2.md sleeve priors stand on practitioner consensus (VRP/theta-harvest, 9:20 straddle, expiry-day decay) — verify before live.

## KEY DECISIONS / NOTES LOG
- 2026-06-11: `python` alias broken on this machine → always use full path. Kaggle API creds absent → anonymous kagglehub download attempted (public datasets allowed). Existing repo data (`raw\nifty500\*.csv`) is DAILY 2005–2021 — fallback only, cannot drive a 1-min backtest.
- Lot size: spec says 75. Note NSE lot size history: 50 (pre-2015), 75 (2015–2021), 50 (2021–2024), 25 (2024), 75 (Apr 2025+). Use 75 flat per spec; document as assumption.
- Weekly expiry day: Thursday historically; NSE moved Nifty weekly expiry to Tuesday (2025). Use Thursday for historical data per spec; document.

## NEXT SESSION ENTRY POINT (Phase 0 done — data is on disk, do NOT re-download)
1. Read this file + `datasets\DATA_AUDIT.md` (quick skim — data confirmed good).
2. **Phase 1:** write `data/build_dataset.py` → load `NIFTY 50_minute.csv`, `INDIA VIX_minute.csv`, `NIFTY BANK_minute.csv`; clean per CRITICAL DATA CAVEATS (drop <300-bar days, session 09:15–15:29); save `datasets\processed\nifty_1min.parquet`, `vix_1min.parquet`, `banknifty_1min.parquet`. Re-run audit on processed data; tick Phase 1 boxes.
3. **Phase 2 onwards:** follow phase checklists in order. Suggested per-session scope (token-aware): Session 2 = Phase 1 + Phase 2 (features+options modules + tests). Session 3 = Phase 3 (engine) + validate. Session 4 = Phase 4 (WFO run). Session 5 = Phases 5–6 (OOS, charts, robustness, summary).
4. Always: tick boxes + update CURRENT STATE before tokens run out. Use full python path (see top).
