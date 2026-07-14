"""
PRICE-BAND TEST AT LONGER HORIZONS: 30d, 63d(~3m), 100d, 126d(~6m), 200d, 252d(~12m)
forward returns from the gap>=5% trigger's entry (today's open), across the
same price bands as before. Unfiltered universe (1,039 stocks) - largest,
most powered sample. Flags n-decay as horizon lengthens (recent signals lack
enough forward history yet, and some names delist/get illiquid).
"""
import os, warnings
import numpy as np, pandas as pd
from scipy import stats
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

SCAN_DIR = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NIFTY_OPTIONS_ML_20260710_pricebands"

BINS = [0, 1, 5, 10, 25, 50, 100, 250, 500, 1000, 1500, 2000, 2500, 5000, 1e9]
LABELS = ["<1", "1-5", "5-10", "10-25", "25-50", "50-100", "100-250", "250-500", "500-1000",
          "1000-1500", "1500-2000", "2000-2500", "2500-5000", ">5000"]
HORIZONS = [30, 63, 100, 126, 200, 252]   # ~1.5m, 3m, 5m, 6m, 10m, 12m (trading days)

print("Loading daily stock panel + recomputing gap-trigger signals with long-horizon forward returns...")
p = pd.read_parquet(os.path.join(SCAN_DIR, "chartlink_prices_full5yr_v2.parquet"))
p["date"] = pd.to_datetime(p["date"])
p = p.sort_values(["symbol", "date"]).reset_index(drop=True)
print(f"{len(p):,} rows, {p['symbol'].nunique()} symbols, {p['date'].min().date()} -> {p['date'].max().date()}")

rows = []
for sym, g in p.groupby("symbol"):
    g = g.sort_values("date").reset_index(drop=True)
    if len(g) < 60:
        continue
    g["turnover_cr"] = g["close"] * g["volume"] / 1e7
    g["prev_close"] = g["close"].shift(1)
    g["gap_pct"] = (g["open"] / g["prev_close"] - 1)
    mask = (g["gap_pct"] >= 0.05) & (g["turnover_cr"] >= 5.0) & (g["open"] >= 20.0)
    if mask.sum() == 0:
        continue
    for h in HORIZONS:
        g[f"fwd_{h}d"] = (g["close"].shift(-h) / g["open"] - 1) * 100
    sub = g[mask].copy()
    sub["entry_price"] = sub["open"]
    rows.append(sub[["symbol", "date", "entry_price", "turnover_cr"] + [f"fwd_{h}d" for h in HORIZONS]])

d = pd.concat(rows, ignore_index=True)
print(f"Gap-trigger signals: {len(d)} across {d['symbol'].nunique()} symbols, {d['date'].min().date()} -> {d['date'].max().date()}")
for h in HORIZONS:
    print(f"  fwd_{h}d available: {d[f'fwd_{h}d'].notna().sum()} (dropped {d[f'fwd_{h}d'].isna().sum()} - insufficient forward history)")

def band_table(df, ret_col, horizon_label):
    dd = df.dropna(subset=["entry_price", ret_col]).copy()
    dd["band"] = pd.cut(dd["entry_price"], bins=BINS, labels=LABELS)
    print(f"\n{'='*100}\n{horizon_label}  (n={len(dd)}, overall mean {dd[ret_col].mean():.2f}%)\n{'='*100}")
    print(f"{'Band':<12} {'n':>6} {'mean%':>8} {'median%':>8} {'win%':>6} {'p-value':>9}")
    rows2 = []
    for b in LABELS:
        sub = dd[dd["band"] == b]; rest = dd[dd["band"] != b]
        if len(sub) < 5:
            print(f"{b:<12} {len(sub):>6}  (too few)")
            continue
        t, pv = stats.ttest_ind(sub[ret_col], rest[ret_col], equal_var=False)
        print(f"{b:<12} {len(sub):>6} {sub[ret_col].mean():>8.2f} {sub[ret_col].median():>8.2f} "
              f"{(sub[ret_col]>0).mean()*100:>5.1f}% {pv:>9.4f}")
        rows2.append({"band": b, "n": len(sub), "mean": sub[ret_col].mean(),
                     "median": sub[ret_col].median(), "win": (sub[ret_col]>0).mean()*100, "p": pv})
    lp = np.log(dd["entry_price"])
    corr, corr_p = stats.pearsonr(lp, dd[ret_col])
    print(f"corr(log price, {ret_col}) = {corr:.4f}  (p={corr_p:.4f})")
    return pd.DataFrame(rows2), corr, corr_p

summary = []
for h in HORIZONS:
    label = {30: "30d (~1.5 month)", 63: "63d (~3 month)", 100: "100d (~5 month)",
             126: "126d (~6 month)", 200: "200d (~10 month)", 252: "252d (~12 month)"}[h]
    rdf, corr, corr_p = band_table(d, f"fwd_{h}d", f"Forward {label} return by price band")
    rdf.to_csv(os.path.join(OUT, f"priceband_longhorizon_{h}d.csv"), index=False)
    summary.append({"horizon": label, "n": d[f"fwd_{h}d"].notna().sum(),
                    "corr_logprice": corr, "corr_p": corr_p})

print("\n" + "="*100)
print("SUMMARY: does the price-level effect strengthen or fade at longer horizons?")
print("="*100)
print(pd.DataFrame(summary).to_string(index=False))

d.to_parquet(os.path.join(OUT, "gap_trigger_longhorizon.parquet"))
print("\nSaved priceband_longhorizon_*.csv, gap_trigger_longhorizon.parquet")
