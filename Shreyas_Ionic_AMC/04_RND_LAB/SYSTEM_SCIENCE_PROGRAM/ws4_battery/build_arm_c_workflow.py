"""Generate arm-C workflow (.js): firm pipeline per task = reviewer -> red-team -> synthesis,
fresh contexts, task text embedded, <=3 concurrent tasks (stages sequential within a task).
PROTOCOL S2/S4: personas may use standing knowledge, NO repo file access; budget cap enforced
by post-hoc metering + honest overage reporting (spend log). LF line endings enforced.
Run AFTER arm B completes (same session model as arms A/B of the grid being run).
"""
import json
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
BAT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/SYSTEM_SCIENCE_PROGRAM/ws4_battery"
RUN_ID = "ws4run_20260713"  # change to the grid's run id (e.g. ws4run_sonnet_YYYYMMDD) before use
RES = BAT / "results" / RUN_ID / "raw"
RES.mkdir(parents=True, exist_ok=True)

ARM_PROMPT = (BAT / "PROTOCOL.md").read_text(encoding="utf-8").split("```")[1].strip() if "```" in (BAT / "PROTOCOL.md").read_text(encoding="utf-8") else ""
assert "Review this" in ARM_PROMPT, "verbatim arm prompt not extracted from PROTOCOL.md"

tasks = [(f"T{i:02d}", (BAT / f"T{i:02d}" / "task.md").read_text(encoding="utf-8")) for i in range(1, 21)]
res_js = str(RES).replace("\\", "/")
J = json.dumps

parts = []
parts.append("export const meta = { name: 'ws4-arm-c', description: 'WS-4 arm C: reviewer->red-team->synthesis per task, <=3 tasks concurrent', phases: [ { title: 'ArmC' } ] }")
parts.append(f"const RES = {J(res_js)}")
parts.append(f"const ARM_PROMPT = {J(ARM_PROMPT)}")
parts.append("const TASKS = [")
for tid, txt in tasks:
    parts.append(f"  [{J(tid)}, {J(txt)}],")
parts.append("]")
parts.append("""
const OUT = { type: 'object', properties: { answer: { type: 'string' } }, required: ['answer'] }
const SAVED = { type: 'object', properties: { saved: { type: 'string' } }, required: ['saved'] }
const NOFILES = " HARD CONSTRAINT: do not read, list, or search ANY files or directories; no code execution; the text above is your entire evidence. Return {answer: <your full review>}."

async function runTask(tid, txt) {
  const base = ARM_PROMPT + "\\n---BEGIN TASK---\\n" + txt + "\\n---END TASK---\\n"
  const r1 = await agent("You are the firm's Head of Quant reviewing a submission.\\n" + base + NOFILES,
    { label: 'C1rev:' + tid, phase: 'ArmC', schema: OUT })
  const r2 = await agent("You are the firm's Red Team (devil's advocate). Attack BOTH the submission below AND the prior reviewer's findings: refute weak claims, find what was missed, flag invented defects.\\n" + base + "\\n---PRIOR REVIEWER FINDINGS---\\n" + (r1 ? r1.answer : '(reviewer unavailable)') + "\\n---END PRIOR---\\n" + NOFILES,
    { label: 'C2red:' + tid, phase: 'ArmC', schema: OUT })
  const r3 = await agent("You are the firm's CIO issuing the consolidated verdict on a submission after two reviews. Weigh the reviewer and red-team views; keep only defects that survive; obey the answer rules verbatim.\\n" + base + "\\n---REVIEWER---\\n" + (r1 ? r1.answer : '') + "\\n---RED TEAM---\\n" + (r2 ? r2.answer : '') + "\\n---END---\\n" + NOFILES.replace('Return {answer: <your full review>}', 'Write your COMPLETE consolidated final answer to ' + RES + '/' + tid + '_armC.md and return {saved: "ok"}'),
    { label: 'C3syn:' + tid, phase: 'ArmC', schema: SAVED })
  return r3
}

const out = []
for (let i = 0; i < TASKS.length; i += 3) {
  const chunk = TASKS.slice(i, i + 3)
  const r = await parallel(chunk.map(([tid, txt]) => () => runTask(tid, txt)))
  out.push(...r)
  log('ArmC done ' + Math.min(i + 3, TASKS.length) + '/20')
}
return { armC_completed: out.filter(Boolean).length }
""")
js_path = BAT / "results" / RUN_ID / "ws4_arm_c.js"
js_path.write_bytes(("\n".join(parts)).encode("utf-8").replace(b"\r\n", b"\n").replace(b"\r", b""))
print("arm-C workflow:", js_path, "| tasks:", len(tasks))
