"""DEV COPY of 155_indicator_mine_signals.py for debugging before re-queueing.
See queue version (once restored) for the authoritative header/docstring."""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
EMA_DIR = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/EMA_INTRADAY_BUYING_20260729"
SB_DIR = EMA_DIR / "signal_budget"
sys.path.insert(0, str(EMA_DIR))
sys.path.insert(0, str(SB_DIR))
from stage1_signal_test import load_spot, resample, nw_tstat  # noqa: E402
from measure_signal_budget import forward_stats, summarize_cell, clip_entry_window  # noqa: E402

OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/INDICATOR_MINE_20260730"
FEAT_PATH = OUT / "chain_features_15min.parquet"
VIX_PATH = ROOT / "intraday_options_strategy/datasets/processed/vix_1min.parquet"

BUILD_END = dt.date(2025, 12, 31)


def zscore_intraday(s: pd.Series, dates: pd.Series, window: int) -> pd.Series:
    """z of the CURRENT bar vs the PRIOR `window` bars (current excluded from its own
    baseline). BUG FOUND 2026-07-30: an inclusive rolling window is self-referential and
    mathematically caps |z| at sqrt(n-1) (=1.5 for n=4 with ddof=1) -- it can NEVER reach a
    z>=2 threshold. Fixed by shifting before rolling."""
    df = pd.DataFrame({"v": s.values, "d": dates.values}, index=s.index)
    shifted = df.groupby("d")["v"].shift(1)
    roll_mean = shifted.groupby(df["d"]).transform(lambda x: x.rolling(window, min_periods=window).mean())
    roll_std = shifted.groupby(df["d"]).transform(lambda x: x.rolling(window, min_periods=window).std())
    return (df["v"] - roll_mean) / roll_std


def load_feat() -> pd.DataFrame:
    f = pd.read_parquet(FEAT_PATH)
    f["bucket"] = pd.to_datetime(f["bucket"])
    f = f.drop_duplicates("bucket").sort_values("bucket").reset_index(drop=True)
    f["date"] = f["bucket"].dt.date
    f["t_signal"] = f["bucket"] + pd.Timedelta(minutes=15)
    return f


if __name__ == "__main__":
    feat = load_feat()
    feat["imb"] = (feat["ce_vol"] - feat["pe_vol"]) / (feat["ce_vol"] + feat["pe_vol"]).replace(0, np.nan)
    print("imb describe:\n", feat["imb"].describe())
    print("imb isna:", feat["imb"].isna().sum(), "of", len(feat))
    z = zscore_intraday(feat["imb"], feat["date"], window=4)
    print("z describe:\n", z.describe())
    print("z isna:", z.isna().sum())
    print("n z>=2:", (z >= 2).sum(), " n z<=-2:", (z <= -2).sum())
    # debug one day manually
    d0 = feat["date"].iloc[100]
    sub = feat[feat["date"] == d0][["bucket", "ce_vol", "pe_vol", "imb"]].copy()
    sub["roll_mean"] = sub["imb"].rolling(4, min_periods=4).mean()
    sub["roll_std"] = sub["imb"].rolling(4, min_periods=4).std()
    sub["z"] = (sub["imb"] - sub["roll_mean"]) / sub["roll_std"]
    print(sub)
