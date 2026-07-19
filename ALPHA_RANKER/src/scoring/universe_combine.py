"""Universe-scale fusion: read the universe_*.parquet theme engines -> per-horizon conviction
for all NIFTY-750 names. Same math as combine_scores.py (weight book, forensic penalty, cascade,
cross-horizon drag, bands) but parquet-based and cross-sectional over the full universe.
Defensive: runs on whatever engine outputs exist; renormalises over available themes.
"""
import os, json, math
import numpy as np, pandas as pd

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER"
RES = os.path.join(BASE, "results")
W = json.load(open(os.path.join(BASE, "weights", "horizon_weights.json")))
UNI = [s.strip() for s in open(os.path.join(BASE, "data", "universe", "symbols_750.txt")) if s.strip()]

def load(name):
    p = os.path.join(RES, name)
    if not os.path.exists(p): return None
    df = pd.read_parquet(p)
    for k in ("symbol", "ticker", "Symbol", "Ticker"):
        if k in df.columns: df = df.set_index(k); break
    df.index = df.index.astype(str).str.upper().str.replace(".NS", "", regex=False)
    return df

def col(df, cands):
    if df is None: return None
    for c in cands:
        for actual in df.columns:
            if c.lower() == str(actual).lower(): return pd.to_numeric(df[actual], errors="coerce")
    for c in cands:  # substring fallback
        for actual in df.columns:
            if c.lower() in str(actual).lower(): return pd.to_numeric(df[actual], errors="coerce")
    return None

tech = load("universe_technical_scores.parquet")
fund = load("universe_fundamental_scores.parquet")
cata = load("universe_catalyst_scores.parquet")
fore = load("universe_forensic_score.parquet")
casc = load("universe_cascade_adjustments.parquet")

TH = {
    "Momentum": col(tech, ["theme_momentum"]),
    "Value":    col(fund, ["Value"]),
    "Quality":  col(fund, ["Quality"]),
    "Growth":   col(fund, ["Growth"]),
    "Flow":     col(tech, ["theme_flow_micro", "theme_flow"]),
    "Catalyst": col(cata, ["theme_catalyst", "theme_catalyst_earnings_momentum"]),
}
forensic = col(fore, ["forensic_risk_score", "forensic_risk_score_0_100", "score"])
cascade  = col(casc, ["net_adj", "net", "total"])
avail = {t: (s is not None) for t, s in TH.items()}

def tv(t, s):
    x = TH[t]
    if x is None or s not in x.index or pd.isna(x.loc[s]): return None
    return float(x.loc[s])

def comp(s, h):
    w = W[h]; num = wsum = 0.0; used = 0
    for t in ["Momentum","Value","Quality","Growth","Flow","Catalyst"]:
        v = tv(t, s)
        if v is None: continue
        num += w[t]*v; wsum += w[t]; used += 1
    return (num/wsum if wsum else None), used

def fpen(s, h):
    if forensic is None or s not in forensic.index or pd.isna(forensic.loc[s]): return 0.0
    return -(float(forensic.loc[s])/100.0) * (W[h]["Forensic"]*200)

def cadj(s):
    if cascade is None or s not in cascade.index or pd.isna(cascade.loc[s]): return 0.0
    return float(np.clip(cascade.loc[s], -20, 20))

def band(x):
    b = W["band_thresholds"]
    if x >= b["STRONG_BUY"]: return "STRONG_BUY"
    if x >= b["BUY"]: return "BUY"
    if x <= b["EXIT"]: return "EXIT"
    if x <= b["REDUCE"]: return "REDUCE"
    return "HOLD"

ch = W["cross_horizon_coupling"]; rows = []
for s in UNI:
    rec = {"symbol": s}; raw = {}
    for h in ["1M","1Y","5Y","MICRO"]:
        c, used = comp(s, h)
        rec[f"cover_{h}"] = used
        raw[h] = None if c is None else (c-50)*2 + fpen(s, h) + cadj(s)
    if raw.get("1M") is not None and raw["1M"] < ch["trigger_1m_below"]:
        ex = raw["1M"] - ch["trigger_1m_below"]
        if raw.get("1Y") is not None: raw["1Y"] += ex*ch["drag_to_1Y"]
        if raw.get("5Y") is not None: raw["5Y"] += ex*ch["drag_to_5Y"]
    for h in ["1M","1Y","5Y","MICRO"]:
        if raw[h] is None: rec[f"score_{h}"] = np.nan; continue
        sc = float(np.clip(raw[h], -100, 100))
        rec[f"score_{h}"] = round(sc,0); rec[f"band_{h}"] = band(sc)
        rec[f"pup_{h}"] = round(1/(1+math.exp(-sc/40)), 2)
    rows.append(rec)

out = pd.DataFrame(rows).set_index("symbol")
out.to_parquet(os.path.join(RES, "universe_final_scores.parquet"))
out.to_csv(os.path.join(RES, "universe_final_scores.csv"))
json.dump({"themes": avail, "forensic": forensic is not None, "cascade": cascade is not None,
           "n_universe": len(UNI), "n_scored_1Y": int(out["score_1Y"].notna().sum()) if "score_1Y" in out else 0},
          open(os.path.join(RES, "universe_coverage.json"), "w"), indent=1)
print("THEMES:", {k:("Y" if v else "-") for k,v in avail.items()}, "| forensic", forensic is not None, "| cascade", cascade is not None)
if "score_1Y" in out.columns:
    print("scored (1Y):", int(out["score_1Y"].notna().sum()), "/", len(UNI))
    print("\nTOP 15 by 1Y:"); print(out.sort_values("score_1Y", ascending=False).head(15)[["score_1M","score_1Y","score_5Y","band_1Y","cover_1Y"]].to_string())
    print("\nBOTTOM 10 by 1Y:"); print(out.sort_values("score_1Y").head(10)[["score_1M","score_1Y","score_5Y","band_1Y","cover_1Y"]].to_string())
