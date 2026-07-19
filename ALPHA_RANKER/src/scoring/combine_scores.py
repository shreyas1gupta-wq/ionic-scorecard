"""Phase-5 scoring engine: fuse all theme outputs into per-horizon conviction (-100..+100).
Defensive by design: runs on whatever theme CSVs exist; renormalises weights over available
additive themes; tracks coverage. Forensic = penalty (size/regime-scaled hook). Cascade = additive
points. Cross-horizon: large negative 1M drags 1Y/5Y (user Q9). ALL OUTPUT IS UNCALIBRATED until Phase 6.
"""
import os, json, math, glob
import numpy as np, pandas as pd

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER"
RES = os.path.join(BASE, "results")
W = json.load(open(os.path.join(BASE, "weights", "horizon_weights.json")))

# master pilot list = the price parquets we pulled
PILOT = sorted([os.path.basename(p)[:-8] for p in glob.glob(os.path.join(RES, "..", "data", "prices", "*.parquet"))
                if "_NSEI" not in p])

def _load(path):
    if not os.path.exists(path): return None
    df = pd.read_csv(path)
    # find symbol key
    for k in ("symbol", "ticker", "Symbol", "Ticker"):
        if k in df.columns:
            df = df.set_index(k); break
    else:
        df = df.set_index(df.columns[0])
    df.index = df.index.astype(str).str.upper().str.replace(".NS", "", regex=False)
    return df

def _pick(df, keywords):
    """return a Series (0-100) = first column whose name contains any keyword (case-insensitive)."""
    if df is None: return None
    for kw in keywords:
        for c in df.columns:
            if kw.lower() in str(c).lower():
                s = pd.to_numeric(df[c], errors="coerce")
                if s.notna().any(): return s
    return None

# --- theme sources (adapter: theme -> (file, keyword-priority)) ---
mom  = _pick(_load(f"{RES}/pilot_1m_scores.csv"), ["theme_momentum", "momentum"])
# flow: pin to the LIVE, delivery-independent theme (delivery data is stale to 2024-06); never the hist/mixed cols
flow = _pick(_load(f"{RES}/pilot_flow_factors.csv"), ["theme_flow_micro_current"])
if flow is None: flow = _pick(_load(f"{RES}/pilot_1m_scores.csv"), ["theme_flow", "flow"])
fund = _load(f"{RES}/pilot_fundamental_scores.csv")
val  = _pick(fund, ["value"]); qual = _pick(fund, ["quality"]); grow = _pick(fund, ["growth"])
# catalyst: prefer FRESH (screener_live, Mar/Jun-2026) over the stale on-disk PIT set (2023-09)
cat  = _pick(_load(f"{RES}/pilot_catalyst_factors_FRESH.csv"), ["theme_catalyst"])
if cat is None:
    cat = _pick(_load(f"{RES}/pilot_catalyst_factors.csv"), ["catalyst", "earnings_mom", "earningsmom", "theme", "surprise"])
forensic = _pick(_load(f"{RES}/pilot_forensic_score.csv"), ["forensic", "risk", "score", "penalty"])
cascade  = _pick(_load(f"{RES}/pilot_cascade_adjustments.csv"), ["net", "total", "adj"])

THEMES = {"Momentum": mom, "Value": val, "Quality": qual, "Growth": grow, "Flow": flow, "Catalyst": cat}
avail = {t: (s is not None) for t, s in THEMES.items()}

def theme_val(t, sym):
    s = THEMES[t]
    if s is None or sym not in s.index or pd.isna(s.loc[sym]): return None
    return float(s.loc[sym])

def composite(sym, horizon):
    w = W[horizon]; num = 0.0; wsum = 0.0; used = []
    for t in ["Momentum", "Value", "Quality", "Growth", "Flow", "Catalyst"]:
        v = theme_val(t, sym)
        if v is None: continue
        num += w[t] * v; wsum += w[t]; used.append(t)
    if wsum == 0: return None, []
    comp = num / wsum          # 0..100 renormalised over available themes
    return comp, used

def forensic_penalty(sym, horizon):
    if forensic is None or sym not in forensic.index or pd.isna(forensic.loc[sym]): return 0.0
    fscore = float(forensic.loc[sym])                      # 0..100, higher = worse
    maxpen = W[horizon]["Forensic"] * 200                  # 1M~10, 5Y~20, MICRO~30
    return -(fscore / 100.0) * maxpen

def cascade_adj(sym):
    if cascade is None or sym not in cascade.index or pd.isna(cascade.loc[sym]): return 0.0
    return float(np.clip(cascade.loc[sym], -20, 20))

def band(score):
    b = W["band_thresholds"]
    if score >= b["STRONG_BUY"]: return "STRONG_BUY"
    if score >= b["BUY"]: return "BUY"
    if score <= b["EXIT"]: return "EXIT"
    if score <= b["REDUCE"]: return "REDUCE"
    return "HOLD"

rows = []
for sym in PILOT:
    rec = {"symbol": sym}
    raw = {}
    for h in ["1M", "1Y", "5Y", "MICRO"]:
        comp, used = composite(sym, h)
        if comp is None:
            rec[f"score_{h}"] = np.nan; rec[f"cover_{h}"] = 0; raw[h] = None; continue
        conv = (comp - 50) * 2 + forensic_penalty(sym, h) + cascade_adj(sym)
        raw[h] = conv
        rec[f"cover_{h}"] = len(used)
    # cross-horizon coupling: large negative 1M drags 1Y/5Y
    ch = W["cross_horizon_coupling"]
    if raw.get("1M") is not None and raw["1M"] < ch["trigger_1m_below"]:
        excess = raw["1M"] - ch["trigger_1m_below"]        # negative
        if raw.get("1Y") is not None: raw["1Y"] += excess * ch["drag_to_1Y"]
        if raw.get("5Y") is not None: raw["5Y"] += excess * ch["drag_to_5Y"]
    for h in ["1M", "1Y", "5Y", "MICRO"]:
        if raw[h] is None: continue
        sc = float(np.clip(raw[h], -100, 100))
        rec[f"score_{h}"] = round(sc, 0)
        rec[f"band_{h}"] = band(sc)
        rec[f"pup_{h}"] = round(1/(1+math.exp(-sc/40)), 2)   # UNCALIBRATED monotone placeholder
    rows.append(rec)

out = pd.DataFrame(rows).set_index("symbol")
cols = []
for h in ["1M", "1Y", "5Y", "MICRO"]:
    cols += [f"score_{h}", f"band_{h}", f"pup_{h}", f"cover_{h}"]
out = out.reindex(columns=[c for c in cols if c in out.columns])
out.to_csv(os.path.join(RES, "pilot_final_scores.csv"))
json.dump({"themes_available": avail, "pilot_n": len(PILOT),
           "forensic_loaded": forensic is not None, "cascade_loaded": cascade is not None},
          open(os.path.join(RES, "scoring_coverage.json"), "w"), indent=1)

pd.set_option("display.width", 220)
print("THEME AVAILABILITY:", {k: ("Y" if v else "-") for k, v in avail.items()},
      "| forensic:", "Y" if forensic is not None else "-", "| cascade:", "Y" if cascade is not None else "-")
show = [c for c in ["score_1M","band_1M","score_1Y","band_1Y","score_5Y","band_5Y","cover_1M"] if c in out.columns]
print("\n=== PROVISIONAL MULTI-HORIZON CONVICTION (uncalibrated) ===")
print(out[show].sort_values("score_1Y" if "score_1Y" in show else show[0], ascending=False).to_string())
print("\nWrote:", os.path.join(RES, "pilot_final_scores.csv"))
