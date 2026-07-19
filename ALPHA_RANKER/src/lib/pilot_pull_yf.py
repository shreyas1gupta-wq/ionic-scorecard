"""Phase-0 pilot: test yfinance data access through the corporate proxy.
Sequential (proxy stalls on threads), truststore for SSL, resume-safe (skips existing).
Writes one parquet per ticker to data/prices/ and prints a D-009 digest.
"""
import os, sys, time, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
import truststore; truststore.inject_into_ssl()
import pandas as pd
import yfinance as yf

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER"
OUT = os.path.join(BASE, "data", "prices")
os.makedirs(OUT, exist_ok=True)

PILOT = {
    "HDFCBANK": "large-quality", "ASIANPAINT": "large-quality", "NESTLEIND": "large-quality",
    "TATASTEEL": "cyclical", "TATAMOTORS": "cyclical", "HINDALCO": "cyclical",
    "TCS": "it", "INFY": "it",
    "GRAVITA": "smallcap-proxy", "SHAKTIPUMP": "smallcap-proxy",
}
PERIOD = "2y"
digest = []
for tk, bucket in PILOT.items():
    yft = f"{tk}.NS"
    fp = os.path.join(OUT, f"{tk}.parquet")
    if os.path.exists(fp):
        df = pd.read_parquet(fp)
        digest.append((tk, bucket, "cached", len(df), str(df.index.min().date()), str(df.index.max().date()), round(float(df['Close'].iloc[-1]),2)))
        continue
    try:
        df = yf.download(yft, period=PERIOD, interval="1d", auto_adjust=False, progress=False, threads=False)
        if df is None or len(df) == 0:
            digest.append((tk, bucket, "EMPTY", 0, "-", "-", "-")); time.sleep(1.5); continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.to_parquet(fp)
        digest.append((tk, bucket, "OK", len(df), str(df.index.min().date()), str(df.index.max().date()), round(float(df['Close'].iloc[-1]),2)))
    except Exception as e:
        digest.append((tk, bucket, f"ERR:{type(e).__name__}", 0, "-", "-", str(e)[:60]))
    time.sleep(1.5)

print("TICKER      BUCKET           STATUS     ROWS  START       END         LAST_CLOSE")
for r in digest:
    print(f"{r[0]:<11} {r[1]:<16} {r[2]:<10} {r[3]:<5} {r[4]:<11} {r[5]:<11} {r[6]}")
json.dump(digest, open(os.path.join(OUT, "_pilot_digest.json"), "w"), indent=1)
print("\nSaved parquets to:", OUT)
