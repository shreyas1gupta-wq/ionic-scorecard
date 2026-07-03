"""Phase 0 data acquisition: Kaggle (anonymous kagglehub), GitHub NSE-Data, India VIX.

Each source is attempted independently; failures are logged, never fatal.
Results land in datasets/raw/ and a machine-readable status file
datasets/download_status.json so the audit/next session knows what we have.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR, DATASETS_DIR  # noqa: E402

STATUS_FILE = DATASETS_DIR / "download_status.json"

KAGGLE_DATASETS = [
    "debashis74017/stock-market-data-nifty-50-stocks",
    "debashis74017/nifty-50-minute-data",
    "rohanrao/nifty50-stock-market-data",
]
GITHUB_REPO = "https://github.com/debaonline4u/NSE-Data"


def try_kaggle() -> dict:
    """Anonymous kagglehub download of public datasets (no API token needed)."""
    out: dict = {"attempted": KAGGLE_DATASETS, "success": [], "errors": {}}
    try:
        import kagglehub
    except ImportError as exc:
        out["errors"]["import"] = str(exc)
        return out
    for ds in KAGGLE_DATASETS:
        try:
            path = kagglehub.dataset_download(ds)
            dest = RAW_DIR / "kaggle" / ds.replace("/", "__")
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copytree(path, dest)
            files = [str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file()]
            out["success"].append({"dataset": ds, "dest": str(dest), "n_files": len(files),
                                   "files_sample": files[:20]})
            print(f"[kaggle] OK {ds}: {len(files)} files -> {dest}")
            if len(out["success"]) >= 1 and ds == KAGGLE_DATASETS[0]:
                break  # primary dataset landed; skip alternates
        except Exception as exc:  # noqa: BLE001 — log and continue to next source
            out["errors"][ds] = f"{type(exc).__name__}: {exc}"
            print(f"[kaggle] FAIL {ds}: {exc}")
    return out


def try_github() -> dict:
    out: dict = {"repo": GITHUB_REPO}
    dest = RAW_DIR / "github" / "NSE-Data"
    try:
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            r = subprocess.run(
                ["git", "clone", "--depth", "1", GITHUB_REPO, str(dest)],
                capture_output=True, text=True, timeout=600,
            )
            if r.returncode != 0:
                out["error"] = r.stderr.strip()[-500:]
                print(f"[github] FAIL: {out['error']}")
                return out
        files = [str(p.relative_to(dest)) for p in dest.rglob("*")
                 if p.is_file() and ".git" not in p.parts]
        out.update(dest=str(dest), n_files=len(files), files_sample=files[:30])
        print(f"[github] OK: {len(files)} files")
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
        print(f"[github] FAIL: {exc}")
    return out


def try_vix_and_indices() -> dict:
    """India VIX + Nifty/BankNifty daily via yfinance (daily only — 1-min not
    available beyond ~8 days on Yahoo; that's what Kaggle is for)."""
    out: dict = {}
    try:
        import yfinance as yf
        for ticker, name in [("^INDIAVIX", "india_vix_daily"),
                             ("^NSEI", "nifty50_daily"),
                             ("^NSEBANK", "banknifty_daily")]:
            try:
                df = yf.download(ticker, start="2008-01-01", auto_adjust=False,
                                 progress=False, multi_level_index=False)
                if df is None or df.empty:
                    out[name] = {"error": "empty frame"}
                    continue
                f = RAW_DIR / f"{name}.csv"
                df.to_csv(f)
                out[name] = {"file": str(f), "rows": len(df),
                             "start": str(df.index[0].date()), "end": str(df.index[-1].date())}
                print(f"[yfinance] OK {ticker}: {len(df)} rows {df.index[0].date()}..{df.index[-1].date()}")
            except Exception as exc:  # noqa: BLE001
                out[name] = {"error": f"{type(exc).__name__}: {exc}"}
                print(f"[yfinance] FAIL {ticker}: {exc}")
    except ImportError as exc:
        out["import_error"] = str(exc)
    return out


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    status = {}
    for key, fn in [("kaggle", try_kaggle), ("github", try_github),
                    ("yfinance", try_vix_and_indices)]:
        try:
            status[key] = fn()
        except Exception:  # noqa: BLE001 — belt and braces; one source must not kill the rest
            status[key] = {"fatal": traceback.format_exc()[-800:]}
    STATUS_FILE.write_text(json.dumps(status, indent=2))
    print(f"\nStatus written -> {STATUS_FILE}")


if __name__ == "__main__":
    main()
