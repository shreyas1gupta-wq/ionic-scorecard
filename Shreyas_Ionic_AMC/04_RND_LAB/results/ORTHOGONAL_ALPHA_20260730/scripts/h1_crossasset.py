"""
H1 -- Overnight cross-asset shock (SPX, VIX, USDINR, US10Y, WTI crude) vs NIFTY intraday
continuation (open->30min / open->60min / open->EOD).
Pre-registered in HYPOTHESES.md BEFORE this ran. Self-contained, writes its own outputs.
"""
import sys, json
import numpy as np
import pandas as pd

ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
OUT = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\ORTHOGONAL_ALPHA_20260730"

# ---------- 1. NIFTY intraday targets ----------
nifty = pd.read_parquet(ROOT + r"\intraday_options_strategy\datasets\raw\hf_index_options_1m\index\NIFTY.parquet")
nifty = nifty[nifty["timestamp"].dt.time >= pd.Timestamp("09:15").time()].copy()
nifty["date"] = pd.to_datetime(nifty["trading_day"])
nifty["t"] = nifty["timestamp"].dt.time

rows = []
for d, g in nifty.groupby("date", sort=True):
    g = g.sort_values("timestamp")
    day_open = g.iloc[0]["open"]
    day_close = g.iloc[-1]["close"]
    g30 = g[g["t"] <= pd.Timestamp("09:45").time()]
    g60 = g[g["t"] <= pd.Timestamp("10:15").time()]
    c30 = g30.iloc[-1]["close"] if len(g30) else np.nan
    c60 = g60.iloc[-1]["close"] if len(g60) else np.nan
    rows.append((d, day_open, c30, c60, day_close))
daily = pd.DataFrame(rows, columns=["date", "open", "c30", "c60", "close"]).sort_values("date").reset_index(drop=True)
daily["prior_close"] = daily["close"].shift(1)
daily["gap"] = daily["open"] - daily["prior_close"]
daily["ret_30"] = daily["c30"] - daily["open"]
daily["ret_60"] = daily["c60"] - daily["open"]
daily["ret_eod"] = daily["close"] - daily["open"]
daily = daily.dropna(subset=["prior_close"]).reset_index(drop=True)
print("NIFTY daily rows:", len(daily), daily["date"].min(), daily["date"].max())

# ---------- 2. cross-asset signals (all daily, own-session pct/diff change) ----------
DATA = ROOT + r"\Shreyas_Ionic_AMC\05_DATA_OFFICE\data"

spx = pd.read_parquet(DATA + r"\us_sp500_daily.parquet").rename(columns={"Date": "date", "Close": "close"})
spx["date"] = pd.to_datetime(spx["date"])
spx = spx.sort_values("date")
spx["spx_ret1d"] = spx["close"].pct_change() * 100

vix = pd.read_parquet(DATA + r"\cboe_vix_daily.parquet").rename(columns={"DATE": "date", "CLOSE": "close"})
vix["date"] = pd.to_datetime(vix["date"])
vix = vix.sort_values("date")
vix["vix_chg1d"] = vix["close"].diff()

usdinr = pd.read_parquet(DATA + r"\usdinr_fred_daily.parquet")
usdinr["date"] = pd.to_datetime(usdinr["date"])
usdinr = usdinr.sort_values("date")
usdinr["usdinr_ret1d"] = usdinr["usdinr"].pct_change() * 100

us10y = pd.read_parquet(DATA + r"\us_treasury_yields_daily.parquet").rename(columns={"Date": "date"})
us10y["date"] = pd.to_datetime(us10y["date"])
us10y = us10y.sort_values("date")
ycol = "10 Yr" if "10 Yr" in us10y.columns else [c for c in us10y.columns if "10" in c][0]
us10y["us10y_chg1d"] = us10y[ycol].diff() * 100  # in bps

wti = pd.read_parquet(DATA + r"\wti_crude_fred_daily.parquet")
wti["date"] = pd.to_datetime(wti["date"])
wti = wti.sort_values("date")
wti["wti_ret1d"] = wti["wti"].pct_change() * 100

SIGNALS = {
    "spx_ret1d": spx[["date", "spx_ret1d"]],
    "vix_chg1d": vix[["date", "vix_chg1d"]],
    "usdinr_ret1d": usdinr[["date", "usdinr_ret1d"]],
    "us10y_chg1d": us10y[["date", "us10y_chg1d"]],
    "wti_ret1d": wti[["date", "wti_ret1d"]],
}

merged = daily.copy()
for name, sdf in SIGNALS.items():
    sdf = sdf.dropna().sort_values("date")
    merged = pd.merge_asof(merged.sort_values("date"), sdf, left_on="date", right_on="date",
                            direction="backward", allow_exact_matches=False)
merged = merged.dropna(subset=list(SIGNALS.keys())).reset_index(drop=True)
print("Merged rows (all signals available):", len(merged), merged["date"].min(), merged["date"].max())

SPLIT = pd.Timestamp("2024-10-01")
HOLDOUT = pd.Timestamp("2026-01-01")
build = merged[merged["date"] < HOLDOUT].copy()
oos = merged[merged["date"] >= HOLDOUT].copy()

HORIZONS = {"30min": "ret_30", "60min": "ret_60", "eod": "ret_eod"}

def cost_pts(date):
    return (4.47 if date < SPLIT else 5.97) + 0.5

def welch(a, b):
    from scipy import stats
    t, p = stats.ttest_ind(a, b, equal_var=False)
    return t, p

def cell_stats(sub, ret_col, lo_mask, hi_mask, label):
    lo = sub.loc[lo_mask, ret_col].dropna()
    hi = sub.loc[hi_mask, ret_col].dropna()
    if len(lo) < 5 or len(hi) < 5:
        return None
    t, p = welch(hi, lo)
    spread = hi.mean() - lo.mean()
    return dict(label=label, n_lo=len(lo), n_hi=len(hi), mean_lo=lo.mean(), mean_hi=hi.mean(),
                spread=spread, t=t)

np.random.seed(20260730)
N_PLACEBO = 500
results = []
for sig_name in SIGNALS:
    q20 = build[sig_name].quantile(0.20)
    q80 = build[sig_name].quantile(0.80)
    for hlabel, ret_col in HORIZONS.items():
        lo_mask_all = merged[sig_name] <= q20
        hi_mask_all = merged[sig_name] >= q80

        build_lo = build[sig_name] <= q20
        build_hi = build[sig_name] >= q80
        c_build = cell_stats(build, ret_col, build_lo, build_hi, "build_full")
        if c_build is None:
            continue
        spread_obs = c_build["spread"]

        pre = build[build["date"] < SPLIT]
        post = build[build["date"] >= SPLIT]
        c_pre = cell_stats(pre, ret_col, pre[sig_name] <= q20, pre[sig_name] >= q80, "pre_2024_10")
        c_post = cell_stats(post, ret_col, post[sig_name] <= q20, post[sig_name] >= q80, "post_2024_10")
        oos_lo = oos[sig_name] <= q20
        oos_hi = oos[sig_name] >= q80
        c_oos = cell_stats(oos, ret_col, oos_lo, oos_hi, "held_out_2026")

        # placebo: day-block permutation on BUILD sample -- shuffle signal-day <-> target-day pairing
        sig_vals = build[sig_name].values
        ret_vals = build[ret_col].values
        null_spreads = np.empty(N_PLACEBO)
        n = len(build)
        for i in range(N_PLACEBO):
            perm = np.random.permutation(n)
            shuf_sig = sig_vals[perm]
            lo_p = shuf_sig <= q20
            hi_p = shuf_sig >= q80
            if lo_p.sum() < 5 or hi_p.sum() < 5:
                null_spreads[i] = np.nan
                continue
            null_spreads[i] = ret_vals[hi_p].mean() - ret_vals[lo_p].mean()
        null_spreads = null_spreads[~np.isnan(null_spreads)]
        placebo_p = (np.abs(null_spreads) >= np.abs(spread_obs)).mean()

        # tradeable direction & net-of-cost, using BUILD sign only (no lookahead into OOS)
        direction = 1.0 if spread_obs >= 0 else -1.0
        trade_lo = build.loc[build_lo, [ret_col, "date"]].copy(); trade_lo["side"] = "lo"
        trade_hi = build.loc[build_hi, [ret_col, "date"]].copy(); trade_hi["side"] = "hi"
        trades = pd.concat([trade_lo, trade_hi])
        trades["signed_pts"] = np.where(trades["side"] == "hi", direction, -direction) * trades[ret_col]
        trades["cost"] = trades["date"].apply(cost_pts)
        trades["net_pts"] = trades["signed_pts"] - trades["cost"]
        n_trades = len(trades)
        n_months = (build["date"].max() - build["date"].min()).days / 30.44
        trades_per_month = n_trades / n_months
        win_mask = trades["net_pts"] > 0
        win_rate = win_mask.mean()
        avg_win = trades.loc[win_mask, "net_pts"].mean() if win_mask.any() else np.nan
        avg_loss = trades.loc[~win_mask, "net_pts"].mean() if (~win_mask).any() else np.nan
        rr = abs(avg_win / avg_loss) if (avg_loss not in (0, np.nan) and not pd.isna(avg_loss)) else np.nan
        gross_mean = trades["signed_pts"].mean()
        net_mean = trades["net_pts"].mean()

        results.append(dict(
            signal=sig_name, horizon=hlabel,
            n_build=c_build["n_lo"] + c_build["n_hi"], spread_pts=spread_obs, t_build=c_build["t"],
            mean_lo=c_build["mean_lo"], mean_hi=c_build["mean_hi"],
            t_pre=c_pre["t"] if c_pre else np.nan, spread_pre=c_pre["spread"] if c_pre else np.nan,
            n_pre=(c_pre["n_lo"] + c_pre["n_hi"]) if c_pre else np.nan,
            t_post=c_post["t"] if c_post else np.nan, spread_post=c_post["spread"] if c_post else np.nan,
            n_post=(c_post["n_lo"] + c_post["n_hi"]) if c_post else np.nan,
            t_oos2026=c_oos["t"] if c_oos else np.nan, spread_oos2026=c_oos["spread"] if c_oos else np.nan,
            n_oos2026=(c_oos["n_lo"] + c_oos["n_hi"]) if c_oos else np.nan,
            placebo_p=placebo_p, direction=direction,
            gross_mean_pts=gross_mean, net_mean_pts=net_mean,
            win_rate=win_rate, rr=rr, trades_per_month=trades_per_month, n_trades_build=n_trades,
        ))

res = pd.DataFrame(results)
res.to_csv(OUT + r"\h1_crossasset_cells.csv", index=False)
print(res[["signal", "horizon", "spread_pts", "t_build", "placebo_p", "net_mean_pts", "win_rate", "rr", "trades_per_month"]].to_string())
print("TOTAL CELLS:", len(res))
