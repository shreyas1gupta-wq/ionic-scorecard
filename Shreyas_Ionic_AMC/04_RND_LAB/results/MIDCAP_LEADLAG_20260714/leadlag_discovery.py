"""
MIDCAP/MICROCAP -> NIFTY LEAD-LAG DISCOVERY (does the hypothesis hold at all?)
==============================================================================
Real 1-min data: NIFTY MIDCAP150 (2019-07+), NIFTY MICROCAP250 (2022-08+),
NIFTY 50 (2015-01+). Common overlap ~2022-08 to 2026-05 (~3.75 yrs).

Tests:
 1. Cross-correlation: does MIDCAP/MICROCAP 1-min return at t predict NIFTY's
    return at t+1..t+5 minutes, ABOVE what NIFTY's own autocorrelation gives?
    (Granger-style: regress NIFTY_ret(t) on NIFTY_ret(t-1) + MIDCAP_ret(t-1),
    check if the midcap term is significant beyond NIFTY's own momentum.)
 2. Same test restricted to 9:15-10:30 and 13:00-15:15 windows vs the rest of
    day, to see if the user's hypothesized windows show a STRONGER effect.
 3. Swing-point reversal test on 5-min bars: does a MIDCAP/MICROCAP swing-low
    reversal (price turns up off a local low) predict a NIFTY move in the
    same direction over the following 15/30/60 minutes?
"""
import os, warnings
import numpy as np, pandas as pd
from scipy import stats
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\datasets\raw\kaggle\debashis74017__nifty-50-minute-data"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\MIDCAP_LEADLAG_20260714"
os.makedirs(OUT, exist_ok=True)

def load(fname):
    d = pd.read_csv(os.path.join(BASE, fname))
    d["date"] = pd.to_datetime(d["date"])
    d = d.sort_values("date").drop_duplicates("date").reset_index(drop=True)
    return d

print("Loading NIFTY 50, MIDCAP 150, MICROCAP250 1-min...")
nifty = load("NIFTY 50_minute.csv")
midcap = load("NIFTY MIDCAP 150_minute.csv")
micro = load("NIFTY MICROCAP250_minute.csv")
print(f"NIFTY: {len(nifty):,} bars {nifty['date'].min()} -> {nifty['date'].max()}")
print(f"MIDCAP150: {len(midcap):,} bars {midcap['date'].min()} -> {midcap['date'].max()}")
print(f"MICROCAP250: {len(micro):,} bars {micro['date'].min()} -> {micro['date'].max()}")

# merge on exact minute timestamp (inner join = common overlap)
m = nifty[["date","close"]].rename(columns={"close":"nifty"}).merge(
    midcap[["date","close"]].rename(columns={"close":"midcap"}), on="date", how="inner").merge(
    micro[["date","close"]].rename(columns={"close":"micro"}), on="date", how="inner")
m = m.sort_values("date").reset_index(drop=True)
print(f"\nCommon 1-min overlap: {len(m):,} bars, {m['date'].min()} -> {m['date'].max()}")

m["time"] = m["date"].dt.time
m["date_only"] = m["date"].dt.date
for col in ["nifty", "midcap", "micro"]:
    m[f"{col}_ret"] = m.groupby("date_only")[col].pct_change() * 100

m = m.dropna(subset=["nifty_ret", "midcap_ret", "micro_ret"])
print(f"After computing intraday returns (dropping day-boundary NaN): {len(m):,} bars")

def granger_test(df, label):
    """Regress nifty_ret(t) on nifty_ret(t-1) + X_ret(t-1); test if X term is significant."""
    df = df.copy()
    df["nifty_ret_lag1"] = df.groupby("date_only")["nifty_ret"].shift(1)
    results = {}
    for xcol in ["midcap_ret", "micro_ret"]:
        df[f"{xcol}_lag1"] = df.groupby("date_only")[xcol].shift(1)
        dd = df.dropna(subset=["nifty_ret", "nifty_ret_lag1", f"{xcol}_lag1"])
        if len(dd) < 100:
            results[xcol] = None; continue
        # simple OLS via numpy (avoid statsmodels dependency)
        X = np.column_stack([np.ones(len(dd)), dd["nifty_ret_lag1"], dd[f"{xcol}_lag1"]])
        y = dd["nifty_ret"].values
        beta, res, rank, sv = np.linalg.lstsq(X, y, rcond=None)
        yhat = X @ beta
        resid = y - yhat
        n, k = X.shape
        sigma2 = (resid @ resid) / (n - k)
        XtX_inv = np.linalg.inv(X.T @ X)
        se = np.sqrt(np.diag(sigma2 * XtX_inv))
        t_stat = beta[2] / se[2]
        p_val = 2 * (1 - stats.t.cdf(abs(t_stat), n - k))
        results[xcol] = {"coef": beta[2], "t": t_stat, "p": p_val, "n": n}
    print(f"\n{label} (n={len(df)}):")
    for xcol, r in results.items():
        if r is None:
            print(f"  {xcol}: insufficient data")
        else:
            print(f"  NIFTY(t) ~ NIFTY(t-1) + {xcol}(t-1): coef={r['coef']:+.4f} t={r['t']:>6.2f} p={r['p']:.4f} n={r['n']:,}")
    return results

print("\n" + "="*100)
print("TEST 1: FULL DAY - does midcap/micro 1-min return LEAD nifty by 1 minute?")
print("="*100)
granger_test(m, "Full session (all times)")

print("\n" + "="*100)
print("TEST 2: WINDOW-SPECIFIC (does the lead-lag effect concentrate in specific windows?)")
print("="*100)
def in_window(t, lo, hi):
    return (t >= pd.to_datetime(lo).time()) & (t < pd.to_datetime(hi).time())

windows = [("09:15","10:30","Opening (09:15-10:30)"), ("10:30","13:00","Midday (10:30-13:00)"),
          ("13:00","15:15","Afternoon (13:00-15:15)"), ("15:15","15:30","Close (15:15-15:30)")]
for lo, hi, lbl in windows:
    sub = m[in_window(m["time"], lo, hi)]
    granger_test(sub, lbl)

# multi-minute-ahead lead test (does midcap predict nifty 2,3,5 min ahead too?)
print("\n" + "="*100)
print("TEST 3: MULTI-MINUTE-AHEAD - does midcap/micro predict nifty 2/3/5 minutes ahead?")
print("="*100)
for lag in [1, 2, 3, 5]:
    mm = m.copy()
    mm["nifty_fwd"] = mm.groupby("date_only")["nifty"].transform(lambda x: x.shift(-lag)/x - 1) * 100
    mm = mm.dropna(subset=["nifty_fwd", "midcap_ret", "micro_ret"])
    if len(mm) < 100: continue
    for xcol in ["midcap_ret", "micro_ret"]:
        corr, p = stats.pearsonr(mm[xcol], mm["nifty_fwd"])
        print(f"  lag={lag}min | corr({xcol}(t), nifty_fwd_{lag}min) = {corr:+.4f} (p={p:.4f}, n={len(mm):,})")

m.to_parquet(os.path.join(OUT, "midcap_nifty_merged_1min.parquet"))
print(f"\nSaved midcap_nifty_merged_1min.parquet ({len(m):,} rows)")
