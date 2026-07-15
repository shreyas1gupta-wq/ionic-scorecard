# HANDOFF — finish the "Firm S" system-vs-LLM benchmark (for the $20 Claude Code account with folder access)
**Paste this as your prompt, or open it and follow it. You have the shared NIFTY 500 folder, so every script is already on disk.**

## What this is (30 sec)
We benchmarked whether a multi-agent research firm beats a single LLM at catching defects in quant-research. The cross-model comparison (Fable/Opus/Sonnet/Haiku) is DONE. What's left is the **system arms** (the multi-agent firm) on an **Opus** base, then grading + write-up. The org account's monthly limit is exhausted — that's why this is on your account.

## Environment
- Python: `C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe` (bare `python` is broken). Prefix `PYTHONIOENCODING=utf-8`.
- `SSP` = `Shreyas_Ionic_AMC/04_RND_LAB/SYSTEM_SCIENCE_PROGRAM`. PowerShell 5.1: no `&&`, one command per line.
- To run a workflow `.js`: use the **Workflow** tool with `scriptPath: "<the .js path a generator prints>"`. Never pass `resumeFromRunId` from another session — every generator auto-skips already-done cells.

## THREE RULES (protect the result)
1. **Do NOT open** `SSP/ws4_battery/ANSWER_KEY.md`, `GRADING_RUBRIC.md`, or any `T*/_verify.py` (stay grader-eligible).
2. **Model parity:** the arms already run (A/B/C/C2) are on **Opus**. If you complete arm C/C2, your session **must be on Opus**. If you can't select Opus, SKIP step 1 and just do steps 2-4 on the arms already collected (n disclosed) — do NOT finish them on a different model.
3. **Grading judge = Haiku (already hard-coded).** We MEASURED Opus self-preference, so Opus must not judge Opus-authored arms. Don't change the judge.

## CURRENT STATE (already banked)
Opus arms in `SSP/ws4_battery/results/ws4run_opus_20260713/raw/`: **A 20/20, B 20/20, C 18/20, C2 12/20.** MG-SYSTEM grid 8/8. Cross-model results all committed.

## STEPS (in order; grade-first so you get the headline even if budget is tight)

**Step 1 — (Opus session, budget permitting) finish arm C & C2 to 20/20:**
```
PYTHONIOENCODING=utf-8 "PY" "SSP/ws4_battery/build_arm_c_workflow.py" ws4run_opus_20260713 C
```
Workflow the printed `ws4_arm_c.js` (it runs only the ~2 missing cells). Then repeat with `C2` and Workflow `ws4_arm_c2.js` (~8 cells). If budget dies mid-way, that's fine — partial is fine, re-run the same generator later (it skips done). *(PY = the python path above.)*

**Step 2 — grade the opus arms (Haiku judge, cheap):**
```
PYTHONIOENCODING=utf-8 "PY" "SSP/build_opus_arms_grade.py"
```
Workflow the printed `SSP/ws4_battery/results/opus_arms_grade/grade.js`. When it finishes, note the workflow's **transcript dir** (printed on launch, ends in `.../subagents/workflows/wf_XXXX/`). Then:
```
PYTHONIOENCODING=utf-8 "PY" "SSP/opus_arms_stats.py" "<that wf dir>/journal.jsonl"
```
This prints the **headline**: A vs B vs C defects-found, the frozen bar (C ≥ 1.2×max(A,B) → does the system beat a single LLM?), and C-vs-C2 (do personas help). Writes `OPUS_ARMS_RESULT.txt`. **Publish whichever way it falls — a negative result is fine and honest.**

**Step 3 — cost/token metering:**
```
PYTHONIOENCODING=utf-8 "PY" "SSP/ws4_spend_extract.py" ws4run_opus_20260713 "<arm-C wf dir>" "<arm-B wf dir>" "<grade wf dir>"
```
(Give it the workflow transcript dirs you launched. Produces `spend.csv` → per-arm tokens/$; arm C cost = its 3-stage total → system cost-per-defect vs single-LLM.)

**Step 4 — commit + report back:**
```
git add -A Shreyas_Ionic_AMC/04_RND_LAB/SYSTEM_SCIENCE_PROGRAM/
git commit -m "opus system arms graded: A/B/C/C2 result + frozen-bar verdict"
```
Tell the Principal the A/B/C numbers + bar verdict. The main account then fills the paper + LinkedIn draft and does the charts.

## Do NOT do (leave for the main account)
- Filling `SYSTEM_VS_LLM_PAPER_DRAFT.md` / `LINKEDIN_POST_DRAFT.md`, the charts, or the style-lint pass.
- Re-grading the grid open-ended (already bias-corrected).
- Touching anything outside `SYSTEM_SCIENCE_PROGRAM/`.

## If anything is unclear
Read `SSP/ws4_battery/results/ws4run_opus_20260713/PROGRESS.md` — the WINDUP CHECKPOINT section has the same steps with more context.
