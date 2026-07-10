"""T6 step 1: verify minute-level OI exists in HF NIFTY weekly option files.
Checks: column name, nonzero coverage, step-not-tick behaviour (intraday changes
should be sparse/blocky, not every-bar noise)."""
import pandas as pd, pyarrow.parquet as pq, numpy as np
from pathlib import Path

BASE = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\datasets\raw\hf_index_options_1m\options\NIFTY")
samples = ["2021-07-01.parquet", "2022-03-03.parquet", "2023-06-01.parquet", "2025-01-02.parquet", "2026-04-07.parquet"]

for f in samples:
    p = BASE / f
    if not p.exists():
        print(f, "MISSING"); continue
    sch = pq.read_schema(p)
    cols = sch.names
    df = pq.read_table(p, columns=["timestamp","strike","option_type","open_interest","volume","close","trading_day"]).to_pandas()
    df["t"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    nz = (df["open_interest"] > 0).mean()
    # pick a liquid CE strike (max total volume) and inspect its OI path on one day
    ce = df[df["option_type"]=="CE"]
    k = ce.groupby("strike")["volume"].sum().idxmax()
    day = sorted(ce["trading_day"].astype(str).unique())[-2]
    s = ce[(ce["strike"]==k) & (ce["trading_day"].astype(str)==day)].sort_values("t")
    oi = s["open_interest"].to_numpy()
    changes = (np.diff(oi) != 0)
    print(f"{f}: cols_has_oi={'open_interest' in cols}  rows={len(df):,}  nonzero_oi={nz:.1%}")
    print(f"  liquid CE {k} on {day}: bars={len(s)}, OI min/max={oi.min():,}/{oi.max():,}, "
          f"pct_bars_oi_changes={changes.mean():.1%}, n_distinct_oi={len(np.unique(oi))}, "
          f"intraday_range_pct={(oi.max()-oi.min())/max(oi.mean(),1):.1%}")
