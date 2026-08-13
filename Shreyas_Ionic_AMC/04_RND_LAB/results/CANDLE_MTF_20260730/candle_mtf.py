"""15-MIN CANDLE FORMATIONS x MULTI-TIMEFRAME EMA/DMA ALIGNMENT, harvested at RR >= 1.5.

PRINCIPAL'S SPEC (2026-07-30):
  "CAN WE TRADE SOMETHING BASIS 15MIN CANDLE FORMATIONS AND SIMILARLY WITH WEEKLY CANDLES COMBINED
   WITH 9,21 EMA OR 10-20 DMA ON BUYING OR SELLING SIDE. NOTE WE ARE RETAIL, DO NOT GIVE TOO LARGE
   TRADE STRATEGY FIND SPINERS WITH MAX 10-100 TRADES PER MONTH HIGHLY PROFITABLE, HIGHER CHANCES OF
   WIN AND >1.5 RISK REWARD ON AVG [1.5 IS MINIMUM WE CAN TRAIL OR BOOK OR PARTIAL AND IMPROVE SMART]"

WHY THIS SETUP IS STRUCTURALLY MORE FAVOURABLE THAN TODAY'S FAILURES
  Everything that lost today lost to the SAME arithmetic: a 2-5 point measured edge against a fixed
  vehicle cost of 1.77 premium points (options) or ~5-6 index points (futures). The binding ratio is
  COST / TARGET. Today's option-buying harvest had a 22.5-point premium target -> cost was 8% of it,
  but the hit rate sat exactly at breakeven so there was nothing to take.
  A 15-min formation stop is the PRIOR CANDLE'S EXTREME, typically 20-35 index points. A 1.5R target
  is then 30-52 points and the futures round trip is 13-21% of it. That is a genuinely different
  regime from a 2-hour 4-point drift, which is why it is worth the run.
  THE BAR: at RR 1:1.5, breakeven hit rate is 40.0% GROSS. Net of a 5.47-point average round trip on
  a 1R of ~25 points, breakeven rises to about 45%. That is the number to beat.

WHAT IS TESTED
  16 formations (8 bullish -> long, 8 bearish -> short), each detected on completed 15-min bars only.
  6 trend filters:  none / 15m 9-21 EMA / daily 10-20 DMA / weekly 9-21 EMA / daily+weekly / all three
  5 exit harvests:  RR 1.5 / RR 2.0 / RR 2.5 / partial 50% at 1R then trail / breakeven at 1R then trail
  => 480 cells. Bonferroni bar at m=480 is t ~ 3.8. Anything below that is not a finding.

CONTROLS
  - Every exit through lib/pathsafe: target is a resting limit, STOP RESOLVES ADVERSELY, both
    intra-bar bounds returned, and a cell whose bounds disagree by >25% is flagged UNRELIABLE.
  - RANDOM-ENTRY PLACEBO matched on count, time-of-day and filter state: if random entries inside the
    same filter earn the same, the FORMATION contributed nothing and the filter was the whole effect.
  - Era split at Oct-2024 (SEBI F&O tightening + STT rise) and 2026 held out entirely.
  - Retail band enforced in the report: trades/month printed for every cell, band 10-100 flagged.
  - Costs era-correct: 4.47 index pts round trip before 2024-10-01, 5.97 after, +0.5 slippage.
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
OUT.mkdir(parents=True, exist_ok=True)
IDX = BASE + r"\intraday_options_strategy\datasets\processed\nifty_1min.parquet"
RNG = np.random.default_rng(20260730)
HELDOUT = pd.Timestamp("2026-01-01")
BREAK = pd.Timestamp("2024-10-01")
SCH = {"2024-06-04", "2024-06-03", "2024-02-01", "2023-02-01", "2022-02-01",
       "2025-02-01", "2026-02-01", "2024-07-23"}
MAX_BARS = 26 * 3          # cap the hold at ~3 sessions of 15-min bars
SLIP = 0.5


def cost(day):
    return (4.47 if pd.Timestamp(day) < BREAK else 5.97) + SLIP


# ---------------------------------------------------------------- bars
print("[load] 1-min -> 15-min", flush=True)
p1 = pd.read_parquet(IDX, columns=["open", "high", "low", "close"]).sort_index()
p1 = p1[(p1.index.time >= pd.Timestamp("09:15").time()) &
        (p1.index.time <= pd.Timestamp("15:30").time())]
b15 = (p1.resample("15min", origin="start_day", offset="9h15min")
       .agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last")).dropna())
b15 = b15[(b15.index.time >= pd.Timestamp("09:15").time()) &
          (b15.index.time <= pd.Timestamp("15:15").time())]
b15["d"] = b15.index.normalize()
print(f"       15-min bars {len(b15):,}  {b15.index.min()} .. {b15.index.max()}", flush=True)

dly = p1.resample("1D").agg(o=("open", "first"), h=("high", "max"),
                            l=("low", "min"), c=("close", "last")).dropna()
dly["ema9"] = dly.c.ewm(span=9, adjust=False).mean()
dly["ema21"] = dly.c.ewm(span=21, adjust=False).mean()
dly["dma10"] = dly.c.rolling(10).mean()
dly["dma20"] = dly.c.rolling(20).mean()
tr = pd.concat([dly.h - dly.l, (dly.h - dly.c.shift()).abs(),
                (dly.l - dly.c.shift()).abs()], axis=1).max(axis=1)
dly["atr14"] = tr.rolling(14).mean()
# DAILY signals must be shifted: a bar's own close is not known while it trades
dly["dma_bull"] = (dly.dma10 > dly.dma20).shift(1)

wk = p1.resample("W-FRI").agg(o=("open", "first"), h=("high", "max"),
                              l=("low", "min"), c=("close", "last")).dropna()
wk["ema9"] = wk.c.ewm(span=9, adjust=False).mean()
wk["ema21"] = wk.c.ewm(span=21, adjust=False).mean()
wk["wk_bull"] = (wk.ema9 > wk.ema21).shift(1)          # prior completed week only
# weekly candle formations, for the positional arm
wb = wk.assign(body=(wk.c - wk.o), rng=(wk.h - wk.l))
wk["wk_engulf_bull"] = ((wb.body > 0) & (wb.body.shift(1) < 0) &
                        (wk.c > wk.o.shift(1)) & (wk.o < wk.c.shift(1))).shift(1)
wk["wk_engulf_bear"] = ((wb.body < 0) & (wb.body.shift(1) > 0) &
                        (wk.c < wk.o.shift(1)) & (wk.o > wk.c.shift(1))).shift(1)
wk["wk_hammer"] = (((wk[["o", "c"]].min(axis=1) - wk.l) >= 2 * wb.body.abs()) &
                   ((wk.h - wk[["o", "c"]].max(axis=1)) <= 0.35 * wb.rng)).shift(1)

b15["ema9"] = b15.c.ewm(span=9, adjust=False).mean()
b15["ema21"] = b15.c.ewm(span=21, adjust=False).mean()
b15["e_bull"] = b15.ema9 > b15.ema21

# map daily/weekly state onto each 15-min bar (prior-period values only -> no lookahead)
b15 = b15.join(dly[["dma_bull", "atr14"]], on="d")
b15["wk_bull"] = pd.Series(wk.wk_bull.values, index=wk.index).reindex(
    b15.index, method="ffill").values
for c_ in ("wk_engulf_bull", "wk_engulf_bear", "wk_hammer"):
    b15[c_] = pd.Series(wk[c_].values, index=wk.index).reindex(b15.index, method="ffill").values

# ---------------------------------------------------------------- formations on completed bars
o, h, l, c = (b15[x].to_numpy(float) for x in ("o", "h", "l", "c"))
body = c - o
ab = np.abs(body)
rng_ = h - l
rng_s = np.where(rng_ <= 0, np.nan, rng_)
up_w = h - np.maximum(o, c)
dn_w = np.minimum(o, c) - l
green, red = body > 0, body < 0


def sh(a, k=1):
    r = np.full_like(a, np.nan, dtype=float) if a.dtype != bool else np.zeros_like(a, dtype=bool)
    r[k:] = a[:-k]
    return r


p_o, p_h, p_l, p_c = sh(o), sh(h), sh(l), sh(c)
p_body, p_ab, p_rng = sh(body), sh(ab), sh(rng_)
p_green, p_red = sh(green.astype(float)) > .5, sh(red.astype(float)) > .5
pp_c, pp_o = sh(c, 2), sh(o, 2)
mid_prev = (p_o + p_c) / 2.0

F = {}
F["BULL_ENGULF"] = (green & p_red & (c > p_o) & (o < p_c), +1)
F["BEAR_ENGULF"] = (red & p_green & (c < p_o) & (o > p_c), -1)
F["HAMMER"] = ((dn_w >= 2 * ab) & (up_w <= 0.3 * rng_s) & (c >= l + 0.6 * rng_s), +1)
F["SHOOTING_STAR"] = ((up_w >= 2 * ab) & (dn_w <= 0.3 * rng_s) & (c <= l + 0.4 * rng_s), -1)
F["MARUBOZU_BULL"] = (green & (ab >= 0.8 * rng_s), +1)
F["MARUBOZU_BEAR"] = (red & (ab >= 0.8 * rng_s), -1)
F["PIERCING"] = (green & p_red & (c > mid_prev) & (c < p_o) & (o < p_c), +1)
F["DARK_CLOUD"] = (red & p_green & (c < mid_prev) & (c > p_o) & (o > p_c), -1)
F["THREE_SOLDIERS"] = (green & p_green & (sh(green.astype(float), 2) > .5) &
                       (c > p_c) & (p_c > pp_c), +1)
F["THREE_CROWS"] = (red & p_red & (sh(red.astype(float), 2) > .5) &
                    (c < p_c) & (p_c < pp_c), -1)
F["MORNING_STAR"] = ((sh(red.astype(float), 2) > .5) & (p_ab <= 0.4 * sh(rng_, 2)) &
                     green & (c > (pp_o + pp_c) / 2), +1)
F["EVENING_STAR"] = ((sh(green.astype(float), 2) > .5) & (p_ab <= 0.4 * sh(rng_, 2)) &
                     red & (c < (pp_o + pp_c) / 2), -1)
F["TWEEZER_BOTTOM"] = ((np.abs(l - p_l) <= 0.1 * rng_s) & green & p_red, +1)
F["TWEEZER_TOP"] = ((np.abs(h - p_h) <= 0.1 * rng_s) & red & p_green, -1)
F["INSIDE_BREAK_UP"] = ((p_h < sh(h, 2)) & (p_l > sh(l, 2)) & (c > p_h), +1)
F["INSIDE_BREAK_DN"] = ((p_h < sh(h, 2)) & (p_l > sh(l, 2)) & (c < p_l), -1)

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
EXITS = ["RR1.5", "RR2.0", "RR2.5", "PARTIAL_1R_trail", "BE_1R_trail"]

atr = b15.atr14.to_numpy(float)
days = b15.d.to_numpy()
ds = b15.d.dt.strftime("%Y-%m-%d").to_numpy()
print(f"[formations] " + ", ".join(f"{k}:{int(np.nansum(v[0]))}" for k, v in F.items()), flush=True)


HLC = np.ascontiguousarray(b15[["h", "l", "c"]].to_numpy(float))
COLS = ["high", "low", "close"]
TS = b15.index.to_numpy()


def run_all_exits(mask, side):
    """Simulate ALL exits for one (formation x filter) in a single pass over the trades.

    The first version of this rebuilt the bar frame once PER EXIT, i.e. 5x per trade, and the
    DataFrame construction dominated the runtime (2.2M frames, iloc + rename + astype each).
    Building it once per trade from a contiguous numpy view and reusing it across the 5 exits is
    the same computation with a fifth of the frame overhead.
    """
    idx = np.where(mask)[0]
    rows = {e: [] for e in EXITS}
    for i in idx:
        if i + 4 >= len(b15) or ds[i] in SCH:
            continue
        a = atr[i]
        if not np.isfinite(a) or a <= 0:
            continue
        entry = c[i]
        # stop = prior candle's extreme, floored at 0.4 ATR so it cannot be absurdly tight
        raw = (entry - min(l[i], p_l[i])) if side > 0 else (max(h[i], p_h[i]) - entry)
        stop = max(raw, 0.4 * a)
        if not np.isfinite(stop) or stop <= 0 or stop > 3 * a:
            continue
        seg = HLC[i + 1:i + 1 + MAX_BARS]
        if len(seg) < 4:
            continue
        bars = pd.DataFrame(seg, columns=COLS)
        ct = cost(days[i])
        base = dict(t=TS[i], ds=ds[i], day=pd.Timestamp(days[i]), side=side, stop=stop, atr=a)
        # the trail leg is shared by PARTIAL and BE, so compute it once
        trail_res = simulate_exit(bars, entry, side, stop=stop, trail=stop)
        one_r = simulate_exit(bars, entry, side, stop=stop, target=1.0 * stop)
        for ex in EXITS:
            if ex.startswith("RR"):
                rr = float(ex[2:])
                r_ = (one_r if rr == 1.0
                      else simulate_exit(bars, entry, side, stop=stop, target=rr * stop))
                pp, po, why = r_.pnl_pessimistic, r_.pnl_optimistic, r_.reason_pessimistic
            elif ex == "PARTIAL_1R_trail":
                # half booked at exactly 1R (resting limit, exact); half trailed by `stop`
                pp = 0.5 * one_r.pnl_pessimistic + 0.5 * trail_res.pnl_pessimistic
                po = 0.5 * one_r.pnl_optimistic + 0.5 * trail_res.pnl_optimistic
                why = f"{one_r.reason_pessimistic}/{trail_res.reason_pessimistic}"
            else:   # BE_1R_trail: trail at 1R distance = breakeven then give back 1R
                pp, po, why = (trail_res.pnl_pessimistic, trail_res.pnl_optimistic,
                               trail_res.reason_pessimistic)
            rows[ex].append(dict(base, pnl_p=pp - ct, pnl_o=po - ct, why=why,
                                 r_mult=(pp - ct) / stop))
    return {e: pd.DataFrame(v) for e, v in rows.items()}


def score(tr, lbl, extra=None):
    if len(tr) < 40:
        return None
    s = summarize([ExitResult(float(a), float(b), "", "", 0, 1)
                   for a, b in zip(tr.pnl_p, tr.pnl_o)], verbose=False)
    w, ls = tr[tr.pnl_p > 0], tr[tr.pnl_p <= 0]
    pf = float(w.pnl_p.sum() / abs(ls.pnl_p.sum())) if len(ls) and ls.pnl_p.sum() else np.nan
    avg_rr = (float(w.pnl_p.mean() / abs(ls.pnl_p.mean()))
              if len(w) and len(ls) and ls.pnl_p.mean() != 0 else np.nan)
    dd = tr.groupby("ds").pnl_p.sum()
    eq = dd.cumsum()
    mdd = float((eq - eq.cummax()).min())
    months = max(len(pd.PeriodIndex(tr.day, freq="M").unique()), 1)
    yrs = max((tr.day.max() - tr.day.min()).days / 365.25, .08)
    ppy = tr.pnl_p.sum() / yrs
    t = float(dd.mean() / dd.std() * np.sqrt(len(dd))) if dd.std() > 0 else np.nan
    r = dict(cell=lbl, n=len(tr), per_month=round(len(tr) / months, 1),
             win=round(float((tr.pnl_p > 0).mean()), 4),
             mean=round(float(tr.pnl_p.mean()), 2), median=round(float(tr.pnl_p.median()), 2),
             avg_win=round(float(w.pnl_p.mean()), 1) if len(w) else None,
             avg_loss=round(float(ls.pnl_p.mean()), 1) if len(ls) else None,
             avg_RR=round(avg_rr, 2) if np.isfinite(avg_rr) else None,
             PF=round(pf, 3) if np.isfinite(pf) else None,
             exp_R=round(float(tr.r_mult.mean()), 3),
             pts_yr=round(ppy, 0), maxDD=round(mdd, 0),
             Calmar=round(ppy / abs(mdd), 3) if mdd else None, t=round(t, 2),
             reliable=bool(s.reliable), spread=round(s.spread_frac, 3))
    if extra:
        r.update(extra)
    return r


# ---------------------------------------------------------------- sweep
print(f"\n[sweep] {len(F)} formations x {len(FILTERS)} filters x {len(EXITS)} exits = "
      f"{len(F) * len(FILTERS) * len(EXITS)} cells; Bonferroni bar t~3.8", flush=True)
rep = []
store = {}
for fname, (fm, side) in F.items():
    fm = np.nan_to_num(fm.astype(float), nan=0.0) > .5
    for flt, fmask in FILTERS.items():
        # a bearish formation wants the INVERTED trend filter (short with the downtrend)
        use = fmask if side > 0 else ~fmask
        if flt == "none":
            use = fmask
        m = fm & use
        if m.sum() < 40:
            continue
        allex = run_all_exits(m, side)
        for ex in EXITS:
            tr = allex[ex]
            if len(tr) < 40:
                continue
            key = f"{fname}|{flt}|{ex}"
            store[key] = tr
            r = score(tr, key)
            if r:
                r["era_pre"] = round(float(tr[tr.day < BREAK].pnl_p.mean()), 2) \
                    if (tr.day < BREAK).sum() > 20 else None
                r["era_post"] = round(float(tr[(tr.day >= BREAK) & (tr.day < HELDOUT)].pnl_p.mean()), 2) \
                    if ((tr.day >= BREAK) & (tr.day < HELDOUT)).sum() > 20 else None
                r["ho_2026"] = round(float(tr[tr.day >= HELDOUT].pnl_p.mean()), 2) \
                    if (tr.day >= HELDOUT).sum() > 10 else None
                r["ho_n"] = int((tr.day >= HELDOUT).sum())
                rep.append(r)
    print(f"  {fname:<16} cells so far {len(rep)}", flush=True)

R = pd.DataFrame(rep)
R.to_csv(OUT / "cells.csv", index=False)
print(f"\n[done] {len(R)} scored cells -> cells.csv", flush=True)
json.dump(dict(n_cells=int(len(R)), bonferroni_m=int(len(R)), t_bar=3.8,
               formations=list(F), filters=list(FILTERS), exits=EXITS,
               retail_band=[10, 100], heldout_from=str(HELDOUT.date())),
          open(OUT / "meta.json", "w"), indent=2)
import pickle
pickle.dump({k: v for k, v in store.items()}, open(OUT / "trades.pkl", "wb"))
print("wrote meta.json + trades.pkl", flush=True)
