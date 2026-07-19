"""
Full-21yr-history turnover cross-check for H002_slope200_1M / H004_mom_sharpe12m_1M /
H043_beta_adj_mom -- companion to turnover_fill_audit.py.

WHY: builders_ma.py / builders_mom.py load `rnd/panel/cube_close.parquet`, which is
ONLY 2021-07-16 -> 2026-07-16 (751 symbols) -- NOT the full panel_long.parquet history
(2005-04 -> 2025-12, 976 symbols, in cube_close_long.parquet / cube_bench_long.parquet).
This means the H002/H004/H043 CARDS (and turnover_fill_audit.py, which faithfully
reproduces the cards' own construction) are silently confined to a ~42-48 month
recent-regime sample -- same root-cause class already caught for H046 (RECONCILED_RETURNS.md)
and H009 (SURVIVORS.md, "bull-only 2021-26 artifact").

This script recomputes the SAME three factor definitions directly from the FULL-history
cubes, to get an honest full-sample one-way monthly turnover for comparison.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

RND = Path(r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/ALPHA_RANKER/rnd")
sys.path.insert(0, str(RND / "lib"))
import harness  # noqa: E402

MIN_NAMES = 20


def get_decile_sets(factor_df: pd.DataFrame, min_names=MIN_NAMES) -> dict:
    out = {}
    for d, g in factor_df.groupby("date"):
        if len(g) < min_names:
            continue
        try:
            g = g.assign(decile=pd.qcut(g["factor"].rank(method="first"), 10, labels=False, duplicates="drop"))
        except ValueError:
            continue
        if g["decile"].nunique() < 3:
            continue
        top_d, bot_d = g["decile"].max(), g["decile"].min()
        out[pd.Timestamp(d)] = (set(g.loc[g["decile"] == top_d, "symbol"]),
                                 set(g.loc[g["decile"] == bot_d, "symbol"]))
    return out


def oneway_turnover_leg(sets_by_date: dict, leg_idx: int) -> float:
    dates = sorted(sets_by_date.keys())
    fracs = []
    for i in range(1, len(dates)):
        cur, prev = sets_by_date[dates[i]][leg_idx], sets_by_date[dates[i - 1]][leg_idx]
        if not cur:
            continue
        fracs.append(len(cur - prev) / len(cur))
    return float(np.mean(fracs)) if fracs else float("nan")


def main():
    panel = pd.read_parquet(RND / "panel" / "panel_long.parquet")
    panel["date"] = pd.to_datetime(panel["date"])
    close = pd.read_parquet(RND / "panel" / "cube_close_long.parquet")
    close.index = pd.to_datetime(close.index)
    close = close.sort_index()
    bench = pd.read_parquet(RND / "panel" / "cube_bench_long.parquet")
    bench.index = pd.to_datetime(bench.index)
    bench = bench.sort_index()
    bench_s = bench.iloc[:, 0] if bench.shape[1] == 1 else bench["NSEI"]

    rebal_dates = sorted(panel["date"].unique())

    # ---- H002_slope200_1M: MA200(t)/MA200(t-21) - 1 ----
    ma200 = close.rolling(200, min_periods=200).mean()
    slope200 = ma200 / ma200.shift(21) - 1.0
    slope200_sub = slope200.reindex(rebal_dates)
    f002 = slope200_sub.stack().rename("factor").reset_index()
    f002.columns = ["date", "symbol", "factor"]

    # ---- H004_mom_sharpe12m_1M: close(t)/close(t-252)-1 / vol_252 (panel col) ----
    vol_lookup = panel.set_index(["date", "symbol"])["vol_252"]
    rows = []
    dates_idx = close.index
    for d in rebal_dates:
        if d not in dates_idx:
            continue
        loc = dates_idx.get_loc(d)
        if loc < 252:
            continue
        p_t = close.iloc[loc]
        p_t0 = close.iloc[loc - 252]
        ret = (p_t / p_t0 - 1.0).dropna()
        for sym, val in ret.items():
            vol = vol_lookup.get((d, sym), np.nan)
            if pd.isna(vol) or vol <= 0:
                continue
            rows.append((d, sym, val / vol))
    f004 = pd.DataFrame(rows, columns=["date", "symbol", "factor"])

    # ---- H043_beta_adj_mom: mom_12_1 - beta_252(t)*mkt_mom_12_1 ----
    beta_lookup = panel.set_index(["date", "symbol"])["beta_252"]
    rows = []
    bench_idx = bench_s.index
    for d in rebal_dates:
        if d not in dates_idx or d not in bench_idx:
            continue
        loc = dates_idx.get_loc(d)
        loc_b = bench_idx.get_loc(d)
        if loc < 252 or loc_b < 252:
            continue
        p_t21 = close.iloc[loc - 21]
        p_t252 = close.iloc[loc - 252]
        mom = (p_t21 / p_t252 - 1.0).dropna()
        mkt_mom = bench_s.iloc[loc_b - 21] / bench_s.iloc[loc_b - 252] - 1.0
        for sym, val in mom.items():
            b = beta_lookup.get((d, sym), np.nan)
            if pd.isna(b):
                continue
            rows.append((d, sym, val - b * mkt_mom))
    f043 = pd.DataFrame(rows, columns=["date", "symbol", "factor"])

    for fid, fdf in (("H002_slope200_1M (FULL 21yr)", f002),
                      ("H004_mom_sharpe12m_1M (FULL 21yr)", f004),
                      ("H043_beta_adj_mom (FULL 21yr)", f043)):
        sets_by_date = get_decile_sets(fdf)
        dates = sorted(sets_by_date.keys())
        top_to = oneway_turnover_leg(sets_by_date, 0)
        bot_to = oneway_turnover_leg(sets_by_date, 1)
        book_to = float(np.nanmean([top_to, bot_to]))
        n_recent = sum(1 for d in dates if d >= pd.Timestamp("2021-07-16"))
        print(f"{fid}: n_dates={len(dates)} (range {dates[0].date() if dates else None} -> "
              f"{dates[-1].date() if dates else None}), n_dates_post_2021_07={n_recent}, "
              f"turnover_long={top_to:.4f}, turnover_short={bot_to:.4f}, book_turnover={book_to:.4f}, "
              f"implied_holding_months_long={1/top_to if top_to else float('nan'):.2f}, "
              f"implied_holding_months_short={1/bot_to if bot_to else float('nan'):.2f}")


if __name__ == "__main__":
    main()
