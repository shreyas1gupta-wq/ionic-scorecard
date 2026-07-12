# T07 — Review request: NIFTY weekly iron condor on F&O bhavcopy

Weekly defined-risk premium sleeve built on exchange bhavcopy (daily EOD rows:
OPEN/HIGH/LOW/CLOSE/SETTLE_PR/CONTRACTS/OI per contract). Underlying settlement uses
the official index close series.

Reported result: 2021-2025, 224 weeks traded, 31 skipped; avg +6.1 pts/week net,
hit rate 71%, worst week -312 pts (wings capped it).

```python
import pandas as pd

fo = load_fo_bhavcopy("NIFTY", "2021-01", "2025-12")   # option rows, daily EOD
idx_close = load_index_close()                          # official index closes

for tuesday in weekly_anchor_days:
    # --- decision, made after Tuesday's close on Tuesday data ---
    ref = idx_close.asof(tuesday)
    legs = {
        "sc": ("CE", round_to_strike(ref * 1.015)),
        "sp": ("PE", round_to_strike(ref * 0.985)),
        "lc": ("CE", round_to_strike(ref * 1.030)),
        "lp": ("PE", round_to_strike(ref * 0.970)),
    }
    # expiry: nearest weekly where ALL four legs traded on Tuesday (CONTRACTS > 0);
    # if none qualifies, fall back to the current monthly
    expiry = pick_expiry(fo, tuesday, legs, require_contracts=True)
    if expiry is None:
        skip("no liquid expiry"); continue

    # --- execution: Wednesday, fill at each leg's bhavcopy OPEN ---
    rows = fo.rows(date=tuesday + one_bday, expiry=expiry, legs=legs)
    if any(r.OPEN <= 0 or r.CONTRACTS == 0 for r in rows.values()):
        skip("leg not traded on entry day"); continue    # conservative no-fill
    credit = (rows["sc"].OPEN + rows["sp"].OPEN
              - rows["lc"].OPEN - rows["lp"].OPEN)
    credit -= slippage_ticks(4) + costs_pts()            # per-leg tick + charges

    # --- exit: hold to expiry, cash-settle at intrinsic from the INDEX close ---
    settle = idx_close.asof(expiry)
    payoff = (max(settle - legs["sc"][1], 0) - max(settle - legs["lc"][1], 0)
              + max(legs["sp"][1] - settle, 0) - max(legs["lp"][1] - settle, 0))
    book(week=tuesday, pnl=credit - payoff)

# guards: expiry <= idx_close.index.max() asserted inside pick_expiry;
# weeks with a scheduled major event (budget, RBI, election result) are skipped
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**
