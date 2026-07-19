"""Batch screener.in PUBLIC scraper — resumable, process-parallel, rate-limit-aware.
Usage:  python screener_scrape.py --slice N/M      (process symbols where idx % M == N)
        python screener_scrape.py --pilot          (just the 10 pilot names)
Reads symbols from data/universe/symbols_750.txt. Writes data/fundamentals/screener_live/<TICKER>.json.
Resume-safe: skips tickers already saved. Backoff on 429/5xx. Sequential within a process (proxy
stalls on threads); run several PROCESSES for parallelism. Reusable each quarter (delete a JSON to refresh it).
"""
import os, sys, time, json, argparse
from io import StringIO
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
import truststore; truststore.inject_into_ssl()
import requests, pandas as pd
from bs4 import BeautifulSoup

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER"
UNI = os.path.join(BASE, "data", "universe", "symbols_750.txt")
OUT = os.path.join(BASE, "data", "fundamentals", "screener_live"); os.makedirs(OUT, exist_ok=True)
LOGDIR = os.path.join(BASE, "data", "fundamentals", "_scrape_logs"); os.makedirs(LOGDIR, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
PILOT = ["HDFCBANK","ASIANPAINT","NESTLEIND","TATASTEEL","HINDALCO","MARUTI","TCS","INFY","GRAVITA","SHAKTIPUMP"]
SEC = {"quarters":"quarterly_results","profit-loss":"profit_loss","balance-sheet":"balance_sheet",
       "cash-flow":"cash_flow","ratios":"ratios","shareholding":"shareholding"}
S = requests.Session(); S.headers.update(UA)

def table_to_records(sec):
    if sec is None: return None
    t = sec.find("table")
    if t is None: return None
    try: df = pd.read_html(StringIO(str(t)))[0]
    except Exception: return None
    df.columns = [str(c).strip() for c in df.columns]
    f = df.columns[0]
    df[f] = df[f].astype(str).str.replace("\xa0"," ").str.replace(r"\s*\+\s*$","",regex=True).str.strip()
    return df.to_dict(orient="records")

def get(url):
    for wait in (0, 5, 15, 30):
        if wait: time.sleep(wait)
        try:
            r = S.get(url, timeout=30)
            if r.status_code == 200: return r.text
            if r.status_code in (429, 500, 502, 503): continue
            return None
        except Exception: continue
    return None

def _valid_q(recs):
    """True if the quarterly table has real period columns (e.g. 'Mar 2026')."""
    if not recs: return False
    for c in recs[0].keys():
        p = str(c).split()
        if len(p) == 2 and p[1].isdigit(): return True
    return False

def build_rec(soup, tk, used):
    rec = {"ticker": tk, "url_path": used, "tables": {}}
    for sid, name in SEC.items():
        rec["tables"][name] = table_to_records(soup.find("section", id=sid) or soup.find(id=sid))
    top = {}; tr = soup.find(id="top-ratios")
    if tr:
        for li in tr.find_all("li"):
            n = li.find("span", class_="name"); v = li.find("span", class_="nowrap value") or li.find("span", class_="value")
            if n and v: top[n.get_text(strip=True)] = " ".join(v.get_text(" ", strip=True).split())
    rec["top_ratios"] = top
    docs = []; dsec = soup.find("section", id="documents") or soup.find(id="documents")
    if dsec:
        for a in dsec.find_all("a", href=True):
            t = a.get_text(" ", strip=True)
            if t: docs.append({"text": t[:80], "href": a["href"]})
    rec["documents"] = docs[:60]
    return rec

def scrape(tk):
    """Try consolidated first; if its financial tables are empty (standalone-only reporters),
    fall back to standalone. Pick the variant whose quarterly table has real period columns."""
    fp = os.path.join(OUT, f"{tk}.json")
    if os.path.exists(fp): return "cached"
    best = None
    for path in (f"{tk}/consolidated/", f"{tk}/"):
        html = get(f"https://www.screener.in/company/{path}")
        if not html or "Quarterly Results" not in html:
            time.sleep(0.4); continue
        rec = build_rec(BeautifulSoup(html, "lxml"), tk, path)
        if _valid_q(rec["tables"].get("quarterly_results")):
            json.dump(rec, open(fp, "w"), indent=1); return "OK"
        best = best or rec          # parseable page but empty financials — remember, keep looking
        time.sleep(0.4)
    if best is not None:
        json.dump(best, open(fp, "w"), indent=1); return "OK-noQ"
    return "FAIL"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", default=None); ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--file", default=UNI, help="symbols file (one per line)")
    a = ap.parse_args()
    if a.pilot:
        syms = PILOT; tag = "pilot"
    else:
        syms = [s.strip() for s in open(a.file) if s.strip()]
        fbase = os.path.splitext(os.path.basename(a.file))[0]
        if a.slice:
            n, m = map(int, a.slice.split("/")); syms = [s for i, s in enumerate(syms) if i % m == n]; tag = f"{fbase}_s{n}of{m}"
        else: tag = fbase
    logf = open(os.path.join(LOGDIR, f"{tag}.log"), "a", buffering=1)
    n_ok = n_cache = n_fail = 0
    for i, tk in enumerate(syms):
        try: r = scrape(tk)
        except Exception as e: r = f"ERR:{type(e).__name__}"
        if r == "OK": n_ok += 1; time.sleep(1.6)
        elif r == "cached": n_cache += 1
        else: n_fail += 1; logf.write(f"{tk} {r}\n")
        if i % 20 == 0: logf.write(f"[{tag}] {i+1}/{len(syms)} ok={n_ok} cache={n_cache} fail={n_fail}\n")
    logf.write(f"[{tag}] DONE ok={n_ok} cache={n_cache} fail={n_fail}\n")
    print(f"[{tag}] DONE ok={n_ok} cache={n_cache} fail={n_fail}")
