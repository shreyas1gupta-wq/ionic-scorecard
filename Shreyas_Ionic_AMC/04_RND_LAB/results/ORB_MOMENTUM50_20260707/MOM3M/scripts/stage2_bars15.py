"""Stage 2: minute -> 15-min OHLCV bars for the 509 union momentum symbols. Cached per shard (resume-safe).
IST = UTC+5:30. Drop time<09:15 (L2 preopen). bar_idx 0..24 (0=OR 09:15-09:29, 24=15:15-15:29 EOD).
OUT: cache/bars15_shard{n}.parquet
"""
import os, glob, time
import numpy as np, pandas as pd
import pyarrow.parquet as pq
import pyarrow.compute as pc

ROOT = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500"
OUT = os.path.join(ROOT, r"Shreyas_Ionic_AMC/04_RND_LAB/results/ORB_MOMENTUM50_20260707/MOM3M")
CACHE = os.path.join(OUT, "cache"); os.makedirs(CACHE, exist_ok=True)

union = set(open(os.path.join(OUT, "union_symbols.txt")).read().split("\n"))
union = {s for s in union if s}
print("union symbols:", len(union))
shards = sorted(glob.glob(os.path.join(ROOT, r"swing_momentum/data/hf_stock_minute/minute/train-*.parquet")))

for si, f in enumerate(shards):
    outp = os.path.join(CACHE, f"bars15_shard{si}.parquet")
    if os.path.exists(outp):
        print("skip (cached)", si); continue
    t0 = time.time()
    tbl = pq.read_table(f, columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"],
                        filters=[("symbol", "in", list(union))])
    df = tbl.to_pandas()
    if len(df) == 0:
        pd.DataFrame().to_parquet(outp); print("empty", si); continue
    # UTC -> IST
    ist = df["timestamp"].dt.tz_convert("Asia/Kolkata")
    df["date"] = ist.dt.normalize().dt.tz_localize(None)
    mins = ist.dt.hour * 60 + ist.dt.minute
    m = mins - (9 * 60 + 15)                       # minutes since 09:15
    df["bar_idx"] = (m // 15).astype("int32")
    df = df[(m >= 0) & (df["bar_idx"] <= 24)]      # L2: drop preopen (<09:15) & post-close
    df = df.sort_values(["symbol", "timestamp"])   # ensure order for first/last
    g = df.groupby(["symbol", "date", "bar_idx"], sort=True, observed=True)
    bars = g.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                 close=("close", "last"), volume=("volume", "sum")).reset_index()
    for c in ["open", "high", "low", "close"]:
        bars[c] = bars[c].astype("float32")
    bars.to_parquet(outp, index=False)
    print(f"shard{si}: in {len(df):,} 1min -> {len(bars):,} 15min | {bars.symbol.nunique()} syms | {time.time()-t0:.0f}s")

print("STAGE2 DONE")
