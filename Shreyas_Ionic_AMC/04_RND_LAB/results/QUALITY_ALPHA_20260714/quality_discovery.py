"""
NEW ALPHA #3: QUALITY FACTOR (margin level + margin stability)
================================================================
Uses earnings_pit's opm_pct (operating margin %) — real accounting data,
never used this session for a standalone factor (only for sales/profit YoY
growth). Quality investing (high, STABLE margins) is well documented,
especially strong in EM/India given large governance/quality dispersion.

Score = trailing-4-quarter avg operating margin (level) minus a penalty for
margin volatility (instability) - all strictly PIT via available_date.
Quarterly rebalance, quintile sort, forward 1/3/6-month return by quintile.
"""
import os, warnings
import numpy as np, pandas as pd
from scipy import stats
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets"
PANEL_DIR = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\QUALITY_ALPHA_20260714"
os.makedirs(OUT, exist_ok=True)

print("Loading earnings PIT + daily price panel...")
ep = pd.read_parquet(os.path.join(BASE, "earnings_pit", "unified_quarterly_pit.parquet"),
                     columns=["symbol", "available_date", "quarter_end", "opm_pct", "eps", "net_profit", "sales"])
ep["available_date"] = pd.to_datetime(ep["available_date"])
ep["quarter_end"] = pd.to_datetime(ep["quarter_end"])
ep = ep.dropna(subset=["available_date", "opm_pct"]).sort_values(["symbol", "available_date"])
print(f"Earnings PIT (with opm_pct): {len(ep):,} rows, {ep['symbol'].nunique()} symbols")

p = pd.read_parquet(os.path.join(PANEL_DIR, "chartlink_prices_full5yr_v2.parquet"))
p["date"] = pd.to_datetime(p["date"])
p = p.sort_values(["symbol", "date"]).reset_index(drop=True)
p["turnover_cr"] = p["close"]*p["volume"]/1e7
sym_dates = {}
sym_close = {}
for sym, g in p.groupby("symbol"):
    g = g.sort_values("date").reset_index(drop=True)
    sym_dates[sym] = list(g["date"])
    sym_close[sym] = g.set_index("date")["close"]

# Build trailing-4Q quality score per event, strictly PIT (only prior available_dates for that symbol)
print("Computing trailing quality scores (4-quarter avg margin, margin stability)...")
qual_rows = []
for sym, g in ep.groupby("symbol"):
    g = g.sort_values("available_date").reset_index(drop=True)
    if len(g) < 5:
        continue
    for i in range(4, len(g)):
        trailing = g.iloc[i-4:i]  # 4 quarters strictly BEFORE the current available_date row i
        cur = g.iloc[i]
        margin_avg = trailing["opm_pct"].mean()
        margin_std = trailing["opm_pct"].std()
        if margin_avg != margin_avg:
            continue
        qual_rows.append({"symbol": sym, "available_date": cur["available_date"],
                          "margin_avg": margin_avg, "margin_std": margin_std,
                          "quality_score": margin_avg - (margin_std if margin_std==margin_std else 0)})

qdf = pd.DataFrame(qual_rows)
print(f"Quality-scored events: {len(qdf)}")

# match to price panel: forward returns from 2 trading days after available_date (consistent w/ PEAD methodology)
def entry_day_for(sym, ad):
    dates = sym_dates.get(sym)
    if not dates: return None
    idx = np.searchsorted(dates, ad)
    entry_i = idx + 2
    if entry_i >= len(dates): return None
    return dates[entry_i]

rows = []
for _, r in qdf.iterrows():
    sym, ad = r["symbol"], r["available_date"]
    ed = entry_day_for(sym, ad)
    if ed is None: continue
    cl = sym_close.get(sym)
    if cl is None or ed not in cl.index: continue
    entry_px = cl.loc[ed]
    out = {"symbol": sym, "available_date": ad, "entry_date": ed,
           "quality_score": r["quality_score"], "margin_avg": r["margin_avg"], "margin_std": r["margin_std"]}
    for h, lbl in [(21, "fwd_1m"), (63, "fwd_3m"), (126, "fwd_6m")]:
        idx_pos = cl.index.get_indexer([ed])[0]
        if idx_pos + h < len(cl):
            out[lbl] = (cl.iloc[idx_pos+h] / entry_px - 1) * 100
        else:
            out[lbl] = np.nan
    rows.append(out)

d = pd.DataFrame(rows)
print(f"Matched to price data: {len(d)}")
d["quarter"] = d["available_date"].dt.to_period("Q")
d["quintile"] = d.groupby("quarter")["quality_score"].transform(
    lambda x: pd.qcut(x, 5, labels=False, duplicates="drop") if x.nunique() >= 5 else np.nan)

print("\n" + "="*100)
print("QUALITY QUINTILE SORT (margin level - margin volatility): forward return by quintile")
print("="*100)
for h in ["fwd_1m", "fwd_3m", "fwd_6m"]:
    dd = d.dropna(subset=[h, "quintile"])
    print(f"\n--- {h} (n={len(dd)}) ---")
    means = {}
    for q in range(5):
        sub = dd[dd["quintile"]==q]
        if len(sub) < 20: continue
        lbl = "Q1 (LOW quality)" if q==0 else ("Q5 (HIGH quality)" if q==4 else f"Q{q+1}")
        print(f"  {lbl:<20} n={len(sub):>5} mean={sub[h].mean():>7.2f}% median={sub[h].median():>7.2f}% win={(sub[h]>0).mean()*100:>5.1f}%")
        means[q] = sub[h]
    if 4 in means and 0 in means:
        t, pv = stats.ttest_ind(means[4], means[0], equal_var=False)
        print(f"  Q5-Q1 spread: {means[4].mean()-means[0].mean():+.2f}%  (t={t:.2f}, p={pv:.4f})")

d.to_csv(os.path.join(OUT, "quality_events.csv"), index=False)
print(f"\nSaved quality_events.csv ({len(d)} events)")
