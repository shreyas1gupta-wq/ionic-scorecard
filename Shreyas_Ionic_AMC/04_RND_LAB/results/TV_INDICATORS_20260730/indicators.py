"""TradingView-style indicator families, hand-rolled (no TA-Lib dependency on this locked-down
laptop). Each `sig_*` function takes `bars` (columns o,h,l,c indexed by the bar's own CLOSE
timestamp, continuous multi-day series -- realistic TradingView behaviour, indicators are NOT
reset each morning) and returns an entries DataFrame(t, dir) with dir=+1 long / -1 short,
restricted to TOD_START..TOD_END so every entry has room to reach 15:25.

Standard textbook default parameters only -- ONE parameterization per family, no param sweep.
Sweeping params per family is exactly the "100 correlated variants" failure mode the firm's
breadth protocol warns against (SHARED_CONTEXT_20260729 SS4); prefer orthogonal families.

Signals are CROSSING/EVENT triggers (not "is-in-state" conditions) throughout, so a family
fires a discrete, countable number of times rather than clustering on every bar of an extended
state -- this matters for an honest trades/month figure.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lib_signals import TOD_START, TOD_END

# --------------------------------------------------------------------------- generic helpers


def _ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def _sma(s, n):
    return s.rolling(n).mean()


def _wilder(s, n):
    return s.ewm(alpha=1 / n, adjust=False).mean()


def true_range(h, l, c):
    pc = c.shift(1)
    return pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)


def atr(h, l, c, n=14):
    return _wilder(true_range(h, l, c), n)


def rsi(c, n=14):
    delta = c.diff()
    up = delta.clip(lower=0)
    dn = -delta.clip(upper=0)
    rs = _wilder(up, n) / _wilder(dn, n).replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def crossover(a, b):
    if np.isscalar(b):
        b = pd.Series(b, index=a.index)
    return (a > b) & (a.shift(1) <= b.shift(1))


def crossunder(a, b):
    if np.isscalar(b):
        b = pd.Series(b, index=a.index)
    return (a < b) & (a.shift(1) >= b.shift(1))


def wma(s, n):
    w = np.arange(1, n + 1, dtype=float)
    return s.rolling(n).apply(lambda x: np.dot(x, w) / w.sum(), raw=True)


def hma(s, n=21):
    half, sq = max(int(n / 2), 1), max(int(np.sqrt(n)), 1)
    return wma(2 * wma(s, half) - wma(s, n), sq)


def choppiness(bars, n=14):
    tr = true_range(bars.h, bars.l, bars.c)
    sum_tr = tr.rolling(n).sum()
    rng = bars.h.rolling(n).max() - bars.l.rolling(n).min()
    return 100 * np.log10(sum_tr / rng.replace(0, np.nan)) / np.log10(n)


def efficiency_ratio(c, n=10):
    return (c - c.shift(n)).abs() / c.diff().abs().rolling(n).sum().replace(0, np.nan)


def _tod_ok(index):
    t = index.time
    return (t >= TOD_START) & (t <= TOD_END)


def make_entries(bull_mask: pd.Series, bear_mask: pd.Series, index) -> pd.DataFrame:
    ok = _tod_ok(index)
    bm = bull_mask.fillna(False).to_numpy() & ok
    sm = bear_mask.fillna(False).to_numpy() & ok
    rows = [{"t": t, "dir": 1} for t in index[bm]] + [{"t": t, "dir": -1} for t in index[sm]]
    if not rows:
        return pd.DataFrame(columns=["t", "dir"])
    return pd.DataFrame(rows).sort_values("t").reset_index(drop=True)


# --------------------------------------------------------------------------- Supertrend (used
# only as an internal filter for combo A -- standalone Supertrend was already measured in
# EMA_INTRADAY_BUYING_20260729 signal_budget (t=1.80-2.76 across 3 variants), not re-run here).
def _calc_supertrend(bars, n=10, mult=3.0):
    h, l, c = bars.h, bars.l, bars.c
    a = atr(h, l, c, n)
    hl2 = (h + l) / 2
    ub, lb = (hl2 + mult * a).to_numpy(), (hl2 - mult * a).to_numpy()
    cl = c.to_numpy()
    st = np.zeros(len(c))
    d = np.ones(len(c), dtype=int)
    first = np.argmax(np.isfinite(lb))
    st[first] = lb[first] if np.isfinite(lb[first]) else 0.0
    for i in range(first + 1, len(c)):
        if not (np.isfinite(ub[i]) and np.isfinite(lb[i])):
            st[i], d[i] = st[i - 1], d[i - 1]
            continue
        fub = ub[i] if (ub[i] < st[i - 1] or cl[i - 1] > st[i - 1]) else st[i - 1]
        flb = lb[i] if (lb[i] > st[i - 1] or cl[i - 1] < st[i - 1]) else st[i - 1]
        if d[i - 1] == 1:
            d[i], st[i] = (-1, fub) if cl[i] < flb else (1, flb)
        else:
            d[i], st[i] = (1, flb) if cl[i] > fub else (-1, fub)
    return pd.Series(d, index=c.index)


# --------------------------------------------------------------------------- single families

def sig_keltner(bars, n=20, atr_n=10, mult=2.0):
    """Keltner Channel breakout: close crosses outside EMA(n) +/- mult*ATR(atr_n)."""
    mid = _ema(bars.c, n)
    a = atr(bars.h, bars.l, bars.c, atr_n)
    upper, lower = mid + mult * a, mid - mult * a
    return make_entries(crossover(bars.c, upper), crossunder(bars.c, lower), bars.index)


def sig_donchian(bars, n=20):
    """Donchian breakout: close breaks the PRIOR n-bar high/low (current bar excluded)."""
    hh = bars.h.rolling(n).max().shift(1)
    ll = bars.l.rolling(n).min().shift(1)
    above, below = bars.c > hh, bars.c < ll
    bull = above & ~above.shift(1).fillna(False)
    bear = below & ~below.shift(1).fillna(False)
    return make_entries(bull, bear, bars.index)


def sig_squeeze_release(bars, n=20, bb_k=2.0, kc_mult=1.5, mom_lb=20):
    """Squeeze Momentum / TTM Squeeze (LazyBear/Carter): BB(n) inside KC(n,kc_mult) = squeeze
    ON; direction at RELEASE from sign(close - close[mom_lb bars ago]) -- a simplified but
    faithful proxy for the indicator's linreg-momentum value (documented simplification, not a
    claim of exact LazyBear replication)."""
    c = bars.c
    basis, dev = _sma(c, n), c.rolling(n).std()
    bb_u, bb_l = basis + bb_k * dev, basis - bb_k * dev
    a = atr(bars.h, bars.l, c, n)
    kc_u, kc_l = basis + kc_mult * a, basis - kc_mult * a
    squeeze_on = (bb_l > kc_l) & (bb_u < kc_u)
    release = (~squeeze_on) & squeeze_on.shift(1).fillna(False)
    mom = c - c.shift(mom_lb)
    return make_entries(release & (mom > 0), release & (mom < 0), bars.index)


def sig_stochrsi(bars, rsi_n=14, stoch_n=14, smooth=3, lo=20, hi=80):
    r = rsi(bars.c, rsi_n)
    rmin, rmax = r.rolling(stoch_n).min(), r.rolling(stoch_n).max()
    st = (r - rmin) / (rmax - rmin).replace(0, np.nan) * 100
    k = _sma(st, smooth)
    return make_entries(crossover(k, lo), crossunder(k, hi), bars.index)


def sig_cci(bars, n=20, lo=-100, hi=100):
    tp = (bars.h + bars.l + bars.c) / 3
    sma = _sma(tp, n)
    mad = tp.rolling(n).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    cci = (tp - sma) / (0.015 * mad.replace(0, np.nan))
    return make_entries(crossover(cci, lo), crossunder(cci, hi), bars.index)


def sig_williams_r(bars, n=14, lo=-80, hi=-20):
    hh, ll = bars.h.rolling(n).max(), bars.l.rolling(n).min()
    wr = (hh - bars.c) / (hh - ll).replace(0, np.nan) * -100
    return make_entries(crossover(wr, lo), crossunder(wr, hi), bars.index)


def sig_elder_ray(bars, n=13):
    """Elder's classic rule: buy when EMA13 is rising and Bear Power (low-EMA13) is negative
    but turning up; mirror for sell (bull power falling in a downtrend)."""
    ema = _ema(bars.c, n)
    bull_pow, bear_pow = bars.h - ema, bars.l - ema
    up, dn = ema > ema.shift(1), ema < ema.shift(1)
    bull = up & (bear_pow < 0) & (bear_pow > bear_pow.shift(1))
    bear = dn & (bull_pow > 0) & (bull_pow < bull_pow.shift(1))
    return make_entries(bull, bear, bars.index)


def sig_vortex(bars, n=14):
    h, l, c = bars.h, bars.l, bars.c
    vm_p = (h - l.shift(1)).abs()
    vm_m = (l - h.shift(1)).abs()
    tr_sum = true_range(h, l, c).rolling(n).sum().replace(0, np.nan)
    vip, vim = vm_p.rolling(n).sum() / tr_sum, vm_m.rolling(n).sum() / tr_sum
    return make_entries(crossover(vip, vim), crossunder(vip, vim), bars.index)


def sig_aroon(bars, n=25):
    h, l = bars.h, bars.l
    up = 100 * (n - h.rolling(n + 1).apply(lambda x: n - np.argmax(x), raw=True)) / n
    dn = 100 * (n - l.rolling(n + 1).apply(lambda x: n - np.argmin(x), raw=True)) / n
    return make_entries(crossover(up, dn), crossunder(up, dn), bars.index)


def sig_ichimoku(bars, tenkan_n=9, kijun_n=26, senkou_n=52):
    h, l, c = bars.h, bars.l, bars.c
    tenkan = (h.rolling(tenkan_n).max() + l.rolling(tenkan_n).min()) / 2
    kijun = (h.rolling(kijun_n).max() + l.rolling(kijun_n).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(kijun_n)
    senkou_b = ((h.rolling(senkou_n).max() + l.rolling(senkou_n).min()) / 2).shift(kijun_n)
    top = pd.concat([senkou_a, senkou_b], axis=1).max(axis=1)
    bot = pd.concat([senkou_a, senkou_b], axis=1).min(axis=1)
    bull = crossover(tenkan, kijun) & (c > top)
    bear = crossunder(tenkan, kijun) & (c < bot)
    return make_entries(bull, bear, bars.index)


def sig_connors_rsi(bars, rsi_n=3, streak_n=2, rank_n=100, lo=10, hi=90):
    c = bars.c
    r1 = rsi(c, rsi_n)
    chg = c.diff().to_numpy()
    streak = np.zeros(len(c))
    s = 0
    for i in range(1, len(chg)):
        if chg[i] > 0:
            s = s + 1 if s >= 0 else 1
        elif chg[i] < 0:
            s = s - 1 if s <= 0 else -1
        else:
            s = 0
        streak[i] = s
    r2 = rsi(pd.Series(streak, index=c.index), streak_n)
    roc1 = c.pct_change()
    rank = roc1.rolling(rank_n).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100, raw=False)
    crsi = (r1 + r2 + rank) / 3
    return make_entries(crossover(crsi, lo), crossunder(crsi, hi), bars.index)


def sig_rvi(bars, n=10):
    o, h, l, c = bars.o, bars.h, bars.l, bars.c
    num = (c - o) + 2 * (c.shift(1) - o.shift(1)) + 2 * (c.shift(2) - o.shift(2)) + (c.shift(3) - o.shift(3))
    den = (h - l) + 2 * (h.shift(1) - l.shift(1)) + 2 * (h.shift(2) - l.shift(2)) + (h.shift(3) - l.shift(3))
    rvi = _sma(num, n) / _sma(den, n).replace(0, np.nan)
    sig = (rvi + 2 * rvi.shift(1) + 2 * rvi.shift(2) + rvi.shift(3)) / 6
    return make_entries(crossover(rvi, sig), crossunder(rvi, sig), bars.index)


def sig_kst(bars):
    c = bars.c

    def roc(n):
        return c.pct_change(n) * 100
    kst = (_sma(roc(10), 10) * 1 + _sma(roc(15), 10) * 2 + _sma(roc(20), 10) * 3
           + _sma(roc(30), 15) * 4)
    sig = _sma(kst, 9)
    return make_entries(crossover(kst, sig), crossunder(kst, sig), bars.index)


def sig_hma(bars, n=21):
    h = hma(bars.c, n)
    slope = h.diff()
    bull = (slope > 0) & (slope.shift(1) <= 0)
    bear = (slope < 0) & (slope.shift(1) >= 0)
    return make_entries(bull, bear, bars.index)


def sig_fractal_breakout(bars, k=2):
    """Williams fractal (k=2 -> 5-bar). A fractal needs k bars AFTER it to confirm, so the
    level is only usable k bars later (shift(k)) -- no lookahead."""
    h, l = bars.h, bars.l
    is_fh = pd.Series(True, index=h.index)
    is_fl = pd.Series(True, index=l.index)
    for i in range(1, k + 1):
        is_fh &= (h > h.shift(i)) & (h > h.shift(-i))
        is_fl &= (l < l.shift(i)) & (l < l.shift(-i))
    last_fh = h.where(is_fh).shift(k).ffill()
    last_fl = l.where(is_fl).shift(k).ffill()
    return make_entries(crossover(bars.c, last_fh), crossunder(bars.c, last_fl), bars.index)


# --------------------------------------------------------------------------- combos (2-3 as
# suggested in the brief: squeeze-release direction confirmed by an orthogonal trend read,
# and two breakout/turn signals gated by a regime filter (Choppiness / Efficiency Ratio)).

def sig_combo_squeeze_supertrend(bars, st_n=10, st_mult=3.0):
    st_dir = _calc_supertrend(bars, st_n, st_mult)
    c = bars.c
    basis, dev = _sma(c, 20), c.rolling(20).std()
    bb_u, bb_l = basis + 2 * dev, basis - 2 * dev
    a = atr(bars.h, bars.l, c, 20)
    kc_u, kc_l = basis + 1.5 * a, basis - 1.5 * a
    squeeze_on = (bb_l > kc_l) & (bb_u < kc_u)
    release = (~squeeze_on) & squeeze_on.shift(1).fillna(False)
    return make_entries(release & (st_dir == 1), release & (st_dir == -1), bars.index)


def sig_combo_donchian_chop(bars, n=20, chop_n=14, chop_bar=38):
    hh = bars.h.rolling(n).max().shift(1)
    ll = bars.l.rolling(n).min().shift(1)
    trending = choppiness(bars, chop_n) < chop_bar
    above, below = bars.c > hh, bars.c < ll
    bull = above & ~above.shift(1).fillna(False) & trending
    bear = below & ~below.shift(1).fillna(False) & trending
    return make_entries(bull, bear, bars.index)


def sig_combo_hma_er(bars, n=21, er_n=10, er_bar=0.3):
    h = hma(bars.c, n)
    slope = h.diff()
    trending = efficiency_ratio(bars.c, er_n) > er_bar
    bull = (slope > 0) & (slope.shift(1) <= 0) & trending
    bear = (slope < 0) & (slope.shift(1) >= 0) & trending
    return make_entries(bull, bear, bars.index)


# --------------------------------------------------------------------------- registry
# horizon_kind: "trend" -> primary horizon = r_eod (let it run to the day's close)
#               "reversion" -> primary horizon = 2 bars of the SIGNAL's own timeframe
#                              (15min bar -> r30, 60min bar -> r120), pre-registered BEFORE
#                              running so no best-of-5 cherry-picking after the fact.
FAMILIES = {
    "KELTNER_BRK":        (sig_keltner, "trend"),
    "DONCHIAN_BRK":        (sig_donchian, "trend"),
    "SQUEEZE_RELEASE":     (sig_squeeze_release, "trend"),
    "STOCH_RSI":           (sig_stochrsi, "reversion"),
    "CCI_EXTREME":         (sig_cci, "reversion"),
    "WILLIAMS_R":          (sig_williams_r, "reversion"),
    "ELDER_RAY":           (sig_elder_ray, "trend"),
    "VORTEX":              (sig_vortex, "trend"),
    "AROON":               (sig_aroon, "trend"),
    "ICHIMOKU_TK":         (sig_ichimoku, "trend"),
    "CONNORS_RSI":         (sig_connors_rsi, "reversion"),
    "RVI":                 (sig_rvi, "trend"),
    "KST":                 (sig_kst, "trend"),
    "HMA_TURN":            (sig_hma, "trend"),
    "FRACTAL_BRK":         (sig_fractal_breakout, "trend"),
    "COMBO_SQUEEZE_ST":    (sig_combo_squeeze_supertrend, "trend"),
    "COMBO_DONCHIAN_CHOP": (sig_combo_donchian_chop, "trend"),
    "COMBO_HMA_ER":        (sig_combo_hma_er, "trend"),
}
