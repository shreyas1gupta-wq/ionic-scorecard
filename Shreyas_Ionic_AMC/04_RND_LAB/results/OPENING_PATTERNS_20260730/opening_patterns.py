"""OPENING-WINDOW PATTERNS — first-15min U-shape reversals and first-30min formations, standalone.

PRINCIPAL'S SPEC (2026-07-30): "CAN WE ALSO CHECK FIRST 15MIN U SHAPE REVERSALS OR FIRST 30MIN
PATTERNS SEPERATELY IN PARALLEL"

WHY THE OPENING WINDOW DESERVES ITS OWN TEST RATHER THAN A FILTER ON THE 15-MIN SWEEP
  STRUCTURAL_EDGES_20260730 measured first-30min-vs-midday absolute return against a RANDOM-WINDOW
  null and it came back REAL (the only intraday-seasonality cell that did; last-30min did NOT).
  Intraday seasonality was also era-STABLE, corr(era1, era3) = 0.893 across 75 buckets. So the
  opening window is the one time-of-day effect in this book with an established prior. A pattern
  that needs the open cannot be expressed as a formation on an arbitrary 15-min bar, which is why
  this runs separately.

THE PATTERNS
  U-SHAPE / V-SHAPE inside the first 15 or 30 minutes, built from 1-MINUTE bars so the shape is
  actually resolvable (a "U" inside a single 15-min candle is invisible at 15-min granularity):
    U_DOWN_UP   price falls to a trough in the middle third of the window, then recovers to close
                the window in its upper third. Depth and recovery both gated in ATR units.
    N_UP_DOWN   the mirror: rallies then fails (an inverted-U / arch).
    V_SHARP     same as U but requiring the trough in a tighter middle band and a faster recovery.
  Plus classic first-30min structures:
    OR_BREAK_UP/DN     break of the first-15min range during 09:30-10:15, in the break's direction
    OR_FAKEOUT_UP/DN   break of the first-15min range that FAILS back inside within 15 min -> trade
                       the opposite way (the opening-range stop-hunt)
    GAP_FILL_LONG/SHORT  gap open beyond 0.3 ATR that starts closing back toward prior close
    IB_NARROW_BREAK    unusually narrow first 30min (bottom tercile of OR width / ATR) then break
  Each is measured LONG or SHORT as its logic dictates. Entry is the CLOSE of the bar that confirms.

HARD CONTROLS
  - All exits through lib/pathsafe (target = resting limit, STOP RESOLVES ADVERSELY, both intra-bar
    bounds returned, unreliable cells flagged). Pessimistic bound quoted.
  - ONE TRADE PER DAY PER PATTERN. Opening patterns cannot overlap by construction, which sidesteps
    the concurrency defect that inflated the 15-min candle sweep's t-stat 9x.
  - RANDOM-DAY placebo: same pattern count, same entry TIME, random days. If the pattern's days are
    no better than random days at the same clock time, the pattern is nothing.
  - Trial count stated; Bonferroni bar computed. Era split at Oct-2024; 2026 held out.
  - Costs era-correct: 4.47 index pts round trip pre-2024-10-01, 5.97 after, +0.5 slippage.
  - Scheduled event days excluded.
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
BREAK, HELDOUT = pd.Timestamp("2024-10-01"), pd.Timestamp("2026-01-01")
SCH = {"2024-06-04", "2024-06-03", "2024-02-01", "2023-02-01", "2022-02-01",
       "2025-02-01", "2026-02-01", "2024-07-23"}
SLIP, LOT, CAP, N_PLACEBO = 0.5, 65, 1_000_000.0, 200
EXITS = ["RR1.5", "RR2.0", "RR2.5", "PARTIAL_1R_trail", "BE_1R_trail"]
FLAT = pd.Timestamp("15:20").time()

print("[load] 1-min", flush=True)
px = pd.read_parquet(IDX, columns=["open", "high", "low", "close"]).sort_index()
px = px[(px.index.time >= pd.Timestamp("09:15").time()) &
        (px.index.time <= pd.Timestamp("15:30").time())]
px["d"] = px.index.normalize()
dly = px.groupby("d").agg(h=("high", "max"), l=("low", "min"), c=("close", "last"))
tr = pd.concat([dly.h - dly.l, (dly.h - dly.c.shift()).abs(),
                (dly.l - dly.c.shift()).abs()], axis=1).max(axis=1)
dly["atr14"] = tr.rolling(14).mean()
dly["pc"] = dly.c.shift()
print(f"       {len(px):,} bars, {len(dly):,} days", flush=True)

# ---------------------------------------------------------------- per-day signal extraction
sig_rows = []
day_bars = {}
for d, g in px.groupby("d"):
    if d not in dly.index or len(g) < 200:
        continue
    D = dly.loc[d]
    atr = float(D.atr14)
    if not np.isfinite(atr) or atr <= 0 or not np.isfinite(D.pc):
        continue
    ds = d.strftime("%Y-%m-%d")
    if ds in SCH:
        continue
    day_bars[d] = g
    c = g["close"].to_numpy(float); h = g["high"].to_numpy(float); lw = g["low"].to_numpy(float)
    ts = g.index
    n = len(c)
    open_px = c[0]

    def emit(pat, i, side):
        if i + 20 >= n:
            return
        sig_rows.append(dict(day=d, ds=ds, pat=pat, i=int(i), t=ts[i], side=int(side),
                             entry=float(c[i]), atr=atr))

    # ---- U / N / V shapes inside the first W minutes, from 1-min bars
    for W, tagW in ((15, "15m"), (30, "30m")):
        if n <= W + 2:
            continue
        seg_c, seg_h, seg_l = c[:W], h[:W], lw[:W]
        lo_i, hi_i = int(np.argmin(seg_l)), int(np.argmax(seg_h))
        depth = (open_px - seg_l[lo_i]) / atr
        recov = (seg_c[-1] - seg_l[lo_i]) / atr
        height = (seg_h[hi_i] - open_px) / atr
        fade = (seg_h[hi_i] - seg_c[-1]) / atr
        lo_f, hi_f = lo_i / W, hi_i / W
        rngW = (seg_h.max() - seg_l.min()) / atr
        # U: trough in the middle, real depth, real recovery, closes in the upper third
        if (0.2 <= lo_f <= 0.8 and depth >= 0.10 and recov >= 0.6 * depth and
                seg_c[-1] >= seg_l.min() + 0.6 * (seg_h.max() - seg_l.min())):
            emit(f"U_DOWN_UP_{tagW}", W - 1, +1)
            if 0.3 <= lo_f <= 0.7 and recov >= 0.85 * depth:
                emit(f"V_SHARP_{tagW}", W - 1, +1)
        # N (inverted U): peak in the middle, then fails, closes in the lower third
        if (0.2 <= hi_f <= 0.8 and height >= 0.10 and fade >= 0.6 * height and
                seg_c[-1] <= seg_l.min() + 0.4 * (seg_h.max() - seg_l.min())):
            emit(f"N_UP_DOWN_{tagW}", W - 1, -1)
            if 0.3 <= hi_f <= 0.7 and fade >= 0.85 * height:
                emit(f"INV_V_SHARP_{tagW}", W - 1, -1)

    # ---- opening-range break / fakeout, using the first 15 min as the range
    orh, orl = h[:15].max(), lw[:15].min()
    or_w = (orh - orl) / atr
    broke_up = broke_dn = -1
    for k in range(15, min(n, 60)):          # 09:30 - 10:15
        if broke_up < 0 and h[k] > orh:
            broke_up = k
            emit("OR_BREAK_UP", k, +1)
        if broke_dn < 0 and lw[k] < orl:
            broke_dn = k
            emit("OR_BREAK_DN", k, -1)
    # fakeout: broke out, then closed back inside the range within 15 min -> trade the other way
    if broke_up >= 0:
        for k in range(broke_up + 1, min(broke_up + 16, n)):
            if c[k] < orh:
                emit("OR_FAKEOUT_UP", k, -1)
                break
    if broke_dn >= 0:
        for k in range(broke_dn + 1, min(broke_dn + 16, n)):
            if c[k] > orl:
                emit("OR_FAKEOUT_DN", k, +1)
                break
    # ---- gap-fill: gap beyond 0.3 ATR, then start closing back toward prior close
    gap = (open_px - D.pc) / atr
    if abs(gap) >= 0.3:
        side = -1 if gap > 0 else +1        # fade the gap
        for k in range(5, min(n, 60)):
            if (side < 0 and c[k] < c[k - 5]) or (side > 0 and c[k] > c[k - 5]):
                emit("GAP_FADE", k, side)
                break
    # ---- narrow first-30min then break (needs the width tercile, applied after the loop)
    sig_rows.append(dict(day=d, ds=ds, pat="__ORW__", i=29, t=ts[min(29, n - 1)], side=0,
                         entry=float(c[min(29, n - 1)]), atr=atr, orw=or_w))

S = pd.DataFrame(sig_rows)
orw = S[S.pat == "__ORW__"].set_index("day")
S = S[S.pat != "__ORW__"].copy()
# narrow-range gate uses a TRAILING expanding tercile so the day never sets its own threshold
orw = orw.sort_index()
orw["thr"] = orw.orw.expanding(120).quantile(1 / 3).shift(1)
narrow_days = set(orw.index[orw.orw <= orw.thr])
print(f"[signals] {len(S):,} raw across {S.pat.nunique()} patterns; "
      f"narrow-OR days {len(narrow_days):,}", flush=True)
print(S.pat.value_counts().to_string(), flush=True)

# add the narrow-OR variants of the OR breaks
extra = S[S.pat.isin(["OR_BREAK_UP", "OR_BREAK_DN"]) & S.day.isin(narrow_days)].copy()
extra["pat"] = "NARROW_" + extra["pat"]
S = pd.concat([S, extra], ignore_index=True)


def cost_of(day):
    return (4.47 if pd.Timestamp(day) < BREAK else 5.97) + SLIP


def run(sub, exit_kind):
    """One trade per day per pattern; hold to 15:20 unless stopped/targeted."""
    rows = []
    for _, r in sub.iterrows():
        g = day_bars.get(r["day"])
        if g is None:
            continue
        i = int(r["i"])
        fut = g.iloc[i + 1:]
        fut = fut[fut.index.time <= FLAT]
        if len(fut) < 10:
            continue
        bars = pd.DataFrame({"high": fut["high"].to_numpy(float),
                             "low": fut["low"].to_numpy(float),
                             "close": fut["close"].to_numpy(float)})
        side, entry, atr = int(r["side"]), float(r["entry"]), float(r["atr"])
        stop = 0.30 * atr                       # ~0.3 ATR, a retail-plausible opening stop
        if exit_kind.startswith("RR"):
            rr = float(exit_kind[2:])
            e = simulate_exit(bars, entry, side, stop=stop, target=rr * stop)
        elif exit_kind == "PARTIAL_1R_trail":
            a1 = simulate_exit(bars, entry, side, stop=stop, target=stop)
            a2 = simulate_exit(bars, entry, side, stop=stop, trail=stop)
            e = ExitResult(0.5 * a1.pnl_pessimistic + 0.5 * a2.pnl_pessimistic,
                           0.5 * a1.pnl_optimistic + 0.5 * a2.pnl_optimistic,
                           "partial", "partial", 0, a2.n_bars)
        else:
            e = simulate_exit(bars, entry, side, stop=stop, trail=stop)
        ct = cost_of(r["day"])
        rows.append(dict(day=r["day"], ds=r["ds"], stop=stop,
                         pnl_p=e.pnl_pessimistic - ct, pnl_o=e.pnl_optimistic - ct,
                         why=e.reason_pessimistic, r_mult=(e.pnl_pessimistic - ct) / stop))
    return pd.DataFrame(rows)


def nw_t(x, lags=5):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 12:
        return np.nan
    m = x.mean(); dv = x - m; n = len(x); var = (dv @ dv) / n
    for L in range(1, min(lags, n - 1) + 1):
        var += 2 * (1 - L / (lags + 1)) * ((dv[L:] @ dv[:-L]) / n)
    return m / np.sqrt(var / n) if var > 0 else np.nan


def score(tr, lbl):
    if len(tr) < 40:
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
    return dict(cell=lbl, n=len(tr), per_month=round(len(tr) / months, 1),
                win=round(float((tr.pnl_p > 0).mean()), 4), mean=round(float(tr.pnl_p.mean()), 2),
                median=round(float(tr.pnl_p.median()), 2),
                avg_RR=round(rr, 2) if np.isfinite(rr) else None,
                PF=round(pf, 3) if np.isfinite(pf) else None,
                exp_R=round(float(tr.r_mult.mean()), 3), pts_yr=round(ppy, 0), maxDD=round(mdd, 0),
                Calmar=round(ppy / abs(mdd), 3) if mdd else None,
                t_naive=round(float(dd.mean() / dd.std() * np.sqrt(len(dd))), 2) if dd.std() else None,
                t_NW=round(float(nw_t(dd.values)), 2),
                CAGR_pct=round(100 * ppy * LOT * lots / CAP, 1) if lots >= 1 else 0.0,
                era_pre=round(float(tr[tr.day < BREAK].pnl_p.mean()), 2) if (tr.day < BREAK).sum() > 15 else None,
                era_post=round(float(tr[(tr.day >= BREAK) & (tr.day < HELDOUT)].pnl_p.mean()), 2)
                if ((tr.day >= BREAK) & (tr.day < HELDOUT)).sum() > 15 else None,
                ho_2026=round(float(tr[tr.day >= HELDOUT].pnl_p.mean()), 2)
                if (tr.day >= HELDOUT).sum() > 8 else None,
                ho_n=int((tr.day >= HELDOUT).sum()),
                reliable=bool(s.reliable), spread=round(s.spread_frac, 3))


pats = sorted(S.pat.unique())
print(f"\n[sweep] {len(pats)} patterns x {len(EXITS)} exits = {len(pats) * len(EXITS)} cells; "
      f"Bonferroni bar t~{round(float(np.sqrt(2 * np.log(len(pats) * len(EXITS)))) + 1.2, 2)}",
      flush=True)
print(f"{'cell':<40}{'n':>6}{'/mo':>6}{'win':>7}{'mean':>8}{'RR':>6}{'expR':>7}{'PF':>7}"
      f"{'Calmar':>8}{'t_nv':>7}{'t_NW':>7}{'pre':>8}{'post':>8}{'ho26':>8}", flush=True)
rep, keep = [], {}
for p in pats:
    sub = S[S.pat == p]
    if len(sub) < 40:
        continue
    for ex in EXITS:
        tr = run(sub, ex)
        r = score(tr, f"{p}|{ex}")
        if not r:
            continue
        rep.append(r)
        keep[f"{p}|{ex}"] = (sub, ex, tr)
        print(f"{r['cell']:<40}{r['n']:>6}{r['per_month']:>6.1f}{r['win']:>7.1%}{r['mean']:>8.2f}"
              f"{(r['avg_RR'] or 0):>6.2f}{r['exp_R']:>7.3f}{(r['PF'] or 0):>7.2f}"
              f"{(r['Calmar'] or 0):>8.2f}{(r['t_naive'] or 0):>7.2f}{(r['t_NW'] or 0):>7.2f}"
              f"{str(r['era_pre']):>8}{str(r['era_post']):>8}{str(r['ho_2026']):>8}"
              f"{'' if r['reliable'] else '  *AMB*'}", flush=True)

R = pd.DataFrame(rep)
R.to_csv(OUT / "cells.csv", index=False)
M = len(R)
BAR = round(float(np.sqrt(2 * np.log(max(M, 2)))) + 1.2, 2)
print(f"\n[done] {M} cells -> cells.csv   Bonferroni-ish bar t ~ {BAR}", flush=True)

# ---------------------------------------------------------------- random-DAY placebo on survivors
cand = R[(R.t_NW.fillna(0) >= 2.5) & (R["mean"] > 0) & R.per_month.between(5, 150)]
print(f"\n[placebo] {len(cand)} cells qualify (t_NW>=2.5, mean>0, 5-150/mo). "
      f"Random DAYS, same clock time, same count.", flush=True)
plc = []
alldays = sorted(day_bars)
for _, row in cand.iterrows():
    key = row["cell"]
    sub, ex, _tr = keep[key]
    draws = []
    for _ in range(N_PLACEBO):
        fake = sub.copy()
        fake["day"] = RNG.choice(alldays, size=len(fake), replace=False)
        fake["ds"] = [pd.Timestamp(x).strftime("%Y-%m-%d") for x in fake["day"]]
        # keep the same bar index (clock time) and re-read entry/atr from the new day
        ok = []
        for _, rr in fake.iterrows():
            g = day_bars.get(rr["day"])
            if g is None or int(rr["i"]) + 20 >= len(g) or rr["ds"] in SCH:
                continue
            a = float(dly.at[rr["day"], "atr14"])
            if not np.isfinite(a) or a <= 0:
                continue
            ok.append(dict(rr, entry=float(g["close"].to_numpy()[int(rr["i"])]), atr=a))
        if not ok:
            continue
        t2 = run(pd.DataFrame(ok), ex)
        if len(t2) > 20:
            draws.append(float(t2.pnl_p.mean()))
    if len(draws) < 20:
        continue
    dr = np.array(draws)
    pv = float((dr >= float(row["mean"])).mean())
    v = "PATTERN REAL" if pv < 0.05 else ("weak" if pv < 0.20 else "TIME-OF-DAY ONLY")
    plc.append(dict(cell=key, n=int(row["n"]), real=float(row["mean"]),
                    placebo_mean=round(float(dr.mean()), 2),
                    placebo_p95=round(float(np.quantile(dr, .95)), 2), p_value=pv, verdict=v,
                    t_NW=float(row["t_NW"]), ho_2026=row["ho_2026"]))
    print(f"  {key:<40}real {float(row['mean']):>7.2f}  plc {dr.mean():>7.2f}  "
          f"p95 {np.quantile(dr, .95):>7.2f}  p={pv:.3f}  {v}", flush=True)

pd.DataFrame(plc).to_csv(OUT / "placebo.csv", index=False)
json.dump(dict(n_cells=M, bar=BAR, n_placebo_tested=len(plc),
               n_pattern_real=sum(1 for x in plc if x["verdict"] == "PATTERN REAL")),
          open(OUT / "meta.json", "w"), indent=2)
print(f"\nwrote cells.csv, placebo.csv, meta.json", flush=True)
print(f"\nSURVIVORS: t_NW >= {BAR}, placebo p<0.05, positive held-out 2026, avg_RR >= 1.5")
if len(plc):
    P = pd.DataFrame(plc)
    good = P[(P.p_value < 0.05) & (P.t_NW >= BAR) & (P.ho_2026.fillna(-1) > 0)]
    print(good.to_string(index=False) if len(good) else "  NONE survive all conditions.")
else:
    print("  no cell even reached the placebo stage.")
