# T09 verification: shift SIGN error. Every feature is evaluated at day t's close
# except adv_dec, which is shift(-1) = the breadth of day t+1 -- the very session
# (open t+1 -> open t+2) the position holds. The signal "confirms" with a number
# measured over the session it is about to trade.
# Demo: breadth is contemporaneous with the session's return by construction
# (broad up-days ARE up-days). shift(-1) turns that into a money machine on a
# zero-edge market; shift(0)/shift(+1) (implementable) earns ~nothing.
import numpy as np
import pandas as pd

rng = np.random.default_rng(3)
n = 5000
sess_ret = rng.normal(0.0003, 0.01, n)             # day-session open->open ~ zero edge
# breadth ratio: strongly tied to the same session's return + noise
adv_dec = np.exp(2.5 + 45 * sess_ret + rng.normal(0, 0.35, n)) / np.exp(2.5)

df = pd.DataFrame({"sess_ret": sess_ret, "adv_dec": adv_dec})
# task alignment: signal day t holds session t+1; adv_dec.shift(-1) at t = breadth of t+1
df["leaked"] = df["adv_dec"].shift(-1)
df["lagged"] = df["adv_dec"]                       # knowable at t close (implementable)
df["hold_ret"] = df["sess_ret"].shift(-1)          # session t+1 return, aligned to t

leak = df.loc[df["leaked"] > 1.5, "hold_ret"].dropna()
fair = df.loc[df["lagged"] > 1.5, "hold_ret"].dropna()
print("signal with shift(-1) (task) : %+.3f%%/day on %d days"
      % (100 * leak.mean(), len(leak)))
print("signal with lagged breadth   : %+.3f%%/day on %d days"
      % (100 * fair.mean(), len(fair)))
assert leak.mean() > fair.mean() + 0.003, "defect demo failed"
print("DEFECT CONFIRMED: .shift(-1) feeds the held session's own breadth into the")
print("entry decision; the edge is fabricated. Fix: use day t's (or t-1's) breadth --")
print("shift(0)/shift(+1) -- and greps for '.shift(-' on features should be standing.")
