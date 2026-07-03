"""Chunked retry downloader — handles corporate proxy connection resets.
Downloads each file in 50MB segments, retrying on ConnectionResetError.
Resumes from exact byte if interrupted. Run again to resume.
"""
import os, sys, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import truststore; truststore.inject_into_ssl()
import requests

TOKEN   = os.environ.get("HF_TOKEN", "")
DEST    = Path(__file__).resolve().parents[2] / "swing_momentum" / "data" / "hf_stock_minute"
DEST.mkdir(parents=True, exist_ok=True)

REPO    = "Saintforest/indian-stock-market-minute-data"
FILES   = [
    ("minute/train-00000.parquet", 1446_318_994),
    ("minute/train-00001.parquet", 1468_538_266),
    ("minute/train-00002.parquet", 1432_671_044),
    ("minute/train-00003.parquet", 1405_952_100),
    ("minute/train-00004.parquet", 1574_050_884),
    ("minute/train-00005.parquet", 1427_750_350),
    ("minute/train-00006.parquet", 1443_519_756),
    ("minute/train-00007.parquet",  193_417_256),
    ("day/train-00000.parquet",     117_731_670),
]
WORKERS   = 6       # parallel files
SEGMENT   = 80 * 1024 * 1024   # 80MB per HTTP request (proxy resets ~150MB)
READ_SZ   = 4 * 1024 * 1024    # 4MB read buffer
MAX_RETRY = 20      # retries per segment
lock = threading.Lock()

def log(msg):
    with lock:
        print(msg, flush=True)

def hf_url(fname):
    return (f"https://huggingface.co/datasets/{REPO}"
            f"/resolve/main/{fname}?download=true")

def download_file(fname, expected_size):
    dest = DEST / fname
    dest.parent.mkdir(parents=True, exist_ok=True)
    url  = hf_url(fname)
    hdrs = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

    existing = dest.stat().st_size if dest.exists() else 0
    if existing >= expected_size:
        log(f"  SKIP   {fname}  ({existing/1e6:.0f}MB complete)")
        return fname, existing

    if existing:
        log(f"  RESUME {fname} from {existing/1e6:.0f}MB / {expected_size/1e6:.0f}MB")
    else:
        log(f"  START  {fname}  ({expected_size/1e6:.0f}MB)")

    pos = existing
    t0  = time.time()

    with open(dest, "ab" if existing else "wb") as f:
        while pos < expected_size:
            end  = min(pos + SEGMENT - 1, expected_size - 1)
            seg_hdrs = dict(hdrs)
            seg_hdrs["Range"] = f"bytes={pos}-{end}"

            for attempt in range(MAX_RETRY):
                try:
                    r = requests.get(url, headers=seg_hdrs, stream=True, timeout=60)
                    r.raise_for_status()
                    written = 0
                    for chunk in r.iter_content(READ_SZ):
                        if chunk:
                            f.write(chunk)
                            written += len(chunk)
                    pos += written
                    elapsed = time.time() - t0
                    mbps = (pos - existing) / elapsed / 1e6 if elapsed > 0 else 0
                    pct  = pos / expected_size * 100
                    log(f"  {fname.split('/')[-1]}  {pct:5.1f}%  {pos/1e6:7.0f}MB  {mbps:.1f}MB/s")
                    break
                except (requests.exceptions.ConnectionError,
                        requests.exceptions.ChunkedEncodingError,
                        ConnectionResetError) as e:
                    wait = min(3 * (attempt + 1), 15)
                    log(f"  RETRY  {fname}  seg {pos/1e6:.0f}MB  attempt {attempt+1}  ({type(e).__name__}) wait {wait}s")
                    # reopen to get current position
                    f.flush()
                    pos = dest.stat().st_size
                    seg_hdrs["Range"] = f"bytes={pos}-{end}"
                    time.sleep(wait)
            else:
                log(f"  FAILED {fname} at {pos/1e6:.0f}MB after {MAX_RETRY} retries")
                return fname, pos

    total_t = time.time() - t0
    avg = (dest.stat().st_size - existing) / total_t / 1e6
    log(f"  DONE   {fname}  {dest.stat().st_size/1e6:.0f}MB  avg {avg:.1f}MB/s")
    return fname, dest.stat().st_size

print(f"Chunked retry downloader — {REPO}")
print(f"Token: {'SET' if TOKEN else 'NOT SET'}  Workers: {WORKERS}  Segment: {SEGMENT//1024//1024}MB")
print(f"Dest : {DEST}\n")

with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {ex.submit(download_file, fn, sz): fn for fn, sz in FILES}
    for fut in as_completed(futs):
        fn = futs[fut]
        try:
            _, final_sz = fut.result()
        except Exception as e:
            log(f"  ERROR {fn}: {e}")

done = list(DEST.rglob("*.parquet"))
total = sum(f.stat().st_size for f in done)
print(f"\nFinal: {len(done)} parquet files, {total/1e9:.2f} GB")
