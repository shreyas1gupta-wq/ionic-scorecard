# T02 verification: same-bar execution (T3). The signal needs the day's CLOSE
# (both ret and the close-vs-DMA test), yet the fill is booked AT that same close.
# The dip-day close cannot be bought after observing it; the first implementable
# fill is the next session's open. If any of the bounce happens overnight, the
# same-day-close fill silently pockets it.
# Demo: intraday move m_t drives the signal; the bounce arrives at the NEXT open
# (o_{t+1} = -0.4*m_t + noise). Compare same-day-close entry vs next-open entry.
import numpy as np

rng = np.random.default_rng(11)
n = 6000
m = rng.normal(0, 0.009, n)                  # intraday close-to-close move drivers
o = np.zeros(n)
o[1:] = -0.4 * m[:-1] + rng.normal(0, 0.004, n - 1)   # overnight bounce after dips

close = np.empty(n)
openp = np.empty(n)
close[0], openp[0] = 100.0, 100.0
for t in range(1, n):
    openp[t] = close[t - 1] * (1 + o[t])
    close[t] = openp[t] * (1 + m[t])

ret = np.empty(n); ret[0] = 0.0
ret[1:] = close[1:] / close[:-1] - 1

same_close, next_open = [], []
for t in range(1, n - 3):
    if ret[t] < -0.012:                       # signal known only AT close[t]
        same_close.append(close[t + 3] / close[t] - 1)     # task's fill
        next_open.append(close[t + 3] / openp[t + 1] - 1)  # implementable fill
same_close, next_open = np.array(same_close), np.array(next_open)

print("trades: %d" % len(same_close))
print("same-day-close fill (task): %+.3f%% per trade" % (100 * same_close.mean()))
print("next-open fill (real)     : %+.3f%% per trade" % (100 * next_open.mean()))
assert same_close.mean() - next_open.mean() > 0.002, "defect demo failed"
print("DEFECT CONFIRMED: the same-bar fill pockets the overnight bounce the")
print("trader could never buy; edge collapses at the implementable fill.")
