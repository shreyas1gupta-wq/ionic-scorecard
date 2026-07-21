"""
scrape_screener_750.py — canonical Screener fundamentals scraper for STOCK_SCORECARD_750.
Built to SCRAPING_SOP.md (FROZEN v1, 2026-07-18) sections 1-2, 5. Rehomed/rebuilt 2026-07-21
(DESK-100) — the original one-off scraper was never in the repo (SOP §7 note).

Pulls Annual P&L / Balance Sheet / Cash Flow (the three existing screener_deep parquets'
long-format schema) from screener.in company pages (consolidated preferred, standalone
fallback). Ratios are NOT scraped pre-computed except the ratio ROWS screener natively shows
(OPM %, Tax %, Dividend Payout %, CFO/OP) which the existing parquets already carry.

Politeness (SOP §5): truststore, sequential requests.Session, >=2s sleep between symbols,
exponential backoff on 429/5xx, abort on 3 consecutive 403s. Resume-safe: _done.json marker
in the STAGING dir; re-runnable at any point (skip done symbols). Writes to
screener_deep/_staging/ — verify (D-009) then promote, never clobber live parquets.

Usage:
  <py> scrape_screener_750.py --test RELIANCE        # parse+diff vs existing parquet, no write
  <py> scrape_screener_750.py --symbols A,B,C         # scrape a specific list
  <py> scrape_screener_750.py --symbols-file f.txt    # one symbol per line
  <py> scrape_screener_750.py --auto-missing          # scrape universe names missing/stale/zero
"""
import argparse
import io
import json
import os
import re
import sys
import time

import truststore
truststore.inject_into_ssl()
import numpy as np
import pandas as pd
import requests

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
DS = os.path.join(ROOT, "datasets", "screener_deep")
STAGE = os.path.join(DS, "_staging")
UNI = os.path.join(ROOT, "ALPHA_RANKER", "data", "universe", "symbols_750.txt")

SECTIONS = {  # section id -> (staging basename, live parquet)
    "profit-loss":  ("pl", "screener_annual_pl.parquet"),
    "balance-sheet": ("bs", "screener_balance_sheet.parquet"),
    "cash-flow":    ("cf", "screener_cash_flow.parquet"),
    "quarters":     ("qtr", "screener_quarterly_results.parquet"),  # NEW: for TTM (Q1 FY27 etc.)
}
MANDATORY = "profit-loss"  # a symbol with no P&L table is a failure; BS/CF/quarters optional
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
PERIOD_RE = re.compile(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}")
SLEEP = 2.2
SCRAPER_VERSION = "scrape_screener_750.py/2026-07-21"


def log(m):
    print(m, flush=True)


def _clean_label(x):
    if not isinstance(x, str):
        x = str(x)
    x = x.replace("\xa0", "").replace("&nbsp;", "")
    x = re.sub(r"\s+\+", "+", x)   # "Sales +" -> "Sales+"
    return x.strip()


def _clean_cell(v):
    """Normalize a scraped data cell to float (NaN for blank/'-'). Values are numerically
    identical to screener display; the scoring engine's _clean_num handles either form, we
    store float for a clean, self-consistent new-rows parquet."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return np.nan
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v)
    s = str(v).replace(",", "").replace("%", "").replace("\xa0", "").strip()
    if s in ("", "-", "nan", "NaN"):
        return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def _first_data_table(html, section_id):
    m = re.search(rf'<section id="{section_id}".*?</section>', html, re.S)
    if not m:
        return None
    block = m.group(0)
    tm = re.search(r'<table class="data-table[^"]*".*?</table>', block, re.S)
    return tm.group(0) if tm else None


def parse_section(html, section_id, sym):
    tbl = _first_data_table(html, section_id)
    if tbl is None:
        return None
    try:
        df = pd.read_html(io.StringIO(tbl))[0]
    except Exception:
        return None
    if df.shape[0] == 0 or df.shape[1] < 2:
        return None
    label_col = df.columns[0]
    df = df.rename(columns={label_col: "metric"})
    df["metric"] = df["metric"].map(_clean_label)
    # keep only period columns (+ TTM), drop growth-range / blank cols
    keep = ["metric"]
    for c in df.columns[1:]:
        cs = _clean_label(c)
        if cs == "TTM" or PERIOD_RE.match(cs):
            keep.append(c)
    df = df[keep].copy()
    df.columns = ["metric"] + [_clean_label(c) for c in keep[1:]]
    df = df[df["metric"].astype(bool)]
    for c in df.columns[1:]:
        df[c] = df[c].map(_clean_cell)
    # drop junk rows with no numeric data in ANY period (e.g. screener's "Raw PDF" link row)
    period_cols = [c for c in df.columns if c != "metric"]
    if period_cols:
        df = df[df[period_cols].notna().any(axis=1)]
    df.insert(0, "symbol", sym)
    return df.reset_index(drop=True)


def _pl_latest_year(html):
    """Max fiscal year present in the P&L table (annual period columns). None if no table."""
    tbl = _first_data_table(html, "profit-loss")
    if tbl is None:
        return None
    ths = re.findall(r"<th[^>]*>(.*?)</th>", tbl, re.S)
    yrs = []
    for t in ths:
        cs = _clean_label(re.sub(r"<[^>]+>", "", t))
        if PERIOD_RE.match(cs):
            m = re.search(r"(19|20)\d{2}", cs)
            if m:
                yrs.append(int(m.group(0)))
    return max(yrs) if yrs else None


def _get(session, url):
    """GET with backoff. Returns (status, text) or (code_str, None)."""
    for attempt in range(4):
        try:
            r = session.get(url, timeout=30)
        except Exception as e:
            time.sleep(2 ** attempt)
            if attempt == 3:
                return f"neterr:{type(e).__name__}", None
            continue
        if r.status_code == 200:
            return 200, r.text
        if r.status_code == 403:
            return "403", None
        if r.status_code == 404:
            return "404", None
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(3 * (attempt + 1))
            continue
        return str(r.status_code), None
    return "retry-exhausted", None


CURRENT_FY = 2025  # accept a consolidated view outright if its latest year >= this


def fetch(session, sym):
    """Return (html, variant) or (None, reason). Prefer consolidated, but only if it is
    CURRENT — screener sometimes serves a dead legacy consolidated series (e.g. COLPAL frozen
    at Mar-2010) while the standalone view is live. So: take consolidated if its latest year
    is current; else fetch standalone and keep whichever variant is more recent."""
    cons_status, cons_html = _get(session, f"https://www.screener.in/company/{sym}/consolidated/")
    if cons_status == "403":
        return None, "403"
    cons_year = _pl_latest_year(cons_html) if cons_html else None
    if cons_year is not None and cons_year >= CURRENT_FY:
        return cons_html, f"consolidated({cons_year})"
    # consolidated missing or stale -> get standalone and compare
    std_status, std_html = _get(session, f"https://www.screener.in/company/{sym}/")
    if std_status == "403":
        return None, "403"
    std_year = _pl_latest_year(std_html) if std_html else None
    cands = [(cons_year, cons_html, "consolidated"), (std_year, std_html, "standalone")]
    cands = [(y, h, v) for y, h, v in cands if h is not None and y is not None]
    if not cands:
        return None, "no-pl-table"
    cands.sort(key=lambda t: t[0], reverse=True)
    y, h, v = cands[0]
    return h, f"{v}({y})"


def load_done():
    p = os.path.join(STAGE, "_done.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    return []


def save_staging(frames, done, failed):
    os.makedirs(STAGE, exist_ok=True)
    for sec, (base, _live) in SECTIONS.items():
        if frames[base]:
            big = pd.concat(frames[base], ignore_index=True)
            big.to_parquet(os.path.join(STAGE, f"screener_{base}_staging.parquet"), index=False)
    json.dump(done, open(os.path.join(STAGE, "_done.json"), "w"), indent=0)
    json.dump({"failed": failed}, open(os.path.join(STAGE, "_failed.json"), "w"), indent=1)


def scrape(symbols):
    os.makedirs(STAGE, exist_ok=True)
    done = load_done()
    done_set = set(done)
    # preload any prior staging frames so we append, not lose
    frames = {base: [] for base, _ in SECTIONS.values()}
    for base, _ in SECTIONS.values():
        sp = os.path.join(STAGE, f"screener_{base}_staging.parquet")
        if os.path.exists(sp):
            frames[base].append(pd.read_parquet(sp))
    failed = []
    if os.path.exists(os.path.join(STAGE, "_failed.json")):
        failed = json.load(open(os.path.join(STAGE, "_failed.json")))["failed"]

    todo = [s for s in symbols if s not in done_set]
    log(f"{len(symbols)} requested, {len(done_set)} already done, {len(todo)} to scrape.")
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    consec_403 = 0
    for i, sym in enumerate(todo, 1):
        html, variant = fetch(session, sym)
        if html is None:
            failed.append({"symbol": sym, "reason": variant})
            log(f"  [{i}/{len(todo)}] {sym}: FAIL ({variant})")
            if variant == "403":
                consec_403 += 1
                if consec_403 >= 3:
                    log("  ABORT: 3 consecutive 403s (SOP §5). Saving progress and stopping.")
                    break
            else:
                consec_403 = 0
            time.sleep(SLEEP)
            continue
        consec_403 = 0
        ok = True
        parsed = {}
        for sec, (base, _live) in SECTIONS.items():
            d = parse_section(html, sec, sym)
            if d is None or d.shape[0] == 0:
                ok = ok and (sec != "profit-loss")  # PL mandatory; BS/CF may be absent
            parsed[base] = d
        if parsed["pl"] is None or parsed["pl"].shape[0] == 0:
            failed.append({"symbol": sym, "reason": "parse-no-pl"})
            log(f"  [{i}/{len(todo)}] {sym}: FAIL (parse-no-pl)")
            time.sleep(SLEEP)
            continue
        for base in frames:
            if parsed[base] is not None and parsed[base].shape[0] > 0:
                frames[base].append(parsed[base])
        done.append(sym)
        done_set.add(sym)
        yrs = [c for c in parsed["pl"].columns if PERIOD_RE.match(c)]
        latest = max((c for c in yrs), key=lambda c: c.split()[-1][:4], default="?")
        log(f"  [{i}/{len(todo)}] {sym}: OK ({variant}) latest~{latest} pl={parsed['pl'].shape[0]}r")
        if i % 10 == 0:
            save_staging(frames, done, failed)
            log(f"    ...checkpoint saved ({len(done)} done)")
        time.sleep(SLEEP)
    save_staging(frames, done, failed)
    meta = {"run_date": time.strftime("%Y-%m-%d %H:%M"), "universe_file": "symbols_750.txt",
            "symbols_attempted": len(todo), "symbols_ok": len(done_set),
            "symbols_failed": failed, "scraper_version": SCRAPER_VERSION}
    json.dump(meta, open(os.path.join(STAGE, "_meta.json"), "w"), indent=1)
    log(f"DONE. {len(done_set)} done total, {len(failed)} failed. Staging -> {STAGE}")


def self_test(sym):
    session = requests.Session()
    session.headers.update({"User-Agent": UA})
    html, variant = fetch(session, sym)
    if html is None:
        log(f"TEST {sym}: fetch failed ({variant})"); return
    log(f"TEST {sym}: fetched variant={variant}")
    for sec, (base, live) in SECTIONS.items():
        d = parse_section(html, sec, sym)
        if d is None:
            log(f"  {base}: parse FAILED / section absent"); continue
        log(f"  {base}: scraped {d.shape[0]} metrics x {d.shape[1]-2} periods; metrics={list(d['metric'])}")
        live_path = os.path.join(DS, live)
        if not os.path.exists(live_path):
            log(f"    (no live {live} yet — periods: {[c for c in d.columns if c not in ('symbol','metric')][-6:]})")
            continue
        existing = pd.read_parquet(live_path)
        ex = existing[existing["symbol"] == sym]
        # compare a couple of overlapping cells
        common_cols = [c for c in d.columns if c in ex.columns and PERIOD_RE.match(str(c))]
        if len(ex) and common_cols:
            for met in ["Net Profit+", "Sales+", "Equity Capital", "Borrowings+", "Free Cash Flow"]:
                a = d[d["metric"] == met]
                b = ex[ex["metric"] == met]
                if len(a) and len(b):
                    col = common_cols[-1]
                    log(f"    {met} [{col}]: scraped={a[col].iloc[0]!r} existing={b[col].iloc[0]!r}")


def compute_auto_missing():
    uni = [l.strip() for l in open(UNI, encoding="utf-8") if l.strip()]
    pl = pd.read_parquet(os.path.join(DS, "screener_annual_pl.parquet"))
    mar = [c for c in pl.columns if re.match(r"^Mar \d{4}$", c)]
    scr = set(pl["symbol"].astype(str))

    def latest_year(sym):
        best = None
        for metric in ("Net Profit+", "Sales+", "Revenue+"):
            row = pl[(pl["symbol"] == sym) & (pl["metric"] == metric)]
            if len(row):
                s = row[mar].iloc[0]
                nn = [int(c.split()[1]) for c in mar if pd.notna(s[c]) and str(s[c]).strip() not in ("", "-", "nan")]
                if nn:
                    best = max(nn) if best is None else max(best, max(nn))
        return best
    missing = [s for s in uni if s not in scr]
    stale_zero = [s for s in scr if (latest_year(s) is None or latest_year(s) < 2025)]
    target = sorted(set(missing) | set(stale_zero))
    log(f"auto-missing: {len(missing)} absent + {len(stale_zero)} stale/zero = {len(target)} target")
    return target


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test")
    ap.add_argument("--symbols")
    ap.add_argument("--symbols-file")
    ap.add_argument("--auto-missing", action="store_true")
    ap.add_argument("--full", action="store_true", help="scrape the ENTIRE symbols_750 universe (all sections)")
    a = ap.parse_args()
    if a.test:
        self_test(a.test)
    elif a.symbols:
        scrape([s.strip() for s in a.symbols.split(",") if s.strip()])
    elif a.symbols_file:
        scrape([l.strip() for l in open(a.symbols_file, encoding="utf-8") if l.strip()])
    elif a.auto_missing:
        scrape(compute_auto_missing())
    elif a.full:
        uni = list(dict.fromkeys(l.strip() for l in open(UNI, encoding="utf-8") if l.strip()))
        scrape(uni)
    else:
        ap.print_help()
