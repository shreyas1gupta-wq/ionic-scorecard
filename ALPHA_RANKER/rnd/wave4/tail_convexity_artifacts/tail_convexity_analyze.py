"""
Tail-convexity payoff-shape analysis (not rank-IC). For each signal: form monthly
top-quintile-minus-bottom-quintile (LS) portfolio on fwd_ret_1M_raw, then measure
hit rate, win/loss asymmetry, skew, and CONDITIONAL return in (a) worst-decile
market months and (b) named crash episodes (2008 GFC, 2020 COVID, 2022 selloff).
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

OUT = Path(r"C:\Users\SHREYA~1.1GU\AppData\Local\Temp\claude\c--Users-Shreyas-1Gupta-OneDrive---Angel-Broking-Limited-Desktop-Backup-NIFTY-500\f6b730da-632d-4ec3-b4d1-d89aa1c2dbff\scratchpad")
RND = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER\rnd")

merged = pd.read_parquet(OUT / "tail_merged.parquet")
merged["date"] = pd.to_datetime(merged["date"])

SIGNALS = [
    "value_EY", "value_dcf_revgap", "value_marketstate_M3", "value_smallcap_M2",
    "mom_resid_peer", "trend_ma65_slope",
    "quality_QMJ", "quality_cfo_pat",
    "bs_issuance", "bs_asset_growth",
    "defensive_BAB", "seasonality",
    "W4_clean_surplus_health", "W4_dep_health", "W4_beta_adj_mom", "W4_amihud_illiq",
]
CANONICAL7 = {"value_EY", "mom_resid_peer", "trend_ma65_slope", "quality_QMJ",
              "bs_issuance", "bs_asset_growth", "quality_cfo_pat"}

# --- market monthly fwd return series (same window convention as fwd_ret_1M_raw) ---
bench = pd.read_parquet(RND / "panel" / "cube_bench_long.parquet")["NIFTY500"]
bench.index = pd.to_datetime(bench.index)
panel_dates = sorted(merged["date"].unique())
mkt_fwd = {}
for i, d in enumerate(panel_dates[:-1]):
    d_next = panel_dates[i + 1]
    if d in bench.index and d_next in bench.index:
        mkt_fwd[d] = bench.loc[d_next] / bench.loc[d] - 1.0
mkt_fwd = pd.Series(mkt_fwd).sort_index()
mkt_fwd.to_csv(OUT / "mkt_fwd_1m.csv")

worst_decile_cut = mkt_fwd.quantile(0.10)
worst_decile_dates = set(mkt_fwd[mkt_fwd <= worst_decile_cut].index)
print(f"market fwd-1M worst-decile cutoff: {worst_decile_cut:.4f}, n={len(worst_decile_dates)} months")
print("worst months:", sorted(worst_decile_dates)[:20])

# named crash episodes (by the panel date that STARTS the crash fwd-return window)
EPISODES = {
    "GFC_2008-09": [d for d in panel_dates if pd.Timestamp("2008-08-01") <= d <= pd.Timestamp("2009-03-01")],
    "COVID_2020-02_03": [d for d in panel_dates if pd.Timestamp("2020-01-15") <= d <= pd.Timestamp("2020-03-31")],
    "SELLOFF_2022": [d for d in panel_dates if pd.Timestamp("2021-12-15") <= d <= pd.Timestamp("2022-06-30")],
}
for name, dates in EPISODES.items():
    print(name, len(dates), dates[:3], "...", dates[-3:] if dates else [])


def ls_series(sig_col, ret_col="fwd_ret_1M_raw", q=5):
    sub = merged[["date", "symbol", sig_col, ret_col]].dropna()
    if len(sub) == 0:
        return pd.Series(dtype=float), 0
    out = {}
    n_dropped_dates = 0
    for d, g in sub.groupby("date"):
        if len(g) < 15:  # need enough names for stable quintiles
            n_dropped_dates += 1
            continue
        try:
            g = g.copy()
            g["q"] = pd.qcut(g[sig_col], q, labels=False, duplicates="drop")
        except ValueError:
            n_dropped_dates += 1
            continue
        qmax = g["q"].max()
        top = g.loc[g["q"] == qmax, ret_col].mean()
        bot = g.loc[g["q"] == 0, ret_col].mean()
        out[d] = top - bot
    return pd.Series(out).sort_index(), n_dropped_dates


results = {}
for sig in SIGNALS:
    ls, n_dropped = ls_series(sig)
    if len(ls) < 12:
        results[sig] = {"error": f"insufficient dates (n={len(ls)})"}
        continue
    wins = ls[ls > 0]
    losses = ls[ls < 0]
    hit_rate = len(wins) / len(ls)
    avg_win = wins.mean() if len(wins) else np.nan
    avg_loss = losses.mean() if len(losses) else np.nan  # negative number
    win_loss_ratio = (avg_win / abs(avg_loss)) if (len(wins) and len(losses) and avg_loss != 0) else np.nan
    skew = stats.skew(ls.values)
    mean_all = ls.mean()

    tail_dates = [d for d in ls.index if d in worst_decile_dates]
    tail_mean = ls.loc[tail_dates].mean() if tail_dates else np.nan
    n_tail = len(tail_dates)

    ep_stats = {}
    for name, dates in EPISODES.items():
        dd = [d for d in dates if d in ls.index]
        ep_stats[name] = {
            "n_months": len(dd),
            "mean_LS": float(ls.loc[dd].mean()) if dd else None,
            "worst_LS": float(ls.loc[dd].min()) if dd else None,
            "months": [(str(d.date()), float(ls.loc[d])) for d in dd],
        }

    results[sig] = {
        "n_dates": int(len(ls)),
        "n_dates_dropped_thin": int(n_dropped),
        "canonical7": sig in CANONICAL7,
        "mean_LS_monthly": float(mean_all),
        "ann_LS_approx": float(mean_all * 12),
        "hit_rate": float(hit_rate),
        "avg_win": float(avg_win) if pd.notna(avg_win) else None,
        "avg_loss": float(avg_loss) if pd.notna(avg_loss) else None,
        "win_loss_ratio": float(win_loss_ratio) if pd.notna(win_loss_ratio) else None,
        "skew": float(skew),
        "worst_month_LS": float(ls.min()),
        "worst_month_date": str(ls.idxmin().date()),
        "best_month_LS": float(ls.max()),
        "n_worst_decile_mkt_months_available": n_tail,
        "mean_LS_in_worst_decile_mkt_months": float(tail_mean) if pd.notna(tail_mean) else None,
        "episodes": ep_stats,
    }
    print(f"{sig:28s} n={len(ls):3d} mean={mean_all*100:6.2f}% hit={hit_rate:.2f} "
          f"skew={skew:+.2f} tail_decile_mean={tail_mean*100 if pd.notna(tail_mean) else float('nan'):6.2f}% "
          f"worst={ls.min()*100:6.2f}%")

with open(OUT / "tail_convexity_results.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print("\nSaved ->", OUT / "tail_convexity_results.json")
