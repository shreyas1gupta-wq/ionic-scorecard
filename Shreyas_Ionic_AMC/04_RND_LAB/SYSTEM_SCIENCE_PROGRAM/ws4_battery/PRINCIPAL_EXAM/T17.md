# T17 — Review request: calendar-spread timing engine

Monthly options calendar-spread family. The signal `ff` (front-back richness per unit
spot) is computed once per day from that day's settlement prints; higher `ff` = better
entry pricing for the spread. The question the engine answers: "which day inside the
T-30..T-10 window should we enter each cycle?"

Reported result: 2019-2026, 86 cycles, +7.2 pts avg per cycle net, hit 69%.

```python
import pandas as pd

cycles = build_monthly_cycles("2019-01", "2026-06")    # expiry calendar
ff = load_ff_series()          # daily: date, lead (days to expiry), ff value

results = []
for cyc in cycles:
    win = ff[(ff["expiry"] == cyc.expiry)
             & (ff["lead"] >= 10) & (ff["lead"] <= 30)]
    if len(win) < 8:
        continue

    # enter where the window's pricing is best
    best = win.loc[win["ff"].idxmax()]
    entry_day = next_session(best["date"])             # fill at next session's open

    spread = open_calendar_spread(entry_day, cyc.expiry,
                                  legs="near_short_far_long",
                                  liquidity="both_legs_traded_else_skip")
    if spread is None:
        continue
    pnl = close_at_lead(spread, lead=2)                # exit T-2, verified prints
    results.append(pnl - costs_pts(2))

r = pd.Series(results)
print("cycles:", len(r), " avg:", round(r.mean(), 1), "pts  hit:",
      round((r > 0).mean() * 100, 1), "%")
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**
