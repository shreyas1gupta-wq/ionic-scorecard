"""Download Indian earnings + fundamentals datasets.
1. MiMIC Indian Earnings Calls — result dates, call transcripts, market reaction
2. Charon107 Financial Parameters from MoneyControl — 992 companies, 5yr annual reports
"""
import os, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import truststore; truststore.inject_into_ssl()
import requests

TOKEN = "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"
ROOT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
SEGMENT = 80 * 1024 * 1024
READ_SZ = 4 * 1024 * 1024
MAX_RETRY = 20
WORKERS = 4
lock = threading.Lock()

JOBS = [
    # MiMIC — earnings calls with RESULT DATE + market reaction
    ("sohomghosh/MiMIC_Multi-Modal_Indian_Earnings_Calls_Dataset",
     "MiMIC_Multi-Modal_Indian_Earnings_Calls.xlsx",
     ROOT / "datasets" / "india_earnings_calls"),
    ("sohomghosh/MiMIC_Multi-Modal_Indian_Earnings_Calls_Dataset",
     "final_train.csv",
     ROOT / "datasets" / "india_earnings_calls"),
    ("sohomghosh/MiMIC_Multi-Modal_Indian_Earnings_Calls_Dataset",
     "final_test.csv",
     ROOT / "datasets" / "india_earnings_calls"),
    ("sohomghosh/MiMIC_Multi-Modal_Indian_Earnings_Calls_Dataset",
     "final_valid.csv",
     ROOT / "datasets" / "india_earnings_calls"),
    ("sohomghosh/MiMIC_Multi-Modal_Indian_Earnings_Calls_Dataset",
     "getting_all_texts_together.pkl",
     ROOT / "datasets" / "india_earnings_calls"),
    ("sohomghosh/MiMIC_Multi-Modal_Indian_Earnings_Calls_Dataset",
     "raw_data/extracted_texts.zip",
     ROOT / "datasets" / "india_earnings_calls"),
    ("sohomghosh/MiMIC_Multi-Modal_Indian_Earnings_Calls_Dataset",
     "data_preparation/Multimodal_Earnings_Transcripts_PPTs__EDA_Technicals_Market_Fundaments.ipynb",
     ROOT / "datasets" / "india_earnings_calls"),

    # Charon107 — financial parameters from MoneyControl (992 companies, 5yr)
    ("Charon107/Financial_Parameter_From_Moneycontrol",
     "Train.parquet",
     ROOT / "datasets" / "india_fundamentals_mc"),
    ("Charon107/Financial_Parameter_From_Moneycontrol",
     "Test.parquet",
     ROOT / "datasets" / "india_fundamentals_mc"),
    ("Charon107/Financial_Parameter_From_Moneycontrol",
     "Companies_List/Companies_List.csv",
     ROOT / "datasets" / "india_fundamentals_mc"),
]

def log(msg):
    with lock:
        print(msg, flush=True)

def hf_url(repo, fname):
    return f"https://huggingface.co/datasets/{repo}/resolve/main/{fname}?download=true"

def download_file(repo, fname, dest_dir):
    dest_dir.mkdir(parents=True, exist_ok=True)
    local = dest_dir / fname.split("/")[-1]
    url = hf_url(repo, fname)
    hdrs = {"Authorization": f"Bearer {TOKEN}"}

    try:
        r = requests.head(url, headers=hdrs, allow_redirects=True, timeout=30)
        total = int(r.headers.get("content-length", 0))
    except Exception as e:
        log(f"  HEAD FAIL {fname}: {e}")
        return fname, 0

    existing = local.stat().st_size if local.exists() else 0
    if existing >= total and total > 0:
        log(f"  SKIP  {fname.split('/')[-1]}  ({total/1e6:.1f}MB)")
        return fname, existing

    log(f"  START  {fname.split('/')[-1]}  ({total/1e6:.1f}MB)")
    pos = existing
    t0 = time.time()
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
                    pct = pos / total * 100
                    mbps = (pos - existing) / max(time.time() - t0, 1) / 1e6
                    log(f"  {fname.split('/')[-1]}  {pct:5.1f}%  {pos/1e6:7.1f}MB  {mbps:.1f}MB/s")
                    break
                except Exception:
                    wait = min(3 * (attempt + 1), 15)
                    log(f"  RETRY {fname.split('/')[-1]} att {attempt+1}")
                    f.flush()
                    pos = local.stat().st_size
                    time.sleep(wait)
            else:
                log(f"  FAILED {fname}")
                return fname, pos

    log(f"  DONE  {fname.split('/')[-1]}  {local.stat().st_size/1e6:.1f}MB")
    return fname, local.stat().st_size

print("Indian Earnings + Fundamentals Downloader")
print(f"Token: SET  Workers: {WORKERS}\n")

with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {ex.submit(download_file, r, f, d): f for r, f, d in JOBS}
    for fut in as_completed(futs):
        try:
            fut.result()
        except Exception as e:
            log(f"  ERROR: {e}")

# Tally
for name in ["india_earnings_calls", "india_fundamentals_mc"]:
    d = ROOT / "datasets" / name
    if d.exists():
        files = [f for f in d.rglob("*") if f.is_file()]
        sz = sum(f.stat().st_size for f in files)
        print(f"\n  {name}: {len(files)} files, {sz/1e6:.0f}MB")
        for f in sorted(files):
            print(f"    {f.stat().st_size/1e6:.1f}MB  {f.name}")

print("\nDone.")
