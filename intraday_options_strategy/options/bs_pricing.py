"""Black-Scholes pricing + Greeks with continuous dividend yield, vectorised.

Implemented manually with scipy.stats.norm per spec. All functions accept
scalars or numpy arrays (broadcasting); time is in YEARS.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

_EPS_T = 1e-8      # floor on time to expiry (years) — avoids div-by-zero
_EPS_SIG = 1e-6    # floor on volatility


def _d1_d2(s: np.ndarray, k: np.ndarray, t: np.ndarray, sigma: np.ndarray,
           r: float, q: float) -> tuple[np.ndarray, np.ndarray]:
    t = np.maximum(t, _EPS_T)
    sigma = np.maximum(sigma, _EPS_SIG)
    vol_t = sigma * np.sqrt(t)
    d1 = (np.log(s / k) + (r - q + 0.5 * sigma**2) * t) / vol_t
    return d1, d1 - vol_t


def bs_price(s, k, t, sigma, r: float, q: float, is_call) -> np.ndarray:
    """European option price. `is_call`: bool or bool array."""
    s, k, t, sigma = map(np.asarray, (s, k, t, sigma))
    is_call = np.asarray(is_call)
    d1, d2 = _d1_d2(s, k, t, sigma, r, q)
    t = np.maximum(t, _EPS_T)
    call = s * np.exp(-q * t) * norm.cdf(d1) - k * np.exp(-r * t) * norm.cdf(d2)
    put = k * np.exp(-r * t) * norm.cdf(-d2) - s * np.exp(-q * t) * norm.cdf(-d1)
    px = np.where(is_call, call, put)
    return np.maximum(px, 0.0)


def implied_vol(price: float, s: float, k: float, t: float, r: float, q: float,
                is_call: bool) -> float:
    """Back out BS implied vol from a market price. NaN if no-arbitrage bounds
    are violated or the solver fails. Brent on [0.5%, 500%] annualised."""
    if t <= 0 or price <= 0:
        return np.nan
    disc_q, disc_r = np.exp(-q * t), np.exp(-r * t)
    intrinsic = max(s * disc_q - k * disc_r, 0.0) if is_call else max(k * disc_r - s * disc_q, 0.0)
    upper = s * disc_q if is_call else k * disc_r
    if price <= intrinsic + 1e-6 or price >= upper - 1e-9:
        return np.nan

    def f(sig: float) -> float:
        return float(bs_price(s, k, t, sig, r, q, is_call)) - price

    try:
        return float(brentq(f, 1e-3, 5.0, maxiter=100, xtol=1e-6))
    except (ValueError, RuntimeError):
        return np.nan


def bs_greeks(s, k, t, sigma, r: float, q: float, is_call) -> dict[str, np.ndarray]:
    """Delta, gamma, theta (PER CALENDAR DAY), vega (per 1 vol point = 0.01)."""
    s, k, t, sigma = map(np.asarray, (s, k, t, sigma))
    is_call = np.asarray(is_call)
    t_f = np.maximum(t, _EPS_T)
    sig = np.maximum(sigma, _EPS_SIG)
    d1, d2 = _d1_d2(s, k, t_f, sig, r, q)
    pdf = norm.pdf(d1)
    disc_q, disc_r = np.exp(-q * t_f), np.exp(-r * t_f)

    delta = np.where(is_call, disc_q * norm.cdf(d1), -disc_q * norm.cdf(-d1))
    gamma = disc_q * pdf / (s * sig * np.sqrt(t_f))
    vega = s * disc_q * pdf * np.sqrt(t_f) / 100.0
    theta_common = -s * disc_q * pdf * sig / (2 * np.sqrt(t_f))
    theta_call = theta_common - r * k * disc_r * norm.cdf(d2) + q * s * disc_q * norm.cdf(d1)
    theta_put = theta_common + r * k * disc_r * norm.cdf(-d2) - q * s * disc_q * norm.cdf(-d1)
    theta = np.where(is_call, theta_call, theta_put) / 365.0
    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega}
