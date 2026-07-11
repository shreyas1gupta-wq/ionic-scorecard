"""D-033 pull: NSE ind_close_all daily CSVs 2011->today. ALL indices incl India VIX (OHLC),
BANKNIFTY, MIDCPNIFTY + P/E, P/B, DivYield columns. Solves Phase-0 #3 (India VIX) and #5 (spot).
Resume-safe. Output: 05_DATA_OFFICE/data/indices_close/indices_{yyyy}.parquet
"""
import datetime as dt
import io, time
from pathlib import Path
import truststore
truststore.inject_into_ssl()
import pandas as pd, requests

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/indices_close"
OUT.mkdir(parents=True, exist_ok=True)
DONE = OUT / "done_dates.txt"

done = set(DONE.read_text().split()) if DONE.exists() else set()
sess = requests.Session()
sess.headers.update({"User-Agent": "Mozilla/5.0 Chrome/126", "Referer": "https://www.nseindia.com/"})
try:
    sess.get("https://www.nseindia.com", timeout=30); print("warm-up OK", flush=True)
except Exception as e:
    print(f"warm-up failed: {e}", flush=True)

buf, cur_year = [], None

def flush(y):
    if not buf:
        return
    p = OUT / f"indices_{y}.parquet"
    new = pd.concat([b.astype(str) for b in buf], ignore_index=True)
    if p.exists():
        new = pd.concat([pd.read_parquet(p).astype(str), new], ignore_index=True).drop_duplicates()
    new.to_parquet(p, index=False)
    print(f"CHECKPOINT {p.name}: {len(new)} rows", flush=True)
    buf.clear()

d, today = dt.date(2011, 1, 1), dt.date.today()
n_ok = n_miss = 0
while d <= today:
    if d.weekday() >= 5 or str(d) in done:
        d += dt.timedelta(days=1); continue
    if cur_year is not None and d.year != cur_year:
        flush(cur_year)
    cur_year = d.year
    url = f"https://archives.nseindia.com/content/indices/ind_close_all_{d:%d%m%Y}.csv"
    try:
        r = sess.get(url, timeout=45)
        if r.status_code == 200 and r.text.startswith("Index Name"):
            df = pd.read_csv(io.StringIO(r.text))
            df["file_date"] = str(d)
            buf.append(df)
            n_ok += 1
        else:
            n_miss += 1
        with open(DONE, "a", encoding="utf-8") as f:
            f.write(str(d) + "\n")
    except Exception as e:
        print(f"{d} ERR {type(e).__name__}", flush=True)
        time.sleep(5)
    if (n_ok + n_miss) % 250 == 0 and (n_ok + n_miss) > 0:
        print(f"progress {d}: ok={n_ok} miss={n_miss}", flush=True)
        flush(cur_year)
    time.sleep(0.55)
    d += dt.timedelta(days=1)
flush(cur_year)
print(f"DONE ok={n_ok} miss={n_miss}", flush=True)

# verify: India VIX COVID peak 2020-03-24 close ~ 86.6 (intraday high ~ 86)
try:
    p20 = pd.read_parquet(OUT / "indices_2020.parquet")
    vix = p20[(p20["Index Name"].str.strip() == "India VIX") & (p20.file_date.isin(["2020-03-24", "2020-03-25", "2020-03-26"]))]
    print("VERIFY India VIX 2020-03-24..26 closes:", list(vix["Closing Index Value"]), "(expect ~83-87 region)", flush=True)
except Exception as e:
    print("verify err", e, flush=True)
