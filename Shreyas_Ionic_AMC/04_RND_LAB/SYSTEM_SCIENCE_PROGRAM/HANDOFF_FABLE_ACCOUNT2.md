# HANDOFF — Fable runs for the "Firm S" system-vs-LLM experiment
**For: the second Claude Code account (the one that still has Fable budget). Paste this whole file as your prompt, or open it and follow it.**

## What you are doing (30 seconds)
We are measuring whether a multi-agent research firm beats a single LLM at catching defects in quant-research submissions. There is a frozen 20-task benchmark (`ws4_battery/`). "Arm A" (single call, no tools) was already run on **Fable 5**. Your job is to run the other Fable arms so the whole core comparison is on the **same model (Fable 5)** — that is the only reason this is on your account. Everything is scripted; you run 4-5 generators + workflows, and every answer auto-saves to the shared project folder. You do NOT grade, analyze, or write anything — another session does that.

## THREE RULES (do not break these — they protect the experiment)
1. **Be on Fable 5.** Run `/model` and confirm the session model is Fable 5 BEFORE anything. Arms B/C/C2 and the MG SYSTEM row inherit the session model; they MUST be Fable to match Arm A. If you cannot select Fable, STOP and tell the Principal — do not run them on another model.
2. **Never open the answer key.** Do NOT read, open, or cat `ws4_battery/ANSWER_KEY.md`, `ws4_battery/GRADING_RUBRIC.md`, or any `ws4_battery/T*/\_verify.py`. Seeing them contaminates the run.
3. **Never resume a workflow run-id from another session.** Every generator below AUTO-SKIPS cells that already have a saved answer, then prints how many are missing. Always run the generator fresh, then launch the `.js` it writes. (A cross-session `resumeFromRunId` silently re-ran and overwrote answers last time — that is why we use skip-and-regenerate instead.)

## Environment
- Python: `C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe` (the bare `python` alias is broken). Prefix every run with `PYTHONIOENCODING=utf-8`.
- Both accounts share this one folder, so all scripts and task files are already on disk. Root: `c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500`.
- PowerShell 5.1 has no `&&` — run commands one per line.

## STEPS (in order; each = run the generator, then launch the .js it prints)
Let `P` = the python exe above, `SSP` = `Shreyas_Ionic_AMC/04_RND_LAB/SYSTEM_SCIENCE_PROGRAM`.

**Step 1 — Battery arms B (single call + scratch tools):**
```
PYTHONIOENCODING=utf-8 "P" "SSP/ws4_battery/build_arms_ab_workflow.py"
```
It prints `missing cells -> armA: 0, armB: N`. Then call the Workflow tool with
`scriptPath: "SSP/ws4_battery/results/ws4run_20260713/ws4_arms_ab.js"` (no resumeFromRunId). Wait for it to finish.

**Step 2 — Firm pipeline, full personas (arm C):**
```
PYTHONIOENCODING=utf-8 "P" "SSP/ws4_battery/build_arm_c_workflow.py" ws4run_20260713 C
```
Then Workflow on `SSP/ws4_battery/results/ws4run_20260713/ws4_arm_c.js`.

**Step 3 — Firm pipeline, ablated / no personas (arm C2):**
```
PYTHONIOENCODING=utf-8 "P" "SSP/ws4_battery/build_arm_c_workflow.py" ws4run_20260713 C2
```
Then Workflow on `SSP/ws4_battery/results/ws4run_20260713/ws4_arm_c2.js`. (C vs C2 is the "do personas/naming help" test — both must be Fable.)

**Step 4 — Model-grid Fable row + SYSTEM row (8 tasks + 8 tasks):**
```
PYTHONIOENCODING=utf-8 "P" "SSP/MODEL_GRID/build_mg_grid.py" fable system
```
Then Workflow on `SSP/MODEL_GRID/mg_grid_fable_sys.js`. Just run all 8 tasks as generated (they're cheap). *Note: the two exact-answer puzzle cells (MG05/MG06) also have a labeled Opus-imputed fallback, so even if those two never run, the table still has a Fable puzzle score — but a real run is better and supersedes it. Do NOT hand-create any answer files.*

**Step 5 — OPTIONAL, only if you have spare Sonnet budget (fills 3 missing Sonnet grid cells):**
```
PYTHONIOENCODING=utf-8 "P" "SSP/MODEL_GRID/build_mg_grid.py" sonnet nosystem
```
Then Workflow on `SSP/MODEL_GRID/mg_grid_sonnet.js`. Skip this if unsure — the first account will cover it.

## If a workflow dies on a spend limit
Some cells will save, some will fail — that is fine. Do NOT resume. Just re-run the SAME generator command (it skips the ones that saved) and launch the freshly-written `.js` again when budget returns. Nothing is lost or duplicated.

## When you are done
Tell the Principal "Fable runs done" (and which steps completed). All answers are already saved under
`SSP/ws4_battery/results/ws4run_20260713/raw/` and `SSP/MODEL_GRID/results/`. The first account picks up from there: token metering → blind grading → stats → paper. You do not need to do anything else.
