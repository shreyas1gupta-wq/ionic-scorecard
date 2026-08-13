# -*- coding: utf-8 -*-
"""ISIN MASTER — symbol <-> ISIN <-> company name for the whole NSE equity list.

WHY THIS EXISTS. `client_intake.py` promises "ISIN first, then normalized-name prefix" and builds its
lookup with `if r.get("isin")` against the scored-universe CSV. That CSV has NO isin column -- not one
of its 101 columns. So `by_isin` was always EMPTY, the exact-match branch never fired, and every single
equity holding silently fell through to NAME-PREFIX matching. That is the fuzzy matching the Principal
banned outright ("REMOVE FUZZY ENTIRELY"), running unnoticed on the primary client-onboarding path.

It is not a theoretical risk. The scored universe carries BOTH `TMCV` (61.2) and `ZFCVINDIA` (43.7) --
the same company before and after its rename, 17.5 points apart. A name-prefix match can land on
either, and nothing downstream would flag it.

SOURCE: NSE's official equity list archive, https://nsearchives.nseindia.com/content/equities/
EQUITY_L.csv -- an exchange archive, so D-033 permits the auto-fetch. It carries SYMBOL, NAME OF
COMPANY, ISIN NUMBER, SERIES and listing date for every listed NSE equity.

Writes 05_DATA_OFFICE/data/isin_master.csv  (symbol, isin, company_name, series, listing_date)
and prints a D-009 verification block: row count, known-value spot checks, duplicate scan, and the
join rate against the scored universe. Nothing is written if the spot checks fail.
"""
import io
import os
import sys

import pandas as pd
import truststore

truststore.inject_into_ssl()
import requests                                                          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def _root(p):
    found = None
    while True:
        p, tail = os.path.split(p)
        if not tail:
            if found:
                return found
            raise RuntimeError("repo root not found")
        cand = os.path.join(p, tail)
        if os.path.isdir(os.path.join(cand, "Shreyas_Ionic_AMC")) or tail == "NIFTY 500":
            found = cand          # outermost match: the live tree, which holds datasets/


ROOT = _root(HERE)
OUTDIR = os.path.join(ROOT, "Shreyas_Ionic_AMC", "05_DATA_OFFICE", "data")
OUT = os.path.join(OUTDIR, "isin_master.csv")
SCORED = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750",
                      "results", "full750_scored_v3.csv")

URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
HOME = "https://www.nseindia.com/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")

# D-009 spot checks: ISINs stable enough to hardcode, verifiable against any public source.
SPOT = {
    "SBIN": "INE062A01020",
    "HAL": "INE066F01020",
    "PFC": "INE134E01011",
    "AUROPHARMA": "INE406A01037",
    "GLENMARK": "INE935A01035",
}


def fetch():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    s.get(HOME, timeout=45)                     # cookie warm-up; the archive 403s without it
    r = s.get(URL, timeout=90, headers={"Referer": HOME})
    r.raise_for_status()
    return pd.read_csv(io.StringIO(r.text))


def main():
    try:
        raw = fetch()
    except Exception as e:
        print(f"FETCH FAILED: {type(e).__name__}: {e}")
        print("NSE archive needs the office proxy to pass cookies; retry or use home network.")
        return 2

    raw.columns = [str(c).strip().upper() for c in raw.columns]
    need = {"SYMBOL": "symbol", "NAME OF COMPANY": "company_name", "ISIN NUMBER": "isin",
            " SERIES": "series", "SERIES": "series", " DATE OF LISTING": "listing_date",
            "DATE OF LISTING": "listing_date"}
    cols = {}
    for src, dst in need.items():
        if src in raw.columns and dst not in cols.values():
            cols[src] = dst
    if "SYMBOL" not in cols or not any(v == "isin" for v in cols.values()):
        print("SCHEMA CHANGED at source. columns seen:", list(raw.columns))
        return 3

    d = raw[list(cols)].rename(columns=cols)
    for c in ("symbol", "isin", "company_name"):
        if c in d.columns:
            d[c] = d[c].astype(str).str.strip()
    d["symbol"] = d["symbol"].str.upper()
    d["isin"] = d["isin"].str.upper()
    d = d[d["isin"].str.match(r"^IN[A-Z0-9]{10}$", na=False)].copy()

    print(f"[DATA] rows with a valid ISIN: {len(d)}")

    # --- D-009 verification, BEFORE writing ---------------------------------------------------------
    ok = True
    print("\nspot checks (known ISINs):")
    for sym, want in SPOT.items():
        got = d.loc[d["symbol"] == sym, "isin"]
        got = got.iloc[0] if len(got) else None
        good = got == want
        ok &= good
        print(f"   {sym:12s} expected {want}  got {got or '(absent)'}  "
              f"{'OK' if good else '*** MISMATCH ***'}")

    dup_sym = d["symbol"].duplicated().sum()
    dup_isin = d["isin"].duplicated().sum()
    print(f"\nduplicate symbols: {dup_sym}   duplicate ISINs: {dup_isin}")
    if dup_isin:
        ex = d[d["isin"].duplicated(keep=False)].sort_values("isin").head(8)
        print("   ISINs on more than one symbol (rename/relisting pairs -- expected, kept):")
        for _, r in ex.iterrows():
            print(f"      {r['isin']}  {r['symbol']:14s} {r['company_name'][:44]}")

    if not ok:
        print("\nABORTED: a spot check failed, so the file was NOT written.")
        return 4

    # --- join rate against the scored universe ------------------------------------------------------
    if os.path.exists(SCORED):
        sc = pd.read_csv(SCORED, usecols=["symbol"])
        sc["symbol"] = sc["symbol"].astype(str).str.strip().str.upper()
        have = set(d["symbol"])
        matched = sc["symbol"].isin(have).sum()
        print(f"\nscored universe join: {matched} of {len(sc)} symbols get an ISIN "
              f"({matched / len(sc) * 100:.1f}%)")
        missing = sorted(set(sc["symbol"]) - have)
        if missing:
            print(f"   {len(missing)} scored symbols absent from the NSE equity list "
                  f"(delisted/merged/BSE-only): {', '.join(missing[:12])}"
                  f"{' ...' if len(missing) > 12 else ''}")

    os.makedirs(OUTDIR, exist_ok=True)
    d.sort_values("symbol").to_csv(OUT, index=False)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
