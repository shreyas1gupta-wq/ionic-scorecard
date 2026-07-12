# T19 — Review request: mid-cap momentum on the union panel

Cross-sectional momentum submission for the equity book. The author rebuilt an older
run after the data office published the survivorship-complete panel.

Reported result: 2014-2025, 16.2% CAGR net vs random-basket null p50 of 11.9%
(strategy at the 93rd percentile of 10,000 nulls); maxDD -34%.

```python
import pandas as pd

close = pd.read_parquet("close_panel_return_v11.parquet")   # union panel incl. delisted
stale = pd.read_parquet("stale_mask.parquet")               # frozen/stale price runs
close = close.mask(stale)                                    # stale rows excluded

members = load_pit_membership()      # 42 Mar/Sep point-in-time snapshots
ret = close.pct_change()

# 12-1 momentum, computed strictly from data through the signal date
mom = close.shift(21).pct_change(231)

for me in month_ends:
    univ = members.asof(me)                      # latest snapshot ON OR BEFORE me
    row = mom.loc[me, [s for s in univ if s in mom.columns]].dropna()
    row = row[eligible_midcap(row.index, asof=me)]
    if len(row) < 120:
        continue
    top = row.nlargest(40).index
    set_target_weights(date=first_session_after(me), names=top, w=1.0 / 40)

# execution: entries at the first session AFTER the rebalance date, filled at open;
# no-fill on circuit-locked or zero-volume opens (fill_check); 45bp/side costs.
#
# delistings: if a held name stops trading, the position is marked to its last
# traded price and the loss realized on the delisting date (no silent drop).
#
# null: 10,000 random 40-name baskets from the SAME panel, SAME PIT universe,
# SAME monthly rebalance dates and cost model (turnover-matched by construction).
port = run_engine(...)
print(report(port))
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**
