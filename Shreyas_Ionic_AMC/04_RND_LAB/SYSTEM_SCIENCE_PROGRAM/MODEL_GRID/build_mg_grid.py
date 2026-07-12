"""Generate mg_grid.js: 8 tasks x 4 single-call model rows + 3-stage system row. LF enforced."""
import json
from pathlib import Path

MG = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\SYSTEM_SCIENCE_PROGRAM\MODEL_GRID")
OUTD = MG / "results"
OUTD.mkdir(exist_ok=True)
J = json.dumps
tasks = [(f"MG{i:02d}", (MG / f"MG{i:02d}.md").read_text(encoding="utf-8")) for i in range(1, 9)]

p = []
p.append("export const meta = { name: 'mg-grid', description: 'MODEL-GRID axis 2: 8 tasks x 4 models + system pipeline', phases: [ { title: 'Models' }, { title: 'System' } ] }")
p.append(f"const RES = {J(str(OUTD).replace(chr(92), '/'))}")
p.append("const TASKS = [")
for tid, txt in tasks:
    p.append(f"  [{J(tid)}, {J(txt)}],")
p.append("]")
p.append(r"""
const OUT = { type: 'object', properties: { saved: { type: 'string' } }, required: ['saved'] }
const A = { type: 'object', properties: { answer: { type: 'string' } }, required: ['answer'] }
const MODELS = ['haiku', 'sonnet', 'opus', 'fable']
const NOTOOLS = ' Answer in one pass. Do NOT use any tools except the single Write specified. '
const NOTOOLS2 = ' Answer in one pass. Do NOT use any tools. '

phase('Models')
const jobs = []
for (const m of MODELS) for (const [tid, txt] of TASKS) jobs.push([m, tid, txt])
for (let i = 0; i < jobs.length; i += 2) {
  const chunk = jobs.slice(i, i + 2)
  await parallel(chunk.map(([m, tid, txt]) => () => agent(
    txt + '\n' + NOTOOLS + 'Write your COMPLETE answer to ' + RES + '/' + tid + '_' + m + '.md and return {saved:"ok"}.',
    { label: 'MG:' + m + ':' + tid, phase: 'Models', schema: OUT, model: m === 'fable' ? undefined : m })))
  if ((i + 2) % 8 === 0) log('models ' + Math.min(i + 2, jobs.length) + '/' + jobs.length)
}

phase('System')
for (let i = 0; i < TASKS.length; i += 2) {
  const chunk = TASKS.slice(i, i + 2)
  await parallel(chunk.map(([tid, txt]) => () => (async () => {
    const r1 = await agent('Review/answer this task in your capacity as Head of Quant.\n' + txt + NOTOOLS2 + 'Return {answer: ...}', { label: 'SYS1:' + tid, phase: 'System', schema: A, agentType: 'quant-head-arjun-rao' })
    const r2 = await agent('Red-team the draft answer below to this task: refute weak parts, add what is missing.\nTASK:\n' + txt + '\nDRAFT:\n' + (r1 ? r1.answer : '') + NOTOOLS2 + 'Return {answer: ...}', { label: 'SYS2:' + tid, phase: 'System', schema: A, agentType: 'red-team-nikhil-bose' })
    return agent('As CIO, produce the final consolidated answer to the task, integrating the draft and the red-team critique. Quality over length.\nTASK:\n' + txt + '\nDRAFT:\n' + (r1 ? r1.answer : '') + '\nCRITIQUE:\n' + (r2 ? r2.answer : '') + NOTOOLS + 'Write the COMPLETE final answer to ' + RES + '/' + tid + '_SYSTEM.md and return {saved:"ok"}.', { label: 'SYS3:' + tid, phase: 'System', schema: OUT, agentType: 'cio-rajan-mehta' })
  })()))
  log('system ' + Math.min(i + 2, TASKS.length) + '/8')
}
return { done: true }
""")
(MG / "mg_grid.js").write_bytes(("\n".join(p)).encode("utf-8").replace(b"\r\n", b"\n").replace(b"\r", b""))
print("mg_grid.js written cleanly")
