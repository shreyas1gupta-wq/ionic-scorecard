"""Build a self-contained WEB_RUN_PACKET.md the Principal pastes into a web-chat account (any model).
Produces downloadable model answers he sends back; we parse on delimiters, grade blind, fold into the paper.
Contains NO answer key / rubric / _verify (integrity: the runner must stay blind)."""
import re
from pathlib import Path

SSP = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\SYSTEM_SCIENCE_PROGRAM")
MG = SSP / "MODEL_GRID"
BAT = SSP / "ws4_battery"

ARM_PROMPT = (BAT / "PROTOCOL.md").read_text(encoding="utf-8").split("```")[1].strip()

mg = [(f"MG{i:02d}", (MG / f"MG{i:02d}.md").read_text(encoding="utf-8").strip()) for i in range(1, 9)]
bat = [(f"T{i:02d}", (BAT / f"T{i:02d}" / "task.md").read_text(encoding="utf-8").strip()) for i in range(1, 21)]

P = []
P.append("# WEB RUN PACKET — Firm S model benchmark (paste into your web-chat account)")
P.append("")
P.append("## What to do (5 steps)")
P.append("1. **Pick the model** in your web account (Fable / Opus / Sonnet — or GPT-5.x / Gemini if this is a non-Claude account). WRITE DOWN the exact model name+version; I need it to label the column.")
P.append("2. **Turn OFF web-search / tools if you can** (we want the raw model, matching our no-tools arm). If they can't be turned off, tell me — I'll label the column 'with-tools'.")
P.append("3. **Best quality (recommended): one FRESH chat per task** — paste the ONE task block, save the reply, new chat, next task. This matches our protocol (no cross-task priming). *Faster fallback:* paste a whole PART in one chat — acceptable, but tell me you did that so I disclose 'shared-context' in the paper.")
P.append("4. **Save every reply** into ONE text/markdown file, keeping the `===== TASKID =====` line above each answer so I can split them. (Save it in the shared laptop folder as `SYSTEM_SCIENCE_PROGRAM/MODEL_GRID/results/web_<model>_<part>.md`, or just paste it back to me here.)")
P.append("5. Send it back. I parse it, grade blind against the sealed key, and drop the numbers into the paper + LinkedIn post.")
P.append("")
P.append("## Integrity rules (please respect — they are what makes this publishable)")
P.append("- Do NOT tell the model what we're testing, do NOT hint at defect counts, do NOT edit its answers.")
P.append("- Answer each task ONCE (no regenerate, no best-of). First reply is the datum.")
P.append("- This packet deliberately contains NO answer key. Please don't ask the model to 'check itself' against anything.")
P.append("")
P.append("=" * 70)
P.append("# PART A — Capability grid (8 tasks). PRIMARY: do this first; it's quick and high-value.")
P.append("Each MG task below is a complete, self-contained prompt. Paste the block under the delimiter (not the delimiter line itself) and save the reply beneath that same delimiter in your output file.")
P.append("")
for tid, txt in mg:
    P.append(f"===== {tid} =====")
    P.append(txt)
    P.append("")
P.append("=" * 70)
P.append("# PART B — Defect-review battery (20 tasks). OPTIONAL but gives a full extra column.")
P.append("For EACH task below, the instruction to give the model is the SAME standard review prompt, then the task text. Copy this exact prompt line, then the task block:")
P.append("")
P.append("--- STANDARD REVIEW PROMPT (prepend to every T task) ---")
P.append(ARM_PROMPT)
P.append("--- END STANDARD PROMPT ---")
P.append("")
for tid, txt in bat:
    P.append(f"===== {tid} =====")
    P.append(txt)
    P.append("")
P.append("=" * 70)
P.append("# OUTPUT FORMAT REMINDER")
P.append("Your saved file should look like:")
P.append("```")
P.append("MODEL: <exact model name/version>   TOOLS: off/on   MODE: fresh-chat-per-task / one-chat-per-part")
P.append("===== MG01 =====")
P.append("<the model's full answer>")
P.append("===== MG02 =====")
P.append("<...>")
P.append("```")
P.append("That's all I need. Thank you!")

out = SSP / "WEB_RUN_PACKET.md"
out.write_bytes(("\n".join(P)).encode("utf-8").replace(b"\r\n", b"\n"))
words = len("\n".join(P).split())
print(f"WEB_RUN_PACKET.md written: {len(P)} lines, ~{words} words, {len(mg)} MG + {len(bat)} battery tasks")
print("path:", out)
