# PORTFOLIO-MARGINAL EVALUATION — decision rule + verdict (2026-07-29/30)
Owner: Ritika Sharma (Risk). Methodology: `.claude/skills/orthogonality/SKILL.md` (RP-17), extended
with a monthly/quarterly-anchored correlation requirement per STACKED_BOOK_20260711.
Scripts: `marginal_framework.py` (main), `summary_ranking.py`, `tc_concentration_check.py`.
Outputs: `candidate_standalone_stats.csv`, `correlation_daily_monthly_quarterly.csv`,
`marginal_weight_sweep.csv`, `summary_ranking.csv`.

## Principal's point, honoured precisely
"Low trade count" and "low statistical reliability" are DIFFERENT objections and must never be
conflated. This file keeps them separate throughout: frequency is never a gate input below; only
t-stat, sign, correlation and empirical marginal contribution are.

## THE BOOK (honest definition)
`STACKED_BOOK_20260711/book_daily_pnl.csv` — 4 real, separately-backtested sleeves stacked:
s1f (certified live/paper) + b1b (Gate-4 PASS, red-team SURVIVED, pre-IC) + midsmall momentum +
breakout equity. 942 daily obs, 2022-01-04..2025-12-31, base capital Rs1cr (RISK_LIMITS D-026).
**This is a research recombination of validated backtests, NOT the live paper ledger** (paper
ledger has exactly one closed trade, S1F-001, 2026-07-14 — far too little history for a
correlation estimate). Stated once here, binding for the whole analysis below.

## DECISION RULE (checkable, apply in order; any FAIL/RED = no space this cycle)

**Gate 1 — Reliability (frequency-blind).** NW t-stat (or simple t if NW unavailable) on net
per-trade/period return, pre-registered build window, no post-hoc cell selection:
  t<1.0 KILL · 1.0-1.5 WATCH (zero size) · 1.5-2.0 PROVISIONAL (capped/paper size) · >=2.0 FULL PASS.
  n<30 at any t -> flag small-sample, DSR/PBO owed before sizing beyond PROVISIONAL.

**Gate 2 — Sign/robustness.** mean net>0 AND net PF>1.0 AND top-1-trade profit share <=30%
(>30% = FRAGILE, blocks FULL PASS regardless of Gate 1).

**Gate 3 — Correlation to book, QUARTERLY-ANCHORED (never daily alone).**
  |corr_quarterly|<=0.35 GREEN · 0.35-0.53 YELLOW (0.53 = the firm's own observed
  too-correlated ceiling, STACKED_BOOK_20260711) · >0.53 RED regardless of Gates 1-2.
  If corr_monthly disagrees with corr_quarterly in sign or by >0.3 in magnitude, treat as NOISE
  (n~16 quarters, SE(r)~0.28 by Fisher) — downgrade to YELLOW, do not cite a lone point estimate.

**Gate 4 — Marginal, empirical (the actual test).** Run the weight sweep (w=5/10/15/20%). PASS
only if at w=10%: book Sharpe, Calmar AND worst-month all do not worsen. Gates 1-2 MUST pass
first — improving book Sharpe by blending in a near-zero/negative-edge low-vol series is
dilution (adding cash), not diversification.

**Gate 5 — Capacity/operational.** Deployable size at the recommended weight sits inside D-031's
Rs10L-10cr band, limit-order-or-skip; lot granularity allows the weight without >20% rounding error.

**Sizing rule if all pass:** size = min(argmax-Sharpe weight, argmax-worst-month weight, 20%
single-candidate concentration cap) — i.e. the MORE CONSERVATIVE of the return-optimal and the
tail-risk-optimal weight, never the return-optimal alone (CIO capital-protection mandate).

## RESULTS — standalone + correlation (real series only; see CSVs for full precision)

| candidate | family | n | t-stat | corr(D) | corr(M) | corr(Q) | Gate1 | Gate2 | Gate3 |
|---|---|---|---|---|---|---|---|---|---|
| TC_breakout20 | TREND_CATCHER | 60 | -0.16 | 0.05 | 0.20 | 0.25 | KILL | FAIL(PF 0.93) | moot |
| TC_ema_cross | TREND_CATCHER | 36 | -1.22 | 0.02 | 0.41 | 0.13 | KILL | FAIL(PF 0.56) | moot |
| TC_sweep_priorweek_reclaim | TREND_CATCHER | 83 | 0.19 | 0.01 | -0.07 | -0.37 | KILL | FAIL(top1=309% of total net) | moot |
| SD_D_priorweek_sweep_long__fixed_5 | SWING_DELTA1 | 58 | 1.86(NW,firm JSON) | 0.12 | 0.28 | 0.21 | PROVISIONAL | PASS(PF1.85,conc10.9%) | GREEN |
| SD_D_priorweek_sweep_long__fixed_10 | SWING_DELTA1 | 54 | 1.71(NW,firm JSON) | 0.09 | 0.36 | 0.41 | PROVISIONAL | PASS(PF1.93,conc11.6%) | YELLOW(but M/Q agree in sign+magnitude order -> real, not noise) |
| SW11_A_intraday_stop30 | SWEEP_11YR | 4378 | -0.53 | -0.02 | 0.23 | 0.20 | KILL | FAIL | moot |
| SW11_B_intraday_trail25 | SWEEP_11YR | 4378 | 3.21 | -0.02 | 0.20 | 0.12 | FULL PASS | PASS | GREEN |
| SW11_C_intraday_trail40 | SWEEP_11YR | 4378 | 3.04 | 0.00 | 0.13 | 0.06 | FULL PASS | PASS | GREEN |
| SW11_D_overnight1_trail40 | SWEEP_11YR | 4378 | 6.37 | 0.00 | 0.04 | -0.04 | FULL PASS | PASS | GREEN |
| SW11_E_swing3_trail60 | SWEEP_11YR | 4378 | 7.77 | -0.02 | 0.12 | -0.04 | FULL PASS | PASS | GREEN |
| SW11_F_intraday_tgt200 | SWEEP_11YR | 4378 | 0.05 | 0.00 | 0.26 | 0.18 | KILL | FAIL | moot |
| CC_unconditional | COVERED_CALL_NIFTY | 119 | -1.01 | -0.01 | -0.43 | -0.37 | KILL(mean edge negative) | FAIL | moot(great "hedge" corr, wrong sign edge) |

## Gate 4 (marginal, empirical) for everything that survived Gates 1-3

| candidate | delta-Sharpe @w10 | delta-Calmar @w10 | delta-worst-month @w10 | best-Sharpe weight | best-worst-month weight | verdict |
|---|---|---|---|---|---|---|
| SD_D_priorweek_sweep_long__fixed_10 | +0.011 | -0.003 | +0.89pp | 50%+ (still rising) | 50%+ (still rising) | PASS, small-n caveat |
| SD_D_priorweek_sweep_long__fixed_5 | +0.004 | -0.012 | +0.94pp | 50%+ (still rising) | 50%+ (still rising) | PASS, small-n caveat |
| SW11_E_swing3_trail60 | +0.542 | +0.928 | +1.37pp | 10% | 5% | PASS w/ kelly-overfit + single-variant caveats |
| SW11_D_overnight1_trail40 | +0.142 | +0.263 | +1.66pp | 10% | 5% | PASS w/ same caveats |
| SW11_B_intraday_trail25 | +0.141 | +0.188 | +0.76pp | 10% | 20% | PASS w/ same caveats |
| SW11_C_intraday_trail40 | -0.026 | +0.037 | +1.38pp | 5% | 15% | borderline, weight-sensitive |

## VERDICT

1. **TREND_CATCHER_MULTIDAY (all 3 Stage-A signals): CLEAN KILL, per its own pre-registered rule**
   ("If NO signal clears the Stage-A bar, STOP — report a clean kill of the whole arm"). This is
   the arm the task explicitly flagged as the interesting "low-frequency but maybe-reliable" test
   case, and it fails on RELIABILITY, not frequency: t=-1.22 to +0.19 (nowhere near the 2.0
   pre-registered bar, most not even near 1.0), two of three net PF<1 (losing money net of costs),
   and the one nominally-net-positive signal (sweep_priorweek_reclaim, +Rs18,018 over 83 trades)
   owes >300% of that total to its single best trade — textbook profit-concentration fragility, the
   exact 99.5%-in-4-trades failure mode the pre-registration was written to catch. Its occasionally
   favorable correlation (sweep_priorweek_reclaim: -0.37 quarterly) is irrelevant — Gate 1/2 already
   killed it. **Do not advance to Stage B.**

2. **SWING_DELTA1 `D_priorweek_sweep_long` family (fixed_5 n=58, fixed_10 n=54): the genuine
   low-frequency-but-real-edge case the Principal is asking about.** ~12-13 trades/year, NW-t
   1.71-1.86 (real per the firm's own JSON — PROVISIONAL band, not FULL PASS, not noise), PF
   1.85-1.93, concentration 11-12% (not fragile), monthly AND quarterly correlation agree in sign
   and rough magnitude (0.28-0.41) — a genuine, if modest, correlation that is NOT a daily-only
   artifact. Gate 4 confirms it empirically: adding it improves book Sharpe, and MEANINGFULLY
   reduces book maxDD (-18.4%->-9.5/-9.6% at 50% weight) and worst month (-9.6%->-4.9/-5.1%) —
   the opposite of the SW11 pattern, because this candidate is genuinely thin/idle most of the
   time and its active periods are not synchronized with the book's worst days. **This is exactly
   the case the SWING_DELTA1 pre-registration itself anticipated**: its own kill-rule reads "FLAG
   (not kill) if net beats S1-F Calmar or genuinely diversifies it — route to IC." Standalone
   Calmar (0.57-0.65) does NOT beat S1-F (2.83), but it DOES genuinely diversify. **Verdict: route
   to IC as a FLAG, per its own pre-registered rule — PAPER-ONLY space now (Gate 1 is PROVISIONAL,
   not FULL PASS), DSR/PBO owed on the 45-valid-cell family before any real capital, re-test next
   quarter.** Recommended paper weight if approved: 10-15% of book notional (below the
   still-rising ceiling found in the tested grid, pending the DSR check).

3. **SWEEP_11YR (futures trend-catcher, 6 exit variants of ONE shared entry signal): NOT a
   low-frequency candidate** (~400 trades/yr) but included as the framework's contrast/robustness
   case. Four of six variants (B/C/D/E) clear every gate cleanly, with E (swing3/trail60) and D
   (overnight1/trail40) showing the largest empirical marginal-Sharpe gains in the whole set
   (+0.54 and +0.14 respectively at w=10%) and genuinely low quarterly correlation (|r|<=0.12).
   **Two hard caveats before this goes anywhere near IC:** (a) sizing uses an IN-SAMPLE-DERIVED
   Kelly fraction (kelly_f_from_IS 0.13-0.19) — a classic overfitting trap the overfit-analyst
   desk must re-derive out-of-sample before trusting the CAGR/Calmar shown; treat current numbers
   as an upper bound. (b) all 6 variants share the SAME entry trigger stream — they are NOT six
   independent diversifiers; at most ONE exit-management flavor may ever be sized, never stacked.
   (c) Sharpe-optimal weight (10%) and tail-risk-optimal weight (5% for D/E, where worst-month
   stops improving before Sharpe does) diverge — per the sizing rule above, size to the smaller of
   the two, not the Sharpe peak.

4. **COVERED_CALL_NIFTY: KILL.** Mean per-cycle edge is NEGATIVE (t=-1.01) on the unconditional
   (baseline) series — matches the DESIGN.md finding that the overlay does not survive real-data
   testing. Its correlation to the book is attractively negative (monthly -0.43, quarterly -0.37,
   and the two agree in sign/magnitude — a real relationship, not noise) but **a negative-expected-
   value series with a nice correlation number is a cost centre, not a diversifier** — Gate 3/4
   never get evaluated because Gate 1/2 already fail. If tail insurance is the actual objective
   (not book-Sharpe), that is Kabir Anand's (hedge desk) mandate under a different sizing
   objective, not this framework's.

## What could NOT be obtained as a real series (stated, not guessed)
- **DEBIT_SPREADS_20260729**: crashed mid-run (`numpy._core._exceptions._ArrayMemoryError` in
  `chain.load_expiry`/`drop_duplicates`); `trades_ALL_partial.csv` (85,086 rows) is the raw,
  UNFILTERED exploratory grid across signal x offset x dte x hold x width x structure — no single
  winning cell has been selected. PENDING, not evaluated.
- **VOL_SELLING_BENCHMARK_20260729**: run_log stops after building entry-day signal flags; no
  trades output exists yet. PENDING.
- **INVERSE_VRP_NICHE_20260729**: IV/RV series build in progress (200/1238 days at last log tick).
  PENDING.
- **CONVEX_STRUCTURES_20260729**: directory empty. NOT STARTED.
- **OPTION_SURFACE_SIGNALS_20260729**: option panel build in progress (800/1236 days at last log
  tick). PENDING.
- **OPTION_BUY_ARMS/bullish-sweep-dte**: pre-registration only, not run. PENDING.
- **OPTION_BUY_ARMS/bearish-arm and confluence-volbreak**: signal TIMESTAMPS only (`t`,
  `direction`), no P&L attached — not yet priced through the option harness. Note
  `confluence-volbreak/signals/stackA_exact4.csv` (n=38) is the same family as the already-
  documented n=35, t=1.73 confluence noise cell (SHARED_CONTEXT) — excluded on that prior finding,
  not re-litigated here.
- **S1-F and B1b themselves**: real series exist and were used AS the book (see above); they are
  not "candidates" in this analysis, they ARE the book.
- **S-01/S-02/S-03/S-05/S-06**: per STRATEGY_REGISTER.md, these are SEND-BACK/FAILED-PRE-IC/KILLED/
  FROZEN/backtest-pending respectively — no real forward series beyond what's already adjudicated
  in the register; not re-pulled into this analysis.

## Statistical honesty notes (P-01..P-12 / EPISTEMIC_CONDUCT)
- Quarterly correlations rest on only 16 observations (2022-2025); Fisher SE(r)~=0.28 at that n,
  so a single quarterly point estimate should never be treated as precise — the rule above
  requires monthly/quarterly AGREEMENT before trusting a YELLOW/GREEN call, precisely because a
  lone quarterly number here could easily be +-0.3 noise.
- Returns are computed as net P&L / each arm's own pre-registered capital base, then reallocated
  to a common book scale for blending — a linear-scalability assumption **[INFERENCE]**, standard
  for this kind of screen but not a claim that live lot-sizing scales frictionlessly.
- SWEEP_11YR trade dates use ENTRY date (no exit-date column on disk) for monthly/quarterly
  bucketing; holds are short (intraday to 3 days) so month-boundary misattribution is rare and
  immaterial at monthly/quarterly grain **[INFERENCE]**, stated not hidden.
- Crash-blind caveat stands on every number above: the book's 2022-2025 window and every
  candidate's build window contain no true crash (2018/2020-grade); worst-month/VaR figures here
  are crash-blind until a COVID-era or live-crisis re-run is done (04_RND_LAB Lessons Learned,
  2026-07 entry).
