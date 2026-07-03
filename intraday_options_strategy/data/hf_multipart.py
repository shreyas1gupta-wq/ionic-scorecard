"""Multi-part parallel downloader: splits each file into N parts downloaded
simultaneously, then assembles. Maximises bandwidth on a proxy that allows
multiple concurrent connections. Each part = ~150MB, 8 parts per file = 8
simultaneous connections per file (72 total across 9 files).
"""
import os, sys, threading, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import truststore; truststore.inject_into_ssl()
import requests

TOKEN      = os.environ.get("HF_TOKEN", "")
DEST       = Path(__file__).resolve().parents[2] / "swing_momentum" / "data" / "hf_stock_minute"
DEST.mkdir(parents=True, exist_ok=True)

REPO       = "Saintforest/indian-stock-market-minute-data"
FILES      = [
    ("minute/train-00000.parquet", 1_446_318_994),
    ("minute/train-00001.parquet", 1_468_538_266),
    ("minute/train-00002.parquet", 1_432_671_044),
    ("minute/train-00003.parquet", 1_405_952_100),
    ("minute/train-00004.parquet", 1_574_050_884),
    ("minute/train-00005.parquet", 1_427_750_350),
    ("minute/train-00006.parquet", 1_443_519_756),
    ("minute/train-00007.parquet",   193_417_256),
    ("day/train-00000.parquet",      117_731_670),
]
PARTS_PER_FILE = 8      # parallel connections per file
MAX_WORKERS    = 48     # total thread pool (8 files × 8 parts + headroom)
CHUNK_READ     = 4 * 1024 * 1024
MAX_RETRY      = 15

lock    = threading.Lock()
prog    = {}   # fname -> bytes done

def log(msg):
    with lock:
        print(msg, flush=True)

def hf_url(fname):
    return (f"https://huggingface.co/datasets/{REPO}"
            f"/resolve/main/{fname}?download=true")

def download_part(fname, part_path, start, end, total_size):
    """Download bytes [start, end] into part_path, resuming if partial."""
    url   = hf_url(fname)
    hdrs  = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
    existing = part_path.stat().st_size if part_path.exists() else 0
    part_size = end - start + 1

    if existing >= part_size:
        with lock:
            prog[fname] = prog.get(fname, 0) + existing
        return  # already done

    pos = start + existing
    for attempt in range(MAX_RETRY):
        try:
            h = dict(hdrs)
            h["Range"] = f"bytes={pos}-{end}"
            r = requests.get(url, headers=h, stream=True, timeout=60)
            r.raise_for_status()
            with open(part_path, "ab" if existing else "wb") as f:
                for chunk in r.iter_content(CHUNK_READ):
                    if chunk:
                        f.write(chunk)
                        existing += len(chunk)
                        pos = start + existing
                        with lock:
                            prog[fname] = prog.get(fname, 0) + len(chunk)
            return
        except Exception as e:
            wait = min(3 * (attempt + 1), 20)
            existing = part_path.stat().st_size if part_path.exists() else 0
            pos = start + existing
            log(f"  retry {part_path.name} @{pos//1e6:.0f}MB attempt {attempt+1} ({type(e).__name__}) wait {wait}s")
            time.sleep(wait)

def assemble(fname, dest, parts, total_size):
    log(f"  assembling {fname} ...")
    with open(dest, "wb") as out:
        for p in parts:
            out.write(p.read_bytes())
            p.unlink()
    # remove part dir if empty
    try: p.parent.rmdir()
    except: pass
    log(f"  DONE  {fname}  {dest.stat().st_size/1e6:.0f}MB")

def download_file(fname, total_size):
    dest = DEST / fname
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and dest.stat().st_size >= total_size:
        log(f"  SKIP  {fname}  already complete")
        return

    part_dir = DEST / (fname + ".parts")
    part_dir.mkdir(parents=True, exist_ok=True)

    part_size = (total_size + PARTS_PER_FILE - 1) // PARTS_PER_FILE
    parts = []
    part_specs = []
    for i in range(PARTS_PER_FILE):
        s = i * part_size
        e = min(s + part_size - 1, total_size - 1)
        if s > total_size - 1:
            break
        p = part_dir / f"part_{i:02d}"
        parts.append(p)
        part_specs.append((s, e, p))

    log(f"  START {fname}  {total_size/1e6:.0f}MB  {len(parts)} parts")
    prog[fname] = sum(p.stat().st_size if p.exists() else 0 for p in parts)

    # submit all parts to the shared thread pool (called from within executor)
    with ThreadPoolExecutor(max_workers=len(parts)) as inner:
        futs = [inner.submit(download_part, fname, p, s, e, total_size)
                for s, e, p in part_specs]
        t0 = time.time()
        done_set = set()
        while len(done_set) < len(futs):
            time.sleep(4)
            for i, f in enumerate(futs):
                if f.done() and i not in done_set:
                    done_set.add(i)
            elapsed = time.time() - t0
            total_done = sum(p.stat().st_size if p.exists() else 0 for p in parts)
            mbps = total_done / elapsed / 1e6 if elapsed > 0 else 0
            pct  = total_done / total_size * 100
            log(f"  {fname.split('/')[-1]}  {pct:5.1f}%  {total_done/1e6:7.0f}MB  {mbps:.1f}MB/s")
        for f in futs:
            f.result()  # raise any exceptions

    # check all parts complete
    all_done = all(p.exists() and p.stat().st_size >= (e - s + 1)
                   for (s, e, p) in part_specs)
    if all_done:
        assemble(fname, dest, parts, total_size)
    else:
        log(f"  WARNING {fname}: some parts incomplete, run again to resume")

print(f"Multi-part downloader  parts/file={PARTS_PER_FILE}  pool={MAX_WORKERS}")
print(f"Token: {'SET' if TOKEN else 'NOT SET'}  Dest: {DEST}\n")

# download all files; each spins its own inner pool
for fname, sz in FILES:
    download_file(fname, sz)

done  = list(DEST.rglob("*.parquet"))
total = sum(f.stat().st_size for f in done)
print(f"\nFinal: {len(done)} parquet files  {total/1e9:.2f} GB")
