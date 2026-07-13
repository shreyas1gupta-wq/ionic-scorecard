"""Generate mg_grid_<tag>.js. Parametrized + skip-completed (never re-run a banked cell).
Usage: python build_mg_grid.py [models] [system|nosystem]
  models  = comma list from {haiku,sonnet,opus,fable}  (default: all four)
  system  = include the 3-stage SYSTEM phase (inherits session model -> run on the base-model session)
Examples:
  python build_mg_grid.py opus nosystem          -> mg_grid_opus.js (Opus single-call row only)
  python build_mg_grid.py fable system           -> mg_grid_fable_sys.js (Fable row + SYSTEM row)
  python build_mg_grid.py sonnet nosystem        -> mg_grid_sonnet.js (fills missing Sonnet cells)
"""
import json, sys
from pathlib import Path

MG = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\SYSTEM_SCIENCE_PROGRAM\MODEL_GRID")
OUTD = MG / "results"
OUTD.mkdir(exist_ok=True)
J = json.dumps

models = (sys.argv[1] if len(sys.argv) > 1 else "haiku,sonnet,opus,fable").split(",")
do_system = (sys.argv[2] if len(sys.argv) > 2 else "system") == "system"
tag = "_".join(models) + ("_sys" if do_system else "")

tasks = [(f"MG{i:02d}", (MG / f"MG{i:02d}.md").read_text(encoding="utf-8")) for i in range(1, 9)]
jobs = [(m, tid, txt) for m in models for tid, txt in tasks if not (OUTD / f"{tid}_{m}.md").exists()]
sys_tasks = [(tid, txt) for tid, txt in tasks if not (OUTD / f"{tid}_SYSTEM.md").exists()] if do_system else []
print(f"tag={tag} | single-call cells missing: {len(jobs)} | system cells missing: {len(sys_tasks)}")

p = []
p.append(f"export const meta = {{ name: 'mg-grid-{tag}', description: 'MODEL-GRID {tag}: single-call rows + optional system', phases: [ {{ title: 'Models' }}, {{ title: 'System' }} ] }}")
p.append(f"const RES = {J(str(OUTD).replace(chr(92), '/'))}")
p.append("const JOBS = [")
for m, tid, txt in jobs:
    p.append(f"  [{J(m)}, {J(tid)}, {J(txt)}],")
p.append("]")
p.append("const SYS_TASKS = [")
for tid, txt in sys_tasks:
    p.append(f"  [{J(tid)}, {J(txt)}],")
p.append("]")
p.append(r"""
const OUT = { type: 'object', properties: { saved: { type: 'string' } }, required: ['saved'] }
const A = { type: 'object', properties: { answer: { type: 'string' } }, required: ['answer'] }
const NT = ' Answer in one pass. Do NOT use any tools except the single Write specified. Do not read, list, or search files. '
const NT2 = ' Answer in one pass. Do NOT use any tools; the task text is your entire input. '

phase('Models')
for (let i = 0; i < JOBS.length; i += 3) {
  const chunk = JOBS.slice(i, i + 3)
  await parallel(chunk.map(([m, tid, txt]) => () => agent(
    txt + '\n' + NT + 'Write your COMPLETE answer to ' + RES + '/' + tid + '_' + m + '.md and return {saved:"ok"}.',
    { label: 'MG:' + m + ':' + tid, phase: 'Models', schema: OUT, model: m })))
  log('models ' + Math.min(i + 3, JOBS.length) + '/' + JOBS.length)
}

phase('System')
for (let i = 0; i < SYS_TASKS.length; i += 2) {
  const chunk = SYS_TASKS.slice(i, i + 2)
  await parallel(chunk.map(([tid, txt]) => () => (async () => {
    const r1 = await agent('Answer this task in your capacity as Head of Quant.\n' + txt + NT2 + 'Return {answer: ...}', { label: 'SYS1:' + tid, phase: 'System', schema: A, agentType: 'quant-head-arjun-rao' })
    const r2 = await agent('Red-team the draft answer below: refute weak parts, add what is missing.\nTASK:\n' + txt + '\nDRAFT:\n' + (r1 ? r1.answer : '') + NT2 + 'Return {answer: ...}', { label: 'SYS2:' + tid, phase: 'System', schema: A, agentType: 'red-team-nikhil-bose' })
    return agent('As CIO, produce the final consolidated answer, integrating the draft and the red-team critique. Quality over length.\nTASK:\n' + txt + '\nDRAFT:\n' + (r1 ? r1.answer : '') + '\nCRITIQUE:\n' + (r2 ? r2.answer : '') + NT + 'Write the COMPLETE final answer to ' + RES + '/' + tid + '_SYSTEM.md and return {saved:"ok"}.', { label: 'SYS3:' + tid, phase: 'System', schema: OUT, agentType: 'cio-rajan-mehta' })
  })()))
  log('system ' + Math.min(i + 2, SYS_TASKS.length) + '/' + SYS_TASKS.length)
}
return { done: true, single: JOBS.length, system: SYS_TASKS.length }
""")
(MG / f"mg_grid_{tag}.js").write_bytes(("\n".join(p)).encode("utf-8").replace(b"\r\n", b"\n").replace(b"\r", b""))
print("written:", MG / f"mg_grid_{tag}.js")
