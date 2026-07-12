# SYSTEM SCIENCE PROGRAM — the firm studies itself
**Chartered 2026-07-13 by Principal order:** *"I want to create the whole system and have scientific backings and proofs and checks and comparison on various fronts for our system vs humans vs single LLM vs other systems and do tests on finance IQ / finance tests and more."*
Owner: CEO (program) + Quant Head (experiment validity) + Librarian (literature). Same laws as market research: pre-registered cards, frozen bars, placebo/control arms, no post-hoc bar-shopping. Spend-limit aware: agent-heavy waves run only when the org budget allows; everything below is resumable from this file.

## WS-1 — Agent / skill / memory upgrades (engineering)
Goal: close the gaps the Blueprint's Section 6 found and adopt best-in-class agent patterns.
- 1a. Memory: evaluate persistent-memory patterns (session-summary compaction discipline, MEMORY.md index hygiene, per-agent append-only Lessons files → are they actually recalled? measure recall hit-rate on 20 seeded facts). claude-mem remains blocked on Node.js (Principal unlock).
- 1b. Skills: dedupe the ~10-skill design cluster; flesh out thin critical stubs (lookahead-audit); add a /style-lint skill (see WS-3). Weekly find-skills cadence already live.
- 1c. Self-improvement loop instrumentation: the retro→leaderboard→board loop exists; add measurable outputs (lessons written/month, lesson-recall rate, repeat-mistake rate — the firm already logs mistakes; count recurrences).
- 1d. GitHub/AI ecosystem scan (agent-heavy, QUEUED for budget): agent-orchestration repos (AutoGen/CrewAI/LangGraph/MetaGPT — patterns only, no installs per ruflo precedent), memory systems (Letta/MemGPT-class), eval harnesses (inspect-ai), finance-agent repos (TradingAgents, FinRobot, FinMem). Deliverable: adopt/reject table with the vibe-trading-style extraction discipline.

## WS-2 — De-AI-ification style system (design)
Goal: outputs (docx/pptx/pdf/html/prose) that read as high-IQ human-made originals, not LLM-generated.
- 2a. Codify a FIRM STYLE GUIDE: typography (serif body/geometric heads, real margins, consistent grid), chart language (one palette, no default-matplotlib look, direct labeling over legends), document furniture (title pages, numbered exhibits, footnoted sources), prose rules (varied sentence rhythm; ban stock LLM tells — "delve", "landscape", "It's important to note", em-dash chains, bullet-overuse; numbers carry units and dates; claims carry file-path citations).
- 2b. Build templates: docx reference template (styles embedded), pptx master, html/css report shell — wired into the existing 09_PRODUCT builder scripts.
- 2c. /style-lint skill: mechanical checker for the banned-tells list + citation presence before any Principal deliverable ships.
- Scientific check: blind A/B — show the Principal (and optionally colleagues) paired documents (old vs new style), guess-which-is-AI test; bar = new style beats old on "human-made" ratings in ≥70% of pairs.

## WS-3 — AlphaPoints efficacy study (does the points system actually help?)
Hypothesis to test honestly: incentive framing changes agent output quality; risk: pure theater + Goodhart effects.
- 3a. Observational pass (cheap, script-first): the 48-entry AP ledger — what behaviors got rewarded? Already known: biggest awards went to honest kills/self-corrections, and the incentive design (bug-catch +15 > gate-pass +10, only honesty failures negative) is deliberately anti-Goodhart. Quantify: did bug-catch frequency rise after AP introduction? (Before/after 2026-07-03.)
- 3b. Pre-registered ablation (the real test, agent-budget QUEUED): 20 matched review tasks (10 with AP framing in the persona prompt, 10 with it stripped), same model/effort, blind-graded by a rubric (defects found, false positives, verdict honesty). BAR: AP arm must beat stripped arm on defects-found at p<0.1 (paired) or the points system is declared THEATER and retired to flavor-text.
- 3c. Literature grounding (Librarian): incentive/persona framing effects in LLM agents; Goodhart taxonomies; cite or admit absence.

## WS-4 — Benchmarking: OUR SYSTEM vs single-LLM vs humans vs other systems
The centerpiece. Pre-registered protocol before any run; all arms get identical budgets and blind grading.
- Arms: (A) single Claude call, no tools; (B) single Claude + tools (search/python); (C) THE FIRM (agents, gates, red-team) at matched total token budget; (D) literature human baselines (CFA pass rates, analyst-forecast accuracy studies); (E) published agent-system scores where comparable (FinBen/FLARE leaderboards, TradingAgents paper numbers).
- Test batteries: (i) public finance QA — FinQA / ConvFinQA / TAT-QA samples + FinBen task subset; (ii) CFA-style mock exams (public sample sets, all 3 levels where free); (iii) OUR OWN adversarial battery (novel, the differentiator): 20 backtest-design traps built from the firm's 9 landmines + T1-T10 taxonomy — "find the lookahead in this engine" tasks with known ground truth; (iv) forecasting calibration (probabilistic questions with resolution dates, Brier-scored).
- BARS (pre-registered): claim "the system adds value over a single LLM" ONLY if arm C beats arm A AND B on (iii) our-battery defects-found by ≥20% relative, and is non-inferior elsewhere at matched budget. Battery (iii) is where the machinery should shine; if C ≤ B there, the multi-agent overhead is not paying and we say so.
- Output: SYSTEM_SCIENCE results pack + eventually a whitepaper (WS-5).

## WS-5 — Architecture documentation & positioning (whitepaper)
Compare our file-based multi-agent OS against published systems (TradingAgents, FinRobot, AutoGen-style orchestration): what is genuinely novel here — provable pre-registration via freeze commits, adversarial certification gates, kill-credibility economics (AlphaPoints), two-desk file-sync resumability, landmine-driven placebo evolution. Draft after WS-4 data exists so claims carry measurements, not adjectives.

## Sequencing & budget honesty
- NOW (script-first, no agents): WS-3a observational AP analysis; WS-2a style-guide draft; WS-1c metrics wiring.
- NEXT BUDGET WINDOW: WS-4 battery construction (our landmine traps — one-time asset), then the pre-registered benchmark run; WS-1d ecosystem scan (3 agents max, D-023).
- PRINCIPAL UNLOCKS that help: Node.js (claude-mem), Kaggle/Tiingo keys (unrelated but pending), colleague raters for WS-2's blind A/B.
- Every WS deliverable gets a card in this file with frozen bars before its run. Trials ledger applies.

## WS-3a OUTCOME (2026-07-13, observational — banked)
45 ledger events, net +534 AP. **Revealed incentive structure: 60% of net AP rewards INTEGRITY-class behavior (bug/leak catches 31% + honest kills 26% + red-team 3%) vs only 12% for PROGRESS-class (gate passes, paper).** Zero negative events. Top earner = Quant Head (+124), second = Red Team (+75) — the economy pays skeptics best, which is the designed anti-Goodhart property working on paper. **FINDING 2 (operational): the ledger is STALE — last entry 2026-07-05, despite the highest-activity week in firm history (trials 229->255, 13 verdicts on 07-13 alone). As currently maintained the points system cannot be influencing anything because nobody is scoring it.** Implication for the Principal's question: before the WS-3b causal ablation is even worth running, either (a) automate ledger updates from journal/RUN_CARD events (script), or (b) accept AP as retrospective flavor. HONEST LIMIT: no counterfactual; constitution-vs-points confound stands until WS-3b.
