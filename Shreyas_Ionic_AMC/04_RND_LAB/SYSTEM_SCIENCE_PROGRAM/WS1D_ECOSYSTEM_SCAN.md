# WS-1d — Agent / AI Ecosystem Scan (patterns-only)
**Program:** SYSTEM SCIENCE (MASTER_PLAN.md §WS-1d). **Owner:** R&D (Aditya Verma). **Date:** 2026-07-12. **Desk:** DESK-100.
**Mission:** scan the July-2026 agent/AI ecosystem for PATTERNS worth adopting into our file-based multi-agent firm. **Patterns only — NO installs, NO dependencies** (ruflo precedent: we transplant ideas, we don't take a runtime).
**Correctness bar:** a repo/pattern is only claimed to do X if verified in its own docs/README/site; every row carries a URL. `[INFERENCE]` marks my judgement layered on a `[DATA]` fact.

**Method / provenance:** 3 sonnet subagents (orchestration; memory+evals; finance+skills), each URL-cited. I then independently WebFetch-verified the load-bearing citations: Letta sleep-time, TradingAgents (arXiv), avoid-ai-writing, dream-skill, skill-eval-harness, skill-lint — all confirmed. The orchestration cluster I verified **entirely first-hand** (the assigned subagent mis-invoked the `deep-research` skill, spawned nested sub-agents, and stalled — process lesson logged below). "Verified absence" = I read the cited doc and did not find the feature; it is not proof the feature exists nowhere in the codebase.

---

## ADOPT / REJECT / WATCH — master table

### Cluster 1 — Orchestration frameworks (verified first-hand)
| Pattern | Framework + URL | What it gives us beyond files+git | Cost | Verdict + reason |
|---|---|---|---|---|
| Handoff as a first-class primitive — delegation is a tool `transfer_to_X` with input filters controlling what state passes | OpenAI Agents SDK — https://openai.github.io/openai-agents-python/handoffs/ | A *declared contract* for who may delegate to whom and exactly what context transfers, vs our free-form Agent-tool prompt | Low | WATCH — our Agent tool already delegates; borrow only the "handoff = filtered-state contract" discipline (state each subagent's context budget explicitly) |
| Durable execution / checkpointer — "persist through failures… automatically resuming from exactly where they left off"; human-in-the-loop "inspect and modify agent state at any point" | LangGraph — https://github.com/langchain-ai/langgraph | Step-level automatic resume + live mid-run interrupt, finer than our manual checkpoint-to-file | Med | WATCH — we resume via journal/CURRENT_STATE; per-step runtime resume needs infra we don't run |
| `@persist` state persistence across restarts (SQLite default) + **forking** a saved run to branch experiments | CrewAI Flows — https://docs.crewai.com/concepts/flows | Fork/branch a run's state | Med | WATCH — git branches already fork our file-state; nothing to build |
| Graph-workflow **checkpointing uniform across patterns** + human-in-the-loop approval + sequential/concurrent/**handoff**/group-chat + Magentic-One planner; declarative YAML/JSON agent defs | Microsoft Agent Framework (successor merging AutoGen+Semantic Kernel) — https://devblogs.microsoft.com/agent-framework/migrate-your-semantic-kernel-and-autogen-projects-to-microsoft-agent-framework-release-candidate/ | Declarative-persona idea (agent defined in structured front-matter), uniform pause/resume | Med | WATCH — validates our design; the declarative-persona-as-data idea is worth a look for our markdown personas |
| SOP-as-code role pipeline — "Code = SOP(Team)"; PM/architect/engineer/QA roles each run a defined SOP | MetaGPT — https://github.com/geekan/MetaGPT | Encoding each persona's stage-gate SOP *inline in the persona* as an enforced checklist | Low | ADOPT (partial) — we have RESEARCH_SOP; make "each persona carries its SOP checklist" universal (some already do) |
| Reflection/critic + group-chat multi-agent debate (AutoGen lineage, now in MS Agent Framework) | https://devblogs.microsoft.com/agent-framework/ (as above) | Structured critic loop | Low | WATCH — our red-team gate + IC debate already cover this |

### Cluster 2 — Memory systems
| Pattern | Project + URL | What it gives our MEMORY.md / Lessons | Cost | Verdict + reason |
|---|---|---|---|---|
| **Sleep-time agent** — background/async memory consolidation ("two agents under the hood: a primary and a sleep-time agent") | Letta — https://www.letta.com/blog/sleep-time-compute *(verified by me)* | A *scheduled* end-of-session consolidation pass, formalizing our informal compaction | Low | **ADOPT** — add an explicit end-of-session consolidation step to SESSION_PROTOCOL |
| MemFS + "doctor" defrag — git-backed markdown memory, periodic split/merge/restructure of bloated files | Letta — https://docs.letta.com/letta-agent/memory | Quarterly defrag of KNOWLEDGE_BASE + persona Lessons sections | Low | **ADOPT** — give Librarian a quarterly defrag pass |
| 3-tier core / archival / recall memory | Letta — https://www.letta.com/blog/memory-blocks/ | Validates our CURRENT_STATE (core) / KNOWLEDGE_BASE (archival) / git-log (recall) split | — | WATCH — no action, confirms design |
| **Bi-temporal fact edges** — valid-from/valid-until/learned-at/invalidated-at; superseded facts kept as history, not deleted | Zep/Graphiti — https://www.getzep.com/platform/graphiti/ | Stops silent overwrite of KB/KILLED_IDEAS; preserves the "believed X until date Y" trail | Med | **ADOPT** — add `valid_from`/`superseded_by` frontmatter instead of overwriting |
| Hybrid vector+BM25+graph retrieval, fused ranked list | Zep/Graphiti — https://www.getzep.com/platform/graphiti/ | Needs a vector DB | High | REJECT — infra dependency contradicts the markdown+git constraint |
| **ADD-only** extraction (never overwrite; keep both versions) + 4-signal relevance (semantic+keyword+entity+temporal; semantic dominates, recency tiebreaker) | mem0 — https://docs.mem0.ai/core-concepts/memory-evaluation | A rubric for how the Librarian ranks which old lesson to surface | Low | ADOPT (partial) — codify "semantic-match first, recency never overrides" as Librarian's retrieval rule |
| Session-end auto-extraction + 3-layer retrieval (index → timeline → full detail, fetch detail only on match) | claude-mem — https://github.com/thedotmack/claude-mem | Token-discipline upgrade: MEMORY.md as compact index, detail fetched only on hit | Low | ADOPT — restructure MEMORY.md index → per-topic files (partly done) |

### Cluster 3 — Eval / verification harnesses (feeds WS-4)
| Pattern | Project + URL | What it gives WS-4 evals | Cost | Verdict + reason |
|---|---|---|---|---|
| **Task = Dataset + Solver + Scorer**, strictly separated | inspect-ai (UK AISI) — https://inspect.aisi.org.uk/scorers.html | Clean WS-4 structure: 1 frozen dataset + N solvers (our-system / single-LLM / human) + 1 frozen scorer — prevents scorer drift between arms | Low | **ADOPT** — the WS-4 scaffolding |
| Multi-grader **majority vote** (`multi_scorer`, 3 judge models) | inspect-ai — https://inspect.aisi.org.uk/model-graded.html | Cheap robustness for rubric scoring — grade 3× / 2 judge models, majority-vote | Low | **ADOPT** |
| `battle` template — pairwise head-to-head, logs win-rate of A vs B | OpenAI evals — https://github.com/openai/evals/blob/main/docs/eval-templates.md | Exact mechanism for WS-4 paired-arm comparison (log win/lose/tie) | Low | ADOPT |
| `select-best` — N outputs shown together, judge names the winner (N-way arena) | promptfoo — https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/select-best/ | 3-way arena (our-system / single-LLM / human) in one grade | Low | ADOPT |
| `llm-rubric` — judge emits strict `{reason, score, pass}` JSON; deterministic checks run first (free), LLM judge only for the remainder | promptfoo — https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/llm-rubric/ | Grader output contract + token-saving triage rule | Low | **ADOPT** — WS-4 grader schema |
| Red-team **plugin taxonomy** — named vulnerability probes vs one free-form attack | promptfoo — https://www.promptfoo.dev/docs/red-team/ | Turn red-team into a named per-strategy checklist: lookahead / overfit / regime-luck / cost-underestimate as "plugins" | Med | WATCH (adopt-lite) — a checklist upgrade for Nikhil Bose |
| Registry — YAML eval-logic / JSONL data separation; copy-edit rubric templates | OpenAI evals — https://github.com/openai/evals/blob/main/docs/build-eval.md | — | Low | WATCH — already covered by our frozen-spec discipline |

### Cluster 4 — Finance-agent systems (architecture vs ours)
| Pattern | System + URL | What it gives us | Cost | Verdict + reason |
|---|---|---|---|---|
| N-round bull/bear debate + facilitator-judge structured verdict (analyst/researcher/trader/risk/fund-mgr roles; reports return/Sharpe/maxDD; **no** DSR/PBO, no pre-registration, no lookahead controls) | TradingAgents (arXiv) — https://arxiv.org/abs/2412.20138 *(verified by me)* | Sharper structure for our IC debate (formal round count + judge records a structured entry) | Low | WATCH — we already have IC+red-team; borrow only the "facilitator records structured entry" mechanic |
| Hard split: all numbers from deterministic Python, LLM only narrates; provenance on every valuation output | FinRobot — https://github.com/AI4Finance-Foundation/FinRobot | Formalizes our ad-hoc scripts-first rule into a named, audited provenance rule | Low | **ADOPT** — codify in TOKEN_POLICY / backtest skill |
| Layered memory with importance-weighted promotion of "significant" events | FinMem (arXiv) — https://arxiv.org/abs/2311.13743 | Auto-promote high-impact lessons vs routine notes | Med | WATCH — our KB/consolidation do this manually |
| Single "connect once, consume everywhere" data layer exposed via MCP (Python/Excel/agents) | OpenBB — https://github.com/OpenBB-finance/OpenBB | Unify fragmented Angel/NSE-bhavcopy/HF scripts behind one interface | High | WATCH — real value, real build cost, not urgent |
| LoRA-tuned lightweight finance-sentiment models + open datasets vs pure prompting | FinGPT — https://github.com/AI4Finance-Foundation/FinGPT | Cheaper/faster news-sweep sentiment | High | REJECT — training/serving infra not worth it at our scale; prompting is fine |

### Cluster 5 — Agent-skills ecosystem (we have 79)
| Pattern / Skill | Source + URL | What it gives us | Cost | Verdict + reason |
|---|---|---|---|---|
| Official Agent-Skills spec + `skill-creator` meta-skill (17 skills incl docx/pptx/xlsx/pdf/mcp-builder/skill-creator/webapp-testing/…) | anthropics/skills — https://github.com/anthropics/skills | Baseline to spec-check our 79 skills (frontmatter, length, token limits) | Low | **ADOPT** — run a compliance pass |
| SKILL.md compliance linter — frontmatter/name-format/length/token-limit checks, GitHub Action or CLI | skill-lint — https://github.com/himself65/skill-lint *(verified)* | Catches malformed skills before they silently underperform | Low | **ADOPT** |
| **De-AI-ification prose linter** — 53 pattern categories (em-dash overuse, sycophantic openers, significance inflation, copula-avoidance…), detect/rewrite/edit modes, 0–100 "AI-ness" score, zero-dep JS engine | avoid-ai-writing — https://github.com/conorbronsdon/avoid-ai-writing *(verified by me)* | The WS-2 `/style-lint` gap, filled — a quality gate for Principal-facing docx / IC memos / investor letters | Low | **ADOPT (top priority)** — matches our internally-flagged style-lint candidate |
| With/without-skill **causal A/B eval harness** — paired variants, deterministic local grading (no model in grade path), leakage detection, per-model lift | skill-eval-harness — https://github.com/adewale/skill-eval-harness *(verified)* | Proof our 79 skills actually lift outcomes vs no-skill baseline; feeds WS-3 (AlphaPoints efficacy) + WS-4 | Med | **ADOPT** — pilot on 3–4 high-use skills first |
| Auto 4-phase memory consolidation (Orient → Gather → Consolidate → Prune&Index) on a 24h Stop hook | dream-skill — https://github.com/grandamenium/dream-skill *(verified)* | Automates our SESSION_JOURNAL/CURRENT_STATE consolidation | Low | ADOPT (pattern) — the memory-consolidation candidate; extract the 4-phase flow, don't install (shell/Node) |

---

## What WE have that THEY don't (whitepaper-facing, WS-5 candidate claims)
Verified absence across the docs cited above (orchestration frameworks; Letta/Zep/mem0/claude-mem; inspect-ai/OpenAI-evals/promptfoo; TradingAgents/FinRobot/FinMem/FinGPT/OpenBB). Honest limit: absence in the doc ≠ absence in the code.

1. **Pre-registration freeze via git-hash before a test; mid-test tuning voids the result (D-030).** Orchestration frameworks checkpoint *state* but never freeze a *hypothesis + success-criteria* before running; the 7 eval/memory harnesses set rubrics/thresholds at config-time, not gated by prior sign-off; TradingAgents only *post-hoc* flags its own Sharpe as suspiciously high. No scanned system pins a pre-commit hash.
2. **Adversarial red-team-of-the-backtest gate** — an agent whose sole job is to *kill the result*, distinct from market-direction debate. TradingAgents' bull/bear debate argues *trade direction*, not backtest validity; no red-team-of-the-evidence role exists in any of the five finance systems.
3. **Placebo / control battery** — a deliberate null/random arm to catch a scorer or pipeline that rubber-stamps everything. No placebo/null-arm concept in any of the 7 harnesses or 5 finance systems.
4. **DSR / PBO multiple-testing correction with an honest trials-ledger.** None of the 5 finance systems mention DSR or PBO; the eval harnesses grade single tasks, not a family-wide overfitting deflation.
5. **Enumerated data-landmine + T1–T10 lookahead taxonomy with a mandatory audit-gate tool.** TradingAgents has one ad-hoc "no future data per day" rule; none have an enumerated taxonomy + a required audit script/gate.
6. **Anti-sycophancy incentive economy (AlphaPoints)** — honest kills paid more than gate-passes (60% of net rewards to integrity-class behavior). No incentive/scoring design found in any scanned system.
7. **Blind grading** — judge unaware which arm produced an output. Absent from inspect-ai model-graded + promptfoo rubric docs (their judge prompts include provider/model context).
8. **Cross-agent lesson-propagation audit** — verifying a lesson learned by one persona is written into every sibling persona that needs it. Letta/Zep/mem0/claude-mem consolidate a *single* agent's own memory; none audit propagation across distinct personas.
9. **Stage-gate idea pipeline with pre-registered KILL + documented RESURRECTION conditions.** None of the finance systems have an idea-governance lifecycle; they are trading/analysis engines, not research-governance OSes.
10. **Persistent, mandatory two-account file-sync as source of truth** (SESSION_JOURNAL + CURRENT_STATE). The scanned systems are frameworks/platforms, not governed operating firms with cross-session/cross-account continuity.

---

## TOP-5 PRIORITIZED ADOPTION LIST
1. **`/style-lint` skill from avoid-ai-writing's 53-category taxonomy.** Extract the pattern list + detect/rewrite/edit modes; hand-build our own checker (do NOT install the JS engine — ruflo precedent). Closes the WS-2 de-AI-ification gap; becomes a mandatory gate on every Principal-facing docx / IC memo / investor letter. Cost Low. Owner: Librarian + Product. URL: https://github.com/conorbronsdon/avoid-ai-writing
2. **WS-4 eval scaffolding = inspect-ai (Dataset+Solver+Scorer) + promptfoo (`llm-rubric` JSON contract, `select-best`/`battle` paired-&-arena grading) + multi-grader majority vote.** Adopt as the WS-4 design spec, not a dependency. Cost Low. Owner: Quant Head + CEO. URLs: https://inspect.aisi.org.uk/scorers.html , https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/llm-rubric/
3. **Session-end consolidation pass** (Letta sleep-time + dream-skill's 4-phase Orient→Gather→Consolidate→Prune) formalized into SESSION_PROTOCOL, plus a quarterly Librarian "defrag" (Letta doctor). Turns our informal compaction into a scheduled, measurable step — directly serves WS-1a (recall hit-rate). Cost Low. Owner: Librarian. URLs: https://www.letta.com/blog/sleep-time-compute , https://github.com/grandamenium/dream-skill
4. **Superseded-not-overwritten discipline** (Zep bi-temporal + mem0 ADD-only): add `valid_from` / `superseded_by` frontmatter to KILLED_IDEAS, KNOWLEDGE_BASE, FACTOR_LIBRARY entries — never overwrite a lesson, append and mark. Preserves the "believed X until Y" audit trail and strengthens trials-ledger honesty (our DSR depends on it). Cost Med. Owner: R&D + Librarian. URL: https://www.getzep.com/platform/graphiti/
5. **Skill hygiene pass**: run skill-lint spec-check across all 79 skills, then pilot skill-eval-harness on 3–4 high-use skills (backtest, red-team, sensitivity) to *prove* they lift outcomes — feeds WS-3 (does the incentive/skill machinery actually help?) and WS-4. Cost Low–Med. Owner: CEO + Quant Head. URLs: https://github.com/himself65/skill-lint , https://github.com/adewale/skill-eval-harness

---

## Process lesson (for future ecosystem scans)
The orchestration subagent mis-invoked the `deep-research` skill, which spawned its own nested sub-agents — burning budget, breaching the spirit of the 3-agent cap, and stalling as it "waited for its sub-agents." **Fix:** research subagents must be instructed to use WebSearch + WebFetch ONLY and explicitly forbidden from invoking agent-spawning skills (deep-research, subagent-driven-development, etc.). I recovered by verifying the entire orchestration cluster first-hand. `[OPINION]` this belongs in the WS-1d method notes and the token-wise/agent-dispatch guidance.
