"""P&L graph + CAGR for the current best strategy (RV-vs-IV short vol, IV/RV>=1.4)
using FIXED sizing vs 0.5x KELLY sizing. Trades overlap across 88 stocks over ~30-day
holds; P&L for each trade is realized on its EXIT day (event-study convention, consistent
with the rest of this session's multi-strat sleeves).
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
BUY = ROOT / "intraday_options_strategy/buying"
R = pd.read_parquet(BUY / "rv_iv_vol.parquet")
SPLIT = dt.date(2024, 12, 31)
CAP = 3_00_000.0
THRESH = 1.4
KELLY_FRAC = 0.5
MAX_RISK_FRAC = 0.10     # cap: no single trade risks > 10% of equity (short-vol tail control)


def build_trades():
    T = R[R["iv_rv"] >= THRESH].copy()
    T["entry"] = pd.to_datetime(T["entry"])
    T["exit"] = pd.to_datetime(T["exit"])
    T = T.sort_values("exit").reset_index(drop=True)
    return T


def fixed_curve(T, cap, frac_per_trade=0.05):
    """Equal fixed-fraction of CURRENT equity per trade, booked on exit day."""
    eq = cap
    curve = []
    for _, row in T.iterrows():
        stake = frac_per_trade * eq
        pnl = stake * row["short_ret"]
        eq += pnl
        curve.append({"date": row["exit"], "eq": eq, "pnl": pnl})
    return pd.DataFrame(curve)


def kelly_curve(T, cap, kfrac, win=40, max_risk=MAX_RISK_FRAC):
    """Rolling Kelly f* = mean/var of trailing short_ret, applied at kfrac x, capped."""
    eq = cap
    curve = []
    hist = []
    for _, row in T.iterrows():
        if len(hist) >= 15:
            arr = np.array(hist[-win:])
            mu, var = arr.mean(), arr.var()
            fstar = mu / var if var > 0 else 0.0
            frac = max(0.0, min(kfrac * fstar, max_risk))
        else:
            frac = 0.03      # warmup stake
        stake = frac * eq
        pnl = stake * row["short_ret"]
        eq += pnl
        curve.append({"date": row["exit"], "eq": eq, "pnl": pnl, "frac": frac})
        hist.append(row["short_ret"])
    return pd.DataFrame(curve)


def to_daily(curve_df, cap, date_index):
    """Step-function equity reindexed to a daily calendar for plotting/Sharpe."""
    s = curve_df.set_index("date")["eq"]
    s = s[~s.index.duplicated(keep="last")]
    full = s.reindex(date_index.union(s.index)).sort_index().ffill().fillna(cap)
    full = full.reindex(date_index).ffill().fillna(cap)
    return full


def stats(eq, cap):
    ret = eq.pct_change().fillna(0)
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / cap) ** (1 / yrs) - 1
    sharpe = ret.mean() / ret.std() * np.sqrt(252) if ret.std() > 0 else 0
    dd = (eq / eq.cummax() - 1).min()
    return {"cagr": cagr, "sharpe": sharpe, "maxdd": dd, "final": eq.iloc[-1]}


if __name__ == "__main__":
    T = build_trades()
    print(f"trades (IV/RV>={THRESH}): {len(T)}  {T['entry'].min().date()}..{T['exit'].max().date()}")

    fixed = fixed_curve(T, CAP, frac_per_trade=0.05)
    kelly = kelly_curve(T, CAP, KELLY_FRAC)

    full_idx = pd.date_range(T["entry"].min(), T["exit"].max(), freq="D")
    eq_fixed = to_daily(fixed, CAP, full_idx)
    eq_kelly = to_daily(kelly, CAP, full_idx)

    for name, eq in [("FIXED (5% notional/trade)", eq_fixed), ("0.5x KELLY (capped 10%)", eq_kelly)]:
        b = eq[eq.index.date <= SPLIT]; f = eq[eq.index.date > SPLIT]
        sb = stats(b, CAP); sf = stats(f, b.iloc[-1] if len(b) else CAP)
        sa = stats(eq, CAP)
        print(f"\n{name}")
        print(f"  BUILD : CAGR {sb['cagr']:+.1%}  Sharpe {sb['sharpe']:.2f}  MaxDD {sb['maxdd']:.0%}")
        print(f"  FWD   : CAGR {sf['cagr']:+.1%}  Sharpe {sf['sharpe']:.2f}  MaxDD {sf['maxdd']:.0%}")
        print(f"  ALL   : CAGR {sa['cagr']:+.1%}  Sharpe {sa['sharpe']:.2f}  MaxDD {sa['maxdd']:.0%}  Final Rs.{sa['final']:,.0f}")

    if "frac" in kelly.columns:
        print(f"\nKelly stake sizing: avg {kelly['frac'].mean():.1%} of equity/trade, max {kelly['frac'].max():.1%}")

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(eq_fixed.index, eq_fixed.values, label="Fixed 5%/trade", lw=1.4, color="#1f77b4")
    ax.plot(eq_kelly.index, eq_kelly.values, label="0.5x Kelly (cap 10%)", lw=1.6, color="#d62728")
    ax.axhline(CAP, color="black", lw=0.6, alpha=0.4)
    ax.axvline(pd.Timestamp(SPLIT), color="gray", ls="--", lw=1)
    ax.text(pd.Timestamp(SPLIT), ax.get_ylim()[0], " forward >", color="gray", fontsize=9)
    ax.set_yscale("log")
    ax.set_title(f"Short-vol (IV/RV>={THRESH}) stock options: Fixed vs 0.5x Kelly — Rs.{CAP:,.0f} start",
                 fontsize=12, fontweight="bold")
    ax.set_ylabel("Equity (Rs., log)")
    ax.legend(fontsize=9)
    fig.autofmt_xdate(); fig.tight_layout()
    out = BUY / "rviv_fixed_vs_kelly.png"
    fig.savefig(out, dpi=130)
    print(f"\nsaved graph -> {out}")
