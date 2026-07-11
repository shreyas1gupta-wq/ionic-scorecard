"""D-033 pull: extend fo_idx bhavcopy 2021-07-01 -> today (completes 15yr daily index-derivs panel;
fills Kavya's 30-DTE monthly-coverage ticket from 2026-07-07 at daily granularity).
Old DERIVATIVES format through 2024-06-28; UDiFF after (columns normalized to old schema).
Resume-safe; same recipe as fo_bhavcopy_backfill_2011_2021.py.
"""
import datetime as dt
import io, time, zipfile
from pathlib import Path
import truststore
truststore.inject_into_ssl()
import pandas as pd, requests

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUTDIR = ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist"
DONE = OUTDIR / "done_dates_ext.txt"
LOG = OUTDIR / "extend.log"
START, END = dt.date(2021, 7, 1), dt.date.today()
MON = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
KEEP = ["INSTRUMENT", "SYMBOL", "EXPIRY_DT", "STRIKE_PR", "OPTION_TYP", "OPEN", "HIGH",
        "LOW", "CLOSE", "SETTLE_PR", "CONTRACTS", "OPEN_INT", "CHG_IN_OI", "TIMESTAMP"]
UDIFF_MAP = {"FinInstrmTp": "INSTRUMENT", "TckrSymb": "SYMBOL", "XpryDt": "EXPIRY_DT",
             "StrkPric": "STRIKE_PR", "OptnTp": "OPTION_TYP", "OpnPric": "OPEN", "HghPric": "HIGH",
             "LwPric": "LOW", "ClsPric": "CLOSE", "SttlmPric": "SETTLE_PR",
             "TtlTradgVol": "CONTRACTS", "OpnIntrst": "OPEN_INT", "ChngInOpnIntrst": "CHG_IN_OI",
             "TradDt": "TIMESTAMP"}

def log(m):
    line = f"{dt.datetime.now():%H:%M:%S} {m}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

done = set(DONE.read_text().split()) if DONE.exists() else set()
sess = requests.Session()
sess.headers.update({"User-Agent": "Mozilla/5.0 Chrome/126", "Referer": "https://www.nseindia.com/"})
try:
    sess.get("https://www.nseindia.com", timeout=30); log("warm-up OK")
except Exception as e:
    log(f"warm-up failed: {e}")

buf, cur_year = [], None

def flush(y):
    if not buf:
        return
    p = OUTDIR / f"fo_idx_{y}.parquet"
    new = pd.concat(buf, ignore_index=True)
    if p.exists():
        new = pd.concat([pd.read_parquet(p), new], ignore_index=True).drop_duplicates(
            subset=["TIMESTAMP", "INSTRUMENT", "SYMBOL", "EXPIRY_DT", "STRIKE_PR", "OPTION_TYP"])
    new.to_parquet(p, index=False)
    log(f"CHECKPOINT {p.name}: {len(new)} rows")
    buf.clear()

d = START
n_ok = n_404 = n_err = 0
while d <= END:
    if d.weekday() >= 5 or str(d) in done:
        d += dt.timedelta(days=1); continue
    if cur_year is not None and d.year != cur_year:
        flush(cur_year)
    cur_year = d.year
    old = (f"https://nsearchives.nseindia.com/content/historical/DERIVATIVES/"
           f"{d.year}/{MON[d.month-1]}/fo{d.day:02d}{MON[d.month-1]}{d.year}bhav.csv.zip")
    new_u = (f"https://nsearchives.nseindia.com/content/fo/"
             f"BhavCopy_NSE_FO_0_0_0_{d:%Y%m%d}_F_0000.csv.zip")  # verified 200 2026-07-11
    got = None
    try:
        for url in ([old, new_u] if d <= dt.date(2024, 6, 28) else [new_u, old]):
            r = sess.get(url, timeout=60)
            if r.status_code == 200:
                got = r; break
        if got is None:
            n_404 += 1
        else:
            with zipfile.ZipFile(io.BytesIO(got.content)) as z:
                df = pd.read_csv(z.open(z.namelist()[0]), low_memory=False)
            df.columns = [c.strip() for c in df.columns]
            if "FinInstrmTp" in df.columns:  # UDiFF
                df = df.rename(columns=UDIFF_MAP)
                df = df[df["INSTRUMENT"].isin(["IDF", "IDO"])]
                df["INSTRUMENT"] = df["INSTRUMENT"].map({"IDF": "FUTIDX", "IDO": "OPTIDX"})
                for c in ("EXPIRY_DT", "TIMESTAMP"):
                    df[c] = pd.to_datetime(df[c]).dt.strftime("%d-%b-%Y").str.upper()
            else:
                df = df[df["INSTRUMENT"].isin(["OPTIDX", "FUTIDX"])]
            cols = [c for c in KEEP if c in df.columns]
            buf.append(df[cols])
            n_ok += 1
        with open(DONE, "a", encoding="utf-8") as f:
            f.write(str(d) + "\n")
    except Exception as e:
        n_err += 1
        log(f"{d} ERR {type(e).__name__}: {str(e)[:70]}")
        time.sleep(5)
    if (n_ok + n_404) % 100 == 0 and (n_ok + n_404) > 0:
        log(f"progress {d}: ok={n_ok} 404={n_404} err={n_err}")
        flush(cur_year)
    time.sleep(0.9)
    d += dt.timedelta(days=1)
flush(cur_year)
log(f"DONE ok={n_ok} 404={n_404} err={n_err}")
