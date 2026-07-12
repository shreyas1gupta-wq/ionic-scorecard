# MODEL-GRID CARD (FROZEN 2026-07-13 pre-run) — models x tasks x cost
Principal ask: metrics/scores for OUR SYSTEM vs Sonnet 5 vs Fable 5 vs Opus 4.8 (+ Haiku 4.5 as the cheap floor)
on token usage and output quality across financial AND general tasks. All runs metered (in+out tokens, $, wall-clock).

## Axis 1 — OBJECTIVE (ground truth): WS-4 defect battery, single-call arm per model
- Arms: A-fable (DONE 2026-07-13, 20/20 banked), A-sonnet, A-opus, A-haiku — identical verbatim prompt, no tools,
  fresh context per task, one run each (each model = distinct arm-system; battery unseen by it).
- Plus system rows from the main experiment: B-fable, C-fable (firm personas), C2-fable (ablated).
- Metrics: defects-found (score>=2 of 16), clean-task FP rate (of 4), mean score, tokens, $, score-per-$.

## Axis 2 — TASK SPECTRUM (8 frozen tasks MG01-MG08, one shot per model per task, temperature default)
| id | type | grading |
|---|---|---|
| MG01 | Backtest DESIGN: spec a leakage-proof backtest for a NIFTY500 monthly momentum idea (data, PIT rules, costs, controls, kill criteria) | rubric (10 anchor items incl PIT membership, available_date, same-exit placebo, cost model, trials accounting) |
| MG02 | IDEA GENERATION: 5 falsifiable, non-overlapping alpha hypotheses for Indian markets w/ cheapest kill-test each | rubric (falsifiability, cheapness of test, non-overlap, mechanism stated, no survivorship-blind ideas) |
| MG03 | PIPELINE ENGINEERING: resume-safe daily ingestion design for an exchange archive behind a flaky proxy (ledger, atomicity, verification, alerting) | rubric (resume-safety, idempotency, verification gate, failure alerting, rate-limit honesty) |
| MG04 | RISK MEMO: 1-page pre-mortem for a short-options book going into a macro event week | rubric (tail quantification, liquidity honesty, concrete de-risk triggers, no hedging platitudes) |
| MG05 | QUANT PUZZLE (objective): expected number of distinct values when drawing n times uniformly with replacement from {1..n}, exact formula + limit ratio as n->inf | EXACT: n(1-(1-1/n)^n); ratio -> 1-1/e ≈ 0.6321 |
| MG06 | PROBABILITY BRAINTEASER (objective): ticket-collector variant — expected draws to see all 4 suits from an infinite uniform card stream, exact | EXACT: 4*H4 = 4*(1+1/2+1/3+1/4) = 25/3 ≈ 8.3333 |
| MG07 | DATA-QUALITY PLAN: verification protocol for adopting a new third-party fundamentals dataset (sampling, cross-checks, PIT-safety, catalog) | rubric (known-value spot-checks, PIT test design, coverage-by-year check, quarantine rules) |
| MG08 | RESEARCH DIGESTION: given an abstract claiming a 2.1-Sharpe ML strategy, list the 6 most likely failure modes to check before believing it | rubric (overfitting/deflation, costs, lookahead, survivorship, regime, capacity — credit only mechanisms, not buzzwords) |
- Task prompts frozen in MG01.md..MG08.md (this folder). No model sees rubrics/answers.
- SYSTEM row on axis 2: the 3-stage firm pipeline (as arm C) runs MG01-MG08 once (fable), reported beside single-model rows.

## Grading (frozen)
- MG05/MG06: objective — exact answer correct (1) / correct with minor slip (0.5) / wrong (0). No judge needed.
- Rubric tasks: TWO independent blind judges (sonnet-tier, fresh contexts) score each anonymized answer against the
  anchor list (0-10); grade = mean; disagreement > 3 points -> third judge, median. Judges never see model identity.
  LLM-as-judge caveats (Zheng et al. 2306.05685: position/verbosity/self-enhancement bias) mitigated by: shuffled
  presentation, anchored rubrics, no side-by-side ranking (absolute scoring), identity scrubbing. Labeled judge-scored.
- OVERALL: no single blended "IQ number" — we report the score-vs-token Pareto per axis; any composite is
  shown ONLY as equal-weight mean of normalized axis scores, labeled composite-for-visualization.

## Integrity
- All prompts frozen in this commit BEFORE any run. One shot per (model, task) — no retries, no best-of.
- All tokens counted incl. system rows' full pipeline overhead. Same accounting as PROTOCOL S4.
- Publish whatever falls out, including "cheaper model matches Fable on X" — that IS the cost-grid finding.
Trials +1 (grid counts as one pre-registered experiment).
