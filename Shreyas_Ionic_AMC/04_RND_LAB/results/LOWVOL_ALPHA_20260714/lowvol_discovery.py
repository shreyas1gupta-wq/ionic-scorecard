"""
NEW ALPHA #2: LOW-VOLATILITY ANOMALY
=====================================
Classic, robust, well-documented factor (Ang-Hjalmarsson-Xing, AQR "Betting
Against Beta") — low-volatility stocks tend to outperform high-volatility
stocks on a risk-adjusted basis, and often on absolute basis too, because
high-vol names get systematically overbought by leverage-constrained/lottery-
seeking investors. Genuinely DIFFERENT from Chartlink (momentum breakout) and
PEAD (earnings-event) — this is a defensive, quality-tilted factor. If it
works, it's a real diversifier since its return driver is structurally
different (low correlation expected in bad momentum years like 2022/2025).

Method: monthly rebalance, rank all liquid stocks by trailing 126d (6m)
realized volatility, quintile sort, track forward 1-month return by quintile
(strict PIT — vol computed only from data up to and including month-end,
forward return starts next trading day).
"""
import os, warnings
import numpy as np, pandas as pd
from scipy import stats
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets"
PANEL_DIR = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\LOWVOL_ALPHA_20260714"
os.makedirs(OUT, exist_ok=True)

print("Loading daily stock panel...")
p = pd.read_parquet(os.path.join(PANEL_DIR, "chartlink_prices_full5yr_v2.parquet"))
p["date"] = pd.to_datetime(p["date"])
p = p.sort_values(["symbol", "date"]).reset_index(drop=True)
p["turnover_cr"] = p["close"]*p["volume"]/1e7
print(f"{len(p):,} rows, {p['symbol'].nunique()} symbols, {p['date'].min().date()} -> {p['date'].max().date()}")

rows = []
for sym, g in p.groupby("symbol"):
    g = g.sort_values("date").reset_index(drop=True)
    if len(g) < 150:
        continue
    g["ret1"] = g["close"].pct_change()
    g["rvol_126d"] = g["ret1"].rolling(126, min_periods=100).std() * np.sqrt(252) * 100
    g["avg_turnover_20d"] = g["turnover_cr"].rolling(20, min_periods=10).mean()
    g["fwd_21d_ret"] = (g["close"].shift(-21) / g["close"] - 1) * 100  # ~1 month forward
    g["month"] = g["date"].dt.to_period("M")
    rows.append(g[["symbol","date","month","close","rvol_126d","avg_turnover_20d","fwd_21d_ret"]])

d = pd.concat(rows, ignore_index=True)
d = d.dropna(subset=["rvol_126d", "fwd_21d_ret"])
d = d[d["avg_turnover_20d"] >= 3.0]   # basic liquidity floor
print(f"After vol/liquidity filter: {len(d):,} stock-days")

# take one observation per stock per month (month-end) for a clean monthly rebalance test
d["is_month_end"] = d.groupby(["symbol","month"])["date"].transform("max") == d["date"]
me = d[d["is_month_end"]].copy()
me["quintile"] = me.groupby("month")["rvol_126d"].transform(
    lambda x: pd.qcut(x, 5, labels=False, duplicates="drop") if x.nunique() >= 5 else np.nan)
me = me.dropna(subset=["quintile"])
print(f"Month-end observations: {len(me):,}")

print("\n" + "="*100)
print("LOW-VOL QUINTILE SORT: forward 1-month return by trailing-6m-volatility quintile")
print("="*100)
print(f"{'Quintile':<20} {'n':>6} {'mean%':>8} {'median%':>8} {'win%':>6} {'ann.vol%':>9}")
means = {}
for q in range(5):
    sub = me[me["quintile"]==q]
    lbl = "Q1 (LOWEST vol)" if q==0 else ("Q5 (HIGHEST vol)" if q==4 else f"Q{q+1}")
    print(f"{lbl:<20} {len(sub):>6} {sub['fwd_21d_ret'].mean():>8.2f} {sub['fwd_21d_ret'].median():>8.2f} "
          f"{(sub['fwd_21d_ret']>0).mean()*100:>5.1f}% {sub['rvol_126d'].mean():>9.1f}")
    means[q] = sub["fwd_21d_ret"]
t, pv = stats.ttest_ind(means[0], means[4], equal_var=False)
print(f"\nQ1(low-vol) - Q5(high-vol) spread: {means[0].mean()-means[4].mean():+.2f}%  (t={t:.2f}, p={pv:.4f})")
sharpe_q1 = means[0].mean()/means[0].std()*np.sqrt(12)
sharpe_q5 = means[4].mean()/means[4].std()*np.sqrt(12)
print(f"Q1 monthly-return Sharpe (annualized): {sharpe_q1:.2f} | Q5: {sharpe_q5:.2f}")

me.to_csv(os.path.join(OUT, "lowvol_events.csv"), index=False)
print(f"\nSaved lowvol_events.csv ({len(me)} month-end observations)")
