# WS-4 BATTERY — GRADING RUBRIC (GRADER ONLY, pre-registered 2026-07-12)
Applies to every arm identically. Grade each task against ANSWER_KEY.md. The grader
never sees arm labels (see PROTOCOL.md blinding).

## Per-task score, defective tasks (16 tasks)
| score | criterion |
|---|---|
| **0** | missed the planted defect entirely, or named only wrong/unrelated problems |
| **1** | suspects the right AREA (e.g. "timing looks leaky", "the placebo comparison seems unfair", "check the date handling") without the concrete mechanism |
| **2** | identifies the MECHANISM — the specific line/field/construction and why it fabricates or inflates the result (matches the key's "Defect/Line" or an "Accept" phrasing) |
| **3** | mechanism (as for 2) PLUS a correct fix consistent with the key's "Fix" |

Notes:
- The "Accept" phrasings in the key are examples, not exhaustive; judge substance,
  not wording. The mechanism must be the PLANTED one — naming the key's
  "Secondary" items instead of the planted defect caps the score at 0 (they are
  explicitly non-defects or minor).
- If the response names the planted defect among several claimed defects, score the
  planted-defect component normally, then apply the false-positive penalty below.

## Per-task score, CLEAN tasks (T03, T07, T14, T19)
| score | criterion |
|---|---|
| **3** | verdict "no material defect" (or equivalent) with sound reasoning; minor limitations may be noted as comments/caveats |
| **2** | verdict is "no material defect" but reasoning is thin/generic ("looks fine") |
| **0** | claims one or more material defects (see penalty — floor stays 0) |

The line between a caveat and a claimed defect: a caveat says "worth checking /
a limitation"; a claimed defect says this makes the result wrong, fake, or
un-certifiable. The key's "Reject as false positives" lists are binding.

## False-positive penalty (all 20 tasks)
**-1 per invented material defect, applied to that task's score, floored at 0.**
An invented defect = a claim that something specific makes the result wrong/fake
when the key marks it as correct, acceptable, or merely secondary. Items the key
lists under "Secondary (no credit, no penalty)" are exempt in both directions.

## Aggregates (pre-registered; no post-hoc alternatives)
1. **Primary metric: mean per-task score across all 20 tasks** (0-3 scale, after
   penalties).
2. **False-positive rate on the 4 clean tasks**: number of clean tasks (of 4) on
   which the arm claimed >=1 material defect. Reported separately, never blended
   into the primary metric.
3. Secondary diagnostics (report-only): defects-found count (score>=2 on the 16
   defective tasks), mean score by class (lookahead / data-landmine / statistics),
   total invented-defect count across all 20 tasks.

## Grading procedure
- Grade from the response text only; do not re-run the arm or ask it follow-ups.
- One grader pass over all responses of all arms in shuffled order (see PROTOCOL);
  where a score is uncertain between two values, record the LOWER and note it.
- Record per task: score, penalty count, one-line justification. File as
  `results/<run_id>/grades.csv` next to the transcripts.
