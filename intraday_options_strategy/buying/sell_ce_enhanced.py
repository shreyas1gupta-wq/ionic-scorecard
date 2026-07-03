"""Sell CE (spot>20DMA) enhanced: add RSI filter (skip oversold -> bounce risk) and
an intraday STOP-LOSS (cut when CE rises to stop_mult x entry) to crush the -21% MDD.
Log-scale PnL graph. Enter 09:20, exit EOD. Build 2021-2025 + forward 2026 H1.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import chain
from engine import (BROKERAGE_PER_ORDER, STT_SELL_PCT, EXCH_TXN_PCT, GST_PCT,
                    SEBI_PER_CRORE, STAMP_BUY_PCT, STEP)

LOT, SLIP = 75, 0.005
CAP = 3_00_000.0


@dataclass
class Cfg:
    stop_mult: float = 0.0     # 0=off; else exit short if CE >= entry*stop_mult
    rsi_min: float = 0.0       # 0=off; else skip days with prior RSI14 < rsi_min
    entry: str = "09:20"
    exit: str = "15:20"


def short_costs(sell_prem, buy_prem):
    qty = LOT
    brok = BROKERAGE_PER_ORDER * 2
    turnover = (sell_prem + buy_prem) * qty
    exch = EXCH_TXN_PCT * turnover
    stt = STT_SELL_PCT * (sell_prem * qty)
    gst = GST_PCT * (brok + exch)
    sebi = SEBI_PER_CRORE * turnover / 1e7
    stamp = STAMP_BUY_PCT * (buy_prem * qty)
    return brok + exch + stt + gst + sebi + stamp


def _rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def daily_ctx(spot):
    g = spot.groupby(spot.index.date)
    d = pd.DataFrame({"close": g["close"].last()})
    d.index = [pd.Timestamp(x).date() for x in d.index]
    d["ma20"] = d["close"].rolling(20).mean().shift(1)
    d["rsi14"] = _rsi(d["close"], 14).shift(1)
    return d


def _t(day, hhmm):
    return pd.Timestamp(day) + pd.Timedelta(hours=int(hhmm[:2]), minutes=int(hhmm[3:]))


def run(cfg: Cfg, start, end):
    spot = chain.load_index()
    dc = daily_ctx(spot)
    days = sorted({d for d in spot.index.date if start <= d <= end})
    rows = []
    for day in days:
        if day not in dc.index or pd.isna(dc.loc[day, "ma20"]):
            continue
        sd = spot[spot.index.date == day]
        et = _t(day, cfg.entry)
        se = sd[sd.index <= et]
        if se.empty:
            continue
        s0 = se["close"].iloc[-1]
        if not (s0 > dc.loc[day, "ma20"]):          # spot > 20DMA only
            continue
        if cfg.rsi_min > 0 and not (dc.loc[day, "rsi14"] >= cfg.rsi_min):
            continue                                 # skip oversold (bounce risk)
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
            ["open", "high", "low", "close"]].sort_index()
        le = leg[leg.index >= et]
        if le.empty:
            continue
        entry_px = le.iloc[0]["open"]
        if entry_px <= 0 or not np.isfinite(entry_px):
            continue
        xt = _t(day, cfg.exit)
        path = le[le.index <= xt]
        exit_px, reason = None, "eod"
        if cfg.stop_mult > 0:
            stop_lvl = entry_px * cfg.stop_mult
            hit = path[path["close"] >= stop_lvl]
            if not hit.empty:
                exit_px, reason = hit.iloc[0]["close"], "stop"
        if exit_px is None:
            exit_px = path["close"].iloc[-1]
        sell_fill = entry_px * (1 - SLIP)
        buy_fill = exit_px * (1 + SLIP)
        net = (sell_fill - buy_fill) * LOT - short_costs(entry_px, exit_px)
        rows.append({"day": day, "dte": dte, "strike": k, "entry": entry_px,
                     "exit": exit_px, "reason": reason, "net_pnl": net, "win": net > 0})
    return pd.DataFrame(rows)


def stats(df, label):
    if df.empty:
        print(f"  {label}: no trades"); return None
    df = df.sort_values("day")
    net = df["net_pnl"].sum()
    eq = CAP + df["net_pnl"].cumsum().values
    dd = ((eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)).min()
    r = df["net_pnl"] / CAP
    yrs = (df["day"].iloc[-1] - df["day"].iloc[0]).days / 365.25 + 1e-9
    tpy = len(df) / yrs
    sharpe = r.mean() / r.std() * np.sqrt(tpy) if r.std() > 0 else 0
    w = df[df["net_pnl"] > 0]["net_pnl"]; l = df[df["net_pnl"] <= 0]["net_pnl"]
    pf = w.sum() / abs(l.sum()) if l.sum() != 0 else np.inf
    print(f"  {label}: n={len(df)} WR={df['win'].mean():.0%} net=Rs.{net:,.0f} PF={pf:.2f} "
          f"tot={net/CAP:+.1%} maxDD={dd:.0%} Sharpe={sharpe:.2f} worst=Rs.{df['net_pnl'].min():,.0f} "
          f"stops={(df['reason']=='stop').sum()}")
    return df


def plot_log(build, fwd, path):
    both = pd.concat([build, fwd]).sort_values("day")
    eq = CAP + both["net_pnl"].cumsum().values
    x = pd.to_datetime(both["day"].values)
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(x, eq, lw=1.5, color="#1f77b4")
    ax.axhline(CAP, color="black", lw=0.7, alpha=0.4)
    if len(fwd):
        ax.axvline(pd.Timestamp(2026, 1, 1), color="gray", ls="--", lw=1)
        ax.text(pd.Timestamp(2026, 1, 1), eq.min(), " forward >", color="gray", fontsize=9)
    ax.set_yscale("log")
    ax.set_title("Sell CE (spot>20DMA) + RSI filter + intraday stop — LOG-scale equity",
                 fontsize=12, fontweight="bold")
    ax.set_ylabel("Equity (Rs., log scale)")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"\nsaved log-scale graph: {path}")


if __name__ == "__main__":
    variants = {
        "base (>20DMA, no filter/stop)": Cfg(),
        "+ intraday stop 2.5x":          Cfg(stop_mult=2.5),
        "+ RSI>=40 (skip oversold)":     Cfg(rsi_min=40),
        "+ stop 2.5x + RSI>=40":         Cfg(stop_mult=2.5, rsi_min=40),
    }
    best_key = "+ stop 2.5x + RSI>=40"
    best_b = best_f = None
    for name, cfg in variants.items():
        print(f"\n### {name}")
        b = run(cfg, dt.date(2021, 1, 1), dt.date(2025, 12, 31))
        bs = stats(b, "BUILD")
        f = run(cfg, dt.date(2026, 1, 1), dt.date(2026, 6, 2))
        fs = stats(f, "FWD  ")
        if name == best_key:
            best_b, best_f = bs, fs
    if best_b is not None:
        plot_log(best_b, best_f if best_f is not None else best_b.iloc[0:0],
                 r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
                 r"\NIFTY 500\intraday_options_strategy\buying\sell_ce_pnl_log.png")
