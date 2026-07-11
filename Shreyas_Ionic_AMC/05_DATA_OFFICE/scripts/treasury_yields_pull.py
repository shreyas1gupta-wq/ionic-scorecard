"""D-033 pull: US Treasury daily par yield curve, 2000-2026, official treasury.gov CSVs.
Output: 05_DATA_OFFICE/data/us_treasury_yields_daily.parquet. Spot-check: 10Y ~0.52% on 2020-08-04 (record low ~0.52).
"""
import io, time
from pathlib import Path
import truststore
truststore.inject_into_ssl()
import pandas as pd, requests

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data"
UA = {"User-Agent": "Mozilla/5.0 Chrome/126"}

frames = []
for y in range(2000, 2027):
    url = (f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
           f"daily-treasury-rates.csv/{y}/all?type=daily_treasury_yield_curve"
           f"&field_tdr_date_value={y}&page&_format=csv")
    try:
        r = requests.get(url, headers=UA, timeout=60)
        if r.status_code == 200 and r.text.startswith("Date"):
            df = pd.read_csv(io.StringIO(r.text))
            frames.append(df)
            print(f"{y}: {len(df)} rows", flush=True)
        else:
            print(f"{y}: HTTP {r.status_code}", flush=True)
    except Exception as e:
        print(f"{y}: ERR {type(e).__name__}", flush=True)
    time.sleep(0.5)

df = pd.concat(frames, ignore_index=True)
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date").drop_duplicates("Date")
row = df[df.Date == "2020-08-04"]
got = row["10 Yr"].iloc[0] if len(row) else None
ok = got is not None and abs(got - 0.52) <= 0.05
print(f"VERIFY 2020-08-04 10Y={got} expect~0.52 -> {'OK' if ok else 'FAIL'}")
if ok:
    df.to_parquet(OUT / "us_treasury_yields_daily.parquet", index=False)
    print(f"SAVED {df.Date.min().date()}..{df.Date.max().date()} n={len(df)} cols={len(df.columns)}")
else:
    print("REJECTED")
