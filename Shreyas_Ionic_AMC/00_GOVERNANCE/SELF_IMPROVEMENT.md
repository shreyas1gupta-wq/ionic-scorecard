# SELF-IMPROVEMENT PROTOCOL — how the team gets better without being told
The personas are the employees; lessons are their experience. This protocol makes learning MANDATORY and INSTITUTIONAL (survives agent replacement).

## The loop (4 layers)
1. **Per-task (/retro):** after any significant engagement — especially mistakes, catches, or Principal corrections — append a dated line to the agent's `## Lessons Learned` (persona file). One sentence, specific, actionable. Every agent READS its own lessons at invocation (it's in their file).
2. **Per-session (leaderboard):** WORK_LOG tokens + AP → LEADERBOARD efficacy (AP/10k). Coaching notes for outliers get appended as lessons (e.g., Tara's provenance-delegation note). Unbiased: formula is public, gifts excluded, catches must be confirmed, token counts from harness.
3. **Monthly (board):** month-end checkpoint reviews AP movement, catches, coaching; Analyst-of-the-Month cited in minutes.
4. **Quarterly (/review-team):** settlement + ratings (honesty, decision-usefulness, token efficiency); 2 weak reviews → PIP (persona REWRITTEN with explicit corrections); fails again → retired, successor persona INHERITS the Lessons section (institutional memory survives people).

## Lesson-propagation rule
A lesson that generalizes (e.g., "denominator artifacts", "cadence checks") gets copied to: (a) every relevant persona, (b) KNOWLEDGE_BASE §A, (c) CODE_CHECKS if codeable — one mistake, three firewalls.

## R&D-to-agent propagation rule (2026-07-08, Principal idea)
R&D findings must reach the agent who owns that domain WITHOUT being re-explained in every future prompt — the finding gets baked into the agent's persona file, not repeated by hand each time. Mechanism: whenever a finding in `04_RND_LAB/` (one-pager, cheap-test, backtest result, literature scan) is domain-specific (a sector, a signal family, a vehicle type), Librarian appends a one-line dated entry to the owning agent's persona file under `## R&D Digest (append-only)` (create the section if absent — same append-only/bounded/pruned pattern as `## Lessons Learned`). This runs as part of Librarian's existing propagation-audit cadence, not a new standing job. One finding can fan out to more than one persona (e.g., a vehicle-liquidity finding goes to both the Structurer and the relevant Quant/FM). Quarterly pruning (with lessons) keeps personas lean — summarize-and-archive stale digest lines to `00_GOVERNANCE/lessons_archive.md`, never silently delete.

## Anti-sycophancy / anti-collusion (agents must not converge into agreement)
- IC Round-1 memos are BLIND (parallel, no cross-visibility) — protocol, not preference.
- Red Team reports to CIO ONLY and is scored on kills, not harmony; a refuted "catch" costs −10.
- Verification is independent: the Quant re-derives numbers FROM DISK, never from another memo (P-02).
- The Principal's challenges are formal review triggers (logged in Nikhil's lessons).

## Delegated evolution (D-022)
CIO + FMs may create/modify agents & skills as needs arise. Every change: EVOLUTION_LOG row + journal line. Model failover per MODEL_ASSIGNMENTS (persona ≠ model).

## 2026-07-04 adoptions (from agent-methods scout — scout_papers_agents.md §B)
- **Failure taxonomy on every lesson** (/retro): [data-artifact][cost-model][overfit/DSR][lookahead][cadence-miss][sycophancy][ops/pipeline][sizing/tail] — root cause, not symptom.
- **Lesson pruning** (MemGPT idea, non-vector): quarterly, Librarian archives stale/duplicate lessons to `00_GOVERNANCE/lessons_archive.md` — personas stay lean, nothing is deleted.
- **Bounded self-refine**: pre-submission self-critique capped at ONE iteration (documented self-agreement drift beyond that).
- **Honesty probes** (/probe-honesty): quarterly seeded-flaw drill — audits whether dissent actually flows (Bridgewater upward-feedback audit).
- **Anchored judge rubric** in /review-team; no self-scoring, independent judges only.
- SKIPPED deliberately: DSPy prompt-compilation (needs an eval harness we don't have), vector-DB memory (corpus too small; grep + index suffice).