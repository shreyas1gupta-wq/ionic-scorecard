"""Build a small, clean NIFTY OPTIDX daily dataset (2016-2026) from the 16-yr bhavcopy archive.
RAM-frugal: one year file at a time, filtered immediately, del+gc.collect() between years.
Also merges in spot (nifty50.parquet) and India VIX (india_vix.parquet).
Writes: cache/nifty_optidx_daily.parquet, cache/spot_vix_daily.parquet
"""
import gc
import sys
import time

import pandas as pd
import pyarrow.parquet as pq

BHAV_DIR = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
            r"\NIFTY 500\Shreyas_Ionic_AMC\05_DATA_OFFICE\data\fo_bhavcopy_hist")
IDX_DIR = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
           r"\NIFTY 500\datasets\index_daily")
OUT_DIR = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
           r"\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache")

YEARS = range(2016, 2027)
COLS = ["INSTRUMENT", "SYMBOL", "EXPIRY_DT", "STRIKE_PR", "OPTION_TYP",
        "CLOSE", "SETTLE_PR", "CONTRACTS", "OPEN_INT", "TIMESTAMP"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def build_optidx():
    frames = []
    for yr in YEARS:
        path = f"{BHAV_DIR}\\fo_idx_{yr}.parquet"
        try:
            t = pq.read_table(path, columns=COLS)
        except FileNotFoundError:
            log(f"{yr}: file not found, skipping")
            continue
        df = t.to_pandas()
        del t
        sub = df[(df["SYMBOL"] == "NIFTY") & (df["INSTRUMENT"] == "OPTIDX")].copy()
        del df
        gc.collect()
        sub = sub.drop(columns=["INSTRUMENT", "SYMBOL"])
        sub["EXPIRY_DT"] = pd.to_datetime(sub["EXPIRY_DT"], format="mixed", dayfirst=True)
        sub["TIMESTAMP"] = pd.to_datetime(sub["TIMESTAMP"], format="mixed", dayfirst=True)
        frames.append(sub)
        log(f"{yr}: {len(sub):,} NIFTY OPTIDX rows "
            f"(contracts>0: {(sub['CONTRACTS'] > 0).sum():,})")
        del sub
        gc.collect()
    out = pd.concat(frames, ignore_index=True)
    del frames
    gc.collect()
    out = out.sort_values(["TIMESTAMP", "EXPIRY_DT", "STRIKE_PR", "OPTION_TYP"]).reset_index(drop=True)
    out.to_parquet(f"{OUT_DIR}\\nifty_optidx_daily.parquet", index=False)
    log(f"TOTAL {len(out):,} rows -> cache/nifty_optidx_daily.parquet "
        f"({out['TIMESTAMP'].min().date()} .. {out['TIMESTAMP'].max().date()})")
    return out


def build_spot_vix():
    spot = pd.read_parquet(f"{IDX_DIR}\\nifty50.parquet")
    vix = pd.read_parquet(f"{IDX_DIR}\\india_vix.parquet")
    for d in (spot, vix):
        d["date"] = pd.to_datetime(d["timestamp"]).dt.tz_localize(None).dt.normalize()
    spot = spot[["date", "close"]].rename(columns={"close": "spot_close"})
    vix = vix[["date", "close"]].rename(columns={"close": "vix_close"})
    m = spot.merge(vix, on="date", how="inner").sort_values("date").reset_index(drop=True)
    # realized vol: 20d rolling std of log returns, annualized
    import numpy as np
    m["logret"] = np.log(m["spot_close"] / m["spot_close"].shift(1))
    m["rv20_ann"] = m["logret"].rolling(20).std() * (252 ** 0.5) * 100
    # trailing (expanding, min 252d, cap 504d window) percentiles -- NO full-sample lookahead
    def trailing_pct(series, min_win=252, max_win=504):
        vals = series.to_numpy(float)
        out = [float("nan")] * len(vals)
        for i in range(len(vals)):
            lo = max(0, i - max_win + 1)
            hist = vals[lo:i]  # strictly PRIOR values, excludes today
            hist = hist[~pd.isna(hist)]
            if len(hist) < min_win or pd.isna(vals[i]):
                continue
            out[i] = float((hist < vals[i]).mean())
        return out
    log("computing trailing VIX percentile (this loops, ~2600 rows, seconds)...")
    m["vix_pct_trail"] = trailing_pct(m["vix_close"])
    log("computing trailing RV20 percentile...")
    m["rv20_pct_trail"] = trailing_pct(m["rv20_ann"])
    m.to_parquet(f"{OUT_DIR}\\spot_vix_daily.parquet", index=False)
    log(f"spot/vix merged {len(m):,} rows -> cache/spot_vix_daily.parquet "
        f"({m['date'].min().date()} .. {m['date'].max().date()})")
    return m


if __name__ == "__main__":
    build_optidx()
    gc.collect()
    build_spot_vix()
    log("DONE")
