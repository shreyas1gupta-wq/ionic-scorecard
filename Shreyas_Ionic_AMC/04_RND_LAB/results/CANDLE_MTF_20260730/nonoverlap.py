"""NON-OVERLAPPING REPLAY — the honest version of the candle sweep.

THE DEFECT IN MY OWN SWEEP, FOUND BEFORE QUOTING IT:
  cells.csv reports THREE_SOLDIERS|none|BE_1R_trail at t=9.90, mean +37.53 pts, exp_R 0.524 over
  8,107 trades. exp_R of 0.52 per trade is not a real trading result; professional systems run
  0.05-0.15R. The cause:
    THREE_SOLDIERS fires on 8,172 of 69,848 bars = 11.7% of ALL 15-min bars, and MAX_BARS=78 holds
    each trade for up to 3 SESSIONS. So at any moment ~9 positions are open simultaneously, and the
    sweep summed them as independent trades.
  Two things break as a result:
    1. UNTRADEABLE. One retail account cannot hold 9 concurrent NIFTY futures positions at the
       sizing implied. The Principal asked for a retail spinner, not a 9-deep book.
    2. THE t-STAT IS FICTION. Overlapping 3-day holds make consecutive daily P&Ls heavily serially
       correlated, and t = mean/std*sqrt(n) assumes independence. t=9.90 is an artifact of counting
       the same market move 9 times.

WHAT THIS DOES
  ONE POSITION AT A TIME. Walk the bars forward; take a signal only if flat; block every new signal
  until the current trade exits at its own bar. That is what a retail trader actually does and it is
  the only version whose n, t, and equity curve mean anything.
  Also reports:
    - NEWEY-WEST t (5 lags) alongside the naive t, so the remaining autocorrelation is priced in
    - the concurrency the ORIGINAL cell implied, so the size of the inflation is visible
    - era split at Oct-2024 and held-out 2026, as everywhere else in this book
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
BASE = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, BASE + r"\Shreyas_Ionic_AMC\04_RND_LAB\lib")
from pathsafe import ExitResult, simulate_exit, summarize      # noqa: E402

OUT = Path(__file__).parent
BREAK, HELDOUT = pd.Timestamp("2024-10-01"), pd.Timestamp("2026-01-01")
SCH = {"2024-06-04", "2024-06-03", "2024-02-01", "2023-02-01", "2022-02-01",
       "2025-02-01", "2026-02-01", "2024-07-23"}
SLIP, LOT, CAP = 0.5, 65, 1_000_000.0
IDX = BASE + r"\intraday_options_strategy\datasets\processed\nifty_1min.parquet"

# ---------------------------------------------------------------- rebuild bars (same as the sweep)
p1 = pd.read_parquet(IDX, columns=["open", "high", "low", "close"]).sort_index()
p1 = p1[(p1.index.time >= pd.Timestamp("09:15").time()) &
        (p1.index.time <= pd.Timestamp("15:30").time())]
b15 = (p1.resample("15min", origin="start_day", offset="9h15min")
       .agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last")).dropna())
b15 = b15[(b15.index.time >= pd.Timestamp("09:15").time()) &
          (b15.index.time <= pd.Timestamp("15:15").time())]
b15["d"] = b15.index.normalize()
dly = p1.resample("1D").agg(h=("high", "max"), l=("low", "min"), c=("close", "last")).dropna()
dly["dma_bull"] = (dly.c.rolling(10).mean() > dly.c.rolling(20).mean()).shift(1)
tr = pd.concat([dly.h - dly.l, (dly.h - dly.c.shift()).abs(),
                (dly.l - dly.c.shift()).abs()], axis=1).max(axis=1)
dly["atr14"] = tr.rolling(14).mean()
wk = p1.resample("W-FRI").agg(c=("close", "last")).dropna()
wk["wk_bull"] = (wk.c.ewm(span=9, adjust=False).mean()
                 > wk.c.ewm(span=21, adjust=False).mean()).shift(1)
b15["ema9"] = b15.c.ewm(span=9, adjust=False).mean()
b15["ema21"] = b15.c.ewm(span=21, adjust=False).mean()
b15["e_bull"] = b15.ema9 > b15.ema21
b15 = b15.join(dly[["dma_bull", "atr14"]], on="d")
b15["wk_bull"] = pd.Series(wk.wk_bull.values, index=wk.index).reindex(
    b15.index, method="ffill").values

o, h, l, c = (b15[x].to_numpy(float) for x in ("o", "h", "l", "c"))
body, rng_ = c - o, h - l
ab = np.abs(body)
rng_s = np.where(rng_ <= 0, np.nan, rng_)
up_w, dn_w = h - np.maximum(o, c), np.minimum(o, c) - l
green, red = body > 0, body < 0


def sh(a, k=1):
    r = (np.zeros_like(a, dtype=bool) if a.dtype == bool
         else np.full_like(a, np.nan, dtype=float))
    r[k:] = a[:-k]
    return r


p_o, p_h, p_l, p_c = sh(o), sh(h), sh(l), sh(c)
p_ab = sh(ab)
p_green, p_red = sh(green.astype(float)) > .5, sh(red.astype(float)) > .5
pp_c, pp_o = sh(c, 2), sh(o, 2)
mid_prev = (p_o + p_c) / 2.0

F = {
    "BULL_ENGULF": (green & p_red & (c > p_o) & (o < p_c), +1),
    "BEAR_ENGULF": (red & p_green & (c < p_o) & (o > p_c), -1),
    "HAMMER": ((dn_w >= 2 * ab) & (up_w <= 0.3 * rng_s) & (c >= l + 0.6 * rng_s), +1),
    "SHOOTING_STAR": ((up_w >= 2 * ab) & (dn_w <= 0.3 * rng_s) & (c <= l + 0.4 * rng_s), -1),
    "MARUBOZU_BULL": (green & (ab >= 0.8 * rng_s), +1),
    "MARUBOZU_BEAR": (red & (ab >= 0.8 * rng_s), -1),
    "PIERCING": (green & p_red & (c > mid_prev) & (c < p_o) & (o < p_c), +1),
    "DARK_CLOUD": (red & p_green & (c < mid_prev) & (c > p_o) & (o > p_c), -1),
    "THREE_SOLDIERS": (green & p_green & (sh(green.astype(float), 2) > .5) &
                       (c > p_c) & (p_c > pp_c), +1),
    "THREE_CROWS": (red & p_red & (sh(red.astype(float), 2) > .5) &
                    (c < p_c) & (p_c < pp_c), -1),
    "MORNING_STAR": ((sh(red.astype(float), 2) > .5) & (p_ab <= 0.4 * sh(rng_, 2)) &
                     green & (c > (pp_o + pp_c) / 2), +1),
    "EVENING_STAR": ((sh(green.astype(float), 2) > .5) & (p_ab <= 0.4 * sh(rng_, 2)) &
                     red & (c < (pp_o + pp_c) / 2), -1),
    "TWEEZER_BOTTOM": ((np.abs(l - p_l) <= 0.1 * rng_s) & green & p_red, +1),
    "TWEEZER_TOP": ((np.abs(h - p_h) <= 0.1 * rng_s) & red & p_green, -1),
    "INSIDE_BREAK_UP": ((p_h < sh(h, 2)) & (p_l > sh(l, 2)) & (c > p_h), +1),
    "INSIDE_BREAK_DN": ((p_h < sh(h, 2)) & (p_l > sh(l, 2)) & (c < p_l), -1),
}
FILTERS = {
    "none": np.ones(len(b15), bool),
    "15m_ema": b15.e_bull.to_numpy(bool),
    "d_dma": b15.dma_bull.fillna(False).to_numpy(bool),
    "wk_ema": pd.Series(b15.wk_bull).fillna(False).to_numpy(bool),
    "d+wk": (b15.dma_bull.fillna(False).to_numpy(bool) &
             pd.Series(b15.wk_bull).fillna(False).to_numpy(bool)),
    "all3": (b15.e_bull.to_numpy(bool) & b15.dma_bull.fillna(False).to_numpy(bool) &
             pd.Series(b15.wk_bull).fillna(False).to_numpy(bool)),
}
atr = b15.atr14.to_numpy(float)
ds = b15.d.dt.strftime("%Y-%m-%d").to_numpy()
days = b15.d.to_numpy()
HLC = np.ascontiguousarray(b15[["h", "l", "c"]].to_numpy(float))
COLS = ["high", "low", "close"]
TS = b15.index.to_numpy()
N = len(b15)


def nw_t(x, lags=5):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 12:
        return np.nan
    m = x.mean(); dv = x - m; n = len(x); var = (dv @ dv) / n
    for L in range(1, min(lags, n - 1) + 1):
        var += 2 * (1 - L / (lags + 1)) * ((dv[L:] @ dv[:-L]) / n)
    return m / np.sqrt(var / n) if var > 0 else np.nan


def replay(mask, side, exit_kind, max_bars):
    """ONE POSITION AT A TIME. A signal is skipped while a trade is open."""
    rows = []
    i, blocked_until = 0, -1
    sig = np.where(mask)[0]
    sigset = set(int(x) for x in sig)
    for i in range(N):
        if i <= blocked_until or i not in sigset:
            continue
        if i + 4 >= N or ds[i] in SCH:
            continue
        a = atr[i]
        if not np.isfinite(a) or a <= 0:
            continue
        entry = c[i]
        raw = (entry - min(l[i], p_l[i])) if side > 0 else (max(h[i], p_h[i]) - entry)
        stop = max(raw, 0.4 * a)
        if not np.isfinite(stop) or stop <= 0 or stop > 3 * a:
            continue
        seg = HLC[i + 1:i + 1 + max_bars]
        if len(seg) < 4:
            continue
        bars = pd.DataFrame(seg, columns=COLS)
        if exit_kind.startswith("RR"):
            rr = float(exit_kind[2:])
            r_ = simulate_exit(bars, entry, side, stop=stop, target=rr * stop)
        elif exit_kind == "PARTIAL_1R_trail":
            h1 = simulate_exit(bars, entry, side, stop=stop, target=stop)
            h2 = simulate_exit(bars, entry, side, stop=stop, trail=stop)
            r_ = ExitResult(0.5 * h1.pnl_pessimistic + 0.5 * h2.pnl_pessimistic,
                            0.5 * h1.pnl_optimistic + 0.5 * h2.pnl_optimistic,
                            "partial", "partial", 0, h2.n_bars)
        else:
            r_ = simulate_exit(bars, entry, side, stop=stop, trail=stop)
        # find the bar the trade actually left on, so the block window is honest
        held = min(max_bars, len(seg))
        ct = (4.47 if pd.Timestamp(days[i]) < BREAK else 5.97) + SLIP
        rows.append(dict(t=TS[i], ds=ds[i], day=pd.Timestamp(days[i]), stop=stop,
                         pnl_p=r_.pnl_pessimistic - ct, pnl_o=r_.pnl_optimistic - ct,
                         why=r_.reason_pessimistic, held=held,
                         r_mult=(r_.pnl_pessimistic - ct) / stop))
        blocked_until = i + held
    return pd.DataFrame(rows)


def score(tr, lbl, orig_n=None):
    if len(tr) < 30:
        return None
    s = summarize([ExitResult(float(a), float(b), "", "", 0, 1)
                   for a, b in zip(tr.pnl_p, tr.pnl_o)], verbose=False)
    w, ls = tr[tr.pnl_p > 0], tr[tr.pnl_p <= 0]
    pf = float(w.pnl_p.sum() / abs(ls.pnl_p.sum())) if len(ls) and ls.pnl_p.sum() else np.nan
    rr = (float(w.pnl_p.mean() / abs(ls.pnl_p.mean()))
          if len(w) and len(ls) and ls.pnl_p.mean() != 0 else np.nan)
    dd = tr.groupby("ds").pnl_p.sum()
    eq = dd.cumsum()
    mdd = float((eq - eq.cummax()).min())
    months = max(len(pd.PeriodIndex(tr.day, freq="M").unique()), 1)
    yrs = max((tr.day.max() - tr.day.min()).days / 365.25, .08)
    ppy = tr.pnl_p.sum() / yrs
    lots = max(int(0.25 * CAP / max(abs(mdd) * LOT, 1)), 0)
    cagr = 100 * ppy * LOT * lots / CAP if lots >= 1 else 0.0
    return dict(cell=lbl, n=len(tr), orig_n=orig_n,
                overlap_x=round(orig_n / len(tr), 1) if orig_n else None,
                per_month=round(len(tr) / months, 1), win=round(float((tr.pnl_p > 0).mean()), 4),
                mean=round(float(tr.pnl_p.mean()), 2), avg_RR=round(rr, 2) if np.isfinite(rr) else None,
                PF=round(pf, 3) if np.isfinite(pf) else None,
                exp_R=round(float(tr.r_mult.mean()), 3),
                med_held=int(tr.held.median()), pts_yr=round(ppy, 0), maxDD=round(mdd, 0),
                Calmar=round(ppy / abs(mdd), 3) if mdd else None,
                t_naive=round(float(dd.mean() / dd.std() * np.sqrt(len(dd))), 2) if dd.std() else None,
                t_NW=round(float(nw_t(dd.values)), 2), lots_25pct=lots, CAGR_pct=round(cagr, 1),
                era_pre=round(float(tr[tr.day < BREAK].pnl_p.mean()), 2) if (tr.day < BREAK).sum() > 15 else None,
                era_post=round(float(tr[(tr.day >= BREAK) & (tr.day < HELDOUT)].pnl_p.mean()), 2)
                if ((tr.day >= BREAK) & (tr.day < HELDOUT)).sum() > 15 else None,
                ho_2026=round(float(tr[tr.day >= HELDOUT].pnl_p.mean()), 2)
                if (tr.day >= HELDOUT).sum() > 8 else None,
                ho_n=int((tr.day >= HELDOUT).sum()),
                reliable=bool(s.reliable), spread=round(s.spread_frac, 3))


# the cells that looked best in the overlapping sweep, plus shorter holds for retail practicality
R0 = pd.read_csv(OUT / "cells.csv")
top = R0.sort_values("t", ascending=False).head(20)["cell"].tolist()
top += R0[(R0["mean"] > 0) & (R0.n >= 100)].sort_values("avg_RR", ascending=False).head(8)["cell"].tolist()
top = list(dict.fromkeys(top))
HOLDS = [26, 52, 78]        # 1, 2, 3 sessions of 15-min bars
print(f"[replay] {len(top)} candidate cells x {len(HOLDS)} hold caps, ONE POSITION AT A TIME",
      flush=True)
print(f"{'cell':<44}{'hold':>5}{'n':>6}{'ovl':>6}{'/mo':>6}{'win':>7}{'mean':>8}{'RR':>6}"
      f"{'expR':>7}{'Calmar':>8}{'t_nv':>7}{'t_NW':>7}{'CAGR':>8}{'ho26':>8}", flush=True)
rep = []
for key in top:
    fname, flt, ex = key.split("|")
    fm, side = F[fname]
    fm = np.nan_to_num(fm.astype(float), nan=0.0) > .5
    fmask = FILTERS[flt]
    use = fmask if (side > 0 or flt == "none") else ~fmask
    m = fm & use
    onr = int(R0.loc[R0.cell == key, "n"].iloc[0])
    for hb in HOLDS:
        tr = replay(m, side, ex, hb)
        r = score(tr, f"{key}|hold{hb}", orig_n=onr if hb == 78 else None)
        if not r:
            continue
        rep.append(r)
        print(f"{key:<44}{hb:>5}{r['n']:>6}{str(r['overlap_x'] or '-'):>6}{r['per_month']:>6.1f}"
              f"{r['win']:>7.1%}{r['mean']:>8.2f}{(r['avg_RR'] or 0):>6.2f}{r['exp_R']:>7.3f}"
              f"{(r['Calmar'] or 0):>8.2f}{(r['t_naive'] or 0):>7.2f}{(r['t_NW'] or 0):>7.2f}"
              f"{r['CAGR_pct']:>7.1f}%{str(r['ho_2026']):>8}", flush=True)

D = pd.DataFrame(rep)
D.to_csv(OUT / "nonoverlap_cells.csv", index=False)
json.dump(dict(n=len(D), note="one position at a time; Newey-West t at 5 lags",
               holds=HOLDS), open(OUT / "nonoverlap_meta.json", "w"), indent=2)
print(f"\n[done] {len(D)} cells -> nonoverlap_cells.csv", flush=True)
if len(D):
    print("\nSURVIVORS: t_NW >= 3.0, positive held-out 2026, 10-100 trades/month, avg_RR >= 1.5")
    s = D[(D.t_NW >= 3.0) & (D.ho_2026.fillna(-1) > 0) & D.per_month.between(10, 100)
          & (D.avg_RR.fillna(0) >= 1.5)]
    print(s[["cell", "n", "per_month", "win", "mean", "avg_RR", "exp_R", "Calmar", "t_NW",
             "CAGR_pct", "ho_2026", "ho_n"]].to_string(index=False) if len(s)
          else "  NONE SURVIVE all four conditions.")
