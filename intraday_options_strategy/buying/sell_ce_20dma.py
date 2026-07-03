"""User strategy: sell 1% OTM NIFTY CE intraday (0.5% OTM on 0/1 DTE), enter ~09:20,
exit at EOD. Split by regime: spot ABOVE vs BELOW 20-DMA (tested separately).
Fixed 1 lot, real prices, short-side costs. Build 2021-2025 + forward 2026 H1.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

import chain
from engine import (BROKERAGE_PER_ORDER, STT_SELL_PCT, EXCH_TXN_PCT, GST_PCT,
                    SEBI_PER_CRORE, STAMP_BUY_PCT, STEP)

LOT, SLIP = 75, 0.005
ENTRY, EXIT = "09:20", "15:20"


def short_costs(sell_prem, buy_prem, lots=1):
    qty = lots * LOT
    brok = BROKERAGE_PER_ORDER * 2
    turnover = (sell_prem + buy_prem) * qty
    exch = EXCH_TXN_PCT * turnover
    stt = STT_SELL_PCT * (sell_prem * qty)     # STT on the sell (entry) premium
    gst = GST_PCT * (brok + exch)
    sebi = SEBI_PER_CRORE * turnover / 1e7
    stamp = STAMP_BUY_PCT * (buy_prem * qty)   # stamp on buy (exit)
    return brok + exch + stt + gst + sebi + stamp


def daily_ma20(spot):
    g = spot.groupby(spot.index.date)
    d = pd.DataFrame({"close": g["close"].last()})
    d.index = [pd.Timestamp(x).date() for x in d.index]
    d["ma20"] = d["close"].rolling(20).mean().shift(1)   # prior-day MA -> no lookahead
    return d


def _t(day, hhmm):
    return pd.Timestamp(day) + pd.Timedelta(hours=int(hhmm[:2]), minutes=int(hhmm[3:]))


def run(start, end):
    spot = chain.load_index()
    dma = daily_ma20(spot)
    days = sorted({d for d in spot.index.date if start <= d <= end})
    rows = []
    for day in days:
        if day not in dma.index or pd.isna(dma.loc[day, "ma20"]):
            continue
        sd = spot[spot.index.date == day]
        et = _t(day, ENTRY)
        se = sd[sd.index <= et]
        if se.empty:
            continue
        s0 = se["close"].iloc[-1]
        ma20 = dma.loc[day, "ma20"]
        regime = "above" if s0 > ma20 else "below"
        exp = chain.nearest_expiry(day, 0, 7)
        if exp is None:
            continue
        dte = (exp - day).days
        otm = 0.005 if dte <= 1 else 0.01
        cdf = chain.day_chain(exp, day)
        if cdf.empty:
            continue
        avail = sorted(cdf["strike"].unique())
        k = min(avail, key=lambda x: abs(x - round(s0 * (1 + otm) / STEP) * STEP))
        leg = cdf[(cdf["strike"] == k) & (cdf["option_type"] == "CE")].set_index("t")[
            ["open", "close"]].sort_index()
        le = leg[leg.index >= et]
        if le.empty:
            continue
        entry_px = le.iloc[0]["open"]
        xt = _t(day, EXIT)
        lx = leg[leg.index <= xt]
        if lx.empty or entry_px <= 0 or not np.isfinite(entry_px):
            continue
        exit_px = lx["close"].iloc[-1]
        sell_fill = entry_px * (1 - SLIP)     # you receive
        buy_fill = exit_px * (1 + SLIP)       # you pay to close
        gross = (sell_fill - buy_fill) * LOT
        costs = short_costs(entry_px, exit_px)
        net = gross - costs
        rows.append({"day": day, "regime": regime, "dte": dte, "otm": otm,
                     "strike": k, "entry": entry_px, "exit": exit_px,
                     "net_pnl": net, "win": net > 0})
    return pd.DataFrame(rows)


def rep(df, cap, label):
    if df.empty:
        print(f"  {label}: no trades"); return
    for reg in ["above", "below"]:
        g = df[df["regime"] == reg]
        if g.empty:
            continue
        wr = g["win"].mean(); net = g["net_pnl"].sum()
        w = g[g["net_pnl"] > 0]["net_pnl"]; l = g[g["net_pnl"] <= 0]["net_pnl"]
        pf = w.sum() / abs(l.sum()) if l.sum() != 0 else np.inf
        g2 = g.sort_values("day")
        eq = cap + g2["net_pnl"].cumsum().values
        dd = ((eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)).min()
        r = g2["net_pnl"] / cap
        tpy = len(g) / (((g2["day"].iloc[-1] - g2["day"].iloc[0]).days) / 365.25 + 1e-9)
        sharpe = r.mean() / r.std() * np.sqrt(tpy) if r.std() > 0 and len(g) > 2 else 0
        print(f"  {label} [{reg} 20DMA]: n={len(g)} WR={wr:.0%} net=Rs.{net:,.0f} "
              f"PF={pf:.2f} tot={net/cap:+.1%} maxDD={dd:.0%} Sharpe={sharpe:.2f} "
              f"worst=Rs.{g['net_pnl'].min():,.0f}")


if __name__ == "__main__":
    CAP = 3_00_000.0
    print("=== SELL 1% OTM CE (0.5% on 0/1 DTE), enter 09:20 exit EOD, by 20DMA regime ===")
    b = run(dt.date(2021, 1, 1), dt.date(2025, 12, 31))
    print("\n[BUILD 2021-2025]"); rep(b, CAP, "BUILD")
    f = run(dt.date(2026, 1, 1), dt.date(2026, 6, 2))
    print("\n[FORWARD 2026 H1]"); rep(f, CAP, "FWD")
