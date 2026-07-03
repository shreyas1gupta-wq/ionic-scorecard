"""Small, disciplined config comparison on the BUILD set (2021-2025).
triggers x structures. Report total return, CAGR, PF, WR, trades/yr, maxDD.
Keep the grid tiny to avoid overfitting; 2026 stays untouched.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import replace

import numpy as np
import pandas as pd

from engine_swing import SwingCfg, run_range

BUILD_START = dt.date(2021, 1, 1)
BUILD_END = dt.date(2025, 12, 31)
YEARS = (BUILD_END - dt.date(2021, 5, 24)).days / 365.25


def metrics(df: pd.DataFrame, cap: float) -> dict:
    if df.empty:
        return {"n": 0}
    df = df.sort_values("exit_t")
    daily = df.groupby(df["exit_t"].dt.date)["net_pnl"].sum()
    eq = cap + daily.cumsum()
    peak = eq.cummax()
    dd = ((eq - peak) / peak).min()
    tot = df["net_pnl"].sum()
    cagr = (1 + tot / cap) ** (1 / YEARS) - 1
    wins = df[df["net_pnl"] > 0]["net_pnl"]
    losses = df[df["net_pnl"] <= 0]["net_pnl"]
    pf = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else np.inf
    # per-trade sharpe-ish (annualized by trades/yr)
    tpy = len(df) / YEARS
    r = df["ret_pct"]
    sharpe = (r.mean() / r.std() * np.sqrt(tpy)) if r.std() > 0 else 0
    return {"n": len(df), "tpy": tpy, "wr": (df["net_pnl"] > 0).mean(),
            "pf": pf, "tot_ret": tot / cap, "cagr": cagr, "maxdd": dd,
            "sharpe": sharpe, "avg_ret": r.mean(), "avg_hold": df["hold_days"].mean()}


CONFIGS = {
    "emacross_ATM":    dict(trigger="ema_cross", strike_offset=0, spread_width=0),
    "emacross_ITM2":   dict(trigger="ema_cross", strike_offset=-2, spread_width=0),
    "emacross_spr4":   dict(trigger="ema_cross", strike_offset=0, spread_width=4),
    "breakout_ATM":    dict(trigger="breakout20", strike_offset=0, spread_width=0),
    "breakout_ITM2":   dict(trigger="breakout20", strike_offset=-2, spread_width=0),
    "breakout_spr4":   dict(trigger="breakout20", strike_offset=0, spread_width=4),
    "bigday_ATM":      dict(trigger="bigday", strike_offset=0, spread_width=0),
    "bigday_ITM2":     dict(trigger="bigday", strike_offset=-2, spread_width=0),
    "bigday_spr4":     dict(trigger="bigday", strike_offset=0, spread_width=4),
}

if __name__ == "__main__":
    base = SwingCfg()
    rows = []
    for name, ov in CONFIGS.items():
        cfg = replace(base, **ov)
        df = run_range(cfg, BUILD_START, BUILD_END)
        m = metrics(df, cfg.capital)
        m["config"] = name
        rows.append(m)
        print(f"{name:16s} n={m.get('n',0):3d} "
              f"tpy={m.get('tpy',0):4.1f} wr={m.get('wr',0):.0%} "
              f"pf={m.get('pf',0):4.2f} totret={m.get('tot_ret',0):+.0%} "
              f"cagr={m.get('cagr',0):+.1%} maxdd={m.get('maxdd',0):.0%} "
              f"sharpe={m.get('sharpe',0):.2f}")
    r = pd.DataFrame(rows).set_index("config").sort_values("cagr", ascending=False)
    print("\nRanked by CAGR:")
    print(r[["n", "tpy", "wr", "pf", "tot_ret", "cagr", "maxdd", "sharpe"]].to_string())
