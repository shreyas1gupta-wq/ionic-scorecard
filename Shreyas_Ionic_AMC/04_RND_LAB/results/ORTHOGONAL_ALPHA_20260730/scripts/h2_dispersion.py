"""
H2 -- NIFTY vs BANKNIFTY intraday relative-value dispersion. Stage-1 signal test only (per
cheapest-first discipline): does an extreme z-score of the intraday NIFTY-vs-BANKNIFTY spread
predict forward MEAN REVERSION of that spread? No P&L/cost harness built unless this clears
placebo with a economically meaningful point size (mirrors CHAIN_MICRO_20260730's own Stage-1/2 gate).
"""
import numpy as np
import pandas as pd

ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
OUT = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\ORTHOGONAL_ALPHA_20260730"

nifty = pd.read_parquet(ROOT + r"\intraday_options_strategy\datasets\raw\hf_index_options_1m\index\NIFTY.parquet")
bnf = pd.read_parquet(ROOT + r"\intraday_options_strategy\datasets\raw\hf_index_options_1m\index\BANKNIFTY.parquet")

for df in (nifty, bnf):
    pass

nifty = nifty[nifty["timestamp"].dt.time >= pd.Timestamp("09:15").time()][["timestamp", "close", "trading_day"]].rename(columns={"close": "nifty"})
bnf = bnf[bnf["timestamp"].dt.time >= pd.Timestamp("09:15").time()][["timestamp", "close"]].rename(columns={"close": "bnf"})

m = pd.merge(nifty, bnf, on="timestamp", how="inner").sort_values("timestamp").reset_index(drop=True)
print("merged 1-min rows:", len(m), m["timestamp"].min(), m["timestamp"].max())
del nifty, bnf

m["date"] = pd.to_datetime(m["trading_day"])
# day-open anchored % return for each index (session-reset)
m["nifty_open"] = m.groupby("date")["nifty"].transform("first")
m["bnf_open"] = m.groupby("date")["bnf"].transform("first")
m["nifty_pct"] = (m["nifty"] / m["nifty_open"] - 1) * 100
m["bnf_pct"] = (m["bnf"] / m["bnf_open"] - 1) * 100
m["spread"] = m["nifty_pct"] - m["bnf_pct"]

# trailing 30-min z-score of spread, reset per day (min_periods=15 to avoid degenerate early-bar z)
def zscore_session(s, window=30, minp=15):
    r = s.rolling(window, min_periods=minp)
    return (s - r.mean()) / r.std()

m["z"] = m.groupby("date")["spread"].transform(lambda s: zscore_session(s))
m = m.dropna(subset=["z"]).reset_index(drop=True)

HORIZ_MIN = [15, 30, 60]
for h in HORIZ_MIN:
    m[f"fwd_spread_chg_{h}"] = m.groupby("date")["spread"].transform(lambda s: s.shift(-h) - s)

SPLIT = pd.Timestamp("2024-10-01")
HOLDOUT = pd.Timestamp("2026-01-01")
build = m[m["date"] < HOLDOUT].copy()
oos = m[m["date"] >= HOLDOUT].copy()

np.random.seed(20260730)
results = []
for h in HORIZ_MIN:
    col = f"fwd_spread_chg_{h}"
    sub = build.dropna(subset=[col, "z"])
    q10, q90 = sub["z"].quantile(0.10), sub["z"].quantile(0.90)
    hi = sub[sub["z"] >= q90][col]   # spread ran up hard -> expect reversion DOWN if mean-reverting
    lo = sub[sub["z"] <= q10][col]   # spread ran down hard -> expect reversion UP
    from scipy import stats
    t, p = stats.ttest_ind(hi, lo, equal_var=False)
    spread_obs = hi.mean() - lo.mean()  # if mean-reverting, expect this NEGATIVE (hi reverts down, lo reverts up)

    # placebo: shuffle minute-bar (row) <-> z assignment within build (breaks the z<->fwd link,
    # keeps each series' own marginal/intraday-time structure via a fixed-size random draw)
    zvals = sub["z"].values
    fvals = sub[col].values
    null = np.empty(300)
    for i in range(300):
        perm = np.random.permutation(len(sub))
        zz = zvals[perm]
        hh = fvals[zz >= q90]
        ll = fvals[zz <= q10]
        if len(hh) < 20 or len(ll) < 20:
            null[i] = np.nan
            continue
        null[i] = hh.mean() - ll.mean()
    null = null[~np.isnan(null)]
    placebo_p = (np.abs(null) >= np.abs(spread_obs)).mean()

    pre = sub[sub["date"] < SPLIT]
    post = sub[sub["date"] >= SPLIT]
    def sub_stat(d):
        h_ = d[d["z"] >= q90][col]; l_ = d[d["z"] <= q10][col]
        if len(h_) < 10 or len(l_) < 10:
            return np.nan, np.nan, 0
        tt, _ = stats.ttest_ind(h_, l_, equal_var=False)
        return h_.mean() - l_.mean(), tt, len(h_) + len(l_)
    spread_pre, t_pre, n_pre = sub_stat(pre)
    spread_post, t_post, n_post = sub_stat(post)

    oos_sub = oos.dropna(subset=[col, "z"])
    spread_oos, t_oos, n_oos = sub_stat(oos_sub)

    n_days_build = build["date"].nunique()
    results.append(dict(horizon_min=h, n_build=len(hi) + len(lo), spread_obs_pct=spread_obs, t_build=t,
                         placebo_p=placebo_p, spread_pre=spread_pre, t_pre=t_pre, n_pre=n_pre,
                         spread_post=spread_post, t_post=t_post, n_post=n_post,
                         spread_oos2026=spread_oos, t_oos2026=t_oos, n_oos2026=n_oos,
                         signal_events_per_day=(len(hi) + len(lo)) / n_days_build))

res = pd.DataFrame(results)
res.to_csv(OUT + r"\h2_dispersion_cells.csv", index=False)
print(res.to_string())
