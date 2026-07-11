"""D-033/B1 pull: NSE participant-wise OI daily CSVs, 2018-01 -> today.
URL verified live in citation pass: archives.nseindia.com/content/nsccl/fao_participant_oi_DDMMYYYY.csv
Tiny files (~2KB). Resume-safe via done-ledger. Schema drift tolerated: raw columns kept per day,
normalized later (format-break map = Kavya follow-up per MASTER_PLAN Phase-0 #4).
Output: 05_DATA_OFFICE/data/participant_oi/participant_oi_{yyyy}.parquet
"""
import datetime as dt
import io, time
from pathlib import Path
import truststore
truststore.inject_into_ssl()
import pandas as pd, requests

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/participant_oi"
OUT.mkdir(parents=True, exist_ok=True)
DONE = OUT / "done_dates.txt"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126",
      "Referer": "https://www.nseindia.com/"}

done = set(DONE.read_text().split()) if DONE.exists() else set()
sess = requests.Session(); sess.headers.update(UA)
try:
    sess.get("https://www.nseindia.com", timeout=30)
    print("warm-up OK", flush=True)
except Exception as e:
    print(f"warm-up failed (continuing): {e}", flush=True)

buf, cur_year = [], None

def flush(y):
    if not buf:
        return
    p = OUT / f"participant_oi_{y}.parquet"
    new = pd.concat([b.astype(str) for b in buf], ignore_index=True)
    if p.exists():
        new = pd.concat([pd.read_parquet(p).astype(str), new], ignore_index=True).drop_duplicates()
    new.to_parquet(p, index=False)
    print(f"CHECKPOINT {p.name}: {len(new)} rows", flush=True)
    buf.clear()

d = dt.date(2018, 1, 1)
today = dt.date.today()
n_ok = n_miss = 0
while d <= today:
    if d.weekday() >= 5 or str(d) in done:
        d += dt.timedelta(days=1); continue
    if cur_year is not None and d.year != cur_year:
        flush(cur_year)
    cur_year = d.year
    url = f"https://archives.nseindia.com/content/nsccl/fao_participant_oi_{d:%d%m%Y}.csv"
    try:
        r = sess.get(url, timeout=45)
        if r.status_code == 200 and len(r.content) > 100:
            # first line is a title row in most vintages; sniff header line
            txt = r.text
            skip = 1 if not txt.splitlines()[0].lower().startswith("client") and "future" not in txt.splitlines()[0].lower() else 0
            df = pd.read_csv(io.StringIO(txt), skiprows=skip)
            df.columns = [str(c).strip() for c in df.columns]
            df["file_date"] = str(d)
            buf.append(df)
            n_ok += 1
        else:
            n_miss += 1
        with open(DONE, "a", encoding="utf-8") as f:
            f.write(str(d) + "\n")
    except Exception as e:
        print(f"{d} ERR {type(e).__name__}: {str(e)[:70]}", flush=True)
        time.sleep(5)
    if (n_ok + n_miss) % 200 == 0 and (n_ok + n_miss) > 0:
        print(f"progress {d}: ok={n_ok} miss={n_miss}", flush=True)
        flush(cur_year)
    time.sleep(0.6)
    d += dt.timedelta(days=1)
flush(cur_year)
print(f"DONE ok={n_ok} miss={n_miss}", flush=True)

# verification: FII index-futures rows should exist for a known date
try:
    p21 = pd.read_parquet(OUT / "participant_oi_2021.parquet")
    chk = p21[p21.file_date == "2021-07-02"]
    print("VERIFY 2021-07-02 rows:", len(chk), "| cols:", list(p21.columns)[:8], flush=True)
except Exception as e:
    print("verify err", e, flush=True)
