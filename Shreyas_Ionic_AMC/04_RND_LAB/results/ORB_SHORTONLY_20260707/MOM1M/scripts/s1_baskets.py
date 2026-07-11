"""S1: 1-MONTH (21 trading day) momentum-50 baskets. Monthly rebalance, causal, PIT universe.
HF daily close is ALREADY split/bonus adjusted (verified in prior 3m run: TTKPRESTIG 10:1,
IRCTC 5:1 show NO price jump) => use raw close, DO NOT re-adjust (would fabricate 10x).
OUT: baskets.csv (month,rank,symbol,ret_1m), union_symbols.txt
"""
import sys, os
import numpy as np, pandas as pd
ROOT = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500"
OUT = os.path.join(ROOT, r"Shreyas_Ionic_AMC/04_RND_LAB/results/ORB_SHORTONLY_20260707/MOM1M")
sys.path.insert(0, os.path.join(ROOT, r"Shreyas_Ionic_AMC/04_RND_LAB/lib"))
import guards as G

LOOKBACK = 21          # trading days ~ 1 month (the NEW variable vs prior 63-td/3m test)
TOP_N = 50
FIRST_MONTH = "2022-01"  # minute data starts 2022-01-03
LAST_MONTH  = "2026-01"  # minute data ends 2026-01-21 (partial)

d = pd.read_parquet(os.path.join(ROOT, r"swing_momentum/data/hf_stock_minute/day/train-00000.parquet"),
                    columns=["symbol", "timestamp", "close"])
d = G.fix_ist_dates(d)                      # L1: 18:30 UTC -> IST next-day date
d["date"] = pd.to_datetime(d["date"])
d = d[d["close"] > 0].sort_values(["symbol", "date"]).reset_index(drop=True)
d["adj"] = d["close"].astype("float64")     # NO re-adjustment (already adjusted)

uni = pd.read_excel(os.path.join(ROOT, "NIFTY500_TICKER_2005_2025_Final.xlsx"), sheet_name="Sheet1")
def snap_to_date(s):
    mon = {"Mar": 3, "Sep": 9}[s[:3]]
    return pd.Timestamp(int(s[3:]), mon, 1)
uni["snap_date"] = uni["Month-Year"].map(snap_to_date)
snap_members = {sd: set(g["Ticker"]) for sd, g in uni.groupby("snap_date")}
snap_dates = sorted(snap_members)

def universe_for(month_start):
    elig = [sd for sd in snap_dates if sd <= month_start]
    return snap_members[elig[-1]] if elig else set()

sym_arr = {}
for sym, g in d.groupby("symbol"):
    sym_arr[sym] = (g["date"].values, g["adj"].values)

months = pd.period_range(FIRST_MONTH, LAST_MONTH, freq="M")
rows = []
for per in months:
    m_start = per.to_timestamp()
    asof = m_start - pd.Timedelta(days=1)    # last day strictly before month => causal
    uset = universe_for(m_start)
    rets = []
    for sym in uset:
        if sym not in sym_arr:
            continue
        dates, adj = sym_arr[sym]
        j = np.searchsorted(dates, np.datetime64(asof), side="right") - 1
        if j < LOOKBACK:
            continue
        p_end = adj[j]; p_start = adj[j - LOOKBACK]
        if p_start <= 0 or not np.isfinite(p_start) or not np.isfinite(p_end):
            continue
        rets.append((sym, p_end / p_start - 1.0))
    if not rets:
        continue
    rr = pd.DataFrame(rets, columns=["symbol", "ret_1m"]).sort_values("ret_1m", ascending=False)
    top = rr.head(TOP_N).reset_index(drop=True)
    top["rank"] = top.index + 1
    top["month"] = str(per)
    rows.append(top)

bask = pd.concat(rows, ignore_index=True)[["month", "rank", "symbol", "ret_1m"]]
bask.to_csv(os.path.join(OUT, "baskets.csv"), index=False)
union = sorted(bask["symbol"].unique())
with open(os.path.join(OUT, "union_symbols.txt"), "w") as f:
    f.write("\n".join(union))

print("ret_1m dist: p50 %.3f p90 %.3f p99 %.3f max %.3f | >1x count %d" % (
    bask.ret_1m.median(), bask.ret_1m.quantile(.9), bask.ret_1m.quantile(.99),
    bask.ret_1m.max(), (bask.ret_1m > 1).sum()))
print("MONTHS", bask["month"].nunique(), "rows", len(bask))
print("UNION symbols", len(union))
print("avg basket size", bask.groupby("month").size().mean())
print("months with <50:", (bask.groupby("month").size() < 50).sum())
print("sample top5 first month:\n", bask[bask.month == bask.month.iloc[0]].head(5).to_string())
print("sample top5 last month:\n", bask[bask.month == bask.month.iloc[-1]].head(5).to_string())
