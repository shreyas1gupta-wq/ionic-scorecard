# T11 verification: rolling(11, center=True) averages 5 FUTURE sessions into the
# smoother. "IV above 1.15x its local average" then preferentially fires at local
# IV PEAKS -- identifiable as peaks only because the window saw IV fall afterwards.
# A short-vol entry conditioned on that is selling tops with hindsight.
# Demo: mean-reverting (OU) IV; payoff proxy = subsequent 10-session IV change
# (short vol profits when IV falls). Centered vs trailing smoother.
import numpy as np
import pandas as pd

rng = np.random.default_rng(17)
n = 6000
iv = np.empty(n); iv[0] = 16.0
for t in range(1, n):
    iv[t] = iv[t - 1] + 0.05 * (16.0 - iv[t - 1]) + rng.normal(0, 0.9)
iv = pd.Series(np.clip(iv, 8, None))

def edge(centered):
    ma = iv.rolling(11, center=centered).mean()
    rich = iv > 1.10 * ma
    entry = rich & ~rich.shift(1).fillna(False)
    fwd = iv.shift(-10) - iv                 # IV change over next 10 sessions
    picks = fwd[entry.fillna(False)].dropna()
    return picks.mean(), len(picks)

e_center, n_center = edge(True)     # task's smoother
e_trail, n_trail = edge(False)      # implementable smoother

print("centered MA (task) : mean 10d IV change after entry %+.2f vols (%d entries)"
      % (e_center, n_center))
print("trailing MA (real) : mean 10d IV change after entry %+.2f vols (%d entries)"
      % (e_trail, n_trail))
assert e_center < e_trail - 0.3, "defect demo failed"
print("DEFECT CONFIRMED: the centered window needs 5 future sessions; it marks")
print("entries at hindsight IV peaks, manufacturing post-entry IV collapse.")
print("Fix: rolling(..., center=False) (trailing window), re-run the battery.")
