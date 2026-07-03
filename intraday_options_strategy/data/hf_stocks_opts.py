"""Download stocks_options + artist-23 ATM options using snapshot_download.
These are smaller files (1-75MB each) so proxy resets are less likely.
Falls back to chunked requests if snapshot stalls.
"""
import os, sys, time
from pathlib import Path
import truststore; truststore.inject_into_ssl()
os.environ["HF_TOKEN"] = os.environ.get("HF_TOKEN", "")

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[2]
OPTS_DEST   = ROOT / "intraday_options_strategy" / "datasets" / "raw" / "hf_index_options_1m"
ARTIST_DEST = ROOT / "intraday_options_strategy" / "datasets" / "raw" / "hf_atm_options"

TOKEN = os.environ.get("HF_TOKEN", "")
OPTS_DEST.mkdir(parents=True, exist_ok=True)
ARTIST_DEST.mkdir(parents=True, exist_ok=True)

jobs = [
    ("thetrademarkk/india-index-options-1m",  OPTS_DEST,   ["stocks_options/*"]),
    ("artist-23/nifty-options-data",           ARTIST_DEST, None),
]

for repo, dest, patterns in jobs:
    print(f"\n>>> {repo}  patterns={patterns}  -> {dest}", flush=True)
    try:
        p = snapshot_download(
            repo_id=repo, repo_type="dataset",
            local_dir=str(dest),
            max_workers=16,
            allow_patterns=patterns,
            token=TOKEN,
        )
        files = [f for f in Path(p).rglob("*") if f.is_file() and ".cache" not in str(f)]
        sz = sum(f.stat().st_size for f in files)
        print(f"OK  {repo}: {len(files)} files, {sz/1e9:.2f}GB", flush=True)
    except Exception as e:
        print(f"FAIL {repo}: {type(e).__name__}: {str(e)[:200]}", flush=True)

print("\nAll done.")
