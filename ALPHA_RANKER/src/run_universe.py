"""One-command universe rebuild: consolidate -> all factor engines -> fusion.
Reusable each quarter after a data refresh. Runs each stage as a subprocess (isolated,
so one failure doesn't kill the rest). Prints a stage-by-stage status line.
"""
import os, subprocess, sys, time
PY = r"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe"
BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER"
STAGES = [
    ("consolidate",  r"src\lib\consolidate_screener.py"),
    ("technical",    r"src\factors\universe_technical.py"),
    ("fundamental",  r"src\factors\universe_fundamental.py"),
    ("forensic",     r"src\forensic\universe_forensic.py"),
    ("cascade",      r"src\cascade\universe_cascade.py"),
    ("fuse",         r"src\scoring\universe_combine.py"),
]
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
for name, rel in STAGES:
    path = os.path.join(BASE, rel)
    if not os.path.exists(path):
        print(f"[{name}] SKIP (missing {rel})"); continue
    t = time.time()
    r = subprocess.run([PY, path], env=env, capture_output=True, text=True)
    tail = (r.stdout or "").strip().splitlines()[-2:]
    status = "OK" if r.returncode == 0 else f"FAIL rc={r.returncode}"
    print(f"[{name}] {status} ({time.time()-t:.0f}s)  {' | '.join(tail)}")
    if r.returncode != 0:
        print((r.stderr or "")[-400:])
print("\nDONE -> results/universe_final_scores.csv")
