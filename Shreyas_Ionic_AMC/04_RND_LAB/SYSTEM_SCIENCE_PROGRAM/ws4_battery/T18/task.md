# T18 — Review request: paper-book fill audit script

Script that audits whether last week's 501 paper entries (options legs, NFO) could
actually have been filled, by pulling daily candles from the broker API and checking
the entry day's traded volume. The broker's daily (ONE_DAY) candles are known to be
stamped at 00:00 IST.

Observed output: **all 501 legs flagged UNFILLABLE (no entry-day bar / zero volume)**,
including deep-liquid ATM NIFTY weeklies. The author concludes the paper book was
untradeable and recommends voiding the week's paper results.

```python
import time

def audit_leg(smart, leg):
    params = {
        "exchange": "NFO",
        "symboltoken": leg.token,
        "interval": "ONE_DAY",
        "fromdate": leg.entry_date.strftime("%Y-%m-%d") + " 09:15",
        "todate": (leg.entry_date + pd.Timedelta(days=5)).strftime("%Y-%m-%d") + " 15:30",
    }
    candles = smart.getCandleData(params)["data"]     # [[ts, o, h, l, c, vol], ...]
    time.sleep(1.3)                                   # rate-limit compliance

    entry_bar = None
    for c in candles or []:
        if c[0][:10] == leg.entry_date.strftime("%Y-%m-%d"):
            entry_bar = c
            break

    if entry_bar is None or entry_bar[5] == 0:
        return "UNFILLABLE"
    if entry_bar[5] * lot_value(leg) < 20 * leg.intended_notional:
        return "THIN"
    return "OK"

results = [audit_leg(smart, leg) for leg in paper_legs]
print(pd.Series(results).value_counts())
# UNFILLABLE    501
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**
