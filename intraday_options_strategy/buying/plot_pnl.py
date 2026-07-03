"""Plot equity curve + Sharpe for a strategy's trade list (build vs forward)."""
from __future__ import annotations

import datetime as dt

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import chain


def daily_equity(trades: pd.DataFrame, cap: float, start: dt.date, end: dt.date):
    """Cumulative equity over all trading days (flat on non-trade days)."""
    spot = chain.load_index()
    days = sorted({d for d in spot.index.date if start <= d <= end})
    pnl = pd.Series(0.0, index=pd.to_datetime(days))
    if not trades.empty:
        by_day = trades.groupby(trades["exit_t"].dt.date)["net_pnl"].sum()
        for d, v in by_day.items():
            ts = pd.Timestamp(d)
            if ts in pnl.index:
                pnl.loc[ts] += v
    eq = cap + pnl.cumsum()
    return eq, pnl


def stats(pnl: pd.Series, cap: float):
    eq = cap + pnl.cumsum()
    ret = pnl / (eq.shift(1).fillna(cap))
    sharpe = ret.mean() / ret.std() * np.sqrt(252) if ret.std() > 0 else 0.0
    peak = eq.cummax()
    maxdd = ((eq - peak) / peak).min()
    yrs = len(pnl) / 252
    cagr = (eq.iloc[-1] / cap) ** (1 / yrs) - 1 if yrs > 0 else 0
    return {"sharpe": sharpe, "maxdd": maxdd, "cagr": cagr,
            "total": eq.iloc[-1] - cap, "final": eq.iloc[-1]}


def plot(trades, cap, split, full_start, full_end, title, outpath):
    eq, pnl = daily_equity(trades, cap, full_start, full_end)
    b = pnl[pnl.index.date <= split]
    f = pnl[pnl.index.date > split]
    sb, sf = stats(b, cap), stats(f, b.cumsum().iloc[-1] + cap if len(b) else cap)
    sa = stats(pnl, cap)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(eq.index, eq.values, lw=1.6, color="#1f77b4")
    ax.axvline(pd.Timestamp(split), color="gray", ls="--", lw=1)
    ax.axhline(cap, color="black", lw=0.7, alpha=0.4)
    ax.fill_between(eq.index, cap, eq.values, where=(eq.values >= cap),
                    color="#2ca02c", alpha=0.10)
    ax.fill_between(eq.index, cap, eq.values, where=(eq.values < cap),
                    color="#d62728", alpha=0.10)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_ylabel("Equity (Rs.)")
    txt = (f"BUILD  Sharpe {sb['sharpe']:.2f} | CAGR {sb['cagr']:+.1%} | "
           f"MaxDD {sb['maxdd']:.0%}\n"
           f"FWD    Sharpe {sf['sharpe']:.2f} | total {sf['total']/cap:+.1%}\n"
           f"ALL    Sharpe {sa['sharpe']:.2f} | net Rs.{sa['total']:,.0f}")
    ax.text(0.015, 0.97, txt, transform=ax.transAxes, va="top", ha="left",
            fontsize=10, family="monospace",
            bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.9))
    ax.text(pd.Timestamp(split), eq.min(), " forward-test >", color="gray", fontsize=9)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(outpath, dpi=130)
    print(f"saved {outpath}")
    print(f"  BUILD sharpe={sb['sharpe']:.2f} cagr={sb['cagr']:+.1%} dd={sb['maxdd']:.0%}")
    print(f"  FWD   sharpe={sf['sharpe']:.2f} total={sf['total']/cap:+.1%}")
    print(f"  ALL   sharpe={sa['sharpe']:.2f} net=Rs.{sa['total']:,.0f}")
    return sa


if __name__ == "__main__":
    from dataclasses import replace
    from engine_swing import SwingCfg, run_range

    cfg = replace(SwingCfg(), trigger="ema_cross", strike_offset=-2, spread_width=0)
    tr = run_range(cfg, dt.date(2021, 1, 1), dt.date(2026, 6, 2))
    plot(tr, cfg.capital, dt.date(2025, 12, 31),
         dt.date(2021, 1, 1), dt.date(2026, 6, 2),
         "NIFTY Option-BUYING (emacross ITM2) — build vs forward",
         r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
         r"\NIFTY 500\intraday_options_strategy\buying\pnl_buying.png")
