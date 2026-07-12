# T06 — Review request: monthly NIFTY short strangle

Backtest of the flagship short-vol candidate. Option chain data is verified entry-day
prices (volume>0 enforced on both legs); spot is the official index close series.
The spot/chain dataset runs through 2026-06-30.

Reported result: 90 cycles 2019-01 to 2026-07, hit rate 84%, avg +41 pts/cycle,
worst cycle -412 pts.

```python
import pandas as pd

spot = load_spot_series()                  # official index closes, through 2026-06-30
chain = load_entry_chains()                # entry-day option prices, volume>0 verified

expiries = monthly_expiry_calendar("2019-01", "2026-07")   # exchange calendar

results = []
for exp in expiries:
    entry_day = last_trading_day_on_or_before(exp - pd.Timedelta(days=45))
    ref = spot.asof(entry_day - pd.Timedelta(days=1))      # prior close for strikes
    ce_k = round_to_strike(ref * 1.03)
    pe_k = round_to_strike(ref * 0.97)

    prem = chain.price(entry_day, exp, ce_k, "CE") + \
           chain.price(entry_day, exp, pe_k, "PE")         # entry-day close prints

    settle_spot = spot.asof(exp)                            # settlement level
    payoff = max(settle_spot - ce_k, 0) + max(pe_k - settle_spot, 0)

    pnl = prem - payoff - COSTS_PTS                         # 4.5 pts/cycle all-in
    results.append({"expiry": exp, "pnl": pnl, "win": pnl > 0})

r = pd.DataFrame(results)
print("cycles:", len(r), " hit rate:", round(r["win"].mean() * 100, 1), "%")
print("avg pnl:", round(r["pnl"].mean(), 1), "pts   worst:", round(r["pnl"].min(), 1))
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**
