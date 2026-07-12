# T15 verification: normalization leakage (T6). mu and sd are computed over the
# FULL 2015-2025 sample -- a decision taken in 2016 uses a mean/std that already
# contain the 2020 COVID spike and the post-2020 regime. Both the entry threshold
# (z>1) and the crash filter (z<2.5) are calibrated with future information.
# Demo: IV with a regime break. Compare entry sets and a short-vol payoff proxy
# under full-sample z vs trailing-252d z (implementable).
import numpy as np
import pandas as pd

rng = np.random.default_rng(23)
n = 2600
base = np.where(np.arange(n) < 1300, 13.0, 21.0)      # regime break mid-sample
spike = np.zeros(n); spike[1250:1300] = np.linspace(0, 30, 50)  # crash episode
iv = pd.Series(base + spike + np.abs(rng.normal(0, 2.0, n)))

# full-sample z (task)
z_full = (iv - iv.mean()) / iv.std()
# trailing z (implementable): stats through YESTERDAY only
mu_tr = iv.rolling(252).mean().shift(1)
sd_tr = iv.rolling(252).std().shift(1)
z_trail = (iv - mu_tr) / sd_tr

e_full = (z_full > 1.0) & (z_full < 2.5)
e_trail = (z_trail > 1.0) & (z_trail < 2.5)

# short-vol payoff proxy: profit ~ IV decline over next 5 sessions
fwd = -(iv.shift(-5) - iv)
p_full = fwd[e_full].dropna()
p_trail = fwd[e_trail].dropna()

both = (e_full & e_trail).sum()
print("entries full-sample z: %d | trailing z: %d | overlap: %d"
      % (e_full.sum(), e_trail.sum(), both))
print("payoff proxy full-sample z (task): %+.2f vols/trade" % p_full.mean())
print("payoff proxy trailing z (real)   : %+.2f vols/trade" % p_trail.mean())
first_half = e_full[:1300].sum(), e_trail[:1300].sum()
print("entries in the FIRST regime: full=%d trailing=%d" % first_half)
assert both < 0.7 * max(e_full.sum(), e_trail.sum()), "entry sets barely differ"
assert p_full.mean() != p_trail.mean()
print("DEFECT CONFIRMED: the two rules trade materially different entry sets --")
print("the backtested rule is calibrated on statistics unknowable at trade time")
print("(pre-break entries are suppressed/selected using the post-break mean).")
print("Fix: trailing-window or expanding-lagged stats; audit_full_sample_stats().")
