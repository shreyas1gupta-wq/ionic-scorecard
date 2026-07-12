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
