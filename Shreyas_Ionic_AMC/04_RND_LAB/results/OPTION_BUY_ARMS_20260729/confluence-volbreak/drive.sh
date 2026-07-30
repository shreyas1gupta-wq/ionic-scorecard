#!/bin/sh
# One CONFIG per PROCESS: long multi-run processes segfaulted (exit 139) once peak memory
# accumulated across ~4 big expiry-scanning runs. Completed runs are cached to
# trades/*.csv and skipped on re-entry, so this loop is fully resumable and a crash
# costs at most one run.
cd "c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/results/OPTION_BUY_ARMS_20260729/confluence-volbreak" || exit 1
PY="C:/Users/Shreyas.1Gupta/AppData/Local/Python/pythoncore-3.14-64/python.exe"
export PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1

CELLS="$1"
CFGS="C1_ATM_hold1525 C2_ATM_tgt50_stp30 C3_ITM2_hold1525 C4_ATM_0dte_hold1525"

for cell in $(echo "$CELLS" | tr ',' ' '); do
  for cfg in $CFGS; do
    for attempt in 1 2; do
      echo "=== $cell / $cfg (attempt $attempt) ==="
      "$PY" run_option_arms.py "$cell" "res_${cell}__${cfg}" "$cfg" 2>&1 | grep -Ev '^\[chain\]'
      rc=$?
      if [ $rc -eq 0 ]; then break; fi
      echo "!!! rc=$rc, retrying (cache makes this cheap)"
    done
  done
done
echo "ALL DONE"
