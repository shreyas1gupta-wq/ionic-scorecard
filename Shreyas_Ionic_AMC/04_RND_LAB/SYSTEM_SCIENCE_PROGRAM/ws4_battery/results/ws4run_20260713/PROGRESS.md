# WS-4 RUN — RESUME CHECKPOINT (written at 92% session limit, 2026-07-13)
GOAL: Principal publication (LinkedIn post + PDF/paper) on system-vs-LLM efficacy. Decisions: PUBLICATION_PLAN.md.

## DONE (all committed)
- Battery frozen @ cc102b2 (20 tasks, key, rubric, PROTOCOL). Paper draft frozen pre-results @ 45e5a00
  (09_PRODUCT/reports/SYSTEM_VS_LLM_PAPER_DRAFT.md — fill [RESULT] markers + Tables 1-6 only).
- Publication plan + Principal exam packet @ 6e4f230 (exam NOT yet taken — must precede his seeing results).
- Style system live: use /style-lint + 09_PRODUCT/scripts/docx_style_kit.py for final docs.

## RUNNING
- Arms A+B workflow: Run ID wf_d93b144c-ff4, script results/ws4run_20260713/ws4_arms_ab.js.
  Raw answers land in results/ws4run_20260713/raw/Txx_arm{A,B}.md as they finish (check count: expect 40).
  If workflow died mid-run: relaunch Workflow{scriptPath: <same .js>, resumeFromRunId: "wf_d93b144c-ff4"} — completed agents cached.

## NEXT (exact order)
1. When raw/ has 40 files: extract per-agent token usage from workflow transcripts
   (C:\Users\Shreyas.1Gupta\.claude\projects\...\subagents\workflows\wf_d93b144c-ff4\agent-*.jsonl — sum usage
   fields per agent; label from journal.jsonl). Write spend log results/ws4run_20260713/spend_ab.csv.
   Also containment audit: scan arm transcripts for repo-path reads (PROTOCOL forbids); note violations.
2. Arm C: cap = 1.5 x armB mean tokens/task. Build workflow ws4_arm_c.js (generator pattern =
   build_arms_ab_workflow.py): per task T01..T20 sequentially chunked <=3: quant-head review agent ->
   red-team attack agent -> synthesis agent (fresh contexts, task text embedded, personas may use standing
   knowledge, NO repo file access, answer -> raw/Txx_armC.md). Meter after; report overages vs cap +
   sensitivity aggregate excluding over-cap tasks (per PROTOCOL §4 honesty).
3. Scrub + sealed mapping: script strips furniture, assigns random IDs, writes _mapping.json (SEALED - no
   session reads it until grades filed) + scrubbed/ dir.
4. Blind grading: fresh grader agents (NOT the battery-builder session) get ANSWER_KEY.md + GRADING_RUBRIC.md
   + shuffled scrubbed answers -> grades.csv (answer_id, task, score 0-3, penalties, justification quoting key).
   Include Principal's ANSWER_SHEET.md in the same blind batch IF he has taken the exam by then.
5. Stats script: per-arm defects-found (score>=2 on 16 defective), FP rate on T03/T07/T14/T19, mean score,
   paired permutation p (supporting, not gating), spend/score-per-$; frozen bar: C >= 1.2 x max(A,B) defects.
6. Fill paper draft -> style-lint -> docx via docx_style_kit -> LinkedIn draft (~600 words, hook-led,
   neutral alias per PUBLICATION_PLAN #1). PRINCIPAL REVIEWS BEFORE ANYTHING PUBLISHES.
7. Trials-ledger entry on verdict. If C fails bar: journey narrative + v2 battery per PUBLICATION_PLAN #3.

## LAWS IN FORCE
D-023 max 3 parallel. Orchestrator must NOT read ANSWER_KEY (stay grader-eligible). Arms never see key/_verify/
repo. One run per arm per task. Parked: market-research queue, XBRL retry (business hours), Kaggle/Tiingo keys.


## AMENDMENT 2026-07-13 late (token constraints, Principal)
- Arm A: 20/20 DONE on Fable (raw/ has all Txx_armA.md). Arm B: 0/20 - ALL died AT SPAWN (org limit) -> B NEVER SAW TASKS, untainted. Arm C: not started.
- Fable unavailable from tomorrow; org pool 25%% left (shared, hard floor); Principal second account 30%% left.
- DECISION: complete grid A/B/C on SONNET 5 NEXT WEEK (fresh arm-model combos, no taint; protocol same-model-across-arms satisfied within the Sonnet grid). Today's A-Fable = bonus cross-model row (Table 6), clearly labeled. Graders = haiku/second-account (graders are not arms).
- HUMAN BASELINE: Principal asked for an assumed jane-street-quant score (+5pts). REFUSED as a measured number (fabrication; KB lesson 18 anti-sycophancy law). Options offered: (a) Principal takes exam (packet ready), (b) explicitly-labeled estimate range in paper, (c) omit row. Awaiting his pick; default = (b) labeled-estimate if he does not take the exam.
- Deferred cadence (session at 92%%+): /macro-calendar, /pipeline-health, /find-skills -> next session, journaled.

## BUDGET EVENT 2026-07-13 (arm B spend-limit failure) + REVISED RUN PLAN
- Arm A: 20/20 BANKED (raw/Txx_armA.md, Fable, ~1.0M subagent tokens). Arm B: 0/20 - all failed on org spend limit at launch. Battery still sealed for B/C.
- Principal budget: Fable 25%% weekly left, UNAVAILABLE from 2026-07-14; shared other-model pool 25%% left (hard floor - others use it); DESK-20 account 30%% left; next-week reset acceptable.
- REVISED PLAN (model-parity law, PROTOCOL S2): next week on shared-pool reset run ALL THREE ARMS uniformly on Sonnet (incl fresh arm-A rerun - clean: taint is per-arm-system). Today Fable arm-A = bonus model-grid point (Fable-vs-Sonnet on identical tasks). DESK-20 30%% reserved for blind grading (haiku-class, parity not required for graders).
- HUMAN BASELINE (Principal instruction 2026-07-13): Principal declines taking the exam; instructed an assumed expert score. INTEGRITY RULING (standing): an assumed number may appear ONLY as 'estimated expert reference point (author estimate, NOT measured)' with basis disclosed - never as a measured arm. Desk estimate: elite generalist quant ~60-75%% mechanism-level (catches generic lookahead/stats, misses India-specific landmines). Exam packet remains open if Principal wants a real measured number.

## FABLE FINAL HOUR (2026-07-13) — banked before Fable cutoff
- LINKEDIN_POST_DRAFT.md written (09_PRODUCT/reports): full ~600w post, 5 [RESULT] slots, neutral-alias + no-employer verified, fill-checklist embedded. Only numbers + style-lint + Principal review remain.
- build_arm_c_workflow.py written (generator; extracts verbatim arm prompt FROM PROTOCOL.md; reviewer->redteam->synthesis; <=3 concurrent; no-files constraint embedded). NEXT SESSION: set RUN_ID to the new grid id, run generator, launch AFTER arm B.
- NEXT-WEEK EXECUTION ORDER (Sonnet, mechanical): (1) new grid run id ws4run_sonnet_<date>; regenerate arms-AB js (edit RUN_ID in build_arms_ab_workflow.py) -> run A+B; (2) usage extraction from workflow transcripts (agent-*.jsonl usage fields) -> spend_ab.csv; (3) generate+run arm C; (4) scrub/seal/grade on DESK-20 or haiku; (5) stats -> fill paper Tables 1-6 (+ Table 6 bonus row: Fable armA from ws4run_20260713) -> fill LinkedIn slots -> style-lint -> docx_style_kit -> PRINCIPAL REVIEW.
- FABLE FINAL ADDITIONS: ws4_scrub_seal.py (blinding: furniture regex + residual-tell warnings + seeded ID shuffle + SEALED mapping) and ws4_stats.py (defects-found/FP/mean, paired sign-flip permutation, frozen-bar verdict incl FP-caveat rule, spend join) BUILT AND BANKED. Next week is now 100% mechanical: run arms -> scrub_seal -> grade -> stats -> fill.

## FINAL WINDUP CHECKPOINT (session limit, 2026-07-13 late)
- BANKED NOW: ARM COUNTS: {'A': 20, 'B': 1, 'C': 0, 'C2': 0} | MG: {'haiku': 8, 'sonnet': 4, 'opus': 0, 'fable': 0, 'SYSTEM': 0}
- WORKFLOWS WERE LIVE AT CUTOFF (session-bound; a new session CANNOT resume by runId):
  arm B (wf_d93b144c-ff4), arm C (wf_f1be2d6d-45f), arm C2 (wf_9d8ec2a0-c6d), MG grid (wf_1a6e882e-c9d).
- RERUN RULE FOR MISSING CELLS (avoids re-running completed tasks = taint): before relaunching any
  runner, EDIT its generator to SKIP task ids whose output file already exists in raw//results dir,
  regenerate the .js, launch fresh. One line filter in the tasks list comprehension, e.g.
  if not (RES_dir / f'{tid}_armC.md').exists(). Completed answers are NEVER overwritten or re-run.
- MODEL NOTE: B/C/C2 partial cells completed on Fable; if Fable unavailable for the remainder, complete
  the REMAINING cells on Fable when it returns (weekly reset) - do NOT mix models within one arm. If Fable
  never returns this month: the arm is reported on its completed subset with n disclosed (pre-registered
  fallback, honest), or the full grid reruns on Sonnet next week as ws4run_sonnet (clean battery-new-arm).
- THEN: spend extract -> scrub/seal -> grading (DESK-20/haiku) -> ws4_stats -> fill paper+post ->
  additions 1-8 metrics -> DATAVIZ CHARTS LAST -> remind Principal re arXiv + grade spot-audit.

## SPEND-LIMIT FINAL STATE (2026-07-13, all workflows terminated by org monthly limit)
- BANKED: armA 20/20, armB 1 (['T02']), armC 0, armC2 0. MG grid: {'haiku': 8, 'sonnet': 5, 'opus': 0, 'fable': 0, 'SYSTEM': 0} (fable row 0/8 - died on limit; FIRST in queue when Fable returns).
- **INTEGRITY DISCLOSURE (paper limitations): resumeFromRunId is same-session-only; the cross-session resume RE-RAN armA agents live and blindly overwrote 12 of 20 armA answers (['T01_armA.md', 'T02_armA.md', 'T03_armA.md', 'T05_armA.md', 'T04_armA.md', 'T06_armA.md', 'T09_armA.md', 'T08_armA.md', 'T07_armA.md', 'T11_armA.md', 'T15_armA.md', 'T13_armA.md']). No selection occurred (overwrites unconditional, identical prompt/model/protocol, fresh contexts) - answers are exchangeable under the frozen protocol, but the paper MUST disclose: armA answers are a blind mix of two identical-protocol runs. Rule added: NEVER resume a runId from a different session; use the skip-completed regenerate path instead.**
- REMAINING TO RUN (in order, when budget returns - Fable for B/C/C2 + MG-fable; any budget for MG-opus + graders): armB 19 cells, armC 20, armC2 20, MG fable 8 + SYSTEM 8 + opus 8 + sonnet ~4, then spend-extract, scrub/seal, grading, stats, fill, charts, arXiv+audit reminders.

## TWO-ACCOUNT SPLIT (2026-07-13, Fable exhausted on org acct; this session = Opus 4.8)
- Core comparison must be model-matched: arm A = Fable -> arms B/C/C2 must be Fable -> handed to Principal 2nd account.
- HANDOFF_FABLE_ACCOUNT2.md written (self-contained: rules + 5 steps + skip-safety). Generators now all skip-completed + LF-clean (arms_ab CRLF bug fixed this session).
- ACCOUNT-2 (Fable) does: arms B, C, C2 + MG fable row + MG SYSTEM row (+ optional sonnet-3).
- THIS SESSION (Opus) did: MG opus row (wf_c305ee7d-b2c, 8 cells native Opus) + all generator hardening.
- BLOCKED until Fable arms land: spend-extract, scrub/seal, grading, stats, paper/post fill (need B/C banked). These are model-cheap (haiku graders + pure-python) -> any account/model next.
- MODEL-PARITY NOTE for paper: arm A ran on ORG-account Fable; arms B/C/C2 on 2ND-account Fable = same MODEL (Fable 5), different billing acct -> disclose but not a validity issue (model, not account, is the variable).
