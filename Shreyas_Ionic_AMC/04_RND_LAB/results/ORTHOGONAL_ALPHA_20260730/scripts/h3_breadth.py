"""
H3 -- NIFTY50 constituent breadth (advance/decline) as a lead on the INDEX's own forward return.
Daily-only (no 1-min constituent load needed -- cheapest-first). Multi-day horizon (1/3/5-day),
explicitly NOT intraday (stated in HYPOTHESES.md prior), still "short-horizon" per the mandate.
"""
import numpy as np
import pandas as pd
from scipy import stats

ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
OUT = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\ORTHOGONAL_ALPHA_20260730"

# ---- PIT NIFTY50 membership (monthly Yes/No wide) ----
xls = pd.ExcelFile(ROOT + r"\Historical stock composition of Nifty 50 and Nifty Next 50.xlsx")
mem = pd.read_excel(xls, sheet_name="Nifty 50")
mem = mem.rename(columns={mem.columns[0]: "symbol"})
month_cols = [c for c in mem.columns if c != "symbol"]
mem_long = mem.melt(id_vars="symbol", value_vars=month_cols, var_name="month", value_name="flag")
mem_long["month"] = pd.to_datetime(mem_long["month"])
mem_long = mem_long[mem_long["flag"] == "Yes"][["symbol", "month"]]
mem_long["ym"] = mem_long["month"].dt.to_period("M")
print("membership rows(Yes):", len(mem_long), "months:", mem_long['month'].min(), "-", mem_long['month'].max())

# ---- constituent daily closes (survivorship-safe union panel) ----
panel = pd.read_parquet(ROOT + r"\datasets\derived\pit_union_panel_v1\close_panel_price_v11.parquet")
panel = panel[["date", "symbol", "close"]].copy()
panel["date"] = pd.to_datetime(panel["date"])
panel["ym"] = panel["date"].dt.to_period("M")

# keep only (symbol, ym) pairs that were actually NIFTY50 members that month
mem_set = set(zip(mem_long["symbol"], mem_long["ym"]))
# restrict panel to the membership window first, THEN vectorized isin() (never .apply() on 6.8M rows)
last_mem_month = mem_long["ym"].max()
panel = panel[(panel["ym"] <= last_mem_month) & (panel["date"] >= "2021-01-01")].copy()
mem_idx = pd.MultiIndex.from_tuples(list(mem_set))
panel_idx = pd.MultiIndex.from_arrays([panel["symbol"], panel["ym"]])
panel["is_member"] = panel_idx.isin(mem_idx)
cons = panel[panel["is_member"]].copy()
print("constituent-day rows:", len(cons))

cons = cons.sort_values(["symbol", "date"])
cons["ret"] = cons.groupby("symbol")["close"].pct_change()
cons = cons.dropna(subset=["ret"])

breadth = cons.groupby("date").agg(adv=("ret", lambda s: (s > 0).sum()),
                                    decl=("ret", lambda s: (s < 0).sum()),
                                    n=("ret", "size")).reset_index()
breadth["ad_breadth"] = (breadth["adv"] - breadth["decl"]) / breadth["n"]
breadth = breadth[breadth["n"] >= 30]  # require reasonable coverage that day
print("breadth days:", len(breadth), breadth["date"].min(), breadth["date"].max())
breadth.to_csv(OUT + r"\h3_breadth_daily.csv", index=False)

# ---- NIFTY daily close (from 1-min spot, consistent with H1/H2) ----
nifty = pd.read_parquet(ROOT + r"\intraday_options_strategy\datasets\raw\hf_index_options_1m\index\NIFTY.parquet")
nifty = nifty[nifty["timestamp"].dt.time >= pd.Timestamp("09:15").time()].copy()
nifty["date"] = pd.to_datetime(nifty["trading_day"])
nclose = nifty.groupby("date")["close"].last().reset_index()
del nifty

m = pd.merge(breadth[["date", "ad_breadth", "n"]], nclose, on="date", how="inner").sort_values("date").reset_index(drop=True)
for h in [1, 3, 5]:
    m[f"fwd_ret_{h}"] = m["close"].shift(-h) / m["close"] - 1
m = m.dropna(subset=[f"fwd_ret_{h}" for h in [1, 3, 5]])
print("merged breadth+nifty rows:", len(m), m["date"].min(), m["date"].max())

SPLIT = pd.Timestamp("2024-10-01")
HOLDOUT = pd.Timestamp("2026-01-01")
build = m[m["date"] < HOLDOUT].copy()
oos = m[m["date"] >= HOLDOUT].copy()

np.random.seed(20260730)
results = []
for h in [1, 3, 5]:
    col = f"fwd_ret_{h}"
    q20, q80 = build["ad_breadth"].quantile(0.20), build["ad_breadth"].quantile(0.80)
    hi = build[build["ad_breadth"] >= q80][col]
    lo = build[build["ad_breadth"] <= q20][col]
    t, p = stats.ttest_ind(hi, lo, equal_var=False)
    spread = (hi.mean() - lo.mean()) * 100  # in %

    bvals = build["ad_breadth"].values
    fvals = build[col].values
    null = np.empty(500)
    for i in range(500):
        perm = np.random.permutation(len(build))
        bb = bvals[perm]
        hh = fvals[bb >= q80]; ll = fvals[bb <= q20]
        if len(hh) < 10 or len(ll) < 10:
            null[i] = np.nan; continue
        null[i] = (hh.mean() - ll.mean()) * 100
    null = null[~np.isnan(null)]
    placebo_p = (np.abs(null) >= np.abs(spread)).mean()

    pre = build[build["date"] < SPLIT]; post = build[build["date"] >= SPLIT]
    def sub_stat(d):
        h_ = d[d["ad_breadth"] >= q80][col]; l_ = d[d["ad_breadth"] <= q20][col]
        if len(h_) < 10 or len(l_) < 10:
            return np.nan, np.nan, 0
        tt, _ = stats.ttest_ind(h_, l_, equal_var=False)
        return (h_.mean() - l_.mean()) * 100, tt, len(h_) + len(l_)
    spread_pre, t_pre, n_pre = sub_stat(pre)
    spread_post, t_post, n_post = sub_stat(post)
    spread_oos, t_oos, n_oos = sub_stat(oos)

    trades_per_month = (len(hi) + len(lo)) / ((build["date"].max() - build["date"].min()).days / 30.44)
    results.append(dict(horizon_days=h, n_build=len(hi) + len(lo), spread_pct=spread, t_build=t,
                         placebo_p=placebo_p, spread_pre_pct=spread_pre, t_pre=t_pre, n_pre=n_pre,
                         spread_post_pct=spread_post, t_post=t_post, n_post=n_post,
                         spread_oos2026_pct=spread_oos, t_oos2026=t_oos, n_oos2026=n_oos,
                         trades_per_month=trades_per_month))

res = pd.DataFrame(results)
res.to_csv(OUT + r"\h3_breadth_cells.csv", index=False)
print(res.to_string())
