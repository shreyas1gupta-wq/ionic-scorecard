"""Dev-only smoke test on 2 expiries before dropping the full job in the queue.
Not for the queue. Run directly (cheap probe, few hundred k rows)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402

COLS = ["timestamp", "strike", "option_type", "volume", "open_interest"]


def load_lean(path):
    t0 = time.time()
    tbl = pq.read_table(path, columns=COLS)
    df = tbl.to_pandas()
    df["t"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    df = df.drop(columns=["timestamp"])
    print(f"  loaded {len(df):,} rows in {time.time()-t0:.1f}s")
    return df


def main():
    mapping, exps = chain.build_expiry_index()
    spot = pd.read_parquet(
        ROOT / "intraday_options_strategy/datasets/raw/hf_index_options_1m/index/NIFTY.parquet"
    )
    spot["t"] = pd.to_datetime(spot["timestamp"]).dt.tz_localize(None)
    spot = spot.drop_duplicates("t").set_index("t").sort_index()[["close"]]
    spot_min = spot["close"]  # Series indexed by minute

    for exp in exps[100:102]:
        print("expiry", exp)
        df = load_lean(mapping[exp])
        df["bucket"] = df["t"].dt.floor("15min")
        # dedup + collapse via max (cheap, avoids drop_duplicates on full frame)
        g = df.groupby(["t", "strike", "option_type"], as_index=False).agg(
            volume=("volume", "max"), open_interest=("open_interest", "max"))
        g["bucket"] = g["t"].dt.floor("15min")
        print("  after dedup-agg:", len(g))

        # --- per-minute collapse across strikes (small) ---
        per_min_vol = g.groupby(["t", "option_type"])["volume"].sum().unstack(fill_value=0)
        # NOTE: this unstack is on a MUCH smaller frame (per-minute, 2 cols) -- safe size.
        per_min_vol.columns = [f"{c.lower()}_vol" for c in per_min_vol.columns]
        per_min_oi = g.groupby(["t", "option_type"])["open_interest"].sum().unstack(fill_value=0)
        per_min_oi.columns = [f"{c.lower()}_oi" for c in per_min_oi.columns]
        per_min = per_min_vol.join(per_min_oi, how="outer").sort_index()
        print("  per_min shape", per_min.shape, per_min.columns.tolist())

        per_min["bucket"] = per_min.index.floor("15min")
        bucket_vol = per_min.groupby("bucket")[["ce_vol", "pe_vol"]].sum()
        bucket_oi = per_min.groupby("bucket")[["ce_oi", "pe_oi"]].last()
        bucket = bucket_vol.join(bucket_oi)
        bucket["spot_ref"] = bucket.index.map(spot_min.reindex(bucket.index, method=None))
        print("  bucket shape", bucket.shape)
        print(bucket.head(5))
        print(bucket[["ce_vol", "pe_vol", "ce_oi", "pe_oi"]].describe())

        # concentration: bucket x strike x type volume (small: buckets x strikes x 2)
        bs = g.groupby(["bucket", "strike", "option_type"], as_index=False)["volume"].sum()
        print("  bucket-strike rows", len(bs))
        bs["spot_ref"] = bs["bucket"].map(spot_min.reindex(bs["bucket"].unique(), method=None))
        ce_otm = bs[(bs["option_type"] == "CE") & (bs["strike"] > bs["spot_ref"])]
        agg = ce_otm.groupby("bucket")["volume"].agg(["max", "sum"])
        conc_ce = (agg["max"] / agg["sum"].replace(0, np.nan))
        print("  conc_ce describe:\n", conc_ce.describe())

        del df, g, per_min, bs
        chain.load_expiry.cache_clear()
        import gc
        gc.collect()


if __name__ == "__main__":
    sys.exit(main())
