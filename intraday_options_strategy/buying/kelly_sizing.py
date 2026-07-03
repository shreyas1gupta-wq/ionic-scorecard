"""0.33x (third) Kelly sizing on the intraday CE-selling strategy (sell CE>20DMA +
2.5x intraday stop) vs fixed 1 lot. Rolling Kelly from trailing trades (no lookahead),
margin-capped (naked CE ~Rs.1.3L/lot). Compares 3L (low-cap) and 10L. Saves PnL graph.

Honest caveat: Kelly on SHORT-vol amplifies the fat left tail; the estimate from trailing
wins understates rare big losses. 0.33x mitigates but does not remove ruin risk.
"""
from __future__ import annotations

import datetime as dt

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import sell_ce_enhanced as sce

MARGIN_PER_LOT = 1_30_000.0   # est. naked NIFTY short-CE SPAN+exposure margin
KELLY_FRAC = 0.33
WIN = 60                       # trailing trades for rolling Kelly
MAX_LOTS = 15
OUT = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
       r"\NIFTY 500\intraday_options_strategy\buying\sell_ce_kelly.png")


def kelly_curve(df, cap):
    """Rolling 0.33x-Kelly, margin-capped. Returns per-trade equity + lots."""
    r1 = df["net_pnl"].values            # 1-lot P&L per trade
    eq = cap
    equity = []
    lots_hist = []
    x_hist = []                           # return-on-margin history
    for i, pnl1 in enumerate(r1):
        # decide lots from trailing stats (data up to i-1)
        if len(x_hist) >= 20:
            arr = np.array(x_hist[-WIN:])
            mu, var = arr.mean(), arr.var()
            fstar = mu / var if var > 0 else 0.0
            target_margin = max(0.0, KELLY_FRAC * fstar * eq)
            lots = int(target_margin // MARGIN_PER_LOT)
        else:
            lots = 1                      # warmup: 1 lot
        lots = max(0, min(lots, int(eq // MARGIN_PER_LOT), MAX_LOTS))
        eq += lots * pnl1
        equity.append(eq)
        lots_hist.append(lots)
        x_hist.append(pnl1 / MARGIN_PER_LOT)
        if eq <= 0:
            # ruin: fill rest flat
            equity += [eq] * (len(r1) - i - 1)
            lots_hist += [0] * (len(r1) - i - 1)
            break
    return np.array(equity), np.array(lots_hist)


def fixed_curve(df, cap, lots=1):
    return cap + (df["net_pnl"] * lots).cumsum().values


def stats(eq, days, cap):
    eq = np.asarray(eq)
    ret = np.diff(np.concatenate([[cap], eq])) / np.concatenate([[cap], eq[:-1]])
    yrs = (days[-1] - days[0]).days / 365.25 + 1e-9
    tpy = len(eq) / yrs
    sharpe = ret.mean() / ret.std() * np.sqrt(tpy) if ret.std() > 0 else 0
    dd = ((eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)).min()
    cagr = (eq[-1] / cap) ** (1 / yrs) - 1 if eq[-1] > 0 else -1
    return {"final": eq[-1], "tot": eq[-1] / cap - 1, "cagr": cagr,
            "sharpe": sharpe, "maxdd": dd}


if __name__ == "__main__":
    df = sce.run(sce.Cfg(stop_mult=2.5), dt.date(2021, 1, 1), dt.date(2026, 6, 2))
    df = df.sort_values("day").reset_index(drop=True)
    days = pd.to_datetime(df["day"].values)
    print(f"trades: {len(df)}  ({df['day'].iloc[0]} .. {df['day'].iloc[-1]})")

    # full-sample Kelly (reference only)
    x = df["net_pnl"].values / MARGIN_PER_LOT
    fstar_full = x.mean() / x.var() if x.var() > 0 else 0
    print(f"full-sample Kelly f* (fraction of equity as margin) = {fstar_full:.2f}  "
          f"-> 0.33x = {0.33*fstar_full:.2f}  (=> ~{0.33*fstar_full:.2f}x capital in margin)")

    fig, ax = plt.subplots(figsize=(12, 6))
    for cap, color in [(3_00_000.0, "#1f77b4"), (10_00_000.0, "#ff7f0e")]:
        fx = fixed_curve(df, cap, 1)
        ke, lots = kelly_curve(df, cap)
        sf, sk = stats(fx, days, cap), stats(ke, days, cap)
        print(f"\ncapital Rs.{cap:,.0f}:")
        print(f"  fixed 1 lot : final Rs.{sf['final']:,.0f}  tot {sf['tot']:+.0%}  "
              f"CAGR {sf['cagr']:+.1%}  Sharpe {sf['sharpe']:.2f}  maxDD {sf['maxdd']:.0%}")
        print(f"  0.33x Kelly : final Rs.{sk['final']:,.0f}  tot {sk['tot']:+.0%}  "
              f"CAGR {sk['cagr']:+.1%}  Sharpe {sk['sharpe']:.2f}  maxDD {sk['maxdd']:.0%}  "
              f"| lots avg {lots.mean():.1f} max {lots.max()}")
        ax.plot(days, ke, color=color, lw=1.5, label=f"0.33x Kelly (Rs.{cap/1e5:.0f}L)")
        ax.plot(days, fx, color=color, lw=1.0, ls="--", alpha=0.6,
                label=f"fixed 1 lot (Rs.{cap/1e5:.0f}L)")
    ax.axvline(pd.Timestamp(2026, 1, 1), color="gray", ls=":", lw=1)
    ax.text(pd.Timestamp(2026, 1, 1), ax.get_ylim()[0], " fwd >", color="gray", fontsize=9)
    ax.set_yscale("log")
    ax.set_title("Intraday CE-selling (>20DMA + 2.5x stop): fixed 1 lot vs 0.33x Kelly",
                 fontsize=12, fontweight="bold")
    ax.set_ylabel("Equity (Rs., log)")
    ax.legend(fontsize=8)
    fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(OUT, dpi=130)
    print(f"\nsaved graph -> {OUT}")
