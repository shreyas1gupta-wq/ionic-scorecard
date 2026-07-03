"""Download the two HuggingFace datasets into our folders (truststore for the
corporate-proxy CA). Index-options-1m -> options project; stock-minute -> swing.
Usage:
  python hf_download.py list           # inspect file lists + sizes only
  python hf_download.py get            # full snapshot download of both
"""
from __future__ import annotations
import sys
from pathlib import Path
import truststore
truststore.inject_into_ssl()
from huggingface_hub import HfApi, snapshot_download

ROOT = Path(__file__).resolve().parents[2]  # NIFTY 500 root
JOBS = [
    ("thetrademarkk/india-index-options-1m",
     ROOT / "intraday_options_strategy" / "datasets" / "raw" / "hf_index_options_1m"),
    ("Saintforest/indian-stock-market-minute-data",
     ROOT / "swing_momentum" / "data" / "hf_stock_minute"),
]
api = HfApi()


def human(n):
    for u in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024 or u == "TB":
            return f"{n:.1f}{u}"
        n /= 1024


def listing():
    for repo, _ in JOBS:
        try:
            info = api.repo_info(repo, repo_type="dataset", files_metadata=True)
            sibs = info.siblings or []
            tot = sum((s.size or 0) for s in sibs)
            print(f"\n=== {repo}: {len(sibs)} files, total {human(tot)}")
            for s in sorted(sibs, key=lambda x: -(x.size or 0))[:15]:
                print(f"  {human(s.size or 0):>10}  {s.rfilename}")
        except Exception as e:
            print(f"{repo}: list ERR {type(e).__name__}: {str(e)[:160]}")


def get():
    # priority resume: NIFTY options + all index files FIRST (unblocks real-fill NIFTY validation),
    # then BANKNIFTY/SENSEX options, then the stock minute data.
    plan = [
        (JOBS[0][0], JOBS[0][1], ["index/*", "options/NIFTY/*"]),
        (JOBS[0][0], JOBS[0][1], ["options/BANKNIFTY/*", "options/SENSEX/*"]),
        (JOBS[1][0], JOBS[1][1], None),
    ]
    for repo, dest, pats in plan:
        dest.mkdir(parents=True, exist_ok=True)
        print(f"\n>>> downloading {repo} {pats or 'ALL'} -> {dest}", flush=True)
        try:
            p = snapshot_download(repo_id=repo, repo_type="dataset", local_dir=str(dest),
                                  max_workers=8, allow_patterns=pats)
            files = [f for f in Path(p).rglob("*") if f.is_file() and ".cache" not in str(f)]
            sz = sum(f.stat().st_size for f in files)
            print(f"OK {repo}: {len(files)} files, {human(sz)} -> {dest}", flush=True)
        except Exception as e:
            print(f"FAIL {repo}: {type(e).__name__}: {str(e)[:300]}", flush=True)


if __name__ == "__main__":
    (get if (len(sys.argv) > 1 and sys.argv[1] == "get") else listing)()
