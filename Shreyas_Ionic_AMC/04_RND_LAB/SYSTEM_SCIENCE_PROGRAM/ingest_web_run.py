"""Ingest a web-account run file (Principal pastes/saves the model's replies).
Splits on '===== TASKID =====', writes one answer file per task into the right results dir so the
existing objective grader + blind judge pipeline picks them up unchanged.
Usage: python ingest_web_run.py <path_to_web_output_file> <model_label>
  MG?? answers  -> MODEL_GRID/results/<TID>_<model_label>.md
  T?? answers   -> ws4_battery/results/webrun_<model_label>/raw/<TID>_armA.md  (single-call = arm A)
"""
import re, sys
from pathlib import Path

SSP = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\SYSTEM_SCIENCE_PROGRAM")
src = Path(sys.argv[1])
model = re.sub(r"[^a-z0-9]+", "", sys.argv[2].lower()) or "webmodel"
text = src.read_text(encoding="utf-8", errors="replace")

blocks = re.split(r"^=+\s*(MG\d\d|T\d\d)\s*=+\s*$", text, flags=re.M)
# blocks = [preamble, TID, body, TID, body, ...]
pairs = list(zip(blocks[1::2], blocks[2::2]))
if not pairs:
    print("NO DELIMITED BLOCKS FOUND. Expected lines like '===== MG01 ====='. Nothing written."); sys.exit(1)

mg_dir = SSP / "MODEL_GRID" / "results"
bat_dir = SSP / "ws4_battery" / "results" / f"webrun_{model}" / "raw"
bat_dir.mkdir(parents=True, exist_ok=True)
n_mg = n_bat = 0
for tid, body in pairs:
    body = body.strip()
    if len(body) < 20:
        print(f"  WARN {tid}: body <20 chars, skipping (empty answer?)"); continue
    if tid.startswith("MG"):
        (mg_dir / f"{tid}_{model}.md").write_text(body, encoding="utf-8"); n_mg += 1
    else:
        (bat_dir / f"{tid}_armA.md").write_text(body, encoding="utf-8"); n_bat += 1
print(f"ingested MG:{n_mg}  battery:{n_bat}  (model label '{model}')")
print(f"MG grid answers -> {mg_dir} (run mg_objective_grade.py + judge)")
if n_bat:
    print(f"battery single-call answers -> {bat_dir} (this is arm A for model '{model}'; scrub/seal + grade)")
