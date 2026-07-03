"""Exhaustive intraday edge hunt for MFT option-buying (secs->hours regime).

Measures, per intraday trigger, the SIGNED max-favorable-excursion (MFE) and
max-adverse-excursion (MAE) over the next H minutes -- what a trailing-exit buyer
actually harvests. For option buying to give big CAGR we need E[MFE] well above the
option breakeven (~0.3-0.5% spot) AND MFE >> |MAE| (convex, capturable).

Also conditions on: time-of-day, realized-vol regime, and trigger STRENGTH
(only very strong moves), to see if ANY sub-population has capturable convexity.
Build set 2021-2025 only.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

import chain

BUILD_END = dt.date(2025, 12, 31)


def _ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def _atr(df, n=14):
    pc = df["close"].shift(1)
    tr = pd.concat([(df["high"] - df["low"]).abs(), (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=1).mean()


def _t(day, hhmm):
    h, m = map(int, hhmm.split(":"))
    return pd.Timestamp(day) + pd.Timedelta(hours=h, minutes=m)


def day_signals(d, day):
    """Intraday breakout/momentum triggers with strength + context tags."""
    out = []
    if len(d) < 150:
        return out
    c = d["close"]
    ema9, ema21 = _ema(c, 9), _ema(c, 21)
    atr = _atr(d, 14)
    twap = c.expanding().mean()
    # realized vol regime (first-hour range as % of price)
    fh = d[d.index <= _t(day, "10:15")]
    fh_rng = (fh["high"].max() - fh["low"].min()) / c.iloc[0] if not fh.empty else np.nan

    for orb in (15, 30):
        or_end = _t(day, "09:15") + pd.Timedelta(minutes=orb)
        orng = d[d.index < or_end]
        if orng.empty:
            continue
        hi, lo = orng["high"].max(), orng["low"].min()
        win = d[(d.index >= or_end) & (d.index <= _t(day, "14:00"))]
        for direction, brk in ((1, win[win["close"] > hi]), (-1, win[win["close"] < lo])):
            g = brk[(_ema(c, 9).reindex(brk.index) > _ema(c, 21).reindex(brk.index)) == (direction == 1)]
            if g.empty:
                continue
            t0 = g.index[0]
            px0 = g.iloc[0]["close"]
            # strength: how far beyond the OR, in ATR units
            ref = hi if direction == 1 else lo
            strength = direction * (px0 - ref) / (atr.reindex([t0]).iloc[0] + 1e-9)
            out.append({"name": f"ORB{orb}", "t": t0, "dir": direction, "px": px0,
                        "strength": strength, "fh_rng": fh_rng})
    return out


def analyze():
    spot = chain.load_index()
    spot = spot[spot.index.date <= BUILD_END]
    days = sorted({d for d in spot.index.date})
    rows = []
    for day in days:
        d = spot[spot.index.date == day]
        if len(d) < 150:
            continue
        for s in day_signals(d, day):
            t, direction, px = s["t"], s["dir"], s["px"]
            hh = int(t.strftime("%H"))
            for H in (30, 60, 120):
                path = d[(d.index > t) & (d.index <= t + pd.Timedelta(minutes=H))]
                if path.empty:
                    continue
                # signed excursions using intrabar high/low
                if direction == 1:
                    mfe = (path["high"].max() / px - 1)
                    mae = (path["low"].min() / px - 1)
                else:
                    mfe = (px / path["low"].min() - 1)
                    mae = (px / path["high"].max() - 1)
                rows.append({"name": s["name"], "H": H, "hour": hh,
                             "strength": s["strength"], "fh_rng": s["fh_rng"],
                             "mfe": mfe, "mae": mae})
    df = pd.DataFrame(rows)
    print(f"[exhaustive] {df['name'].count()} signal-horizon rows, "
          f"{df.groupby(['name']).ngroups} triggers\n")

    def report(sub, label):
        if sub.empty:
            print(f"{label}: (empty)"); return
        g = sub.groupby("H").agg(n=("mfe", "size"), mfe=("mfe", "mean"),
                                 mae=("mae", "mean"),
                                 mfe_p75=("mfe", lambda x: x.quantile(0.75)),
                                 mfe_p90=("mfe", lambda x: x.quantile(0.90)))
        g["mfe/|mae|"] = g["mfe"] / g["mae"].abs()
        print(f"\n### {label}")
        fmt = {c: "{:+.3%}".format for c in ["mfe", "mae", "mfe_p75", "mfe_p90"]}
        fmt["mfe/|mae|"] = "{:.2f}".format
        print(g.to_string(formatters=fmt))

    print("=" * 70)
    print("ALL intraday breakout signals (MFE/MAE, signed):")
    report(df, "ALL triggers")
    print("\nBreakeven note: option ATM needs ~+0.3-0.5% spot MFE to profit after theta+costs.")

    # conditioned sub-populations
    report(df[df["strength"] > 1.0], "STRONG breakouts (>1 ATR beyond range)")
    report(df[df["strength"] > 2.0], "VERY STRONG breakouts (>2 ATR)")
    report(df[df["fh_rng"] > 0.008], "HIGH-vol days (first-hr range >0.8%)")
    report(df[(df["hour"] >= 13)], "AFTERNOON entries (>=13:00)")
    report(df[(df["hour"] <= 10)], "MORNING entries (<=10:00)")


if __name__ == "__main__":
    analyze()
