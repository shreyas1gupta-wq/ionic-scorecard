"""Download remaining individual stock options (1-min) from HF.
~2219 files, ~3.5GB. Chunked retry for corporate proxy.
"""
import os, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import truststore; truststore.inject_into_ssl()
import requests
from huggingface_hub import HfApi

TOKEN = os.environ.get("HF_TOKEN", "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")
ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "intraday_options_strategy" / "datasets" / "raw" / "hf_index_options_1m"
REPO = "thetrademarkk/india-index-options-1m"
SEGMENT = 80 * 1024 * 1024
READ_SZ = 4 * 1024 * 1024
MAX_RETRY = 20
WORKERS = 6
lock = threading.Lock()
stats = {"done": 0, "skip": 0, "fail": 0, "total": 0}

def log(msg):
    with lock:
        print(msg, flush=True)

def hf_url(fname):
    return f"https://huggingface.co/datasets/{REPO}/resolve/main/{fname}?download=true"

def download_file(fname):
    local = DEST / fname
    local.parent.mkdir(parents=True, exist_ok=True)
    url = hf_url(fname)
    hdrs = {"Authorization": f"Bearer {TOKEN}"}

    try:
        r = requests.head(url, headers=hdrs, allow_redirects=True, timeout=30)
        total = int(r.headers.get("content-length", 0))
    except Exception as e:
        with lock: stats["fail"] += 1
        return

    existing = local.stat().st_size if local.exists() else 0
    if existing >= total and total > 0:
        with lock: stats["skip"] += 1
        return

    pos = existing
    with open(local, "ab" if existing else "wb") as f:
        while pos < total:
            end = min(pos + SEGMENT - 1, total - 1)
            seg_hdrs = dict(hdrs, Range=f"bytes={pos}-{end}")
            for attempt in range(MAX_RETRY):
                try:
                    r = requests.get(url, headers=seg_hdrs, stream=True, timeout=60)
                    r.raise_for_status()
                    for chunk in r.iter_content(READ_SZ):
                        if chunk:
                            f.write(chunk)
                            pos += len(chunk)
                    break
                except Exception:
                    wait = min(3 * (attempt + 1), 15)
                    f.flush()
                    pos = local.stat().st_size
                    time.sleep(wait)
            else:
                with lock: stats["fail"] += 1
                return

    with lock:
        stats["done"] += 1
        if stats["done"] % 50 == 0:
            log(f"  Progress: {stats['done']}/{stats['total']} done, {stats['skip']} skip, {stats['fail']} fail")

# Enumerate all files from HF
print("Enumerating stock options files from HF...")
api = HfApi(token=TOKEN)
info = api.repo_info(REPO, repo_type="dataset", files_metadata=True)
all_files = [s.rfilename for s in info.siblings
             if s.rfilename.endswith('.parquet')
             and s.rfilename.startswith('stocks_options/')]

stats["total"] = len(all_files)
print(f"Found {len(all_files)} stock options files to process")
print(f"Workers: {WORKERS}\n")

t0 = time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = [ex.submit(download_file, f) for f in all_files]
    for fut in as_completed(futs):
        try:
            fut.result()
        except Exception as e:
            log(f"  ERROR: {e}")

elapsed = time.time() - t0
print(f"\nDone in {elapsed:.0f}s")
print(f"  Downloaded: {stats['done']}")
print(f"  Skipped:    {stats['skip']}")
print(f"  Failed:     {stats['fail']}")

# Verify
so_files = list((DEST / "stocks_options").rglob("*.parquet"))
print(f"\nOn disk: {len(so_files)} stock options parquets")
print(f"Expected: {len(all_files)}")
print(f"Match: {'YES' if len(so_files) >= len(all_files) else 'NO — ' + str(len(all_files) - len(so_files)) + ' missing'}")
