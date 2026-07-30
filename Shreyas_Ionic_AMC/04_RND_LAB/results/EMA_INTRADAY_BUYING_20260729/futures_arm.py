"""Futures arm: the SAME intraday EMA signal traded as a delta-1 index-equivalent
position (no theta, no VRP drag). Purpose is diagnostic, not a product:

  - futures FAIL  -> the SIGNAL is dead; no option structure can rescue it.
  - futures PASS but options fail -> instrument drag (theta+VRP+spread) is the binding
    constraint, and the honest conclusion is "trade the signal delta-1, not by buying options".

Intraday only: entry on the bar after the cross, mandatory flat 15:25, opposite-cross exit,
optional stop. Costs = NIFTY futures retail intraday (see COSTS below).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from stage1_signal_test import (BUILD_END, ENTRY_END, ENTRY_START, FLAT_BY, GRID,
                                load_spot, nw_tstat, resample, signals)

OUT = Path(__file__).parent

LOT = 75
# NIFTY futures retail intraday costs, per round trip, as a fraction of notional.
# brokerage Rs20/order (2 orders), exch txn ~0.0019% + GST18%, stamp 0.002% buy,
# STT futures sell 0.02% (2025 schedule), SEBI Rs10/cr, slippage 1 tick ~0.25pt each way.
STT_FUT_SELL = 0.02 / 100
EXCH_TXN_FUT = 0.0019 / 100
GST = 0.18
STAMP_BUY_FUT = 0.002 / 100
SEBI_PER_CR = 10.0
BROKERAGE_PER_ORDER = 20.0
SLIP_POINTS_PER_SIDE = 0.25          # 1 tick; NIFTY fut is the most liquid contract on NSE
STOP_PCT = 0.004                     # 0.4% adverse move on the index -> cut (tested vs none)


def rt_cost_rupees(entry_px: float, exit_px: float, lots: int = 1) -> float:
    qty = lots * LOT
    brok = BROKERAGE_PER_ORDER * 2
    turnover = (entry_px + exit_px) * qty
    exch = EXCH_TXN_FUT * turnover
    stt = STT_FUT_SELL * (exit_px * qty)
    gst = GST * (brok + exch)
    stamp = STAMP_BUY_FUT * (entry_px * qty)
    sebi = SEBI_PER_CR * turnover / 1e7
    return brok + exch + stt + gst + sebi + stamp


def run_cell(spot: pd.DataFrame, rule: str, fast: int, slow: int, use_stop: bool) -> pd.DataFrame:
    bars = resample(spot, rule)
    sig = signals(bars, fast, slow)
    if sig.empty:
        return pd.DataFrame()
    sig["date"] = pd.to_datetime(sig["t"]).dt.date
    # opposite-cross exit: within a day, a position is closed by the next signal of either dir
    by_day_sig = {d: g.sort_values("t") for d, g in sig.groupby("date")}
    by_day_spot = {d: g for d, g in spot.groupby(spot.index.date)}
    rows = []
    for d, sg in by_day_sig.items():
        day = by_day_spot.get(d)
        if day is None:
            continue
        flat_t = pd.Timestamp(d) + pd.Timedelta(hours=int(FLAT_BY[:2]),
                                                minutes=int(FLAT_BY[3:]))
        times = sg["t"].tolist()
        for i, (t0, sgn) in enumerate(zip(times, sg["dir"].tolist())):
            fwd = day[(day.index > t0) & (day.index <= flat_t)]
            if fwd.empty:
                continue
            e = float(fwd["open"].iloc[0])
            if not np.isfinite(e) or e <= 0:
                continue
            # exit at: next opposite/any signal, stop, or mandatory flat
            hard_t = times[i + 1] if i + 1 < len(times) else flat_t
            seg = fwd[fwd.index <= hard_t]
            if seg.empty:
                continue
            reason, x = "signal_or_flat", float(seg["close"].iloc[-1])
            if use_stop:
                if sgn > 0:
                    hit = seg.index[seg["low"] <= e * (1 - STOP_PCT)]
                else:
                    hit = seg.index[seg["high"] >= e * (1 + STOP_PCT)]
                if len(hit):
                    reason = "stop"
                    x = e * (1 - STOP_PCT) if sgn > 0 else e * (1 + STOP_PCT)
            gross_pts = sgn * (x - e) - 2 * SLIP_POINTS_PER_SIDE
            gross = gross_pts * LOT
            cost = rt_cost_rupees(e, x)
            rows.append({"date": d, "t": t0, "dir": sgn, "entry": e, "exit": x,
                         "reason": reason, "gross_pts": gross_pts,
                         "gross": gross, "cost": cost, "net": gross - cost,
                         "notional": e * LOT})
    return pd.DataFrame(rows)


def metrics(df: pd.DataFrame, label: str, capital: float = 3_00_000.0) -> dict:
    if df.empty or len(df) < 10:
        return {"label": label, "n": int(len(df))}
    net = df["net"]
    daily = df.groupby("date")["net"].sum()
    eq = capital + daily.cumsum()
    peak = eq.cummax()
    mdd = float(((eq - peak) / peak).min())
    yrs = max((max(df["date"]) - min(df["date"])).days / 365.25, 0.01)
    total = float(net.sum())
    cagr = (eq.iloc[-1] / capital) ** (1 / yrs) - 1 if eq.iloc[-1] > 0 else float("nan")
    dr = daily / capital
    sharpe = float(dr.mean() / dr.std() * np.sqrt(252)) if dr.std() > 0 else float("nan")
    wins, losses = net[net > 0], net[net <= 0]
    pf = float(wins.sum() / abs(losses.sum())) if losses.sum() != 0 else float("inf")
    m = df.copy()
    m["ym"] = pd.to_datetime(m["date"]).dt.to_period("M")
    monthly = m.groupby("ym")["net"].sum()
    return {
        "label": label, "n": int(len(df)), "trading_days": int(len(daily)),
        "net_rupees": round(total), "gross_rupees": round(float(df["gross"].sum())),
        "costs_rupees": round(float(df["cost"].sum())),
        "mean_pts_per_trade": round(float(df["gross_pts"].mean()), 3),
        "hit_rate": round(float((net > 0).mean()), 4),
        "t_nw": round(float(nw_tstat(daily.values)), 3),
        "CAGR_pct": round(100 * float(cagr), 2), "maxDD_pct": round(100 * mdd, 2),
        "Calmar": round(float(cagr / abs(mdd)), 2) if mdd else None,
        "Sharpe": round(sharpe, 2), "PF": round(pf, 2),
        "months": int(len(monthly)),
        "months_positive": int((monthly > 0).sum()),
        "month_win_rate": round(float((monthly > 0).mean()), 4),
        "worst_month_rupees": round(float(monthly.min())),
        "best_month_rupees": round(float(monthly.max())),
        "max_single_trade_share": round(float(net.abs().max() / abs(total)), 4) if total else None,
    }


def main():
    spot = load_spot()
    print(f"[spot] {len(spot):,} bars", flush=True)
    report = {"note": "delta-1 futures arm; diagnostic for signal-vs-instrument-drag",
              "stop_pct": STOP_PCT, "cells": []}
    for rule, fast, slow in GRID:
        for use_stop in (False, True):
            name = f"{rule}_EMA{fast}_{slow}{'_stop' if use_stop else '_nostop'}"
            df = run_cell(spot, rule, fast, slow, use_stop)
            if df.empty:
                print(f"  {name}: no trades"); continue
            b = df[df["date"] <= BUILD_END]
            f = df[df["date"] > BUILD_END]
            cell = {"cell": name, "build": metrics(b, "build"),
                    "forward_2026H1": metrics(f, "forward") if len(f) else None}
            report["cells"].append(cell)
            bm = cell["build"]
            print(f"  {name}: n={bm['n']} pts/trade={bm.get('mean_pts_per_trade')} "
                  f"CAGR={bm.get('CAGR_pct')}% MDD={bm.get('maxDD_pct')}% "
                  f"Sharpe={bm.get('Sharpe')} PF={bm.get('PF')} t={bm.get('t_nw')} "
                  f"months+={bm.get('months_positive')}/{bm.get('months')}", flush=True)
            fm = cell["forward_2026H1"]
            if fm and fm.get("n", 0) >= 10:
                print(f"      forward: n={fm['n']} net={fm['net_rupees']} "
                      f"pts/trade={fm['mean_pts_per_trade']} PF={fm['PF']}", flush=True)
            df.to_csv(OUT / f"futures_{name}_trades.csv", index=False)
    (OUT / "futures_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nwrote futures_report.json", flush=True)


if __name__ == "__main__":
    main()
