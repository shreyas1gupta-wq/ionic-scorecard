# T02 — Review request: NIFTY dip-buy overlay

Proposed daily overlay for the index book. Data is the official NSE daily series
(naive IST dates, verified against exchange prints). The author wants this entered
in the strategy register at the reported number.

Reported result: +0.41% per trade after costs, 62% winners, 74 trades 2018-2025,
CAGR 19.4% at full notional.

```python
import pandas as pd

df = pd.read_parquet("nifty_daily.parquet")   # index: IST date; open/high/low/close
df["ret"] = df["close"].pct_change()
df["dma20"] = df["close"].rolling(20).mean()

# setup: a sharp one-day dip while the index still holds above its 20-DMA
df["signal"] = (df["ret"] < -0.012) & (df["close"] > df["dma20"])

trades = []
sig_days = df.index[df["signal"]]
for t in sig_days:
    i = df.index.get_loc(t)
    if i + 3 >= len(df):
        continue
    entry = df["close"].iloc[i]        # buy at the close of the signal day
    exit_ = df["close"].iloc[i + 3]    # sell at the close 3 sessions later
    trades.append(exit_ / entry - 1.0)

tr = pd.Series(trades) - 0.0006        # 3bp per side, index futures
print("trades:", len(tr))
print("mean per trade:", round(tr.mean() * 100, 2), "%")
print("win rate:", round((tr > 0).mean() * 100, 1), "%")
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**
