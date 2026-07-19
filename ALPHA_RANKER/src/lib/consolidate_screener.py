"""Consolidate data/fundamentals/screener_live/*.json -> reusable tidy parquets.
Run after (or during) the scrape; idempotent. Output goes to data/fundamentals/consolidated/.
Long format everywhere: (symbol, metric/holder, period, value). Plus a coverage manifest.
"""
import os, glob, json, re
import numpy as np, pandas as pd

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER"
SL = os.path.join(BASE, "data", "fundamentals", "screener_live")
OUT = os.path.join(BASE, "data", "fundamentals", "consolidated"); os.makedirs(OUT, exist_ok=True)

def num(x):
    try: return float(str(x).replace(",", "").replace("%", "").replace("₹", "").strip())
    except Exception: return np.nan

def melt_table(recs, symbol):
    """recs = list of {metric: , 'Mar 2024':, ...} -> long rows."""
    out = []
    if not recs: return out
    keyc = list(recs[0].keys())[0]
    pcols = [c for c in recs[0].keys() if c != keyc]
    for row in recs:
        metric = str(row[keyc]).strip()
        for p in pcols:
            out.append({"symbol": symbol, "metric": metric, "period": p, "value": num(row[p])})
    return out

TAB = ["quarterly_results", "profit_loss", "balance_sheet", "cash_flow", "ratios", "shareholding"]
acc = {t: [] for t in TAB}
top_rows, doc_rows, manifest = [], [], []

for f in sorted(glob.glob(os.path.join(SL, "*.json"))):
    r = json.load(open(f)); sym = r["ticker"]; t = r.get("tables", {})
    m = {"symbol": sym, "url_path": r.get("url_path")}
    for tab in TAB:
        recs = t.get(tab)
        acc[tab] += melt_table(recs, sym)
        m[tab] = len(recs) if recs else 0
    for k, v in (r.get("top_ratios") or {}).items():
        top_rows.append({"symbol": sym, "ratio": k, "raw": v, "value": num(v)})
    for d in (r.get("documents") or []):
        doc_rows.append({"symbol": sym, "text": d.get("text"), "href": d.get("href")})
    # latest quarter present
    q = t.get("quarterly_results") or []
    qcols = [c for c in (q[0].keys() if q else []) if re.match(r"[A-Za-z]{3}\s+\d{4}", str(c))]
    m["latest_qtr"] = qcols[-1] if qcols else None
    m["n_docs"] = len(r.get("documents") or [])
    manifest.append(m)

for tab in TAB:
    pd.DataFrame(acc[tab]).to_parquet(os.path.join(OUT, f"{tab}.parquet"))
pd.DataFrame(top_rows).to_parquet(os.path.join(OUT, "top_ratios.parquet"))
pd.DataFrame(doc_rows).to_parquet(os.path.join(OUT, "documents.parquet"))
man = pd.DataFrame(manifest)
man.to_csv(os.path.join(OUT, "coverage_manifest.csv"), index=False)

print(f"consolidated {len(manifest)} symbols -> {OUT}")
print("rows per table:", {t: len(acc[t]) for t in TAB})
print("with quarterly_results:", int((man['quarterly_results'] > 0).sum()),
      "| with shareholding:", int((man['shareholding'] > 0).sum()))
print("latest_qtr distribution:\n", man['latest_qtr'].value_counts().head(8).to_string())
