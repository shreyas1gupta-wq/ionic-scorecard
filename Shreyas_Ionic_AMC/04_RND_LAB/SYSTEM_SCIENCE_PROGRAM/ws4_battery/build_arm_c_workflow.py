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
RUN_ID = __import__('sys').argv[1] if len(__import__('sys').argv) > 1 else "ws4run_20260713"  # change to the grid's run id (e.g. ws4run_sonnet_YYYYMMDD) before use
RES = BAT / "results" / RUN_ID / "raw"
RES.mkdir(parents=True, exist_ok=True)

ARM_PROMPT = (BAT / "PROTOCOL.md").read_text(encoding="utf-8").split("```")[1].strip() if "```" in (BAT / "PROTOCOL.md").read_text(encoding="utf-8") else ""
assert "Review this" in ARM_PROMPT, "verbatim arm prompt not extracted from PROTOCOL.md"

VARIANT_EARLY = __import__('sys').argv[2] if len(__import__('sys').argv) > 2 else 'C'
tasks = [(f"T{i:02d}", (BAT / f"T{i:02d}" / "task.md").read_text(encoding="utf-8")) for i in range(1, 21)]
tasks = [(t, x) for t, x in tasks if not (RES / f"{t}_arm{VARIANT_EARLY}.md").exists()]
print(f"missing arm{VARIANT_EARLY} cells: {len(tasks)}")
res_js = str(RES).replace("\\", "/")
J = json.dumps

parts = []
VARIANT = __import__('sys').argv[2] if len(__import__('sys').argv) > 2 else 'C'
parts.append(f"export const meta = {{ name: 'ws4-arm-{VARIANT.lower()}', description: 'WS-4 arm {VARIANT}: 3-stage pipeline, <=3 tasks concurrent', phases: [ {{ title: 'Arm{VARIANT}' }} ] }}")
parts.append(f'const VARIANT = {J(VARIANT)}')
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

// VARIANT is set at generation time: 'C' (full firm: real persona agentTypes) or 'C2' (ablated: neutral roles, no personas)
async function runTask(tid, txt) {
  const base = ARM_PROMPT + "\\n---BEGIN TASK---\\n" + txt + "\\n---END TASK---\\n"
  const full = VARIANT === 'C'
  const o1 = full ? { agentType: 'quant-head-arjun-rao' } : {}
  const o2 = full ? { agentType: 'red-team-nikhil-bose' } : {}
  const o3 = full ? { agentType: 'cio-rajan-mehta' } : {}
  const p1 = full ? "Review this submission in your capacity as Head of Quant.\\n" : "You are an experienced quantitative code and results reviewer.\\n"
  const p2 = full ? "Red-team this: attack BOTH the submission AND the prior reviewer's findings — refute weak claims, find what was missed, flag invented defects.\\n" : "You are a skeptical second reviewer instructed to refute: attack BOTH the submission AND the prior reviewer's findings — refute weak claims, find what was missed, flag invented defects.\\n"
  const p3 = full ? "As CIO, issue the consolidated verdict after the two reviews below. Keep only defects that survive; obey the answer rules verbatim.\\n" : "You are the final arbiter consolidating two reviews below into one verdict. Keep only defects that survive; obey the answer rules verbatim.\\n"
  const r1 = await agent(p1 + base + NOFILES, { label: VARIANT + '1rev:' + tid, phase: 'Arm' + VARIANT, schema: OUT, ...o1 })
  const r2 = await agent(p2 + base + "\\n---PRIOR REVIEWER FINDINGS---\\n" + (r1 ? r1.answer : '(reviewer unavailable)') + "\\n---END PRIOR---\\n" + NOFILES, { label: VARIANT + '2red:' + tid, phase: 'Arm' + VARIANT, schema: OUT, ...o2 })
  const r3 = await agent(p3 + base + "\\n---REVIEWER---\\n" + (r1 ? r1.answer : '') + "\\n---RED TEAM---\\n" + (r2 ? r2.answer : '') + "\\n---END---\\n" + NOFILES.replace('Return {answer: <your full review>}', 'Write your COMPLETE consolidated final answer to ' + RES + '/' + tid + '_arm' + VARIANT + '.md and return {saved: "ok"}'), { label: VARIANT + '3syn:' + tid, phase: 'Arm' + VARIANT, schema: SAVED, ...o3 })
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
js_path = BAT / "results" / RUN_ID / f"ws4_arm_{VARIANT.lower()}.js"
js_path.write_bytes(("\n".join(parts)).encode("utf-8").replace(b"\r\n", b"\n").replace(b"\r", b""))
print("arm-C workflow:", js_path, "| tasks:", len(tasks))
