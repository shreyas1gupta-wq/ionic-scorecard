"""Download stock options parquets from HF. v3: sequential, verbose, skip existing."""
import time
from pathlib import Path

import truststore; truststore.inject_into_ssl()
import requests
from huggingface_hub import HfApi

TOKEN = "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"
ROOT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
DEST = ROOT / "intraday_options_strategy" / "datasets" / "raw" / "hf_index_options_1m"
REPO = "thetrademarkk/india-index-options-1m"

print("Stock Options Downloader v3 (sequential)", flush=True)
print("Enumerating files...", flush=True)
api = HfApi(token=TOKEN)
info = api.repo_info(REPO, repo_type="dataset", files_metadata=True)
all_files = [(s.rfilename, s.size) for s in info.siblings
             if s.rfilename.endswith('.parquet')
             and s.rfilename.startswith('stocks_options/')]

print(f"Found {len(all_files)} stock options files", flush=True)

to_download = []
for fname, expected_size in all_files:
    local = DEST / fname
    if local.exists() and local.stat().st_size >= (expected_size or 0) and (expected_size or 0) > 0:
        continue
    to_download.append((fname, expected_size or 0))

print(f"Already complete: {len(all_files) - len(to_download)}", flush=True)
print(f"To download: {len(to_download)}\n", flush=True)

session = requests.Session()
session.headers.update({"Authorization": f"Bearer {TOKEN}"})

done = 0
fail = 0
total_bytes = 0
t0 = time.time()

for i, (fname, expected_size) in enumerate(to_download):
    short = fname.split("/")[-1]
    local = DEST / fname
    local.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://huggingface.co/datasets/{REPO}/resolve/main/{fname}?download=true"

    for attempt in range(5):
        try:
            r = session.get(url, stream=True, timeout=120)
            r.raise_for_status()
            with open(local, 'wb') as f:
                for chunk in r.iter_content(1024 * 1024):
                    if chunk:
                        f.write(chunk)
            sz = local.stat().st_size
            done += 1
            total_bytes += sz
            if done % 10 == 0:
                elapsed = time.time() - t0
                rate = total_bytes / max(elapsed, 1) / 1e6
                print(f"  [{done}/{len(to_download)}] {short} {sz/1e3:.0f}KB | total {total_bytes/1e6:.0f}MB {rate:.1f}MB/s | fail={fail}", flush=True)
            break
        except Exception as e:
            if attempt < 4:
                time.sleep(3 * (attempt + 1))
            else:
                print(f"  FAIL {short}: {type(e).__name__}: {str(e)[:60]}", flush=True)
                fail += 1

elapsed = time.time() - t0
print(f"\nDone in {elapsed:.0f}s ({elapsed/60:.1f}min)", flush=True)
print(f"  Downloaded: {done} ({total_bytes/1e6:.0f}MB)", flush=True)
print(f"  Failed: {fail}", flush=True)

so_files = list((DEST / "stocks_options").rglob("*.parquet"))
print(f"\nOn disk: {len(so_files)}/{len(all_files)} stock options parquets", flush=True)
