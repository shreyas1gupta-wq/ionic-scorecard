"""Mean-reversion edge test (build set 2021-2025). Does buying the BOUNCE work?

Triggers: oversold -> buy CE (expect up-reversion); overbought -> buy PE.
Measures signed forward return + MFE/MAE + SKEW. Option buyers need positive skew;
mean-reversion typically has NEGATIVE skew (small wins, big loss when it fails).
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

import chain

BUILD_END = dt.date(2025, 12, 31)


def _rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def _t(day, hhmm):
    h, m = map(int, hhmm.split(":"))
    return pd.Timestamp(day) + pd.Timedelta(hours=h, minutes=m)


def day_signals(d, day):
    out = []
    if len(d) < 150:
        return out
    c = d["close"]
    rsi2 = _rsi(c, 2)
    rsi14 = _rsi(c, 14)
    twap = c.expanding().mean()
    std = c.expanding().std()
    z = (c - twap) / std.replace(0, np.nan)
    bb_mid = c.rolling(20).mean()
    bb_std = c.rolling(20).std()
    lower = bb_mid - 2 * bb_std
    upper = bb_mid + 2 * bb_std
    win = d[(d.index >= _t(day, "09:45")) & (d.index <= _t(day, "14:30"))]

    triggers = {
        "RSI2<5_buyCE":   (rsi2 < 5, 1),
        "RSI14<30_buyCE": (rsi14 < 30, 1),
        "belowBB_buyCE":  (c < lower, 1),
        "z<-2_buyCE":     (z < -2, 1),
        "RSI2>95_buyPE":  (rsi2 > 95, -1),
        "RSI14>70_buyPE": (rsi14 > 70, -1),
        "aboveBB_buyPE":  (c > upper, -1),
        "z>2_buyPE":      (z > 2, -1),
    }
    for name, (cond, direction) in triggers.items():
        cw = cond.reindex(win.index).fillna(False)
        hit = win[cw]
        if hit.empty:
            continue
        # first occurrence only (one trade/day/signal)
        t0 = hit.index[0]
        out.append({"name": name, "t": t0, "dir": direction, "px": hit.iloc[0]["close"]})
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
            for H in (30, 60):
                path = d[(d.index > t) & (d.index <= t + pd.Timedelta(minutes=H))]
                if path.empty:
                    continue
                endp = path["close"].iloc[-1]
                fwd = direction * (endp / px - 1)
                if direction == 1:
                    mfe = path["high"].max() / px - 1
                    mae = path["low"].min() / px - 1
                else:
                    mfe = px / path["low"].min() - 1
                    mae = px / path["high"].max() - 1
                rows.append({"name": s["name"], "H": H, "fwd": fwd, "mfe": mfe, "mae": mae})
    df = pd.DataFrame(rows)
    print(f"[mean-rev] {len(df)} rows\n")
    for H in (30, 60):
        sub = df[df["H"] == H]
        g = sub.groupby("name").agg(
            n=("fwd", "size"), fwd_mean=("fwd", "mean"),
            hit=("fwd", lambda x: (x > 0).mean()),
            mfe=("mfe", "mean"), mae=("mae", "mean"),
            skew=("fwd", lambda x: x.skew()))
        g["mfe/|mae|"] = g["mfe"] / g["mae"].abs()
        g = g.sort_values("fwd_mean", ascending=False)
        print(f"### Horizon {H} min")
        fmt = {c: "{:+.3%}".format for c in ["fwd_mean", "mfe", "mae"]}
        fmt["hit"] = "{:.0%}".format; fmt["mfe/|mae|"] = "{:.2f}".format
        fmt["skew"] = "{:+.2f}".format
        print(g.to_string(formatters=fmt))
        print()
    print("Buyers need fwd_mean > ~+0.3% AND positive skew. Sellers profit from the "
          "opposite (small consistent decay).")


if __name__ == "__main__":
    analyze()
