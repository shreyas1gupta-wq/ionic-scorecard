---
name: retro
description: Post-task self-improvement — capture a lesson from a mistake, catch, or Principal correction into the responsible agent's persona (and propagate if general). Use for /retro <what happened>, after any correction, or when an engagement ends with a notable learning.
---

# /retro — lesson capture (SELF_IMPROVEMENT layer 1)

1. Identify: WHO learned it and WHAT the lesson is — and TAG it with a root-cause from the failure taxonomy (Reflexion adoption 2026-07-04): `[data-artifact]` `[cost-model]` `[overfit/DSR]` `[lookahead]` `[cadence-miss]` `[sycophancy]` `[ops/pipeline]` `[sizing/tail]`. Name the causal diagnosis, not the symptom — tagged lessons cluster and dedupe instead of sprawling.
   (original guidance) WHAT = one-sentence, specific, actionable lesson (bad: "be careful with data"; good: "c4_short_thru normalizes by a decaying leg — never consume raw").
2. Append a dated line to that agent's `## Lessons Learned` in `.claude/agents/<agent>.md` (append-only; never rewrite history).
3. **Propagation check** (SELF_IMPROVEMENT rule): does it generalize? If yes → also add to `04_RND_LAB/KNOWLEDGE_BASE.md §A`, copy to other relevant personas, and — if codeable — add a guard/detector to `04_RND_LAB/CODE_CHECKS.md` + `lib/guards.py`.
4. If it stemmed from a mistake that cost something: consider the AP ledger (−10 sloppy claim / −15 missed bug caught downstream) — fairness per TEAM_ROSTER scoring; log in EVOLUTION_LOG if a persona/process changed.
5. Cheap tier; no subagents. One journal line if the lesson changed firm process.
