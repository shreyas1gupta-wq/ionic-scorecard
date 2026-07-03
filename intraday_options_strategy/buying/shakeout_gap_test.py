"""Spot-edge tests for two user ideas (build 2021-2025 only, isolate directional edge):
  1) SHAKEOUT: failed 20-bar breakout that closes back inside -> enter the REVERSAL.
     Tested on 5-min intraday and on daily bars. Signed forward return + hit + MFE/MAE.
  2) GAPS: gap-up/down at open -> does the day CONTINUE or FADE/FILL? by size & 20DMA.
Option breakeven needs ~>0.3-0.5% signed follow-through.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

import chain

BUILD_END = dt.date(2025, 12, 31)


def daily_bars(spot):
    g = spot.groupby(spot.index.date)
    d = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(),
                      "low": g["low"].min(), "close": g["close"].last()})
    d.index = pd.to_datetime([pd.Timestamp(x) for x in d.index])
    return d


# ---------- 1a. DAILY shakeout ----------
def daily_shakeout(spot):
    d = daily_bars(spot)
    d = d[d.index.date <= BUILD_END]
    n = 20
    hh = d["high"].rolling(n).max().shift(1)
    ll = d["low"].rolling(n).min().shift(1)
    c = d["close"]
    # upthrust: today HIGH breaks 20d high but CLOSE falls back below it -> short reversal
    upthrust = (d["high"] > hh) & (c < hh)
    # spring: today LOW breaks 20d low but CLOSE recovers above it -> long reversal
    spring = (d["low"] < ll) & (c > ll)
    fwd = {h: c.shift(-h) / c - 1 for h in (1, 2, 3, 5)}
    print("=" * 74)
    print("1a. DAILY SHAKEOUT (failed 20d breakout, enter reversal at close)")
    print("=" * 74)
    for name, mask, sign in [("spring->LONG", spring, +1), ("upthrust->SHORT", upthrust, -1)]:
        idx = mask[mask].index
        row = f"  {name:16s} n={len(idx):3d} "
        for h in (1, 2, 3, 5):
            v = (sign * fwd[h].reindex(idx)).dropna()
            row += f"| d{h} {v.mean():+.2%}({(v>0).mean():.0%}) "
        print(row)
    print("  need >~0.6-1.0% signed for a few-DTE option.\n")


# ---------- 1b. 5-MIN intraday shakeout ----------
def intraday_shakeout(spot):
    print("=" * 74)
    print("1b. 5-MIN INTRADAY SHAKEOUT (per day, 12-bar range fail -> reversal)")
    print("=" * 74)
    days = sorted({d for d in spot.index.date if d <= BUILD_END})
    rows = []
    for day in days:
        sd = spot[spot.index.date == day]
        if len(sd) < 120:
            continue
        b = sd.resample("5min").agg({"open": "first", "high": "max",
                                     "low": "min", "close": "last"}).dropna()
        if len(b) < 30:
            continue
        n = 12
        hh = b["high"].rolling(n).max().shift(1)
        ll = b["low"].rolling(n).min().shift(1)
        c = b["close"]
        upthrust = (b["high"] > hh) & (c < hh)
        spring = (b["low"] < ll) & (c > ll)
        for name, mask, sign in [("spring", spring, +1), ("upthrust", upthrust, -1)]:
            hit = b[mask.fillna(False)]
            # only entries before 14:30 (need room), one per type per day (first)
            hit = hit[hit.index.time <= dt.time(14, 30)]
            if hit.empty:
                continue
            t0 = hit.index[0]
            px = hit.iloc[0]["close"]
            for H in (6, 12):  # 30, 60 min (5-min bars)
                path = b[(b.index > t0) & (b.index <= t0 + pd.Timedelta(minutes=5 * H))]
                if path.empty:
                    continue
                endp = path["close"].iloc[-1]
                fwd = sign * (endp / px - 1)
                if sign == 1:
                    mfe = path["high"].max() / px - 1
                    mae = path["low"].min() / px - 1
                else:
                    mfe = px / path["low"].min() - 1
                    mae = px / path["high"].max() - 1
                rows.append({"type": name, "H": H, "fwd": fwd, "mfe": mfe, "mae": mae})
    df = pd.DataFrame(rows)
    for name in ("spring", "upthrust"):
        for H in (6, 12):
            s = df[(df["type"] == name) & (df["H"] == H)]
            if s.empty:
                continue
            print(f"  {name:9s} +{5*H:>2}min: n={len(s):4d} fwd {s['fwd'].mean():+.3%}"
                  f"({(s['fwd']>0).mean():.0%}) | MFE {s['mfe'].mean():+.3%} "
                  f"MAE {s['mae'].mean():+.3%} | MFE/|MAE| {s['mfe'].mean()/abs(s['mae'].mean()):.2f}")
    print()


# ---------- 2. GAPS ----------
def gap_test(spot):
    d = daily_bars(spot)
    d = d[d.index.date <= BUILD_END]
    prev_c = d["close"].shift(1)
    gap = d["open"] / prev_c - 1
    o2c = d["close"] / d["open"] - 1            # intraday move after open
    ma20 = d["close"].rolling(20).mean().shift(1)
    filled = ((d["low"] <= prev_c) & (d["high"] >= prev_c))  # touched prev close = gap filled
    df = pd.DataFrame({"gap": gap, "o2c": o2c, "filled": filled,
                       "above20": d["close"].shift(1) > ma20}).dropna()
    print("=" * 74)
    print("2. GAPS: open->close move & gap-fill, by gap bucket (daily)")
    print("=" * 74)
    df["bucket"] = pd.cut(df["gap"], [-1, -0.007, -0.002, 0.002, 0.007, 1],
                          labels=["gapdn>0.7%", "gapdn.2-.7", "flat", "gapup.2-.7", "gapup>0.7%"])
    g = df.groupby("bucket", observed=True).agg(
        n=("o2c", "size"), o2c_mean=("o2c", "mean"),
        o2c_up=("o2c", lambda x: (x > 0).mean()), fill=("filled", "mean"))
    print(g.to_string(formatters={"o2c_mean": "{:+.3%}".format,
                                  "o2c_up": "{:.0%}".format, "fill": "{:.0%}".format}))
    print("\n  'continuation' = o2c same sign as gap; 'fade' = opposite. fill = touched prev close.")
    # continuation vs fade explicitly
    up = df[df["gap"] > 0.002]
    dn = df[df["gap"] < -0.002]
    print(f"\n  GAP-UP  (>0.2%): n={len(up)} o2c {up['o2c'].mean():+.3%} "
          f"(continues up {(up['o2c']>0).mean():.0%}, fills {up['filled'].mean():.0%})")
    print(f"  GAP-DOWN(<-.2%): n={len(dn)} o2c {dn['o2c'].mean():+.3%} "
          f"(continues dn {(dn['o2c']<0).mean():.0%}, fills {dn['filled'].mean():.0%})")


if __name__ == "__main__":
    spot = chain.load_index()
    daily_shakeout(spot)
    intraday_shakeout(spot)
    gap_test(spot)
