"""Nifty factor-index downloader (Principal-contributed scraper, firm-adapted 2026-07-04).
Source: niftyindices.com Backpage API. D-009 note: source approved by Principal directly.
Adaptations: truststore (corporate proxy), parquet output (long format) + optional xlsx,
CLI dates, chunked politeness. Recurring use: /factor-indices skill (monthly refresh).
Usage: python nifty_indices_download.py [START DD-Mon-YYYY] [END DD-Mon-YYYY] [--xlsx]
"""
import json
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import truststore; truststore.inject_into_ssl()
import pandas as pd
import requests

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUTDIR = ROOT / "datasets/nifty_factor_indices"; OUTDIR.mkdir(parents=True, exist_ok=True)

INDICES = [
    # broad
    "NIFTY 50", "NIFTY 100", "NIFTY LARGEMID250", "NIFTY 500", "NIFTY MIDCAP 150",
    "NIFTY SMLCAP 100", "NIFTY SMALLCAP 250", "NIFTY500 MULTICAP",
    # factor
    "NIFTY100 LOWVOL30", "NIFTY200 QUALITY 30", "NIFTY200 VALUE 30", "NIFTY200MOMENTM30",
    "NIFTY200 ALPHA 30", "NIFTY500 MOMENTUM 50", "NIFTY500 VALUE 50",
    "NIFTY MIDCAP150 MOMENTUM 50", "NIFTY SMALLCAP250 MOMENTUM QUALITY 100", "NIFTY HIGH BETA 50",
    # equal weight / value
    "NIFTY TOP 10 EQUAL WEIGHT", "NIFTY TOP 20 EQUAL WEIGHT", "NIFTY50 VALUE 20",
]
BASE = "https://www.niftyindices.com"
REFERER = f"{BASE}/reports/historical-data"
API = f"{BASE}/Backpage.aspx/getHistoricaldatatabletoString"


def session_():
    s = requests.Session()
    # headers synced EXACTLY to the Principal's reference downloader (2026-07-26) —
    # the missing Sec-Fetch-* trio + Accept-Encoding made the WAF serve an HTML shell
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
                      "Accept-Language": "en-US,en;q=0.9", "Accept-Encoding": "gzip, deflate, br",
                      "Connection": "keep-alive"})
    r = s.get(REFERER, timeout=30); r.raise_for_status()
    return s


def fetch(s, name, start, end):
    payload = {"cinfo": json.dumps({"name": name, "startDate": start, "endDate": end, "indexName": name})}
    h = {"Accept": "application/json, text/javascript, */*; q=0.01", "Content-Type": "application/json; charset=UTF-8",
         "Referer": REFERER, "Origin": BASE, "X-Requested-With": "XMLHttpRequest",
         "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-origin"}
    try:
        r = s.post(API, json=payload, headers=h, timeout=30); r.raise_for_status()
        rows = json.loads(r.json().get("d", "[]"))
    except Exception as e:
        print(f"  WARN {name}: {type(e).__name__} {str(e)[:60]}"); return []
    out = []
    for row in rows:
        dk = next((k for k in row if "date" in k.lower()), None)
        ck = next((k for k in row if "close" in k.lower()), None)
        if dk and ck:
            try:
                out.append({"index": name, "date_raw": row[dk], "close": float(str(row[ck]).replace(",", ""))})
            except ValueError:
                pass
    print(f"  OK {name:<42} {len(out):>4} rows")
    return out


def parse_date(d):
    for fmt in ("%d %b %Y", "%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y"):
        try:
            return datetime.strptime(d, fmt)
        except ValueError:
            pass
    return pd.NaT


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    start = args[0] if args else "01-Jan-2015"
    end = args[1] if len(args) > 1 else datetime.now().strftime("%d-%b-%Y")
    print(f"nifty factor indices: {start} -> {end}")
    s = session_()
    all_rows = []
    for idx in INDICES:
        all_rows += fetch(s, idx, start, end)
        time.sleep(0.5)
    if not all_rows:
        sys.exit("NOTHING fetched — likely proxy-blocked; run from home network or check cookies")
    df = pd.DataFrame(all_rows)
    df["date"] = df["date_raw"].map(parse_date)
    df = df.dropna(subset=["date"]).drop(columns=["date_raw"]).sort_values(["index", "date"])
    out = OUTDIR / "factor_indices_close.parquet"
    if out.exists():  # merge-dedupe for incremental refreshes
        old = pd.read_parquet(out)
        df = pd.concat([old, df]).drop_duplicates(["index", "date"], keep="last").sort_values(["index", "date"])
    df.to_parquet(out)
    print(f"saved {out} ({len(df)} rows, {df['index'].nunique()} indices, {df['date'].min().date()} -> {df['date'].max().date()})")
    if "--xlsx" in sys.argv:
        wide = df.pivot_table("close", "date", "index")
        wide.to_excel(OUTDIR / "factor_indices_close.xlsx")
        print("xlsx written")
