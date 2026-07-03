"""Fix-up downloader for datasets that 404'd in hf_news_all.py + remaining ones.
Run AFTER hf_news_all.py finishes (or concurrently if proxy allows).
"""
import os, sys, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import truststore; truststore.inject_into_ssl()
import requests
from huggingface_hub import HfApi

TOKEN   = os.environ.get("HF_TOKEN", "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")
ROOT    = Path(__file__).resolve().parents[2]
SEGMENT = 80 * 1024 * 1024
READ_SZ = 4 * 1024 * 1024
MAX_RETRY = 20
WORKERS = 4
lock = threading.Lock()

def log(msg):
    with lock:
        print(msg, flush=True)

def hf_url(repo, fname):
    return (f"https://huggingface.co/datasets/{repo}"
            f"/resolve/main/{fname}?download=true")

def download_file(repo, fname, dest_dir):
    dest_dir.mkdir(parents=True, exist_ok=True)
    local = dest_dir / fname.split("/")[-1]
    url = hf_url(repo, fname)
    hdrs = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

    try:
        r = requests.head(url, headers=hdrs, allow_redirects=True, timeout=30)
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
    except Exception as e:
        log(f"  HEAD FAIL {repo}/{fname}: {e}")
        return fname, 0

    existing = local.stat().st_size if local.exists() else 0
    if existing >= total and total > 0:
        log(f"  SKIP  {fname.split('/')[-1]}  ({total/1e6:.0f}MB already)")
        return fname, existing

    if existing:
        log(f"  RESUME {fname.split('/')[-1]} {existing/1e6:.0f}/{total/1e6:.0f}MB")
    else:
        log(f"  START  {fname.split('/')[-1]}  ({total/1e6:.0f}MB)")

    pos = existing
    t0 = time.time()
    with open(local, "ab" if existing else "wb") as f:
        while pos < total:
            end = min(pos + SEGMENT - 1, total - 1)
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
                    pct = pos / total * 100 if total else 0
                    log(f"  {fname.split('/')[-1]}  {pct:5.1f}%  {pos/1e6:7.0f}MB  {mbps:.1f}MB/s")
                    break
                except (requests.exceptions.ConnectionError,
                        requests.exceptions.ChunkedEncodingError,
                        requests.exceptions.HTTPError,
                        ConnectionResetError) as e:
                    wait = min(3 * (attempt + 1), 15)
                    log(f"  RETRY {fname.split('/')[-1]} {pos/1e6:.0f}MB att {attempt+1} {wait}s")
                    f.flush()
                    pos = local.stat().st_size
                    seg_hdrs["Range"] = f"bytes={pos}-{end}"
                    time.sleep(wait)
            else:
                log(f"  FAILED {fname} at {pos/1e6:.0f}MB")
                return fname, pos

    avg = (local.stat().st_size - existing) / max(time.time() - t0, 1) / 1e6
    log(f"  DONE  {fname.split('/')[-1]}  {local.stat().st_size/1e6:.0f}MB  avg {avg:.1f}MB/s")
    return fname, local.stat().st_size


print("=" * 60)
print("NEWS FIX-UP DOWNLOADER")
print("=" * 60)

# === 1. Million News Headlines (correct filename) ===
print("\n--- Million News Headlines (Australian ABC, 2003-2021) ---")
download_file(
    "DeveloperOats/Million_News_Headlines",
    "abcnews-date-text.csv",
    ROOT / "datasets" / "million_headlines"
)

# === 2. HuffPost News Category — enumerate files first ===
print("\n--- HuffPost News Category (2012-2022) ---")
api = HfApi(token=TOKEN)
try:
    info = api.repo_info("heegyu/news-category-dataset", repo_type="dataset",
                         files_metadata=True)
    data_files = [s.rfilename for s in (info.siblings or [])
                  if s.rfilename.endswith(('.json', '.parquet', '.csv', '.jsonl'))]
    log(f"  Found files: {data_files}")
    for fn in data_files:
        download_file("heegyu/news-category-dataset", fn,
                       ROOT / "datasets" / "huffpost_news")
except Exception as e:
    log(f"  HuffPost enumerate failed: {e}")

# === 3. BBC News alltime — monthly parquet files ===
print("\n--- BBC News alltime (global, multi-year by month) ---")
try:
    info = api.repo_info("RealTimeData/bbc_news_alltime", repo_type="dataset",
                         files_metadata=True)
    bbc_files = [s.rfilename for s in (info.siblings or [])
                 if s.rfilename.endswith(('.parquet', '.csv'))]
    tot_sz = sum((s.size or 0) for s in (info.siblings or [])
                 if s.rfilename.endswith(('.parquet', '.csv')))
    log(f"  BBC: {len(bbc_files)} data files, {tot_sz/1e6:.0f}MB total")
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(download_file, "RealTimeData/bbc_news_alltime", fn,
                          ROOT / "datasets" / "bbc_news_alltime"): fn
                for fn in bbc_files}
        for fut in as_completed(futs):
            try:
                fut.result()
            except Exception as e:
                log(f"  ERROR: {e}")
except Exception as e:
    log(f"  BBC enumerate failed: {e}")

# === 4. TOI Headlines via datasets lib ===
print("\n--- TOI Headlines (2001-2023, 3.3M headlines) ---")
toi_file = ROOT / "datasets" / "toi_headlines" / "toi_headlines.parquet"
if toi_file.exists() and toi_file.stat().st_size > 1000:
    log(f"  SKIP  toi_headlines.parquet ({toi_file.stat().st_size/1e6:.0f}MB)")
else:
    try:
        from datasets import load_dataset
        ds = load_dataset("community-datasets/times_of_india_news_headlines",
                          split="train")
        toi_file.parent.mkdir(parents=True, exist_ok=True)
        ds.to_parquet(str(toi_file))
        log(f"  TOI: {len(ds)} headlines -> {toi_file}")
    except Exception as e:
        log(f"  TOI download failed: {e}")

# === TALLY ===
print("\n" + "=" * 60)
print("NEWS DATASET TALLY")
print("=" * 60)
for name in ["india_fin_news", "moneycontrol_news", "toi_headlines",
             "million_headlines", "bbc_news_alltime", "huffpost_news",
             "gdelt_events"]:
    d = ROOT / "datasets" / name
    if d.exists():
        files = [f for f in d.rglob("*") if f.is_file()]
        sz = sum(f.stat().st_size for f in files)
        print(f"  {name:25s}: {len(files):3d} files  {sz/1e6:8.0f}MB")
    else:
        print(f"  {name:25s}: NOT YET")

total_d = ROOT / "datasets"
if total_d.exists():
    all_files = [f for f in total_d.rglob("*") if f.is_file()]
    total_sz = sum(f.stat().st_size for f in all_files)
    print(f"\n  TOTAL: {len(all_files)} files, {total_sz/1e6:.0f}MB ({total_sz/1e9:.1f}GB)")

print("\nDone.")
