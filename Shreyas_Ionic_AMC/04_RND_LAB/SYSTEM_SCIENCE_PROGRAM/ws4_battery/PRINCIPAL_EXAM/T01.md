# T01 — Review request: cross-sectional reversal engine

A junior quant proposes a daily mean-reversion sleeve on the F&O universe. Features come
from a vendor daily parquet; execution prices come from the official NSE close panel.
Reported result: Sharpe 2.4 (2021-2025), +0.19% per trade-day after 5bp/side costs.

Data notes supplied with the submission:

- `hf_daily.parquet` — vendor daily OHLCV, one row per symbol-day. The `ts` column is
  tz-aware UTC; bars carry stamps like `2025-03-04 18:30:00+00:00`. `close` is
  split/bonus adjusted (audited).
- `bhav_close.parquet` — official NSE close panel, index = naive IST calendar date,
  columns = symbols. Spot-checked against exchange prints (94.8% exact match).

```python
import pandas as pd

hf = pd.read_parquet("hf_daily.parquet")
hf["date"] = hf["ts"].dt.date
sig_close = hf.pivot(index="date", columns="symbol", values="close").sort_index()

bhav = pd.read_parquet("bhav_close.parquet").sort_index()
ret = bhav.pct_change()                       # official close-to-close returns

# signal input: 1-day return from the vendor panel
rev1 = sig_close.pct_change()
# per-day cross-sectional z-score of the 1-day return
xz = rev1.sub(rev1.mean(axis=1), axis=0).div(rev1.std(axis=1), axis=0)

# at each signal date d: long the 30 most-oversold names
pos = {d: xz.loc[d].nsmallest(30).index for d in xz.index if d in ret.index}

pnl = []
dates = list(ret.index)
for d, names in pos.items():
    i = dates.index(d)
    if i + 2 >= len(dates):
        continue
    entry_d = dates[i + 1]                    # enter at the NEXT session's close
    exit_d = dates[i + 2]                     # exit one session later at close
    held = [n for n in names if n in ret.columns]
    gross = ret.loc[exit_d, held].mean()      # close(entry_d) -> close(exit_d)
    pnl.append(gross - 0.0010)                # 5bp/side round trip

daily = pd.Series(pnl)
print("mean per trade-day:", round(daily.mean() * 100, 3), "%")
print("annualised Sharpe:", round(daily.mean() / daily.std() * 252 ** 0.5, 2))
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**
