# T1 — Regime Layer-1 (30-min conditional drift) — SUMMARY
_Persisted by Head of Quant (parent) 2026-07-10; subagent report-file writes blocked. Content verbatim from t1-regime agent._

VERDICT: **KILL** (strict vs frozen pre-registered bar: day-clustered |t|>=3 AND >=6 NIFTY pts/30-min)

**0/4 regimes survive. A+C both fail -> System 1 dead as designed. <2/4 -> Layer-1 killed; families unconditioned-only.**

**Key stats** — NIFTY 50 spot 1-min -> 5-min bars, 2020-01-01 -> 2025-12-31, n=111,240 bars / 1,487 days, guards: drop_preopen, assert_next_bar, 50-bar warmup, same-day fwd windows only. FULL-sample fwd-30-min effect (conditional mean - unconditional, points; day-clustered t):

| Regime | n | share | effect pts | t | survives |
|---|---|---|---|---|---|
| A trend-up | 38,531 | 37.7% | +0.71 | +2.20 | NO |
| B trend-dn | 26,139 | 25.5% | -0.52 | -1.17 | NO |
| C range | 21,050 | 20.6% | -0.82 | -1.83 | NO |
| D volatile | 16,598 | 16.2% | +0.19 | +0.21 | NO |

Per-era fwd30 effect(t): 2020-22 A +0.39(0.86), B -0.48(-0.77), C -0.63(-0.96), D +0.31(0.32); 2023-25 A +1.03(2.19), B -0.59(-0.96), C -1.01(-1.66), D +0.18(0.09). Per-year max |t| = 2.43 (A 2023); B/C/D sign-flip across years. fwd60: effects 0.9-1.4 pts, all |t|<1.7 — horizon doesn't rescue. Largest effect anywhere = 1.03 pts vs 6 required (6-30x short).

**Battery:** 1-bar-lag test — effects unchanged (A +0.71 -> +0.72), no lookahead. Within-day shuffle placebo NOT a clean null: shuffled A shows +4.0 pts t=15.2 because shuffling preserves day-level regime composition, which is contemporaneous with day drift — i.e., the only "signal" in regimes is concurrent drift, not forward prediction; the real test's day-clustering handles this (flagged, not hidden). Secondary: regimes DO predict forward VOL (D fwd-30m vol 55.0 vs 35.8 pts, 1.54x) — risk-scaling info at best, per KB A.19/K-015 any allocator use must beat both static parents; the return-predictivity premise is dead.

**Spec-reconstruction disclosure (loud, not silent):** the Principal's exact A/B/C/D formulas were never persisted to disk (triage doc names regimes only; searched ideas/, 90_PRINCIPALS_DESK, journal, memory). Pre-registered canonical fixed classifier in the script header BEFORE the single pass, zero tuning: 5-min bars >=09:15 IST; s=(EMA20-EMA50)/ATR14; RV12 = 12-bar 5-min return std; D if RV12>0.12%/bar (precedence), A if s>+0.5, B if s<-0.5, else C. If the Principal supplies materially different thresholds T1 may be re-run once against them, but the 6-30x margin below the bar leaves no realistic threshold rescue. Trial ledger: T1 = 4 trials, one pass.

**Files:** t1_regime.py (frozen spec + thresholds in header), RESULTS.csv (regime x scope x horizon: FULL, 2 eras, 6 years), PLACEBO_SHUFFLE.csv, LAG1BAR.csv, regime_bars.csv.gz. Data source: intraday_options_strategy/datasets/raw/kaggle/debashis74017__nifty-50-minute-data/NIFTY 50_minute.csv (naive-IST kaggle dump, first bar 09:15 — HF-UTC tz landmine N/A, documented in script).
