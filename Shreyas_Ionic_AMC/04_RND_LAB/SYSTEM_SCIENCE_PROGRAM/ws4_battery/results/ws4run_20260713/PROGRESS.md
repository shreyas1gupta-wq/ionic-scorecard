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
