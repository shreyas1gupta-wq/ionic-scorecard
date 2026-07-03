"""Fast parallel HuggingFace downloader using hf_transfer (Rust engine).
Only downloads the stock-minute dataset — options are already complete.
Run:  python hf_fast.py
"""
import os, sys
os.environ["HF_XET_HIGH_PERFORMANCE"] = "1"   # activate Xet high-perf transfer

from pathlib import Path
import truststore; truststore.inject_into_ssl()
from huggingface_hub import snapshot_download, HfApi

DEST = Path(__file__).resolve().parents[2] / "swing_momentum" / "data" / "hf_stock_minute"
DEST.mkdir(parents=True, exist_ok=True)

REPO = "Saintforest/indian-stock-market-minute-data"

# how many files already there
existing = list(DEST.rglob("*.parquet"))
print(f"Already downloaded: {len(existing)} files")
print(f"Destination: {DEST}")
print(f"Downloading {REPO} with hf_transfer (parallel Rust engine) ...\n", flush=True)

try:
    p = snapshot_download(
        repo_id=REPO,
        repo_type="dataset",
        local_dir=str(DEST),
        max_workers=16,        # hf_transfer handles true parallelism
    )
    files = [f for f in Path(p).rglob("*") if f.is_file() and ".cache" not in str(f)]
    sz = sum(f.stat().st_size for f in files)
    gb = sz / 1e9
    print(f"\nDone: {len(files)} files, {gb:.2f} GB -> {DEST}")
except KeyboardInterrupt:
    print("\nInterrupted — run again to resume (snapshot_download is resumable).")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    print("Tip: if proxy blocks, set HF_ENDPOINT or add HF_TOKEN env var for higher rate limits.")
