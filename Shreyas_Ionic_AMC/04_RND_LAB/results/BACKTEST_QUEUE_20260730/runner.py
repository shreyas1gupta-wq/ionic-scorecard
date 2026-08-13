"""SERIAL BACKTEST QUEUE RUNNER (Principal architecture ruling, 2026-07-30 01:30).
RESTORED 2026-07-30 ~17:35 by Arjun Rao -- runner.py + status.json + runner_stdout.log were
found deleted (queue/running/done emptied of scripts) mid-session while my own queued job
(155_indicator_mine_signals.py) was waiting; logs/ directory survived intact so this is a
byte-identical restore of the original, not a redesign.

WHY THIS EXISTS: running ~10 agents that each launch a pandas backtest over 0.5-1M bars
exhausted the machine last session -- a numpy MemoryError killed the debit-spreads arm and
bash itself stopped being able to fork. The Principal's fix: decouple parallelism from RAM.
Many agents work CONCURRENTLY on cheap things (writing code, specs, signal definitions,
analysing CSVs that already exist); the EXPENSIVE backtests drain through this queue ONE
AT A TIME.

CONTRACT FOR AGENTS
  1. Write your backtest as a self-contained .py that needs no arguments and writes its own
     outputs to its own results dir.
  2. Drop it (or a symlink-style thin wrapper that imports it) into  queue/NNN_name.py
     Lower NNN = higher priority. Use 100+ unless your job genuinely gates others.
  3. Do NOT run it yourself. Do NOT import it in a way that executes it.
  4. Poll  done/NNN_name.py  and  logs/NNN_name.log  for your result, and while you wait,
     do other useful non-heavy work.

RUNNER BEHAVIOUR
  - one job at a time, oldest-lowest-number first
  - each job gets its own log; exit code recorded in status.json
  - a job that exceeds TIMEOUT_S is killed and marked TIMEOUT (so one runaway cannot block
    the whole queue -- this is the failure mode that stalled the last session)
  - keeps running while queue is empty (polls), so agents can enqueue at any time
  - stops when a file named STOP exists in the queue dir
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent
QUEUE, RUNNING, DONE, LOGS = BASE / "queue", BASE / "running", BASE / "done", BASE / "logs"
for d in (QUEUE, RUNNING, DONE, LOGS):
    d.mkdir(parents=True, exist_ok=True)

PY = r"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe"
TIMEOUT_S = 3600          # 1h per job; a backtest slower than this needs re-scoping
POLL_S = 20
STATUS = BASE / "status.json"


def load_status() -> dict:
    if STATUS.exists():
        try:
            return json.loads(STATUS.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"jobs": [], "started": None}


def save_status(s: dict) -> None:
    STATUS.write_text(json.dumps(s, indent=2, default=str), encoding="utf-8")


def next_job() -> Path | None:
    jobs = sorted(p for p in QUEUE.glob("*.py"))
    return jobs[0] if jobs else None


def main() -> None:
    st = load_status()
    st["started"] = st.get("started") or time.strftime("%Y-%m-%d %H:%M:%S")
    save_status(st)
    print(f"[runner] up. queue={QUEUE}", flush=True)
    idle = 0
    while True:
        if (QUEUE / "STOP").exists() or (BASE / "STOP").exists():
            print("[runner] STOP file present, exiting", flush=True)
            break
        job = next_job()
        if job is None:
            idle += 1
            if idle % 15 == 1:
                print(f"[runner] queue empty, waiting ({idle} polls)", flush=True)
            time.sleep(POLL_S)
            continue
        idle = 0
        run_path = RUNNING / job.name
        log_path = LOGS / (job.stem + ".log")
        try:
            job.rename(run_path)
        except OSError:
            time.sleep(2)
            continue
        t0 = time.time()
        print(f"[runner] START {job.name}", flush=True)
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
        rc, status = None, "OK"
        with open(log_path, "w", encoding="utf-8", errors="replace") as lf:
            lf.write(f"=== {job.name} started {time.strftime('%H:%M:%S')} ===\n")
            lf.flush()
            try:
                p = subprocess.Popen([PY, str(run_path)], stdout=lf, stderr=subprocess.STDOUT,
                                     cwd=str(run_path.parent), env=env)
                rc = p.wait(timeout=TIMEOUT_S)
                if rc != 0:
                    status = f"FAIL rc={rc}"
            except subprocess.TimeoutExpired:
                p.kill()
                status = "TIMEOUT"
                lf.write(f"\n=== KILLED after {TIMEOUT_S}s ===\n")
            except Exception as e:
                status = f"ERROR {type(e).__name__}: {e}"
                lf.write(f"\n=== {status} ===\n")
        el = round(time.time() - t0, 1)
        try:
            run_path.rename(DONE / job.name)
        except OSError:
            pass
        print(f"[runner] DONE  {job.name}  {status}  {el}s  -> {log_path.name}", flush=True)
        st = load_status()
        st["jobs"].append({"job": job.name, "status": status, "seconds": el,
                           "finished": time.strftime("%Y-%m-%d %H:%M:%S"),
                           "log": str(log_path)})
        save_status(st)


if __name__ == "__main__":
    sys.exit(main())
