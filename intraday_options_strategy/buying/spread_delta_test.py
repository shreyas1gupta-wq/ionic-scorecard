"""User idea: BUY 0.7-delta call + SELL 0.3-delta call = delta-calibrated bull call
debit spread. Less theta (financed by the short OTM leg) + partial VRP capture, defined
risk, 1 buy + 1 sell. Tested on the regime-bull ORB trigger. Fixed 1 lot. Build + forward.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

import chain
from engine import _costs, STEP, _hhmm
from engine_regime import daily_features, mtf_5min_ma
from delta_test import bull_orb_trigger, pick_by_delta, yte, R, Q, LOT, SLIP
from options.bs_pricing import implied_vol


def sim_spread(cdf, k_long, k_short, t0, day, sl, tp, trail):
    """Long call k_long (0.7d) + short call k_short (0.3d, higher strike)."""
    def leg(k):
        return cdf[(cdf["strike"] == k) & (cdf["option_type"] == "CE")].set_index("t")[
            ["open", "close"]].sort_index()
    L, S = leg(k_long), leg(k_short)
    if L.empty or S.empty or k_short <= k_long:
        return None
    aL = L[L.index > t0]
    if aL.empty:
        return None
    entry_bar = aL.index[0]
    long_e = aL.iloc[0]["open"]
    aS = S[S.index >= entry_bar]
    short_e = aS.iloc[0]["open"] if not aS.empty else 0.0
    debit = long_e - short_e
    if debit <= 0:
        return None
    width = k_short - k_long
    fill_debit = long_e * (1 + SLIP) - short_e * (1 - SLIP)
    if fill_debit <= 0:
        return None
    net = (L["close"] - S["close"].reindex(L.index).ffill())
    net = net[net.index >= entry_bar]
    tgt = debit + tp * (width - debit)       # capture tp-fraction of max profit
    stp = debit * (1 - sl)
    eod = _hhmm(day, "15:15")
    peak = debit
    ex_t = ex_v = reason = None
    for t, v in net.items():
        if t <= entry_bar:
            continue
        if t >= eod:
            ex_t, ex_v, reason = t, v, "eod"; break
        if v >= tgt:
            ex_t, ex_v, reason = t, v, "target"; break
        if v <= stp:
            ex_t, ex_v, reason = t, v, "stop"; break
        if trail > 0:
            peak = max(peak, v)
            if peak > debit and v <= peak * (1 - trail):
                ex_t, ex_v, reason = t, v, "trail"; break
    if ex_t is None:
        ex_t, ex_v, reason = net.index[-1], float(net.iloc[-1]), "eod"
    fill_exit = min(max(ex_v, 0.0), width)
    gross = (fill_exit - fill_debit) * LOT
    costs = _costs(fill_debit, max(fill_exit, 0.0), 1, LOT, True)
    net_pnl = gross - costs
    return {"day": day, "k_long": k_long, "k_short": k_short, "width": width,
            "debit": fill_debit, "reason": reason, "net_pnl": net_pnl,
            "win": net_pnl > 0, "ret_pct": fill_exit / fill_debit - 1,
            "maxloss": fill_debit * LOT}


def run(start, end, sl=0.5, tp=0.8, trail=0.4):
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
        s0, T = price, yte(t0, exp)
        atmk = min(avail, key=lambda x: abs(x - round(s0 / STEP) * STEP))
        ce = cdf[(cdf["strike"] == atmk) & (cdf["option_type"] == "CE")]
        ce = ce[ce["t"] <= t0]
        iv = 0.13
        if not ce.empty:
            e = implied_vol(ce["close"].iloc[-1], s0, atmk, T, R, Q, True)
            if np.isfinite(e) and 0.03 < e < 1.5:
                iv = e
        k_long = pick_by_delta(cdf, s0, T, iv, 0.70, avail)
        k_short = pick_by_delta(cdf, s0, T, iv, 0.30, avail)
        tr = sim_spread(cdf, k_long, k_short, t0, day, sl, tp, trail)
        if tr:
            rows.append(tr)
    return pd.DataFrame(rows)


def rep(df, label):
    if df.empty:
        print(f"  {label}: no trades"); return
    wr = df["win"].mean(); net = df["net_pnl"].sum()
    w = df[df["net_pnl"] > 0]["net_pnl"]; l = df[df["net_pnl"] <= 0]["net_pnl"]
    pf = w.sum() / abs(l.sum()) if l.sum() != 0 else np.inf
    print(f"  {label}: n={len(df)} WR={wr:.0%} net=Rs.{net:,.0f} PF={pf:.2f} "
          f"avg=Rs.{df['net_pnl'].mean():,.0f} avg_debit={df['debit'].mean():.1f} "
          f"avg_maxloss=Rs.{df['maxloss'].mean():,.0f} reasons={df['reason'].value_counts().to_dict()}")


if __name__ == "__main__":
    print("=== BUY 0.7d + SELL 0.3d bull call spread, regime-bull ORB ===")
    b = run(dt.date(2021, 1, 1), dt.date(2025, 12, 31))
    rep(b, "BUILD")
    f = run(dt.date(2026, 1, 1), dt.date(2026, 6, 2))
    rep(f, "FWD  ")
    if not b.empty:
        print(f"\n  vs naked 0.5d long build net was -Rs.57,922; naked 0.7d -Rs.102,074")
