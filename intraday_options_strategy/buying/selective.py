"""Selective intraday 1-min option buying: FIXED 1 lot, 1:2 risk-reward, then MINE
which filters/timings gave the best win rate -- and test if they PERSIST out-of-sample.

Every trade tagged with context (hour, day-of-week, DTE, trend, vol-regime, signal
strength, direction) so we can find WR>60% buckets on BUILD and check them on FORWARD.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

import chain
from engine import (_costs, STEP, _atr, _ema, _hhmm)

pd.set_option("display.width", 220, "display.max_columns", None)

STOP_PCT = 0.25            # risk
TARGET_PCT = 0.50          # reward = 2x risk -> 1:2
ENTRY_FROM, ENTRY_TO = "09:30", "14:30"
ORB_MIN = 15
SLIP = 0.005
LOT = 75
OUT = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
       r"\NIFTY 500\intraday_options_strategy\buying\trades_selective.parquet")


def daily_ctx(spot):
    g = spot.groupby(spot.index.date)
    d = pd.DataFrame({"close": g["close"].last()})
    d.index = pd.to_datetime(d.index)
    d["ema20"] = d["close"].ewm(span=20, adjust=False).mean()
    d["trend"] = np.where(d["close"] > d["ema20"], "up", "down")
    # realized vol regime: 10-day close-to-close std, annualized
    d["rv"] = d["close"].pct_change().rolling(10).std() * np.sqrt(252)
    d["volreg"] = pd.qcut(d["rv"].rank(method="first"), 3, labels=["lowvol", "midvol", "highvol"])
    return d


def day_signals(spot_day, day):
    d = spot_day.copy()
    if len(d) < 120:
        return []
    or_end = _hhmm(day, "09:15") + pd.Timedelta(minutes=ORB_MIN)
    orng = d[d.index < or_end]
    if orng.empty:
        return []
    hi, lo = orng["high"].max(), orng["low"].min()
    d["ema9"] = _ema(d["close"], 9)
    d["ema21"] = _ema(d["close"], 21)
    d["atr"] = _atr(d, 14)
    d["twap"] = d["close"].expanding().mean()
    fh = d[d.index <= _hhmm(day, "10:15")]
    fh_rng = (fh["high"].max() - fh["low"].min()) / d["close"].iloc[0] if not fh.empty else np.nan
    win = d[(d.index >= max(or_end, _hhmm(day, ENTRY_FROM))) & (d.index <= _hhmm(day, ENTRY_TO))]
    out = []
    for direction in (1, -1):
        if direction == 1:
            brk = win[(win["close"] > hi) & (win["ema9"] > win["ema21"]) & (win["close"] > win["twap"])]
            ref = hi
        else:
            brk = win[(win["close"] < lo) & (win["ema9"] < win["ema21"]) & (win["close"] < win["twap"])]
            ref = lo
        if brk.empty:
            continue
        t0 = brk.index[0]
        px0 = brk.iloc[0]["close"]
        atr0 = brk.iloc[0]["atr"]
        strength = direction * (px0 - ref) / (atr0 + 1e-9)
        out.append({"t": t0, "dir": direction, "strength": strength, "fh_rng": fh_rng})
    return out


def sim(cdf, sig, spot_at, day):
    direction = sig["dir"]
    otype = "CE" if direction == 1 else "PE"
    avail = sorted(cdf["strike"].unique())
    if not avail:
        return None
    k = min(avail, key=lambda x: abs(x - round(spot_at / STEP) * STEP))
    leg = cdf[(cdf["strike"] == k) & (cdf["option_type"] == otype)].set_index("t")[
        ["open", "high", "low", "close"]].sort_index()
    after = leg[leg.index > sig["t"]]
    if after.empty:
        return None
    entry = after.iloc[0]["open"]
    if not np.isfinite(entry) or entry <= 0:
        return None
    fill = entry * (1 + SLIP)
    tgt = entry * (1 + TARGET_PCT)
    stp = entry * (1 - STOP_PCT)
    eod = _hhmm(day, "15:15")
    ex_t = ex_v = reason = None
    for t, row in after.iterrows():
        if t >= eod:
            ex_t, ex_v, reason = t, row["close"], "eod"; break
        if row["close"] >= tgt:
            ex_t, ex_v, reason = t, tgt, "target"; break
        if row["close"] <= stp:
            ex_t, ex_v, reason = t, stp, "stop"; break
    if ex_t is None:
        ex_t, ex_v, reason = after.index[-1], after.iloc[-1]["close"], "eod"
    fill_exit = max(ex_v, 0.0) * (1 - SLIP)
    gross = (fill_exit - fill) * LOT
    costs = _costs(fill, max(fill_exit, 0.0), 1, LOT, False)
    net = gross - costs
    return {"day": day, "otype": otype, "strike": k, "entry_t": sig["t"],
            "exit_t": ex_t, "reason": reason, "ret_pct": fill_exit / fill - 1,
            "net_pnl": net, "win": net > 0,
            "hour": sig["t"].hour, "dir": "CE" if direction == 1 else "PE",
            "strength": sig["strength"], "fh_rng": sig["fh_rng"]}


def run(start, end):
    spot = chain.load_index()
    dctx = daily_ctx(spot)
    days = sorted({d for d in spot.index.date if start <= d <= end})
    rows = []
    for i, day in enumerate(days):
        sd = spot[spot.index.date == day]
        sigs = day_signals(sd, day)
        if not sigs:
            continue
        exp = chain.nearest_expiry(day, 0, 7)
        if exp is None:
            continue
        cdf = chain.day_chain(exp, day)
        if cdf.empty:
            continue
        for s in sigs:
            spot_at = sd.asof(s["t"])["close"]
            tr = sim(cdf, s, spot_at, day)
            if tr:
                tr["dte"] = (exp - day).days
                ts = pd.Timestamp(day)
                tr["dow"] = ts.day_name()[:3]
                tr["trend"] = dctx.loc[ts, "trend"] if ts in dctx.index else "?"
                tr["volreg"] = str(dctx.loc[ts, "volreg"]) if ts in dctx.index else "?"
                rows.append(tr)
        if i % 200 == 0:
            print(f"  ...{day} ({i}/{len(days)}) trades={len(rows)}")
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = run(dt.date(2021, 1, 1), dt.date(2026, 6, 2))
    df["dte_b"] = pd.cut(df["dte"], [-1, 0, 2, 99], labels=["0DTE", "1-2DTE", "3+DTE"])
    df["str_b"] = pd.cut(df["strength"], [-99, 0.5, 1.5, 99], labels=["weak", "mid", "strong"])
    df["hour_b"] = df["hour"].astype(str) + "h"
    df.to_parquet(OUT)
    print(f"\nsaved {len(df)} trades -> {OUT}")

    build = df[df["day"] <= dt.date(2025, 12, 31)]
    fwd = df[df["day"] > dt.date(2025, 12, 31)]
    print(f"\nBUILD {len(build)} trades, overall WR {build['win'].mean():.1%}, "
          f"net Rs.{build['net_pnl'].sum():,.0f} (fixed 1 lot)")
    print(f"FWD   {len(fwd)} trades, overall WR {fwd['win'].mean():.1%}, "
          f"net Rs.{fwd['net_pnl'].sum():,.0f}")

    print("\n=== single-filter win rates on BUILD (target: find WR>60%) ===")
    for dim in ["dir", "hour_b", "dow", "trend", "volreg", "dte_b", "str_b"]:
        g = build.groupby(dim, observed=True).agg(n=("win", "size"), wr=("win", "mean"),
                                                  net=("net_pnl", "sum"))
        g = g[g["n"] >= 30].sort_values("wr", ascending=False)
        print(f"\n[{dim}]")
        print(g.to_string(formatters={"wr": "{:.1%}".format, "net": "Rs.{:,.0f}".format}))

    print("\n=== best combos (dir x trend x hour) BUILD, then FORWARD persistence ===")
    bc = build.groupby(["dir", "trend", "hour_b"], observed=True).agg(
        n=("win", "size"), wr=("win", "mean"), net=("net_pnl", "sum"))
    bc = bc[bc["n"] >= 30].sort_values("wr", ascending=False).head(10)
    fc = fwd.groupby(["dir", "trend", "hour_b"], observed=True).agg(
        fn=("win", "size"), fwr=("win", "mean"))
    j = bc.join(fc)
    print(j.to_string(formatters={"wr": "{:.1%}".format, "fwr": "{:.1%}".format,
                                  "net": "Rs.{:,.0f}".format}))
    print("\nBreakeven WR at 1:2 R:R = 33%. Watch whether high-BUILD-WR combos keep WR on FWD.")
