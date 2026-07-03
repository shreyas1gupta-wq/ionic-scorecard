"""Regime-aligned, multi-timeframe intraday option BUYING (user's design).

Only trade when higher-timeframe regime + intraday trigger AGREE on direction:
  BULL regime (buy CE): 3m return>0 AND close>20DMA AND close>200DMA
  BEAR regime (buy PE): 3m return<0 AND close<20DMA AND close<200DMA
  else: NO TRADE (neutral days skipped).
Confluence filters (toggleable): 200-period 5-min MA, 5-day RSI, trigger =
ORB breakout / Europe-session-open breakout / expiry-day breakout.
Fixed 1 lot, 1:2 R:R. Regime uses PRIOR-day data (no lookahead). Build + forward.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd

import chain
from engine import _costs, STEP, _atr, _ema, _hhmm

LOT = 75
SLIP = 0.005


@dataclass
class RegCfg:
    trigger: str = "orb"          # orb | europe | expiry
    orb_min: int = 15
    entry_from: str = "09:30"
    entry_to: str = "14:30"
    use_mtf: bool = True          # price vs 200-period 5-min MA in regime dir
    use_rsi: bool = True          # 5-day RSI momentum filter
    strike_offset: int = -1       # ITM by 1 (less theta)
    stop_pct: float = 0.25
    target_pct: float = 0.50      # 1:2
    trail_pct: float = 0.0
    eod: str = "15:15"
    only_bull: bool = False       # trade only bull-regime longs (drop shorts)


def _rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def daily_features(spot):
    g = spot.groupby(spot.index.date)
    d = pd.DataFrame({"close": g["close"].last()})
    d.index = pd.to_datetime(d.index)
    d["ma20"] = d["close"].rolling(20).mean()
    d["ma200"] = d["close"].rolling(200).mean()
    d["ret3m"] = d["close"].pct_change(63)
    d["rsi5"] = _rsi(d["close"], 5)
    # regime from PRIOR day (shift 1) -> known at today's open
    p = d.shift(1)
    d["regime"] = "neutral"
    d.loc[(p["ret3m"] > 0) & (p["close"] > p["ma20"]) & (p["close"] > p["ma200"]), "regime"] = "bull"
    d.loc[(p["ret3m"] < 0) & (p["close"] < p["ma20"]) & (p["close"] < p["ma200"]), "regime"] = "bear"
    d["rsi5_prev"] = p["rsi5"]
    return d


def mtf_5min_ma(spot, n=200):
    c5 = spot["close"].resample("5min").last().dropna()
    return c5.rolling(n).mean()


def triggers(sd, day, cfg, direction):
    """Return first entry timestamp in `direction` per the chosen trigger, else None."""
    if len(sd) < 120:
        return None
    if cfg.trigger == "europe":
        # Europe open ~13:30 IST: breakout of the day's range just before 13:30
        ref_end = _hhmm(day, "13:30")
        pre = sd[sd.index < ref_end]
        if pre.empty:
            return None
        hi, lo = pre["high"].max(), pre["low"].min()
        win = sd[(sd.index >= ref_end) & (sd.index <= _hhmm(day, "15:00"))]
    else:  # orb / expiry both use opening-range breakout
        or_end = _hhmm(day, "09:15") + pd.Timedelta(minutes=cfg.orb_min)
        orng = sd[sd.index < or_end]
        if orng.empty:
            return None
        hi, lo = orng["high"].max(), orng["low"].min()
        win = sd[(sd.index >= max(or_end, _hhmm(day, cfg.entry_from))) &
                 (sd.index <= _hhmm(day, cfg.entry_to))]
    ema9 = _ema(sd["close"], 9)
    ema21 = _ema(sd["close"], 21)
    if direction == 1:
        brk = win[(win["close"] > hi) & (ema9.reindex(win.index) > ema21.reindex(win.index))]
    else:
        brk = win[(win["close"] < lo) & (ema9.reindex(win.index) < ema21.reindex(win.index))]
    return brk.index[0] if not brk.empty else None


def sim(cdf, t0, direction, spot_at, day, cfg):
    otype = "CE" if direction == 1 else "PE"
    avail = sorted(cdf["strike"].unique())
    if not avail:
        return None
    atmk = round(spot_at / STEP) * STEP
    k = atmk - cfg.strike_offset * STEP * direction  # offset<0 -> ITM
    k = min(avail, key=lambda x: abs(x - k))
    leg = cdf[(cdf["strike"] == k) & (cdf["option_type"] == otype)].set_index("t")[
        ["open", "high", "low", "close"]].sort_index()
    after = leg[leg.index > t0]
    if after.empty:
        return None
    entry = after.iloc[0]["open"]
    if not np.isfinite(entry) or entry <= 0:
        return None
    fill = entry * (1 + SLIP)
    tgt, stp = entry * (1 + cfg.target_pct), entry * (1 - cfg.stop_pct)
    eod = _hhmm(day, cfg.eod)
    peak = entry
    ex_t = ex_v = reason = None
    for t, row in after.iterrows():
        if t >= eod:
            ex_t, ex_v, reason = t, row["close"], "eod"; break
        if row["close"] >= tgt:
            ex_t, ex_v, reason = t, tgt, "target"; break
        if row["close"] <= stp:
            ex_t, ex_v, reason = t, stp, "stop"; break
        if cfg.trail_pct > 0:
            peak = max(peak, row["close"])
            if peak > entry and row["close"] <= peak * (1 - cfg.trail_pct):
                ex_t, ex_v, reason = t, row["close"], "trail"; break
    if ex_t is None:
        ex_t, ex_v, reason = after.index[-1], after.iloc[-1]["close"], "eod"
    fx = max(ex_v, 0.0) * (1 - SLIP)
    gross = (fx - fill) * LOT
    costs = _costs(fill, max(fx, 0.0), 1, LOT, False)
    return {"day": day, "dir": otype, "strike": k, "entry_t": t0, "exit_t": ex_t,
            "reason": reason, "ret_pct": fx / fill - 1, "net_pnl": gross - costs,
            "win": (gross - costs) > 0}


def run(cfg, start, end):
    spot = chain.load_index()
    dfeat = daily_features(spot)
    ma5 = mtf_5min_ma(spot) if cfg.use_mtf else None
    days = sorted({d for d in spot.index.date if start <= d <= end})
    rows = []
    for i, day in enumerate(days):
        ts = pd.Timestamp(day)
        if ts not in dfeat.index:
            continue
        regime = dfeat.loc[ts, "regime"]
        if regime == "neutral":
            continue
        if cfg.only_bull and regime != "bull":
            continue
        direction = 1 if regime == "bull" else -1
        if cfg.use_rsi:
            rsi = dfeat.loc[ts, "rsi5_prev"]
            if direction == 1 and not (rsi > 50):
                continue
            if direction == -1 and not (rsi < 50):
                continue
        sd = spot[spot.index.date == day]
        t0 = triggers(sd, day, cfg, direction)
        if t0 is None:
            continue
        if cfg.use_mtf:
            price = sd.asof(t0)["close"]
            mval = ma5.asof(t0)
            if pd.isna(mval):
                continue
            if direction == 1 and not (price > mval):
                continue
            if direction == -1 and not (price < mval):
                continue
        exp = chain.nearest_expiry(day, 0, 7)
        if exp is None:
            continue
        cdf = chain.day_chain(exp, day)
        if cdf.empty:
            continue
        spot_at = sd.asof(t0)["close"]
        tr = sim(cdf, t0, direction, spot_at, day, cfg)
        if tr:
            tr["regime"] = regime
            rows.append(tr)
        if i % 300 == 0:
            print(f"  ...{day} ({i}/{len(days)}) trades={len(rows)}")
    return pd.DataFrame(rows)


def report(df, label):
    print(f"\n--- {label}: {len(df)} trades ---")
    if df.empty:
        print("  no trades"); return
    wr = df["win"].mean()
    net = df["net_pnl"].sum()
    wins = df[df["net_pnl"] > 0]["net_pnl"]
    losses = df[df["net_pnl"] <= 0]["net_pnl"]
    pf = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else np.inf
    print(f"WR {wr:.1%} | net Rs.{net:,.0f} (1 lot) | PF {pf:.2f} | "
          f"avg/trade Rs.{df['net_pnl'].mean():,.0f} | reasons {df['reason'].value_counts().to_dict()}")
    if "regime" in df:
        for reg, g in df.groupby("regime"):
            print(f"   {reg}: n={len(g)} WR={g['win'].mean():.0%} net=Rs.{g['net_pnl'].sum():,.0f}")


if __name__ == "__main__":
    for name, cfg in [("BULL-ONLY ORB + convex (let winners run)",
                       RegCfg(trigger="orb", only_bull=True, strike_offset=-1,
                              target_pct=1.5, trail_pct=0.4, stop_pct=0.30))]:
        print("\n" + "=" * 70 + f"\n{name}\n" + "=" * 70)
        b = run(cfg, dt.date(2021, 1, 1), dt.date(2025, 12, 31))
        report(b, "BUILD 2021-2025")
        f = run(cfg, dt.date(2026, 1, 1), dt.date(2026, 6, 2))
        report(f, "FORWARD 2026 H1")
