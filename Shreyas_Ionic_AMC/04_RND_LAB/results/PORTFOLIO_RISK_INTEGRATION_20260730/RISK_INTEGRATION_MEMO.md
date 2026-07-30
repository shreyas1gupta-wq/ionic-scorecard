# PORTFOLIO RISK INTEGRATION — combined-book risk, sizing, and circuit breakers (2026-07-30)
Owner: Ritika Sharma (Risk), reports to CIO. RP-29..36 methodology. Builds on my own prior output
this session (`PORTFOLIO_MARGINAL_20260729/DECISION_RULE_AND_VERDICT.md`) — do not re-derive that;
this memo is the INTEGRATION layer on top of it. Script: `risk_integration.py` (self-contained,
run inline — small CSVs, no full-panel scan, no queue entry needed). Outputs: `combined_book_risk_table.csv`,
`corr_monthly.csv`, `corr_quarterly.csv`, `monthly_pnl_by_sleeve.csv`, `worst_5_months_joint.csv`,
`crash_joint_test.json`, `var_sanity_flagship.json`.

## [DATA] What is real vs [INFERENCE]/not-available, stated up front
- REAL, on-disk, used as-is: STACKED_BOOK 4-sleeve book (2022-2025, 942 obs), SWEEP_11YR trades_E/D
  1lot CSVs (2015-2026, 11.34yr, carry-adjusted by me reproducing `carry_adj.py`'s method exactly —
  that script printed to stdout and banked nothing, so I re-derived and saved its daily net-Rs output),
  SWING_DELTA1 `all_trades.csv` cell D_priorweek_sweep_long__fixed_10 (2021-2025), A4_COVID_REPLICATION
  `a4_cycles.csv` (real 2011-2021 option settles, monthly-cycle grain).
- **NOT AVAILABLE: no long-dated short-vol income-sleeve series exists on disk as of this run.**
  Checked the full `results/` tree for long-dated/income/leap/hedge-named output dirs — none found.
  Per the task brief, two other agents are building the hedge overlay and the income sleeve in
  parallel; nothing here should be read as pre-judging their output. Every place below that would
  need that series says so explicitly and uses the best REAL proxy instead (never synthesized).
- [INFERENCE] flags: candidate returns are computed on each candidate's OWN pre-registered capital
  base then blended pro-rata into book-capital weight (same convention as `marginal_framework.py`,
  stated there as a linear-scalability assumption, repeated here unchanged).

## 1. CORRELATION — monthly AND quarterly, 2022-2025 book window (daily is a demonstrated artifact)
| pair | monthly | quarterly | read |
|---|---|---|---|
| book vs sweep_E | 0.10 | 0.01 | genuinely low both horizons — real diversifier, not a daily artifact this time |
| book vs sweep_D | 0.04 | 0.02 | same, slightly lower |
| book vs swing_D10 | 0.37 | 0.43 | moderate, agrees in sign+magnitude (matches my own prior verdict, 0.36/0.41) |
| **s1f (book's own short-vol sleeve) vs sweep_E** | **0.30** | **0.48** | **rises at quarterly — see §3, this is the critical finding** |
| s1f vs sweep_D | 0.20 | 0.46 | same pattern, variant-independent |
| s1f vs swing_D10 | -0.01 | 0.13 | sign disagreement → NOISE per own Gate-3 rule, no reliable relationship |
| sweep_E vs swing_D10 | -0.26 | -0.01 | sign disagreement → NOISE, i.e. effectively ORTHOGONAL — safe to size both without double-counting |
| sweep_E vs sweep_D | 0.83 | 0.83 | as expected — same entry signal, confirms "at most ONE ever sized" constraint |

n=48 months / 16 quarters (2022-2025 only); quarterly SE(r)≈0.28 (Fisher), so single quarterly points
are noisy — I trust only monthly/quarterly AGREEMENT, per my own decision rule from yesterday.

## 2. COMBINED-BOOK RISK TABLE (2022-2025 real overlap, historical VaR/ES, daily)
| scenario | Sharpe | Calmar | maxDD | VaR95 | VaR99 | ES95 | ES99 | worst mo | best mo |
|---|---|---|---|---|---|---|---|---|---|
| Book alone | 1.50 | 1.33 | -18.38% | -1.29% | -2.83% | -2.33% | -4.07% | -9.61% | +10.93% |
| Book + Sweep-E @10% | 1.74 | 1.69 | -15.62% | -1.14% | -2.66% | -2.11% | -3.72% | -7.50% | +11.59% |
| Book + Sweep-D @10% (conservative alt) | 1.57 | 1.51 | -15.48% | -1.15% | -2.55% | -2.11% | -3.68% | -7.17% | +10.38% |
| Book + Swing @10% (paper-only) | 1.51 | 1.33 | -16.66% | -1.16% | -2.55% | -2.10% | -3.68% | -8.71% | +9.84% |
| **Book + Sweep-E @10% + Swing @10% (FLAGSHIP)** | **1.77** | **1.72** | **-13.94%** | **-1.01%** | **-2.37%** | **-1.89%** | **-3.33%** | **-6.61%** | +10.50% |
| Book + Sweep-E @15% + Swing @15% (upper end tested) | 1.91 | 1.89 | -12.51% | -0.87% | -2.13% | -1.67% | -2.97% | -5.11% | +10.28% |

Sweep-E and swing improve every metric at every tested weight, monotonically through 15% — consistent
with their genuinely low/orthogonal correlation to the book AND to each other (§1).

**VaR 3-method sanity (RP-34 duty) on the flagship combo:**
VaR95: historical -1.01% / parametric-normal -1.21% / bootstrap-MC -1.02% — all agree.
VaR99: historical -2.37% / parametric-normal -1.75% / **bootstrap-MC -2.47%**.
**Parametric-normal UNDERSTATES 99% tail risk by ~35% vs historical/MC** — the combo's daily return
has excess kurtosis 11.5 (fat-tailed, near-zero skew -0.03). Reconciliation: trust historical/MC for
99%, not the normal approximation. This is the same "know your VaR method's blind spot" lesson every
RP-34 run turns up; here it happens on the GOOD side (own book), so it is stated, not buried.

## 3. ★ THE CRITICAL CORRELATION QUESTION — do sweep (short-biased) and short-vol income hedge in a crash?
**Short answer: NOT in calm markets, YES in the one real crash on record — the relationship is
regime-dependent, and averaging over it (as any single correlation number does) hides exactly the
thing that matters.**

- **Calm-regime evidence (2022-2025, real):** sweep_E vs s1f (the book's own short-vol 0DTE sleeve)
  runs +0.30 monthly, **+0.48 quarterly** — RISING at the lower-frequency horizon, the opposite of a
  reassuring pattern, and close to my own Gate-3 RED ceiling (0.53). In normal-to-choppy markets these
  two do NOT reliably offset each other — if anything they mildly co-move (both can have a good or
  bad quarter together; sweep_D shows the same pattern, 0.46 quarterly, so this is not a single-variant
  artifact).
- **Crash evidence (real, 2020, the ONE true crash in reach of any of this session's data):** the firm's
  own A4_COVID_REPLICATION short-vol proxy cycle (real 2011-2021 option settles, the entry-Feb/expiry-
  Mar-26-2020 cycle that ran straight through the COVID bottom) lost **-543.8 pts = -Rs40,785/lot** —
  a real, documented short-vol crash loss. Over the EXACT SAME calendar window (2020-02-28..2020-03-26),
  sweep_E's own real 1-min-bar-derived P&L was **+Rs302,006 on its Rs10L capital (+30.2%)** over 8
  trading days. Widening to the full COVID window (2020-02-15..2020-04-15): sweep_E made **+Rs372,265
  (+37.2% of capital)** over 17 trading days — its single best stretch in the whole 11.34-year sample.
- **Read: in the one crash this firm has real settle-level short-vol data for, the sweep was strongly
  positive while the short-vol structure was strongly negative — a genuine crash hedge.** But the
  2022-2025 quarterly correlation (the only window where BOTH sweep and an in-book short-vol sleeve
  coexist) shows a mild POSITIVE relationship. **Both are true; they describe different regimes.**
  The mechanism is intuitive once stated: a short-biased trend/reclaim sweep with trailing stops
  profits from LARGE DIRECTIONAL MOVES (either way, but its short lots run further in a crash); a
  short-vol income structure profits from the ABSENCE of large moves. In quiet-to-moderate markets
  neither large-move condition is triggered often, so their P&L just mildly co-moves with whatever
  else is happening; in a genuine crash the sweep's convexity activates hard exactly when short-vol's
  path-dependent loss activates hard, in opposite directions.
- **Caveat, stated not hidden:** this crash comparison uses TWO DIFFERENT proxies across different eras
  (sweep_E's own 2020 P&L directly; a REAL but DIFFERENT short-vol structure's 2020 P&L, since s1f
  itself has no pre-2022 history) — not a same-instrument apples-to-apples test, but it is the best
  REAL evidence available, and it is evidence, not an assumption. **When the long-dated income sleeve
  lands, this exact test (its P&L on 2020-02-28..2020-03-26 and the wider Feb-Apr 2020 window, against
  sweep_E's real P&L in the same window) must be re-run on matched instruments before anyone credits
  it as a hedge.** Until then: size the income sleeve as if it does NOT reliably hedge the sweep in
  normal times, and treat any crash-hedge benefit as a bonus, not a planning assumption.
- **Consequence for MY ledger (charter duty):** the long-dated income sleeve, being "implicitly
  short-vol," belongs in the SAME shared VaR budget as S-01..S-04 (RISK_LIMITS' correlated-sleeve
  rule), not a fresh independent risk allowance — it does not earn a free diversification credit
  merely by having a different structure/tenor from the existing short-vol book.

## 4. WORST 5 BOOK MONTHS (2022-2025) — joint sleeve behaviour, extends the firm's own finding
STACKED_BOOK_20260711/RESULTS.md already found "only S1-F stayed orthogonal in worst months." Adding
the new candidates to that exact test:

| month | book | s1f (in-book short-vol) | sweep_E | sweep_D | swing_D10 |
|---|---|---|---|---|---|
| 2022-02 | -9.61% | +0.12% | **+11.47%** | +14.80% | -0.69% |
| 2024-03 | -8.32% | +0.26% | **+8.34%** | +4.54% | +0.00% |
| 2022-01 | -5.80% | -0.01% | -7.06% | -5.88% | +0.52% |
| 2025-07 | -4.40% | +0.12% | +3.25% | -1.32% | -0.83% |
| 2024-10 | -3.82% | +0.14% | -0.69% | -4.26% | +0.00% |

s1f stays flat-to-slightly-positive in all 5, confirming the firm's earlier finding still holds.
**Sweep_E was STRONGLY POSITIVE in the two worst months** (the two biggest book drawdowns, +11.5%
and +8.3% respectively) — a real diversification win exactly when it mattered most. But it was
ALSO negative in the book's 3rd-worst month (Jan-2022, -7.06%, co-negative with the book) — **not a
universal hedge, mixed at the month level**, consistent with §3's "regime-dependent, not a clean
hedge" conclusion. Swing_D10 is small and mostly flat/idle in these months (its edge windows rarely
coincide with the book's bad months) — genuinely orthogonal but also genuinely small at this weight.

## 5. SIZING — recommended weights and reasoning
| sleeve | recommended weight | capital status | reasoning |
|---|---|---|---|
| Existing 4-sleeve book | keep at v2 risk-parity config (CAGR 15.8%/MDD -8.1%/Sharpe 2.29, STACKED_BOOK_20260711) | live/paper as already registered | unchanged by this analysis — the baseline the candidates are measured against |
| **Sweep-E (liquidity-sweep delta-1)** | **10% of book capital = Rs10L**, sized at **0.5% risk/trade or 1-lot fixed WITHIN that Rs10L** — NOT the 0.75%-Sharpe-peak or Kelly tiers | size to the MORE CONSERVATIVE of return-optimal and tail-risk-optimal, per my own decision rule; leverage does not improve Calmar (flat 0.66-1.36 across a 10x risk-fraction range) and Sharpe degrades past ~0.75% — no reason to carry the extra MDD (1-lot: -21.7% MDD vs 0.75%: -52.8% MDD for a Sharpe gain of 1.65→1.85) |
| Sweep-D (overnight1/trail40) | **0% — do not stack alongside Sweep-E.** Both share the SAME entry signal (0.83 corr both horizons); at most ONE exit-management variant may ever be sized. Keep D on file as the tail-conservative fallback (lower MDD -11.4% vs -18.0%, higher Calmar 0.95 vs 0.85) if the CIO prefers less drawdown over the extra Sharpe | n/a | constraint already established this session, re-confirmed by the 0.83 correlation measured here |
| Swing_D10 (D_priorweek_sweep_long, fixed_10) | 10-15% of book capital, **PAPER ONLY** (unchanged from my prior verdict — Gate 1 is PROVISIONAL not FULL PASS, DSR/PBO still owed) | paper | genuinely orthogonal to both the book (0.37/0.43) and to sweep_E (noise-level, no double-count risk) — safe to combine, but its own reliability gate hasn't cleared FULL PASS yet |
| Long-dated short-vol income sleeve | **0% — cannot size, no series exists.** When it lands: run it through the SAME 5-gate decision rule, AND the §3 crash-vs-sweep test on matched dates, before any weight | n/a | do not assume the "different structure" diversification story until tested — §3 shows it may not hold in normal times |

**Margin/capacity check (D-031, RISK_LIMITS, margin ruling):**
- Sweep-E and swing_D10 are naked delta-1 futures (unhedged) → 10% margin ruling applies. Both already
  assume `margin_pct=0.10` internally in their own backtests (SWEEP_11YR `report.json`), so the
  recommended 10%-of-book weight is a clean 1:1 reallocation — no separate margin overlay needed.
- Incremental margin from adding both at 10%+10% ≈ Rs2L (10% of the Rs20L notional carve-out) —
  immaterial against the book's existing documented margin usage (~Rs44L vs a Rs75L pledge base per
  STACKED_BOOK_20260711, not re-verified fresh here) and comfortably inside RISK_LIMITS' free-cash
  ≥30%-of-equity floor (Rs30L on a Rs1cr book).
- **Rs10L sits at the FLOOR of D-031's Rs10L-10cr band** — already flagged in this session's own
  sweep write-up as "near minimum viable capital" (below ~Rs2.5L capital the sweep cannot trade a
  full lot at all). No headroom to size DOWN further; sizing UP is a Sharpe-negative move per the
  leverage finding above.
- Position-level 1% max-risk-per-position (RISK_LIMITS) is respected by the 0.5% risk/trade
  recommendation (half the ceiling, deliberately conservative).

## 6. CIRCUIT BREAKERS / KILL-SWITCH — for THIS combined book (Book + Sweep-E@10% + Swing@10%, paper)
Ladder keyed to the flagship combo's own real 2022-2025 stats (worst month -6.61%, realized maxDD
-13.94%, VaR99 -2.37%/-2.47% hist/MC) plus the existing RISK_LIMITS hard triggers (unchanged, not
loosened):

| level | trigger (from book-equity high-water mark) | action | who |
|---|---|---|---|
| L0 Normal | DD < 5% | monitor only | Risk (me), weekly snapshot |
| L1 Watch | DD 5-8% (captures the flagship's typical worst-month range) | freeze NEW sweep/swing entries; re-check whether quarterly sweep-vs-s1f correlation has moved toward the 0.53 RED ceiling (regime check per §3); no forced closes | Risk → CIO notified |
| L2 De-risk | DD 8-12% **OR** any single-day book loss >3% (existing RISK_LIMITS hard trigger, unchanged) | **halve sweep+swing weights 10%→5% each first** (cheapest/fastest to unwind — see below); hold the core option book unless L3 also fires | CIO review before next entry (existing rule) |
| L3 Kill-switch | DD ≥ 14% (at/above the flagship's own realized in-sample maxDD — a breach of history) **OR** any realized loss > 2× modeled worst-case (existing hard rule) | **FLATTEN sweep+swing entirely**; pause ALL new entries firm-wide pending CIO+Principal review; only then consider unwinding the option sleeves (s1f/b1b) if the breach is book-wide, not sweep/swing-specific | CIO + Principal |

**De-risk SEQUENCE and why:** sweep/swing are single-instrument NIFTY futures, deep-liquid, small lot
count at the recommended conservative sizing (median ~1-4 lots) → **flatten FIRST**, same session,
low single-digit minutes even with staggered limit orders, at a cost of roughly one exit leg of the
futures round-trip (COST_STANDARDS 5.0-6.5pts RT → ~2.5-3.5pts one-way + slippage, i.e., Rs150-350/lot
— trivial in rupee terms at this size). The core book's OPTION sleeves (s1f 0DTE straddle, b1b) are
slower and costlier to unwind (bid-ask widens in stress, defined-risk legs need paired closes) — so
they are the LAST resort, only at L3 and only if the drawdown is book-wide rather than isolated to
the futures candidates. This ordering is new to this memo (not previously specified) and should be
added to the standing kill-switch-drill playbook for this book.

**Time-to-flat estimate:** sweep+swing combined at recommended weights ≈ Rs20L notional, single-digit
median lots → full flatten achievable within one trading session (realistically minutes, not hours)
given NIFTY futures' continuous liquidity; no circuit/volume-fill risk at this instrument (contrast
with the firm's single-stock-options landmine #7b, which does not apply to index futures at this size).

## 7. CRASH-BLINDNESS — stated honestly, every number above carries this caveat
- **Book (2022-2025) and swing_D10 (2021-2025): fully crash-blind.** No 2018/2020-grade event in
  either window. Every book-alone and swing-alone stat above (VaR, maxDD, worst month) would be
  optimistic in a true crash — this is the standing 04_RND_LAB Lessons-Learned caveat, restated here
  because this memo's own combined-book numbers inherit it.
- **Sweep_E/D: NOT crash-blind for itself** — 11.34-year history including COVID (2020), the 2015-16
  correction, and 2018 IL&FS. Its own worst month (full history) is -12.0%, which happens to have
  occurred WITHIN the 2022-2025 window (Sep-2025), not during COVID — i.e., sweep's own worst month
  on record is NOT a crash month, it is an ordinary bad month. COVID itself was sweep's BEST stretch
  (+37.2% over 2020-02-15..04-15), per §3.
- **A4 short-vol proxy: real 2011-2021 settles including COVID**, used ONLY for the §3 crash-joint
  test (cycle-grain, not daily — cannot enter the correlation matrix on equal footing with the daily
  series above, stated as a limitation, not smoothed over).
- **Could NOT stress the COMBINATION (book+sweep+swing all three together) through a true crash**,
  because no single window has all three series active simultaneously with COVID-grade stress present
  (book/swing don't reach back to 2020; the crash evidence in §3 is sweep-vs-a-different-short-vol-
  proxy, not sweep-vs-the-actual-book). This is the honest limit of what real data allows today.
- **The long-dated income sleeve cannot be stress-tested at all — it does not exist yet.** Nothing in
  this memo should be read as having validated its crash behaviour; §3's finding is a plausible
  mechanism and a real analogous data point, not a measurement of the actual future sleeve.
