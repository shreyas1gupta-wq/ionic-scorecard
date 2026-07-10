"""T6 step 1b: deep check of late-era OI (0-flicker suspicion) + dup-bar check in early era."""
import pandas as pd, pyarrow.parquet as pq, numpy as np
from pathlib import Path

BASE = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\datasets\raw\hf_index_options_1m\options\NIFTY")

def look(f, day_idx=-2):
    df = pq.read_table(BASE/f, columns=["timestamp","strike","option_type","open_interest","volume","trading_day"]).to_pandas()
    df["t"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    df = df.drop_duplicates(["t","strike","option_type"])
    ce = df[df["option_type"]=="CE"]
    k = ce.groupby("strike")["volume"].sum().idxmax()
    day = sorted(ce["trading_day"].astype(str).unique())[day_idx]
    s = ce[(ce["strike"]==k) & (ce["trading_day"].astype(str)==day)].sort_values("t")
    oi = s["open_interest"].to_numpy()
    d = np.diff(oi)
    zero_frac = (oi==0).mean()
    # flicker: nonzero -> 0 -> nonzero patterns
    flick = sum(1 for i in range(1,len(oi)-1) if oi[i]==0 and oi[i-1]>0 and oi[i+1]>0)
    print(f"{f} CE{k} {day}: bars={len(s)} zero_frac={zero_frac:.1%} flicker0={flick} "
          f"chg_rate={(d!=0).mean():.1%} med_abs_chg={np.median(np.abs(d[d!=0])) if (d!=0).any() else 0:,.0f}")
    # first/last 5 OI values
    print("  head:", oi[:5], " tail:", oi[-5:])
    # zero-OI location: time buckets
    tt = s["t"].dt.time
    z = s[s["open_interest"]==0]
    if len(z): print("  zero-OI time range:", z['t'].dt.time.min(), "->", z['t'].dt.time.max(), f"n={len(z)}")

for f in ["2025-01-02.parquet","2026-04-07.parquet","2023-06-01.parquet"]:
    look(f)
# also check dedup effect on early file (752 bars -> ?)
