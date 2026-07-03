"""Resumable retry loop for the 1-min Kaggle dataset.

The corporate proxy resets long transfers; kagglehub resumes from the partial
.archive file, so repeated attempts make monotonic progress. Bounded attempts,
short backoff, copies to datasets/raw/kaggle/ on success.
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

import truststore

truststore.inject_into_ssl()

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402

import kagglehub  # noqa: E402  (after truststore injection)

DATASET = "debashis74017/nifty-50-minute-data"
MAX_ATTEMPTS = 60
BACKOFF_SEC = 5


def main() -> None:
    dest = RAW_DIR / "kaggle" / DATASET.replace("/", "__")
    if dest.exists():
        print(f"Already present: {dest}")
        return
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            path = kagglehub.dataset_download(DATASET)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(path, dest)
            files = sorted(p.name for p in dest.rglob("*") if p.is_file())
            print(f"SUCCESS on attempt {attempt}: {len(files)} files -> {dest}")
            print("\n".join(files[:40]))
            return
        except Exception as exc:  # noqa: BLE001 — proxy resets are expected; resume and go again
            print(f"[attempt {attempt}/{MAX_ATTEMPTS}] {type(exc).__name__}: {str(exc)[:160]}")
            time.sleep(BACKOFF_SEC)
    print("FAILED after all attempts — see PLAN.md fallback (kaggle.json or synthetic proxy).")


if __name__ == "__main__":
    main()
