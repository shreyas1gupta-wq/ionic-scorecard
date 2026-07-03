"""Overnight-drift + gap-down-fade standalone strategies WITH realistic costs.

These are the two long-equity timing edges that powered the Sharpe-2 multi-strat mix.
The mix modeled them GROSS; here we apply real round-trip costs (NIFTYBEES/futures) and
a cost-sensitivity sweep, because the overnight edge (~+0.08%/night) is small and
cost-sensitive. Traded via the index (NIFTYBEES ETF / Nifty futures), NOT options.
Build 2021-2025 / forward 2026 H1. Costs in basis points of notional (1x, no leverage).
"""
from __future__ import annotations

import datetime as dt

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import chain

SPLIT = dt.date(2025, 12, 31)


def daily():
    spot = chain.load_index()
    g = spot.groupby(spot.index.date)
    d = pd.DataFrame({"open": g["open"].first(), "close": g["close"].last()})
    d.index = pd.to_datetime([pd.Timestamp(x) for x in d.index])
    return d


def metrics(ret, label):
    """ret = daily fractional return series (0 on inactive days)."""
    ret = ret.dropna()
    b = ret[ret.index.date <= SPLIT]; f = ret[ret.index.date > SPLIT]

    def m(r):
        if len(r) < 5 or r.std() == 0:
            return (0, 0, 0, 0)
        eq = (1 + r).cumprod()
        dd = (eq / eq.cummax() - 1).min()
        sharpe = r.mean() / r.std() * np.sqrt(252)
        cagr = eq.iloc[-1] ** (252 / len(r)) - 1
        return (sharpe, cagr, dd, eq.iloc[-1] - 1)
    sb, cb, ddb, tb = m(b); sf, cf, ddf, tf = m(f)
    n_act = int((ret != 0).sum())
    print(f"  {label:34s}: BUILD Sharpe {sb:5.2f} CAGR {cb:+6.1%} DD {ddb:5.0%} | "
          f"FWD Sharpe {sf:5.2f} tot {tf:+6.1%} | active {n_act}")
    return b, f


def overnight_returns(d, cost_bps):
    """Long close[t] -> open[t+1], every day, minus round-trip cost."""
    c2o = d["open"].shift(-1) / d["close"] - 1
    net = (c2o - cost_bps / 1e4).shift(1)   # realize next day
    return net


def gapfade_returns(d, cost_bps, gap_thresh=-0.005):
    """On gap-down > threshold: long open -> close, minus round-trip cost."""
    gap = d["open"] / d["close"].shift(1) - 1
    o2c = d["close"] / d["open"] - 1
    r = pd.Series(0.0, index=d.index)
    mask = gap < gap_thresh
    r[mask] = o2c[mask] - cost_bps / 1e4
    return r


if __name__ == "__main__":
    d = daily()
    print("=" * 92)
    print("OVERNIGHT DRIFT (long close->open daily) — cost sensitivity (round-trip bps of notional)")
    print("=" * 92)
    for cb in (0, 3, 5, 8):
        metrics(overnight_returns(d, cb), f"overnight @ {cb}bps")

    print("\n" + "=" * 92)
    print("GAP-DOWN FADE (gap<-0.5% -> long open->close) — cost sensitivity")
    print("=" * 92)
    for cb in (0, 4, 6, 10):
        metrics(gapfade_returns(d, cb), f"gapfade @ {cb}bps")

    print("\n" + "=" * 92)
    print("COMBINED (overnight @5bps + gapfade @6bps, equal capital, both long index)")
    print("=" * 92)
    on = overnight_returns(d, 5).reindex(d.index).fillna(0)
    gf = gapfade_returns(d, 6).reindex(d.index).fillna(0)
    combo = 0.5 * on + 0.5 * gf
    bo, fo = metrics(on, "overnight @5bps")
    bg, fg = metrics(gf, "gapfade @6bps")
    bc, fc = metrics(combo, "COMBINED (50/50)")
    print(f"\n  corr(overnight, gapfade) build = {pd.concat([on[on.index.date<=SPLIT], gf[gf.index.date<=SPLIT]], axis=1).corr().iloc[0,1]:.2f}")

    # equity graph (net, combined + each)
    fig, ax = plt.subplots(figsize=(12, 6))
    for s, lab, c in [(on, "Overnight @5bps", "#1f77b4"), (gf, "Gap-fade @6bps", "#ff7f0e"),
                      (combo, "Combined 50/50", "#2ca02c")]:
        eq = (1 + s).cumprod()
        ax.plot(eq.index, eq.values, label=lab, lw=1.5 if lab.startswith("Comb") else 1.1)
    ax.axvline(pd.Timestamp(2026, 1, 1), color="gray", ls=":", lw=1)
    ax.text(pd.Timestamp(2026, 1, 1), ax.get_ylim()[0], " fwd >", color="gray", fontsize=9)
    ax.set_yscale("log"); ax.set_title("Overnight-drift & Gap-fade (net of costs, index-traded) — growth of 1",
                                       fontsize=12, fontweight="bold")
    ax.set_ylabel("Growth of Rs.1 (log)"); ax.legend(fontsize=9)
    fig.autofmt_xdate(); fig.tight_layout()
    out = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
           r"\NIFTY 500\intraday_options_strategy\buying\overnight_gapfade.png")
    fig.savefig(out, dpi=130)
    print(f"\nsaved graph -> {out}")
