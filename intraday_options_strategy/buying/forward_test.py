"""ONE-SHOT forward test of the locked config on the untouched 2026 H1 holdout.

Locked on build set (2021-2025): ema_cross bullish trend, uptrend regime, buy
2-strike ITM weekly CE (3-9 DTE), hold <=4d, target +100% / trail 35% / stop 35%.
No parameters were tuned on 2026 data. This is the honest out-of-sample check.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import replace

import pandas as pd

from engine_swing import SwingCfg, run_range, summarize
from compare import metrics

pd.set_option("display.width", 220, "display.max_columns", None)

BUILD = (dt.date(2021, 1, 1), dt.date(2025, 12, 31))
FWD = (dt.date(2026, 1, 1), dt.date(2026, 6, 2))

LOCKED = {
    "emacross_ITM2 (PRIMARY)": dict(trigger="ema_cross", strike_offset=-2, spread_width=0),
    "emacross_ATM (sibling)":  dict(trigger="ema_cross", strike_offset=0, spread_width=0),
}

TRADE_COLS = ["enter_day", "exp", "dte0", "strike", "entry_debit", "fill_debit",
              "fill_exit", "ret_pct", "reason", "hold_days", "lots", "net_pnl"]


def show(df, cap):
    m = metrics(df, cap)
    if not df.empty:
        print(df[TRADE_COLS].to_string(index=False,
              formatters={"ret_pct": "{:+.0%}".format, "net_pnl": "Rs.{:,.0f}".format,
                          "entry_debit": "{:.1f}".format, "fill_debit": "{:.1f}".format,
                          "fill_exit": "{:.1f}".format}))
    return m


if __name__ == "__main__":
    base = SwingCfg()
    for name, ov in LOCKED.items():
        cfg = replace(base, **ov)
        print("\n" + "=" * 90)
        print(f"CONFIG: {name}   cap=Rs.{cfg.capital:,.0f}")
        print("=" * 90)

        print("\n[BUILD 2021-2025]")
        bdf = run_range(cfg, *BUILD)
        bm = show(bdf, cfg.capital)
        summarize(bdf, cfg, "build")

        print("\n[FORWARD 2026 H1 — UNTOUCHED]")
        fdf = run_range(cfg, *FWD)
        fm = show(fdf, cfg.capital)
        summarize(fdf, cfg, "forward")

        print(f"\n>>> {name}")
        print(f"    BUILD  : n={bm.get('n',0)} WR={bm.get('wr',0):.0%} PF={bm.get('pf',0):.2f} "
              f"CAGR={bm.get('cagr',0):+.1%} maxDD={bm.get('maxdd',0):.0%}")
        print(f"    FORWARD: n={fm.get('n',0)} WR={fm.get('wr',0):.0%} PF={fm.get('pf',0):.2f} "
              f"totret={fm.get('tot_ret',0):+.1%} maxDD={fm.get('maxdd',0):.0%}")
