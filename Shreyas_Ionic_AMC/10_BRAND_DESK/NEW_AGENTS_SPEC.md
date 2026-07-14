# NEW AGENTS & SKILLS — SPEC (deferred build)
*Created 2026-07-15. BUILD LATER — Shreyas builds these in a dedicated Fable-token session, AFTER this week's AMC post ships. Nothing in the Brand Desk is blocked on them; until built, run the pipeline by manually invoking existing agents per `BRAND_CHARTER.md` §11.*

**Build order when the session comes:** compliance skill first (it's the gate everything depends on) → post pipeline skill → track-record skill → orchestrator agent → optional scoring agent. Follow the firm's `/hire` skill for agents and the skill-authoring convention in `.claude/skills/`.

---

## 1. Agent: `brand-desk-lead` (orchestrator persona)
- **Role:** Head of Brand & Publishing. Owns the weekly pipeline, the buffer, the calendar, and the track-record ledger. Reports to CEO (ops) + defers to compliance on any §7 question.
- **Primary model:** analysis-tier (Sonnet-class) for orchestration; escalate to Opus only for the final synthesis of a flagship thesis.
- **Summon when:** running the weekly sweep, staging the buffer, or coordinating the other brand agents.
- **Persona notes:** obsessive about the charter's voice rule (§8) — its job is to make output sound like Shreyas, and to REJECT its own drafts that read AI-written. Presents OPTIONS, never a single take.
- **Roster/CLAUDE.md:** add a row to `00_GOVERNANCE/TEAM_ROSTER.md` + `MODEL_ASSIGNMENTS.md` + the CLAUDE.md team table; log in EVOLUTION_LOG.

## 2. Skill: `/brand-compliance-check`
- **Distinct from the firm's internal `compliance-audit`** — this one is tuned to PUBLIC-post optics + AIF/employer/SEBI exposure, not internal firm governance.
- **Input:** a draft post. **Output:** PASS / FLAG / REJECT + specific reasons, mapped to charter §7 items.
- **Checks:** stock-call detection; employer/client/AUM/strategy leakage; P&L/credential/PII leakage; "would an Ionic colleague be uncomfortable" test; disclaimer presence + freshness (not repeated boilerplate); RA/IA recommendation-language scan.
- **Default:** uncertain → REJECT (charter's caution-first rule). Runs BEFORE Shreyas's own final read, never replaces it.

## 3. Skill: `/brand-post`
- **The weekly pipeline as one command.** Orchestrates charter §11 steps 1-8: sweep → 2-3 draft options → `/brand-compliance-check` each → red-team pass → package (visuals/PDF + `/style-lint`) → fill the scoring rubric → pre-register falsifiable claims → present options to Shreyas.
- **Terminal output: final TEXT only** for Shreyas to post manually. NEVER posts anything itself. NEVER touches LinkedIn/Substack credentials or APIs.

## 4. Skill: `/track-record-review`
- **Quarterly.** Reads `PUBLIC_TRACK_RECORD.md`, finds entries that have matured, scores each (HIT/MISS/PARTIAL/VOID) with evidence, updates the ledger, and drafts the public P7 check-in post (hits AND misses).

## 5. (Optional) Agent/skill: draft scorer
- Automates charter §12 rubric scoring so the options arrive pre-scored. Low priority — the manual rubric works fine until volume justifies it.

---

## Guardrails that MUST survive into the built versions
- Human-post-only: no tool ever posts to LinkedIn/Substack. Shreyas posts manually, always (charter §10, §11 step 9).
- Two-stage gate: agent compliance pass → Shreyas's own final read. Never collapse to one.
- Voice rule is a HARD gate: AI-sounding draft = failed draft (charter §8).
- Every falsifiable claim pre-registered + committed before posting (charter §6).
