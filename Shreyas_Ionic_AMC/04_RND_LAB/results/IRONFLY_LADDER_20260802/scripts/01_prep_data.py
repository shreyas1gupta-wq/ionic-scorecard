"""IRONFLY_LADDER_20260802 -- step 1: extend the existing OPTBUY_CONVEXITY_20260731 cache.
Reuses nifty_optidx_all_traded.parquet (ALL expiries, CONTRACTS>0 gated) and spot_vix_daily.parquet
(spot, vix, rv20_ann, trailing percentiles) verbatim -- consolidate-reused-code convention, avoids
re-parsing the 16-yr bhavcopy archive. Adds only what's new: RV50 (50-trading-day realized vol).
"""
import time
import numpy as np
import pandas as pd

SRC = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
       r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache")
OUT = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
       r"\Shreyas_Ionic_AMC\04_RND_LAB\results\IRONFLY_LADDER_20260802\cache")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    log("loading spot_vix_daily.parquet (reused from OPTBUY_CONVEXITY_20260731)...")
    sv = pd.read_parquet(f"{SRC}\\spot_vix_daily.parquet")
    log(f"  {len(sv):,} rows, {sv['date'].min().date()}..{sv['date'].max().date()}")

    # RV50: 50-trading-day rolling std of log returns, annualized -- same formula as the
    # existing rv20_ann, just a 50d window. Uses .rolling() so it is trailing-only by
    # construction (row i only sees rows i-49..i), no lookahead.
    sv["rv50_ann"] = sv["logret"].rolling(50).std() * (252 ** 0.5) * 100

    n_valid = sv["rv50_ann"].notna().sum()
    log(f"RV50 computed: {n_valid:,}/{len(sv):,} rows valid (first 49 rows are NaN by construction)")

    sv.to_parquet(f"{OUT}\\spot_vix_ext.parquet", index=False)
    log(f"-> cache/spot_vix_ext.parquet ({len(sv):,} rows)")

    # Sanity echo: compare rv20 vs rv50 typical levels (should be same order of magnitude)
    log(f"rv20_ann mean={sv['rv20_ann'].mean():.2f} rv50_ann mean={sv['rv50_ann'].mean():.2f} "
        f"(sanity: same order of magnitude expected)")
    log("DONE")


if __name__ == "__main__":
    main()
