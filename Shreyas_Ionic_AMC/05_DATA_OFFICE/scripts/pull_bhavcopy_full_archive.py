"""v1.1 PASS 3 -- FULL NSE bhavcopy archive pull, 2013-01-01 -> today.
Owner: Manoj Pillai (E-023). Order: Principal via coordinator 2026-07-04 (union panel v1.1,
"search for left names and download from proxy sources").

STRATEGY (per brief): don't pull per-name. Pull the FULL daily EQ-series archive ONCE and build
a permanent firm asset: datasets/nse_bhavcopy_daily/close_all.parquet (symbol, date, close,
series-EQ-only). This kills every future "is X in our data" coverage question, not just today's.

Recipe (proven, see 05_DATA_OFFICE/scripts/nse_indices_close_pull.py + bhavcopy_backfill.py):
  - truststore.inject_into_ssl() before any HTTPS (corporate proxy).
  - cookie warm-up: GET https://www.nseindia.com once before hitting nsearchives.
  - sequential requests.Session() only (threads stall on the corporate proxy).
  - ~1 req/sec (0.9s sleep) -- proxy etiquette, matches the earlier 370+-download precedent.
  - two URL formats, tried in order (old first -- covers 2013 through ~2024-06-28):
      old:  https://nsearchives.nseindia.com/content/historical/EQUITIES/{YYYY}/{MMM}/cm{DD}{MMM}{YYYY}bhav.csv.zip
      new:  https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{DDMMYYYY}.csv
    (verified empirically 2026-07-04: old format 200s through 2024-06-28, 404s by 2024-07-08;
    new format 200s from at least 2024-06-28 AND works retroactively back to today; trying old
    first is just an optimization -- if a date 404s on old, new is tried automatically.)
  - EQ-series only (SERIES=='EQ') kept; other series (BE, BZ, etc.) dropped -- this is a close
    PRICE panel, one row per (symbol,date), matching the union panel's own schema intent.
  - BACKGROUND script, resume-safe: checkpoint parquet written every 100 trading days; on
    restart, dates already in the checkpoint are skipped (idempotent, D-023 checkpoint law).
  - flush=True on every print (D-023 visibility while running as background/detached process).
  - read-only on all inputs; writes confined to datasets/nse_bhavcopy_daily/.
"""
import datetime as dt
import io
import sys
import time
import zipfile
from pathlib import Path

import truststore
truststore.inject_into_ssl()
import pandas as pd
import requests

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUTDIR = ROOT / "datasets" / "nse_bhavcopy_daily"
OUTDIR.mkdir(parents=True, exist_ok=True)
OUT_PARQUET = OUTDIR / "close_all.parquet"
LOG = OUTDIR / "pull_bhavcopy_full_archive.log"

START = dt.date(2013, 1, 1)
END = dt.date.today()

MON = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126 Safari/537.36")


def log(msg: str) -> None:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def daterange(a: dt.date, b: dt.date):
    d = a
    while d <= b:
        if d.weekday() < 5:  # weekdays only; NSE holidays 404 naturally, counted as skip
            yield d
        d += dt.timedelta(days=1)


def old_url(d: dt.date) -> str:
    m = MON[d.month - 1]
    return (f"https://nsearchives.nseindia.com/content/historical/EQUITIES/"
            f"{d.year}/{m}/cm{d.day:02d}{m}{d.year}bhav.csv.zip")


def new_url(d: dt.date) -> str:
    return (f"https://nsearchives.nseindia.com/products/content/"
            f"sec_bhavdata_full_{d.day:02d}{d.month:02d}{d.year}.csv")


def fetch_day(session: requests.Session, d: dt.date):
    """Returns a standardized DataFrame (symbol, date, close, series) for EQ rows, or None."""
    # --- try old zip format first ---
    for attempt in range(3):
        try:
            r = session.get(old_url(d), timeout=30)
        except Exception:
            time.sleep(1.5)
            continue
        if r.status_code == 200 and r.content[:2] == b"PK":
            try:
                z = zipfile.ZipFile(io.BytesIO(r.content))
                raw = pd.read_csv(z.open(z.namelist()[0]))
                raw.columns = [c.strip() for c in raw.columns]
                raw = raw[raw["SERIES"].astype(str).str.strip() == "EQ"]
                out = pd.DataFrame({
                    "symbol": raw["SYMBOL"].astype(str).str.strip().str.upper(),
                    "date": pd.Timestamp(d),
                    "close": pd.to_numeric(raw["CLOSE"], errors="coerce"),
                    "series": "EQ",
                })
                return out.dropna(subset=["close"])
            except Exception as e:
                log(f"  {d.isoformat()}: old-format parse error {type(e).__name__}: {e} -- trying new format")
                break
        elif r.status_code in (403, 401):
            log(f"  {d.isoformat()}: old-format HTTP {r.status_code} -- re-warm cookies")
            try:
                session.get("https://www.nseindia.com", timeout=15)
            except Exception:
                pass
            time.sleep(1.0)
            continue
        else:
            break  # 404 etc -- fall through to new format
    # --- try new csv format ---
    for attempt in range(3):
        try:
            r = session.get(new_url(d), timeout=30)
        except Exception:
            time.sleep(1.5)
            continue
        if r.status_code == 200 and len(r.content) > 100:
            try:
                raw = pd.read_csv(io.BytesIO(r.content))
                raw.columns = [c.strip() for c in raw.columns]
                raw = raw[raw["SERIES"].astype(str).str.strip() == "EQ"]
                out = pd.DataFrame({
                    "symbol": raw["SYMBOL"].astype(str).str.strip().str.upper(),
                    "date": pd.Timestamp(d),
                    "close": pd.to_numeric(raw["CLOSE_PRICE"], errors="coerce"),
                    "series": "EQ",
                })
                return out.dropna(subset=["close"])
            except Exception as e:
                log(f"  {d.isoformat()}: new-format parse error {type(e).__name__}: {e}")
                return None
        elif r.status_code in (403, 401):
            log(f"  {d.isoformat()}: new-format HTTP {r.status_code} -- re-warm cookies")
            try:
                session.get("https://www.nseindia.com", timeout=15)
            except Exception:
                pass
            time.sleep(1.0)
            continue
        else:
            return None  # genuine holiday / not published
    return None


def main():
    log(f"=== bhavcopy full archive pull: {START.isoformat()} -> {END.isoformat()} ===")
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "*/*"})
    try:
        s.get("https://www.nseindia.com", timeout=15)
        log("cookie warm-up OK")
    except Exception as e:
        log(f"cookie warm-up FAILED: {e} -- continuing anyway")

    have_dates = set()
    existing_frames = []
    if OUT_PARQUET.exists():
        old = pd.read_parquet(OUT_PARQUET)
        have_dates = set(pd.to_datetime(old["date"]).dt.date.astype(str))
        existing_frames.append(old)
        log(f"RESUME: {len(have_dates)} trading days already checkpointed "
            f"({len(old):,} rows, {old['symbol'].nunique():,} symbols)")

    days = [d for d in daterange(START, END) if d.isoformat() not in have_dates]
    log(f"{len(days)} trading days remaining to fetch "
        f"({len(list(daterange(START, END))) - len(days)} already done)")

    new_frames = []
    ok, holiday_or_miss, errs = 0, 0, 0
    t0 = time.time()
    for i, d in enumerate(days, 1):
        df = fetch_day(s, d)
        if df is not None and len(df):
            new_frames.append(df)
            ok += 1
        else:
            holiday_or_miss += 1
        if i % 25 == 0:
            elapsed = time.time() - t0
            log(f"  [{i}/{len(days)}] ok={ok} holiday/miss={holiday_or_miss} "
                f"elapsed={elapsed/60:.1f}min rate={i/max(elapsed,1):.2f}days/s")
        if i % 100 == 0 and new_frames:
            combo = pd.concat(existing_frames + new_frames, ignore_index=True)
            combo = combo.drop_duplicates(["symbol", "date"], keep="last")
            combo.to_parquet(OUT_PARQUET, index=False)
            log(f"  CHECKPOINT written: {len(combo):,} total rows, "
                f"{combo['symbol'].nunique():,} symbols, through {d.isoformat()}")
        time.sleep(0.9)

    if new_frames:
        combo = pd.concat(existing_frames + new_frames, ignore_index=True)
        combo = combo.drop_duplicates(["symbol", "date"], keep="last")
        combo = combo.sort_values(["symbol", "date"]).reset_index(drop=True)
        combo.to_parquet(OUT_PARQUET, index=False)
        log(f"FINAL WRITE: {len(combo):,} rows, {combo['symbol'].nunique():,} symbols, "
            f"{combo['date'].min().date()} -> {combo['date'].max().date()}")
    else:
        log("no new frames fetched this run (all dates already checkpointed, or nothing but holidays)")

    log(f"=== DONE: fetched {ok} new trading days, {holiday_or_miss} holiday/miss, "
        f"total elapsed {(time.time()-t0)/60:.1f} min ===")


if __name__ == "__main__":
    main()
