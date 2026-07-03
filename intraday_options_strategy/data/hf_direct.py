"""Direct parallel HTTPS downloader for HF datasets — bypasses Xet/snapshot_download
which stalls through corporate proxies. Uses requests + Range headers for resume,
ThreadPoolExecutor for parallel files.
Usage:  python hf_direct.py
"""
import os, sys, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import truststore; truststore.inject_into_ssl()
import requests

TOKEN = os.environ.get("HF_TOKEN", "")
DEST  = Path(__file__).resolve().parents[2] / "swing_momentum" / "data" / "hf_stock_minute"
DEST.mkdir(parents=True, exist_ok=True)

REPO  = "Saintforest/indian-stock-market-minute-data"
FILES = [
    "minute/train-00000.parquet",
    "minute/train-00001.parquet",
    "minute/train-00002.parquet",
    "minute/train-00003.parquet",
    "minute/train-00004.parquet",
    "minute/train-00005.parquet",
    "minute/train-00006.parquet",
    "minute/train-00007.parquet",
    "day/train-00000.parquet",
]
WORKERS  = 4   # parallel files (more won't help if proxy is the bottleneck)
CHUNK_SZ = 8 * 1024 * 1024   # 8 MB read chunks

lock = threading.Lock()

def hf_url(fname):
    return f"https://huggingface.co/datasets/{REPO}/resolve/main/{fname}?download=true"

def download_file(fname):
    url   = hf_url(fname)
    dest  = DEST / fname
    dest.parent.mkdir(parents=True, exist_ok=True)

    headers = {}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    # check remote size
    r = requests.head(url, headers=headers, allow_redirects=True, timeout=30)
    total = int(r.headers.get("content-length", 0))

    # resume support
    existing = dest.stat().st_size if dest.exists() else 0
    if existing and existing == total:
        with lock:
            print(f"  SKIP  {fname}  ({total/1e6:.0f}MB already complete)", flush=True)
        return fname, total, True

    if existing:
        headers["Range"] = f"bytes={existing}-"
        mode = "ab"
        with lock:
            print(f"  RESUME {fname} from {existing/1e6:.0f}MB / {total/1e6:.0f}MB", flush=True)
    else:
        mode = "wb"
        with lock:
            print(f"  START  {fname}  ({total/1e6:.0f}MB)", flush=True)

    r = requests.get(url, headers=headers, stream=True, timeout=60)
    r.raise_for_status()

    downloaded = existing
    with open(dest, mode) as f:
        for chunk in r.iter_content(chunk_size=CHUNK_SZ):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)

    with lock:
        print(f"  DONE   {fname}  ({downloaded/1e6:.0f}MB)", flush=True)
    return fname, downloaded, False

def human(n):
    for u in ["B","KB","MB","GB"]:
        if n < 1024 or u == "GB": return f"{n:.1f}{u}"
        n /= 1024

print(f"HF direct downloader — {REPO}")
print(f"Token: {'SET' if TOKEN else 'NOT SET (unauthenticated)'}  Workers: {WORKERS}")
print(f"Dest : {DEST}\n")

with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futures = {ex.submit(download_file, f): f for f in FILES}
    for fut in as_completed(futures):
        fname = futures[fut]
        try:
            _, sz, skipped = fut.result()
        except Exception as e:
            print(f"  ERROR {fname}: {e}", flush=True)

# final tally
files = list(DEST.rglob("*.parquet"))
total_sz = sum(f.stat().st_size for f in files)
print(f"\nAll done: {len(files)} parquet files, {human(total_sz)}")
