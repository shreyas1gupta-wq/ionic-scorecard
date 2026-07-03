"""Signal-edge diagnostic on NIFTY spot (build set 2021-2025 only).

Isolates DIRECTIONAL edge from theta/costs: for each candidate entry signal we
measure the SIGNED forward spot return at several horizons + the payoff skew
(option buyers need positive skew: occasional big moves that overcome theta).

If a signal's mean signed forward move can't clear ~0.3-0.5% (rough option
breakeven over the hold), buying options on it is hopeless regardless of structure.
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


def gen_signals(d: pd.DataFrame, day: dt.date) -> list[dict]:
    """All candidate signals for one day. Each: {name, t, dir, px}."""
    out = []
    if len(d) < 120:
        return out
    c = d["close"]
    ema9, ema21 = _ema(c, 9), _ema(c, 21)
    atr = _atr(d, 14)
    twap = c.expanding().mean()
    open_px = d["open"].iloc[0]

    # opening ranges
    for orb in (15, 30, 60):
        or_end = _t(day, "09:15") + pd.Timedelta(minutes=orb)
        orng = d[d.index < or_end]
        if orng.empty:
            continue
        hi, lo = orng["high"].max(), orng["low"].min()
        win = d[(d.index >= or_end) & (d.index <= _t(day, "14:30"))]
        # first breakout each side
        up = win[win["close"] > hi]
        dn = win[win["close"] < lo]
        if not up.empty:
            t = up.index[0]
            out.append({"name": f"ORB{orb}_up", "t": t, "dir": 1, "px": up.iloc[0]["close"]})
        if not dn.empty:
            t = dn.index[0]
            out.append({"name": f"ORB{orb}_dn", "t": t, "dir": -1, "px": dn.iloc[0]["close"]})
        # ORB + trend gate
        up_tr = win[(win["close"] > hi) & (ema9.reindex(win.index) > ema21.reindex(win.index))
                    & (win["close"] > twap.reindex(win.index))]
        dn_tr = win[(win["close"] < lo) & (ema9.reindex(win.index) < ema21.reindex(win.index))
                    & (win["close"] < twap.reindex(win.index))]
        if not up_tr.empty:
            t = up_tr.index[0]
            out.append({"name": f"ORB{orb}+trend_up", "t": t, "dir": 1, "px": up_tr.iloc[0]["close"]})
        if not dn_tr.empty:
            t = dn_tr.index[0]
            out.append({"name": f"ORB{orb}+trend_dn", "t": t, "dir": -1, "px": dn_tr.iloc[0]["close"]})

    # first-hour momentum -> trade at 10:15 in same direction
    t1015 = _t(day, "10:15")
    if t1015 in d.index or (d.index <= t1015).any():
        p0 = d["close"].iloc[0]
        p1 = d[d.index <= t1015]["close"].iloc[-1]
        r = p1 / p0 - 1
        if abs(r) > 0.002:
            out.append({"name": "FH_momo", "t": d[d.index <= t1015].index[-1],
                        "dir": 1 if r > 0 else -1, "px": p1})

    # gap-and-go: open vs prior close handled outside (needs prev day). skip here.

    # range-compression breakout: first-hour range < 0.5*ATR-of-day-proxy then break
    fh = d[d.index <= _t(day, "10:15")]
    if not fh.empty:
        fh_range = (fh["high"].max() - fh["low"].min()) / open_px
        if fh_range < 0.004:  # tight morning
            hi, lo = fh["high"].max(), fh["low"].min()
            win = d[(d.index > _t(day, "10:15")) & (d.index <= _t(day, "14:00"))]
            up = win[win["close"] > hi]
            dn = win[win["close"] < lo]
            if not up.empty:
                out.append({"name": "COIL_up", "t": up.index[0], "dir": 1, "px": up.iloc[0]["close"]})
            if not dn.empty:
                out.append({"name": "COIL_dn", "t": dn.index[0], "dir": -1, "px": dn.iloc[0]["close"]})
    return out


def analyze():
    spot = chain.load_index()
    spot = spot[spot.index.date <= BUILD_END]
    days = sorted({d for d in spot.index.date})
    print(f"[research] {len(days)} build-set days {days[0]}..{days[-1]}")

    rows = []
    for day in days:
        d = spot[spot.index.date == day]
        if len(d) < 120:
            continue
        sigs = gen_signals(d, day)
        for s in sigs:
            t, direction, px = s["t"], s["dir"], s["px"]
            fwd = {}
            for h in (15, 30, 60):
                tt = t + pd.Timedelta(minutes=h)
                fp = d[d.index <= tt]["close"].iloc[-1] if (d.index <= tt).any() else np.nan
                fwd[h] = direction * (fp / px - 1)
            eodp = d["close"].iloc[-1]
            fwd["eod"] = direction * (eodp / px - 1)
            rows.append({"name": s["name"], **{f"r{k}": v for k, v in fwd.items()}})

    df = pd.DataFrame(rows)
    print(f"[research] {len(df)} signal instances\n")
    # aggregate per signal
    agg = []
    for name, g in df.groupby("name"):
        row = {"signal": name, "n": len(g)}
        for h in ("r15", "r30", "r60", "reod"):
            v = g[h].dropna()
            row[f"{h}_mean"] = v.mean()
            row[f"{h}_hit"] = (v > 0).mean()
        # skew proxy at 60m: p90 vs |p10|
        v60 = g["r60"].dropna()
        row["r60_p90"] = v60.quantile(0.90)
        row["r60_p10"] = v60.quantile(0.10)
        agg.append(row)
    a = pd.DataFrame(agg).sort_values("r60_mean", ascending=False)
    pd.set_option("display.width", 200, "display.max_columns", None)
    fmt = {c: "{:+.3%}".format for c in a.columns if c.endswith(("mean", "p90", "p10"))}
    fmt.update({c: "{:.1%}".format for c in a.columns if c.endswith("hit")})
    print(a.to_string(index=False, formatters=fmt))
    print("\nNote: option ATM breakeven over ~60m hold is roughly +0.3% to +0.5% in spot.")


if __name__ == "__main__":
    analyze()
