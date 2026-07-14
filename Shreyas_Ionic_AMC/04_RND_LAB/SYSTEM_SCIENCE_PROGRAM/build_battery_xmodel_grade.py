"""Build cross-model battery grading workflow (blind, cheapest judge=haiku, ONE call per task).
Per task: grader gets the sealed key entry + rubric + the 4 anonymized model answers -> scores each 0-3
(+FP penalty). Sealed mapping so we unseal after grades filed. Generator reads the key (orchestrator stays blind)."""
import json, re, random
from pathlib import Path

SSP = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\SYSTEM_SCIENCE_PROGRAM")
BAT = SSP / "ws4_battery"
COLS = {"fable": "webrun_fable", "opus": "ws4run_opus_20260713", "sonnet": "webrun_sonnetweb", "haiku": "webrun_haiku"}
OUT = BAT / "results" / "xmodel_grade"; OUT.mkdir(parents=True, exist_ok=True)
rubric = (BAT / "GRADING_RUBRIC.md").read_text(encoding="utf-8")
key = (BAT / "ANSWER_KEY.md").read_text(encoding="utf-8")
kparts, cur = {}, None
for ln in key.splitlines():
    m = re.match(r"^#+\s*(T\d\d)\b", ln) or re.match(r"^\**\s*(T\d\d)\b", ln)
    if m and (ln.startswith("#") or ln.startswith("**")):
        cur = m.group(1); kparts[cur] = []
    if cur:
        kparts[cur].append(ln)
assert len(kparts) >= 18, f"key split found {len(kparts)} tasks"

rng = random.Random(7)
mapping = {}
cases = []
for i in range(1, 21):
    tid = f"T{i:02d}"
    ans = []
    for model, d in COLS.items():
        f = BAT / "results" / d / "raw" / f"{tid}_armA.md"
        if f.exists():
            ans.append((model, f.read_text(encoding="utf-8").strip()))
    rng.shuffle(ans)
    ids = [f"B{i:02d}{chr(97+j)}" for j in range(len(ans))]
    blob = []
    for (model, body), bid in zip(ans, ids):
        mapping[bid] = {"task": tid, "model": model}
        blob.append(f"----- ANSWER {bid} -----\n{body}")
    cases.append({"tid": tid, "key": "\n".join(kparts.get(tid, [f"{tid}: (key missing)"])),
                  "answers": "\n\n".join(blob), "ids": ids})
(OUT / "battery_xmodel_mapping.json").write_text(json.dumps(mapping, indent=1), encoding="utf-8")

J = json.dumps
P = ["export const meta = { name: 'battery-xmodel-grade', description: 'Blind cross-model battery grading, 1 haiku judge/task', phases: [ { title: 'Grade' } ] }"]
P.append(f"const RUBRIC = {J(rubric)}")
P.append("const CASES = [")
for c in cases:
    P.append(f"  {J(c)},")
P.append("]")
P.append(r"""
const G = { type: 'object', properties: { grades: { type: 'array', items: { type: 'object', properties: {
  answer_id: {type:'string'}, score: {type:'integer'}, penalties: {type:'integer'}, note: {type:'string'} },
  required: ['answer_id','score','penalties'] } } }, required: ['grades'] }
phase('Grade')
const all = []
for (let i = 0; i < CASES.length; i += 5) {
  const chunk = CASES.slice(i, i + 5)
  const r = await parallel(chunk.map(c => () => agent(
    "You are a strict BLIND grader for a defect-review benchmark. You do NOT know which model wrote which answer.\n\n--- RUBRIC ---\n" + RUBRIC +
    "\n--- ANSWER KEY (ground truth for task " + c.tid + ") ---\n" + c.key +
    "\n--- ANSWERS TO GRADE (" + c.ids.join(', ') + ") ---\n" + c.answers +
    "\n\nScore EACH answer: score 0-3 (0 missed/wrong; 1 right area; 2 identifies the mechanism; 3 mechanism + correct fix). penalties = -1 per INVENTED material defect (for a CLEAN task per the key, any claimed material defect is invented; 0 or negative). Return {grades:[...]} for all " + c.ids.length + " answers. Use no tools.",
    { label: 'grade:' + c.tid, phase: 'Grade', schema: G, model: 'haiku' })))
  all.push(...r)
  log('graded ' + Math.min(i+5, CASES.length) + '/20')
}
const rows = []
for (let i=0;i<all.length;i++){ if(!all[i]) continue; for (const g of all[i].grades) rows.push({...g, task: CASES[i].tid}) }
return { n: rows.length, rows }
""")
(OUT / "grade.js").write_bytes(("\n".join(P)).encode("utf-8").replace(b"\r\n", b"\n"))
print(f"grade.js built: 20 tasks, {len(mapping)} answers, sealed mapping written")
