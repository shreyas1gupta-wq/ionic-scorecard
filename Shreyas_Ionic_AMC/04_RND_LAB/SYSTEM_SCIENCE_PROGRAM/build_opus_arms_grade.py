"""Grade the OPUS core arms A/B/C/C2 (ws4run_opus_20260713) blind vs sealed key.
JUDGE = HAIKU (NON-opus, because opus self-preference on opus-authored arms is MEASURED). 1 judge/task.
Grades whatever exists per arm (C/C2 may be partial -> n disclosed). Writes grade.js + sealed mapping."""
import json, re, random
from pathlib import Path
SSP = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\SYSTEM_SCIENCE_PROGRAM")
BAT = SSP / "ws4_battery"; RAW = BAT / "results" / "ws4run_opus_20260713" / "raw"
OUT = BAT / "results" / "opus_arms_grade"; OUT.mkdir(parents=True, exist_ok=True)
ARMS = ["A", "B", "C", "C2"]
rubric = (BAT / "GRADING_RUBRIC.md").read_text(encoding="utf-8")
key = (BAT / "ANSWER_KEY.md").read_text(encoding="utf-8")
kp, cur = {}, None
for ln in key.splitlines():
    m = re.match(r"^#+\s*(T\d\d)\b", ln) or re.match(r"^\**\s*(T\d\d)\b", ln)
    if m and (ln.startswith("#") or ln.startswith("**")):
        cur = m.group(1); kp[cur] = []
    if cur: kp[cur].append(ln)
rng = random.Random(11); mapping = {}; cases = []
for i in range(1, 21):
    tid = f"T{i:02d}"; ans = []
    for arm in ARMS:
        f = RAW / f"{tid}_arm{arm}.md"
        if f.exists(): ans.append((arm, f.read_text(encoding="utf-8").strip()))
    if not ans: continue
    rng.shuffle(ans); ids = [f"O{i:02d}{chr(97+j)}" for j in range(len(ans))]; blob = []
    for (arm, body), oid in zip(ans, ids):
        mapping[oid] = {"task": tid, "arm": arm}; blob.append(f"----- ANSWER {oid} -----\n{body}")
    cases.append({"tid": tid, "key": "\n".join(kp.get(tid, [tid])), "answers": "\n\n".join(blob), "ids": ids})
(OUT / "opus_arms_mapping.json").write_text(json.dumps(mapping, indent=1), encoding="utf-8")
J = json.dumps
P = ["export const meta = { name:'opus-arms-grade', description:'Blind grade opus arms A/B/C/C2, haiku judge', phases:[{title:'Grade'}] }"]
P.append(f"const RUBRIC = {J(rubric)}"); P.append("const CASES = " + J(cases))
P.append(r"""
const G = { type:'object', properties:{ grades:{ type:'array', items:{ type:'object', properties:{
  answer_id:{type:'string'}, score:{type:'integer'}, penalties:{type:'integer'} }, required:['answer_id','score'] } } }, required:['grades'] }
phase('Grade')
const all=[]
for (let i=0;i<CASES.length;i+=5){
  const ch=CASES.slice(i,i+5)
  const r=await parallel(ch.map(c=>()=>agent(
    "You are a strict BLIND grader for a defect-review benchmark. You do NOT know which system produced which answer.\n--- RUBRIC ---\n"+RUBRIC+
    "\n--- ANSWER KEY (ground truth for "+c.tid+") ---\n"+c.key+
    "\n--- ANSWERS ("+c.ids.join(', ')+") ---\n"+c.answers+
    "\n\nScore EACH 0-3 (0 missed;1 area;2 mechanism;3 mechanism+fix). penalties=-1 per INVENTED material defect (for a CLEAN task per key, any claimed material defect is invented). Return {grades:[...]} all "+c.ids.length+". No tools.",
    { label:'grade:'+c.tid, phase:'Grade', schema:G, model:'haiku' })))
  all.push(...r); log('graded '+Math.min(i+5,CASES.length)+'/'+CASES.length)
}
const rows=[]; for(let i=0;i<all.length;i++){ if(!all[i])continue; for(const g of all[i].grades) rows.push({...g, task:CASES[i].tid}) }
return { n: rows.length, rows }
""")
(OUT / "grade.js").write_bytes(("\n".join(P)).encode("utf-8").replace(b"\r\n", b"\n"))
counts = {a: len(list(RAW.glob(f"T*_arm{a}.md"))) for a in ARMS}
print(f"grade.js built. opus arm counts {counts}, {len(mapping)} answers to grade")
