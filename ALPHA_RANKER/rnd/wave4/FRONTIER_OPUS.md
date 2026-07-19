# WAVE-4 FRONTIER — Independent Quant Judgment (Arjun Rao, E-004)
> Written from first principles against the files, before reconciliation with the two Fable coverage/hypothesis agents.
> Verified: FINAL_MODEL.md, CONSOLIDATION.md, SURVIVORS.md, trials_counter.json (457 total), forward_test/FROZEN_SPEC.md + freeze_manifest.json, scoreboard_v2.csv (430 rows).

---

## Q1 — GOVERNING VERDICT: does more research help or hurt? (read this first)

**A large trial-generating wave HURTS the stated goal (certify/deploy THE 7-leg composite). The binding constraint is NOT an idea shortage — it is TIME on a forward test we have ALREADY frozen and banked.**

The facts that decide this:
- DSR ≈ 1.58e-58, PBO ≈ 0.922 on BOTH the biased AND the survivorship-corrected universe (`FINAL_MODEL.md` S5-RISKOFFICE). This is a *multiplicity* verdict, not a construction defect. **More trials only raise the N the model must be deflated against — deflation is monotone in trial count. No sensitivity battery, perturbation test, or re-run can lower it. They can only make it worse.**
- The one gate compute cannot close — a fresh, calendar-time, evaluate-once held-out test — **is already built and frozen**: `composite_final.py` sha256 `9fbfe8...61cb` on record, 802 names banked as-of 2025-12-05, pre-registered success bar ~0.11 realized IC, grade ONCE at the Principal's chosen horizon (~Dec 2026 for a 12-mo window). No grading has occurred; none should before the horizon.

So for THIS model the answer is binary and already set: **we wait and grade once. Nothing a wave produces can certify it faster, and touching the frozen file voids the test.**

**Honest EV of the wave, then, splits cleanly:**
- **EV of research aimed at rescuing / re-certifying / "improving" the 7-leg composite = negative.** It deepens the hole and risks tampering with the freeze. Do not do it.
- **EV of a SMALL, orthogonality-first wave hunting genuinely NEW, independent edge = positive but bounded.** Its payoff is *option value on the NEXT model* — a second sleeve that (a) diversifies the book and (b) gets its OWN fresh forward clock. Anything it finds inherits the same evaluate-once forward requirement; it does not shortcut this one.

**Therefore the wave should be SMALL and orthogonal-only, not large.** Cap new hypotheses hard, pre-register each with its own family trial-count and kill threshold, so the successor never inherits a 457-trial deflation. Size for a handful of high-conviction orthogonal bets, not breadth.

---

## Q2 — Ranked unexplored directions (by honest EV = orthogonality × money × data-availability × statistical power)

Every leg today is a slow, monthly, cross-sectional price+fundamental signal. The white space is (a) ownership/flow, (b) forward-looking/expectations, (c) return-component decomposition, (d) the sizing axis. Data reality gates this list — I mark what is on disk vs blocked.

**1. Promoter / insider (SAST) accumulation drift — HIGHEST EV.**
Mechanism: promoters/insiders buy ahead of value realization; SAST/bulk-deal disclosures. Orthogonal: it is an *ownership-change* signal, uncorrelated by construction with price momentum, value level, or accounting quality. Why top: **the signal is already validated on our own data** (IC_IR 1.33, mono 0.72, gates clean, correct sign — `CONSOLIDATION.md` resurrection list); it is blocked ONLY by stale 2023-12 shareholding (17% coverage). This is nearly-free EV: the research is done, it needs a *data pull*, not a search. ONE test: pull fresh NSE SAST/shareholding 2024-26 (home-network, D-033), re-run the existing card — does IC_IR hold >0.5 at >50% coverage with correct sign and clean one-day-lag?

**2. Gross profitability, GP/Assets (Novy-Marx) — high EV, fully buildable now.**
Mechanism: gross profit / total assets is the cleanest "quality" numerator, documented to add over BOTH value and standard quality composites. Orthogonal: QMJ is a *blended* rank-average; GP/A is the specific sub-signal shown to survive controlling for value and for profitability composites — likely corr < 0.6 to QMJ. Data: on disk (fundamentals PIT). ONE test: incremental IC_IR of GP/A over the frozen 7-leg composite residual on panel_long — promote only if corr<0.6 AND ΔIC_IR>0 AND clean lag/placebo.

**3. Overnight-return premium (overnight vs intraday decomposition) — medium-high EV, buildable.**
Mechanism: the overnight (prev-close→open) return component carries a documented premium distinct from the intraday component; consistent with the firm's own "overnight-drift lead" memory. Orthogonal: it decomposes a return the 12-1 momentum leg only sees in aggregate — a different component, not a different lookback. Data: buildable from daily bhavcopy open/close (no intraday feed needed). Caveat: higher turnover → cost-sensitive. ONE test: cross-sectional IC of trailing-N-day overnight component, net-of-cost decile spread positive AND incremental over the momentum leg.

**4. Leading (predictive) regime classifier for the SIZING layer — medium EV. I argue AGAINST it being #1.**
Mechanism: replace/augment the current trailing breadth (%>200DMA) + contemporaneous VIX scalar with a *leading* aggregate signal (yield-curve slope, credit spreads, cross-asset momentum, VIX term-structure) to set gross exposure earlier. Orthogonal: it lives on the time-series exposure axis, near-zero correlation to cross-sectional stock ranks by construction — genuinely orthogonal, true.
**But the Principal's instinct that this is #1 is wrong, and here is the money reason:** validation power. A cross-sectional leg has hundreds of independent name-date observations per rebalance — real statistical power, real DSR headroom on its own family. A regime-timing overlay has **N ≈ 5 independent bear episodes in 21 years (2008, 2011, 2018, 2020, 2022)**. You cannot certify a timing edge on N≈5 — it is a DSR death sentence *by construction*, and macro-timing is historically the most regime-unstable, most overfit-prone corner of quant. The existing breadth scalar already captures the bulk of the win (maxDD −52%→−26%). A "leading" version is a marginal improvement on an already-thin, hard-to-validate axis. It belongs at ~#4, capped by episode count — not at the front. ONE test: does it beat the current breadth+VIX scalar on OOS maxDD-adjusted return with a one-day-lag causal check AND survive leave-one-bear-out (drop 2020 — does it still work)? If it dies without 2020, it is a 2020 artifact.

**5. Analyst EPS-revision momentum — high *if* data exists; almost certainly data-blocked.**
Mechanism: the single most-documented factor orthogonal to both price-momentum and value — sell-side FY1/FY2 estimate revisions lead price. Orthogonal: it is a *change in expectations*, distinct from realized-return momentum (H003) and static value level (EY). ONE test (gated): a 1-hour data-availability probe FIRST — do we have ANY estimate-revision history on disk? We have no I/B/E/S. Build only if a source exists; otherwise park honestly, do not fabricate a proxy.

**6. Options-implied cross-section (IV skew / put-call) — orthogonal but data-thin.**
Mechanism: IV skew and put-call ratios are forward-looking risk-premium signals (Xing-Zhang-Zhao). Orthogonal: implied, not realized. Data: thin/patchy (210 F&O names, `W2_OPT_DATA_COVERAGE.md`). ONE test: coverage probe, then IC on the 210-name subset with a strict ADV/liquidity gate — if the tradeable subset is <100 names the capacity is too small to matter, kill.

**7. Fundamental-trend momentum (ΔGP/A, ΔROE 4Q) — medium, QMJ-overlap risk.**
Mechanism: acceleration in profitability leads returns. Orthogonal-ish but the QMJ growth sub-component may already own it. ONE test: incremental over the composite AND over the GP/A *level* (direction #2) — must beat both to earn a slot.

**8. Net-operating-assets / balance-sheet bloat (Hirshleifer) — low, likely redundant.**
Mechanism: NOA accumulation predicts low returns. Likely correlated with asset-growth + CFO/PAT legs already in the model. ONE test: corr to those two legs <0.6 gate BEFORE scoring; if it fails the corr gate it is not a new bet.

**Recommended wave scope: pursue #1 and #2 for real; run the #3 build and the #4 leave-one-bear-out honestly; treat #5/#6 as data-availability probes only; #7/#8 only if #2 clears and time remains.** That is the entire disciplined wave.

---

## Q3 — Combination-method verdict

**Worth ONE shot — SIZING-axis only:**
- **Formalized regime-GATED leg weighting (exposure, not selection).** The quality-in-bear gate already tested clean (`W3_qualgate`, IC_IR 0.44/1Y, 1.57/5Y, lag+placebo pass). The sanctioned extension is a *causal* p_bear that up-weights QMJ/EY and down-weights momentum/trend in bear/high-vol, floored at 0 (never short a leg). This is exposure control, which the firm already endorses — NOT return-blending (tested and rejected: lifts full-cross-section IC but dilutes the tradeable extreme-decile spread). Pre-register it, forward-test on its OWN fresh clock, and it MUST NOT touch the frozen composite's rank-average.

**Worth ONE diagnostic shot only, low expectation:**
- **Value×quality conditional double-sort** as an orthogonality *diagnostic*, not a product. History says it will just re-express the linear composite with more turnover — the firm already killed QARP/GARP/Greenblatt/magic-formula interactions, none beat EY-alone. Run it once to confirm the linear rank-average captures the interaction; expect a null.

**TRAPS — do not:**
- **ML / ridge / tree / any fitted-weight combiner.** Already failed ("ML/ridge overfits; forced interactions destroy strong legs"). The mechanism is decisive: with 7 cross-sectionally-correlated legs, monthly rebalance, ~13yr usable (~150 rebalance dates), an ML combiner has far more effective parameters than independent time-blocks → it fits regime-specific noise, AND every hyperparameter is a trial → catastrophic multiplication of the exact DSR-deflation this forward test exists to escape. **Rank-average's zero-fitted-parameter property is precisely what keeps its trial count honest — any fitted weighting scheme re-opens the multiplicity hole.** Keep rank-average as the selection combiner, permanently. Innovate only on the exposure/sizing axis.

---

## Q4 — DO-NOT-DO LIST (the traps that would deepen the overfit hole)

1. **Do NOT run more variants of the 7 legs or the composite** — MA windows, momentum lookbacks, weighting schemes, decile-vs-quintile, rebalance offsets. Each adds a trial to the family that IS the binding overfit constraint; it cannot help the frozen model and deflates every successor.
2. **Do NOT edit, re-tune, or re-freeze `composite_final.py`.** A hash mismatch voids the forward test. No "small improvements" to the frozen spec — ever. New ideas become a NEW version with its OWN fresh forward clock.
3. **Do NOT grade or peek at the forward test early.** Interim checks that inform a stopping decision are stopping-rule p-hacking — they recreate the multiplicity we froze to escape.
4. **Do NOT re-test dead ideas hoping for a new answer.** PEAD (killed twice, both grains), seasonality (passenger, ΔIC_IR −0.047), Weinstein stage-2 (sign-flip), short-term mean-reversion, raw growth, ROCE-longevity (wrong sign), deleveraging, FII/DII accumulation (wrong sign), forced value×quality interactions. Reopen only on pre-registered resurrection conditions WITH new data.
5. **Do NOT add legs absorbed by existing ones.** BAB↔QMJ 0.77; DCF/market-state/smallcap↔EY 0.74-1.00. Enforce the orthogonality gate (corr<0.6 AND ΔIC_IR>0) BEFORE scoring a candidate, not after — no more redundant "12 factors that are really 7."
6. **Do NOT quote in-sample IC_IR (1.345 / 1.760) or ×12-annualized magnitudes as evidence.** They are inflated by the 457-trial search and a disclosed decay trend. The forward test's ~0.11 decayed-era bar is the ONLY honest success benchmark.
7. **Do NOT build a large wave.** Cap new hypotheses; pre-register each with a kill threshold and its own family trial-count. Few high-conviction orthogonal bets beat many marginal ones — every promote inherits the same evaluate-once forward requirement.
8. **Do NOT confuse "orthogonal + high in-sample IC" with deployable.** Nothing here deploys without its own frozen forward test. The wave produces *candidates for the next freeze*, not certified alpha.
9. **Do NOT let a leading-regime-classifier's orthogonality seduce the wave into over-investing in timing.** N≈5 bears caps its certifiability; validate leave-one-bear-out or don't build it.

---
*Reconciliation note for the parent: if the two Fable agents' coverage map shows any of directions #1-#3 already tested and killed on fresh data, drop it; my ranking assumes the SAST signal is still only data-blocked (not re-killed) and GP/A has not been run as a standalone incremental test — both should be confirmed against their coverage output before spending the wave's budget.*
