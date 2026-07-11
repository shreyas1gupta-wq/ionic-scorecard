"""Stage 2: minute -> 5-MIN OHLCV bars for the union momentum symbols. Cached per shard (resume-safe).
IST = UTC+5:30. Drop time<09:15 (L2 preopen). bar_idx 0..74 (0=OR 09:15-09:19, 74=15:25-15:29 EOD).
15-min bars are derived from these in stage3 (bar15 = bar5//3), so only ONE pass over raw minute data.
OUT: cache/bars5_shard{n}.parquet
"""
import os, glob, time
import numpy as np, pandas as pd
import pyarrow.parquet as pq

ROOT = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500"
OUT = os.path.join(ROOT, r"Shreyas_Ionic_AMC/04_RND_LAB/results/ORB_SHORTONLY_20260707/MOM2W")
CACHE = os.path.join(OUT, "cache"); os.makedirs(CACHE, exist_ok=True)

union = {s for s in open(os.path.join(OUT, "union_symbols.txt")).read().split("\n") if s}
print("union symbols:", len(union))
shards = sorted(glob.glob(os.path.join(ROOT, r"swing_momentum/data/hf_stock_minute/minute/train-*.parquet")))

for si, f in enumerate(shards):
    outp = os.path.join(CACHE, f"bars5_shard{si}.parquet")
    if os.path.exists(outp):
        print("skip (cached)", si); continue
    t0 = time.time()
    tbl = pq.read_table(f, columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"],
                        filters=[("symbol", "in", list(union))])
    df = tbl.to_pandas()
    if len(df) == 0:
        pd.DataFrame().to_parquet(outp); print("empty", si); continue
    ist = df["timestamp"].dt.tz_convert("Asia/Kolkata")          # L1 tz fix
    df["date"] = ist.dt.normalize().dt.tz_localize(None)
    mins = ist.dt.hour * 60 + ist.dt.minute
    m = mins - (9 * 60 + 15)                                     # minutes since 09:15
    df["bar_idx"] = (m // 5).astype("int32")
    df = df[(m >= 0) & (df["bar_idx"] <= 74)]                    # L2: drop preopen & post-close
    df = df.sort_values(["symbol", "timestamp"])
    g = df.groupby(["symbol", "date", "bar_idx"], sort=True, observed=True)
    bars = g.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                 close=("close", "last"), volume=("volume", "sum")).reset_index()
    for c in ["open", "high", "low", "close"]:
        bars[c] = bars[c].astype("float32")
    bars.to_parquet(outp, index=False)
    print(f"shard{si}: {len(df):,} 1min -> {len(bars):,} 5min | {bars.symbol.nunique()} syms | {time.time()-t0:.0f}s")

print("STAGE2 DONE")
