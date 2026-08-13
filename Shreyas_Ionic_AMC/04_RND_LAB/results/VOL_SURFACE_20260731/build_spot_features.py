"""Build daily spot-return + multi-sampling realized-vol features from the clean 1-min NIFTY index
series (no option chain needed here -> no chainlock required, safe to run anytime).

Outputs (this dir):
  spot_daily.parquet   : one row per trading day
      close                  : EOD close (last bar, no pre-open auction rows in this file)
      ret1                   : close-to-close daily log return (t-1 -> t)
      fwd_ret_{1,3,5,10,20}  : forward close-to-close log return, day t -> t+h (uses FUTURE data,
                                only ever used as a dependent variable, never a predictor)
      rv5_var, rv15_var      : INTRADAY (open->close same day) realized variance that day, from
                                5-min and 15-min sampled log returns (overnight gap excluded, stated)
      rv5_cum, rv15_cum      : cumulative sum of rv{5,15}_var in trading-day order, for O(1) range
                                queries: sum over (day_a, day_b] = cum[day_b] - cum[day_a]
      trail_rv5_ann_10/20    : trailing annualized RV (10/20 trading days), 5-min sampling
      trail_rv15_ann_10/20   : trailing annualized RV (10/20 trading days), 15-min sampling
  Landmine guards: file's own coverage already starts at 09:15 (verified: min/max time 09:15/15:29,
  no pre-open auction rows) — see intraday_options_strategy/datasets/processed/nifty_1min.parquet.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
SRC = BASE + r"\intraday_options_strategy\datasets\processed\nifty_1min.parquet"
OUT = Path(__file__).parent / "spot_daily.parquet"


def intraday_rv(px: pd.Series, freq: str) -> pd.Series:
    """Per-day realized variance (sum of squared log returns) at `freq` sampling, intraday only."""
    r = px.resample(freq, label="right", closed="right").last().dropna()
    day_of_bar = r.index.normalize()
    prev_day = pd.Series(day_of_bar.values).shift(1).values
    same_day_mask = day_of_bar.values == prev_day  # drop the overnight-spanning first return/day
    lr = np.log(r).diff()
    lr = lr[same_day_mask]
    var_by_day = (lr ** 2).groupby(lr.index.normalize()).sum()
    return var_by_day


def main():
    df = pd.read_parquet(SRC)
    df = df.sort_index()
    close = df["close"]

    daily_close = close.groupby(close.index.normalize()).last()
    daily_close.index.name = "day"

    rv5 = intraday_rv(close, "5min")
    rv15 = intraday_rv(close, "15min")

    out = pd.DataFrame({"close": daily_close})
    out["rv5_var"] = rv5
    out["rv15_var"] = rv15
    out = out.sort_index()

    out["ret1"] = np.log(out["close"]).diff()
    for h in (1, 3, 5, 10, 20):
        out[f"fwd_ret_{h}"] = np.log(out["close"].shift(-h)) - np.log(out["close"])

    out["rv5_cum"] = out["rv5_var"].fillna(0).cumsum()
    out["rv15_cum"] = out["rv15_var"].fillna(0).cumsum()

    n_per_year = 252
    for w in (10, 20):
        out[f"trail_rv5_ann_{w}"] = np.sqrt(out["rv5_var"].rolling(w).sum() * n_per_year / w)
        out[f"trail_rv15_ann_{w}"] = np.sqrt(out["rv15_var"].rolling(w).sum() * n_per_year / w)

    out = out.reset_index()
    out.to_parquet(OUT)
    print(f"wrote {OUT}  shape={out.shape}  range={out['day'].min()}..{out['day'].max()}")
    print(out.tail(5))


if __name__ == "__main__":
    main()
