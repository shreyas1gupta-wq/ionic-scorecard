# AMENDMENT (frozen 2026-07-13, BEFORE any arm-C variant has run) — ablation arm C2
Principal question: do naming, salary/bonus (AlphaPoints) framing, and persona memory/lessons actually help?

## Design (pre-registered secondary analysis; the frozen A/B/C bar in PROTOCOL.md S6 is UNCHANGED)
- **C (full)**: 3-stage pipeline (review -> adversarial second review -> synthesis) run AS THE FIRM —
  real persona agents (Head of Quant / Red Team / CIO persona files: names, charters, AlphaPoints
  incentive context, appended Lessons Learned). "Standing persona knowledge" per PROTOCOL S8.
- **C2 (ablated)**: BYTE-IDENTICAL pipeline structure, prompts stripped to neutral roles
  ("experienced quantitative reviewer" / "skeptical second reviewer instructed to refute" /
  "final arbiter") — no firm names, no incentive framing, no lessons, no persona files.
- Same battery, same verbatim arm prompt core, same task order, fresh contexts, one run each
  (each variant is a distinct arm-system seeing the battery once — no reruns, no selection).
- Same budget cap as C (1.5x measured arm-B average); same blind grading batch.

## Decomposition (reported, not gated)
- structure effect = C2 - B
- identity/incentive/memory BUNDLE effect = C - C2 (bundle test; components not separable at this budget — stated honestly)

## Interpretation rules (frozen)
- If C > C2 meaningfully (>=2 defects-found or >=0.25 mean-score): the firm dressing earns its tokens.
- If C ~= C2: the value is STRUCTURE, not theater — AlphaPoints/naming/memory get demoted to
  flavor pending WS-3b, and we say so in the publication.
- If C < C2: persona baggage HURTS review quality — a first-class finding; publish it.
