"""Comprehensive news downloader: finish mveen3 + TOI + long-history (15-20yr) datasets.
Uses chunked retry for corporate proxy compatibility.

Datasets:
1. mveen3 Indian stock news (remaining files: ~2.2GB)
2. TOI Headlines 2001-2023 (3.3M headlines, ~260MB)
3. Million News Headlines 2003-2021 (1.2M Australian ABC, ~60MB)
4. BBC News alltime (global by month, ~280MB)
5. HuffPost News Category 2012-2022 (210k articles, ~83MB)
6. GDELT Events (global geopolitical, decades)
"""
import os, sys, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import truststore; truststore.inject_into_ssl()
import requests

TOKEN   = os.environ.get("HF_TOKEN", "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")
ROOT    = Path(__file__).resolve().parents[2]
SEGMENT = 80 * 1024 * 1024
READ_SZ = 4 * 1024 * 1024
MAX_RETRY = 20
WORKERS = 4
lock = threading.Lock()

JOBS = [
    # === mveen3 remaining files ===
    ("mveen3/Six_Year_Indian_Stock_Market_Dataset-News_and_Ticker",
     "dataset/tier_segregated_news.csv",
     ROOT / "datasets" / "india_fin_news"),
    ("mveen3/Six_Year_Indian_Stock_Market_Dataset-News_and_Ticker",
     "dataset/processed_news_dataset.csv",
     ROOT / "datasets" / "india_fin_news"),
    ("mveen3/Six_Year_Indian_Stock_Market_Dataset-News_and_Ticker",
     "dataset/tft_ready.csv",
     ROOT / "datasets" / "india_fin_news"),
    ("mveen3/Six_Year_Indian_Stock_Market_Dataset-News_and_Ticker",
     "dataset/news_sentiment.csv",
     ROOT / "datasets" / "india_fin_news"),
    ("mveen3/Six_Year_Indian_Stock_Market_Dataset-News_and_Ticker",
     "dataset/stock_dataset/nifty50_ticker.csv",
     ROOT / "datasets" / "india_fin_news"),

    # === Million News Headlines (Australian ABC, 2003-2021, 1.2M headlines) ===
    ("DeveloperOats/Million_News_Headlines",
     "News_dataset.csv",
     ROOT / "datasets" / "million_headlines"),

    # === HuffPost News Category (2012-2022, 210k articles) ===
    ("heegyu/news-category-dataset",
     "News_Category_Dataset_v3.json",
     ROOT / "datasets" / "huffpost_news"),
]

# BBC News alltime — monthly parquet files, need to enumerate
BBC_REPO = "RealTimeData/bbc_news_alltime"
BBC_DEST = ROOT / "datasets" / "bbc_news_alltime"

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
        total = int(r.headers.get("content-length", 0))
    except Exception as e:
        log(f"  HEAD FAIL {fname}: {e}")
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
                        ConnectionResetError) as e:
                    wait = min(3 * (attempt + 1), 15)
                    log(f"  RETRY {fname.split('/')[-1]} {pos/1e6:.0f}MB att {attempt+1} {wait}s")
                    f.flush()
                    pos = local.stat().st_size
                    seg_hdrs["Range"] = f"bytes={pos}-{end}"
                    time.sleep(wait)
            else:
                log(f"  FAILED {fname} at {pos/1e6:.0f}MB after {MAX_RETRY} retries")
                return fname, pos

    avg = (local.stat().st_size - existing) / max(time.time() - t0, 1) / 1e6
    log(f"  DONE  {fname.split('/')[-1]}  {local.stat().st_size/1e6:.0f}MB  avg {avg:.1f}MB/s")
    return fname, local.stat().st_size


def get_bbc_files():
    """Enumerate BBC news monthly parquet files."""
    from huggingface_hub import HfApi
    api = HfApi(token=TOKEN)
    try:
        info = api.repo_info(BBC_REPO, repo_type="dataset", files_metadata=True)
        files = [s.rfilename for s in (info.siblings or [])
                 if s.rfilename.endswith('.parquet') or s.rfilename.endswith('.csv')]
        return files
    except Exception as e:
        log(f"  BBC enumerate failed: {e}")
        return []


print("=" * 60)
print("COMPREHENSIVE NEWS DOWNLOADER")
print("=" * 60)
print(f"Token: {'SET' if TOKEN else 'NOT SET'}  Workers: {WORKERS}")
print(f"Root: {ROOT}\n")

# Phase 1: main jobs (mveen3 remaining + Million Headlines + HuffPost)
print("--- PHASE 1: Direct file downloads ---")
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {ex.submit(download_file, repo, fn, dest): fn
            for repo, fn, dest in JOBS}
    for fut in as_completed(futs):
        try:
            fut.result()
        except Exception as e:
            log(f"  ERROR: {e}")

# Phase 2: BBC News alltime (enumerate then download)
print("\n--- PHASE 2: BBC News alltime ---")
bbc_files = get_bbc_files()
if bbc_files:
    log(f"  Found {len(bbc_files)} BBC news files")
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(download_file, BBC_REPO, fn, BBC_DEST): fn
                for fn in bbc_files}
        for fut in as_completed(futs):
            try:
                fut.result()
            except Exception as e:
                log(f"  ERROR: {e}")

# Phase 3: TOI Headlines via datasets lib
print("\n--- PHASE 3: TOI Headlines (2001-2023) ---")
toi_dest = ROOT / "datasets" / "toi_headlines"
toi_file = toi_dest / "toi_headlines.parquet"
if toi_file.exists() and toi_file.stat().st_size > 1000:
    print(f"  SKIP  toi_headlines.parquet already exists ({toi_file.stat().st_size/1e6:.0f}MB)")
else:
    try:
        from datasets import load_dataset
        ds = load_dataset("community-datasets/times_of_india_news_headlines", split="train")
        toi_dest.mkdir(parents=True, exist_ok=True)
        ds.to_parquet(str(toi_file))
        print(f"  TOI: {len(ds)} headlines -> {toi_file}")
    except Exception as e:
        print(f"  TOI download failed: {e}")

# Phase 4: GDELT — try to get the events file
print("\n--- PHASE 4: GDELT Events ---")
gdelt_targets = [
    ("DescribeEvents/gdelt_news_events", None, ROOT / "datasets" / "gdelt_events"),
]
for repo, _, dest in gdelt_targets:
    try:
        from huggingface_hub import HfApi
        api = HfApi(token=TOKEN)
        info = api.repo_info(repo, repo_type="dataset", files_metadata=True)
        files = [s.rfilename for s in (info.siblings or [])
                 if s.rfilename.endswith(('.parquet', '.csv', '.json', '.jsonl'))]
        tot = sum((s.size or 0) for s in (info.siblings or [])
                  if s.rfilename.endswith(('.parquet', '.csv', '.json', '.jsonl')))
        log(f"  GDELT: {len(files)} data files, {tot/1e6:.0f}MB total")
        if tot < 2000 * 1e6:  # only download if under 2GB
            with ThreadPoolExecutor(max_workers=WORKERS) as ex:
                futs = {ex.submit(download_file, repo, fn, dest): fn
                        for fn in files}
                for fut in as_completed(futs):
                    try:
                        fut.result()
                    except Exception as e:
                        log(f"  ERROR: {e}")
        else:
            log(f"  GDELT too large ({tot/1e6:.0f}MB), skipping bulk download")
    except Exception as e:
        log(f"  GDELT failed: {e}")

# === TALLY ===
print("\n" + "=" * 60)
print("DATASET TALLY")
print("=" * 60)
for name in ["india_fin_news", "moneycontrol_news", "toi_headlines",
             "million_headlines", "bbc_news_alltime", "huffpost_news",
             "gdelt_events", "yahoo_finance", "forex_daily",
             "nifty50_weights", "us_fin_news", "reddit_sp500"]:
    d = ROOT / "datasets" / name
    if d.exists():
        files = [f for f in d.rglob("*") if f.is_file()]
        sz = sum(f.stat().st_size for f in files)
        print(f"  {name:25s}: {len(files):3d} files  {sz/1e6:8.0f}MB")
    else:
        print(f"  {name:25s}: NOT DOWNLOADED")

print("\nDone.")
