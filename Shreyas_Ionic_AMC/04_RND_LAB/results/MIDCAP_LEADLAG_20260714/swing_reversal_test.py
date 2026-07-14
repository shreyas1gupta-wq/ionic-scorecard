"""
SWING-POINT REVERSAL TEST: does a MIDCAP/MICROCAP swing-low reversal (price
turns up off a local low on 5/15/30-min bars) predict a NIFTY move in the
SAME direction over the following 15/30/60 minutes? This tests the specific
"low-to-high / high-to-low / U-shape" pattern hypothesis, not raw 1-min corr
(which was too small to trade - see leadlag_discovery.py).

Also tests: does breaking PREVIOUS DAY's high/low on midcap/micro precede
NIFTY doing the same?
"""
import os, warnings
import numpy as np, pandas as pd
from scipy import stats
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\MIDCAP_LEADLAG_20260714"
m = pd.read_parquet(os.path.join(OUT, "midcap_nifty_merged_1min.parquet"))
m = m.set_index("date")

def resample(df, freq):
    o = df.resample(freq).agg({"nifty":"ohlc", "midcap":"ohlc", "micro":"ohlc"})
    o.columns = ['_'.join(c) for c in o.columns]
    return o.dropna()

def find_swings(s, window=3):
    """local min/max with `window` bars on each side."""
    is_low = (s == s.rolling(2*window+1, center=True).min())
    is_high = (s == s.rolling(2*window+1, center=True).max())
    return is_low, is_high

for freq, label in [("5min", "5-minute"), ("15min", "15-minute"), ("30min", "30-minute")]:
    print("\n" + "="*100)
    print(f"SWING REVERSAL TEST — {label} bars")
    print("="*100)
    r = resample(m, freq)
    r = r.reset_index()
    r["date_only"] = r["date"].dt.date
    r["time"] = r["date"].dt.time

    for src in ["midcap", "micro"]:
        low_col = f"{src}_low"; close_col = f"{src}_close"
        is_low, is_high = find_swings(r[low_col], window=3)
        r[f"{src}_swing_low"] = is_low

        # at each swing low, check subsequent 3-bar reversal (close > swing low close) = "confirmed reversal"
        r["nifty_ret_confirm3bar"] = r["nifty_close"].shift(-3) / r["nifty_close"] - 1
        r["nifty_ret_confirm6bar"] = r["nifty_close"].shift(-6) / r["nifty_close"] - 1
        r[f"{src}_confirmed_up"] = (r[close_col].shift(-2) > r[low_col]) & r[f"{src}_swing_low"]

        ev = r[r[f"{src}_confirmed_up"] == True].dropna(subset=["nifty_ret_confirm3bar"])
        base = r.dropna(subset=["nifty_ret_confirm3bar"])
        if len(ev) < 20:
            print(f"  {src}: too few swing-low-reversal events ({len(ev)})")
            continue
        t, p = stats.ttest_ind(ev["nifty_ret_confirm3bar"], base["nifty_ret_confirm3bar"], equal_var=False)
        print(f"  {src} swing-low reversal (n={len(ev)}): NIFTY fwd 3-bar mean {ev['nifty_ret_confirm3bar'].mean()*100:+.4f}% "
              f"(base {base['nifty_ret_confirm3bar'].mean()*100:+.4f}%) win={(ev['nifty_ret_confirm3bar']>0).mean()*100:.1f}% p={p:.4f}")
        t6, p6 = stats.ttest_ind(ev["nifty_ret_confirm6bar"].dropna(), base["nifty_ret_confirm6bar"].dropna(), equal_var=False)
        print(f"  {src} swing-low reversal (n={len(ev)}): NIFTY fwd 6-bar mean {ev['nifty_ret_confirm6bar'].dropna().mean()*100:+.4f}% "
              f"(base {base['nifty_ret_confirm6bar'].dropna().mean()*100:+.4f}%) p={p6:.4f}")

print("\n" + "="*100)
print("PREVIOUS-DAY HIGH/LOW BREAK TEST — does midcap/micro breaking prior-day H/L lead nifty doing the same?")
print("="*100)
daily = m.resample("D").agg({"nifty":"ohlc","midcap":"ohlc","micro":"ohlc"}).dropna()
daily.columns = ['_'.join(c) for c in daily.columns]
daily = daily.reset_index()
for src in ["nifty", "midcap", "micro"]:
    daily[f"{src}_prevhigh"] = daily[f"{src}_high"].shift(1)
    daily[f"{src}_prevlow"] = daily[f"{src}_low"].shift(1)
daily["midcap_broke_high"] = daily["midcap_high"] > daily["midcap_prevhigh"]
daily["nifty_broke_high"] = daily["nifty_high"] > daily["nifty_prevhigh"]
daily["micro_broke_high"] = daily["micro_high"] > daily["micro_prevhigh"]

ct = pd.crosstab(daily["midcap_broke_high"], daily["nifty_broke_high"], normalize="index")
print("\nP(nifty breaks prior-day high | midcap breaks prior-day high):")
print(ct.to_string())
odds, pv = stats.fisher_exact(pd.crosstab(daily["midcap_broke_high"], daily["nifty_broke_high"]))
print(f"Fisher exact p-value: {pv:.4f}")

print("\nSaved: (results printed above, no additional file needed)")
