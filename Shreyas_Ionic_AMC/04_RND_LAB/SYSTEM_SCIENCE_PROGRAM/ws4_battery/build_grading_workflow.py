"""Generate blind-grading workflow (.js). Run AFTER ws4_scrub_seal.py.
Per task: one grader agent gets GRADING_RUBRIC + that task's ANSWER_KEY entry + the task's scrubbed
answers (random IDs, shuffled). Graders are fresh contexts (PROTOCOL S5/S8), sonnet-tier.
Grader NEVER sees arm identities; this generator (python) reads the key, the orchestrator does not.
Usage: python build_grading_workflow.py <RUN_ID>
"""
import json, re, sys, random
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
BAT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/SYSTEM_SCIENCE_PROGRAM/ws4_battery"
RUN = BAT / "results" / sys.argv[1]
SCR = RUN / "scrubbed"
rubric = (BAT / "GRADING_RUBRIC.md").read_text(encoding="utf-8")
key = (BAT / "ANSWER_KEY.md").read_text(encoding="utf-8")

# split key per task (## T01 ... style headings)
key_parts = {}
cur = None
for line in key.splitlines():
    m = re.match(r"^#+\s*(T\d\d)\b", line)
    if m:
        cur = m.group(1)
        key_parts[cur] = []
    if cur:
        key_parts[cur].append(line)
assert len(key_parts) == 20, f"key split found {len(key_parts)} tasks"

rng = random.Random(41)
J = json.dumps
parts = []
parts.append("export const meta = { name: 'ws4-grading', description: 'Blind grading: 20 grader agents, one per task', phases: [ { title: 'Grade' } ] }")
parts.append(f"const RUNDIR = {J(str(RUN).replace(chr(92), '/'))}")
parts.append("const CASES = [")
for i in range(1, 21):
    tid = f"T{i:02d}"
    answers = sorted(SCR.glob(f"{tid}_R*.md"))
    assert answers, f"no scrubbed answers for {tid} - run ws4_scrub_seal.py first"
    rng.shuffle(answers)
    blob = []
    for a in answers:
        rid = a.stem.split("_")[1]
        blob.append(f"=== ANSWER {rid} ===\n" + a.read_text(encoding="utf-8"))
    case = {
        "tid": tid,
        "key": "\n".join(key_parts[tid]),
        "answers": "\n\n".join(blob),
        "ids": [a.stem.split("_")[1] for a in answers],
    }
    parts.append(f"  {J(case)},")
parts.append("]")
parts.append(f"const RUBRIC = {J(rubric)}")
parts.append("""
const GRADE = { type: 'object', properties: { grades: { type: 'array', items: { type: 'object', properties: {
  answer_id: { type: 'string' }, score: { type: 'integer' }, penalties: { type: 'integer' },
  justification: { type: 'string' } }, required: ['answer_id','score','penalties','justification'] } } }, required: ['grades'] }

phase('Grade')
const all = []
for (let i = 0; i < CASES.length; i += 3) {
  const chunk = CASES.slice(i, i + 3)
  const r = await parallel(chunk.map(c => () => agent(
    "You are a blind grader for a research-review benchmark. You see anonymized answers only; you do not know or guess which system produced which answer.\\n\\n--- GRADING RUBRIC ---\\n" + RUBRIC +
    "\\n--- ANSWER KEY FOR TASK " + c.tid + " (ground truth) ---\\n" + c.key +
    "\\n--- ANSWERS TO GRADE (" + c.ids.join(', ') + ") ---\\n" + c.answers +
    "\\n\\nGrade EACH answer per the rubric: score 0-3 (0 missed/wrong, 1 right area, 2 mechanism identified, 3 mechanism + correct fix), penalties = -1 per invented material defect (0 or negative; for CLEAN tasks per the key, a claimed material defect = invented). Justification must quote the key phrase you matched (or the invented claim you penalized). Return {grades:[...]} for all " + c.ids.length + " answers. Do not read or write any files.",
    { label: 'grade:' + c.tid, phase: 'Grade', schema: GRADE, model: 'sonnet' })))
  all.push(...r)
  log('graded ' + Math.min(i + 3, CASES.length) + '/20')
}
const rows = []
for (let i = 0; i < all.length; i++) {
  const c = CASES[i]
  if (!all[i]) continue
  for (const g of all[i].grades) rows.push({ ...g, task: c.tid })
}
return { total_grades: rows.length, rows }
""")
js = RUN / "ws4_grading.js"
js.write_bytes(("\n".join(parts)).encode("utf-8").replace(b"\r\n", b"\n").replace(b"\r", b""))
print("grading workflow:", js, "| cases: 20")
print("NOTE: after run, save returned rows to grades.csv (answer_id,task,score,penalties,justification), then ws4_stats.py")
