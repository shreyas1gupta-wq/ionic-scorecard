"""
Post-hoc decomposition of H1's wti_ret1d/eod cell (see h1_wti_diagnostic.py): the symmetric
top-bottom pair turned out to be driven ENTIRELY by the bottom quintile (short NIFTY following
the biggest overnight WTI crude crashes). This is NOT pre-registered as a separate test -- it was
discovered after seeing h1's results -- so it is reported as exploratory/post-hoc and re-tested
on its OWN placebo + the untouched 2026 held-out sample, per D-035 discipline.
"""
import numpy as np
import pandas as pd
from scipy import stats

ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
OUT = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\ORTHOGONAL_ALPHA_20260730"

nifty = pd.read_parquet(ROOT + r"\intraday_options_strategy\datasets\raw\hf_index_options_1m\index\NIFTY.parquet")
nifty = nifty[nifty["timestamp"].dt.time >= pd.Timestamp("09:15").time()].copy()
nifty["date"] = pd.to_datetime(nifty["trading_day"])
rows = []
for d, g in nifty.groupby("date", sort=True):
    g = g.sort_values("timestamp")
    rows.append((d, g.iloc[0]["open"], g.iloc[-1]["close"]))
daily = pd.DataFrame(rows, columns=["date", "open", "close"]).sort_values("date").reset_index(drop=True)
daily["ret_eod"] = daily["close"] - daily["open"]

wti = pd.read_parquet(ROOT + r"\Shreyas_Ionic_AMC\05_DATA_OFFICE\data\wti_crude_fred_daily.parquet")
wti["date"] = pd.to_datetime(wti["date"]); wti = wti.sort_values("date")
wti["wti_ret1d"] = wti["wti"].pct_change() * 100
merged = pd.merge_asof(daily.sort_values("date"), wti[["date", "wti_ret1d"]].dropna(),
                        direction="backward", allow_exact_matches=False).dropna(subset=["wti_ret1d"])

SPLIT = pd.Timestamp("2024-10-01")
HOLDOUT = pd.Timestamp("2026-01-01")
build = merged[merged["date"] < HOLDOUT].copy()
oos = merged[merged["date"] >= HOLDOUT].copy()
build["cost"] = build["date"].apply(lambda d: (4.47 if d < SPLIT else 5.97) + 0.5)
oos["cost"] = 5.97 + 0.5

for pctile, tag in [(0.20, "quintile"), (0.3333, "tercile")]:
    q = build["wti_ret1d"].quantile(pctile)
    sub = build[build["wti_ret1d"] <= q].copy()
    sub["net_pts"] = -sub["ret_eod"] - sub["cost"]
    sub["cum"] = sub["net_pts"].cumsum()
    dd = (sub["cum"] - sub["cum"].cummax()).min()
    pos = sub[sub["net_pts"] > 0]["net_pts"]
    conc = pos.max() / pos.sum() if len(pos) else np.nan
    n_months = (build["date"].max() - build["date"].min()).days / 30.44
    t, p = stats.ttest_1samp(sub["net_pts"], 0)

    # placebo: day-block permutation, same threshold, re-pair signal<->target
    np.random.seed(20260730)
    sig = build["wti_ret1d"].values
    ret = build["ret_eod"].values
    cost = build["cost"].values
    null_means = np.empty(500)
    for i in range(500):
        perm = np.random.permutation(len(build))
        s = sig[perm]
        mask = s <= q
        if mask.sum() < 5:
            null_means[i] = np.nan
            continue
        null_means[i] = (-ret[mask] - cost[mask]).mean()
    null_means = null_means[~np.isnan(null_means)]
    placebo_p = (np.abs(null_means) >= np.abs(sub["net_pts"].mean())).mean()

    # OOS 2026, SAME threshold (fixed from build, not re-fit)
    oos_sub = oos[oos["wti_ret1d"] <= q].copy()
    oos_sub["net_pts"] = -oos_sub["ret_eod"] - oos_sub["cost"]
    t_oos, _ = stats.ttest_1samp(oos_sub["net_pts"], 0) if len(oos_sub) > 3 else (np.nan, np.nan)

    print(f"--- {tag} (q={pctile}) SHORT-ONLY leg ---")
    print(f"  build n={len(sub)}, trades/month={len(sub)/n_months:.1f}, mean_net={sub['net_pts'].mean():.2f} pts, "
          f"t={t:.2f}, win%={(sub['net_pts']>0).mean()*100:.1f}, placebo_p={placebo_p:.3f}")
    print(f"  maxDD_pts={dd:.1f}, largest_trade_share_of_profit={conc:.3f}")
    print(f"  2026 HELD OUT: n={len(oos_sub)}, mean_net={oos_sub['net_pts'].mean() if len(oos_sub) else np.nan:.2f}, "
          f"t={t_oos:.2f}, win%={(oos_sub['net_pts']>0).mean()*100 if len(oos_sub) else np.nan:.1f}")
    sub.to_csv(OUT + rf"\h1_wti_shortonly_{tag}_build_trades.csv", index=False)
