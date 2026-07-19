import os, time
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
import truststore; truststore.inject_into_ssl()
import pandas as pd, yfinance as yf

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
OUT = os.path.join(BASE, "datasets", "etf_universe")

CANDS = {"SMALL250": "SMALL250.NS", "MOSMALL250": "MOSMALL250.NS"}
for tag, tk in CANDS.items():
    df = yf.download(tk, period="max", interval="1d", auto_adjust=False, progress=False, threads=False)
    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    n = df["Close"].notna().sum()
    print(tag, tk, "rows", len(df), "nonnull", n, "min", df["Date"].min(), "max", df["Date"].max())
    if n >= 30:
        df.to_parquet(os.path.join(OUT, f"{tag}.parquet"))
    time.sleep(1.0)
