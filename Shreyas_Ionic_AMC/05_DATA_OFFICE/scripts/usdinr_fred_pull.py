"""USDINR daily from FRED (DEXINUS, official, D-033 class). Saves parquet + prints D-009 sample checks."""
import truststore; truststore.inject_into_ssl()
import io, requests, pandas as pd
from pathlib import Path

OUT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\05_DATA_OFFICE\data")
url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXINUS"
s = requests.Session()
r = s.get(url, timeout=60)
r.raise_for_status()
df = pd.read_csv(io.StringIO(r.text))
df.columns = ["date", "usdinr"]
df["date"] = pd.to_datetime(df["date"])
df["usdinr"] = pd.to_numeric(df["usdinr"], errors="coerce")
df = df.dropna().reset_index(drop=True)
df.to_parquet(OUT / "usdinr_fred_daily.parquet", index=False)
print(f"rows {len(df)} | {df.date.min().date()} .. {df.date.max().date()}")
for d_, v in [("2013-08-28", 68.36), ("2020-03-23", 76.02), ("2011-01-03", 44.72)]:
    row = df[df.date == d_]
    print(d_, "fred=", float(row.usdinr.iloc[0]) if len(row) else "MISSING", "expect~", v)
print("monotone:", df.date.is_monotonic_increasing, "| dupes:", int(df.date.duplicated().sum()))
