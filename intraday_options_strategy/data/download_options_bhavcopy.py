"""Download NSE F&O EOD bhavcopy (real option settlement prices + OI).

Used to calibrate the real ATM-IV / India-VIX multiplier by DTE, which is the
single unknown gating the 0DTE short-premium edge (see results/V2_REPORT.md).

EOD bhavcopy gives end-of-day settlement price per contract → we back out IV
for ATM options with DTE >= 1 (expiry-day EOD is pure intrinsic, useless for
IV; the m(DTE) curve is extrapolated to DTE->0).

NSE blocks bare requests: we prime cookies via a homepage GET with browser
headers, use truststore for the corporate-proxy CA, and fast-fail per URL.

Usage:
  python data/download_options_bhavcopy.py probe          # 1 date connectivity test
  python data/download_options_bhavcopy.py bulk 2024-01-01 2025-12-31 7
                                          # start end step_days(sampling)
"""
from __future__ import annotations

import io
import sys
import time
import zipfile
from datetime import timedelta
from pathlib import Path

import truststore
truststore.inject_into_ssl()

import pandas as pd  # noqa: E402
import requests  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402

OUT = RAW_DIR / "options"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
# UDiFF format (2024-07-08 onward) and legacy format (before)
UDIFF = "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{ymd}_F_0000.csv.zip"
LEGACY = ("https://nsearchives.nseindia.com/content/historical/DERIVATIVES/"
          "{Y}/{Mon}/fo{d:02d}{Mon}{Y}bhav.csv.zip")
UDIFF_START = pd.Timestamp("2024-07-08")


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    try:
        s.get("https://www.nseindia.com", timeout=10)              # prime cookies
        s.get("https://www.nseindia.com/all-reports-derivatives", timeout=10)
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] cookie prime failed: {str(exc)[:120]}")
    return s


def _url(day: pd.Timestamp) -> str:
    if day >= UDIFF_START:
        return UDIFF.format(ymd=day.strftime("%Y%m%d"))
    return LEGACY.format(Y=day.year, Mon=day.strftime("%b").upper(), d=day.day)


def fetch_one(s: requests.Session, day: pd.Timestamp) -> str:
    dest = OUT / f"fo_{day.strftime('%Y%m%d')}.csv"
    if dest.exists():
        return "cached"
    try:
        r = s.get(_url(day), timeout=20)
        if r.status_code != 200 or len(r.content) < 500:
            return f"http {r.status_code} / {len(r.content)}B"
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            name = z.namelist()[0]
            df = pd.read_csv(z.open(name))
        # keep only NIFTY/BANKNIFTY index options (drops ~95% of rows/size)
        if "TckrSymb" in df.columns and "OptnTp" in df.columns:
            df = df[df["TckrSymb"].isin(["NIFTY", "BANKNIFTY"])
                    & df["OptnTp"].isin(["CE", "PE"])]
        OUT.mkdir(parents=True, exist_ok=True)
        df.to_csv(dest, index=False)
        return f"OK {len(df)} idx-opt rows"
    except Exception as exc:  # noqa: BLE001
        return f"ERR {type(exc).__name__}: {str(exc)[:120]}"


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "probe"
    s = _session()
    if mode == "probe":
        for back in (3, 4, 5, 6, 7, 10, 14):
            day = pd.Timestamp.now().normalize() - timedelta(days=back)
            if day.weekday() >= 5:
                continue
            print(f"{day.date()} ({_url(day).split('/')[-1]}): {fetch_one(s, day)}")
    elif mode == "bulk":
        start, end = pd.Timestamp(sys.argv[2]), pd.Timestamp(sys.argv[3])
        step = int(sys.argv[4]) if len(sys.argv) > 4 else 7
        days = pd.bdate_range(start, end)[::step]
        ok = 0
        for i, day in enumerate(days):
            res = fetch_one(s, day)
            if res.startswith(("OK", "cached")):
                ok += 1
            if i % 10 == 0 or res.startswith("ERR"):
                print(f"[{i+1}/{len(days)}] {day.date()}: {res}", flush=True)
            if i % 25 == 24:
                s = _session()                                     # refresh cookies
            time.sleep(0.4)
        print(f"\nDONE: {ok}/{len(days)} files in {OUT}")
    print("done")


if __name__ == "__main__":
    main()
