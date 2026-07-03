"""Phase 0 data audit: inventory every raw source, profile 1-min candidates,
and write a human-readable DATA_AUDIT.md that the next session reads first.

Audit covers (per spec S2.5): date range, # trading days, missing candles/gaps,
obvious quality issues. Lookahead safety is a construction-time guarantee
(features built from past bars only) — asserted later in features/, noted here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR, DATASETS_DIR  # noqa: E402

AUDIT_FILE = DATASETS_DIR / "DATA_AUDIT.md"
EXPECTED_BARS_PER_DAY = 375  # 09:15–15:29 inclusive, 1-min


def find_csvs(root: Path, limit: int = 5000) -> list[Path]:
    if not root.exists():
        return []
    out = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".csv", ".txt", ".parquet"}:
            out.append(p)
            if len(out) >= limit:
                break
    return out


def profile_minute_csv(path: Path) -> dict | None:
    """Profile a candidate 1-min file: detect datetime column, freq, range, gaps."""
    try:
        df = pd.read_csv(path, nrows=200_000)
    except Exception as exc:  # noqa: BLE001
        return {"file": str(path), "error": str(exc)[:200]}
    dt_col = next((c for c in df.columns
                   if c.lower() in {"date", "datetime", "timestamp", "time", "date_time"}), None)
    if dt_col is None:
        return None
    try:
        ts = pd.to_datetime(df[dt_col], errors="coerce", format="mixed").dropna()
    except Exception:  # noqa: BLE001
        return None
    if len(ts) < 100:
        return None
    freq_s = ts.sort_values().diff().dropna().dt.total_seconds().mode()
    freq = float(freq_s.iloc[0]) if len(freq_s) else None
    if freq != 60.0:
        return None  # not 1-min; skip expensive full row count
    n_rows_total = sum(1 for _ in open(path, "rb")) - 1
    days = ts.dt.normalize().nunique()
    return {
        "file": str(path.relative_to(RAW_DIR)),
        "size_mb": round(path.stat().st_size / 1e6, 1),
        "rows_total": n_rows_total,
        "modal_freq_sec": freq,
        "is_minute": freq == 60.0,
        "sample_start": str(ts.min()),
        "sample_end": str(ts.max()),
        "sample_days": int(days),
        "columns": list(df.columns)[:12],
    }


def deep_audit_minute(path: Path, dt_col_hint: str | None = None) -> dict:
    """Full-file audit of the chosen 1-min index source."""
    df = pd.read_csv(path)
    dt_col = dt_col_hint or next(c for c in df.columns
                                 if c.lower() in {"date", "datetime", "timestamp", "time", "date_time"})
    df["dt"] = pd.to_datetime(df[dt_col], errors="coerce", format="mixed")
    df = df.dropna(subset=["dt"]).sort_values("dt")
    df["day"] = df["dt"].dt.normalize()
    per_day = df.groupby("day").size()
    short_days = per_day[per_day < EXPECTED_BARS_PER_DAY * 0.9]
    num_cols = [c for c in df.columns if c.lower() in {"open", "high", "low", "close", "volume"}]
    issues = []
    for c in num_cols:
        bad = int((pd.to_numeric(df[c], errors="coerce") <= 0).sum()) if c != "volume" else 0
        if bad:
            issues.append(f"{bad} non-positive values in {c}")
    dup = int(df["dt"].duplicated().sum())
    if dup:
        issues.append(f"{dup} duplicate timestamps")
    return {
        "file": str(path),
        "rows": len(df),
        "start": str(df["dt"].min()),
        "end": str(df["dt"].max()),
        "trading_days": int(per_day.shape[0]),
        "median_bars_per_day": float(per_day.median()),
        "days_with_<90pct_bars": int(short_days.shape[0]),
        "worst_short_days": {str(k.date()): int(v) for k, v in short_days.nsmallest(5).items()},
        "issues": issues or ["none detected"],
    }


def main() -> None:
    status_file = DATASETS_DIR / "download_status.json"
    status = json.loads(status_file.read_text()) if status_file.exists() else {}

    lines = ["# DATA AUDIT — Phase 0", f"\nGenerated: {pd.Timestamp.now()}\n",
             "## Download status summary\n```json",
             json.dumps({k: {kk: vv for kk, vv in v.items() if kk != 'files_sample'}
                         if isinstance(v, dict) else v for k, v in status.items()},
                        indent=2, default=str)[:3000],
             "```\n## File inventory & 1-min candidates\n"]

    candidates = []
    for f in find_csvs(RAW_DIR):
        if f.stat().st_size < 100_000:  # skip tiny files for minute-data candidacy
            continue
        prof = profile_minute_csv(f)
        if prof and prof.get("is_minute"):
            candidates.append(prof)

    # rank: exact Nifty 50 index file first, then BankNifty, then by size
    def rank(p: dict) -> tuple:
        name = Path(p["file"]).name.upper()
        exact = name.startswith("NIFTY 50_MINUTE")
        bank = name.startswith("NIFTY BANK_MINUTE")
        return (not exact, not bank, -p["size_mb"])

    candidates.sort(key=rank)
    lines.append(f"Found **{len(candidates)}** 1-minute candidate files.\n")
    for p in candidates[:25]:
        lines.append(f"- `{p['file']}` ({p['size_mb']} MB, ~{p['rows_total']:,} rows, "
                     f"{p['sample_start']} → {p['sample_end']} in first 200k rows)")

    if candidates:
        best = RAW_DIR / candidates[0]["file"]
        lines.append(f"\n## Deep audit of primary candidate: `{candidates[0]['file']}`\n```json")
        lines.append(json.dumps(deep_audit_minute(best), indent=2))
        lines.append("```")
    else:
        lines.append("\n**NO 1-minute data found.** Next session: obtain kaggle.json "
                     "credentials OR build synthetic proxy (PLAN.md Phase 1 / S2.4).")

    lines.append("\n## Lookahead note\nAll features will be built from bars [t-n, t-1] + close(t) "
                 "only; entries at next bar open. Asserted via shift-tests in features/ (Phase 2).")
    AUDIT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Audit written -> {AUDIT_FILE}")
    print(f"1-min candidates found: {len(candidates)}")
    if candidates:
        print("Primary:", candidates[0]["file"])


if __name__ == "__main__":
    main()
