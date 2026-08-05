# -*- coding: utf-8 -*-
"""probe_nse_xbrl_floor.py - how far back does NSE serve STRUCTURED financial results?

Purpose: decide whether scaling the existing XBRL pull (35 symbols today, with a real
`intimation_date`) can reach the Principal's 15-year requirement, or whether a commercial source is
the only route. This is a PROBE, not a downloader - it fetches a handful of windows and reports what
came back. Nothing is written to any dataset.

Why a probe rather than an assertion: XBRL for financial results was mandated in phases, so the
historical floor is an empirical question. Guessing it and then building a scraper against the guess
is how a week gets wasted.

Environment facts from CLAUDE.md, not rediscovered here:
  - truststore.inject_into_ssl() before any HTTPS
  - corporate proxy is slow; sequential requests.Session() only, threads stall
  - NSE needs a cookie warm-up GET on the homepage first
  - some /api endpoints 403 at the office and need home network; that is a possible outcome here
    and is reported as such rather than treated as "no data exists"
"""
import datetime as dt
import json
import sys
import time

import truststore
truststore.inject_into_ssl()
import requests

BASE = "https://www.nseindia.com"
RESULTS = BASE + "/api/corporates-financial-results"
HDRS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE + "/companies-listing/corporate-filings-financial-results",
}

# one window per year, always a results season (Jul = Q1 filings), oldest first so the floor shows
YEARS = [2011, 2013, 2015, 2017, 2018, 2019, 2020, 2022, 2024, 2026]


def warm(s):
    for url in (BASE, BASE + "/companies-listing/corporate-filings-financial-results"):
        try:
            r = s.get(url, timeout=25)
            print(f"  warm-up {url.rsplit('/', 1)[-1] or 'home'}: {r.status_code}")
        except Exception as e:
            print(f"  warm-up failed: {type(e).__name__}: {e}")
            return False
        time.sleep(1.2)
    return True


def probe(s, year):
    p = dict(index="equities", from_date=f"01-07-{year}", to_date=f"31-07-{year}",
             period="Quarterly")
    try:
        r = s.get(RESULTS, params=p, timeout=35)
    except Exception as e:
        return dict(year=year, status="EXC", detail=f"{type(e).__name__}: {e}")
    if r.status_code != 200:
        return dict(year=year, status=r.status_code, detail=r.text[:90].replace("\n", " "))
    try:
        j = r.json()
    except Exception:
        return dict(year=year, status="NOTJSON", detail=r.text[:90].replace("\n", " "))
    rows = j if isinstance(j, list) else j.get("data", j.get("resultsResponse", []))
    if not isinstance(rows, list):
        return dict(year=year, status="SHAPE", detail=str(type(rows))[:60])
    n = len(rows)
    sample = rows[0] if n else {}
    # the two fields that decide whether this source is usable at all
    has_xbrl = any(k for k in sample if "xbrl" in str(k).lower())
    date_keys = [k for k in sample
                 if any(t in str(k).lower() for t in ("date", "broadcast", "intimation", "submit"))]
    return dict(year=year, status=200, rows=n, has_xbrl=has_xbrl,
                date_keys=date_keys[:4], keys=list(sample.keys())[:10])


def main():
    s = requests.Session()
    s.headers.update(HDRS)
    print("NSE structured-results probe (read-only, nothing saved)")
    if not warm(s):
        print("\nVERDICT: could not establish a session. Office proxy or network. "
              "Re-run from home network before concluding anything about the data.")
        return 2

    out = []
    for y in YEARS:
        r = probe(s, y)
        out.append(r)
        if r.get("status") == 200:
            print(f"  {y}: 200  rows={r['rows']:5d}  xbrl_field={r['has_xbrl']}  "
                  f"date_fields={r['date_keys']}")
        else:
            print(f"  {y}: {r['status']}  {str(r.get('detail'))[:70]}")
        time.sleep(1.5)                      # rate-limit courtesy, sequential by design

    ok = [r for r in out if r.get("status") == 200 and r.get("rows", 0) > 0]
    print("\n" + "=" * 74)
    if not ok:
        codes = {r.get("status") for r in out}
        print(f"VERDICT: no year returned rows. Status codes seen: {codes}.")
        print("  If these are 401/403, it is the office proxy, NOT absence of data - retry from")
        print("  home network. Do not conclude the source is unusable from an office run.")
    else:
        floor = min(r["year"] for r in ok)
        print(f"VERDICT: structured results returned for {sorted(r['year'] for r in ok)}")
        print(f"  earliest year with rows: {floor}")
        span = 2026 - floor
        print(f"  implied usable span: ~{span} years")
        if span >= 15:
            print("  -> MEETS the 15-year requirement. Scaling the XBRL pull is the right build.")
        else:
            print(f"  -> SHORT of 15 years by ~{15 - span}. Scaling this source alone will not")
            print("     reach the requirement; a commercial panel (ACE Equity / Prowess) is needed")
            print("     for the earlier years, or the study window has to be shortened.")
        print(f"  first-row field names: {ok[-1].get('keys')}")
    print("=" * 74)
    with open("nse_xbrl_probe_result.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
