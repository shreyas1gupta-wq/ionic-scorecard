"""Test user's ideas: (A) delta-based strike selection (0.3/0.5/0.7 delta) with strict
SL + convex exits on the best trigger (regime-aligned bull long); (B) overnight-hold
edge (enter at close, exit next open) as a spot diagnostic.
Real BS deltas (ATM-implied IV), real option fills, fixed 1 lot, build + forward.
"""
from __future__ import annotations

import datetime as dt
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from options.bs_pricing import bs_greeks, implied_vol  # noqa: E402

import chain  # noqa: E402
from engine import _costs, STEP, _ema, _atr, _hhmm  # noqa: E402
from engine_regime import daily_features, mtf_5min_ma  # noqa: E402

LOT, SLIP = 75, 0.005
R, Q = 0.065, 0.012


def yte(t0, exp):
    ex = pd.Timestamp(exp) + pd.Timedelta(hours=15, minutes=30)
    return max((ex - t0).total_seconds() / (365.25 * 24 * 3600), 1e-5)


def bull_orb_trigger(sd, day, orb_min=15):
    if len(sd) < 120:
        return None
    or_end = _hhmm(day, "09:15") + pd.Timedelta(minutes=orb_min)
    orng = sd[sd.index < or_end]
    if orng.empty:
        return None
    hi = orng["high"].max()
    ema9, ema21 = _ema(sd["close"], 9), _ema(sd["close"], 21)
    win = sd[(sd.index >= max(or_end, _hhmm(day, "09:30"))) & (sd.index <= _hhmm(day, "14:30"))]
    brk = win[(win["close"] > hi) & (ema9.reindex(win.index) > ema21.reindex(win.index))]
    return brk.index[0] if not brk.empty else None


def pick_by_delta(cdf, s0, T, iv, target, avail):
    best, bd = None, 9e9
    for k in avail:
        d = float(bs_greeks(s0, k, T, iv, R, Q, True)["delta"])
        if abs(d - target) < bd:
            bd, best = abs(d - target), k
    return best


def sim_call(cdf, k, t0, day, sl, tp, trail):
    leg = cdf[(cdf["strike"] == k) & (cdf["option_type"] == "CE")].set_index("t")[
        ["open", "high", "low", "close"]].sort_index()
    after = leg[leg.index > t0]
    if after.empty:
        return None
    entry = after.iloc[0]["open"]
    if not np.isfinite(entry) or entry <= 0:
        return None
    fill = entry * (1 + SLIP)
    tgt, stp = entry * (1 + tp), entry * (1 - sl)
    eod = _hhmm(day, "15:15")
    peak = entry
    ex_v = reason = None
    ex_t = None
    for t, row in after.iterrows():
        if t >= eod:
            ex_v, reason, ex_t = row["close"], "eod", t; break
        if row["close"] >= tgt:
            ex_v, reason, ex_t = tgt, "target", t; break
        if row["close"] <= stp:
            ex_v, reason, ex_t = stp, "stop", t; break
        if trail > 0:
            peak = max(peak, row["close"])
            if peak > entry and row["close"] <= peak * (1 - trail):
                ex_v, reason, ex_t = row["close"], "trail", t; break
    if ex_v is None:
        ex_v, reason, ex_t = after.iloc[-1]["close"], "eod", after.index[-1]
    fx = max(ex_v, 0.0) * (1 - SLIP)
    net = (fx - fill) * LOT - _costs(fill, max(fx, 0.0), 1, LOT, False)
    return {"day": day, "strike": k, "ret_pct": fx / fill - 1, "net_pnl": net,
            "win": net > 0, "reason": reason, "entry": entry}


def run_delta(target, start, end, sl=0.35, tp=1.0, trail=0.4):
    spot = chain.load_index()
    dfeat = daily_features(spot)
    ma5 = mtf_5min_ma(spot)
    days = sorted({d for d in spot.index.date if start <= d <= end})
    rows = []
    for day in days:
        ts = pd.Timestamp(day)
        if ts not in dfeat.index or dfeat.loc[ts, "regime"] != "bull":
            continue
        if not (dfeat.loc[ts, "rsi5_prev"] > 50):
            continue
        sd = spot[spot.index.date == day]
        t0 = bull_orb_trigger(sd, day)
        if t0 is None:
            continue
        price = sd.asof(t0)["close"]
        mv = ma5.asof(t0)
        if pd.isna(mv) or not (price > mv):
            continue
        exp = chain.nearest_expiry(day, 0, 7)
        if exp is None:
            continue
        cdf = chain.day_chain(exp, day)
        if cdf.empty:
            continue
        avail = sorted(cdf["strike"].unique())
        s0 = price
        T = yte(t0, exp)
        atmk = min(avail, key=lambda x: abs(x - round(s0 / STEP) * STEP))
        ce_atm = cdf[(cdf["strike"] == atmk) & (cdf["option_type"] == "CE")]
        ce_atm = ce_atm[ce_atm["t"] <= t0]
        iv = 0.13
        if not ce_atm.empty:
            iv_est = implied_vol(ce_atm["close"].iloc[-1], s0, atmk, T, R, Q, True)
            if np.isfinite(iv_est) and 0.03 < iv_est < 1.5:
                iv = iv_est
        k = pick_by_delta(cdf, s0, T, iv, target, avail)
        tr = sim_call(cdf, k, t0, day, sl, tp, trail)
        if tr:
            rows.append(tr)
    return pd.DataFrame(rows)


def rep(df, label):
    if df.empty:
        print(f"  {label}: no trades"); return
    wr = df["win"].mean()
    net = df["net_pnl"].sum()
    wins = df[df["net_pnl"] > 0]["net_pnl"]; los = df[df["net_pnl"] <= 0]["net_pnl"]
    pf = wins.sum() / abs(los.sum()) if los.sum() != 0 else np.inf
    print(f"  {label}: n={len(df)} WR={wr:.0%} net=Rs.{net:,.0f} PF={pf:.2f} "
          f"avg={df['net_pnl'].mean():,.0f} maxwin={df['net_pnl'].max():,.0f} "
          f"reasons={df['reason'].value_counts().to_dict()}")


def overnight_edge():
    """Enter at close, exit next open: spot close-to-open return by regime."""
    spot = chain.load_index()
    g = spot.groupby(spot.index.date)
    d = pd.DataFrame({"open": g["open"].first(), "close": g["close"].last()})
    d.index = pd.to_datetime(d.index)
    dfeat = daily_features(spot)
    d["regime"] = dfeat["regime"]
    d["c2o"] = d["open"].shift(-1) / d["close"] - 1   # overnight return
    b = d[d.index.date <= dt.date(2025, 12, 31)]
    print("\n=== OVERNIGHT close->next-open spot return (build) ===")
    print(f"ALL: mean {b['c2o'].mean():+.3%}  hit {(b['c2o']>0).mean():.0%}  n={b['c2o'].notna().sum()}")
    for reg in ["bull", "bear", "neutral"]:
        s = b[b["regime"] == reg]["c2o"].dropna()
        print(f"{reg}: mean {s.mean():+.3%}  hit {(s>0).mean():.0%}  n={len(s)}")
    print("Option overnight-buy needs mean >> ~+0.3% to beat 1 day theta+gap. ")


if __name__ == "__main__":
    print("=== (A) DELTA SELECTION on regime-bull ORB (strict SL, convex exits) ===")
    for tgt in (0.30, 0.50, 0.70):
        print(f"\n-- target delta {tgt} --")
        b = run_delta(tgt, dt.date(2021, 1, 1), dt.date(2025, 12, 31))
        rep(b, "BUILD")
        f = run_delta(tgt, dt.date(2026, 1, 1), dt.date(2026, 6, 2))
        rep(f, "FWD  ")
    overnight_edge()
