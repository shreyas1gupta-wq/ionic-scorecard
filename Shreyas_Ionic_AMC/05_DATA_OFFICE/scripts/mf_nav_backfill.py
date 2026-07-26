# -*- coding: utf-8 -*-
"""mf_nav_backfill.py — backfill month-end AMFI NAV cross-sections into
datasets/mf_nav/nav_monthend.parquet (the store mf_nav_refresh.py accrues monthly).

Why: the MF Dashboard's NAV rows end 2025-01-31 for most categories; a true June-end
2026 QFRA-1 run needs month-end NAVs Feb-2025..Jun-2026 (Principal 2026-07-26).
Fund side only — benchmark index levels are a separate (network-gated) pull.

Method per month: request AMFI's history report for the month's last 6 calendar days
(portal.amfiindia.com DownloadNAVHistoryReport_Po.aspx, semicolon-separated), keep each
scheme's LATEST row in the window = the month-end NAV. Resume-safe: months already in
the store are skipped. Sequential requests (corporate proxy), ~1s pause.

Usage: python mf_nav_backfill.py [--from 2025-02] [--to 2026-06]
"""
import io
import os
import sys
import time
import argparse
import datetime as dt

import truststore; truststore.inject_into_ssl()
import requests
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(ROOT, "datasets", "mf_nav")
ME_PATH = os.path.join(OUT, "nav_monthend.parquet")
URL = "https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx"


def month_ends(frm, to):
    y, m = map(int, frm.split("-"))
    y2, m2 = map(int, to.split("-"))
    while (y, m) <= (y2, m2):
        nxt = dt.date(y + (m == 12), (m % 12) + 1, 1)
        yield dt.date(y, m, 1), nxt - dt.timedelta(days=1)
        y, m = nxt.year, nxt.month


def parse_amfi(text):
    """AMFI history format: 'Scheme Code;Scheme Name;ISIN.../ISIN...;ISIN...;NAV;Repurchase;Sale;Date'
    interleaved with category/AMC header lines — keep only rows with 8 ;-fields."""
    rows = []
    for line in text.splitlines():
        parts = line.split(";")
        if len(parts) != 8 or parts[0].strip().lower() == "scheme code":
            continue
        code, name, isin_g, _isin_r, nav, _rep, _sale, date = [p.strip() for p in parts]
        try:
            nav = float(nav)
        except ValueError:
            continue
        rows.append((code, isin_g, name, nav, date))
    df = pd.DataFrame(rows, columns=["scheme_code", "isin", "name", "nav", "date"])
    df["date"] = pd.to_datetime(df["date"], format="%d-%b-%Y", errors="coerce")
    return df.dropna(subset=["date"])


def main(frm, to):
    os.makedirs(OUT, exist_ok=True)
    hist = pd.read_parquet(ME_PATH) if os.path.exists(ME_PATH) else pd.DataFrame(
        columns=["scheme_code", "isin", "name", "nav", "date"])
    if len(hist):
        hist["date"] = pd.to_datetime(hist["date"])
    have = set(hist["date"].dt.strftime("%Y-%m")) if len(hist) else set()
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0"
    added = 0
    for first, last in month_ends(frm, to):
        ym = first.strftime("%Y-%m")
        if ym in have:
            print(f"{ym}: already in store, skip", flush=True)
            continue
        frmdt = (last - dt.timedelta(days=5)).strftime("%d-%b-%Y")
        todt = last.strftime("%d-%b-%Y")
        for attempt in (1, 2, 3):
            try:
                r = s.get(URL, params={"frmdt": frmdt, "todt": todt}, timeout=180)
                r.raise_for_status()
                break
            except Exception as e:
                print(f"{ym}: attempt {attempt} failed: {repr(e)[:120]}", flush=True)
                time.sleep(5 * attempt)
        else:
            print(f"{ym}: FAILED after retries — resume later, store untouched", flush=True)
            continue
        df = parse_amfi(r.text)
        if df.empty:
            print(f"{ym}: parsed 0 rows ({len(r.text)/1e3:.0f} KB) — check format", flush=True)
            continue
        # month-end = each scheme's last available NAV in the window
        df = df.sort_values("date").groupby("scheme_code", as_index=False).last()
        hist = pd.concat([hist, df], ignore_index=True)
        hist.to_parquet(ME_PATH, index=False)      # bank after every month (resume-safe)
        added += 1
        print(f"{ym}: +{len(df)} schemes @ {df['date'].max().date()} (store banked)", flush=True)
        time.sleep(1.2)
    n_me = hist["date"].dt.to_period("M").nunique() if len(hist) else 0
    print(f"\ndone: {added} months added · store now holds {n_me} month-ends, "
          f"{len(hist)} rows -> {ME_PATH}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm", default="2025-02")
    ap.add_argument("--to", dest="to", default="2026-06")
    a = ap.parse_args()
    main(a.frm, a.to)
