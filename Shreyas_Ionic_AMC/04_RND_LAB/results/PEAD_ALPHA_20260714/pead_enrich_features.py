"""
PEAD Q5 ENRICHMENT: add volume, pre-event momentum/RS/volatility at 21d/63d/126d,
and check entry-day gap risk (practical execution). All features strictly PIT
(computed only from data before available_date / before the entry day).
"""
import os, warnings
import numpy as np, pandas as pd
from scipy import stats
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets"
PANEL_DIR = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PEAD_ALPHA_20260714"

ev = pd.read_csv(os.path.join(OUT, "pead_events.csv"), parse_dates=["available_date"])
p = pd.read_parquet(os.path.join(PANEL_DIR, "chartlink_prices_full5yr_v2.parquet"))
p["date"] = pd.to_datetime(p["date"])
p = p.sort_values(["symbol", "date"]).reset_index(drop=True)

# NIFTY50 + Smallcap100 for relative strength
idx = pd.read_parquet(os.path.join(BASE, "index_daily", "nse_official_all_indices.parquet"),
                      columns=["index_name", "date", "close"])
idx["date"] = pd.to_datetime(idx["date"])
n50 = idx[idx["index_name"]=="Nifty 50"].sort_values("date").set_index("date")["close"]
sc100 = idx[idx["index_name"]=="NIFTY Smallcap 100"].sort_values("date").set_index("date")["close"]

print("Precomputing per-symbol indicator series...")
sym_data = {}
for sym, g in p.groupby("symbol"):
    g = g.sort_values("date").reset_index(drop=True)
    g["turnover_cr"] = g["close"]*g["volume"]/1e7
    g["vol_avg20"] = g["volume"].rolling(20, min_periods=5).mean()
    g["ret1"] = g["close"].pct_change()
    for h in [21, 63, 126]:
        g[f"mom_{h}d"] = g["close"].pct_change(h) * 100
        g[f"rvol_{h}d"] = g["ret1"].rolling(h, min_periods=h//2).std() * np.sqrt(252) * 100
    sym_data[sym] = g.set_index("date")

def get_val(sym, d, col, dates_before=True):
    g = sym_data.get(sym)
    if g is None: return np.nan
    sub = g.loc[g.index < d] if dates_before else g.loc[g.index <= d]
    if len(sub) == 0: return np.nan
    return sub[col].iloc[-1]

rows = []
for _, r in ev.iterrows():
    sym, ad = r["symbol"], r["available_date"]
    g = sym_data.get(sym)
    if g is None: continue
    prior = g.loc[g.index < ad]
    if len(prior) < 30: continue
    last = prior.iloc[-1]
    # reaction-day volume ratio (the day of/after the announcement)
    react_row = g.loc[g.index >= ad]
    react_vol_ratio = np.nan
    if len(react_row):
        rr = react_row.iloc[0]
        react_vol_ratio = rr["volume"]/last["vol_avg20"] if last["vol_avg20"] > 0 else np.nan
    # RS vs benchmarks over 63d (before event)
    n50_now = n50.loc[n50.index <= ad]; n50_63 = n50.loc[n50.index <= ad - pd.Timedelta(days=90)]
    sc_now = sc100.loc[sc100.index <= ad]; sc_63 = sc100.loc[sc100.index <= ad - pd.Timedelta(days=90)]
    n50_ret63 = (n50_now.iloc[-1]/n50_63.iloc[-1]-1)*100 if len(n50_now) and len(n50_63) else np.nan
    sc_ret63 = (sc_now.iloc[-1]/sc_63.iloc[-1]-1)*100 if len(sc_now) and len(sc_63) else np.nan
    rs_vs_n50_63 = last.get("mom_63d", np.nan) - n50_ret63 if n50_ret63 == n50_ret63 else np.nan
    rs_vs_sc_63 = last.get("mom_63d", np.nan) - sc_ret63 if sc_ret63 == sc_ret63 else np.nan

    out = {"symbol": sym, "available_date": ad, "reaction_pct": r["reaction_pct"],
           "fwd_20d": r["fwd_20d"], "fwd_60d": r["fwd_60d"], "fwd_120d": r["fwd_120d"],
           "react_vol_ratio": react_vol_ratio,
           "mom_21d_pre": last.get("mom_21d", np.nan), "mom_63d_pre": last.get("mom_63d", np.nan),
           "mom_126d_pre": last.get("mom_126d", np.nan),
           "rvol_21d_pre": last.get("rvol_21d", np.nan), "rvol_63d_pre": last.get("rvol_63d", np.nan),
           "rvol_126d_pre": last.get("rvol_126d", np.nan),
           "rs_vs_n50_63": rs_vs_n50_63, "rs_vs_sc100_63": rs_vs_sc_63,
           "turnover_cr_pre": last["turnover_cr"], "close_pre": last["close"]}
    rows.append(out)

df = pd.DataFrame(rows)
df["quarter"] = df["available_date"].dt.to_period("Q")
df["decile_rank"] = df.groupby("quarter")["reaction_pct"].transform(
    lambda x: pd.qcut(x, 5, labels=False, duplicates="drop") if x.nunique() >= 5 else np.nan)
q5 = df[df["decile_rank"] == 4].dropna(subset=["fwd_60d"])
print(f"\nQ5 events with enriched features: {len(q5)}")

def sub_test(mask, label, ret_col="fwd_60d"):
    sub = q5[mask]; rest = q5[~mask]
    if len(sub) < 15:
        print(f"  {label:<40} n={len(sub):>4} (too few)")
        return
    t, pv = stats.ttest_ind(sub[ret_col], rest[ret_col], equal_var=False)
    print(f"  {label:<40} n={len(sub):>4} mean={sub[ret_col].mean():>7.2f}% (rest={rest[ret_col].mean():>6.2f}%) "
          f"win={( sub[ret_col]>0).mean()*100:>5.1f}%  p={pv:.4f}")

print("\n" + "="*100)
print("WITHIN Q5: does volume, momentum, RS, or pre-event volatility further sort the winners? (fwd_60d)")
print("="*100)
print("\n-- Reaction-day volume --")
sub_test(q5["react_vol_ratio"] >= q5["react_vol_ratio"].median(), "High volume (>=median)")
sub_test(q5["react_vol_ratio"] >= 3, "Volume >= 3x avg")
sub_test(q5["react_vol_ratio"] < 1.5, "Volume < 1.5x avg (weak confirmation)")

print("\n-- Pre-event momentum (already trending BEFORE the earnings catalyst) --")
for h in ["21d", "63d", "126d"]:
    col = f"mom_{h}_pre"
    sub_test(q5[col] >= q5[col].median(), f"Above-median {h} momentum pre-event")
sub_test(q5["mom_126d_pre"] < 0, "NEGATIVE 6m momentum pre-event (turnaround/reversal case)")

print("\n-- Relative strength vs benchmarks (63d pre-event) --")
sub_test(q5["rs_vs_n50_63"] > 0, "Beat NIFTY50 over trailing 3m before event")
sub_test(q5["rs_vs_sc100_63"] > 0, "Beat Smallcap100 over trailing 3m before event")

print("\n-- Pre-event volatility (compression vs expansion) --")
for h in ["21d", "63d", "126d"]:
    col = f"rvol_{h}_pre"
    sub_test(q5[col] < q5[col].median(), f"LOW (below-median) realized vol, {h} pre-event (compression)")

print("\n-- Combined: momentum + volume confirmation --")
sub_test((q5["mom_63d_pre"] > 0) & (q5["react_vol_ratio"] >= 2), "3m uptrend AND reaction vol>=2x")
sub_test((q5["mom_63d_pre"] <= 0) & (q5["react_vol_ratio"] >= 2), "3m downtrend/flat BUT reaction vol>=2x (turnaround)")

df.to_csv(os.path.join(OUT, "pead_enriched_features.csv"), index=False)
print(f"\nSaved pead_enriched_features.csv ({len(df)} events)")
