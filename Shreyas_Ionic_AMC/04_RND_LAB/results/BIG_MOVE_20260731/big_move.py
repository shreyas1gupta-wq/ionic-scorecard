"""RARE, LARGE-MAGNITUDE SETUPS — the RR curve against the random-walk null.

PRINCIPAL'S SPEC (2026-07-31): "why are we just making 5-10 points instead of 30-60 points or 100
points? find good setups even if it trades less, does not trade few months, i do not care find good
setups to trade."

THE DIAGNOSIS THIS RUN IS BUILT ON
  Every family tested this session landed at 2-5 points of gross edge. That is NOT "a small edge" —
  it is the signature of NO edge. For a driftless random walk with a stop at -S and a target at
  +R*S, the probability of touching the target first is EXACTLY  1/(1+R)  (barrier ratio, no time
  limit). At RR 1.5 that is 40.0%. I measured 40-43%. So at intraday horizons NIFTY is behaving as a
  near-perfect random walk, and the 5-6 point cost then turns "no edge" into "a loss".
  Chasing a better intraday indicator cannot fix that. Two things can:
    1. A MUCH LARGER TARGET, so the fixed cost stops mattering. At a 300-pt target, 5.5 pts of cost
       is 1.8% instead of 100%+.
    2. A CONDITION under which the hit rate decays SLOWER than 1/(1+R) as R grows. That, and only
       that, is convexity — and it is what a buyer of options or a wide-target trend trade needs.

  So this run drops the 10-100 trades/month constraint ENTIRELY (Principal has explicitly lifted it),
  moves to DAILY bars with multi-day-to-multi-week holds, conditions on EXTREMES where the
  distribution is fattest, and measures the FULL RR CURVE rather than one target.

THE CENTRAL MEASUREMENT — "excess hit rate"
  For each setup and each RR in {1, 1.5, 2, 3, 4, 5, 6, 8}:
      excess(R) = observed_hit_rate(R) - 1/(1+R)
  A random walk gives excess = 0 at every R (slightly negative once a time cap bites, since timeouts
  steal target touches). CONVEXITY means excess(R) is positive AND RISING in R. Pure drift means
  excess is positive but FLAT or FALLING. That distinction is the whole point of the exercise and
  no test I ran earlier this session could see it, because they all fixed RR at 1.5.

SETUPS — rare by design, extreme-conditioned, on DAILY bars
  S1  COMPRESSION_5  / S2 COMPRESSION_10 : n-day range in the bottom decile of its own 2y trailing
      distribution -> breakout in the direction of the break. Generalises the NARROW_OR result
      (+8.07 -> +18.50 -> +41.38 across eras, the most promising thing in the opening-pattern run).
  S3  VOL_TROUGH  : 20d realised vol in the bottom decile -> expansion, direction from the break.
  S4  DONCHIAN_20 / S5 DONCHIAN_50 : classic multi-week breakout. Never tested at daily level here.
  S6  GAP_EXTREME : |overnight gap| > 1.0 x ATR14, traded in the gap's direction.
  S7  GAP_EXTREME_FADE : the same events, faded. Mirror of S6 on identical events.
  S8  CRASH_REVERSAL : after a <= -2 ATR day, long.
  S9  STREAK_DOWN_3 : 3+ consecutive down days, long.
  S10 NEAR_52W_HIGH : within 1% of a 52w high -> long (momentum at the extreme).
  S11 WEEKLY_ENGULF_BULL / S12 WEEKLY_ENGULF_BEAR / S13 WEEKLY_HAMMER : WEEKLY candle formations as
      TRIGGERS. This is the half of the Principal's earlier ask that CANDLE_MTF left undone — it
      computed weekly formations as columns but only ever used the weekly 9/21 EMA as a filter.
  S14 WEEKLY_EMA_CROSS : weekly 9/21 EMA cross, entered on the next weekly open.
  Each setup also gets a WEEKLY-EMA-ALIGNED variant, since the Principal asked for the combination.

CONTROLS
  - Every exit through lib/pathsafe (target = resting limit, STOP RESOLVES ADVERSELY, both intra-bar
    bounds; unreliable cells flagged). Pessimistic bound quoted throughout.
  - ONE POSITION AT A TIME. The overlap defect that inflated a t-stat ~10x earlier today cannot recur.
  - RANDOM-ENTRY-DAY placebo, matched on count, for every setup that shows positive excess.
  - The 1/(1+R) null is printed beside every observed hit rate, so a "good" hit rate that is merely
    the barrier ratio cannot be mistaken for an edge.
  - Era split at 2024-10-01; 2026 held out. Costs 4.47/5.97 index pts + 0.5 slippage, charged ONCE
    per trade regardless of hold length (correct for futures).
  - Trials counted and the Bonferroni bar stated.
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
RNG = np.random.default_rng(20260731)
BREAK, HELDOUT = pd.Timestamp("2024-10-01"), pd.Timestamp("2026-01-01")
SLIP, LOT, CAP = 0.5, 65, 1_000_000.0
RRS = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]
MAX_HOLD = 25          # trading days. Long enough that a 3-6R target is reachable.
STOP_ATR = 1.0         # stop = 1.0 x daily ATR14. Wide, so noise cannot take us out.
N_PLACEBO = 300

# ---------------------------------------------------------------- daily + weekly bars
print("[load] 1-min -> daily/weekly", flush=True)
p1 = pd.read_parquet(IDX, columns=["open", "high", "low", "close"]).sort_index()
p1 = p1[(p1.index.time >= pd.Timestamp("09:15").time()) &
        (p1.index.time <= pd.Timestamp("15:30").time())]
D = p1.resample("1D").agg(o=("open", "first"), h=("high", "max"),
                          l=("low", "min"), c=("close", "last")).dropna()
tr = pd.concat([D.h - D.l, (D.h - D.c.shift()).abs(), (D.l - D.c.shift()).abs()], axis=1).max(axis=1)
D["atr"] = tr.rolling(14).mean()
D["ret"] = D.c.pct_change()
D["rv20"] = D.ret.rolling(20).std()
D["gap"] = D.o - D.c.shift()
D["rng"] = D.h - D.l
for n in (5, 10):
    D[f"rng{n}"] = D.h.rolling(n).max() - D.l.rolling(n).min()
    # bottom-decile threshold from a 2y TRAILING window, shifted so today never sets its own bar
    D[f"rng{n}_thr"] = D[f"rng{n}"].rolling(500, min_periods=200).quantile(0.10).shift(1)
D["rv20_thr"] = D.rv20.rolling(500, min_periods=200).quantile(0.10).shift(1)
D["dc20h"] = D.h.rolling(20).max().shift(1)
D["dc20l"] = D.l.rolling(20).min().shift(1)
D["dc50h"] = D.h.rolling(50).max().shift(1)
D["dc50l"] = D.l.rolling(50).min().shift(1)
D["hi52"] = D.h.rolling(250).max().shift(1)
D["lo52"] = D.l.rolling(250).min().shift(1)
D["down"] = (D.c < D.c.shift()).astype(int)
D["streak_dn"] = D.down.groupby((D.down != D.down.shift()).cumsum()).cumsum()

W = p1.resample("W-FRI").agg(o=("open", "first"), h=("high", "max"),
                             l=("low", "min"), c=("close", "last")).dropna()
W["ema9"] = W.c.ewm(span=9, adjust=False).mean()
W["ema21"] = W.c.ewm(span=21, adjust=False).mean()
W["bull"] = W.ema9 > W.ema21
wb = W.c - W.o
W["engulf_bull"] = (wb > 0) & (wb.shift(1) < 0) & (W.c > W.o.shift(1)) & (W.o < W.c.shift(1))
W["engulf_bear"] = (wb < 0) & (wb.shift(1) > 0) & (W.c < W.o.shift(1)) & (W.o > W.c.shift(1))
W["hammer"] = (((W[["o", "c"]].min(axis=1) - W.l) >= 2 * wb.abs()) &
               ((W.h - W[["o", "c"]].max(axis=1)) <= 0.35 * (W.h - W.l)))
W["cross_up"] = W.bull & ~W.bull.shift(1).fillna(False)
W["cross_dn"] = ~W.bull & W.bull.shift(1).fillna(False)
# project weekly state onto daily, using only COMPLETED weeks (shift 1 then ffill)
wsig = W[["bull", "engulf_bull", "engulf_bear", "hammer", "cross_up", "cross_dn"]].shift(1)
for c_ in wsig.columns:
    D["w_" + c_] = wsig[c_].reindex(D.index, method="ffill").fillna(False).astype(bool)
D = D.dropna(subset=["atr"])
print(f"       daily {len(D):,} bars {D.index.min().date()} .. {D.index.max().date()}; "
      f"weekly {len(W):,}", flush=True)

HLC = np.ascontiguousarray(D[["h", "l", "c"]].to_numpy(float))
COLS = ["high", "low", "close"]
dates = D.index.to_numpy()
atr = D.atr.to_numpy(float)
N = len(D)


def cost_of(i):
    return (4.47 if pd.Timestamp(dates[i]) < BREAK else 5.97) + SLIP


# ---------------------------------------------------------------- setups
def build():
    d = D
    S = {}
    S["COMPRESSION_5_break"] = (
        (d.rng5 <= d.rng5_thr) & (d.c > d.h.shift(1)), +1)
    S["COMPRESSION_5_breakdn"] = (
        (d.rng5 <= d.rng5_thr) & (d.c < d.l.shift(1)), -1)
    S["COMPRESSION_10_break"] = (
        (d.rng10 <= d.rng10_thr) & (d.c > d.h.shift(1)), +1)
    S["COMPRESSION_10_breakdn"] = (
        (d.rng10 <= d.rng10_thr) & (d.c < d.l.shift(1)), -1)
    S["VOL_TROUGH_up"] = ((d.rv20 <= d.rv20_thr) & (d.c > d.c.shift(1)), +1)
    S["VOL_TROUGH_dn"] = ((d.rv20 <= d.rv20_thr) & (d.c < d.c.shift(1)), -1)
    S["DONCHIAN_20_up"] = (d.c > d.dc20h, +1)
    S["DONCHIAN_20_dn"] = (d.c < d.dc20l, -1)
    S["DONCHIAN_50_up"] = (d.c > d.dc50h, +1)
    S["DONCHIAN_50_dn"] = (d.c < d.dc50l, -1)
    S["GAP_EXTREME_go"] = ((d.gap.abs() > 1.0 * d.atr) & (d.gap > 0), +1)
    S["GAP_EXTREME_go_dn"] = ((d.gap.abs() > 1.0 * d.atr) & (d.gap < 0), -1)
    S["GAP_EXTREME_fade_dn"] = ((d.gap.abs() > 1.0 * d.atr) & (d.gap > 0), -1)
    S["GAP_EXTREME_fade_up"] = ((d.gap.abs() > 1.0 * d.atr) & (d.gap < 0), +1)
    S["CRASH_REVERSAL"] = ((d.c - d.c.shift()) <= -2.0 * d.atr, +1)
    S["SPIKE_FADE"] = ((d.c - d.c.shift()) >= 2.0 * d.atr, -1)
    S["STREAK_DOWN_3"] = (d.streak_dn >= 3, +1)
    S["NEAR_52W_HIGH"] = (d.c >= 0.99 * d.hi52, +1)
    S["NEAR_52W_LOW"] = (d.c <= 1.01 * d.lo52, -1)
    S["WEEKLY_ENGULF_BULL"] = (d.w_engulf_bull, +1)
    S["WEEKLY_ENGULF_BEAR"] = (d.w_engulf_bear, -1)
    S["WEEKLY_HAMMER"] = (d.w_hammer, +1)
    S["WEEKLY_EMA_CROSS_UP"] = (d.w_cross_up, +1)
    S["WEEKLY_EMA_CROSS_DN"] = (d.w_cross_dn, -1)
    out = {}
    for k, (m, side) in S.items():
        m = m.fillna(False).to_numpy(bool)
        out[k] = (m, side)
        # weekly-EMA-aligned variant (the Principal's combination ask)
        al = D.w_bull.to_numpy(bool) if side > 0 else ~D.w_bull.to_numpy(bool)
        out[k + "|wkEMA"] = (m & al, side)
    return out


SET = build()
print(f"[setups] {len(SET)} (incl. weekly-EMA-aligned variants)", flush=True)


def replay(mask, side, rr):
    """One position at a time. Stop = 1 ATR, target = rr ATR. Returns trade frame."""
    rows, blocked = [], -1
    for i in np.where(mask)[0]:
        i = int(i)
        if i <= blocked or i + 3 >= N:
            continue
        a = atr[i]
        if not np.isfinite(a) or a <= 0:
            continue
        entry = HLC[i, 2]
        stop = STOP_ATR * a
        seg = HLC[i + 1:i + 1 + MAX_HOLD]
        if len(seg) < 3:
            continue
        e = simulate_exit(pd.DataFrame(seg, columns=COLS), entry, side,
                          stop=stop, target=rr * stop)
        ct = cost_of(i)
        rows.append(dict(i=i, date=pd.Timestamp(dates[i]), stop=stop,
                         pnl=e.pnl_pessimistic - ct, pnl_o=e.pnl_optimistic - ct,
                         why=e.reason_pessimistic, r=(e.pnl_pessimistic - ct) / stop,
                         hit=int(e.reason_pessimistic == "target")))
        blocked = i + min(MAX_HOLD, len(seg))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- the RR curve
print(f"\n{'setup':<30}{'RR':>5}{'n':>5}{'/yr':>6}{'hit%':>7}{'null%':>7}{'excess':>8}"
      f"{'mean':>9}{'expR':>7}{'t':>7}{'pre':>8}{'post':>8}{'ho26':>8}", flush=True)
rep = []
for name, (mask, side) in SET.items():
    if mask.sum() < 25:
        continue
    for rr in RRS:
        tr_ = replay(mask, side, rr)
        if len(tr_) < 25:
            continue
        null = 1.0 / (1.0 + rr)
        hit = float(tr_.hit.mean())
        yrs = max((tr_.date.max() - tr_.date.min()).days / 365.25, .3)
        t = (float(tr_.pnl.mean() / tr_.pnl.std() * np.sqrt(len(tr_)))
             if tr_.pnl.std() > 0 else np.nan)
        s = summarize([ExitResult(float(a), float(b), "", "", 0, 1)
                       for a, b in zip(tr_.pnl, tr_.pnl_o)], verbose=False)
        pre = tr_[tr_.date < BREAK]
        post = tr_[(tr_.date >= BREAK) & (tr_.date < HELDOUT)]
        ho = tr_[tr_.date >= HELDOUT]
        row = dict(setup=name, RR=rr, n=len(tr_), per_year=round(len(tr_) / yrs, 1),
                   hit=round(hit, 4), null=round(null, 4), excess=round(hit - null, 4),
                   mean_pts=round(float(tr_.pnl.mean()), 1),
                   med_pts=round(float(tr_.pnl.median()), 1),
                   exp_R=round(float(tr_.r.mean()), 3),
                   stop_pts=round(float(tr_.stop.mean()), 0),
                   t=round(float(t), 2) if np.isfinite(t) else None,
                   pre=round(float(pre.pnl.mean()), 1) if len(pre) > 8 else None,
                   post=round(float(post.pnl.mean()), 1) if len(post) > 8 else None,
                   ho26=round(float(ho.pnl.mean()), 1) if len(ho) > 4 else None,
                   ho_n=len(ho), reliable=bool(s.reliable))
        rep.append(row)
        if rr in (1.5, 3.0, 5.0, 8.0):
            print(f"{name[:30]:<30}{rr:>5.1f}{len(tr_):>5}{len(tr_) / yrs:>6.1f}{hit:>7.1%}"
                  f"{null:>7.1%}{hit - null:>+8.1%}{tr_.pnl.mean():>9.1f}{tr_.r.mean():>7.3f}"
                  f"{(t if np.isfinite(t) else 0):>7.2f}{str(row['pre']):>8}"
                  f"{str(row['post']):>8}{str(row['ho26']):>8}"
                  f"{'' if s.reliable else ' *AMB*'}", flush=True)

R = pd.DataFrame(rep)
R.to_csv(OUT / "rr_curves.csv", index=False)
M = len(R)
BAR = round(float(np.sqrt(2 * np.log(max(M, 2)))) + 1.2, 2)
print(f"\n[cells] {M} (setup x RR) -> rr_curves.csv   Bonferroni-ish bar t ~ {BAR}", flush=True)

# ---------------------------------------------------------------- who has CONVEXITY?
print("\n" + "=" * 118, flush=True)
print("CONVEXITY TEST — is excess hit rate POSITIVE and RISING in RR?", flush=True)
print("  rising excess = genuine convexity (the thing an option buyer or wide-target trend needs)")
print("  flat/falling positive excess = pure drift, works but does not scale with target")
print("=" * 118, flush=True)
conv = []
for name, g in R.groupby("setup"):
    g = g.sort_values("RR")
    if len(g) < 5:
        continue
    slope = np.polyfit(g.RR, g.excess, 1)[0]
    best = g.loc[g.exp_R.idxmax()]
    conv.append(dict(setup=name, n_at_RR3=int(g[g.RR == 3].n.iloc[0]) if (g.RR == 3).any() else None,
                     mean_excess=round(float(g.excess.mean()), 4),
                     excess_slope=round(float(slope), 5),
                     best_RR=float(best.RR), best_expR=float(best.exp_R),
                     best_mean=float(best.mean_pts), best_t=best.t,
                     best_per_year=float(best.per_year), best_ho26=best.ho26))
C = pd.DataFrame(conv).sort_values("best_expR", ascending=False)
C.to_csv(OUT / "convexity.csv", index=False)
print(f"{'setup':<30}{'mean exc':>10}{'exc slope':>11}{'bestRR':>8}{'expR':>8}{'mean':>9}"
      f"{'t':>7}{'/yr':>6}{'ho26':>8}", flush=True)
for _, r in C.head(22).iterrows():
    print(f"{r.setup[:30]:<30}{r.mean_excess:>+10.2%}{r.excess_slope:>+11.4f}{r.best_RR:>8.1f}"
          f"{r.best_expR:>8.3f}{r.best_mean:>9.1f}{(r.best_t if r.best_t else 0):>7.2f}"
          f"{r.best_per_year:>6.1f}{str(r.best_ho26):>8}", flush=True)

# ---------------------------------------------------------------- placebo on the winners
print("\n" + "=" * 118, flush=True)
print("RANDOM-ENTRY-DAY PLACEBO on setups with positive expectancy at their best RR", flush=True)
print("=" * 118, flush=True)
cand = C[(C.best_expR > 0.05)]
print(f"{len(cand)} setups qualify (best exp_R > 0.05)", flush=True)
plc = []
pool = np.arange(30, N - MAX_HOLD - 2)
for _, r in cand.iterrows():
    name = r.setup
    mask, side = SET[name]
    rr = r.best_RR
    real = replay(mask, side, rr)
    if len(real) < 25:
        continue
    draws = []
    for _ in range(N_PLACEBO):
        idx = np.sort(RNG.choice(pool, size=min(len(real), len(pool)), replace=False))
        m2 = np.zeros(N, bool); m2[idx] = True
        t2 = replay(m2, side, rr)
        if len(t2) > 10:
            draws.append(float(t2.r.mean()))
    if len(draws) < 30:
        continue
    dr = np.array(draws)
    pv = float((dr >= real.r.mean()).mean())
    v = "SETUP REAL" if pv < 0.05 else ("weak" if pv < 0.20 else "NO EDGE vs random day")
    plc.append(dict(setup=name, RR=rr, n=len(real), real_expR=round(float(real.r.mean()), 3),
                    placebo_expR=round(float(dr.mean()), 3),
                    placebo_p95=round(float(np.quantile(dr, .95)), 3), p_value=pv, verdict=v))
    print(f"  {name[:32]:<32} RR{rr:>4.1f}  real expR {real.r.mean():>+7.3f}  "
          f"placebo {dr.mean():>+7.3f} (p95 {np.quantile(dr, .95):>+6.3f})  p={pv:.3f}  {v}",
          flush=True)

pd.DataFrame(plc).to_csv(OUT / "placebo.csv", index=False)
json.dump(dict(n_cells=M, bar=BAR, stop_atr=STOP_ATR, max_hold_days=MAX_HOLD, rrs=RRS,
               n_setups=len(SET), n_placebo=N_PLACEBO,
               note="daily bars, one position at a time, 1/(1+R) random-walk null"),
          open(OUT / "meta.json", "w"), indent=2)
print("\nwrote rr_curves.csv, convexity.csv, placebo.csv, meta.json", flush=True)
print("\nHOW TO READ THIS: the null column is what a COIN FLIP delivers at that RR. A hit rate of\n"
      "25% at RR 3 is not skill - it is exactly the barrier ratio. Only positive EXCESS is signal,\n"
      "and only RISING excess is convexity.", flush=True)
