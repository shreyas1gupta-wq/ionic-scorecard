"""
SWING-POINT REVERSAL TEST v2 — LOOKAHEAD-FIXED.
v1 used a CENTERED rolling window to find swing lows (needs future bars to
confirm), so the "signal" wasn't knowable until after part of the forward
return window had already elapsed. Fixed here: a swing low at bar t-k is only
confirmed using bars up to and including the CURRENT bar t (k bars of
no-new-low AFTER the low, all in the past relative to t). Forward returns are
measured from t (the bar where the signal becomes knowable), not from t-k.
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

K = 3  # confirmation bars (strictly backward-looking)

for freq, label in [("5min", "5-minute"), ("15min", "15-minute"), ("30min", "30-minute")]:
    print("\n" + "="*100)
    print(f"SWING REVERSAL TEST v2 (no lookahead) — {label} bars, confirm={K} bars back")
    print("="*100)
    r = resample(m, freq).reset_index()

    for src in ["midcap", "micro"]:
        low_col = f"{src}_low"; close_col = f"{src}_close"
        n = len(r)
        # at bar t: was bar (t-K) the minimum low over [t-2K, t] (i.e. using ONLY
        # bars up to and including t - no future data)? and has price since
        # closed back above that low (reversal confirmed by bar t)?
        signal = np.zeros(n, dtype=bool)
        for i in range(2*K, n):
            window_lows = r[low_col].iloc[i-2*K:i+1].values  # bars [t-2K .. t], all <= t
            candidate_idx = i - K  # the tentative low, K bars back from "now" (t=i)
            candidate_low = r[low_col].iloc[candidate_idx]
            if candidate_low == window_lows.min() and candidate_low == r[low_col].iloc[i-2*K:candidate_idx+1].min():
                # candidate_idx is the lowest point in the trailing 2K+1 window as of now
                if r[close_col].iloc[i] > candidate_low:  # reversal: current close back above that low
                    signal[i] = True
        r[f"{src}_signal_v2"] = signal

        ev_idx = r.index[r[f"{src}_signal_v2"]]
        fwd3 = []; fwd6 = []
        for idx in ev_idx:
            if idx + 3 < n:
                fwd3.append(r["nifty_close"].iloc[idx+3] / r["nifty_close"].iloc[idx] - 1)
            if idx + 6 < n:
                fwd6.append(r["nifty_close"].iloc[idx+6] / r["nifty_close"].iloc[idx] - 1)
        fwd3 = np.array(fwd3); fwd6 = np.array(fwd6)
        base3 = (r["nifty_close"].shift(-3) / r["nifty_close"] - 1).dropna().values
        base6 = (r["nifty_close"].shift(-6) / r["nifty_close"] - 1).dropna().values

        if len(fwd3) < 20:
            print(f"  {src}: too few confirmed signals ({len(fwd3)})")
            continue
        t3, p3 = stats.ttest_ind(fwd3, base3, equal_var=False)
        t6, p6 = stats.ttest_ind(fwd6, base6, equal_var=False) if len(fwd6) > 20 else (np.nan, np.nan)
        print(f"  {src} (n={len(fwd3)}): NIFTY fwd-3bar mean {fwd3.mean()*100:+.4f}% (base {base3.mean()*100:+.4f}%) "
              f"win={ (fwd3>0).mean()*100:.1f}% p={p3:.4f}")
        print(f"  {src} (n={len(fwd6)}): NIFTY fwd-6bar mean {fwd6.mean()*100:+.4f}% (base {base6.mean()*100:+.4f}%) "
              f"win={(fwd6>0).mean()*100:.1f}% p={p6:.4f}")

print("\nDone (v2, no-lookahead swing signal).")
