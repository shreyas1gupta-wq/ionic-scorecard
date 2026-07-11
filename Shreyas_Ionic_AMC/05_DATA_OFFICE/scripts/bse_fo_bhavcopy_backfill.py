"""D-033 pull: BSE F&O UDiFF bhavcopy 2023-05-01 -> today (SENSEX/BANKEX weekly options era).
Index derivatives only. Output: 05_DATA_OFFICE/data/bse_fo_bhavcopy/bse_fo_{yyyy}.parquet
"""
import datetime as dt
import io, time
from pathlib import Path
import truststore
truststore.inject_into_ssl()
import pandas as pd, requests

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/bse_fo_bhavcopy"
OUT.mkdir(parents=True, exist_ok=True)
DONE = OUT / "done_dates.txt"
KEEP = ["TradDt", "FinInstrmTp", "TckrSymb", "XpryDt", "StrkPric", "OptnTp", "OpnPric",
        "HghPric", "LwPric", "ClsPric", "SttlmPric", "TtlTradgVol", "OpnIntrst", "ChngInOpnIntrst"]

done = set(DONE.read_text().split()) if DONE.exists() else set()
sess = requests.Session(); sess.headers.update({"User-Agent": "Mozilla/5.0 Chrome/126"})
buf, cur_year = [], None

def flush(y):
    if not buf:
        return
    p = OUT / f"bse_fo_{y}.parquet"
    new = pd.concat(buf, ignore_index=True)
    if p.exists():
        new = pd.concat([pd.read_parquet(p), new], ignore_index=True).drop_duplicates(
            subset=["TradDt", "TckrSymb", "XpryDt", "StrkPric", "OptnTp", "FinInstrmTp"])
    new.to_parquet(p, index=False)
    print(f"CHECKPOINT {p.name}: {len(new)} rows", flush=True)
    buf.clear()

d, today = dt.date(2023, 5, 1), dt.date.today()
n_ok = n_miss = 0
while d <= today:
    if d.weekday() >= 5 or str(d) in done:
        d += dt.timedelta(days=1); continue
    if cur_year is not None and d.year != cur_year:
        flush(cur_year)
    cur_year = d.year
    url = f"https://www.bseindia.com/download/Bhavcopy/Derivative/BhavCopy_BSE_FO_0_0_0_{d:%Y%m%d}_F_0000.CSV"
    try:
        r = sess.get(url, timeout=60)
        if r.status_code == 200 and r.text.startswith("TradDt"):
            df = pd.read_csv(io.StringIO(r.text), low_memory=False)
            df = df[df["FinInstrmTp"].isin(["IDO", "IDF"])]
            cols = [c for c in KEEP if c in df.columns]
            buf.append(df[cols])
            n_ok += 1
        else:
            n_miss += 1
        with open(DONE, "a", encoding="utf-8") as f:
            f.write(str(d) + "\n")
    except Exception as e:
        print(f"{d} ERR {type(e).__name__}", flush=True)
        time.sleep(5)
    if (n_ok + n_miss) % 150 == 0 and (n_ok + n_miss) > 0:
        print(f"progress {d}: ok={n_ok} miss={n_miss}", flush=True)
        flush(cur_year)
    time.sleep(0.7)
    d += dt.timedelta(days=1)
flush(cur_year)
print(f"DONE ok={n_ok} miss={n_miss}", flush=True)
try:
    p = pd.read_parquet(OUT / "bse_fo_2026.parquet")
    sx = p[(p.TckrSymb == "SENSEX") & (p.FinInstrmTp == "IDO")]
    print(f"VERIFY 2026: SENSEX option rows={len(sx)}, expiries={sx.XpryDt.nunique()}", flush=True)
except Exception as e:
    print("verify err", e, flush=True)
