"""Long-only trend/momentum SWING option-buying engine (multi-day holds).

Rationale (the one directional edge that survived research): NIFTY has a mild but
persistent UPWARD DRIFT / trend effect. Bullish EMA-trend & big-up-day continuation
show +0.3-0.5% over 2-3 days at 60-74% hit; short side has no edge. So: LONG CE only,
in a confirmed daily uptrend, on a momentum trigger. Express as a DEBIT SPREAD (buy
CE + sell further-OTM CE) to cut theta/vega/cost, or single long CE. Hold up to a few
days; trail winners to ride the right tail; cut losers fast. Real 1-min option fills.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd

import chain
from engine import _costs, STEP  # reuse cost model + strike step


@dataclass
class SwingCfg:
    # daily trend/entry
    ema_fast: int = 10
    ema_slow: int = 20
    trend_ema: int = 50            # regime: daily close must be > this EMA
    trigger: str = "ema_cross"     # ema_cross | breakout20 | bigday
    breakout_n: int = 20
    bigday_ret: float = 0.010
    # instrument
    min_dte: int = 3               # want room so theta isn't brutal at entry
    max_dte: int = 9
    strike_offset: int = 0         # 0=ATM; -1 => 1 ITM (lower strike for CE)
    spread_width: int = 0          # 0 single long; >0 sell CE this many strikes OTM
    # exits
    target_pct: float = 1.00       # let winners run (convexity)
    stop_pct: float = 0.35
    trail_pct: float = 0.35        # trail from peak once profitable
    max_hold_days: int = 4
    entry_hhmm: str = "09:20"
    exit_hhmm: str = "15:15"       # square-off time on the exit day
    # portfolio
    slippage_pct: float = 0.005
    capital: float = 3_00_000.0
    risk_per_trade: float = 0.03
    lot_size: int = 75


def _daily(spot: pd.DataFrame) -> pd.DataFrame:
    g = spot.groupby(spot.index.date)
    d = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(),
                      "low": g["low"].min(), "close": g["close"].last()})
    d.index = [pd.Timestamp(x).date() for x in d.index]
    return d


def entry_days(spot: pd.DataFrame, cfg: SwingCfg) -> list[dt.date]:
    """Days whose CLOSE triggers a long; enter NEXT session (no lookahead)."""
    d = _daily(spot)
    c = d["close"]
    ef = c.ewm(span=cfg.ema_fast, adjust=False).mean()
    es = c.ewm(span=cfg.ema_slow, adjust=False).mean()
    reg = c.ewm(span=cfg.trend_ema, adjust=False).mean()
    uptrend = c > reg
    ret1 = c.pct_change()
    hh = d["high"].rolling(cfg.breakout_n).max()

    if cfg.trigger == "ema_cross":
        trig = (ef > es) & (ef.shift(1) <= es.shift(1))
    elif cfg.trigger == "breakout20":
        trig = c > hh.shift(1)
    elif cfg.trigger == "bigday":
        trig = ret1 > cfg.bigday_ret
    else:
        raise ValueError(cfg.trigger)

    fire = trig & uptrend
    trig_days = [dd for dd, v in fire.items() if bool(v)]
    # map each trigger day -> next available session
    all_days = list(d.index)
    pos = {dd: i for i, dd in enumerate(all_days)}
    nxt = []
    for dd in trig_days:
        i = pos[dd]
        if i + 1 < len(all_days):
            nxt.append(all_days[i + 1])
    return sorted(set(nxt))


def _atm(x):
    return int(round(x / STEP) * STEP)


def _leg(df: pd.DataFrame, strike: int) -> pd.DataFrame:
    s = df[(df["strike"] == strike) & (df["option_type"] == "CE")]
    return s.set_index("t")[["open", "high", "low", "close"]].sort_index()


def simulate(spot: pd.DataFrame, enter_day: dt.date, cfg: SwingCfg) -> dict | None:
    exp = chain.nearest_expiry(enter_day, cfg.min_dte, cfg.max_dte)
    if exp is None:
        return None
    df = chain.load_expiry(exp)
    # spot at entry time
    et = pd.Timestamp(enter_day) + pd.Timedelta(
        hours=int(cfg.entry_hhmm[:2]), minutes=int(cfg.entry_hhmm[3:]))
    sp = spot[(spot.index.date == enter_day) & (spot.index <= et)]
    if sp.empty:
        return None
    s0 = sp["close"].iloc[-1]
    avail = sorted(df["strike"].unique())
    if not avail:
        return None
    k = _atm(s0) - cfg.strike_offset * STEP   # offset<0 -> ITM (lower strike)
    k = min(avail, key=lambda x: abs(x - k))
    long_leg = _leg(df, k)
    long_leg = long_leg[long_leg.index >= et]
    if long_leg.empty:
        return None
    long_entry = long_leg.iloc[0]["open"]
    if not np.isfinite(long_entry) or long_entry <= 0:
        return None

    has_short = cfg.spread_width > 0
    short_leg = None
    short_entry = 0.0
    if has_short:
        sk = min(avail, key=lambda x: abs(x - (k + cfg.spread_width * STEP)))
        short_leg = _leg(df, sk)
        short_leg = short_leg[short_leg.index >= long_leg.index[0]]
        if short_leg.empty:
            has_short = False
        else:
            short_entry = short_leg.iloc[0]["open"]

    entry_bar = long_leg.index[0]
    lc = long_leg["close"]
    net = lc - short_leg["close"].reindex(lc.index).ffill() if has_short else lc
    entry_debit = long_entry - short_entry
    if entry_debit <= 0:
        return None
    fill_debit = long_entry * (1 + cfg.slippage_pct) - \
        (short_entry * (1 - cfg.slippage_pct) if has_short else 0.0)

    last_day = min(exp, enter_day + dt.timedelta(days=cfg.max_hold_days))
    tgt = entry_debit * (1 + cfg.target_pct)
    stp = entry_debit * (1 - cfg.stop_pct)
    peak = entry_debit
    exit_t = exit_val = reason = None
    for t, val in net.items():
        if t <= entry_bar:
            continue
        d_ = t.date()
        # square-off on the final allowed day at exit time
        eod = pd.Timestamp(d_) + pd.Timedelta(hours=int(cfg.exit_hhmm[:2]),
                                               minutes=int(cfg.exit_hhmm[3:]))
        if d_ >= last_day and t >= eod:
            exit_t, exit_val, reason = t, val, "timebox"; break
        if val >= tgt:
            exit_t, exit_val, reason = t, val, "target"; break
        if val <= stp:
            exit_t, exit_val, reason = t, val, "stop"; break
        if cfg.trail_pct > 0:
            peak = max(peak, val)
            if peak > entry_debit and val <= peak * (1 - cfg.trail_pct):
                exit_t, exit_val, reason = t, val, "trail"; break
    if exit_t is None:
        exit_t, exit_val, reason = net.index[-1], float(net.iloc[-1]), "expiry"

    fill_exit = max(exit_val, 0.0) * (1 - cfg.slippage_pct) if not has_short \
        else max(exit_val, 0.0)  # spread slippage approximated in entry
    outlay_per_lot = fill_debit * cfg.lot_size
    lots = max(1, int((cfg.risk_per_trade * cfg.capital) // max(outlay_per_lot, 1)))
    qty = lots * cfg.lot_size
    gross = (fill_exit - fill_debit) * qty
    costs = _costs(fill_debit, max(fill_exit, 0.0), lots, cfg.lot_size, has_short)
    net_pnl = gross - costs
    return {
        "enter_day": enter_day, "exp": exp, "dte0": (exp - enter_day).days,
        "strike": k, "spread": has_short, "entry_t": entry_bar, "exit_t": exit_t,
        "reason": reason, "entry_debit": entry_debit, "fill_debit": fill_debit,
        "exit_val": exit_val, "fill_exit": fill_exit, "lots": lots, "qty": qty,
        "gross": gross, "costs": costs, "net_pnl": net_pnl,
        "ret_pct": fill_exit / fill_debit - 1,
        "hold_days": (exit_t.date() - entry_bar.date()).days,
    }


def run_range(cfg: SwingCfg, start: dt.date, end: dt.date) -> pd.DataFrame:
    spot = chain.load_index()
    edays = [d for d in entry_days(spot, cfg) if start <= d <= end]
    rows = []
    for d in edays:
        try:
            tr = simulate(spot, d, cfg)
            if tr:
                rows.append(tr)
        except Exception as e:
            print(f"  {d}: ERR {type(e).__name__}: {e}")
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame, cfg: SwingCfg, label: str):
    print(f"\n--- {label}: {len(df)} trades ---")
    if df.empty:
        return
    wr = (df["net_pnl"] > 0).mean()
    tot = df["net_pnl"].sum()
    gross = df["gross"].sum()
    costs = df["costs"].sum()
    wins = df[df["net_pnl"] > 0]["net_pnl"]
    losses = df[df["net_pnl"] <= 0]["net_pnl"]
    pf = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else np.inf
    print(f"win rate {wr:.1%} | net Rs.{tot:,.0f} | gross Rs.{gross:,.0f} | "
          f"costs Rs.{costs:,.0f} | PF {pf:.2f}")
    print(f"avg ret% {df['ret_pct'].mean():+.1%} | avg net/trade Rs.{df['net_pnl'].mean():,.0f} "
          f"| avg hold {df['hold_days'].mean():.1f}d | on Rs.{cfg.capital:,.0f} cap: "
          f"{tot/cfg.capital:+.1%} total")
    print(f"reasons: {df['reason'].value_counts().to_dict()}")


if __name__ == "__main__":
    cfg = SwingCfg()
    df = run_range(cfg, dt.date(2021, 1, 1), dt.date(2025, 12, 31))
    summarize(df, cfg, "BUILD 2021-2025 (ema_cross, single long ATM CE)")
