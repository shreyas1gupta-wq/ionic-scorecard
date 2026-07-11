"""D-033 pull v2: FRED daily closes -> 05_DATA_OFFICE/data/ (Stooq rejected: JS anti-bot via proxy).
SP500 (FRED id SP500, ~10yr window) + USDINR (DEXINUS, 1973+). D-009 spot-checks before accept.
"""
import io
from pathlib import Path
import truststore
truststore.inject_into_ssl()
import pandas as pd, requests

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data"
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126"}

JOBS = [
    ("SP500", "us_sp500_daily.parquet", {"2020-03-23": (2237.40, 1.0), "2024-12-31": (5881.63, 2.0)}),
    ("DEXINUS", "usdinr_daily.parquet", {"2020-03-23": (76.0, 1.5)}),
]

for fid, name, checks in JOBS:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={fid}"
    r = requests.get(url, headers=UA, timeout=120)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    date_col, val_col = df.columns[0], df.columns[1]
    df.columns = ["Date", "Close"]
    df["Date"] = pd.to_datetime(df["Date"])
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df = df.dropna()
    ok = True
    for dstr, (exp, tol) in checks.items():
        row = df[df.Date == dstr]
        if not len(row):
            print(f"[{fid}] check date {dstr} not in window (span starts {df.Date.min().date()}) - tolerated" )
            continue
        got = row.Close.iloc[0]
        good = abs(got - exp) <= tol
        ok &= good
        print(f"[{fid}] {dstr} Close={got} expected~{exp} -> {'OK' if good else 'FAIL'}")
    span = f"{df.Date.min().date()}..{df.Date.max().date()}, n={len(df)}"
    if ok and len(df) > 1000:
        df.to_parquet(OUT / name, index=False)
        print(f"[{fid}] SAVED {name} ({span})")
    else:
        print(f"[{fid}] REJECTED ({span})")
