"""Recompute the Catalyst/earnings-momentum theme from FRESH screener_live quarterly data
(latest = Mar/Jun 2026, vs the stale on-disk 2023-09 PIT set). Same factor logic as AG2,
new source. Writes results/pilot_catalyst_factors_FRESH.csv + a fresh promoter table.
"""
import os, json, glob, re
import numpy as np, pandas as pd

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER"
SL = os.path.join(BASE, "data", "fundamentals", "screener_live")
RES = os.path.join(BASE, "results")

def qkey(lbl):
    m = re.match(r"([A-Za-z]{3})\s+(\d{4})", str(lbl))
    if not m: return None
    mon = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,"Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}[m.group(1)]
    return int(m.group(2))*100 + mon

def num(x):
    try: return float(str(x).replace(",","").replace("%","").strip())
    except Exception: return np.nan

def series(tbl, want):
    """return {qtr_label: value} for the first row whose label matches any want-keyword."""
    if not tbl: return {}
    keyc = list(tbl[0].keys())[0]
    qcols = [c for c in tbl[0].keys() if qkey(c)]
    qcols = sorted(qcols, key=qkey)
    for row in tbl:
        lbl = str(row[keyc]).lower()
        if any(w in lbl for w in want):
            return {c: num(row[c]) for c in qcols}
    return {}

def yoy(s, k, n=4):
    ks = sorted(s, key=qkey)
    if len(ks) <= n: return np.nan
    a, b = s[ks[-1]], s[ks[-1-n]]
    if pd.isna(a) or pd.isna(b) or b == 0: return np.nan
    return a/abs(b) - 1

def qoq(s):
    ks = sorted(s, key=qkey)
    if len(ks) < 2: return np.nan
    a, b = s[ks[-1]], s[ks[-2]]
    if pd.isna(a) or pd.isna(b) or b == 0: return np.nan
    return a/abs(b) - 1

def surprise(s):
    ks = sorted(s, key=qkey)
    if len(ks) < 5: return np.nan
    hist = [s[k] for k in ks[-5:-1]]
    if any(pd.isna(hist)): return np.nan
    x = np.arange(4); coef = np.polyfit(x, hist, 1); exp = np.polyval(coef, 4)
    if exp == 0: return np.nan
    return (s[ks[-1]] - exp)/abs(exp)

rows, prom = [], []
for f in sorted(glob.glob(os.path.join(SL, "*.json"))):
    r = json.load(open(f)); tk = r["ticker"]; t = r["tables"]
    q = t.get("quarterly_results") or []
    sales = series(q, ["sales","revenue"]); npf = series(q, ["net profit"]); eps = series(q, ["eps"])
    opm = series(q, ["opm","financing margin"])
    ql = sorted([c for c in (q[0].keys() if q else []) if qkey(c)], key=qkey)
    latest_q = ql[-1] if ql else "-"
    opm_change = np.nan
    if opm:
        ks = sorted(opm, key=qkey)
        if len(ks) >= 5 and not any(pd.isna([opm[k] for k in ks[-5:]])):
            opm_change = opm[ks[-1]] - np.mean([opm[k] for k in ks[-5:-1]])
    rec = {"symbol": tk, "latest_qtr": latest_q,
           "sales_yoy": yoy(sales,"s"), "np_yoy": yoy(npf,"n"), "eps_yoy": yoy(eps,"e"),
           "sales_qoq": qoq(sales), "np_qoq": qoq(npf),
           "np_accel": (yoy(npf,"n") - (lambda s: yoy({k:v for k,v in s.items()},"n"))(npf)) if False else np.nan,
           "opm_change": opm_change, "np_surprise": surprise(npf), "sales_surprise": surprise(sales)}
    rows.append(rec)
    # fresh promoter %
    shp = t.get("shareholding") or []
    if shp:
        kc = list(shp[0].keys())[0]; sc = [c for c in shp[0].keys() if qkey(c)]
        latest_shp = sorted(sc, key=qkey)[-1] if sc else None
        for row in shp:
            if "promoter" in str(row[kc]).lower():
                prom.append({"symbol": tk, "shp_asof": latest_shp, "promoter_pct": num(row.get(latest_shp))}); break

df = pd.DataFrame(rows).set_index("symbol")
# cross-sectional percentile -> theme
facs = ["sales_yoy","np_yoy","eps_yoy","sales_qoq","np_qoq","opm_change","np_surprise","sales_surprise"]
pct = df[facs].rank(pct=True)*100
df["theme_catalyst_earnings_momentum"] = pct.mean(axis=1).round(1)
df.round(3).to_csv(os.path.join(RES, "pilot_catalyst_factors_FRESH.csv"))
pd.DataFrame(prom).to_csv(os.path.join(RES, "pilot_promoter_FRESH.csv"), index=False)

pd.set_option("display.width", 200)
print("FRESH catalyst (source: screener_live, latest Mar/Jun 2026):")
print(df[["latest_qtr","sales_yoy","np_yoy","theme_catalyst_earnings_momentum"]].round(3).to_string())
print("\nFresh promoter holdings:")
print(pd.DataFrame(prom).to_string(index=False))
