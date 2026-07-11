"""HF chuyin0321/timeseries-daily-stocks (2023-09 vintage, no signup) -> vintage-union layer. Resume-safe."""
import truststore; truststore.inject_into_ssl()
import requests, pandas as pd
from pathlib import Path

OUT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\05_DATA_OFFICE\data\us_vintage_2023_09")
OUT.mkdir(parents=True, exist_ok=True)
s = requests.Session()
s.headers["User-Agent"] = "Mozilla/5.0"
api = "https://huggingface.co/api/datasets/chuyin0321/timeseries-daily-stocks"
tree = s.get(api + "/tree/main/data", timeout=60).json()
files = [f["path"] for f in tree if f["path"].endswith(".parquet")]
if not files:
    tree = s.get(api + "/tree/main", timeout=60).json()
    files = [f["path"] for f in tree if f["path"].endswith(".parquet")]
print(f"{len(files)} parquet files", flush=True)
for p in files:
    dst = OUT / p.replace("/", "_")
    if dst.exists() and dst.stat().st_size > 0:
        print("skip", dst.name, flush=True)
        continue
    url = f"https://huggingface.co/datasets/chuyin0321/timeseries-daily-stocks/resolve/main/{p}"
    with s.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        tmp = dst.with_suffix(".part")
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
        tmp.rename(dst)
    print("done", dst.name, dst.stat().st_size // 1048576, "MB", flush=True)
# digest
import glob
fs = sorted(OUT.glob("*.parquet"))
n, syms = 0, set()
for f in fs:
    df = pd.read_parquet(f, columns=None)
    n += len(df)
    sc = next((c for c in df.columns if c.lower() in ("symbol", "ticker")), df.columns[0])
    syms.update(df[sc].unique())
    del df
print(f"TOTAL rows {n} | distinct symbols {len(syms)}", flush=True)
