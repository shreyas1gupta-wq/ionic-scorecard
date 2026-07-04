"""OFFICIAL NSE index closes — ALL indices daily via nsearchives ind_close_all CSVs.
Office-proxy-WORKING route to the same official numbers as the Principal's niftyindices.com
scraper (that endpoint stays Zscaler-blocked; this host is proven — 370+ bhavcopy downloads).
Feeds factor-index replication (D-M4): official NAV series for NIFTY200 MOMENTUM 30,
Nifty100 Low Volatility 30, Alpha/Quality/Value family, plus every other NSE index.

Output: datasets/index_daily/nse_official_all_indices.parquet
  cols: index_name, date, open, high, low, close, points_change, pct_change, volume, pe, pb, div_yield
Pull order: NEWEST -> OLDEST (recent overlap matters most for TE); resume-safe (skips dates
already in parquet); checkpoint every 40 files; 404 = holiday, skip. Sequential session,
~0.8s/req (proxy etiquette). Run: background, ~45-60 min for 2016->today first pass.
"""
import datetime as dt
import io
import sys
import time
from pathlib import Path

import truststore
truststore.inject_into_ssl()
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "datasets" / "index_daily" / "nse_official_all_indices.parquet"
START = dt.date(2016, 1, 1)
END = dt.date.today()

COLMAP = {
    "Index Name": "index_name", "Index Date": "date", "Open Index Value": "open",
    "High Index Value": "high", "Low Index Value": "low", "Closing Index Value": "close",
    "Points Change": "points_change", "Change(%)": "pct_change", "Volume": "volume",
    "P/E": "pe", "P/B": "pb", "Div Yield": "div_yield",
}

s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                "(KHTML, like Gecko) Chrome/126 Safari/537.36", "Accept": "*/*"})
try:
    s.get("https://www.nseindia.com", timeout=15)  # cookie warm-up (bhavcopy recipe)
except Exception:
    pass

have = set()
frames = []
if OUT.exists():
    old = pd.read_parquet(OUT)
    have = set(old["date"].astype(str))
    frames.append(old)
    print(f"resume: {len(have)} dates already on disk", flush=True)

dates = [END - dt.timedelta(days=i) for i in range((END - START).days + 1)]
dates = [d for d in dates if d.weekday() < 5]  # newest first, weekdays only

new, misses, errs = [], 0, 0
for n, d in enumerate(dates):
    iso = d.isoformat()
    if iso in have:
        continue
    url = f"https://nsearchives.nseindia.com/content/indices/ind_close_all_{d:%d%m%Y}.csv"
    try:
        r = s.get(url, timeout=25)
        if r.status_code == 200 and b"Index Name" in r.content[:200]:
            df = pd.read_csv(io.BytesIO(r.content))
            df = df.rename(columns={k: v for k, v in COLMAP.items() if k in df.columns})
            keep = [c for c in COLMAP.values() if c in df.columns]
            df = df[keep]
            df["date"] = iso  # trust the URL date; file's Index Date col format varies
            for c in df.columns:
                if c not in ("index_name", "date"):
                    df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")
            new.append(df)
        elif r.status_code in (403, 401):
            errs += 1
            print(f"{iso}: HTTP {r.status_code} — re-warming cookies", flush=True)
            try:
                s.get("https://www.nseindia.com", timeout=15)
            except Exception:
                pass
            if errs > 30:
                print("too many auth errors, stopping (resume-safe)", flush=True)
                break
        else:
            misses += 1  # holiday / not published
    except Exception as e:
        errs += 1
        print(f"{iso}: {type(e).__name__}", flush=True)
        time.sleep(3)
        if errs > 30:
            print("too many errors, stopping (resume-safe)", flush=True)
            break
    time.sleep(0.8)
    if new and len(new) % 40 == 0:
        allf = pd.concat(frames + new, ignore_index=True).drop_duplicates(["index_name", "date"])
        allf.to_parquet(OUT, index=False)
        print(f"checkpoint: +{len(new)} days pulled (through {iso}), parquet rows {len(allf)}", flush=True)

if new:
    allf = pd.concat(frames + new, ignore_index=True).drop_duplicates(["index_name", "date"])
    allf.sort_values(["index_name", "date"]).to_parquet(OUT, index=False)
    mom = allf[allf["index_name"].str.contains("Momentum", case=False, na=False)]
    print(f"DONE: {len(new)} new days, parquet rows {len(allf)}, holidays/misses {misses}", flush=True)
    print("momentum indices coverage:", flush=True)
    print(mom.groupby("index_name")["date"].agg(["min", "max", "count"]).to_string(), flush=True)
else:
    print(f"DONE: nothing new (misses {misses})", flush=True)
