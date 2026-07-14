"""Build web-chat packets. Usage: python build_web_packet.py [full|grid|battery] [model_hint]
Contains NO answer key / rubric (runner stays blind). Battery-only packet = one model's single-call
defect column (arm A). Skips nothing (the web account is a fresh model)."""
import sys
from pathlib import Path

SSP = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\SYSTEM_SCIENCE_PROGRAM")
MG, BAT = SSP / "MODEL_GRID", SSP / "ws4_battery"
part = sys.argv[1] if len(sys.argv) > 1 else "full"
hint = sys.argv[2] if len(sys.argv) > 2 else ""
ARM_PROMPT = (BAT / "PROTOCOL.md").read_text(encoding="utf-8").split("```")[1].strip()
mg = [(f"MG{i:02d}", (MG / f"MG{i:02d}.md").read_text(encoding="utf-8").strip()) for i in range(1, 9)]
bat = [(f"T{i:02d}", (BAT / f"T{i:02d}" / "task.md").read_text(encoding="utf-8").strip()) for i in range(1, 21)]

P = [f"# WEB PACKET ({part.upper()}{' — ' + hint if hint else ''}) — Firm S benchmark"]
P += ["", "## Steps", f"1. Select the model{' — set it to ' + hint if hint else ''}. Note exact name/version.",
      "2. Turn OFF web-search/tools if possible (we want the raw model).",
      "3. Best: one FRESH chat per task (no cross-task priming). Fallback: one chat per part (tell me if so).",
      "4. Save each reply under its `===== TASKID =====` line into ONE .md/.txt file. Answer each task ONCE.",
      "5. Send the file back. Do NOT edit answers, do NOT hint what's being tested.", ""]
if part in ("full", "grid"):
    P += ["=" * 60, "# PART A — Capability grid (8 tasks)", ""]
    for tid, txt in mg:
        P += [f"===== {tid} =====", txt, ""]
if part in ("full", "battery"):
    P += ["=" * 60, "# PART B — Defect-review battery (20 tasks)",
          "Prepend this EXACT prompt to every T task, then the task text:", "",
          "--- STANDARD REVIEW PROMPT ---", ARM_PROMPT, "--- END ---", ""]
    for tid, txt in bat:
        P += [f"===== {tid} =====", txt, ""]
P += ["=" * 60, "# OUTPUT: first line `MODEL: <name>  TOOLS: off/on  MODE: fresh-per-task/one-chat`, then the ===== TASKID ===== blocks with answers."]

name = {"full": "WEB_RUN_PACKET", "grid": "WEB_PACKET_GRID", "battery": "WEB_PACKET_BATTERY"}[part]
if hint:
    name += "_" + hint.upper()
out = SSP / f"{name}.md"
out.write_bytes(("\n".join(P)).encode("utf-8").replace(b"\r\n", b"\n"))
print(f"{out.name}: part={part} hint={hint} ({sum(1 for l in P if l.startswith('====='))} task blocks)")
