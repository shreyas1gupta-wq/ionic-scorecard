# T13 — Review request: 12-1 momentum on the NIFTY-500

Classic cross-sectional momentum submission. Prices are the survivorship-complete
adjusted union panel (includes delisted names). Execution is next-open entry with
circuit/zero-volume no-fill checks and 45bp/side costs.

Reported result: 2013-2025, top-50 monthly-rebalanced basket 24.8% CAGR vs index 12.1%.

```python
import pandas as pd

close = pd.read_parquet("union_close_panel.parquet")   # adjusted, incl. delisted names

universe = pd.read_csv("nifty500_constituents.csv")["Symbol"].tolist()
# downloaded from the index provider's website, 2026-07 refresh, 500 symbols

close = close[[c for c in close.columns if c in universe]]
ret = close.pct_change()

# 12-1 momentum: return from t-252 to t-21 (skip the most recent month)
mom = close.shift(21).pct_change(231)

month_ends = close.groupby(close.index.to_period("M")).tail(1).index
weights = pd.DataFrame(0.0, index=close.index, columns=close.columns)

for me in month_ends:
    row = mom.loc[me].dropna()
    if len(row) < 200:
        continue
    top = row.nlargest(50).index
    nxt = close.index[close.index.searchsorted(me, side="right")]
    weights.loc[nxt:, :] = 0.0
    weights.loc[nxt:, top] = 1.0 / 50

# next-open entries approximated at next session; no-fill on circuit-locked or
# zero-volume opens handled inside apply_fill_rules()
port = apply_fill_rules(weights.shift(1) * ret)
port -= turnover_costs(weights, bps_per_side=45)
print("CAGR:", ann_return(port), " maxDD:", max_drawdown(port))
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**
