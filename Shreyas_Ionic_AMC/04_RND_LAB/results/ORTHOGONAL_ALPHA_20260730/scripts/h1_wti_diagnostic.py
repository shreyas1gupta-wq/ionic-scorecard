"""
Follow-up diagnostic on the ONLY H1 cell that cleared its own placebo (wti_ret1d, all 3 horizons).
Checks concentration + drawdown before any tier upgrade -- per the framework's hard-kill #3
(profit concentration >30% from a single trade) and general prudence (maxDD).
Reuses the exact same build/quintile/direction construction as h1_crossasset.py (not re-derived).
"""
import numpy as np
import pandas as pd

ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
OUT = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\ORTHOGONAL_ALPHA_20260730"

nifty = pd.read_parquet(ROOT + r"\intraday_options_strategy\datasets\raw\hf_index_options_1m\index\NIFTY.parquet")
nifty = nifty[nifty["timestamp"].dt.time >= pd.Timestamp("09:15").time()].copy()
nifty["date"] = pd.to_datetime(nifty["trading_day"])
nifty["t"] = nifty["timestamp"].dt.time
rows = []
for d, g in nifty.groupby("date", sort=True):
    g = g.sort_values("timestamp")
    rows.append((d, g.iloc[0]["open"], g.iloc[-1]["close"]))
daily = pd.DataFrame(rows, columns=["date", "open", "close"]).sort_values("date").reset_index(drop=True)
daily["prior_close"] = daily["close"].shift(1)
daily["ret_eod"] = daily["close"] - daily["open"]
daily = daily.dropna(subset=["prior_close"]).reset_index(drop=True)

wti = pd.read_parquet(ROOT + r"\Shreyas_Ionic_AMC\05_DATA_OFFICE\data\wti_crude_fred_daily.parquet")
wti["date"] = pd.to_datetime(wti["date"]); wti = wti.sort_values("date")
wti["wti_ret1d"] = wti["wti"].pct_change() * 100
merged = pd.merge_asof(daily.sort_values("date"), wti[["date", "wti_ret1d"]].dropna(),
                        direction="backward", allow_exact_matches=False).dropna(subset=["wti_ret1d"])

HOLDOUT = pd.Timestamp("2026-01-01")
SPLIT = pd.Timestamp("2024-10-01")
build = merged[merged["date"] < HOLDOUT].copy()
q20, q80 = build["wti_ret1d"].quantile(0.20), build["wti_ret1d"].quantile(0.80)
lo = build["wti_ret1d"] <= q20
hi = build["wti_ret1d"] >= q80
direction = 1.0 if (build.loc[hi, "ret_eod"].mean() - build.loc[lo, "ret_eod"].mean()) >= 0 else -1.0

tl = build.loc[lo, ["date", "ret_eod"]].copy(); tl["side"] = "lo"
th = build.loc[hi, ["date", "ret_eod"]].copy(); th["side"] = "hi"
trades = pd.concat([tl, th]).sort_values("date").reset_index(drop=True)
trades["signed_pts"] = np.where(trades["side"] == "hi", direction, -direction) * trades["ret_eod"]
trades["cost"] = trades["date"].apply(lambda d: (4.47 if d < SPLIT else 5.97) + 0.5)
trades["net_pts"] = trades["signed_pts"] - trades["cost"]

trades["cum_net"] = trades["net_pts"].cumsum()
run_max = trades["cum_net"].cummax()
dd = trades["cum_net"] - run_max
maxdd_pts = dd.min()
total_profit = trades["net_pts"].sum()
pos_trades = trades[trades["net_pts"] > 0]
largest_trade_share = pos_trades["net_pts"].max() / pos_trades["net_pts"].sum() if len(pos_trades) else np.nan

print("n_trades", len(trades))
print("total_net_pts", total_profit)
print("mean_net_pts", trades["net_pts"].mean())
print("maxDD_pts (cumulative, in index points on 1-lot equivalent)", maxdd_pts)
print("largest single trade as share of total POSITIVE profit:", largest_trade_share)
print("worst single trade pts:", trades["net_pts"].min())
print("best single trade pts:", trades["net_pts"].max())
print("longest losing streak (consecutive net_pts<0):",
      (trades["net_pts"] < 0).astype(int).groupby((trades["net_pts"] >= 0).cumsum()).sum().max())

# monthly net pts, gross vs net win-rate consistency (trap check from EMA_INTRADAY_BUYING lesson)
trades["month"] = trades["date"].dt.to_period("M")
monthly = trades.groupby("month").agg(gross=("signed_pts", "sum"), net=("net_pts", "sum"), n=("net_pts", "size"))
monthly.to_csv(OUT + r"\h1_wti_monthly.csv")
print("months positive on GROSS:", (monthly["gross"] > 0).mean())
print("months positive on NET:", (monthly["net"] > 0).mean())
print("n months:", len(monthly))

trades.to_csv(OUT + r"\h1_wti_eod_trades.csv", index=False)
