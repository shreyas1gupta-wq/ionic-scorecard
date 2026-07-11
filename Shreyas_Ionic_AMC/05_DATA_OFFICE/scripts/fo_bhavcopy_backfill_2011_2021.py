"""D-033/A4 pull: NSE F&O bhavcopy 2011-01-01 -> 2021-06-30, INDEX derivatives only.
Adapts the proven recipe from pull_bhavcopy_full_archive.py (2026-07-04, 370+ downloads):
truststore, cookie warm-up, sequential session, ~1 req/s, old DERIVATIVES URL format
(valid through 2024-06; our whole window uses it). Resume-safe: per-year parquet
checkpoints + done-dates ledger. Keeps INSTRUMENT in {OPTIDX, FUTIDX} (all index
underlyings) — the A4 COVID-replication card needs NIFTY monthly options + futures.
Output: Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist/fo_idx_{YYYY}.parquet
"""
import datetime as dt
import io
import time
import zipfile
from pathlib import Path

import truststore
truststore.inject_into_ssl()
import pandas as pd
import requests

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUTDIR = ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist"
OUTDIR.mkdir(parents=True, exist_ok=True)
DONE = OUTDIR / "done_dates.txt"
LOG = OUTDIR / "backfill.log"

START, END = dt.date(2011, 1, 1), dt.date(2021, 6, 30)
MON = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126 Safari/537.36")
KEEP = ["INSTRUMENT", "SYMBOL", "EXPIRY_DT", "STRIKE_PR", "OPTION_TYP", "OPEN", "HIGH",
        "LOW", "CLOSE", "SETTLE_PR", "CONTRACTS", "OPEN_INT", "CHG_IN_OI", "TIMESTAMP"]

def log(msg):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

done = set()
if DONE.exists():
    done = set(DONE.read_text().split())

sess = requests.Session()
sess.headers.update({"User-Agent": UA, "Referer": "https://www.nseindia.com/"})
try:
    sess.get("https://www.nseindia.com", timeout=30)
    log("cookie warm-up OK")
except Exception as e:
    log(f"warm-up failed (continuing): {e}")

year_buf, cur_year = [], None

def flush_year(y):
    if not year_buf:
        return
    p = OUTDIR / f"fo_idx_{y}.parquet"
    new = pd.concat(year_buf, ignore_index=True)
    if p.exists():
        old = pd.read_parquet(p)
        new = pd.concat([old, new], ignore_index=True).drop_duplicates(
            subset=["TIMESTAMP", "INSTRUMENT", "SYMBOL", "EXPIRY_DT", "STRIKE_PR", "OPTION_TYP"])
    new.to_parquet(p, index=False)
    log(f"CHECKPOINT {p.name}: {len(new)} rows total")
    year_buf.clear()

d = START
n_ok = n_404 = n_err = 0
while d <= END:
    if d.weekday() >= 5 or str(d) in done:
        d += dt.timedelta(days=1)
        continue
    if cur_year is not None and d.year != cur_year:
        flush_year(cur_year)
    cur_year = d.year
    url = (f"https://nsearchives.nseindia.com/content/historical/DERIVATIVES/"
           f"{d.year}/{MON[d.month-1]}/fo{d.day:02d}{MON[d.month-1]}{d.year}bhav.csv.zip")
    try:
        r = sess.get(url, timeout=60)
        if r.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                df = pd.read_csv(z.open(z.namelist()[0]))
            df.columns = [c.strip() for c in df.columns]
            df = df[df["INSTRUMENT"].isin(["OPTIDX", "FUTIDX"])]
            cols = [c for c in KEEP if c in df.columns]
            year_buf.append(df[cols])
            n_ok += 1
        elif r.status_code == 404:
            n_404 += 1  # holiday
        else:
            n_err += 1
            log(f"{d} HTTP {r.status_code}")
        with open(DONE, "a", encoding="utf-8") as f:
            f.write(str(d) + "\n")
    except Exception as e:
        n_err += 1
        log(f"{d} ERR {type(e).__name__}: {e}")
        time.sleep(5)  # do not mark done -> retried on resume
    if (n_ok + n_404) % 100 == 0 and (n_ok + n_404) > 0:
        log(f"progress {d}: ok={n_ok} holiday404={n_404} err={n_err}")
        flush_year(cur_year)
    time.sleep(0.9)
    d += dt.timedelta(days=1)

flush_year(cur_year)
log(f"DONE: ok={n_ok} holiday404={n_404} err={n_err}")
