"""Route 3B import (ops): quarterly_results_all.json -> firm parquet + board-meetings history audit.
Writes to 05_DATA_OFFICE/data (datasets/ is read-only legacy). Prints D-009 digest.
"""
import json, io
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data"
SRC = ROOT / "datasets/nse_earnings_dates"

# ---- audit board meetings history depth ----
bm = json.load(io.open(SRC / "board_meetings_all.json", encoding="utf-8"))
if isinstance(bm, dict):
    for k in ("data", "records", "rows"):
        if k in bm:
            bm = bm[k]; break
bdf = pd.DataFrame(bm)
datecol = next((c for c in bdf.columns if "date" in c.lower() and "meet" in c.lower()), None) or \
          next((c for c in bdf.columns if "date" in c.lower()), None)
bdf["dt"] = pd.to_datetime(bdf[datecol], errors="coerce", dayfirst=True)
fr = bdf[bdf.astype(str).apply(lambda r: r.str.contains("inancial", na=False)).any(axis=1)]
print(f"board_meetings: {len(bdf)} rows, cols {bdf.columns.tolist()[:8]}")
print(f"  date range {bdf.dt.min()} .. {bdf.dt.max()} | fin-results rows {len(fr)}, earliest {fr.dt.min()}")
print(f"  by year: {bdf.dt.dt.year.value_counts().sort_index().to_dict()}")

# ---- import quarterly results ----
qr = json.load(io.open(SRC / "quarterly_results_all.json", encoding="utf-8"))
if isinstance(qr, dict):
    for k in ("data", "records", "rows", "resCorporate"):
        if k in qr:
            qr = qr[k]; break
qdf = pd.DataFrame(qr)
print(f"quarterly_results: {len(qdf)} rows")
print("cols:", qdf.columns.tolist())
bc = next((c for c in qdf.columns if "broadcast" in c.lower() or "broadCast" in c), None)
if bc:
    qdf["broadcast_dt"] = pd.to_datetime(qdf[bc], errors="coerce", dayfirst=True)
    print("broadcast by year:", qdf.broadcast_dt.dt.year.value_counts().sort_index().to_dict())
rel = qdf[qdf.astype(str).apply(lambda r: r.str.contains("RELIANCE", na=False)).any(axis=1)]
print("RELIANCE rows:", len(rel))
print(rel.head(3).to_string()[:1500])
qdf.to_parquet(OUT / "nse_quarterly_results_pit.parquet", index=False)
print("saved ->", OUT / "nse_quarterly_results_pit.parquet")
