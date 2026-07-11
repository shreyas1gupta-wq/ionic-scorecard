"""S2: minute -> BOTH 5-min and 15-min OHLCV bars for the 1-month-momentum union symbols.
One pass per shard (expensive read done once), resample to both timeframes. Cached per shard (resume-safe).
IST = UTC+5:30. Drop time<09:15 (L2 preopen). 15-min idx 0..24; 5-min idx 0..74.
OUT: cache/bars15_shard{n}.parquet, cache/bars5_shard{n}.parquet
"""
import os, glob, time, sys
import numpy as np, pandas as pd
import pyarrow.parquet as pq

ROOT = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500"
OUT = os.path.join(ROOT, r"Shreyas_Ionic_AMC/04_RND_LAB/results/ORB_SHORTONLY_20260707/MOM1M")
CACHE = os.path.join(OUT, "cache"); os.makedirs(CACHE, exist_ok=True)

union = {s for s in open(os.path.join(OUT, "union_symbols.txt")).read().split("\n") if s}
print("union symbols:", len(union), flush=True)
shards = sorted(glob.glob(os.path.join(ROOT, r"swing_momentum/data/hf_stock_minute/minute/train-*.parquet")))

def resample(df, step, maxidx):
    m = df["_min"].values
    bar_idx = (m // step).astype("int32")
    sub = df.assign(bar_idx=bar_idx)
    sub = sub[(m >= 0) & (bar_idx <= maxidx)]
    g = sub.groupby(["symbol", "date", "bar_idx"], sort=True, observed=True)
    bars = g.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                 close=("close", "last"), volume=("volume", "sum")).reset_index()
    for c in ["open", "high", "low", "close"]:
        bars[c] = bars[c].astype("float32")
    return bars

# which shards still need doing (either timeframe missing)
todo = [i for i in range(len(shards))
        if not (os.path.exists(os.path.join(CACHE, f"bars15_shard{i}.parquet"))
                and os.path.exists(os.path.join(CACHE, f"bars5_shard{i}.parquet")))]
print("shards to process:", todo, flush=True)

for si in todo:
    f = shards[si]
    t0 = time.time()
    tbl = pq.read_table(f, columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"],
                        filters=[("symbol", "in", list(union))])
    df = tbl.to_pandas()
    if len(df) == 0:
        pd.DataFrame().to_parquet(os.path.join(CACHE, f"bars15_shard{si}.parquet"))
        pd.DataFrame().to_parquet(os.path.join(CACHE, f"bars5_shard{si}.parquet"))
        print("empty", si, flush=True); continue
    ist = df["timestamp"].dt.tz_convert("Asia/Kolkata")
    df["date"] = ist.dt.normalize().dt.tz_localize(None)
    df["_min"] = (ist.dt.hour * 60 + ist.dt.minute) - (9 * 60 + 15)   # minutes since 09:15
    df = df.sort_values(["symbol", "timestamp"])
    b15 = resample(df, 15, 24)
    b5 = resample(df, 5, 74)
    b15.to_parquet(os.path.join(CACHE, f"bars15_shard{si}.parquet"), index=False)
    b5.to_parquet(os.path.join(CACHE, f"bars5_shard{si}.parquet"), index=False)
    print(f"shard{si}: {len(df):,} 1min -> {len(b15):,} 15m / {len(b5):,} 5m | "
          f"{df.symbol.nunique()} syms | {time.time()-t0:.0f}s", flush=True)

print("STAGE2 DONE", flush=True)
