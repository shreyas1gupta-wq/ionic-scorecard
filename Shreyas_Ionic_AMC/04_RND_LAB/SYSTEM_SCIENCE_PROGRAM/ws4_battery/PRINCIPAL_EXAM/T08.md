# T08 — Review request: NIFTY opening gap fade (1-minute data)

Intraday overlay using the vendor 1-minute NIFTY file (tz-aware IST timestamps; the
file includes every print the vendor ships for the session). Previous-day close is
taken from the same file's last bar at or before 15:30.

Reported result: 2022-2026, 388 trades, +0.09% per trade after 1bp/side futures costs,
win rate 58%.

```python
import pandas as pd
from datetime import time

m = pd.read_parquet("nifty_1min.parquet")     # ts (tz-aware IST), open, high, low, close
m["d"] = m["ts"].dt.date
m["t"] = m["ts"].dt.time

prev_close = (m[m["t"] <= time(15, 30)]
              .groupby("d")["close"].last().shift(1))

trades = []
for d, g in m.groupby("d"):
    if d not in prev_close.index or pd.isna(prev_close[d]):
        continue
    g = g.sort_values("ts")
    day_open = g.iloc[0]["open"]              # first print of the session
    gap = day_open / prev_close[d] - 1.0
    if abs(gap) < 0.004:                      # only fade gaps > 0.4%
        continue

    direction = -1 if gap > 0 else 1          # fade the gap
    entry_px = day_open
    exit_row = g[g["t"] >= time(10, 15)].iloc[0]
    exit_px = exit_row["close"]
    trades.append(direction * (exit_px / entry_px - 1.0) - 0.0002)

tr = pd.Series(trades)
print("trades:", len(tr), " mean:", round(tr.mean() * 100, 3), "%",
      " win:", round((tr > 0).mean() * 100, 1), "%")
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**
