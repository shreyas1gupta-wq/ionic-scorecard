"""D-033 pull: XAUUSD (gold) 1-min 2009-2026 from HF fokan/xauusd-2009-2026 (HistData MT4 format).
Yearly CSVs -> single parquet. Resume-safe per year. Verification: COVID-era + recent spot checks.
"""
import io
from pathlib import Path
import truststore
truststore.inject_into_ssl()
import pandas as pd, requests

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/commodities_1m"
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 Chrome/126"}
BASE = "https://huggingface.co/datasets/fokan/xauusd-2009-2026/resolve/main"

frames = []
for y in range(2009, 2027):
    p = OUT / f"XAUUSD_1m_{y}.parquet"
    if p.exists():
        print(f"{y}: exists, skip", flush=True); continue
    url = f"{BASE}/DAT_MT_XAUUSD_M1_{y}.csv"
    r = requests.get(url, headers=UA, timeout=300)
    if r.status_code != 200:
        print(f"{y}: HTTP {r.status_code}", flush=True); continue
    df = pd.read_csv(io.StringIO(r.text), header=None,
                     names=["date", "time", "open", "high", "low", "close", "vol"])
    df["ts"] = pd.to_datetime(df["date"] + " " + df["time"], format="%Y.%m.%d %H:%M")
    df = df[["ts", "open", "high", "low", "close"]]
    df.to_parquet(p, index=False)
    print(f"{y}: {len(df)} rows saved", flush=True)

# verification: gold ~2070 high Aug-2020; ~1615-1640 low Mar-2020
try:
    d20 = pd.read_parquet(OUT / "XAUUSD_1m_2020.parquet")
    aug = d20[(d20.ts >= "2020-08-01") & (d20.ts < "2020-09-01")]
    mar = d20[(d20.ts >= "2020-03-01") & (d20.ts < "2020-04-01")]
    print(f"VERIFY 2020-08 high={aug.high.max():.0f} (expect ~2070+-15); "
          f"2020-03 low={mar.low.min():.0f} (expect ~1450-1480)", flush=True)
except Exception as e:
    print("verify err", e)
print("DONE", flush=True)
