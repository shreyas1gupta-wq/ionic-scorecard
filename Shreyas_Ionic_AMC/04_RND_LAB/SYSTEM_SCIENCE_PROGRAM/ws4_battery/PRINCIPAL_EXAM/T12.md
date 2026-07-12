# T12 — Review request: weekly short straddle on F&O bhavcopy

Hold-to-expiry weekly straddle engine on exchange bhavcopy data. Bhavcopy option rows
carry: INSTRUMENT, SYMBOL, EXPIRY_DT, STRIKE_PR, OPTION_TYP, OPEN, HIGH, LOW, CLOSE,
SETTLE_PR, CONTRACTS, OI, TIMESTAMP.

Reported result: 2020-2025, 261 weeks; hit rate 64%; several expiry weeks show
four-digit point losses even on weeks the index barely moved — the author attributes
these to expiry-day pin risk and asks whether to add a stop.

```python
import pandas as pd

fo = load_fo_bhavcopy("NIFTY", "2020-01", "2025-12")

for week in weekly_cycles:
    entry_day = week.first_session          # e.g. Friday after prior expiry
    ref = index_close.asof(entry_day - one_bday)
    k = round_to_strike(ref)                # ATM off prior close

    ce = fo.row(entry_day, week.expiry, k, "CE")
    pe = fo.row(entry_day, week.expiry, k, "PE")
    if ce.CONTRACTS == 0 or pe.CONTRACTS == 0:
        continue                            # only traded strikes at entry
    credit = ce.CLOSE + pe.CLOSE            # sell at entry-day close prints

    # exit at expiry: use the exchange's settlement field on the expiry-day row --
    # SETTLE_PR is the official settlement and avoids stale last-trade CLOSE prints
    ce_x = fo.row(week.expiry, week.expiry, k, "CE").SETTLE_PR
    pe_x = fo.row(week.expiry, week.expiry, k, "PE").SETTLE_PR
    debit = ce_x + pe_x

    book(week, pnl=credit - debit - costs_pts(4))

# summary output:
#   weeks: 261   hit: 64.0%   avg: -118.3 pts
#   worst 5 weeks all land ON expiry dates with |index move| < 0.4%:
#     2023-08-31: -23,912 pts   2021-04-08: -14,466 pts   2024-02-29: -21,880 pts ...
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**
