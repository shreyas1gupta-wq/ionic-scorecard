"""Tiny BS/IV/delta helpers, copied verbatim (not rewritten) from
GATED_BUYING_20260730/gated_buying.py lines 70-96, so we don't import that script's module-level
side effects (it runs a full pipeline on import). r=0.065 per firm convention.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

R = 0.065


def bs(S, K, T, sig, typ):
    if T <= 0 or sig <= 0:
        return max(0.0, (S - K) if typ == "CE" else (K - S))
    d1 = (np.log(S / K) + (R + 0.5 * sig * sig) * T) / (sig * np.sqrt(T))
    d2 = d1 - sig * np.sqrt(T)
    if typ == "CE":
        return S * norm.cdf(d1) - K * np.exp(-R * T) * norm.cdf(d2)
    return K * np.exp(-R * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def iv_of(px, S, K, T, typ):
    if px <= 0.05 or T <= 0:
        return np.nan
    intr = max(0.0, (S - K) if typ == "CE" else (K - S))
    if px < intr - 0.01:
        return np.nan
    try:
        return brentq(lambda s: bs(S, K, T, s, typ) - px, 1e-4, 5.0, maxiter=80, xtol=1e-6)
    except Exception:
        return np.nan


def delta_of(S, K, T, sig, typ):
    if T <= 0 or not np.isfinite(sig) or sig <= 0:
        return 1.0 if ((typ == "CE" and S > K) or (typ == "PE" and S < K)) else 0.0
    d1 = (np.log(S / K) + (R + 0.5 * sig * sig) * T) / (sig * np.sqrt(T))
    return float(norm.cdf(d1)) if typ == "CE" else float(norm.cdf(d1) - 1.0)
