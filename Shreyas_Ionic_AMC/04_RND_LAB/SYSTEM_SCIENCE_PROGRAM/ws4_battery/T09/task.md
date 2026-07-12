# T09 — Review request: index trend filter with breadth confirmation

Daily long/flat timing model for the index sleeve. All series are official NSE daily
data with correct IST dates; `advances`/`declines` are the exchange's daily
market-breadth counts for each session.

Reported result: 2015-2025, long 38% of days, CAGR 17.1% vs buy-and-hold 12.4%,
max DD -11% vs -38%.

```python
import pandas as pd

df = pd.read_parquet("nifty_with_breadth.parquet")
# index: IST date; columns: open, close, advances, declines

df["ret1"] = df["close"].pct_change()

# features -- evaluated at day t's close, from data known by that close:
df["mom10"] = df["close"].pct_change(10)
df["vol20"] = df["ret1"].rolling(20).std()
df["adv_dec"] = (df["advances"] / df["declines"]).shift(-1)
df["above_dma"] = df["close"] > df["close"].rolling(50).mean()
df["vol_regime_ok"] = df["vol20"] < df["vol20"].rolling(100).mean()

df["signal"] = (
    (df["mom10"] > 0)
    & (df["adv_dec"] > 1.5)
    & df["above_dma"].fillna(False)
    & df["vol_regime_ok"].fillna(False)
)

# execution: signal at day t's close -> long from day t+1's open to day t+2's open
# (open-to-open return of the next session, aligned back to the signal day)
df["o2o_next"] = df["open"].shift(-2) / df["open"].shift(-1) - 1.0

pos = df["signal"].astype(int)
strat = pos * df["o2o_next"] - pos.diff().abs().fillna(0) * 0.0003

n = strat.notna().sum()
print("long share:", round(pos.mean() * 100, 1), "%")
print("CAGR:", round((1 + strat.dropna()).prod() ** (252 / n) - 1, 4))
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**
