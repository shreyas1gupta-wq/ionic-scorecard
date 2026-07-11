"""
FEATURE LAB — what separates winning breakout signals from losers?
Strict point-in-time: every feature uses only bars/filings dated <= signal date.
Outcome: raw forward 30-trading-day return from next-day open (no SL), plus MFE/MAE.

Outputs:
  signal_features_pit.csv   - full feature matrix
  feature_quintiles.csv     - univariate quintile analysis
  ml_report.txt             - time-split GBM results + importances
"""
import os, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
BASE = os.path.join(ROOT, "datasets")
OUT = os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710")
SIG_CSV = r"C:\Users\Shreyas.1Gupta\Downloads\Backtest D_2026_3 (2).csv"
START = pd.Timestamp("2022-10-01")

print("Loading signals + panel...")
sig = pd.read_csv(SIG_CSV)
sig["Date"] = pd.to_datetime(sig["Date"], format="%d-%m-%Y")
sig = sig[sig["Date"] >= START].sort_values("Date").reset_index(drop=True)

panel = pd.read_parquet(os.path.join(OUT, "chartlink_prices_full5yr.parquet"))
panel["date"] = pd.to_datetime(panel["date"])
sym_df = {}
for s, g in panel.groupby("symbol"):
    g = g.sort_values("date").reset_index(drop=True)
    sym_df[s] = g

# NIFTY context
idx = pd.read_parquet(os.path.join(BASE, "index_daily", "nifty50.parquet"))
tcol = "timestamp" if "timestamp" in idx.columns else "date"
idx["date"] = pd.to_datetime(idx[tcol])
if idx["date"].dt.tz is not None: idx["date"] = idx["date"].dt.tz_localize(None)
idx = idx.sort_values("date").reset_index(drop=True)
idx["n_sma20"] = idx["close"].rolling(20).mean()
idx["n_r21"] = idx["close"].pct_change(21)
nifty_map = idx.set_index("date")[["close", "n_sma20", "n_r21"]]

# Earnings PIT
ep = pd.read_parquet(os.path.join(BASE, "earnings_pit", "unified_quarterly_pit.parquet"),
                     columns=["symbol", "available_date", "quarter_end", "sales", "net_profit"])
ep["available_date"] = pd.to_datetime(ep["available_date"])
ep["quarter_end"] = pd.to_datetime(ep["quarter_end"])
ep = ep.dropna(subset=["available_date"]).sort_values(["symbol", "available_date"])
prev = ep[["symbol", "quarter_end", "sales", "net_profit"]].copy()
prev["quarter_end"] = prev["quarter_end"] + pd.DateOffset(years=1)
prev = prev.rename(columns={"sales": "sales_prev", "net_profit": "np_prev"})
ep = ep.merge(prev, on=["symbol", "quarter_end"], how="left")
ep["sales_yoy"] = (ep["sales"] - ep["sales_prev"]) / ep["sales_prev"].abs() * 100
ep["np_yoy"] = (ep["net_profit"] - ep["np_prev"]) / ep["np_prev"].abs() * 100
earn_by_sym = {s: g[["available_date", "net_profit", "sales_yoy", "np_yoy"]].values
               for s, g in ep.groupby("symbol")}

print("Computing features per signal...")
rows = []
for _, r in sig.iterrows():
    s, sd = r["Symbol"], r["Date"]
    g = sym_df.get(s)
    if g is None: continue
    ix = g.index[g["date"] == sd]
    if len(ix) == 0: continue
    i = ix[0]
    if i < 60 or i + 31 >= len(g):
        hist_ok = i >= 60
        fwd_ok = i + 31 < len(g)
        if not hist_ok: continue
    o, h, l, c, v = g.loc[i, ["open", "high", "low", "close", "volume"]]
    pc = g.loc[i-1, "close"]
    hist = g.iloc[max(0, i-260):i+1]
    cl = hist["close"]; hi = hist["high"]; lo = hist["low"]; vol = hist["volume"]

    rng = h - l
    feat = {
        "symbol": s, "signal_date": sd,
        "mcap": r.get("Marketcapname", ""), "sector": r.get("Sector", ""),
        # signal-day candle anatomy
        "chg_pct": (c/pc-1)*100,
        "gap_pct": (o/pc-1)*100,
        "body_pct": (c-o)/o*100,
        "upper_wick_pct": (h-max(o, c))/c*100,
        "lower_wick_pct": (min(o, c)-l)/c*100,
        "close_in_range": (c-l)/rng if rng > 0 else 1.0,
        "range_pct": rng/pc*100,
        "vol_ratio": v/vol.iloc[-21:-1].mean() if vol.iloc[-21:-1].mean() > 0 else np.nan,
        "turnover_cr": c*v/1e7,
        # momentum stack (pre-signal)
        "ret_5d": (pc/cl.iloc[-7]-1)*100 if len(cl) >= 7 else np.nan,
        "ret_21d": (pc/cl.iloc[-22]-1)*100 if len(cl) >= 22 else np.nan,
        "ret_63d": (pc/cl.iloc[-64]-1)*100 if len(cl) >= 64 else np.nan,
        "ret_126d": (pc/cl.iloc[-127]-1)*100 if len(cl) >= 127 else np.nan,
        "ret_252d": (pc/cl.iloc[-253]-1)*100 if len(cl) >= 253 else np.nan,
    }
    # trend / extension
    sma20 = cl.iloc[-21:-1].mean(); sma50 = cl.iloc[-51:-1].mean() if len(cl) >= 51 else np.nan
    sma200 = cl.iloc[-201:-1].mean() if len(cl) >= 201 else np.nan
    feat["dist_sma20_pct"] = (c/sma20-1)*100
    feat["dist_sma50_pct"] = (c/sma50-1)*100 if sma50 == sma50 else np.nan
    feat["dist_sma200_pct"] = (c/sma200-1)*100 if sma200 == sma200 else np.nan
    feat["golden"] = int(sma50 == sma50 and sma200 == sma200 and sma50 > sma200)
    hi252 = hi.iloc[:-1].max()
    feat["dist_52wh_pct"] = (c/hi252-1)*100
    feat["new_52wh"] = int(c >= hi252)
    # 52w position
    lo252 = lo.iloc[:-1].min()
    feat["pos_52w"] = (c-lo252)/(hi252-lo252) if hi252 > lo252 else np.nan
    # base length: days since close was last within 3% of today's close (before the run)
    prior = cl.iloc[:-1].values
    above = np.where(prior >= c*0.97)[0]
    feat["base_days"] = (len(prior) - 1 - above[-1]) if len(above) else len(prior)
    # volatility / compression
    tr = pd.concat([hi-lo, (hi-cl.shift(1)).abs(), (lo-cl.shift(1)).abs()], axis=1).max(axis=1)
    atr14 = tr.iloc[-15:-1].mean()
    feat["atr_pct"] = atr14/pc*100
    rng5 = (hi.iloc[-6:-1] - lo.iloc[-6:-1]).mean()
    rng20 = (hi.iloc[-21:-1] - lo.iloc[-21:-1]).mean()
    feat["vcp_ratio"] = rng5/rng20 if rng20 > 0 else np.nan   # <1 = contracting
    feat["bb_width_pct"] = cl.iloc[-21:-1].std()*4/sma20*100
    # consecutive up days before signal
    diffs = np.sign(np.diff(cl.iloc[-11:].values))
    consec = 0
    for d_ in diffs[::-1][1:]:
        if d_ > 0: consec += 1
        else: break
    feat["consec_up_before"] = consec
    feat["ret_3d_before"] = (pc/cl.iloc[-4]-1)*100 if len(cl) >= 4 else np.nan
    # RSI14
    delta = cl.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, min_periods=14).mean()
    rs = gain/loss.replace(0, np.nan)
    feat["rsi14"] = float((100-100/(1+rs)).iloc[-1])
    # volume pattern: up-day vol vs down-day vol last 20
    h20 = g.iloc[max(0, i-20):i]
    prev_c20 = h20["close"].shift(1).bfill()
    upv = h20.loc[h20["close"] > prev_c20, "volume"].mean()
    dnv = h20.loc[h20["close"] <= prev_c20, "volume"].mean()
    feat["updown_vol_ratio"] = upv/dnv if dnv and dnv > 0 else np.nan
    # market context (as of signal date)
    nrow = nifty_map[nifty_map.index <= sd].tail(1)
    if len(nrow):
        feat["nifty_above20"] = int(nrow["close"].iloc[0] > nrow["n_sma20"].iloc[0])
        feat["nifty_r21_pct"] = nrow["n_r21"].iloc[0]*100
    # earnings PIT
    eg = earn_by_sym.get(s)
    feat["days_since_earn"] = np.nan
    feat["earn_recent7"] = 0; feat["sales_yoy"] = np.nan; feat["np_yoy"] = np.nan
    if eg is not None:
        past = [(ad, npf, syo, nyo) for ad, npf, syo, nyo in eg if pd.notna(ad) and ad <= sd]
        if past:
            ad, npf, syo, nyo = past[-1]
            feat["days_since_earn"] = (sd-ad).days
            feat["earn_recent7"] = int((sd-ad).days <= 7)
            feat["sales_yoy"] = syo if syo == syo else np.nan
            feat["np_yoy"] = nyo if nyo == nyo else np.nan
    # ---------- OUTCOME (forward, next-day open entry) ----------
    if i+1 < len(g):
        e_o = g.loc[i+1, "open"]
        fwd = g.iloc[i+2:i+32]
        if e_o > 0 and len(fwd) >= 10:
            feat["fwd30_ret"] = (fwd["close"].iloc[-1]/e_o-1)*100
            feat["mfe30"] = (fwd["high"].max()/e_o-1)*100
            feat["mae30"] = (fwd["low"].min()/e_o-1)*100
            rows.append(feat)

df = pd.DataFrame(rows)
print(f"Feature matrix: {df.shape}")
df.to_csv(os.path.join(OUT, "signal_features_pit.csv"), index=False)

# ================= UNIVARIATE QUINTILES =================
print("\n" + "="*90)
print("UNIVARIATE: quintile mean fwd30 return / win-rate  (win = fwd30 > 0)")
print("="*90)
FEATS = ["chg_pct","gap_pct","body_pct","upper_wick_pct","lower_wick_pct","close_in_range",
         "vol_ratio","turnover_cr","ret_5d","ret_21d","ret_63d","ret_126d","ret_252d",
         "dist_sma20_pct","dist_sma50_pct","dist_sma200_pct","dist_52wh_pct","pos_52w",
         "base_days","atr_pct","vcp_ratio","bb_width_pct","consec_up_before","ret_3d_before",
         "rsi14","updown_vol_ratio","nifty_r21_pct","days_since_earn","sales_yoy","np_yoy"]
qrows = []
for f in FEATS:
    if f not in df.columns: continue
    d2 = df.dropna(subset=[f, "fwd30_ret"])
    if len(d2) < 150: continue
    try:
        d2["q"] = pd.qcut(d2[f], 5, labels=False, duplicates="drop")
    except Exception:
        continue
    qm = d2.groupby("q").agg(mean_ret=("fwd30_ret","mean"), win=("fwd30_ret", lambda x: (x>0).mean()*100),
                             n=("fwd30_ret","size"), lo=(f,"min"), hi=(f,"max"))
    spread = qm["mean_ret"].iloc[-1] - qm["mean_ret"].iloc[0]
    qrows.append({"feature": f, "Q1_ret": round(qm['mean_ret'].iloc[0],2), "Q3_ret": round(qm['mean_ret'].iloc[len(qm)//2],2),
                  "Q5_ret": round(qm['mean_ret'].iloc[-1],2), "spread_Q5_Q1": round(spread,2),
                  "Q1_win": round(qm['win'].iloc[0],1), "Q5_win": round(qm['win'].iloc[-1],1)})
    print(f"{f:<20} Q1 {qm['mean_ret'].iloc[0]:>6.2f}% ... Q5 {qm['mean_ret'].iloc[-1]:>6.2f}%   spread {spread:>+6.2f}  "
          f"win Q1 {qm['win'].iloc[0]:>4.1f}% Q5 {qm['win'].iloc[-1]:>4.1f}%")
qdf = pd.DataFrame(qrows).sort_values("spread_Q5_Q1", key=abs, ascending=False)
qdf.to_csv(os.path.join(OUT, "feature_quintiles.csv"), index=False)

# binary flags
print("\nBinary flags:")
for f in ["earn_recent7", "new_52wh", "golden", "nifty_above20"]:
    if f in df.columns:
        for val, gd in df.groupby(f):
            print(f"  {f}={val}: n={len(gd)}, mean fwd30 {gd['fwd30_ret'].mean():.2f}%, win {(gd['fwd30_ret']>0).mean()*100:.1f}%")

# WINNERS vs LOSERS profile
print("\nWINNER (fwd30>=+10%) vs LOSER (fwd30<=-5%) feature means:")
wn = df[df["fwd30_ret"] >= 10]; ls = df[df["fwd30_ret"] <= -5]
print(f"  winners n={len(wn)}, losers n={len(ls)}")
for f in FEATS:
    if f in df.columns and wn[f].notna().sum() > 50:
        print(f"  {f:<20} win {wn[f].mean():>9.2f} | lose {ls[f].mean():>9.2f}")

# ================= ML: time-split GBM =================
print("\n" + "="*90)
print("ML: HistGradientBoosting, train <= 2024-12-31, test 2025-01+ (strict time split)")
print("="*90)
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance

ml = df.copy()
ml["mcap_c"] = ml["mcap"].astype("category").cat.codes
X_cols = [f for f in FEATS if f in ml.columns] + ["earn_recent7","new_52wh","golden","nifty_above20","mcap_c"]
ml = ml.dropna(subset=["fwd30_ret"])
tr = ml[ml["signal_date"] <= "2024-12-31"]
te = ml[ml["signal_date"] >= "2025-01-01"]
print(f"train {len(tr)} / test {len(te)}")
Xtr, ytr = tr[X_cols], tr["fwd30_ret"]
Xte, yte = te[X_cols], te["fwd30_ret"]

reg = HistGradientBoostingRegressor(max_depth=3, max_iter=200, learning_rate=0.05,
                                    min_samples_leaf=40, random_state=42)
reg.fit(Xtr, ytr)
pred = reg.predict(Xte)
te2 = te.copy(); te2["pred"] = pred
te2["pq"] = pd.qcut(te2["pred"], 5, labels=False, duplicates="drop")
print("\nOOS (2025-26) quintiles by model score:")
for q, gq in te2.groupby("pq"):
    print(f"  Q{q+1}: n={len(gq)}, mean fwd30 {gq['fwd30_ret'].mean():>6.2f}%, win {(gq['fwd30_ret']>0).mean()*100:.1f}%")
ic = np.corrcoef(pred, yte)[0,1]
print(f"OOS IC (corr pred vs actual): {ic:.3f}")

imp = permutation_importance(reg, Xte, yte, n_repeats=5, random_state=42)
imp_df = pd.DataFrame({"feature": X_cols, "importance": imp.importances_mean}).sort_values("importance", ascending=False)
print("\nTop 15 permutation importances (OOS):")
print(imp_df.head(15).to_string(index=False))

with open(os.path.join(OUT, "ml_report.txt"), "w", encoding="utf-8") as fh:
    fh.write(f"train {len(tr)} test {len(te)} | OOS IC {ic:.3f}\n")
    fh.write(te2.groupby("pq")["fwd30_ret"].agg(["mean","count"]).to_string() + "\n\n")
    fh.write(imp_df.to_string(index=False))
print("\nSaved: signal_features_pit.csv, feature_quintiles.csv, ml_report.txt")
