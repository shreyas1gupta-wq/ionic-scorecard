# WORK ORDER — DESK-100: complete the firm build
Filed 2026-07-03 by DESK-20. Protocol first: read root `CLAUDE.md`, `SESSION_JOURNAL.md`, `DECISIONS_LOG.md`.

## WHO YOU ARE — first-time briefing (the Principal has NOT told you this directly before)
- The Principal (Shreyas) runs this firm with **TWO Claude accounts on the same laptop, same folder**:
  - **DESK-20** — Claude desktop app ($20 plan): CIO office — R&D, ideas, analysis, light work. ≤2 parallel subagents.
  - **DESK-100** — Claude Code in VS Code ($100 plan): **that is YOU** — the execution floor: backtests, bulk data, batch/multi-agent workflows, EOD auto-runs. ≤6 parallel subagents (~3× DESK-20).
- You are teammates, not the same entity. **Neither desk can see the other's conversations.** The ONLY shared memory is this folder: root `CLAUDE.md` (constitution), `SESSION_JOURNAL.md` (what happened), `CURRENT_STATE.md` (what's true now), `DECISIONS_LOG.md` (Principal rulings D-001…D-020).
- Non-negotiable sync protocol: at session START read CURRENT_STATE + last 2 journal entries; at session END (and every milestone) append a journal entry + update CURRENT_STATE; checkpoint mid-task so the other desk or a token-limit restart can resume where you stopped.
- Trust the books over assumptions — and when the books conflict with the disk, audit the disk and correct the books (this very work order exists because a prior session's journal claimed work that wasn't on disk).
- Work done in your past VS Code sessions (FINAL_STRATEGY_FORWARD_CHECK, AngelDailyOptionCapture task) predates the firm — it's already reflected in the journal's pre-firm history; going forward, everything you do gets journaled under DESK-100.

## True state (verified on disk by DESK-20, 2026-07-03 late)
**BUILT:** root `CLAUDE.md`, `README.md`, `00_GOVERNANCE/` (5 files), `01_COMMAND_CENTER/` (3 files + this order), `02_PROMPT_LIBRARY/drafts/BUILD_ADDENDUM_v1.md`.
**NOT BUILT** (the "FIRM FOUNDED" journal entry overstated — treat it as spec, not fact): `.claude/agents/` (15 personas), `.claude/skills/`, git init, `03_RESEARCH_DESK`, `04_RND_LAB`, `05_DATA_OFFICE`, `06_TRADING_DESK`, `07_RISK_OFFICE`, `99_OPS` and all their files.

## Build list (execute in order; checkpoint + journal after EACH step per D-013)
1. **git init** at root. `.gitignore`: `datasets/`, `*.parquet`, large `*.xlsx`, any credentials, `__pycache__/`, `.claude/settings.local.json`. Local only, never push remote (D-003).
2. **`.claude/agents/`** — 15 personas exactly per the roster table in root CLAUDE.md. Each file: name + persona, role charter, memo format, model tier primary+backup (per `00_GOVERNANCE/MODEL_ASSIGNMENTS.md`), and bake in prompt clauses P-01…P-12 from `BUILD_ADDENDUM_v1.md §2`.
3. **Folders 03→07 + 99** per the CLAUDE.md firm map, with their named files:
   - 03: `IC_MEMO_TEMPLATE.md`, `memos/`
   - 04: `IDEA_PIPELINE.md` (stage gates, auto-advance except live gate D-010), `KILLED_IDEAS.md` (seed: ~14 intraday option-buying variants + resurrection condition; FF-calendar recent losing streak note; IV/RV bad-IV data bug), `KNOWLEDGE_BASE.md` (seed from ADDENDUM §4)
   - 05: `DATA_CATALOG.md` (full parquet inventory: path, schema, rows, date range, known bugs, update command — pull from RESUME_TOMORROW.md + HANDOFF.md), `DATA_QUALITY_RULES.md` (the 6 landmines + verification protocol D-009)
   - 06: `COST_STANDARDS.md` (formalize ADDENDUM §3, keep DRAFT banner until Principal approves), `STRATEGY_REGISTER.md` (seed: 4 forward strategies from FINAL_STRATEGY_FORWARD_CHECK + Track-1 deploy rule ≥0.45% straddle filter), `PAPER_LEDGER.md`
   - 07: `RISK_LIMITS.md` (draft), `ADVERSARIAL_REVIEWS.md` (wire in ADDENDUM §5 checklist)
   - 99: `EOD_ROUTINE.md` (own AngelDailyOptionCapture + 23 Angel stragglers retry), `BACKUP_POLICY.md`
4. **`.claude/skills/`** — thin, cheap wrappers: `/ic-memo`, `/red-team`, `/data-check`, `/idea-log`, `/eod`. Each points at firm files; no heavy logic in the skill itself.
5. **FACTOR_LIBRARY.md** in 04_RND_LAB from ADDENDUM §1 (Principal's mandate + data map) — this is the research menu.
6. **Research machinery** (from ADDENDUM v1.1 extensions):
   - `04_RND_LAB/RESEARCH_SOP.md` ← §7 (8-step loop + one-pager template), §10 (validation protocol), §12 (paper SOP + Definition-of-Done), §14 (cadence)
   - `04_RND_LAB/CODE_CHECKS.md` ← §9 verbatim; plus `04_RND_LAB/lib/guards.py` — the landmine guards as an importable module (assert helpers for tz/auction/PIT/merge/same-bar/option-gap)
   - `02_PROMPT_LIBRARY/drafts/RP-01.md … RP-10.md` ← §8, one file each (stay in drafts until Principal approves)
   - `03_RESEARCH_DESK/ANALYST_CHECKLISTS.md` ← §13 (forensic + Minervini template + call-NLP recipe)
7. Finish: append journal entry, update `CURRENT_STATE.md`, list anything skipped. Do NOT move any prompt to `approved/` (D-020 — Principal approves one by one).

Token guidance: mechanical scaffolding → cheap tier, ≤6 parallel, checkpoint each numbered step.
