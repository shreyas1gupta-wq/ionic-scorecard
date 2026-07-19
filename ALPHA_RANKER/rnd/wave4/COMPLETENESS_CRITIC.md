# ALPHA_RANKER — Adversarial Completeness & Self-Deception Audit
**Red Team (Nikhil Bose, E-014) · 2026-07-17 · reports to CIO**
Targets: rnd/FINAL_MODEL.md (7-leg composite), wave-4 additions (clean-surplus, depreciation, 40 Tier-A rescues), ABSOLUTE_SCORER_SPEC.md, the low-t rescue principle.
Tags: [DATA] on-disk fact, [INFERENCE] my construction, [OPINION] my judgment.

---

## BOTTOM LINE (read first)
**Verdict: CAUTION — on solid ground on PROCESS, fooling itself on MAGNITUDE and on the COUNT of independent finds.**
The program's honesty machinery is genuinely good: survivorship remediated, T1-T10 clean, PBO/DSR failure openly
disclosed, forward test frozen with a content hash and evaluate-once protocol. That is real discipline and it is why
this is CAUTION, not OVER-MINED. But three specific self-deceptions have crept in with wave-4, and the low-t rescue is
the vector for two of them. None is fatal; all are fixable before anything touches a book. Nothing here is in-sample-promoted, which is the saving grace.

---

## RANKED BLIND-SPOTS & RISKS

### #1 — MAGNITUDE IS NOT TRUSTWORTHY, AND THE RESCUE RANKS ON IT [DATA]
The whole IC-vs-money pivot ranks Tier-A rescues by "absolute net-of-cost return" (H002 19.3%/yr, H043 19.0%, H004 17.6%).
That number is `net_LS_v2` from `scoreboard_v2.csv` — the SAME field the firm's own docs say is the *corrected* one. It is not.
- [DATA] `CAPSTONE_value_EY_1Y` net_LS_v2 = **0.129 (12.9%/yr)**. `H046_ey_only_1Y` net_LS_v2 = **0.0195 (1.95%)**.
  Same factor (earnings yield), same horizon, **6.6× apart**, both in the "corrected" v2 file. FINAL_MODEL §5b calls the
  authoritative EY figure "~+2%/yr." So the scoreboard the rescue ranks on carries EY at ~13% — inconsistent with the
  model's own headline by 6×.
- [DATA] Whole-scoreboard net_LS_v2: mean 7.2%, **max 97.3%/yr**, 91 of 430 cards >15%/yr. Cost-corrected market-neutral
  decile long-shorts on Indian large/mid-caps do not throw 97%/yr. The ×12 bug is documented as "fixed," but these
  magnitudes say a return-overlap / construction inconsistency survives in v2.
- [INFERENCE] Consequence: the rescue's headline ordering (H002 > H043 > H004 by "money") is built on a field the firm
  itself cannot reconcile to within 6×. Ranking rescues by absolute return is the right *principle* (per the low-t memo),
  but the *instrument* is broken. **Implication:** before any rescue is green-lit, rebuild ONE consistent net-of-cost
  decile-LS figure (single construction, single annualization, verified on EY = ~2%) and re-rank. Until then, treat every
  "%/yr" in WAVE4_FINDINGS and RESURRECTION_RESCREEN §4-5 as unverified.

### #2 — THE 40 RESCUES ARE ~1–2 INDEPENDENT BETS, NOT 6 FAMILIES, AND OVERLAP THE MODEL [DATA]
- [DATA] RESURRECTION_RESCREEN §4 states all six Tier-A families are "momentum/trend-adjacent technical factors at 1Y."
- [DATA] `reports/orthogonality_matrix.csv` contains NONE of H001/H002/H003/H004/H043 — orthogonality was **never run**
  on the rescued families, neither against each other nor incrementally against the frozen 7-leg model.
- [DATA] The model ALREADY owns `mom_resid_plain` + `trend_ma65_slope`; within the model these two correlate 0.37.
- [OPINION] The proud honesty step of the base model was collapsing 12 raw factors → 7 independent bets. That exact step
  was skipped for the rescues. "40 cards / 6 families" is count-inflation: it is one trend factor and one momentum factor,
  sliced by MA-length and lookback, most of which the model already has a representative of. **Implication:** run the
  incremental-IC / orthogonality test of each rescue family against the frozen 7-leg composite before calling any of them
  a "genuine NEW rescue" (H043 beta-adj momentum is the only plausible net-new bet, and it is a single card, n_trials=1).

### #3 — H002 IS A 48-VARIANT SWEEP DRESSED AS A "SINGLE PRE-REGISTERED HYPOTHESIS" [DATA]
The Tier-A gate is "single pre-registered hypothesis, n_trials < 100 = modest search space." That threshold launders a sweep.
- [DATA] H002 = **48–49 variants** in the scoreboard (MA-length {20..200} × {slope, distance, stack} × {1M,1Y}).
  net_LS_v2 across those variants ranges **−8.8% to +20.3%**; signed_ic_ir from −0.22 to +0.80. The rescreen reports the
  winner (`slope150`, 19.3%) as "the family."
- [DATA] The doc's own §4 says "H002 n_trials=82/family"; scoreboard/trials_counter say 48. The trial count feeding the
  gate is itself inconsistent.
- [OPINION] Picking the best of 48 length/type variants IS the multiple-testing the rescue claims exemption from. "n_trials
  < 100" is not a small search space when the search is over a smooth parameter and you keep the max. Sign is stable across
  *regime buckets* (as reported) but NOT across the *parameter sweep* (half the variants are ≤0) — the doc reports the
  first and is silent on the second. **Implication:** for sweep families, forward-test the WHOLE plateau's rank-average
  (or a pre-registered single length), never the post-hoc argmax. Report the sign distribution across the sweep, not just across regimes.

### #4 — WHAT HAS NOT BEEN TESTED AT ALL (genuine blind spots, not variant-spam)
- [DATA/OPINION] **Turnover / capacity / real fills on the rescued technicals.** MA-slope and vol-scaled momentum are the
  highest-turnover factors in the book, and the model's own lesson (CONSOLIDATION §3) is that the regime overlay died on
  *gross* return dilution, not cost. Yet the rescues are ranked on a "cost-corrected" number of unknown provenance (#1) and
  no fill-audit / ADV-participation exists for them. A 19%/yr technical LS that trades monthly on 500 names is a capacity
  and slippage question that is completely untested. This is the most likely place a rescue evaporates live.
- [OPINION] **Cross-factor timing / correlation of the sleeves in a crash.** Everything is validated as within-date
  cross-section. What is untested: do the 7 legs + additions co-crash (all long-quality/short-junk unwinds together in a
  junk rip, Feb-2016 / Nov-2020-style)? The book-level drawdown under a factor-crash regime is not modelled — only
  single-factor bear IC is.
- [OPINION] **Non-monthly / non-linear payoff structure.** The entire program is monthly-rebalanced linear rank-IC. The
  low-t memo itself flags the "~0 IC most of the time, huge payoff in the rare event" tail profile as a first-class case —
  but nothing in the corpus tests any signal on that basis (event-study P&L, conditional-on-tail returns). PEAD was killed
  on monthly IC and then on event-time IC, but no signal has been evaluated for convex/tail payoff, which is the Principal's
  stated interest and a true modality gap.

### #5 — ABSOLUTE SCORER: A DISCIPLINED SPEC THAT STILL SMUGGLES AN UNVALIDATED TIMING BET [INFERENCE/OPINION]
- [DATA] The spec is unusually honest: order-preserving invariant + unit test, coefficients pre-set from priors (not
  fitted), soft tanh (no per-crash dummies), leave-one-bear-out gate, provisional-sign-only, one-directional (never feeds
  the frozen selection engine). The `s_mkt` breadth/VIX scalar is independently validated (maxDD −52%→−26%).
- [OPINION] The order-preservation invariant protects SELECTION. It does **nothing** to protect the LEVEL/SIGN — and the
  level is set by the `α_h·M` market-valuation term, which is validated on the *most* data-starved axis in the building
  (~5 bears). So the invariant is a real guard against the return-blend relapse, but it is *not* a guard against the actual
  new bet: a market-timing call that can flip the sign of the whole book ("best house on a street that's on fire").
- [OPINION] Harm channel: "provisional-sign only" is a caveat in a spec; in the Principal's head a "−12, market-regime-
  capped" on a top pick becomes a de-risk instruction. If the valuation band is high and the market rips (2020-21, 2023-24),
  the unvalidated layer causes a real, attributable miss — wearing the validated product's authority. The `M` term is a
  Shiller/Buffett-indicator market-timing bet, and those have famously long, wrong stretches. **Implication:** ship the
  `s_mkt` sizing dial (validated) and the dual-display STRUCTURE now; keep the `α_h·M` level term dark (display sign only,
  cap its contribution hard, never let it drive a negative absolute on a top pick until it clears leave-one-bear-out AND a
  forward grade). Genuine improvement only if the market term stays quarantined; a way to do harm the moment it doesn't.

### #6 — OVER-MINING: 496 TRIALS ON ~13 INDEPENDENT YEARS [DATA]
- [DATA] trials_counter.json = **496 trials**; PBO 0.909–0.922 and DSR ≈ 0 on both biased and PIT universes; FINAL_MODEL
  §5a: portfolio-level history is really ~2012–2025 (~13yr), ~5 bears; IC_mean decayed 0.190 (2015-20) → 0.111 (2020-25).
- [INFERENCE] 1Y-forward returns rebalanced monthly are ~12× overlapping → the *independent* sample is ~13 annual blocks
  / ~5 bear regimes, not 145 IC dates. 496 trials against ~13 independent years = the data has been looked at ~38× per
  independent observation. **No in-sample MAGNITUDE can be trusted, full stop.** What *can* be believed, and only weakly:
  the SIGN/RANK of the two or three most economically-forced, most-orthogonal factors (EY value, momentum) — because those
  have independent global literature and survive the placebo/lag gates — but even their magnitude is a forward-test question.
- [OPINION] This is not disqualifying *because* the program already concluded the same thing and built the frozen forward
  test as the only escape. The danger is behavioural: each new wave (wave-4 added ~40 trials) makes the multiple-testing
  wall taller, and the rescue mechanism is a licence to keep mining. Every rescued family is a new trial on the same ~13
  years.

---

## Q1 — IS THE LOW-t RESCUE SOUND OR SLIPPERY? (the ruling)
**Ruling: SOUND IN PRINCIPLE, SLIPPERY IN THIS EXECUTION — recoverable with three fixes.**

The principle is correct and I endorse it: low-t on a thin sample is Type-II (power), not evidence of no-effect; keeping
lag + placebo as the only hard gates is right; forward-testing (not in-sample promoting) the rescues is the correct
disposition. The base logic is not the problem.

**THE LINE (state it precisely).** A signal is "underpowered-but-real" and rescuable ONLY if ALL of:
1. **Pre-registered, single construction** — not the argmax of a parameter sweep. (H002/H001 FAIL: 48/20-variant sweeps,
   winner reported as the family. H043/H003 PASS: single cards.)
2. **Sign stable across the SWEEP and across eras/regimes** — not just across regime buckets of the chosen variant.
   (Reported for regimes; NOT reported for the sweep — several H002 variants are ≤0.)
3. **Incrementally orthogonal to what the book already owns** — proven by incremental-IC vs the frozen composite, not
   assumed. (NOT DONE for any rescue; all 6 overlap existing momentum/trend legs.)
4. **Economically forced ex-ante** with an independent (global) prior — momentum/value qualify; a specific MA length does not.
5. **Absolute edge not one-or-two-prints-deep** (leave-one-bear-out) — the memo's own guard; applied to Amihud/cross-asset,
   NOT yet to the 40 technical rescues.
6. **Ranked on a magnitude the firm can reconcile** (see #1 — currently fails at 6×).

On the wrong side of that line TODAY: the H001/H002 sweep winners (fail #1, #2-sweep, #3), and any rescue quoted by a
net_LS_v2 the firm can't reconcile (all of them, #6). On the right side: H043 beta-adj momentum and H003 residual momentum
as *single* hypotheses — but they still owe #3 (orthogonality vs the model, which already has residual momentum) and #5.

**FALSIFICATION TEST for the rescue principle itself** (pre-register, run once): take the 40 Tier-A rescues and an equal
number of DELIBERATELY-NULL sweeps — same MA-length/lookback machinery run on RANDOMLY PERMUTED forward returns (or on a
scrambled cross-section). Push both sets through the identical rescreen pipeline. **If the null sweeps get "rescued" at a
materially similar rate** (similar rescue-score distribution, similar count clearing rescue-score ≥ 0.30 with clean
lag/placebo), the rescue criterion is manufacturing candidates from noise and must tighten. **If real rescues clear
materially more often than the null set, the principle is doing real work.** This is the placebo the rescreen never ran on
itself — it ran placebo on individual cards but not on the RESCUE DECISION. Until that test passes, "rescued" ≠ "real."

---

## Q3 — SINGLE BIGGEST RISK & THE Dec-2026 NULL POST-MORTEM
**Biggest risk: the honest edge is real but too small to survive real turnover/costs at capacity — i.e. the model is a
true ~2%/yr EY-class cross-sectional tilt that the inflated net_LS_v2 figures (#1) have made everyone quietly believe is a
12–20%/yr edge.** If the frozen 7-leg forward test comes back null-or-marginal in Dec-2026, the most likely reason (ranked):
1. **Decay + small true magnitude:** IC already halved 0.19→0.11; forward realizes ≤0.11, decile spread net-of-cost lands
   near zero. The magnitude confusion (#1) means nobody has an honest prior for how thin "success" actually is.
2. **~7-month PIT lag on the banked scores** (FROZEN_SPEC §4): the "1Y forward" window is really shorter and stale — a
   grading artifact that can null a real edge.
3. **Turnover/cost on the trend/momentum legs** (#4) eating the gross in live conditions the backtest didn't model.
**De-risk NOW:** (a) fix and reconcile the one net-of-cost figure so the success bar is set against an honest ~2–4%/yr
prior, not a fantasised 12–20%; (b) pre-register the exact net-of-cost decile-LS statistic and its cost model as part of
the grade, not just IC; (c) log the PIT-lag-adjusted window explicitly. All three are free and must precede the grade.

---

## Q5 — CAN ANY IN-SAMPLE RESULT BE TRUSTED?
[INFERENCE] For **magnitude: no** — 496 trials / ~13 independent years / DSR≈0 / PBO≈0.92 forbids it, and the 6× EY
inconsistency proves the point empirically. For **existence/sign/rank of the 2–3 most economically-forced, gate-clean,
literature-backed factors (EY, momentum, quality-composite): weakly yes, directionally**, pending the forward test — these
would be believed even by an outsider with no access to this search. Everything else (the rescues, the 8-leg blends, the
cross-asset sizing, the absolute-scorer magnitude) is a forward-test candidate whose in-sample number carries no
evidentiary weight. The program already reached this verdict; the wave-4 rescue must not be used to quietly re-admit
in-sample belief through the "money-first" door.

---

## WHAT WOULD FLIP THIS TO SOLID
1. One reconciled net-of-cost decile-LS figure, verified EY ≈ 2%/yr, re-rank the rescues on it (#1, #6).
2. Incremental-IC / orthogonality of every rescue family vs the frozen 7-leg composite (#2, line-item #3).
3. Sweep-argmax rescues (H001/H002) replaced by plateau-rank-average or a pre-registered single length; report sign
   distribution across the sweep (#3).
4. The rescue-principle placebo (null-sweep falsification, Q1) run and passed.
5. Absolute scorer: `α_h·M` level term quarantined (sign-display, capped, no negative-on-top-pick) until leave-one-bear-out
   + forward grade (#5).
6. Leave-one-bear-out on the 40 technical rescues, per the memo's own guard (#5).
