"""D-033 pull: paperswithbacktest/Stocks-Daily-Price (US stocks daily bulk, 4 shards, ~530MB).
Resume-safe per shard; verification: schema + ticker count + AAPL spot-check after download.
Output: 05_DATA_OFFICE/data/us_stocks_daily/ (shards kept as-is; readers use pyarrow dataset).
"""
from pathlib import Path
import truststore
truststore.inject_into_ssl()
import pandas as pd, requests

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/us_stocks_daily"
OUT.mkdir(parents=True, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 Chrome/126",
     "Authorization": "Bearer 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"}
BASE = "https://huggingface.co/datasets/paperswithbacktest/Stocks-Daily-Price/resolve/main/data"

for i in range(4):
    name = f"train-0000{i}-of-00004.parquet"
    p = OUT / name
    if p.exists() and p.stat().st_size > 100e6:
        print(f"{name}: exists, skip", flush=True)
        continue
    with requests.get(f"{BASE}/{name}", headers=H, timeout=600, stream=True) as r:
        r.raise_for_status()
        tmp = p.with_suffix(".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
        tmp.rename(p)
    print(f"{name}: {p.stat().st_size/1e6:.0f} MB saved", flush=True)

# verification
import pyarrow.dataset as ds
d = ds.dataset(str(OUT), format="parquet")
print("schema:", d.schema.names, flush=True)
tbl = d.to_table()
df = tbl.to_pandas()
sym_col = next(c for c in df.columns if c.lower() in ("symbol", "ticker", "sym"))
date_col = next(c for c in df.columns if "date" in c.lower())
print(f"rows={len(df):,} | tickers={df[sym_col].nunique():,} | "
      f"span={df[date_col].min()} .. {df[date_col].max()}", flush=True)
aapl = df[df[sym_col].isin(["AAPL", "aapl"])]
print(f"AAPL rows={len(aapl):,}", flush=True)
print("DONE", flush=True)
