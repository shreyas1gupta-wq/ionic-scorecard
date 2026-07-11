"""Black-76 IV solver + greeks for the FnO Replay Game (ROADMAP section 4.6).

Pure math, stdlib only (math.erf for the normal CDF -- no scipy).
Stateless: all caching lives in app.py (per (ci, strike, cp, hm)).
Conventions:
  - price = exp(-rT) * (F*N(d1) - K*N(d2)) for CE; put-call parity for PE
  - theta returned PER CALENDAR DAY (rupee change of premium)
  - vega returned per 1 vol POINT (i.e. sigma +0.01)
  - unsolvable / below-intrinsic marks -> iv None, delta +/-1.0, others 0
ASCII-only (cp1252 console).
"""
import math

R_DEFAULT = 0.065
_SQRT2 = math.sqrt(2.0)
_SQRT2PI = math.sqrt(2.0 * math.pi)


def n_cdf(x):
    return 0.5 * (1.0 + math.erf(x / _SQRT2))


def n_pdf(x):
    return math.exp(-0.5 * x * x) / _SQRT2PI


def intrinsic(F, K, cp):
    return max(0.0, F - K) if cp == "CE" else max(0.0, K - F)


def b76_price(F, K, T, r, sigma, cp):
    """Black-76 forward-based option price with discounting."""
    if F <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return math.exp(-r * max(T, 0.0)) * intrinsic(F, K, cp)
    st = sigma * math.sqrt(T)
    d1 = math.log(F / K) / st + 0.5 * st
    d2 = d1 - st
    df = math.exp(-r * T)
    if cp == "CE":
        return df * (F * n_cdf(d1) - K * n_cdf(d2))
    return df * (K * n_cdf(-d2) - F * n_cdf(-d1))


def solve_iv(mark, F, K, T, r=R_DEFAULT, cp="CE", lo=0.01, hi=5.0, iters=60):
    """Bisection IV in [0.01, 5.0]; None if below intrinsic or unbracketable."""
    if mark is None or mark <= 0 or F <= 0 or K <= 0 or T <= 0:
        return None
    if mark < intrinsic(F, K, cp) - 0.05:
        return None
    if not (b76_price(F, K, T, r, lo, cp) <= mark <= b76_price(F, K, T, r, hi, cp)):
        return None
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if b76_price(F, K, T, r, mid, cp) < mark:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def greeks(F, K, T, r, sigma, cp):
    """Greeks from a solved sigma. delta signed (put negative), gamma wrt F,
    theta per calendar day (rupees of premium), vega per 1 vol point."""
    st = sigma * math.sqrt(T)
    df = math.exp(-r * T)
    d1 = math.log(F / K) / st + 0.5 * st
    d2 = d1 - st
    if cp == "CE":
        delta = df * n_cdf(d1)
        price = df * (F * n_cdf(d1) - K * n_cdf(d2))
    else:
        delta = -df * n_cdf(-d1)
        price = df * (K * n_cdf(-d2) - F * n_cdf(-d1))
    gamma = df * n_pdf(d1) / (F * st)
    vega = df * F * n_pdf(d1) * math.sqrt(T) / 100.0
    theta = (r * price - df * F * n_pdf(d1) * sigma / (2.0 * math.sqrt(T))) / 365.0
    return dict(delta=round(delta, 4), gamma=round(gamma, 6),
                theta=round(theta, 2), vega=round(vega, 2))


def solve(mark, F, K, T, r=R_DEFAULT, cp="CE"):
    """IV + greeks bundle. iv is the raw sigma (decimal), or None when the mark
    is below intrinsic-0.05 or the bisection cannot bracket it (then delta=+/-1)."""
    iv = solve_iv(mark, F, K, T, r, cp)
    if iv is None:
        return dict(iv=None, delta=1.0 if cp == "CE" else -1.0,
                    gamma=0.0, theta=0.0, vega=0.0)
    g = greeks(F, K, T, r, iv, cp)
    g["iv"] = iv
    return g
