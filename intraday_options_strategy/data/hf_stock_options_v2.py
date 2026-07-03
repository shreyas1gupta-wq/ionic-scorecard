"""Download stock options parquets from HF. v2: per-file logging, 2 workers, robust retry."""
import os, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import truststore; truststore.inject_into_ssl()
import requests
from huggingface_hub import HfApi

TOKEN = "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"
ROOT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
DEST = ROOT / "intraday_options_strategy" / "datasets" / "raw" / "hf_index_options_1m"
REPO = "thetrademarkk/india-index-options-1m"
SEGMENT = 80 * 1024 * 1024
READ_SZ = 4 * 1024 * 1024
MAX_RETRY = 10
WORKERS = 2
lock = threading.Lock()
stats = {"done": 0, "skip": 0, "fail": 0, "total": 0, "bytes": 0}

def log(msg):
    with lock:
        print(msg, flush=True)

def download_file(fname):
    short = fname.split("/")[-1]
    local = DEST / fname
    local.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://huggingface.co/datasets/{REPO}/resolve/main/{fname}?download=true"
    hdrs = {"Authorization": f"Bearer {TOKEN}"}

    for head_try in range(3):
        try:
            r = requests.head(url, headers=hdrs, allow_redirects=True, timeout=30)
            total = int(r.headers.get("content-length", 0))
            break
        except Exception as e:
            if head_try == 2:
                log(f"  FAIL HEAD {short}: {e}")
                with lock: stats["fail"] += 1
                return
            time.sleep(3)

    existing = local.stat().st_size if local.exists() else 0
    if existing >= total and total > 0:
        with lock:
            stats["skip"] += 1
            n = stats["skip"] + stats["done"]
            if n % 100 == 0:
                log(f"  [{n}/{stats['total']}] skip={stats['skip']} done={stats['done']} fail={stats['fail']}")
        return

    pos = existing
    with open(local, "ab" if existing else "wb") as f:
        while pos < total:
            end = min(pos + SEGMENT - 1, total - 1)
            seg_hdrs = dict(hdrs, Range=f"bytes={pos}-{end}")
            for attempt in range(MAX_RETRY):
                try:
                    r = requests.get(url, headers=seg_hdrs, stream=True, timeout=120)
                    r.raise_for_status()
                    for chunk in r.iter_content(READ_SZ):
                        if chunk:
                            f.write(chunk)
                            pos += len(chunk)
                    break
                except Exception as e:
                    wait = min(3 * (attempt + 1), 15)
                    log(f"  RETRY {short} att {attempt+1}: {type(e).__name__}")
                    f.flush()
                    pos = local.stat().st_size
                    time.sleep(wait)
            else:
                log(f"  FAILED {short} after {MAX_RETRY} retries")
                with lock: stats["fail"] += 1
                return

    with lock:
        stats["done"] += 1
        stats["bytes"] += total
        n = stats["skip"] + stats["done"]
        if stats["done"] % 10 == 0 or n % 100 == 0:
            log(f"  [{n}/{stats['total']}] done={stats['done']} ({stats['bytes']/1e6:.0f}MB) skip={stats['skip']} fail={stats['fail']}")

print("Stock Options Downloader v2")
print("Enumerating files from HF...")
api = HfApi(token=TOKEN)
info = api.repo_info(REPO, repo_type="dataset", files_metadata=True)
all_files = [s.rfilename for s in info.siblings
             if s.rfilename.endswith('.parquet')
             and s.rfilename.startswith('stocks_options/')]

stats["total"] = len(all_files)
print(f"Found {len(all_files)} stock options files")
print(f"Workers: {WORKERS}")

existing_count = sum(1 for f in all_files if (DEST / f).exists() and (DEST / f).stat().st_size > 0)
print(f"Already on disk: {existing_count}")
print(f"To download: ~{len(all_files) - existing_count}\n")

t0 = time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = [ex.submit(download_file, f) for f in all_files]
    for fut in as_completed(futs):
        try:
            fut.result()
        except Exception as e:
            log(f"  EXCEPTION: {e}")

elapsed = time.time() - t0
print(f"\nDone in {elapsed:.0f}s ({elapsed/60:.1f}min)")
print(f"  Downloaded: {stats['done']} ({stats['bytes']/1e6:.0f}MB)")
print(f"  Skipped:    {stats['skip']}")
print(f"  Failed:     {stats['fail']}")

so_files = list((DEST / "stocks_options").rglob("*.parquet"))
print(f"\nOn disk: {len(so_files)} stock options parquets")
print(f"Expected: {len(all_files)}")
print(f"Match: {'YES' if len(so_files) >= len(all_files) else 'NO - ' + str(len(all_files) - len(so_files)) + ' missing'}")
