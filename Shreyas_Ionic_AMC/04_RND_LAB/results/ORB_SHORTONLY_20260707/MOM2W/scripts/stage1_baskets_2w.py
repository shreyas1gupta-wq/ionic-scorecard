"""Stage 1: 2-WEEK (10-td) momentum-50 baskets, BI-WEEKLY rebalance (every 10 td), causal, PIT universe.
Rationale for cadence: a 10-td momentum signal held a full month is stale for ~2 of 4 weeks; rebalancing
every 10 td keeps the holding horizon == the ranking horizon. HF daily close is ALREADY split/bonus-adj
(verified prior work TTKPRESTIG/IRCTC) => use raw close, price-return momentum.
OUT: active_days.csv (date,symbol,rank,rebal_date,ret_2w), baskets_rebal.csv, union_symbols.txt
"""
import sys, os
import numpy as np, pandas as pd
ROOT = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500"
OUT = os.path.join(ROOT, r"Shreyas_Ionic_AMC/04_RND_LAB/results/ORB_SHORTONLY_20260707/MOM2W")
sys.path.insert(0, os.path.join(ROOT, r"Shreyas_Ionic_AMC/04_RND_LAB/lib"))
import guards as G

LOOKBACK = 10           # trading days ~ 2 weeks
REBAL_EVERY = 10        # bi-weekly rebalance (== lookback, no staleness)
TOP_N = 50
MIN_DATE = pd.Timestamp("2022-01-03")   # minute data starts here
MAX_DATE = pd.Timestamp("2026-01-21")   # minute data ends here

# ---- daily close (HF), IST date, already split/bonus-adjusted ----
d = pd.read_parquet(os.path.join(ROOT, r"swing_momentum/data/hf_stock_minute/day/train-00000.parquet"),
                    columns=["symbol", "timestamp", "close"])
d = G.fix_ist_dates(d)                      # L1: 18:30 UTC -> IST next-day date
d["date"] = pd.to_datetime(d["date"])
d = d[d["close"] > 0].sort_values(["symbol", "date"]).reset_index(drop=True)
d["adj"] = d["close"].astype("float64")     # NO re-adjustment (HF already adjusted)

# ---- PIT universe snapshots ----
uni = pd.read_excel(os.path.join(ROOT, "NIFTY500_TICKER_2005_2025_Final.xlsx"), sheet_name="Sheet1")
def snap_to_date(s):
    mon = {"Mar": 3, "Sep": 9}[s[:3]]
    return pd.Timestamp(int(s[3:]), mon, 1)
uni["snap_date"] = uni["Month-Year"].map(snap_to_date)
snap_members = {sd: set(g["Ticker"]) for sd, g in uni.groupby("snap_date")}
snap_dates = sorted(snap_members)
def universe_for(day):
    elig = [sd for sd in snap_dates if sd <= day]
    return snap_members[elig[-1]] if elig else set()

# ---- trading calendar (union of dates in daily data, within minute range) ----
cal = np.array(sorted(d["date"].unique()))
cal = cal[(cal >= np.datetime64(MIN_DATE)) & (cal <= np.datetime64(MAX_DATE))]
print("trading days in range:", len(cal), cal[0], "->", cal[-1])

# ---- per-symbol sorted arrays for fast trailing-return lookup ----
sym_arr = {sym: (g["date"].values, g["adj"].values) for sym, g in d.groupby("symbol")}

# ---- bi-weekly rebalance schedule ----
rebal_idx = list(range(0, len(cal), REBAL_EVERY))
rows_active = []
rows_rebal = []
for ri, i in enumerate(rebal_idx):
    rdate = pd.Timestamp(cal[i])
    asof = pd.Timestamp(cal[i - 1]) if i >= 1 else None   # last trading day strictly before rebal
    if asof is None:
        continue                                          # first period has no prior day to rank on
    uset = universe_for(rdate)
    rets = []
    for sym in uset:
        if sym not in sym_arr:
            continue
        dates, adj = sym_arr[sym]
        j = np.searchsorted(dates, np.datetime64(asof), side="right") - 1  # last obs <= asof
        if j < LOOKBACK:
            continue
        p_end = adj[j]; p_start = adj[j - LOOKBACK]
        if p_start <= 0 or not np.isfinite(p_start) or not np.isfinite(p_end):
            continue
        rets.append((sym, p_end / p_start - 1.0))
    if not rets:
        continue
    rr = pd.DataFrame(rets, columns=["symbol", "ret_2w"]).sort_values("ret_2w", ascending=False)
    top = rr.head(TOP_N).reset_index(drop=True)
    top["rank"] = top.index + 1
    top["rebal_date"] = rdate
    rows_rebal.append(top)
    # active trading days = [rdate, next_rebal) intersect calendar
    end_i = rebal_idx[ri + 1] if ri + 1 < len(rebal_idx) else len(cal)
    active_dates = cal[i:end_i]
    for _, rw in top.iterrows():
        for ad in active_dates:
            rows_active.append((pd.Timestamp(ad), rw["symbol"], int(rw["rank"]),
                                rdate, round(rw["ret_2w"], 6)))

bask = pd.concat(rows_rebal, ignore_index=True)[["rebal_date", "rank", "symbol", "ret_2w"]]
bask.to_csv(os.path.join(OUT, "baskets_rebal.csv"), index=False)
act = pd.DataFrame(rows_active, columns=["date", "symbol", "rank", "rebal_date", "ret_2w"])
act.to_csv(os.path.join(OUT, "active_days.csv"), index=False)
union = sorted(act["symbol"].unique())
with open(os.path.join(OUT, "union_symbols.txt"), "w") as f:
    f.write("\n".join(union))

print("REBALANCES:", bask["rebal_date"].nunique(), "| avg basket size:",
      round(bask.groupby("rebal_date").size().mean(), 1),
      "| rebals with <50:", int((bask.groupby("rebal_date").size() < 50).sum()))
print("ret_2w dist: p50 %.3f p90 %.3f p99 %.3f max %.3f | >1.0 (100%%) count %d" % (
    bask.ret_2w.median(), bask.ret_2w.quantile(.9), bask.ret_2w.quantile(.99),
    bask.ret_2w.max(), int((bask.ret_2w > 1.0).sum())))
print("UNION symbols:", len(union), "| active symbol-days:", len(act))
# turnover: avg fraction of basket replaced rebal-to-rebal
prev = None; turns = []
for rd, g in bask.groupby("rebal_date"):
    s = set(g["symbol"])
    if prev is not None:
        turns.append(1 - len(s & prev) / TOP_N)
    prev = s
print("avg name turnover per rebalance: %.1f%%" % (100 * np.mean(turns)))
print("STAGE1 DONE")
