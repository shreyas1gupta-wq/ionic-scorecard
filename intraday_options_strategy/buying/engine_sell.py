"""Option SELLING engine — defined-risk short-vol on NIFTY weeklies (VRP harvest).

Structures: iron_condor (sell OTM put+call, buy wings), short_strangle (naked),
iron_fly (sell ATM straddle + wings). Delta-based strike selection, richness (IV)
filter, manage-at-target / stop exits, hold to expiry otherwise. Fixed 1 lot,
realistic costs. Build 2021-2025 + untouched forward 2026 H1.
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
from engine import STEP  # noqa: E402
from engine import BROKERAGE_PER_ORDER, STT_SELL_PCT, EXCH_TXN_PCT, GST_PCT, \
    SEBI_PER_CRORE, STAMP_BUY_PCT  # noqa: E402

R, Q, LOT, SLIP = 0.065, 0.012, 75, 0.0075


@dataclass
class SellCfg:
    structure: str = "iron_condor"    # iron_condor | short_strangle | iron_fly
    target_dte: int = 3
    min_dte: int = 2
    max_dte: int = 5
    short_delta: float = 0.18         # sell legs (condor/strangle)
    wing_delta: float = 0.08          # buy wings (condor/fly)
    fly_wing_pts: int = 6             # iron_fly wing width in strikes
    strad_min: float = 0.0060         # richness filter: ATM straddle >= this % of spot
    target_frac: float = 0.50         # buy back at 50% of credit captured
    stop_mult: float = 2.0            # stop if cost-to-close >= stop_mult * credit
    entry_hhmm: str = "09:20"
    exit_hhmm: str = "15:15"
    capital: float = 3_00_000.0
    lot_size: int = 75


def _leg(df, k, otype):
    s = df[(df["strike"] == k) & (df["option_type"] == otype)]
    return s.set_index("t")["close"].sort_index()


def _leg_open_at(df, k, otype, t0):
    s = df[(df["strike"] == k) & (df["option_type"] == otype)].set_index("t").sort_index()
    a = s[s.index >= t0]
    return a["open"].iloc[0] if not a.empty else np.nan


def pick_delta(df, s0, T, iv, target, otype, avail):
    is_call = otype == "CE"
    best, bd = None, 9e9
    for k in avail:
        d = abs(float(bs_greeks(s0, k, T, iv, R, Q, is_call)["delta"]))
        if abs(d - target) < bd:
            bd, best = abs(d - target), k
    return best


def yte(t0, exp):
    ex = pd.Timestamp(exp) + pd.Timedelta(hours=15, minutes=30)
    return max((ex - t0).total_seconds() / (365.25 * 24 * 3600), 1e-5)


def costs_multi(sell_prem, buy_prem, close_prem, n_legs, lots, lot_size):
    qty = lots * lot_size
    n_orders = n_legs * 2
    brok = BROKERAGE_PER_ORDER * n_orders
    turnover = (sell_prem + buy_prem + close_prem) * qty
    exch = EXCH_TXN_PCT * turnover
    stt = STT_SELL_PCT * (sell_prem * qty)        # STT on sell-side premium
    gst = GST_PCT * (brok + exch)
    sebi = SEBI_PER_CRORE * turnover / 1e7
    stamp = STAMP_BUY_PCT * (buy_prem * qty)
    return brok + exch + stt + gst + sebi + stamp


def simulate(spot, exp, cfg: SellCfg):
    df = chain.load_expiry(exp)
    tdays = sorted(df["trading_day"].unique())
    entry_day = None
    for td in tdays:
        d = dt.date.fromisoformat(td)
        if cfg.min_dte <= (exp - d).days <= cfg.max_dte:
            entry_day = d
            if (exp - d).days <= cfg.target_dte:
                break
    if entry_day is None:
        return None
    et = pd.Timestamp(entry_day) + pd.Timedelta(
        hours=int(cfg.entry_hhmm[:2]), minutes=int(cfg.entry_hhmm[3:]))
    sp = spot[(spot.index.date == entry_day) & (spot.index <= et)]
    if sp.empty:
        return None
    s0 = sp["close"].iloc[-1]
    avail = sorted(df["strike"].unique())
    if len(avail) < 6:
        return None
    atmk = min(avail, key=lambda x: abs(x - round(s0 / STEP) * STEP))
    T = yte(et, exp)
    ce0 = _leg(df[df["t"] <= et], atmk, "CE")
    pe0 = _leg(df[df["t"] <= et], atmk, "PE")
    if ce0.empty or pe0.empty:
        return None
    straddle = ce0.iloc[-1] + pe0.iloc[-1]
    if straddle / s0 < cfg.strad_min:
        return {"skip": True, "exp": exp}
    iv = implied_vol(ce0.iloc[-1], s0, atmk, T, R, Q, True)
    if not (np.isfinite(iv) and 0.03 < iv < 1.5):
        iv = straddle / s0 / (0.8 * np.sqrt(T))   # rough fallback

    # choose strikes (short + wings)
    legs = []  # (strike, otype, side)  side=+1 sell, -1 buy
    if cfg.structure == "short_strangle":
        ksp = pick_delta(df, s0, T, iv, cfg.short_delta, "PE", avail)
        ksc = pick_delta(df, s0, T, iv, cfg.short_delta, "CE", avail)
        legs = [(ksp, "PE", +1), (ksc, "CE", +1)]
    elif cfg.structure == "iron_fly":
        legs = [(atmk, "PE", +1), (atmk, "CE", +1),
                (min(avail, key=lambda x: abs(x - (atmk - cfg.fly_wing_pts * STEP))), "PE", -1),
                (min(avail, key=lambda x: abs(x - (atmk + cfg.fly_wing_pts * STEP))), "CE", -1)]
    else:  # iron_condor
        ksp = pick_delta(df, s0, T, iv, cfg.short_delta, "PE", avail)
        ksc = pick_delta(df, s0, T, iv, cfg.short_delta, "CE", avail)
        kbp = pick_delta(df, s0, T, iv, cfg.wing_delta, "PE", avail)
        kbc = pick_delta(df, s0, T, iv, cfg.wing_delta, "CE", avail)
        kbp = min(kbp, ksp - STEP)
        kbc = max(kbc, ksc + STEP)
        legs = [(ksp, "PE", +1), (ksc, "CE", +1), (kbp, "PE", -1), (kbc, "CE", -1)]

    # entry prices (open at/after et)
    entry_px = {}
    for k, o, side in legs:
        px = _leg_open_at(df, k, o, et)
        if not np.isfinite(px):
            return None
        entry_px[(k, o)] = px
    sell_prem = sum(entry_px[(k, o)] for k, o, s in legs if s == +1)
    buy_prem = sum(entry_px[(k, o)] for k, o, s in legs if s == -1)
    credit = sell_prem - buy_prem
    if credit <= 0:
        return None
    # slippage: worse credit at entry
    fill_credit = (sum(entry_px[(k, o)] * (1 - SLIP) for k, o, s in legs if s == +1)
                   - sum(entry_px[(k, o)] * (1 + SLIP) for k, o, s in legs if s == -1))
    if fill_credit <= 0:
        return None

    # value-to-close path = sum(short_close) - sum(long_close)
    series = {}
    for k, o, side in legs:
        series[(k, o, side)] = _leg(df, k, o)
    idx = series[(legs[0][0], legs[0][1], legs[0][2])].index
    idx = idx[idx >= et]

    def val_at(t):
        v = 0.0
        for k, o, side in legs:
            s = series[(k, o, side)]
            sub = s[s.index <= t]
            if sub.empty:
                return np.nan
            v += side * sub.iloc[-1]
        return v

    # defined max loss (condor/fly)
    if cfg.structure == "short_strangle":
        max_loss = np.nan  # naked
    else:
        put_w = abs(legs[0][0] - legs[2][0]) if cfg.structure != "iron_fly" else cfg.fly_wing_pts * STEP
        call_w = abs(legs[1][0] - legs[3][0]) if cfg.structure != "iron_fly" else cfg.fly_wing_pts * STEP
        max_loss = (max(put_w, call_w) - fill_credit) * cfg.lot_size

    tgt = fill_credit * (1 - cfg.target_frac)   # cost-to-close small = profit taken
    stop_v = fill_credit * cfg.stop_mult
    exit_t = exit_v = reason = None
    step = 5  # check every 5 min for speed
    pts = list(idx)[::step]
    for t in pts:
        if t <= et:
            continue
        d_ = t.date()
        eod = pd.Timestamp(d_) + pd.Timedelta(hours=int(cfg.exit_hhmm[:2]),
                                              minutes=int(cfg.exit_hhmm[3:]))
        v = val_at(t)
        if not np.isfinite(v):
            continue
        if d_ >= exp and t >= eod:
            es = spot[spot.index.date == exp]
            s1 = es["close"].iloc[-1] if not es.empty else s0
            v = 0.0
            for k, o, side in legs:
                intr = max(0.0, (k - s1) if o == "PE" else (s1 - k))
                v += side * intr
            exit_t, exit_v, reason = t, max(v, 0.0), "expiry"; break
        if v <= tgt:
            exit_t, exit_v, reason = t, v, "target"; break
        if v >= stop_v:
            exit_t, exit_v, reason = t, v, "stop"; break
    if exit_t is None:
        exit_t, exit_v, reason = idx[-1], val_at(idx[-1]), "eod"

    close_prem = max(exit_v, 0.0)
    fill_close = close_prem * (1 + SLIP)
    n_legs = len(legs)
    gross = (fill_credit - fill_close) * cfg.lot_size
    costs = costs_multi(sell_prem, buy_prem, close_prem, n_legs, 1, cfg.lot_size)
    net = gross - costs
    return {"enter_day": entry_day, "exp": exp, "dte0": (exp - entry_day).days,
            "credit": fill_credit, "close": close_prem, "reason": reason,
            "net_pnl": net, "win": net > 0, "max_loss": max_loss,
            "hold_days": (exit_t.date() - entry_day).days,
            "strad_pct": straddle / s0}


def run(cfg, start, end, verbose=False):
    spot = chain.load_index()
    _, exps = chain.build_expiry_index()
    rows, skipped = [], 0
    for exp in exps:
        if not (start <= exp <= end):
            continue
        try:
            tr = simulate(spot, exp, cfg)
        except Exception as e:
            if verbose:
                print(f"  {exp}: ERR {type(e).__name__}: {e}")
            continue
        if tr is None:
            continue
        if tr.get("skip"):
            skipped += 1
            continue
        rows.append(tr)
    df = pd.DataFrame(rows)
    return df, skipped


def report(df, cfg, label):
    print(f"\n--- {label}: {len(df)} trades ---")
    if df.empty:
        print("  no trades"); return
    wr = df["win"].mean(); net = df["net_pnl"].sum()
    w = df[df["net_pnl"] > 0]["net_pnl"]; l = df[df["net_pnl"] <= 0]["net_pnl"]
    pf = w.sum() / abs(l.sum()) if l.sum() != 0 else np.inf
    # sharpe on per-trade returns (annualize by ~trades/yr), and on capital
    yrs = 4.6
    tpy = len(df) / yrs
    ml = df["max_loss"].mean()
    print(f"  WR {wr:.1%} | net Rs.{net:,.0f} (1 lot) | PF {pf:.2f} | "
          f"avg Rs.{df['net_pnl'].mean():,.0f} | worst Rs.{df['net_pnl'].min():,.0f}")
    print(f"  avg credit {df['credit'].mean():.1f} | avg max-loss/def-risk Rs.{ml:,.0f} "
          f"| avg hold {df['hold_days'].mean():.1f}d | reasons {df['reason'].value_counts().to_dict()}")
    # equity + sharpe/maxdd on capital
    d2 = df.sort_values("exp")
    eq = cfg.capital + d2["net_pnl"].cumsum().values
    peak = np.maximum.accumulate(eq)
    dd = ((eq - peak) / peak).min()
    r = d2["net_pnl"] / cfg.capital
    sharpe = r.mean() / r.std() * np.sqrt(tpy) if r.std() > 0 else 0
    print(f"  on Rs.{cfg.capital:,.0f}: total {net/cfg.capital:+.1%} | maxDD {dd:.1%} | "
          f"trade-Sharpe {sharpe:.2f} | ~{tpy:.0f} trades/yr")


if __name__ == "__main__":
    for struct in ["iron_condor", "iron_fly", "short_strangle"]:
        cfg = SellCfg(structure=struct)
        print("\n" + "=" * 74 + f"\n{struct.upper()}  (short_d={cfg.short_delta}, "
              f"filter straddle>={cfg.strad_min:.2%}, manage@{cfg.target_frac:.0%})\n" + "=" * 74)
        b, sk = run(cfg, dt.date(2021, 1, 1), dt.date(2025, 12, 31))
        print(f"  (build: {sk} expiries skipped by IV filter)")
        report(b, cfg, "BUILD 2021-2025")
        f, _ = run(cfg, dt.date(2026, 1, 1), dt.date(2026, 6, 2))
        report(f, cfg, "FORWARD 2026 H1")
