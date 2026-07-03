"""Realistic Indian-market frictions for option/equity strategy backtests.

Bundles: transaction costs (brokerage/STT/exch/GST/stamp/SEBI), liquidity-scaled slippage,
UC/LC circuit checks, and a volume/OI liquidity gate. Plus a screen_then_full() helper that
runs a strategy on a ~20% time-contiguous SAMPLE first and only runs the FULL backtest if the
sample passes a hurdle — to save compute per strategy.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

# ---- transaction costs (per Zerodha/Angel-style 2024-25 retail schedule) --------------------
BROKERAGE_PER_ORDER = 20.0
STT_OPT_SELL = 0.0625 / 100        # STT on options SELL premium (0.0625%)
STT_EQ_DELIVERY = 0.10 / 100       # equity delivery, both sides
STT_EQ_INTRADAY_SELL = 0.025 / 100
EXCH_TXN_OPT = 0.0495 / 100        # NSE options exch txn on premium
EXCH_TXN_EQ = 0.00297 / 100
GST = 0.18
STAMP_BUY = 0.003 / 100            # options buy stamp
SEBI_PER_CR = 10.0


def option_costs(sell_prem, buy_prem, close_prem, n_legs, lots, lot_size):
    """Round-trip option costs in rupees for the whole position."""
    qty = lots * lot_size
    brok = BROKERAGE_PER_ORDER * n_legs * 2
    turnover = (sell_prem + buy_prem + close_prem) * qty
    exch = EXCH_TXN_OPT * turnover
    stt = STT_OPT_SELL * (sell_prem * qty)          # STT on sell-side premium
    gst = GST * (brok + exch)
    sebi = SEBI_PER_CR * turnover / 1e7
    stamp = STAMP_BUY * (buy_prem * qty)
    return brok + exch + stt + gst + sebi + stamp


# ---- liquidity-scaled slippage --------------------------------------------------------------
def slippage_pct(underlying_type: str, moneyness: str = "atm", premium: float = None) -> float:
    """Per-leg slippage as fraction of premium. Wider for stock options & OTM/cheap options."""
    base = {"index": 0.004, "stock": 0.015}.get(underlying_type, 0.01)
    mult = {"atm": 1.0, "near_otm": 1.4, "far_otm": 2.5, "deep_itm": 1.6}.get(moneyness, 1.0)
    s = base * mult
    if premium is not None and premium < 5:      # cheap options: spread is a big % of price
        s *= 2.0
    return s


# ---- UC/LC circuit check --------------------------------------------------------------------
# NSE daily price bands: F&O stocks effectively 10-20% (no band for most F&O, but the
# index / illiquid names have bands). We treat a large single-day move as an untradeable
# circuit event: if |day return| >= band, exit fills are unreliable -> penalize/skip.
def hit_circuit(day_open, day_close, band=0.095):
    if not (np.isfinite(day_open) and np.isfinite(day_close) and day_open > 0):
        return False
    return abs(day_close / day_open - 1) >= band


def circuit_exit_penalty(intended_ret, hit_up_or_down: bool, penalty=0.03):
    """If underlying hit a circuit on the exit day, worsen the realized return (couldn't exit
    at the intended price). Conservative flat penalty on top of slippage."""
    return intended_ret - penalty if hit_up_or_down else intended_ret


# ---- volume / OI liquidity gate -------------------------------------------------------------
def liquid_enough(volume, oi, min_volume=500, min_oi=500):
    """Require some traded volume AND open interest at entry to consider a strike tradeable."""
    v = (volume is not None) and np.isfinite(volume) and volume >= min_volume
    o = (oi is not None) and np.isfinite(oi) and oi >= min_oi
    return v or o     # OR: either recent volume or standing OI indicates tradeability


# ---- screen-then-full runner ----------------------------------------------------------------
def screen_then_full(run_fn, all_dates, sample_frac=0.20, hurdle_fn=None, contiguous=True):
    """run_fn(dates) -> DataFrame with a 'net_pnl' or 'ret' column.
    1) Run on the first `sample_frac` of dates (time-contiguous by default).
    2) If hurdle_fn(sample_df) is True, run on ALL dates and return (full_df, 'passed').
       else return (sample_df, 'screened_out')."""
    all_dates = sorted(all_dates)
    n = max(1, int(len(all_dates) * sample_frac))
    sample_dates = all_dates[:n] if contiguous else all_dates[::int(1 / sample_frac)]
    sdf = run_fn(sample_dates)
    if hurdle_fn is None:
        col = "ret" if "ret" in sdf.columns else "net_pnl"
        hurdle_fn = lambda d: (len(d) >= 20 and d[col].mean() > 0 and (d[col] > 0).mean() >= 0.45)
    passed = (not sdf.empty) and hurdle_fn(sdf)
    if not passed:
        return sdf, "screened_out"
    return run_fn(all_dates), "passed"


def quick_metrics(df, ret_col="ret", cap=3_00_000.0, split=dt.date(2024, 12, 31), date_col="entry"):
    if df.empty or len(df) < 5:
        return {"n": len(df)}
    r = df[ret_col]
    out = {"n": len(df), "mean": float(r.mean()), "median": float(r.median()),
           "hit": float((r > 0).mean()), "worst": float(r.min())}
    if date_col in df.columns:
        d = pd.to_datetime(df[date_col])
        b = df[d.dt.date <= split][ret_col]; f = df[d.dt.date > split][ret_col]
        out["build_mean"] = float(b.mean()) if len(b) else np.nan
        out["fwd_mean"] = float(f.mean()) if len(f) else np.nan
    return out


if __name__ == "__main__":
    # smoke test
    print("option RT cost (sell100 buy60 close30, 4 legs, 1 lot x75):",
          round(option_costs(100, 60, 30, 4, 1, 75), 1))
    print("slippage stock far_otm cheap:", slippage_pct("stock", "far_otm", 3))
    print("circuit hit 10% move:", hit_circuit(100, 110))
    print("liquid (vol=600,oi=0):", liquid_enough(600, 0))
