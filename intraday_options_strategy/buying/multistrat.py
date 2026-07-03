"""Multi-strategy mix: can combining sleeves reach Sharpe>2? The answer is all about
CORRELATION. Build daily P&L for each sleeve, show the correlation matrix, then combine
(risk-parity) and measure portfolio Sharpe vs the standalone sleeves. Build + forward.

Sleeves:
  A  Intraday CE-selling (>20DMA + 2.5x stop)         short-vol, short-delta
  B  Weekly short strangle (naked, Δ0.18)             short-vol, delta-neutral
  C  Overnight drift (hold NIFTY close->next open)    LONG-delta, different driver
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

import chain
import sell_ce_enhanced as sce
import engine_sell as es

pd.set_option("display.width", 200)
START, SPLIT, END = dt.date(2021, 1, 1), dt.date(2025, 12, 31), dt.date(2026, 6, 2)
NOTIONAL = 3_00_000.0


def daily_index():
    spot = chain.load_index()
    days = sorted({d for d in spot.index.date if START <= d <= END})
    return pd.DatetimeIndex(pd.to_datetime(days))


def sleeve_A():
    df = sce.run(sce.Cfg(stop_mult=2.5), START, END)
    s = df.groupby(df["day"])["net_pnl"].sum()
    s.index = pd.to_datetime(s.index)
    return s


def sleeve_B():
    df, _ = es.run(es.SellCfg(structure="strangle"), START, END)
    s = df.groupby(df["exp"])["net_pnl"].sum()   # realize at expiry
    s.index = pd.to_datetime(s.index)
    return s


def sleeve_C():
    spot = chain.load_index()
    g = spot.groupby(spot.index.date)
    d = pd.DataFrame({"open": g["open"].first(), "close": g["close"].last()})
    d.index = pd.to_datetime([pd.Timestamp(x) for x in d.index])
    c2o = d["open"].shift(-1) / d["close"] - 1        # overnight return, realized next open
    pnl = (c2o * NOTIONAL).shift(1)                    # assign to the day it's realized
    return pnl.dropna()


def ann_sharpe(x):
    x = x.dropna()
    return x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0.0


def maxdd(cum):
    peak = np.maximum.accumulate(cum)
    return float(((cum - peak) / np.maximum(peak, 1)).min())


if __name__ == "__main__":
    idx = daily_index()
    A = sleeve_A().reindex(idx).fillna(0.0)
    B = sleeve_B().reindex(idx).fillna(0.0)
    C = sleeve_C().reindex(idx).fillna(0.0)
    M = pd.DataFrame({"A_CEsell": A, "B_strangle": B, "C_overnight": C})

    print("=== standalone sleeves (rupees/day, fixed sizing) ===")
    for c in M.columns:
        s = M[c]
        print(f"  {c:12s}: ann.Sharpe {ann_sharpe(s):5.2f} | net Rs.{s.sum():>10,.0f} "
              f"| maxDD {maxdd(s.cumsum()):.0%} | active days {int((s!=0).sum())}")

    print("\n=== CORRELATION of daily P&L (the whole game) ===")
    # correlation only over days where >=1 sleeve active (avoid 0-inflation)
    act = M[(M != 0).any(axis=1)]
    print(act.corr().round(2).to_string())

    # risk-parity combine: scale each to unit daily std, equal-weight
    stds = M.std().replace(0, np.nan)
    Z = M / stds
    combo = Z.mean(axis=1)                       # equal vol contribution
    # also short-vol-only combo (A+B) for contrast
    combo_sv = (M[["A_CEsell", "B_strangle"]] / stds[["A_CEsell", "B_strangle"]]).mean(axis=1)

    def report(series, name):
        b = series[series.index.date <= SPLIT]
        f = series[series.index.date > SPLIT]
        print(f"  {name:22s}: ALL Sharpe {ann_sharpe(series):4.2f} | "
              f"BUILD {ann_sharpe(b):4.2f} | FWD {ann_sharpe(f):4.2f} | "
              f"maxDD {maxdd(series.cumsum()):.0%}")

    print("\n=== combined portfolios (risk-parity, ann. Sharpe) ===")
    report(combo_sv, "short-vol only (A+B)")
    report(combo, "A+B+C (add overnight)")
    # optimize simple weights on BUILD for max Sharpe (then check FWD) — coarse
    best = None
    bser = None
    for wa in np.arange(0, 1.01, 0.2):
        for wb in np.arange(0, 1.01 - wa + 1e-9, 0.2):
            wc = 1 - wa - wb
            if wc < -1e-9:
                continue
            s = wa * Z["A_CEsell"] + wb * Z["B_strangle"] + wc * Z["C_overnight"]
            bs = ann_sharpe(s[s.index.date <= SPLIT])
            if best is None or bs > best[0]:
                best = (bs, wa, wb, wc); bser = s
    print(f"\n  best BUILD-Sharpe weights: A={best[1]:.1f} B={best[2]:.1f} C={best[3]:.1f}")
    report(bser, "best-weight mix")
    print("\nNote: Sharpe annualized from daily P&L. Diversification only helps to the "
          "extent sleeves are UNcorrelated — see the matrix above.")
