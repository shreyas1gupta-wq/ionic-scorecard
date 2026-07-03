"""Full INTRADAY 1-min option-buying backtest (square off same day) + PnL graph.
Best honest shot: ITM (less theta), let winners run w/ trailing, cut losers fast.
Build 2021-2025 + untouched forward 2026 H1. Uses engine.py (1-min entries/exits).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import replace

import pandas as pd

from engine import Config, run_range
from plot_pnl import daily_equity, stats, plot

BUILD = (dt.date(2021, 1, 1), dt.date(2025, 12, 31))
FWD = (dt.date(2026, 1, 1), dt.date(2026, 6, 2))
SPLIT = dt.date(2025, 12, 31)

VARIANTS = {
    "base_ATM":   dict(strike_offset=0, spread_width=0, target_pct=0.5,
                       stop_pct=0.3, trail_pct=0.0, time_stop_min=90),
    "ITM_convex": dict(strike_offset=-1, spread_width=0, target_pct=1.0,
                       stop_pct=0.35, trail_pct=0.4, time_stop_min=45,
                       max_trades_per_day=5),
    "spread_fast": dict(strike_offset=0, spread_width=4, target_pct=0.8,
                        stop_pct=0.4, trail_pct=0.4, time_stop_min=45),
}

if __name__ == "__main__":
    base = Config()
    results = {}
    for name, ov in VARIANTS.items():
        cfg = replace(base, **ov)
        print(f"\n=== {name} (full range) ===")
        tr = run_range(cfg, BUILD[0], FWD[1], progress=False)
        results[name] = (cfg, tr)
        if tr.empty:
            print("  no trades"); continue
        _, pnl = daily_equity(tr, cfg.capital, BUILD[0], FWD[1])
        b = pnl[pnl.index.date <= SPLIT]
        f = pnl[pnl.index.date > SPLIT]
        sb = stats(b, cfg.capital)
        sf = stats(f, cfg.capital + b.cumsum().iloc[-1] if len(b) else cfg.capital)
        wr = (tr["net_pnl"] > 0).mean()
        print(f"  trades={len(tr)} WR={wr:.0%} | BUILD sharpe={sb['sharpe']:.2f} "
              f"cagr={sb['cagr']:+.1%} dd={sb['maxdd']:.0%} net=Rs.{sb['total']:,.0f}")
        print(f"                       | FWD   sharpe={sf['sharpe']:.2f} "
              f"total={sf['total']/cfg.capital:+.1%} net=Rs.{sf['total']:,.0f}")

    # plot the variant with best BUILD sharpe
    best = max(results, key=lambda k: (
        stats(daily_equity(results[k][1], results[k][0].capital, BUILD[0], FWD[1])[1]
              [daily_equity(results[k][1], results[k][0].capital, BUILD[0], FWD[1])[1].index.date <= SPLIT],
              results[k][0].capital)["sharpe"] if not results[k][1].empty else -9))
    cfg, tr = results[best]
    plot(tr, cfg.capital, SPLIT, BUILD[0], FWD[1],
         f"NIFTY INTRADAY 1-min option buying ({best}) — build vs forward",
         r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
         r"\NIFTY 500\intraday_options_strategy\buying\pnl_intraday.png")
    print(f"\nplotted best build-sharpe variant: {best}")
