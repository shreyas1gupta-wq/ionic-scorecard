# T04 — Review request: quarterly revenue-growth rotation

Submission for the fundamental-momentum family. Universe membership is taken from the
42-snapshot point-in-time constituent file (as-of logic on Mar/Sep snapshot dates), so
the author states survivorship is handled. Prices are the adjusted union close panel.

Reported result: top-30 basket 21.7% CAGR vs universe equal-weight 12.9% (2016-2025),
quarterly rebalance, 40bp/side costs included.

```python
import pandas as pd

rev = pd.read_parquet("quarterly_revenue.parquet")
# columns: symbol, quarter_end (fiscal quarter end date), revenue (consolidated, Rs cr)
rev = rev.sort_values(["symbol", "quarter_end"])
rev["rev_yoy"] = rev.groupby("symbol")["revenue"].pct_change(4)

close = pd.read_parquet("close_panel.parquet")     # adjusted closes, IST dates
ret = close.pct_change()
members = load_pit_membership()                    # symbol lists as-of Mar/Sep snapshots

qe_dates = sorted(rev["quarter_end"].unique())
weights = pd.DataFrame(0.0, index=close.index, columns=close.columns)

for qe in qe_dates:
    snap = rev[rev["quarter_end"] == qe].dropna(subset=["rev_yoy"])
    univ = members.asof(qe)                        # membership as of the quarter end
    snap = snap[snap["symbol"].isin(univ)]
    if len(snap) < 60:
        continue
    top = snap.nlargest(30, "rev_yoy")["symbol"]

    # rebalance on the first trading day AFTER the quarter ends, fill at open
    rebal_day = close.index[close.index.searchsorted(qe, side="right")]
    held = [s for s in top if s in close.columns]
    weights.loc[rebal_day:, :] = 0.0
    weights.loc[rebal_day:, held] = 1.0 / len(held)

# open-fill approximated as next session; positions earn from the session
# after the rebalance day
port = (weights.shift(1) * ret).sum(axis=1)
port -= turnover_costs(weights, bps_per_side=40)
print("CAGR:", ann_return(port))
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**
