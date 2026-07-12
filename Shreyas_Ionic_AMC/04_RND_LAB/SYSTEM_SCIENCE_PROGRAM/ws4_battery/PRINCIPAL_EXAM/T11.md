# T11 — Review request: IV-richness straddle seller

Short-vol entry rule on the index. The raw IV series is noisy day-to-day, so the author
smooths it before testing richness. Data: daily ATM IV series (correct IST dates) plus
verified entry-day straddle prices.

Reported result: 2018-2025, 96 entries, avg +2.1% of premium per trade net, hit 76%.

```python
import pandas as pd

iv = pd.read_parquet("nifty_atm_iv.parquet")["iv"]     # daily ATM IV, %

# de-noise the series before comparing level vs local average
iv_ma = iv.rolling(11, center=True).mean()

rich = iv > 1.15 * iv_ma                # IV rich vs its local average
entry_days = rich & ~rich.shift(1).fillna(False)       # first day of a rich episode

trades = []
for d in iv.index[entry_days]:
    # sell the 1-month ATM straddle at the NEXT session's open,
    # exit at 50% of premium decay or 15 sessions, whichever first
    t = simulate_straddle(entry=next_open(d), exit_rule=("decay50", 15))
    if t is not None:                    # skipped if either leg untraded at entry
        trades.append(t.net_pnl_pct_premium)

tr = pd.Series(trades)
print("entries:", len(tr), " mean:", round(tr.mean(), 2),
      "% of premium  win:", round((tr > 0).mean() * 100, 1), "%")
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**
