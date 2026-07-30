"""Dev: hand-vectorized BS delta (numpy + scipy.stats.norm) for strike selection, per
options-python-libs skill guidance (py_vollib_vectorized is broken on this stack)."""
from __future__ import annotations
import numpy as np
from scipy.stats import norm


def bs_delta(S, K, T, r, sigma, is_call):
    """Vectorized Black-Scholes delta. S,K,T,sigma arrays or scalars; is_call bool array."""
    S = np.asarray(S, float); K = np.asarray(K, float)
    T = np.maximum(np.asarray(T, float), 1.0 / 365 / 24)   # floor at 1 trading hour
    sigma = np.maximum(np.asarray(sigma, float), 0.01)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    call_delta = norm.cdf(d1)
    return np.where(is_call, call_delta, call_delta - 1.0)


if __name__ == "__main__":
    # anchor check vs vollib: S=K=100 t=0.25 r=5% sigma=20% -> delta 0.5695 / -0.4305
    print(bs_delta(100, 100, 0.25, 0.05, 0.20, True))
    print(bs_delta(100, 100, 0.25, 0.05, 0.20, False))
    # NIFTY-scale sanity: spot 20000, weekly 3DTE, VIX 14
    strikes = np.arange(19500, 20600, 50)
    d_ce = bs_delta(20000, strikes, 3/365, 0.0, 0.14, True)
    for k, d in zip(strikes, d_ce):
        print(k, round(float(d), 3))
