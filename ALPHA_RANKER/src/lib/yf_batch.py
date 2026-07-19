"""Batch yfinance OHLCV — resumable, process-parallel. 5y daily for richer 1Y/5Y factors.
Usage: python yf_batch.py --slice N/M    |    python yf_batch.py --benchmark
Reads data/universe/symbols_750.txt. Writes data/prices/<TICKER>.parquet (resume-safe skip).
Sequential within a process (proxy stalls on threads); run several processes.
"""
import os, time, argparse
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
import truststore; truststore.inject_into_ssl()
import pandas as pd, yfinance as yf

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER"
UNI = os.path.join(BASE, "data", "universe", "symbols_750.txt")
OUT = os.path.join(BASE, "data", "prices"); os.makedirs(OUT, exist_ok=True)
LOG = os.path.join(BASE, "data", "_yf_logs"); os.makedirs(LOG, exist_ok=True)

def pull(sym, yf_sym, fp):
    if os.path.exists(fp): return "cached"
    try:
        df = yf.download(yf_sym, period="5y", interval="1d", auto_adjust=False, progress=False, threads=False)
        if df is None or len(df) == 0: return "EMPTY"
        if hasattr(df.columns, "get_level_values"): df.columns = df.columns.get_level_values(0)
        df.to_parquet(fp); return "OK"
    except Exception as e: return f"ERR:{type(e).__name__}"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", default=None); ap.add_argument("--benchmark", action="store_true")
    a = ap.parse_args()
    if a.benchmark:
        print("_NSEI", pull("_NSEI", "^NSEI", os.path.join(OUT, "_NSEI.parquet"))); raise SystemExit
    syms = [s.strip() for s in open(UNI) if s.strip()]
    n, m = map(int, a.slice.split("/")); syms = [s for i, s in enumerate(syms) if i % m == n]
    tag = f"s{n}of{m}"; logf = open(os.path.join(LOG, f"{tag}.log"), "a", buffering=1)
    ok = cache = fail = 0
    for i, tk in enumerate(syms):
        r = pull(tk, f"{tk}.NS", os.path.join(OUT, f"{tk}.parquet"))
        if r == "OK": ok += 1; time.sleep(1.0)
        elif r == "cached": cache += 1
        else: fail += 1; logf.write(f"{tk} {r}\n")
        if i % 25 == 0: logf.write(f"[{tag}] {i+1}/{len(syms)} ok={ok} cache={cache} fail={fail}\n")
    logf.write(f"[{tag}] DONE ok={ok} cache={cache} fail={fail}\n")
    print(f"[{tag}] DONE ok={ok} cache={cache} fail={fail}")
