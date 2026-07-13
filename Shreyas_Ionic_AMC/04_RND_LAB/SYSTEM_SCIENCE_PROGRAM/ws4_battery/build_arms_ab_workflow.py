"""Generate the arms-A/B run workflow (.js) with task texts EMBEDDED (orchestrator context stays clean).
Arm A: task text in prompt, zero tools, one response. Arm B: same prompt + scratch python allowed.
Agents write raw answers to results/<run_id>/raw/ and return one confirmation line.
"""
import json
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
BAT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/SYSTEM_SCIENCE_PROGRAM/ws4_battery"
RUN_ID = __import__('sys').argv[1] if len(__import__('sys').argv) > 1 else "ws4run_20260713"
RES = BAT / "results" / RUN_ID / "raw"
RES.mkdir(parents=True, exist_ok=True)

ARM_PROMPT = """You are reviewing a quantitative research submission for a trading firm.
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
"""

tasks = []
for i in range(1, 21):
    tid = f"T{i:02d}"
    txt = (BAT / tid / "task.md").read_text(encoding="utf-8")
    tasks.append((tid, txt))
# skip-completed rule (never re-run a banked cell)
a_tasks = [(t, x) for t, x in tasks if not (RES / f"{t}_armA.md").exists()]
b_tasks = [(t, x) for t, x in tasks if not (RES / f"{t}_armB.md").exists()]
print(f"missing cells -> armA: {len(a_tasks)}, armB: {len(b_tasks)}")

def js_str(s):
    return json.dumps(s)

res_dir_js = str(RES).replace("\\", "/")

lines = []
lines.append("export const meta = {")
lines.append("  name: 'ws4-arms-ab',")
lines.append("  description: 'WS-4 battery arms A (no tools) and B (scratch tools), 20 tasks each, chunks of 3',")
lines.append("  phases: [ { title: 'ArmA' }, { title: 'ArmB' } ],")
lines.append("}")
lines.append(f"const RES = {js_str(res_dir_js)}")
lines.append(f"const ARM_PROMPT = {js_str(ARM_PROMPT)}")
lines.append("const A_TASKS = [")
for tid, txt in a_tasks:
    lines.append(f"  [{js_str(tid)}, {js_str(txt)}],")
lines.append("]")
lines.append("const B_TASKS = [")
for tid, txt in b_tasks:
    lines.append(f"  [{js_str(tid)}, {js_str(txt)}],")
lines.append("]")
lines.append("""
const OUT = { type: 'object', properties: { saved: { type: 'string' } }, required: ['saved'] }

function armAPrompt(tid, txt) {
  return ARM_PROMPT + "\\n---BEGIN TASK---\\n" + txt + "\\n---END TASK---\\n\\n" +
    "HARD CONSTRAINTS: Do NOT use any tools except the final Write described here. Do not read any files, do not run code, do not search. Reason in one pass and produce your final answer. " +
    "Then Write your COMPLETE final answer (verbatim, nothing omitted) to the file " + RES + "/" + tid + "_armA.md and return {saved: 'ok'}."
}
function armBPrompt(tid, txt) {
  return ARM_PROMPT + "\\n---BEGIN TASK---\\n" + txt + "\\n---END TASK---\\n\\n" +
    "TOOLS: You MAY write and execute scratch python (use python at C:/Users/Shreyas.1Gupta/AppData/Local/Python/pythoncore-3.14-64/python.exe with PYTHONIOENCODING=utf-8) inside a scratch folder you create under your session scratchpad ONLY. You may not read, list, or search ANY other files or directories; the task text above is your entire evidence. " +
    "When done, Write your COMPLETE final answer to " + RES + "/" + tid + "_armB.md and return {saved: 'ok'}."
}

async function runArm(phaseName, promptFn, suffix, LIST) {
  phase(phaseName)
  const out = []
  for (let i = 0; i < LIST.length; i += 3) {
    const chunk = LIST.slice(i, i + 3)
    const r = await parallel(chunk.map(([tid, txt]) => () =>
      agent(promptFn(tid, txt), { label: suffix + ':' + tid, phase: phaseName, schema: OUT })))
    out.push(...r)
    log(phaseName + ' done ' + Math.min(i + 3, LIST.length) + '/' + LIST.length)
  }
  return out
}

const a = await runArm('ArmA', armAPrompt, 'A', A_TASKS)
const b = await runArm('ArmB', armBPrompt, 'B', B_TASKS)
return { armA_completed: a.filter(Boolean).length, armB_completed: b.filter(Boolean).length }
""")
js_path = BAT / "results" / RUN_ID / "ws4_arms_ab.js"
js_path.write_bytes(("\n".join(lines)).encode("utf-8").replace(b"\r\n", b"\n").replace(b"\r", b""))
print("workflow script:", js_path)
print("tasks embedded:", len(tasks), "| raw dir:", RES)
