"""Select the FRONT-WEEK expiry's row per 15-min bucket from the already-built
INDICATOR_MINE_20260730/chain_features_15min.parquet (columns: bucket, ce_vol, pe_vol, ce_oi,
pe_oi, spot_ref, conc_ce, conc_pe, expiry). REUSE, NOT rebuild -- avoids re-touching the raw
1-min option chain entirely (RAM-safe by construction: this file is already a 76k-row aggregate).

That source file has ONE ROW PER (bucket, expiry) -- every expiry alive on that date contributes
its own row (a weekly near, weekly next, and often a monthly are all simultaneously alive).
The consumer that first used it (155_indicator_mine_signals.py) did a bare
`drop_duplicates("bucket")`, which keeps whatever row happens to be FIRST in file order -- NOT
guaranteed to be the front (nearest, min-DTE) expiry. Verified on a 3-row sample for
2021-05-24 09:15 that file order is NOT expiry-ascending. FIX HERE: explicitly parse `expiry`,
compute DTE = expiry_date - bucket_date, keep only DTE>=0 (tradeable, not yet expired), and take
the MINIMUM-DTE row per bucket (deterministic, no reliance on file order).
"""
import pandas as pd
import numpy as np

SRC = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\INDICATOR_MINE_20260730\chain_features_15min.parquet"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NEWDIM_LEVELS_20260731"


def main():
    f = pd.read_parquet(SRC)
    f["bucket"] = pd.to_datetime(f["bucket"])
    f["expiry_dt"] = pd.to_datetime(f["expiry"])
    f["bucket_date"] = f["bucket"].dt.normalize()
    f["dte"] = (f["expiry_dt"] - f["bucket_date"]).dt.days
    before = len(f)
    f = f[f["dte"] >= 0].copy()
    print(f"dropped {before - len(f)} rows with dte<0 (stale/expired rows in source)")

    f = f.sort_values(["bucket", "dte"])
    front = f.drop_duplicates("bucket", keep="first").sort_values("bucket").reset_index(drop=True)
    front["total_vol"] = front["ce_vol"] + front["pe_vol"]
    front["date"] = front["bucket"].dt.normalize()

    # sanity: compare against the naive (buggy) drop_duplicates the earlier consumer used
    naive = f.sort_values("bucket").drop_duplicates("bucket", keep="first")
    mismatch = (naive.set_index("bucket")["dte"] != front.set_index("bucket")["dte"]).mean()
    print(f"fraction of buckets where naive-first-row picked a DIFFERENT (non-front) expiry than "
          f"the min-DTE selection here: {mismatch:.3f}")

    keep = ["bucket", "date", "dte", "expiry", "total_vol", "ce_vol", "pe_vol", "spot_ref",
            "conc_ce", "conc_pe", "ce_oi", "pe_oi"]
    front = front[keep]
    front.to_parquet(f"{OUT}/chain_front_15min.parquet")
    print("front shape", front.shape, front["bucket"].min(), front["bucket"].max())
    print("spot_ref nonnull frac", front["spot_ref"].notna().mean())
    print("total_vol==0 frac", (front["total_vol"] == 0).mean())
    print("dte distribution:\n", front["dte"].describe())


if __name__ == "__main__":
    main()
