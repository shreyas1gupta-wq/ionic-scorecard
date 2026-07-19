# AMF_PINE_BT — backtest "Adaptive Momentum Fusion [WillyAlgoTrader]" on NIFTY500 since 2015
Owner: DESK-100. Date 2026-07-16. Principal handed a TradingView Pine v6 **indicator** (adaptive
MACD/PPO oscillator + Jurik-smoothed signal + divergences + 6 adaptation engines). Task: turn it into
a testable long-only strategy and backtest it on NIFTY500 PIT constituents, daily, 2015→2026-01-22.

## WHAT THIS IS / ISN'T
- It is an INDICATOR, not a strategy. The tradeable content = the oscillator/signal crossover and the
  zero-line cross. Divergence/dashboard/alerts/watermark/theming are visual — IGNORE for backtest.
- SCREEN-grade backtest: faithful translation + honest costs + benchmark. Not a Gate-4 certification.

## FAITHFUL TRANSLATION (transcribe these Pine formulas EXACTLY into Python)
Default params: source=close, fastLen=8, slowLen=21, signalLen=7, mode="MACD" (also run "PPO"),
smoothFactor(phase)=0.7, engine="Efficiency" (default).
- `efficiencyRatio(src,len)`: direction=abs(src-src[len]); volatility=sum(abs(src-src[1]),len);
  return safeDiv(direction,volatility,0.5).  safeDiv(n,d,fb)= d!=0 & finite ? n/d : fb.
- `adaptiveEma(src,alpha)`: alpha clamped [0.01,1]; result = alpha*src + (1-alpha)*prev (seed=first src).
- `engineEfficiency(src,len)`: er=efficiencyRatio; fastSc=2/3; slowSc=2/31; sc=(er*(fastSc-slowSc)+slowSc)^2;
  return adaptiveEma(src,sc).   [CLOSE-ONLY → testable now]
- `engineMomentum(src,len)`: roc=safeDiv(src-src[len],src[len])*100; rocAbs=abs(roc);
  rocMax=highest(abs(roc),len*2); norm= rocMax>0 ? min(rocAbs/rocMax,1):0.5;
  baseAlpha=2/(len+1); alpha=clamp(baseAlpha+norm*(1-baseAlpha)*0.5,0.01,1); adaptiveEma(src,alpha).
  [CLOSE-ONLY → testable now]
- `jurikSmooth(src,len,phase)`: beta=0.45*(len-1)/(0.45*(len-1)+2); alphaJ=beta^3;
  e0=(1-alphaJ)*src+alphaJ*e0[1];  e1=(src-e0)*(1-beta)+beta*e1[1];
  e2=(e0+phase*e1 - e2[1])*(1-alphaJ)^2 + alphaJ^2*e2[1];  return e2.  (seed carefully per Pine nz()).
- fastMA=engine(close,fastLen); slowMA=engine(close,slowLen);
  osc = mode=="PPO" ? safeDiv(fastMA-slowMA,slowMA)*100 : fastMA-slowMA;
  signalLine = jurikSmooth(osc, signalLen, smoothFactor);
- bullCross = crossover(osc,signalLine); bearCross = crossunder(osc,signalLine);
  zeroBull = crossover(osc,0); zeroBear = crossunder(osc,0).
- Warmup: ignore signals for first max(slowLen*2,50) bars per symbol (Pine `isWarmedUp`).
VERIFY the translation on 1 symbol by eyeballing osc/signal sanity (finite, oscillates around 0).

## ENGINES
- Test NOW (close-only, faithful): **Efficiency (default)** and **Momentum**.
- BLOCKED (need OHLCV+volume we don't have on disk): Volatility, Fractal, Volume, Composite, and
  divergence signals. List them as "requires bhavcopy full-OHLCV pull (D-033 data-office job)" — do
  NOT fake them with close-only proxies.

## STRATEGY RULES (long-only — Principal's stated preference)
Run these variants (each × {Efficiency, Momentum} × {MACD, PPO} — keep the grid bounded, ~8-12 cells):
- V1 CROSS: long on bullCross; flat on bearCross. No shorting.
- V2 CROSS+ZEROFILTER: long on bullCross ONLY IF osc>0; flat on bearCross OR osc<0.
- V3 ZEROLINE: long on zeroBull; flat on zeroBear.
No-lookahead: signal confirmed at bar close (barstate.isconfirmed) → ENTER at the NEXT bar's close
(panel is close-only). Exit likewise next close. Assert entry_date > signal_date (guards.assert_next_bar).

## DATA
- Prices (PRICE basis, correct for P&L, close-only): `datasets/derived/pit_union_panel_v1/close_panel_price.parquet`
  (cols date,symbol,close,source,spliced; 2000→2026-01-22).
- Universe: `NIFTY500_TICKER_2005_2025_Final.xlsx` (Sheet1: Month-Year, Ticker; 42 snapshots).
  Membership PIT: a name trades only while it is in the most-recent snapshot on/before the bar date
  (this is the survivorship control — mandatory).
- Benchmark: NIFTY500 buy-hold. Use `datasets/etf_gold_silver/niftybees_daily.parquet` OR
  `datasets/index_daily/nse_official_all_indices.parquet` (find the NIFTY500 or NIFTY50 series;
  state which you used). Report strategy vs benchmark over the SAME 2015→2026 window.
- Guards lib: `Shreyas_Ionic_AMC/04_RND_LAB/lib/guards.py`, `lookahead_audit.py`.

## PORTFOLIO & COSTS
- Per-trade pooled stats (all trades, all names): n_trades, win%, mean_net_%/trade, median, t_stat,
  avg_hold_days, and vs a same-holding-length random-entry placebo (K≥200) — is the crossover timing
  better than random entry held the same duration?
- Portfolio NAV: equal-weight across names currently long; daily rebalance; cash (0% return) when a
  slot has no long signal (report avg exposure %). CAGR, Sharpe(ann rf=0), maxDD, per-calendar-year
  return, turnover. Cost = **0.67% round-trip** per COST_STANDARDS (also report 1.07% / 2x).
- Positions open at 2026-01-22 marked at last close (flag cens%).

## OUTPUT CONTRACT (one row per cell → results.csv)
`engine, mode, variant, n_trades, win_pct, mean_net_pct, t_stat, avg_hold_d, exposure_pct,
 cagr, sharpe, maxdd, turnover, placebo_mean, beats_placebo (bool), cagr_2x, vs_benchmark_cagr`

## DELIVERABLES
- `amf_engine.py` (faithful translation + a 1-symbol sanity check), `amf_backtest.py` (universe run,
  portfolio, costs, benchmark), `results.csv`, ledgers, `FINDINGS.md`.
- FINDINGS.md (HUMAN-format): does AMF (default Efficiency/MACD/V1) beat NIFTY500 buy-hold net of
  costs 2015-2026? Best cell? Per-year table. Turnover/cost drag. Honest verdict + the OHLCV-engine
  follow-up. No post-hoc parameter tuning beyond the frozen grid above.

## RULES
PIT membership + next-bar entry + one_day_lag_test on the aggregate (must not collapse edge to 0).
Sonnet tier (D-036). No fabricated data. Flag every limitation (close-only, no volume, panel ends Jan-2026).
