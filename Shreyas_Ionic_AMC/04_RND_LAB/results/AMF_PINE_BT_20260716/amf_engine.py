"""
AMF_PINE_BT_20260716 — faithful Python translation of "Adaptive Momentum Fusion
[WillyAlgoTrader]" Pine v6 indicator's TRADEABLE core (close-only engines: Efficiency,
Momentum; modes: MACD, PPO). Per SPEC.md formulas, transcribed exactly.

BLOCKED (not implemented, need OHLCV/volume not on disk): Volatility, Fractal, Volume,
Composite engines + divergence signals. Requires bhavcopy full-OHLCV pull (D-033 data
office job) before those can be built.

All recursive filters (adaptiveEma, jurikSmooth) are stateful per-bar and cannot be
vectorized without breaking numerical fidelity to the Pine recursion — implemented as
tight Python loops over plain lists (fastest pure-CPython option; no numba on this box).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FAST_SC = 2.0 / 3.0     # KAMA fast constant (fixed, NOT fastLen-dependent per spec)
SLOW_SC = 2.0 / 31.0    # KAMA slow constant (fixed)


def safe_div(n: np.ndarray, d: np.ndarray, fb: float) -> np.ndarray:
    """safeDiv(n,d,fb) = d!=0 & finite(n/d) ? n/d : fb."""
    n = np.asarray(n, dtype=float)
    d = np.asarray(d, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        q = n / d
    ok = (d != 0) & np.isfinite(q)
    out = np.where(ok, q, fb)
    return out


def efficiency_ratio(src: np.ndarray, length: int) -> np.ndarray:
    """direction=abs(src-src[len]); volatility=sum(abs(src-src[1]),len); safeDiv(...,0.5)."""
    s = pd.Series(src)
    direction = (s - s.shift(length)).abs()
    volatility = s.diff().abs().rolling(length).sum()
    er = safe_div(direction.values, volatility.values, 0.5)
    return er


def adaptive_ema(src: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """alpha clamped [0.01,1]; y[0]=src[0] (seed); y[t]=a*x+(1-a)*y[t-1]."""
    a = np.clip(alpha, 0.01, 1.0)
    x = list(np.asarray(src, dtype=float))
    al = list(a)
    n = len(x)
    y = [0.0] * n
    if n == 0:
        return np.array(y)
    y[0] = x[0]
    prev = y[0]
    for t in range(1, n):
        cur = al[t] * x[t] + (1.0 - al[t]) * prev
        y[t] = cur
        prev = cur
    return np.array(y)


def engine_efficiency(src: np.ndarray, length: int) -> np.ndarray:
    er = efficiency_ratio(src, length)
    sc = (er * (FAST_SC - SLOW_SC) + SLOW_SC) ** 2
    return adaptive_ema(src, sc)


def engine_momentum(src: np.ndarray, length: int) -> np.ndarray:
    s = pd.Series(src, dtype=float)
    shifted = s.shift(length)
    roc = safe_div((s - shifted).values, shifted.values, 0.0) * 100.0
    roc_abs = np.abs(roc)
    roc_max = pd.Series(roc_abs).rolling(length * 2).max().values
    with np.errstate(invalid="ignore"):
        norm = np.where(roc_max > 0, np.minimum(roc_abs / np.where(roc_max > 0, roc_max, 1.0), 1.0), 0.5)
    base_alpha = 2.0 / (length + 1)
    alpha = np.clip(base_alpha + norm * (1.0 - base_alpha) * 0.5, 0.01, 1.0)
    return adaptive_ema(s.values, alpha)


def jurik_smooth(src: np.ndarray, length: int, phase: float) -> np.ndarray:
    """beta=0.45*(len-1)/(0.45*(len-1)+2); alphaJ=beta^3.
    e0=(1-aJ)*x+aJ*e0[1]; e1=(x-e0)*(1-beta)+beta*e1[1];
    e2=(e0+phase*e1-e2[1])*(1-aJ)^2+aJ^2*e2[1]. Seed: e0[-1]=e1[-1]=e2[-1]=0 (Pine nz())."""
    beta = 0.45 * (length - 1) / (0.45 * (length - 1) + 2.0)
    aJ = beta ** 3
    x = list(np.asarray(src, dtype=float))
    n = len(x)
    e0_prev = e1_prev = e2_prev = 0.0
    out = [0.0] * n
    one_m_aJ2 = (1.0 - aJ) ** 2
    aJ2 = aJ ** 2
    for t in range(n):
        xt = x[t]
        e0 = (1.0 - aJ) * xt + aJ * e0_prev
        e1 = (xt - e0) * (1.0 - beta) + beta * e1_prev
        e2 = (e0 + phase * e1 - e2_prev) * one_m_aJ2 + aJ2 * e2_prev
        out[t] = e2
        e0_prev, e1_prev, e2_prev = e0, e1, e2
    return np.array(out)


def compute_amf(close: np.ndarray, fast_len: int = 8, slow_len: int = 21, signal_len: int = 7,
                 phase: float = 0.7, engine: str = "Efficiency", mode: str = "MACD") -> dict:
    """Returns dict of arrays: fastMA, slowMA, osc, signal, bull_cross, bear_cross,
    zero_bull, zero_bear, warmed_up (bool mask, first max(slow_len*2,50) bars = False)."""
    close = np.asarray(close, dtype=float)
    n = len(close)
    eng = engine_efficiency if engine == "Efficiency" else engine_momentum
    fast_ma = eng(close, fast_len)
    slow_ma = eng(close, slow_len)
    if mode == "PPO":
        osc = safe_div(fast_ma - slow_ma, slow_ma, 0.0) * 100.0
    else:
        osc = fast_ma - slow_ma
    signal = jurik_smooth(osc, signal_len, phase)

    osc_prev = np.roll(osc, 1)
    sig_prev = np.roll(signal, 1)
    bull_cross = (osc_prev < sig_prev) & (osc > signal)
    bear_cross = (osc_prev > sig_prev) & (osc < signal)
    zero_bull = (osc_prev < 0) & (osc > 0)
    zero_bear = (osc_prev > 0) & (osc < 0)
    bull_cross[0] = bear_cross[0] = zero_bull[0] = zero_bear[0] = False

    warm_bars = max(slow_len * 2, 50)
    warmed_up = np.zeros(n, dtype=bool)
    warmed_up[warm_bars:] = True

    return dict(fast_ma=fast_ma, slow_ma=slow_ma, osc=osc, signal=signal,
                bull_cross=bull_cross & warmed_up, bear_cross=bear_cross & warmed_up,
                zero_bull=zero_bull & warmed_up, zero_bear=zero_bear & warmed_up,
                warmed_up=warmed_up)


# ---------------- 1-symbol sanity check ----------------
if __name__ == "__main__":
    import sys
    sys.path.insert(0, r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\lib")
    panel_path = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets\derived\pit_union_panel_v1\close_panel_price.parquet"
    df = pd.read_parquet(panel_path)
    sym = "RELIANCE"
    s = df[df["symbol"] == sym].sort_values("date").reset_index(drop=True)
    print(f"[sanity] symbol={sym} rows={len(s)} range={s['date'].min()} -> {s['date'].max()}")
    close = s["close"].values

    results = {}
    for engine in ("Efficiency", "Momentum"):
        for mode in ("MACD", "PPO"):
            r = compute_amf(close, engine=engine, mode=mode)
            results[(engine, mode)] = r
            osc, sig = r["osc"], r["signal"]
            wu = r["warmed_up"]
            finite_ok = np.isfinite(osc[wu]).all() and np.isfinite(sig[wu]).all()
            osc_mean = np.nanmean(osc[wu])
            osc_std = np.nanstd(osc[wu])
            n_bull = int(r["bull_cross"].sum())
            n_bear = int(r["bear_cross"].sum())
            n_zb = int(r["zero_bull"].sum())
            n_zs = int(r["zero_bear"].sum())
            print(f"[sanity] engine={engine:10s} mode={mode:4s} finite_ok={finite_ok} "
                  f"osc_mean={osc_mean:.4f} osc_std={osc_std:.4f} "
                  f"bullCross={n_bull} bearCross={n_bear} zeroBull={n_zb} zeroBear={n_zs}")
            assert finite_ok, f"NON-FINITE values in {engine}/{mode} — translation bug"
            assert n_bull > 0 and n_bear > 0, f"no crossovers fired for {engine}/{mode} — check logic"

    print("[sanity] ALL CHECKS PASSED — osc/signal finite, oscillate, crossovers fire.")
