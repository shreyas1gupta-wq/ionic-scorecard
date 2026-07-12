# T08 verification: the first print of the session is the 09:00 pre-open AUCTION
# bar, not the 09:15 continuous-session open. Two effects:
#  1) the gap is measured off the auction print (wrong classification on the days
#     where auction deviates from the real open), and
#  2) the fade is FILLED at the auction print -- a price that does not exist in
#     the continuous session. Any auction-vs-open deviation becomes instant fake
#     P&L for the fade (short the inflated print, "revert" to the real open).
import numpy as np

rng = np.random.default_rng(5)
n = 1500
prev_close = 100.0 * np.ones(n)
true_gap = rng.normal(0, 0.006, n)                 # real overnight gap
open_915 = prev_close * (1 + true_gap)             # real continuous-session open
auction_dev = rng.normal(0, 0.0025, n)             # auction print deviation
open_900 = open_915 * (1 + auction_dev)            # what .iloc[0] returns
drift_to_1015 = rng.normal(0, 0.004, n)            # zero-edge market afterwards
px_1015 = open_915 * (1 + drift_to_1015)

def fade(open_used):
    pnl, n_tr = [], 0
    for i in range(n):
        gap = open_used[i] / prev_close[i] - 1
        if abs(gap) < 0.004:
            continue
        d = -1 if gap > 0 else 1
        pnl.append(d * (px_1015[i] / open_used[i] - 1))
        n_tr += 1
    return np.array(pnl), n_tr

pnl_naive, k_naive = fade(open_900)     # task's engine
pnl_true, k_true = fade(open_915)       # correct engine

flips = np.sum((np.abs(open_900 / prev_close - 1) >= 0.004)
               != (np.abs(open_915 / prev_close - 1) >= 0.004))
print("trades naive=%d true=%d | signal-classification flips: %d days" %
      (k_naive, k_true, flips))
print("fade edge using 09:00 auction print: %+.3f%%/trade" % (100 * pnl_naive.mean()))
print("fade edge using real 09:15 open    : %+.3f%%/trade" % (100 * pnl_true.mean()))
assert pnl_naive.mean() > pnl_true.mean() + 0.0005, "defect demo failed"
print("DEFECT CONFIRMED: on a zero-edge market the auction-print engine still shows")
print("a positive fade edge -- it is trading a price unavailable after 09:15.")
print("Fix: filter bars to t >= 09:15; real open = first bar of continuous session.")
