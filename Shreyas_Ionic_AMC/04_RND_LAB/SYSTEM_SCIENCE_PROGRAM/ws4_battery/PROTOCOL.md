# WS-4 BATTERY — PRE-REGISTERED RUN PROTOCOL (frozen 2026-07-12, before any arm has run)
Charter: MASTER_PLAN.md WS-4, test battery (iii) — "OUR OWN adversarial battery".
No task, key entry, rubric rule, or bar in this file may change after the first arm
runs. Any change = new battery version with a restarted clock (D-030 discipline).

## 1. The asset
20 tasks in `ws4_battery/T01..T20/task.md`. 16 contain exactly one planted,
verified defect; 4 are clean false-positive controls. Ground truth: ANSWER_KEY.md.
Scoring: GRADING_RUBRIC.md. Defect verification: `_verify.py` per defective folder
(all 16 run green 2026-07-12).

**Containment rules (absolute):**
- An arm receives ONLY the text of one `task.md` at a time. Never `_verify.py`,
  never ANSWER_KEY.md / GRADING_RUBRIC.md / this file, never another task's folder.
- Arms B and C get code/tool access in an ISOLATED scratch directory containing a
  copy of the single task.md — never a path under the firm repo (the repo contains
  the key and, worse, the source landmine docs; that would contaminate the arm).
  Arm C's agents MAY use their standing persona knowledge; they may NOT open
  repo files during the run.
- Tasks are run in fixed order T01..T20, one fresh context per task (no carryover
  between tasks within an arm).

## 2. Arms
| arm | definition |
|---|---|
| **A** | single Claude call, NO tools. One message = the arm prompt + task.md text. One response, no follow-ups. |
| **B** | single Claude call WITH code tools (python execution / file write in the scratch dir). Same one arm prompt; the model may write and run scratch code before answering. One final answer per task. |
| **C** | THE FIRM's review pipeline: the standing multi-agent review (e.g. quant-head review + red-team attack + overfit-analyst pass, per the firm's normal gate flow) applied to the same task.md, at a TOTAL token budget matched to arm B's actual usage (see §4). The pipeline's single consolidated verdict is the answer. |

Same base model family and settings across arms (record exact model id per run).
Arms D (human baselines) and E (published systems) are out of scope for this
battery; they attach to batteries (i)/(ii) per MASTER_PLAN.

## 3. Identical arm prompt (verbatim; the ONLY prompt any arm receives)
```
You are reviewing a quantitative research submission for a trading firm.
The task text below contains a scenario and either code or a results write-up.

Review this. Identify any defects that would make the result wrong or fake.
Be specific.

Rules for your answer:
- If you find defects, name each one: the exact line/field/claim, the mechanism
  by which it corrupts the result, and the correct fix.
- Some submissions contain NO material defect. If so, say exactly that: "No
  material defect." Do not invent problems; minor style or robustness notes must
  be clearly labelled as non-material comments.
- Finish with a numbered list: your claimed material defects (or "none").

[TASK.MD TEXT PASTED HERE]
```
No arm gets hints about defect classes, counts, or the existence of clean tasks
beyond the wording above (which every arm sees identically).

## 4. Budget matching
- Record tokens (in+out, all calls/agents) per task per arm.
- Arm C's per-task budget cap = 1.5x arm B's measured per-task average (headroom
  for orchestration); if C exceeds the cap on a task, that task's C answer is
  whatever the pipeline has consolidated at cutoff. Report actual spend per arm.
- One run per arm per task (no best-of-N anywhere).

## 5. Blind grading
1. Collect the final answer text of every (arm, task) pair.
2. A scrub pass removes arm-identifying furniture (agent names, persona headers,
   tool logs, token counts) leaving only the substantive answer.
3. Each answer gets a random ID; the arm->ID mapping is written to a sealed file
   (`results/<run_id>/_mapping.json`) not opened until all grades are filed.
4. The grader (a fresh session with ONLY ANSWER_KEY.md + GRADING_RUBRIC.md + the
   scrubbed answers, in shuffled order) files `grades.csv`: answer_id, task,
   score, penalties, one-line justification.
5. Unseal the mapping, compute aggregates per arm.

## 6. The frozen bar (copied verbatim from MASTER_PLAN.md WS-4)
> BARS (pre-registered): claim "the system adds value over a single LLM" ONLY if
> arm C beats arm A AND B on (iii) our-battery defects-found by >=20% relative,
> and is non-inferior elsewhere at matched budget. Battery (iii) is where the
> machinery should shine; if C <= B there, the multi-agent overhead is not paying
> and we say so.

Operationalization for THIS battery (fixed now): "defects-found" = count of the 16
defective tasks scored >=2 (mechanism identified). ">=20% relative" = C's count
>= 1.2x max(A's count, B's count). Additionally report (not gate): mean score and
clean-task false-positive rate — if C wins on defects-found but posts a WORSE
clean-task false-positive rate than B, the write-up must say so prominently
(a red team that hallucinates defects is not added value).

## 7. Outputs
`results/<run_id>/` under this folder: raw transcripts per (arm, task), scrubbed
answers, sealed mapping, grades.csv, spend log, and a RESULTS.md with the
aggregate table and the bar verdict. Everything banked to disk as it is produced
(token-cut safe). Trials-ledger entry on run start and on verdict.

## 8. Integrity notes
- The battery is one-shot-per-arm: once an arm has seen the tasks, reruns of the
  same arm on this battery are tainted (memorization) — new comparisons need a
  fresh battery version (T21+ or v2).
- The battery was BUILT by an AI session with access to the firm's landmine docs;
  arm C's personas draw on the same docs. That is by design (the firm's knowledge
  IS the treatment); arm A/B fairness comes from the defects being real,
  self-contained, and detectable from the task text alone — verified per task.
- Graders must not be the session that built the battery, where operationally
  possible; if unavoidable, grades must quote the key verbatim as justification.
