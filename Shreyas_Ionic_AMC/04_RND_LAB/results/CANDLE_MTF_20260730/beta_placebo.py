"""IS IT THE PATTERN, OR IS IT LONG BETA WITH A WIDE TRAIL? The decisive test.

WHY I AM RUNNING THIS BEFORE QUOTING ANY OF IT
  nonoverlap_cells.csv survives everything I have thrown at it so far: one position at a time,
  Newey-West t of 7.85, held-out 2026 positive, 5-13 trades/month, avg RR 2.04, win 53.4%.
  Two facts say stop and check anyway:
    1. EVERY top cell is a BULLISH formation - THREE_SOLDIERS, MORNING_STAR, HAMMER, TWEEZER_BOTTOM,
       MARUBOZU_BULL, BULL_ENGULF, PIERCING, INSIDE_BREAK_UP. Not one bearish formation appears.
    2. NIFTY went from ~8,000 to ~26,000 across this sample, +225%. And the winning exit is always
       BE_1R_trail - a WIDE trail (stop = max(prior-candle range, 0.4 x DAILY ATR) which is ~100
       index points, not 25) held for up to 3 sessions.
  "Go long on strength, trail 100 points behind, hold 3 days" will print money on a tripling index
  with no pattern recognition whatsoever. An expectancy of 0.61R per trade is not a candlestick
  edge; it is what index beta looks like when you harvest it with a wide trailing stop.

THE THREE NULLS
  N1 RANDOM-TIME LONG: same trade count, same time-of-day histogram, RANDOM bars, LONG, identical
     stop/trail/hold. This is the number that matters. If N1 earns what the pattern earns, the
     pattern contributes nothing.
  N2 EVERY-BAR LONG: take a long on a large random sample of ALL bars. The unconditional beta
     harvest. Gives the scale of the free lunch.
  N3 SHORT MIRROR: the same pattern logic, same exit, but SHORT. If longs pay and shorts lose by a
     symmetric amount, the effect is directional drift, not pattern information.

If N1 >= the pattern, the correct verdict is "this is beta, not alpha" and it must be reported that
way regardless of how good the t-stat looks.
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
from pathsafe import ExitResult, simulate_exit      # noqa: E402

OUT = Path(__file__).parent
BREAK, HELDOUT = pd.Timestamp("2024-10-01"), pd.Timestamp("2026-01-01")
SCH = {"2024-06-04", "2024-06-03", "2024-02-01", "2023-02-01", "2022-02-01",
       "2025-02-01", "2026-02-01", "2024-07-23"}
SLIP, N_DRAW = 0.5, 120
RNG = np.random.default_rng(90210)
IDX = BASE + r"\intraday_options_strategy\datasets\processed\nifty_1min.parquet"

p1 = pd.read_parquet(IDX, columns=["open", "high", "low", "close"]).sort_index()
p1 = p1[(p1.index.time >= pd.Timestamp("09:15").time()) &
        (p1.index.time <= pd.Timestamp("15:30").time())]
b15 = (p1.resample("15min", origin="start_day", offset="9h15min")
       .agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last")).dropna())
b15 = b15[(b15.index.time >= pd.Timestamp("09:15").time()) &
          (b15.index.time <= pd.Timestamp("15:15").time())]
b15["d"] = b15.index.normalize()
dly = p1.resample("1D").agg(h=("high", "max"), l=("low", "min"), c=("close", "last")).dropna()
tr = pd.concat([dly.h - dly.l, (dly.h - dly.c.shift()).abs(),
                (dly.l - dly.c.shift()).abs()], axis=1).max(axis=1)
dly["atr14"] = tr.rolling(14).mean()
dly["dma_bull"] = (dly.c.rolling(10).mean() > dly.c.rolling(20).mean()).shift(1)
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
body = c - o
ab = np.abs(body)
rng_ = h - l
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
    "THREE_SOLDIERS": (green & p_green & (sh(green.astype(float), 2) > .5) &
                       (c > p_c) & (p_c > pp_c), +1),
    "MORNING_STAR": ((sh(red.astype(float), 2) > .5) & (p_ab <= 0.4 * sh(rng_, 2)) &
                     green & (c > (pp_o + pp_c) / 2), +1),
    "HAMMER": ((dn_w >= 2 * ab) & (up_w <= 0.3 * rng_s) & (c >= l + 0.6 * rng_s), +1),
    "MARUBOZU_BULL": (green & (ab >= 0.8 * rng_s), +1),
    "BULL_ENGULF": (green & p_red & (c > p_o) & (o < p_c), +1),
    "TWEEZER_BOTTOM": ((np.abs(l - p_l) <= 0.1 * rng_s) & green & p_red, +1),
    "THREE_CROWS": (red & p_red & (sh(red.astype(float), 2) > .5) &
                    (c < p_c) & (p_c < pp_c), -1),
    "SHOOTING_STAR": ((up_w >= 2 * ab) & (dn_w <= 0.3 * rng_s) & (c <= l + 0.4 * rng_s), -1),
}
atr = b15.atr14.to_numpy(float)
ds = b15.d.dt.strftime("%Y-%m-%d").to_numpy()
days = b15.d.to_numpy()
HLC = np.ascontiguousarray(b15[["h", "l", "c"]].to_numpy(float))
COLS = ["high", "low", "close"]
hhmm = np.array([t.hour * 100 + t.minute for t in b15.index])
N = len(b15)


def replay(entries, side, max_bars, block=True):
    """entries = sorted bar indices. One position at a time when block=True."""
    rows, blocked = [], -1
    for i in entries:
        i = int(i)
        if block and i <= blocked:
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
        e = simulate_exit(pd.DataFrame(seg, columns=COLS), entry, side, stop=stop, trail=stop)
        ct = (4.47 if pd.Timestamp(days[i]) < BREAK else 5.97) + SLIP
        rows.append(dict(i=i, day=pd.Timestamp(days[i]), ds=ds[i], stop=stop,
                         pnl=e.pnl_pessimistic - ct,
                         r=(e.pnl_pessimistic - ct) / stop))
        blocked = i + min(max_bars, len(seg))
    return pd.DataFrame(rows)


HOLD = 78
print(f"[setup] hold={HOLD} bars (~3 sessions), exit=BE_1R_trail, "
      f"stop=max(prior-candle range, 0.4 x daily ATR)", flush=True)
print(f"        median stop across all bars = "
      f"{np.nanmedian([max(0.4 * a, 1) for a in atr]):.0f} index points -> this is a WIDE stop",
      flush=True)
print(f"        NIFTY {c[0]:.0f} -> {c[-1]:.0f} over the sample "
      f"({100 * (c[-1] / c[0] - 1):+.0f}%)", flush=True)

# ---- N2: unconditional every-bar long, the pure beta harvest
print(f"\n[N2] unconditional LONG on a random 3,000-bar sample, same exit, one-at-a-time",
      flush=True)
samp = np.sort(RNG.choice(np.arange(30, N - 100), size=3000, replace=False))
n2 = replay(samp, +1, HOLD)
print(f"     n={len(n2)}  mean {n2.pnl.mean():+.2f} pts  expR {n2.r.mean():+.3f}  "
      f"win {(n2.pnl > 0).mean():.1%}", flush=True)
n2s = replay(samp, -1, HOLD)
print(f"     SHORT mirror: n={len(n2s)}  mean {n2s.pnl.mean():+.2f} pts  "
      f"expR {n2s.r.mean():+.3f}  win {(n2s.pnl > 0).mean():.1%}", flush=True)

rep = []
print(f"\n{'pattern':<17}{'n':>5}{'real':>9}{'expR':>7}{'N1 plc':>9}{'plc p95':>9}{'p':>7}"
      f"{'N3 short':>10}{'verdict':>20}", flush=True)
for fname, (fm, side) in F.items():
    fm = np.nan_to_num(fm.astype(float), nan=0.0) > .5
    ent = np.where(fm)[0]
    real = replay(ent, side, HOLD)
    if len(real) < 60:
        continue
    # ---- N1: random bars matched on count + time-of-day, SAME side
    want = pd.Series(hhmm[real.i.to_numpy()]).value_counts()
    pools = {hm: np.where((hhmm == hm) & (np.arange(N) > 30) & (np.arange(N) < N - 100))[0]
             for hm in want.index}
    draws = []
    for _ in range(N_DRAW):
        pick = []
        for hm, k in want.items():
            pl = pools[hm]
            if len(pl):
                pick.append(RNG.choice(pl, size=min(k, len(pl)), replace=False))
        if not pick:
            continue
        idx = np.sort(np.concatenate(pick))
        t2 = replay(idx, side, HOLD)
        if len(t2) > 30:
            draws.append(float(t2.pnl.mean()))
    dr = np.array(draws)
    # ---- N3: same pattern, opposite side
    mirror = replay(ent, -side, HOLD)
    rm = float(mirror.pnl.mean()) if len(mirror) > 30 else np.nan
    pv = float((dr >= real.pnl.mean()).mean()) if len(dr) else np.nan
    if not np.isfinite(pv):
        v = "no null"
    elif pv < 0.05:
        v = "PATTERN ADDS"
    elif pv < 0.20:
        v = "weak"
    else:
        v = "BETA, NOT PATTERN"
    rep.append(dict(pattern=fname, side=side, n=len(real),
                    real_mean=round(float(real.pnl.mean()), 2),
                    real_expR=round(float(real.r.mean()), 3),
                    n1_placebo_mean=round(float(dr.mean()), 2) if len(dr) else None,
                    n1_placebo_p95=round(float(np.quantile(dr, .95)), 2) if len(dr) else None,
                    p_value=pv, n3_short_mirror=round(rm, 2) if np.isfinite(rm) else None,
                    verdict=v))
    print(f"{fname:<17}{len(real):>5}{real.pnl.mean():>9.2f}{real.r.mean():>7.3f}"
          f"{(dr.mean() if len(dr) else 0):>9.2f}"
          f"{(np.quantile(dr, .95) if len(dr) else 0):>9.2f}{pv:>7.3f}"
          f"{(rm if np.isfinite(rm) else 0):>10.2f}{v:>20}", flush=True)

D = pd.DataFrame(rep)
D.to_csv(OUT / "beta_placebo.csv", index=False)
json.dump(dict(hold_bars=HOLD, n_draws=N_DRAW,
               n2_uncond_long_mean=round(float(n2.pnl.mean()), 2),
               n2_uncond_long_expR=round(float(n2.r.mean()), 3),
               n2_uncond_short_mean=round(float(n2s.pnl.mean()), 2),
               nifty_start=float(c[0]), nifty_end=float(c[-1]),
               results=rep), open(OUT / "beta_placebo.json", "w"), indent=2, default=str)
print(f"\nwrote beta_placebo.csv/.json", flush=True)
print(f"\nUNCONDITIONAL LONG BENCHMARK: {n2.pnl.mean():+.2f} pts / {n2.r.mean():+.3f}R per trade.")
print("Any pattern whose mean does not clearly exceed that number is harvesting index drift with a\n"
      "wide trailing stop, and must be reported as beta rather than as a candlestick edge.")
