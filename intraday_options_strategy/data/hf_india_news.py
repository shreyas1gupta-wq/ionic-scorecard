"""Download Indian financial news datasets from HuggingFace.
Uses chunked retry for proxy compatibility.
"""
import os, sys, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import truststore; truststore.inject_into_ssl()
import requests

TOKEN   = os.environ.get("HF_TOKEN", "")
ROOT    = Path(__file__).resolve().parents[2]
SEGMENT = 80 * 1024 * 1024
READ_SZ = 4 * 1024 * 1024
MAX_RETRY = 20
WORKERS = 4
lock = threading.Lock()

JOBS = [
    # Indian stock market news + sentiment (6yr, 2.8GB) — THE big one
    ("mveen3/Six_Year_Indian_Stock_Market_Dataset-News_and_Ticker",
     "dataset/tier_segregated_news.csv",
     ROOT / "datasets" / "india_fin_news"),
    ("mveen3/Six_Year_Indian_Stock_Market_Dataset-News_and_Ticker",
     "dataset/processed_news_dataset.csv",
     ROOT / "datasets" / "india_fin_news"),
    ("mveen3/Six_Year_Indian_Stock_Market_Dataset-News_and_Ticker",
     "dataset/news_sentiment.csv",
     ROOT / "datasets" / "india_fin_news"),
    ("mveen3/Six_Year_Indian_Stock_Market_Dataset-News_and_Ticker",
     "dataset/tft_ready.csv",
     ROOT / "datasets" / "india_fin_news"),
    ("mveen3/Six_Year_Indian_Stock_Market_Dataset-News_and_Ticker",
     "dataset/raw_dataset/moneycontrol_raw.csv",
     ROOT / "datasets" / "india_fin_news" / "raw"),
    ("mveen3/Six_Year_Indian_Stock_Market_Dataset-News_and_Ticker",
     "dataset/raw_dataset/economictimes_raw.csv",
     ROOT / "datasets" / "india_fin_news" / "raw"),
    ("mveen3/Six_Year_Indian_Stock_Market_Dataset-News_and_Ticker",
     "dataset/raw_dataset/financialexpress_raw.csv",
     ROOT / "datasets" / "india_fin_news" / "raw"),
    ("mveen3/Six_Year_Indian_Stock_Market_Dataset-News_and_Ticker",
     "dataset/raw_dataset/businessstandard_raw.csv",
     ROOT / "datasets" / "india_fin_news" / "raw"),

    # MoneyControl news (43MB, 29k articles with datetime)
    ("LogeshChandran/money_control_news",
     "data/train-00000-of-00001.parquet",
     ROOT / "datasets" / "moneycontrol_news"),

    # Times of India headlines (3.3M headlines, ~260MB via HF datasets lib)
    # This one uses HF datasets loader, not direct file — handle separately below
]

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
        log(f"  SKIP  {fname.split('/')[-1]}  ({total/1e6:.0f}MB)")
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
                log(f"  FAILED {fname} at {pos/1e6:.0f}MB")
                return fname, pos

    avg = (local.stat().st_size - existing) / max(time.time() - t0, 1) / 1e6
    log(f"  DONE  {fname.split('/')[-1]}  {local.stat().st_size/1e6:.0f}MB  avg {avg:.1f}MB/s")
    return fname, local.stat().st_size

print("Indian financial news downloader")
print(f"Token: {'SET' if TOKEN else 'NOT SET'}  Workers: {WORKERS}\n")

with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {ex.submit(download_file, repo, fn, dest): fn
            for repo, fn, dest in JOBS}
    for fut in as_completed(futs):
        try:
            fut.result()
        except Exception as e:
            log(f"  ERROR: {e}")

# TOI headlines via datasets lib (auto-download + cache)
print("\nDownloading Times of India headlines via datasets lib...")
try:
    from datasets import load_dataset
    ds = load_dataset("community-datasets/times_of_india_news_headlines", split="train")
    dest = ROOT / "datasets" / "toi_headlines"
    dest.mkdir(parents=True, exist_ok=True)
    ds.to_parquet(str(dest / "toi_headlines.parquet"))
    print(f"  TOI: {len(ds)} headlines -> {dest / 'toi_headlines.parquet'}")
except Exception as e:
    print(f"  TOI download failed: {e}")
    print("  (install: pip install datasets)")

# tally
for name in ["india_fin_news", "moneycontrol_news", "toi_headlines"]:
    d = ROOT / "datasets" / name
    if d.exists():
        files = [f for f in d.rglob("*") if f.is_file()]
        sz = sum(f.stat().st_size for f in files)
        print(f"  {name}: {len(files)} files  {sz/1e6:.0f}MB")

print("\nDone.")
