"""Backfill the missing single-stock option months from NSE UDiFF/legacy F&O bhavcopy.
Downloads every trading day 2024-04-01..2025-08-31 + 2026-06, keeps OPTSTK rows for our 88
stocks whose EXPIRY falls in a missing month, and writes DAILY-granularity parquets into the
main stocks_options dir (schema compatible with the EOD backtests). Only gap expiries; never
clobbers existing 1-min files.
"""
import truststore; truststore.inject_into_ssl()
import requests, zipfile, io, datetime as dt, time
from pathlib import Path
import pandas as pd

PROJ = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
SOPT = PROJ / "intraday_options_strategy/datasets/raw/hf_index_options_1m/stocks_options"
LOG = Path("backfill.log")
stocks = sorted({p.name for p in SOPT.iterdir() if p.is_dir()})
existing = {s: {p.stem for p in (SOPT / s).glob("*.parquet")} for s in stocks}

GAP_MONTHS = {(2024, m) for m in range(4, 13)} | {(2025, m) for m in range(1, 9)} | {(2026, 6)}


def log(m):
    ts = dt.datetime.now().strftime("%H:%M:%S")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{ts} {m}\n")
    print(f"{ts} {m}", flush=True)


H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36", "Accept": "*/*"}
s = requests.Session(); s.headers.update(H)
try: s.get("https://www.nseindia.com/", timeout=25)
except Exception: pass

MON = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]


def fetch(day):
    """Return standardized DataFrame for a trading day, or None (holiday/missing)."""
    ud = f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{day.strftime('%Y%m%d')}_F_0000.csv.zip"
    lg = f"https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{day.year}/{MON[day.month-1]}/fo{day.strftime('%d')}{MON[day.month-1]}{day.year}bhav.csv.zip"
    for url, kind in ((ud, "udiff"), (lg, "legacy")):
        for _ in range(3):
            try:
                r = s.get(url, timeout=60)
                if r.status_code == 200 and r.content[:2] == b"PK":
                    z = zipfile.ZipFile(io.BytesIO(r.content))
                    df = pd.read_csv(z.open(z.namelist()[0]))
                    return standardize(df, kind, day)
                elif r.status_code in (403, 404):
                    break
            except Exception:
                time.sleep(1.5)
    return None


def standardize(df, kind, day):
    if kind == "udiff":
        df = df[df["FinInstrmTp"] == "STO"]
        out = pd.DataFrame({
            "sym": df["TckrSymb"], "expiry": pd.to_datetime(df["XpryDt"]).dt.date,
            "strike": df["StrkPric"], "option_type": df["OptnTp"],
            "open": df["OpnPric"], "high": df["HghPric"], "low": df["LwPric"],
            "close": df["ClsPric"], "settle": df["SttlmPric"],
            "volume": df["TtlTradgVol"], "oi": df["OpnIntrst"]})
    else:  # legacy
        df = df[df["INSTRUMENT"] == "OPTSTK"]
        out = pd.DataFrame({
            "sym": df["SYMBOL"], "expiry": pd.to_datetime(df["EXPIRY_DT"]).dt.date,
            "strike": df["STRIKE_PR"], "option_type": df["OPTION_TYP"],
            "open": df["OPEN"], "high": df["HIGH"], "low": df["LOW"],
            "close": df["CLOSE"], "settle": df["SETTLE_PR"],
            "volume": df["CONTRACTS"], "oi": df["OPEN_INT"]})
    out = out[out["sym"].isin(stocks)]
    out = out[out["expiry"].map(lambda e: (e.year, e.month) in GAP_MONTHS)]
    out["trading_day"] = day.isoformat()
    out["timestamp"] = pd.Timestamp(day) + pd.Timedelta(hours=15, minutes=30)
    return out


def daterange(a, b):
    d = a
    while d <= b:
        if d.weekday() < 5:
            yield d
        d += dt.timedelta(days=1)


if __name__ == "__main__":
    days = list(daterange(dt.date(2024, 4, 1), dt.date(2025, 8, 31))) + \
           list(daterange(dt.date(2026, 6, 1), dt.date(2026, 6, 30)))
    log(f"=== bhavcopy backfill: {len(days)} trading days, {len(stocks)} stocks, gap expiries only ===")
    frames = []; ok = 0; miss = 0
    for i, day in enumerate(days, 1):
        df = fetch(day)
        if df is not None and len(df):
            frames.append(df); ok += 1
        else:
            miss += 1
        if i % 25 == 0:
            log(f"  [{i}/{len(days)}] fetched={ok} holiday/miss={miss} rows so far={sum(len(f) for f in frames)}")
        time.sleep(0.15)
    log(f"downloaded {ok} days ({miss} skipped). concatenating...")
    if not frames:
        log("NO DATA — abort"); raise SystemExit
    allrows = pd.concat(frames, ignore_index=True)
    log(f"total gap-expiry option rows: {len(allrows)}")
    written = 0
    for (sym, expiry), g in allrows.groupby(["sym", "expiry"]):
        estr = expiry.isoformat()
        if estr in existing.get(sym, set()):
            continue                      # never clobber existing 1-min data
        g = g.drop(columns=["sym", "expiry"]).sort_values(["trading_day", "strike", "option_type"])
        (SOPT / sym).mkdir(parents=True, exist_ok=True)
        g.to_parquet(SOPT / sym / f"{estr}.parquet")
        written += 1
    log(f"=== BACKFILL COMPLETE: wrote {written} (sym,expiry) daily parquets into stocks_options ===")
    # report new coverage
    allexp = set()
    for st in stocks:
        for p in (SOPT / st).glob("*.parquet"):
            allexp.add(p.stem)
    yrs = {}
    for e in allexp:
        y = e[:4]; yrs[y] = yrs.get(y, 0) + 0
    from collections import Counter
    c = Counter(e[:4] for e in allexp) if False else None
    log("new distinct expiries: " + str(sorted(allexp)))
