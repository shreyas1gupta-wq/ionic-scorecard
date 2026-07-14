# Token Policy — spend tokens like risk capital
Principle: tokens are the firm's fuel. Every burn must buy decision-value. Being token-smart is a rated KPI (AP penalties for waste).

## Account budgets
| | DESK-20 (desktop, $20) | DESK-100 (VS Code, $100) |
|---|---|---|
| Role | CIO office: ideas, memos, reviews, direction | Execution floor: backtests, bulk data, batch runs |
| Max parallel subagents | **2** | **6** |
| Bulk scrapes / bulk downloads | NO — hand off to DESK-100 | YES |
| Full-portfolio backtests | NO (design only) | YES |
| Multi-agent IC sessions | Small IC (2–3 agents) | Full IC (5) when needed |
| EOD auto-routines | — | Owns `AngelDailyOptionCapture` + EOD_ROUTINE |

## Model tiering (cheapest tier that does the job)
- **haiku** — mechanical: data checks, formatting, file inventory, simple extraction.
- **sonnet** — analysis: sector memos, technical reads, feature engineering, standard research and coding/backtesting.
- **opus/top** — judgment: CIO/FM decisions, Red Team audits, backtest-validity review, research synthesis, anything that will drive capital allocation.
Never summon the full IC for a question one analyst can answer. FM/CIO decide who convenes.

## Checkpoint & resume protocol (token-limit safety)
1. Any task >15 min of work: write progress to a checkpoint file (scratch or the relevant firm doc) at each major step.
2. Before a foreseeable limit: update `01_COMMAND_CENTER/CURRENT_STATE.md` with exact resume instructions ("done X, next Y, files at Z").
3. Resume rule: new session reads CURRENT_STATE first — never redo finished work, never re-derive facts already journaled.

## Anti-waste rules
- Don't re-read large files already summarized in the journal/catalog — trust the firm docs.
- Batch independent tool calls; prefer one pass over a file tree to many small passes.
- Background long-running jobs; don't poll in tight loops.
- Reuse `02_PROMPT_LIBRARY/approved/` prompts instead of re-crafting.
- Big exploratory sweeps (50-agent workflows etc.) only on DESK-100 and only with a written objective + budget in the journal.


## D-023 amendment (2026-07-04, after spend-limit hit)
- **MAX 3 parallel agents firm-wide.** Sequence waves; prefer 2 heavy + 1 light.
- Every agent prompt must instruct checkpointing partial outputs to disk (results/, drafts) BEFORE final synthesis — a limit-hit must never lose completed computation.
- Spend-limit behavior observed: main loop survives; subagent spawns fail with ~0 tokens. On hit: stop spawning, salvage in-flight outputs, journal + commit, hand off to next session.

## STRICT ENFORCEMENT + TOKEN-SAVING HACKS (Principal order, 2026-07-04)
**MAX 3 PARALLEL AGENTS — STRICTLY APPLIED EVERY TIME (D-023).** No exceptions, no "just this once". Workflow-harness runs that internally exceed 3 are prohibited; use ≤3 scout waves instead unless told.
Hacks (all agents, all desks):
1. **/to-md before reading binaries** — docx/xlsx/pdf/parquet → lean .md digest (35x+ savings measured). Reading binaries directly = token-waste event (−5 AP).
2. **Grep before Read** — locate the section, then Read with offset/limit; never read whole large files for one fact.
3. **Digest-once, reference-many** — long sources get a one-time .md summary filed next to them; later work reads the digest.
4. **Background scripts over agents** — a .py run in background costs ~0 tokens; agents are for judgment, not computation.
5. **Main-loop for small tasks** — spawning an agent for <10-minute work wastes its boot context.
6. **Cheap tier first** (P-07); escalate only for judgment.
7. **Checkpoint files, not context relay** — hand structured files between steps (telephone-game lesson), never long verbal recaps.
8. **No transcript re-reads** — task outputs are salvaged once into WORK_LOG/artifacts; never re-read raw agent transcripts.
9. **Compact prompts** — agent briefs carry file PATHS + precise asks, never pasted file contents the agent can read itself.