# T06 verification: settlement beyond the end of data (T8 / guard-L7 class).
# Data ends 2026-06-30 but the expiry loop runs to Jul-2026. For that cycle,
# spot.asof(expiry) silently returns the LAST AVAILABLE close, so the strangle
# "expires" near the level it was sold at: a certain, near-full-premium win is
# booked for a position whose true outcome is still UNKNOWN.
# Demo: history ends at the cut; the cycle's expiry lies beyond it. The backtest
# books one fixed number; Monte-Carlo continuation of the same process shows the
# true outcome is a DISTRIBUTION with a fat loss tail. Booking the certain win
# is fabrication, independent of which continuation happens.
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
n_hist = 480
px = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.01, n_hist)),
               index=pd.date_range("2024-01-01", periods=n_hist, freq="B"))
data_end = px.index[-1]

expiry = data_end + pd.Timedelta(days=30)          # expires ~1 month past the data
entry = expiry - pd.Timedelta(days=45)             # entry inside the data window
ref = px.asof(entry)
ce_k, pe_k = ref * 1.03, ref * 0.97
prem = ref * 0.015                                  # 1.5%-of-spot premium

# --- what the task's engine books ---
settle_stale = px.asof(expiry)                      # .asof past the end -> last close
booked = prem - max(settle_stale - ce_k, 0) - max(pe_k - settle_stale, 0)

# --- what reality can still do: simulate the unseen 21 sessions 5000 times ---
unseen = 21
last = px.iloc[-1]
finals = last * np.cumprod(1 + rng.normal(0, 0.01, (5000, unseen)), axis=1)[:, -1]
payoff = np.maximum(finals - ce_k, 0) + np.maximum(pe_k - finals, 0)
true_pnl = prem - payoff

print("cycle expiring %s vs data ending %s" % (expiry.date(), data_end.date()))
print("backtest books (stale .asof settle): %+8.2f pts  (a certain 'win')" % booked)
print("true outcome distribution          : mean %+8.2f | P(loss) %.0f%% | worst %+8.2f"
      % (true_pnl.mean(), 100 * (true_pnl < 0).mean(), true_pnl.min()))
assert booked > 0.9 * prem, "engine did not book the near-full-premium fake win"
assert (true_pnl < 0).mean() > 0.10 and true_pnl.min() < -prem, "no real risk shown"
assert booked > true_pnl.mean(), "booked win does not overstate the true expectation"
print("DEFECT CONFIRMED: the engine settles a cycle whose expiry is beyond")
print("max(data) at a stale spot, converting an open, risky position into a")
print("certain booked win. Same class as the S-04 incident (84 fabricated wins).")
print("Fix: assert expiry <= spot.index.max(); drop or report such cycles as OPEN.")
