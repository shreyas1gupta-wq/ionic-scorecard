"""Pull official NSE index daily closes via Angel SmartAPI (proxy-proof — office network OK).
Indices incl. INDIA VIX + factor indices Angel carries; plus momentum-ETF proxies (equity tokens).
Output: datasets/index_daily/{slug}.parquet (merge-dedupe). D-009: Angel = already-approved source.
"""
import sys, time, json, datetime as dt
from pathlib import Path
import pandas as pd

sys.path.insert(0, r"C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture")
import angel_cfg

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "datasets/index_daily"; OUT.mkdir(parents=True, exist_ok=True)

INDICES = {  # name -> (exchange, token)
    "india_vix":        ("NSE", "99926017"),
    "nifty50":          ("NSE", "99926000"),
    "nifty500":         ("NSE", "99926004"),
    "banknifty":        ("NSE", "99926009"),
    "midcap150":        ("NSE", "99926060"),
    "lowvol30":         ("NSE", "99926058"),   # NIFTY100 LOWVOL30
    "alpha50":          ("NSE", "99926059"),   # NIFTY ALPHA 50
    "value20":          ("NSE", "99926045"),   # NIFTY50 VALUE 20
}
YEARS = list(range(2016, 2027))
COLS = ["timestamp", "open", "high", "low", "close", "volume"]

obj, sess = angel_cfg.login(); print("login OK", flush=True)

# momentum-ETF proxies: find in scrip master
scrip = json.loads(Path(r"C:\Users\SHREYA~1.1GU\AppData\Local\Temp\claude\c--Users-Shreyas-1Gupta-OneDrive---Angel-Broking-Limited-Desktop-Backup-NIFTY-500\d096bfac-0d55-4716-97ef-0deefc915522\scratchpad\scrip_master.json").read_bytes())
import re
etf_pat = re.compile(r"MOM(ENTUM)?(30|50)|MULTIMOM", re.I)
etfs = {x["symbol"].replace("-EQ", "").lower(): ("NSE", x["token"]) for x in scrip
        if x.get("exch_seg") == "NSE" and x.get("symbol", "").endswith("-EQ") and etf_pat.search(x.get("symbol", ""))}
print("momentum ETF proxies found:", list(etfs)[:6], flush=True)
INDICES.update({f"etf_{k}": v for k, v in etfs.items()})

for slug, (exch, tok) in INDICES.items():
    frames = []
    for y in YEARS:
        try:
            r = obj.getCandleData({"exchange": exch, "symboltoken": tok, "interval": "ONE_DAY",
                                   "fromdate": f"{y}-01-01 09:15", "todate": f"{y}-12-31 15:30"})
            d = r.get("data") or []
            if d:
                frames.append(pd.DataFrame(d, columns=COLS))
        except Exception as e:
            print(f"  warn {slug} {y}: {str(e)[:50]}", flush=True)
        time.sleep(1.25)
    if not frames:
        print(f"  NONE for {slug}", flush=True); continue
    df = pd.concat(frames, ignore_index=True).drop_duplicates("timestamp")
    p = OUT / f"{slug}.parquet"
    if p.exists():
        old = pd.read_parquet(p)
        df = pd.concat([old, df]).drop_duplicates("timestamp")
    df = df.sort_values("timestamp")
    df.to_parquet(p)
    print(f"  saved {slug}: {len(df)} rows {df['timestamp'].iloc[0][:10]} -> {df['timestamp'].iloc[-1][:10]}", flush=True)
print("DONE", flush=True)
