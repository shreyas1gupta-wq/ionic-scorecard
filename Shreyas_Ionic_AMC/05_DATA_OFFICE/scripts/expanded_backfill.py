"""Expand the universe: backfill the 122 NEW F&O single stocks (in Angel OPTSTK but not in our
88) from NSE bhavcopy, 2024-07-01..2026-06-30 (2 yrs daily), ALL expiries. Writes daily parquets
into stocks_options so the backtests AND the live daily-capture task auto-include them.
"""
import truststore; truststore.inject_into_ssl()
import requests, zipfile, io, datetime as dt, time, json
from pathlib import Path
import pandas as pd

PROJ = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
SOPT = PROJ / "intraday_options_strategy/datasets/raw/hf_index_options_1m/stocks_options"
LOG = Path("expanded_backfill.log")
scrip = json.loads(Path("scrip_master.json").read_bytes())
optstk = sorted({x["name"] for x in scrip if x.get("exch_seg") == "NFO" and x.get("instrumenttype") == "OPTSTK"})
have = {p.name for p in SOPT.iterdir() if p.is_dir()}
NEW = [s for s in optstk if s not in have]


def log(m):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now().strftime('%H:%M:%S')} {m}\n")
    print(m, flush=True)


H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36", "Accept": "*/*"}
s = requests.Session(); s.headers.update(H)
try: s.get("https://www.nseindia.com/", timeout=25)
except Exception: pass
MON = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]
NEWSET = set(NEW)


def fetch(day):
    ud = f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{day.strftime('%Y%m%d')}_F_0000.csv.zip"
    lg = f"https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{day.year}/{MON[day.month-1]}/fo{day.strftime('%d')}{MON[day.month-1]}{day.year}bhav.csv.zip"
    for url, kind in ((ud, "udiff"), (lg, "legacy")):
        for _ in range(3):
            try:
                r = s.get(url, timeout=60)
                if r.status_code == 200 and r.content[:2] == b"PK":
                    z = zipfile.ZipFile(io.BytesIO(r.content))
                    df = pd.read_csv(z.open(z.namelist()[0]))
                    return std(df, kind, day)
                elif r.status_code in (403, 404):
                    break
            except Exception:
                time.sleep(1.2)
    return None


def std(df, kind, day):
    if kind == "udiff":
        df = df[df["FinInstrmTp"] == "STO"]
        o = pd.DataFrame({"sym": df["TckrSymb"], "expiry": pd.to_datetime(df["XpryDt"]).dt.date,
                          "strike": df["StrkPric"], "option_type": df["OptnTp"], "open": df["OpnPric"],
                          "high": df["HghPric"], "low": df["LwPric"], "close": df["ClsPric"],
                          "settle": df["SttlmPric"], "volume": df["TtlTradgVol"], "oi": df["OpnIntrst"]})
    else:
        df = df[df["INSTRUMENT"] == "OPTSTK"]
        o = pd.DataFrame({"sym": df["SYMBOL"], "expiry": pd.to_datetime(df["EXPIRY_DT"]).dt.date,
                          "strike": df["STRIKE_PR"], "option_type": df["OPTION_TYP"], "open": df["OPEN"],
                          "high": df["HIGH"], "low": df["LOW"], "close": df["CLOSE"], "settle": df["SETTLE_PR"],
                          "volume": df["CONTRACTS"], "oi": df["OPEN_INT"]})
    o = o[o["sym"].isin(NEWSET)]
    o["trading_day"] = day.isoformat()
    o["timestamp"] = pd.Timestamp(day) + pd.Timedelta(hours=15, minutes=30)
    return o


def drange(a, b):
    d = a
    while d <= b:
        if d.weekday() < 5:
            yield d
        d += dt.timedelta(days=1)


if __name__ == "__main__":
    days = list(drange(dt.date(2024, 7, 1), dt.date(2026, 6, 30)))
    log(f"=== EXPANDED backfill: {len(NEW)} new stocks, {len(days)} days (2024-07..2026-06) ===")
    frames = []; ok = 0; miss = 0
    for i, day in enumerate(days, 1):
        df = fetch(day)
        if df is not None and len(df):
            frames.append(df); ok += 1
        else:
            miss += 1
        if i % 40 == 0:
            log(f"  [{i}/{len(days)}] ok={ok} miss={miss} rows={sum(len(f) for f in frames)}")
        time.sleep(0.12)
    allrows = pd.concat(frames, ignore_index=True)
    log(f"downloaded {ok} days; total new-stock rows {len(allrows)}; writing...")
    written = 0
    for (sym, expiry), g in allrows.groupby(["sym", "expiry"]):
        g = g.drop(columns=["sym", "expiry"]).sort_values(["trading_day", "strike", "option_type"])
        (SOPT / sym).mkdir(parents=True, exist_ok=True)
        g.to_parquet(SOPT / sym / f"{expiry.isoformat()}.parquet")
        written += 1
    nstk = len({p.name for p in SOPT.iterdir() if p.is_dir()})
    log(f"=== DONE: wrote {written} parquets; universe now {nstk} stocks ===")
