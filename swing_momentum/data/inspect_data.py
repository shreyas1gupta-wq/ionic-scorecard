"""Inventory the available equity datasets for the swing track."""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

def peek(name, **kw):
    p = ROOT / name
    if not p.exists():
        print(f"MISSING: {name}"); return
    try:
        xl = pd.ExcelFile(p)
        print(f"\n=== {name} | sheets={xl.sheet_names[:6]}")
        df = pd.read_excel(p, sheet_name=xl.sheet_names[0], nrows=6, **kw)
        print(f"  shape(head)={df.shape} cols={list(df.columns)[:14]}")
        print(df.head(4).to_string()[:1200])
    except Exception as e:
        print(f"  ERR {name}: {str(e)[:160]}")

for n in ["Nifty500_Master_Dataset_2005_2025.xlsx",
          "NIFTY500_TICKER_2005_2025_Final.xlsx",
          "Nifty500_Delisted_2005_2025.xlsx",
          "Historical stock composition of Nifty 50 and Nifty Next 50.xlsx"]:
    peek(n)
