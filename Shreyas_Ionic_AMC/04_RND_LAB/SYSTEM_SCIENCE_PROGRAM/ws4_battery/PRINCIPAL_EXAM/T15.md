# T15 — Review request: IV-percentile strangle seller

Weekly short-vol rule on the index. The author standardizes the IV level before
thresholding, "so the rule generalizes across vol regimes". Entry-day option prices
are verified; entries are next-session-open after the signal evaluates true.

Reported result: 2015-2025, 214 entries, avg +1.7% of premium net, hit 79%,
worst trade -21% of premium (Mar-2020 skipped by the crash filter).

```python
import pandas as pd

hist = pd.read_parquet("nifty_iv_daily.parquet")       # 2015-2025 daily ATM IV

mu = hist["iv"].mean()
sd = hist["iv"].std()
hist["iv_z"] = (hist["iv"] - mu) / sd

# entry: IV meaningfully rich vs its normal level, but not crash regime
hist["entry"] = (hist["iv_z"] > 1.0) & (hist["iv_z"] < 2.5)

trades = []
for d in hist.index[hist["entry"]]:
    t = sell_weekly_strangle(
        signal_day=d,
        entry="next_open",                 # fills at next session's open prints
        wings=(0.97, 1.03),
        exit_rule=("hold_to_expiry",),
        liquidity=("both_legs_traded",),   # skip if either leg had no trades
    )
    if t is not None:
        trades.append(t.net_pnl_pct_premium)

tr = pd.Series(trades)
print("entries:", len(tr), " mean:", round(tr.mean(), 2), "% of premium",
      " hit:", round((tr > 0).mean() * 100, 1), "%")
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**
