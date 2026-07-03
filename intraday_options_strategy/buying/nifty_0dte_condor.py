"""NIFTY adaptation of 'Theta Profits' 0DTE Breakeven Iron Condor (John Sandvand, SPX).

Original (SPX): market-neutral iron condor, 0DTE, entered ~hourly through the day,
short strikes 10-15 delta, longs ~30 SPX points away (~0.5-0.6% width), equal credit per
side, OCO stop designed so a busted side closes near-breakeven, target ~full decay.

NIFTY adaptation: NIFTY's own weekly-expiry (0DTE) days, 5-6 entries/day ~1hr apart,
short strikes at target delta (test 10/12/15), wings at INDIA-scaled width (test 100/150/200
points, roughly matching SPX's 0.5-0.6% on NIFTY's ~25000 level), target %, stop multiple —
all swept to find the best Indian config. Fixed 1 lot per entry, real fills, full costs.
"""
from __future__ import annotations

import datetime as dt
import sys
from dataclasses import dataclass
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from options.bs_pricing import bs_greeks, implied_vol  # noqa: E402

import chain  # noqa: E402
from engine import STEP  # noqa: E402
from engine_sell import costs_multi  # noqa: E402

R_, Q_, LOT, SLIP = 0.065, 0.012, 75, 0.008
SPLIT = dt.date(2025, 12, 31)


@dataclass
class CondorCfg:
    short_delta: float = 0.12
    wing_pts: int = 150
    n_entries: int = 5
    target_frac: float = 0.60     # buy back at (1 - target_frac) of credit remaining
    stop_mult: float = 2.0        # stop when cost-to-close >= stop_mult x credit received
    entry_times: tuple = ("09:20", "10:20", "11:20", "12:20", "13:20")
    eod: str = "15:15"


def _t(day, hhmm):
    return pd.Timestamp(day) + pd.Timedelta(hours=int(hhmm[:2]), minutes=int(hhmm[3:]))


def pick_delta_strike(cdf_at_t, s0, T, iv, target, otype, avail):
    is_call = otype == "CE"
    ks = np.asarray(avail, dtype=float)
    d = np.abs(np.asarray(bs_greeks(s0, ks, T, iv, R_, Q_, is_call)["delta"]))
    return avail[int(np.argmin(np.abs(d - target)))]


def simulate_entry(cdf, spot, entry_t, day, exp, cfg: CondorCfg):
    avail = sorted(cdf["strike"].unique())
    if len(avail) < 8:
        return None
    atmk = min(avail, key=lambda x: abs(x - round(spot / STEP) * STEP))
    T = max((pd.Timestamp(exp) + pd.Timedelta(hours=15, minutes=30) - entry_t).total_seconds()
            / (365.25 * 24 * 3600), 1e-6)
    ce_atm = cdf[(cdf["strike"] == atmk) & (cdf["option_type"] == "CE") & (cdf["t"] <= entry_t)]
    if ce_atm.empty:
        return None
    iv = implied_vol(ce_atm["close"].iloc[-1], spot, atmk, T, R_, Q_, True)
    if not (np.isfinite(iv) and 0.02 < iv < 3.0):
        iv = 0.12

    ksc = pick_delta_strike(cdf, spot, T, iv, cfg.short_delta, "CE", avail)
    ksp = pick_delta_strike(cdf, spot, T, iv, cfg.short_delta, "PE", avail)
    kbc = min(avail, key=lambda x: abs(x - (ksc + cfg.wing_pts)))
    kbp = min(avail, key=lambda x: abs(x - (ksp - cfg.wing_pts)))
    if kbc <= ksc:
        kbc = ksc + STEP
    if kbp >= ksp:
        kbp = ksp - STEP
    legs = [(ksc, "CE", +1), (kbc, "CE", -1), (ksp, "PE", +1), (kbp, "PE", -1)]

    def leg_series(k, o):
        s = cdf[(cdf["strike"] == k) & (cdf["option_type"] == o)].set_index("t")["close"].sort_index()
        return s[s.index >= entry_t]

    series = {}
    entry_px = {}
    for k, o, side in legs:
        s = leg_series(k, o)
        if s.empty:
            return None
        series[(k, o, side)] = s
        entry_px[(k, o)] = s.iloc[0]
    sell_prem = sum(entry_px[(k, o)] for k, o, s in legs if s == +1)
    buy_prem = sum(entry_px[(k, o)] for k, o, s in legs if s == -1)
    credit = (sum(entry_px[(k, o)] * (1 - SLIP) for k, o, s in legs if s == +1)
              - sum(entry_px[(k, o)] * (1 + SLIP) for k, o, s in legs if s == -1))
    if credit <= 0:
        return None

    idx = series[legs[0][:3]].index
    common_idx = idx
    for k, o, side in legs[1:]:
        common_idx = common_idx.intersection(series[(k, o, side)].index)
    common_idx = common_idx.sort_values()
    if len(common_idx) == 0:
        return None

    def val_at(t):
        v = 0.0
        for k, o, side in legs:
            s = series[(k, o, side)]
            sub = s[s.index <= t]
            if sub.empty:
                return np.nan
            v += side * sub.iloc[-1]
        return v

    tgt = credit * (1 - cfg.target_frac)
    stop_v = credit * cfg.stop_mult
    eod_t = _t(day, cfg.eod)
    exit_v = reason = None
    for t in common_idx[::3]:      # sample every 3 min for speed
        if t <= entry_t:
            continue
        if t >= eod_t:
            v = val_at(t)
            exit_v, reason = (v if np.isfinite(v) else 0.0), "eod"; break
        v = val_at(t)
        if not np.isfinite(v):
            continue
        if v <= tgt:
            exit_v, reason = v, "target"; break
        if v >= stop_v:
            exit_v, reason = v, "stop"; break
    if exit_v is None:
        v = val_at(common_idx[-1])
        exit_v, reason = (v if np.isfinite(v) else 0.0), "eod"

    close_prem = max(exit_v, 0.0)
    fill_close = close_prem * (1 + SLIP)
    gross = (credit - fill_close) * LOT
    costs = costs_multi(sell_prem, buy_prem, close_prem, 4, 1, LOT)
    net = gross - costs
    return {"day": day, "entry_t": entry_t, "credit": credit, "reason": reason, "net_pnl": net,
            "win": net > 0}


def run(cfg: CondorCfg, start, end):
    return run_grid([cfg], start, end)[id(cfg)]


def run_grid(cfgs: list, start, end):
    """Day-major: load each 0DTE day's chain ONCE, evaluate ALL configs against it.
    Avoids re-reading the same ~260 expiry files once per config (27x waste)."""
    spot = chain.load_index()
    days = sorted({d for d in spot.index.date if start <= d <= end})
    out = {id(c): [] for c in cfgs}
    max_entries = max(c.n_entries for c in cfgs)
    all_times = sorted(set(t for c in cfgs for t in c.entry_times[:c.n_entries]))
    for day in days:
        exp = chain.nearest_expiry(day, 0, 0)
        if exp is None or exp != day:
            continue
        cdf = chain.day_chain(exp, day)
        if cdf.empty:
            continue
        sd = spot[spot.index.date == day]
        spot_at = {}
        for hhmm in all_times:
            et = _t(day, hhmm)
            se = sd[sd.index <= et]
            if not se.empty:
                spot_at[hhmm] = (et, se["close"].iloc[-1])
        for cfg in cfgs:
            for hhmm in cfg.entry_times[:cfg.n_entries]:
                if hhmm not in spot_at:
                    continue
                et, s0 = spot_at[hhmm]
                try:
                    tr = simulate_entry(cdf, s0, et, day, exp, cfg)
                except Exception:
                    tr = None
                if tr:
                    out[id(cfg)].append(tr)
    return {k: pd.DataFrame(v) for k, v in out.items()}


def stat(df, cap=3_00_000.0):
    if df.empty or len(df) < 5:
        return dict(n=len(df))
    wr = df["win"].mean(); net = df["net_pnl"].sum()
    w = df[df["net_pnl"] > 0]["net_pnl"]; l = df[df["net_pnl"] <= 0]["net_pnl"]
    pf = w.sum() / abs(l.sum()) if l.sum() != 0 else 99.0
    d2 = df.sort_values("day")
    daily = d2.groupby("day")["net_pnl"].sum()
    eq = cap + daily.cumsum().values
    dd = ((eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)).min()
    r = daily.values / cap
    yrs = max((d2["day"].iloc[-1] - d2["day"].iloc[0]).days / 365.25, 0.1)
    sharpe = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0
    return dict(n=len(df), wr=wr, pf=pf, net=net, tot=net / cap, maxdd=dd, sharpe=sharpe)


if __name__ == "__main__":
    DELTAS = [0.10, 0.12, 0.15]
    WIDTHS = [100, 150, 200]
    STOPS = [1.5, 2.0, 2.5]
    cfgs = [CondorCfg(short_delta=d, wing_pts=w, stop_mult=s) for d, w, s in product(DELTAS, WIDTHS, STOPS)]
    print(f"[grid] {len(cfgs)} configs, day-major single pass (build)...")
    build_out = run_grid(cfgs, dt.date(2021, 1, 1), dt.date(2025, 12, 31))
    print(f"[grid] {len(cfgs)} configs, day-major single pass (forward)...")
    fwd_out = run_grid(cfgs, dt.date(2026, 1, 1), dt.date(2026, 6, 2))

    results = []
    for cfg in cfgs:
        b, f = build_out[id(cfg)], fwd_out[id(cfg)]
        sb, sf = stat(b), stat(f)
        results.append({"delta": cfg.short_delta, "width": cfg.wing_pts, "stop": cfg.stop_mult,
                        "b_n": sb.get("n", 0), "b_wr": sb.get("wr", np.nan), "b_pf": sb.get("pf", np.nan),
                        "b_sharpe": sb.get("sharpe", np.nan), "b_maxdd": sb.get("maxdd", np.nan),
                        "b_tot": sb.get("tot", np.nan),
                        "f_n": sf.get("n", 0), "f_pf": sf.get("pf", np.nan),
                        "f_sharpe": sf.get("sharpe", np.nan), "f_tot": sf.get("tot", np.nan)})
        print(f"delta={cfg.short_delta:.2f} width={cfg.wing_pts} stop={cfg.stop_mult}: "
              f"B n={sb.get('n',0):4d} WR={sb.get('wr',0):.0%} PF={sb.get('pf',0):.2f} "
              f"Sharpe={sb.get('sharpe',0):.2f} DD={sb.get('maxdd',0):.0%} tot={sb.get('tot',0):+.0%} | "
              f"F n={sf.get('n',0):4d} PF={sf.get('pf',0):.2f} Sharpe={sf.get('sharpe',0):.2f} tot={sf.get('tot',0):+.0%}")
    RES = pd.DataFrame(results)
    RES.to_csv(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\buying\nifty_0dte_condor_grid.csv", index=False)
    print("\nTOP 10 by BUILD Sharpe:")
    print(RES.sort_values("b_sharpe", ascending=False).head(10).to_string(index=False))
    print("\nRobust (build AND forward Sharpe > 0), top by forward Sharpe:")
    robust = RES[(RES["b_sharpe"] > 0) & (RES["f_sharpe"] > 0)]
    print(robust.sort_values("f_sharpe", ascending=False).head(10).to_string(index=False))
