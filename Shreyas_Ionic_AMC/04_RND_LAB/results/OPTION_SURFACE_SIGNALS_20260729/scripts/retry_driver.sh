#!/bin/bash
OUT="/c/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/results/OPTION_SURFACE_SIGNALS_20260729"
PY="/c/Users/Shreyas.1Gupta/AppData/Local/Python/pythoncore-3.14-64/python.exe"
cd "$OUT/scripts"
attempt=0
while [ ! -f "$OUT/panel_raw.parquet" ] && [ $attempt -lt 25 ]; do
  attempt=$((attempt+1))
  echo "=== attempt $attempt at $(date) ===" >> run_stdout.log
  PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 "$PY" build_panel.py >> run_stdout.log 2>&1
  rc=$?
  echo "=== attempt $attempt exited rc=$rc ===" >> run_stdout.log
  if [ -f "$OUT/panel_raw.parquet" ]; then
    echo "SUCCESS after $attempt attempts" >> run_stdout.log
    break
  fi
  sleep 5
done
