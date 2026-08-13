"""Futures covered-call / covered-put / collar engine, weekly tenor.
Pre-registered in PRE_REGISTRATION.md (written before this ran). Reuses chain.py accessors
(do not rewrite). Real traded option prices for P&L; BS delta (hand-rolled, math.erf, no
external lib) ONLY for strike selection off trailing realized vol -- per session METHOD LAW.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402

OUT = Path(__file__).parent
NIFTY_1MIN = ROOT / "intraday_options_strategy" / "datasets" / "processed" / "nifty_1min.parquet"

LOT = 75
R = 0.065
BUILD_END = dt.date(2025, 12, 31)
HOLDOUT_START = dt.date(2026, 1, 1)
DELTAS = [0.15, 0.25, 0.35]
TAIL_PUT_DELTA = 0.10

# ---------------------------------------------------------------------------
# cost model (SHARED_CONTEXT costs, authoritative for this mandate)
# ---------------------------------------------------------------------------

def option_leg_cost(premium: float, lot_size: int, side: str, event: str) -> float:
    """Rupee cost of ONE order. side in {'sell_open','buy_close','buy_open','sell_close'},
    event in {'order','exercise'}. Follows COST_STANDARDS.md + SHARED_CONTEXT Rs25/lot/side."""
    notional = premium * lot_size
    if event == "exercise":
        # automatic cash settlement at expiry, ITM: STT 0.125% of INTRINSIC, nothing else
        return 0.00125 * notional
    brokerage = 25.0
    exch_txn = 0.00035 * notional
    stt = 0.001 * notional if side in ("sell_open", "sell_close") else 0.0
    stamp = 0.00003 * notional if side in ("buy_open",) else 0.0  # options buy stamp 0.003%
    gst = 0.18 * (brokerage + exch_txn)
    slippage = 0.0025 * notional  # liquid ATM-ish index option floor
    return brokerage + exch_txn + stt + stamp + gst + slippage


def futures_cost_pts(entry_date: dt.date) -> float:
    return (4.47 if entry_date < dt.date(2024, 10, 1) else 5.97) + 0.5


# ---------------------------------------------------------------------------
# BS delta (hand-rolled, no external lib dependency)
# ---------------------------------------------------------------------------

def _ncdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_deltas(S: float, K: float, T: float, sigma: float, r: float = R):
    if T <= 0 or sigma <= 0:
        call_d = 1.0 if S > K else 0.0
        return call_d, call_d - 1.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    cd = _ncdf(d1)
    return cd, cd - 1.0


def nw_tstat(x: np.ndarray, lags: int = 5) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 10:
        return float("nan")
    m = x.mean()
    d = x - m
    g0 = (d @ d) / n
    var = g0
    for L in range(1, min(lags, n - 1) + 1):
        gL = (d[L:] @ d[:-L]) / n
        var += 2 * (1 - L / (lags + 1)) * gL
    if var <= 0:
        return float("nan")
    return m / math.sqrt(var / n)


# ---------------------------------------------------------------------------
# spot / vol
# ---------------------------------------------------------------------------

def build_daily_close() -> pd.Series:
    df = pd.read_parquet(NIFTY_1MIN)
    df = df[df.index.time >= dt.time(9, 15)]
    daily = df.groupby(df.index.date)["close"].last()
    daily.index = pd.to_datetime(daily.index)
    return daily.sort_index()


def trailing_ann_vol(daily: pd.Series, asof: dt.date, window: int = 20) -> float:
    """PIT-safe: uses only closes strictly BEFORE asof."""
    hist = daily[daily.index.date < asof]
    if len(hist) < window + 1:
        return float("nan")
    r = np.log(hist / hist.shift(1)).dropna().iloc[-window:]
    return float(r.std() * math.sqrt(252))


def sma(daily: pd.Series, asof: dt.date, window: int = 20) -> float:
    hist = daily[daily.index.date < asof]
    if len(hist) < window:
        return float("nan")
    return float(hist.iloc[-window:].mean())


def spot_close_on(daily: pd.Series, day: dt.date):
    sub = daily[daily.index.date == day]
    return float(sub.iloc[0]) if len(sub) else None


# ---------------------------------------------------------------------------
# strike selection off a day's chain snapshot
# ---------------------------------------------------------------------------

def snapshot_prices(df_exp: pd.DataFrame, day: dt.date, after_time=dt.time(9, 20)):
    """First bar at/after after_time on `day`, per strike+type -> close price."""
    day_df = df_exp[df_exp["trading_day"] == day.isoformat()]
    if day_df.empty:
        return None
    day_df = day_df[day_df["t"].dt.time >= after_time]
    if day_df.empty:
        return None
    t0 = day_df["t"].min()
    snap = day_df[day_df["t"] == t0]
    out = {}
    for _, row in snap.iterrows():
        if row["close"] and row["close"] > 0:
            out[(int(row["strike"]), row["option_type"])] = float(row["close"])
    return out if out else None


def pick_strike(snap: dict, opt_type: str, S: float, T: float, sigma: float, target_delta: float):
    best = None
    for (K, ot), px in snap.items():
        if ot != opt_type:
            continue
        cd, pd_ = bs_deltas(S, K, T, sigma)
        d = cd if opt_type == "CE" else abs(pd_)
        diff = abs(d - target_delta)
        if best is None or diff < best[0]:
            best = (diff, K, px, d)
    if best is None:
        return None
    return {"K": best[1], "px": best[2], "delta": best[3]}


def eod_close(df_exp: pd.DataFrame, day: dt.date, K: int, opt_type: str):
    day_df = df_exp[(df_exp["trading_day"] == day.isoformat()) & (df_exp["strike"] == K)
                     & (df_exp["option_type"] == opt_type)]
    if day_df.empty:
        return None
    row = day_df.sort_values("t").iloc[-1]
    px = float(row["close"])
    return px if px > 0 else None
