"""Reshape surface_panel_raw.parquet (rows = day x expiry) into a daily FRONT/NEXT term-structure
table, merge with spot_daily.parquet forward-return/vol targets, and compute the matched-horizon
forward realized vol (for VRP) via O(1) prefix-sum range queries. No chain access here -> safe to
re-run anytime while extraction is still in progress (it will just cover fewer days).

Output: daily_surface.parquet
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
RAW = HERE / "surface_panel_raw.parquet"
SPOT = HERE / "spot_daily.parquet"
OUT = HERE / "daily_surface.parquet"

OCT2024 = pd.Timestamp("2024-10-01")
HELDOUT = pd.Timestamp("2026-01-01")


def era(day: pd.Timestamp) -> str:
    if day >= HELDOUT:
        return "HELDOUT_2026"
    if day >= OCT2024:
        return "POST_OCT2024"
    return "PRE_OCT2024"


def main():
    raw = pd.read_parquet(RAW)
    raw["day"] = pd.to_datetime(raw["day"])
    raw["next_day"] = pd.to_datetime(raw["next_day"]) if "next_day" in raw.columns else pd.NaT
    raw["expiry_dt"] = pd.to_datetime(raw["expiry"])
    raw = raw.sort_values(["day", "dte"]).reset_index(drop=True)
    raw["rank"] = raw.groupby("day")["dte"].rank(method="first").astype(int)

    raw["skew25"] = raw["iv25p"] - raw["iv25c"]
    raw["bfly25"] = 0.5 * (raw["iv25c"] + raw["iv25p"]) - raw["atm_iv"]
    # 1-day-hold structure P&L legs (short = entry premium received - exit premium paid), using the
    # REAL listed strike nearest the 25-delta point (k25c_real/k25p_real), not the interpolated one.
    raw["pnl_sell_call25"] = raw["px25c_real_entry"] - raw["px25c_real_exit"]
    raw["pnl_sell_put25"] = raw["px25p_real_entry"] - raw["px25p_real_exit"]
    raw["pnl_sell_atm_straddle"] = ((raw["ce_atm_px_entry"] - raw["ce_atm_px_exit"]) +
                                     (raw["pe_atm_px_entry"] - raw["pe_atm_px_exit"]))

    front = raw[raw["rank"] == 1].set_index("day")
    nxt = raw[raw["rank"] == 2].set_index("day")

    keep = ["expiry_dt", "dte", "T", "spot", "atm_iv", "skew25", "bfly25", "k25c", "k25p",
            "k25c_real", "k25p_real", "px25c_real_entry", "px25c_real_exit",
            "px25p_real_entry", "px25p_real_exit", "pnl_sell_call25", "pnl_sell_put25",
            "ce_atm_px_entry", "ce_atm_px_exit", "pe_atm_px_entry", "pe_atm_px_exit",
            "pnl_sell_atm_straddle", "next_day"]
    f = front[keep].add_prefix("f_")
    n = nxt[keep].add_prefix("n_")
    d = f.join(n, how="left")
    d.index.name = "day"
    d = d.reset_index()
    d["term_slope"] = d["n_atm_iv"] - d["f_atm_iv"]
    d["term_inverted"] = d["term_slope"] < 0

    # Calendar structure (same ATM strike, both computed off the same day's spot so they match):
    # SHORT front CE + LONG next CE, 1-day hold, close-to-close. Isolates the term-structure play.
    d["calendar_pnl_ce"] = ((d["f_ce_atm_px_entry"] - d["f_ce_atm_px_exit"]) +
                             (d["n_ce_atm_px_exit"] - d["n_ce_atm_px_entry"]))

    spot = pd.read_parquet(SPOT)
    spot["day"] = pd.to_datetime(spot["day"])
    spot = spot.set_index("day").sort_index()

    d = d.merge(spot.reset_index(), on="day", how="left")

    # trading-day integer position for O(1) forward-RV range queries
    pos = pd.Series(np.arange(len(spot)), index=spot.index)

    def fwd_rv_ann(day, dte_col, cum_col, n_per_year=252):
        """Forward realized vol from `day` (exclusive) to day+dte_col calendar days (inclusive),
        via nearest available trading-day position (expiry may be a non-trading holiday edge)."""
        if day not in pos.index:
            return np.nan
        i0 = pos.loc[day]
        target_date = day + pd.Timedelta(days=int(dte_col))
        later = pos.index[pos.index >= target_date]
        if len(later) == 0:
            return np.nan
        i1 = pos.loc[later[0]]
        if i1 <= i0:
            return np.nan
        cum = spot[cum_col]
        var_sum = cum.iloc[i1] - cum.iloc[i0]
        h = i1 - i0
        return float(np.sqrt(var_sum * n_per_year / h))

    f_dte = d["f_dte"].fillna(-1).astype(int)
    n_dte = d["n_dte"].fillna(-1).astype(int)
    d["f_fwd_rv5"] = [fwd_rv_ann(day, dte, "rv5_cum") if dte > 0 else np.nan
                       for day, dte in zip(d["day"], f_dte)]
    d["f_fwd_rv15"] = [fwd_rv_ann(day, dte, "rv15_cum") if dte > 0 else np.nan
                        for day, dte in zip(d["day"], f_dte)]
    d["n_fwd_rv5"] = [fwd_rv_ann(day, dte, "rv5_cum") if dte > 0 else np.nan
                       for day, dte in zip(d["day"], n_dte)]
    d["n_fwd_rv15"] = [fwd_rv_ann(day, dte, "rv15_cum") if dte > 0 else np.nan
                        for day, dte in zip(d["day"], n_dte)]

    # FIXED-horizon forward realized vol (decoupled from option dte) for the skew/term/IV-RV ->
    # forward-vol prediction cells (standard 5d/10d horizons, comparable across the whole panel)
    def fwd_rv_fixed(day, ndays, cum_col, n_per_year=252):
        if day not in pos.index:
            return np.nan
        i0 = pos.loc[day]
        i1 = i0 + ndays
        if i1 >= len(spot):
            return np.nan
        cum = spot[cum_col]
        var_sum = cum.iloc[i1] - cum.iloc[i0]
        return float(np.sqrt(var_sum * n_per_year / ndays))

    for h in (5, 10):
        d[f"fwd_rv5_fix_{h}"] = [fwd_rv_fixed(day, h, "rv5_cum") for day in d["day"]]
        d[f"fwd_rv15_fix_{h}"] = [fwd_rv_fixed(day, h, "rv15_cum") for day in d["day"]]

    # VRP in vol points (annualized IV minus matched-horizon forward realized vol)
    d["vrp_f_5"] = d["f_atm_iv"] - d["f_fwd_rv5"]
    d["vrp_f_15"] = d["f_atm_iv"] - d["f_fwd_rv15"]
    d["vrp_n_5"] = d["n_atm_iv"] - d["n_fwd_rv5"]
    d["vrp_n_15"] = d["n_atm_iv"] - d["n_fwd_rv15"]

    # PIT expanding percentile helper (never full-sample)
    def expanding_pctrank(s: pd.Series) -> pd.Series:
        s = s.copy()
        out = np.full(len(s), np.nan)
        vals = s.to_numpy()
        for i in range(len(vals)):
            if i < 20 or np.isnan(vals[i]):
                continue
            hist = vals[:i]
            hist = hist[~np.isnan(hist)]
            if len(hist) < 20:
                continue
            out[i] = (hist < vals[i]).mean()
        return pd.Series(out, index=s.index)

    d["skew25_chg1"] = d["f_skew25"].diff()
    d["iv_rv5_10"] = d["f_atm_iv"] - d["trail_rv5_ann_10"]
    d["iv_rv15_10"] = d["f_atm_iv"] - d["trail_rv15_ann_10"]
    d["iv_rv5_20"] = d["f_atm_iv"] - d["trail_rv5_ann_20"]
    d["iv_rv15_20"] = d["f_atm_iv"] - d["trail_rv15_ann_20"]
    for c in ["f_skew25", "skew25_chg1", "term_slope", "iv_rv5_10", "iv_rv15_10",
              "iv_rv5_20", "iv_rv15_20"]:
        d[f"{c}_pct"] = expanding_pctrank(d[c])

    d["era"] = d["day"].apply(era)
    d.to_parquet(OUT)
    print(f"wrote {OUT} shape={d.shape}")
    print(d["era"].value_counts())
    print(d[["day", "f_dte", "n_dte", "f_atm_iv", "n_atm_iv", "f_skew25", "term_slope"]].tail(8))


if __name__ == "__main__":
    main()
