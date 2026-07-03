"""Download supplementary datasets for alpha research.
Uses chunked retry (80MB segments) for proxy compatibility.
Run:  python hf_extra.py
"""
import os, sys, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import truststore; truststore.inject_into_ssl()
import requests

TOKEN   = os.environ.get("HF_TOKEN", "")
ROOT    = Path(__file__).resolve().parents[2]  # NIFTY 500
SEGMENT = 80 * 1024 * 1024
READ_SZ = 4 * 1024 * 1024
MAX_RETRY = 20
WORKERS = 4
lock = threading.Lock()

# (repo, remote_path, local_dest_dir)
JOBS = [
    # 1. Yahoo Finance data (US) — stock prices + earnings transcripts + news + financials
    ("defeatbeta/yahoo-finance-data", "data/stock_prices.parquet",
     ROOT / "datasets" / "yahoo_finance"),
    ("defeatbeta/yahoo-finance-data", "data/stock_news.parquet",
     ROOT / "datasets" / "yahoo_finance"),
    ("defeatbeta/yahoo-finance-data", "data/stock_earning_call_transcripts.parquet",
     ROOT / "datasets" / "yahoo_finance"),
    ("defeatbeta/yahoo-finance-data", "data/stock_statement.parquet",
     ROOT / "datasets" / "yahoo_finance"),
    ("defeatbeta/yahoo-finance-data", "data/stock_sec_filing.parquet",
     ROOT / "datasets" / "yahoo_finance"),
    ("defeatbeta/yahoo-finance-data", "data/stock_shares_outstanding.parquet",
     ROOT / "datasets" / "yahoo_finance"),
    ("defeatbeta/yahoo-finance-data", "data/stock_profile.parquet",
     ROOT / "datasets" / "yahoo_finance"),
    ("defeatbeta/yahoo-finance-data", "data/stock_dividend.parquet",
     ROOT / "datasets" / "yahoo_finance"),
    ("defeatbeta/yahoo-finance-data", "data/economic_indicator.parquet",
     ROOT / "datasets" / "yahoo_finance"),
    ("defeatbeta/yahoo-finance-data", "data/treasury_yield.parquet",
     ROOT / "datasets" / "yahoo_finance"),
    ("defeatbeta/yahoo-finance-data", "data/stock_market_index.parquet",
     ROOT / "datasets" / "yahoo_finance"),

    # 2. Forex daily prices (all pairs, 9MB)
    ("paperswithbacktest/Forex-Daily-Price", "data/train-00000-of-00001.parquet",
     ROOT / "datasets" / "forex_daily"),

    # 3. Nifty 50 constituent weights (20yr, survivorship-free, 143KB)
    ("AMP4010/Historical_Nifty_50_Constituent_Weights_20Y", "weights.csv",
     ROOT / "datasets" / "nifty50_weights"),
    ("AMP4010/Historical_Nifty_50_Constituent_Weights_20Y", "summary.csv",
     ROOT / "datasets" / "nifty50_weights"),

    # 4. US financial news headlines (773MB, timestamped)
    ("gowthamgoli/Us_Financial_news_dataset", "Us_financial_news_dataset.csv",
     ROOT / "datasets" / "us_fin_news"),

    # 5. Reddit finance posts for S&P500 sentiment (2.3GB)
    ("emilpartow/reddit_finance_posts_sp500", "00_combined.csv",
     ROOT / "datasets" / "reddit_sp500"),
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

    # get remote size
    try:
        r = requests.head(url, headers=hdrs, allow_redirects=True, timeout=30)
        total = int(r.headers.get("content-length", 0))
    except Exception as e:
        log(f"  HEAD FAIL {fname}: {e}")
        return fname, 0

    existing = local.stat().st_size if local.exists() else 0
    if existing >= total and total > 0:
        log(f"  SKIP  {fname}  ({total/1e6:.0f}MB)")
        return fname, existing

    if existing:
        log(f"  RESUME {fname} {existing/1e6:.0f}/{total/1e6:.0f}MB")
    else:
        log(f"  START  {fname}  ({total/1e6:.0f}MB)")

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
                    log(f"  RETRY {fname} {pos/1e6:.0f}MB att {attempt+1} ({type(e).__name__}) {wait}s")
                    f.flush()
                    pos = local.stat().st_size
                    seg_hdrs["Range"] = f"bytes={pos}-{end}"
                    time.sleep(wait)
            else:
                log(f"  FAILED {fname} at {pos/1e6:.0f}MB")
                return fname, pos

    avg = (local.stat().st_size - existing) / max(time.time() - t0, 1) / 1e6
    log(f"  DONE  {fname}  {local.stat().st_size/1e6:.0f}MB  avg {avg:.1f}MB/s")
    return fname, local.stat().st_size

print(f"Extra dataset downloader  Workers: {WORKERS}  Token: {'SET' if TOKEN else 'NOT SET'}")
print(f"Root: {ROOT}\n")

with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {ex.submit(download_file, repo, fn, dest): f"{repo}/{fn}"
            for repo, fn, dest in JOBS}
    for fut in as_completed(futs):
        key = futs[fut]
        try:
            _, sz = fut.result()
        except Exception as e:
            log(f"  ERROR {key}: {e}")

# tally
for name, d in [("yahoo_finance", ROOT/"datasets"/"yahoo_finance"),
                ("forex_daily", ROOT/"datasets"/"forex_daily"),
                ("nifty50_weights", ROOT/"datasets"/"nifty50_weights"),
                ("us_fin_news", ROOT/"datasets"/"us_fin_news"),
                ("reddit_sp500", ROOT/"datasets"/"reddit_sp500")]:
    if d.exists():
        files = list(d.rglob("*"))
        sz = sum(f.stat().st_size for f in files if f.is_file())
        print(f"  {name}: {len(files)} files  {sz/1e6:.0f}MB")

print("\nAll done.")
