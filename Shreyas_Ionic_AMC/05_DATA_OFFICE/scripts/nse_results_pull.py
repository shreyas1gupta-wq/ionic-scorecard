# -*- coding: utf-8 -*-
"""nse_results_pull.py -- resume-safe month-by-month pull of NSE structured
financial-results filings, 2011-01 -> today, from the LIVE corporates API.

https://www.nseindia.com/api/corporates-financial-results
  params: index=equities, from_date=DD-MM-YYYY, to_date=DD-MM-YYYY, period=Quarterly|Annual

Confirmed reachable from the office proxy 2026-08-05 (probe_nse_xbrl_floor.py +
two follow-up diagnostics, not re-probed from scratch here). Both `Quarterly`
and `Annual` period values are accepted and return distinct non-zero row
counts. Empirical floor for THIS endpoint: Jan-2000 and Jan-1996 both return
200/0 rows; Jan-2009 returns 200/1312 rows -- true floor is somewhere between
2000 and 2009, i.e. comfortably below the 2011 start this script uses.

RESUME-SAFE BY DESIGN (D-033 requirement for big pulls): one raw JSON file per
(period, year, month). A file is only written AFTER a successful parse, so an
interrupted run loses at most the one in-flight month. Re-running the script
skips every month that already has a file on disk.

Every field NSE returns is kept as-is -- no column pre-filtering. Per-month
row counts are appended to pull_log.csv (success AND failure rows) so gaps
are visible without re-opening every JSON file.

Environment facts (CLAUDE.md, not re-learned here):
  - truststore.inject_into_ssl() before any HTTPS call
  - corporate proxy is slow; sequential requests.Session() only, threads stall
  - sleep >=1.5s between calls or NSE starts refusing
  - warm-up quirk: GET https://www.nseindia.com/ returns 403 but still seeds
    cookies; the second GET (the results-filter page) returns 200. Keep that
    order -- do not "fix" the 403 away.

Usage:
  python nse_results_pull.py                          # full 2011-01 -> current month, both periods
  python nse_results_pull.py --start 2011-01 --end 2011-06 --periods Quarterly   # smoke test
  python nse_results_pull.py --periods Quarterly,Annual --sleep 1.7             # explicit
"""
import argparse
import calendar
import datetime as dt
import json
import sys
import time
from pathlib import Path

import truststore

truststore.inject_into_ssl()
import requests

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT_DIR = ROOT / "datasets" / "nse_results_pit"
RAW_DIR = OUT_DIR / "raw"
LOG_PATH = OUT_DIR / "pull_log.csv"

BASE = "https://www.nseindia.com"
RESULTS_URL = BASE + "/api/corporates-financial-results"
HDRS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE + "/companies-listing/corporate-filings-financial-results",
}

DEFAULT_SLEEP = 1.7
MAX_CONSECUTIVE_FAILS = 3  # abort the run rather than hammer a refusing server


def log(msg):
    ts = dt.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def warm(s):
    for url in (BASE, BASE + "/companies-listing/corporate-filings-financial-results"):
        try:
            r = s.get(url, timeout=25)
            log(f"  warm-up {url.rsplit('/', 1)[-1] or 'home'}: {r.status_code}")
        except Exception as e:
            log(f"  warm-up failed: {type(e).__name__}: {e}")
            return False
        time.sleep(1.3)
    return True


def month_windows(start_y, start_m, end_y, end_m):
    y, m = start_y, start_m
    today = dt.date.today()
    while (y, m) <= (end_y, end_m):
        last_day = calendar.monthrange(y, m)[1]
        from_date = dt.date(y, m, 1)
        to_date = dt.date(y, m, last_day)
        if to_date > today:
            to_date = today
        if from_date <= today:
            yield y, m, from_date, to_date
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1


def fetch(s, period, from_date, to_date):
    params = dict(index="equities", from_date=from_date.strftime("%d-%m-%Y"),
                   to_date=to_date.strftime("%d-%m-%Y"), period=period)
    try:
        r = s.get(RESULTS_URL, params=params, timeout=40)
    except Exception as e:
        return None, f"EXC:{type(e).__name__}:{e}"
    if r.status_code != 200:
        return None, f"HTTP{r.status_code}"
    try:
        j = r.json()
    except Exception:
        return None, "NOTJSON"
    rows = j if isinstance(j, list) else j.get("data", j.get("resultsResponse", []))
    if not isinstance(rows, list):
        return None, f"SHAPE:{type(rows).__name__}"
    return rows, None


def append_log(row):
    hdr_needed = not LOG_PATH.exists()
    with open(LOG_PATH, "a", encoding="utf-8", newline="") as f:
        if hdr_needed:
            f.write("period,year,month,from_date,to_date,status,n_rows,ts\n")
        f.write(f"{row['period']},{row['year']},{row['month']:02d},{row['from_date']},"
                f"{row['to_date']},{row['status']},{row['n_rows']},{row['ts']}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2011-01")
    ap.add_argument("--end", default=None, help="default = current month")
    ap.add_argument("--periods", default="Quarterly,Annual")
    ap.add_argument("--sleep", type=float, default=DEFAULT_SLEEP)
    args = ap.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    sy, sm = (int(x) for x in args.start.split("-"))
    if args.end:
        ey, em = (int(x) for x in args.end.split("-"))
    else:
        today = dt.date.today()
        ey, em = today.year, today.month

    periods = [p.strip() for p in args.periods.split(",") if p.strip()]
    log(f"Plan: periods={periods} window={sy}-{sm:02d}..{ey}-{em:02d} sleep={args.sleep}s")

    s = requests.Session()
    s.headers.update(HDRS)
    log("Session warm-up:")
    if not warm(s):
        log("ABORT: warm-up failed (office proxy / network). Nothing fetched this run.")
        sys.exit(2)

    total_fetched = 0
    total_skipped = 0
    consecutive_fails = 0

    for period in periods:
        for y, m, fd, td in month_windows(sy, sm, ey, em):
            fname = RAW_DIR / f"{period.lower()}_{y:04d}_{m:02d}.json"
            if fname.exists():
                total_skipped += 1
                continue

            rows, err = fetch(s, period, fd, td)
            ts = dt.datetime.now().isoformat(timespec="seconds")

            if err:
                consecutive_fails += 1
                log(f"[{period}] {y}-{m:02d}: ERROR {err} (consecutive_fails={consecutive_fails})")
                append_log(dict(period=period, year=y, month=m, from_date=fd, to_date=td,
                                 status=err, n_rows=0, ts=ts))
                if consecutive_fails == 1:
                    # one retry after a fresh warm-up -- covers a mid-run cookie expiry
                    time.sleep(args.sleep)
                    if warm(s):
                        rows, err2 = fetch(s, period, fd, td)
                        if not err2:
                            consecutive_fails = 0
                        else:
                            log(f"  retry also failed: {err2}")
                if err and consecutive_fails >= MAX_CONSECUTIVE_FAILS:
                    log(f"ABORT: {consecutive_fails} consecutive failures -- NSE is refusing or "
                        f"network is down. Stopping so remaining months stay un-fetched for a "
                        f"clean resume, rather than hammering the server.")
                    log(f"Progress this run: fetched={total_fetched} skipped={total_skipped}")
                    sys.exit(3)
                if err:
                    time.sleep(args.sleep)
                    continue

            consecutive_fails = 0
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(rows, f, default=str)
            n = len(rows)
            total_fetched += 1
            log(f"[{period}] {y}-{m:02d}: OK rows={n}")
            append_log(dict(period=period, year=y, month=m, from_date=fd, to_date=td,
                             status="OK", n_rows=n, ts=ts))
            time.sleep(args.sleep)

    log(f"DONE. fetched_this_run={total_fetched} skipped_already_on_disk={total_skipped}")


if __name__ == "__main__":
    main()
