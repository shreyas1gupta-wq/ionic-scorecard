"""DIRECTIONAL OPTION BUYING AT 0.6 DELTA / ITM-100 / ITM-50, HARVESTED AT RR 1:1.5.

PRINCIPAL'S SPEC (2026-07-30): "FIND HIGH CAGR STRATEGIES USING OPTION BUYING ONLY 0.6 DELTA OR
ITM 100/50 POINT STRIKE AND BEST HARVEST RISK REWARD ATLEAST 1:1.5"

WHAT IS NEW HERE VERSUS THE 21 CELLS THAT ALL LOST
  buy_delta_band.py tested the 0.4-0.8 band UNCONDITIONALLY: 21 cells, every one negative. The
  missing ingredient was never the strike or the trail - it was the CONDITION. This run buys only
  when a pre-registered, placebo-cleared condition is present, and harvests at a fixed 1:1.5.

THE CONDITIONS, AND WHY THESE THREE
  INDICATOR_MINE_20260730 ran 15 cells against a Bonferroni bar of t=3.8 (m=481 trials). Results:
    B2_vix_rv_divergence_low   +4.584 pts  t=4.029  placebo p=0.000  maxday 0.133  n=19504  <- ONLY
                                                                                    cell over the bar
    A6_vwap_proxy_continue     +4.153 pts  t=2.576  placebo p=0.000  maxday 0.087  n=9655
    C1_sweep_priorday_30min    +6.669 pts  t=2.085  placebo p=0.055  maxday 0.129  n=1232
    C2_sweep_priorday_45min    +6.892 pts  t=2.124  placebo p=0.020  maxday 0.189  n=1092
  B2 is a REGIME filter (IV cheap vs realised) with no direction of its own; A6/C1/C2 are directional
  triggers. So the design is TRIGGER x IV-STATE x STRIKE x STOP, and IV-RICH is carried as a CONTROL
  arm: if buying works just as well when IV is expensive, the B2 gate was noise and I will say so.

THE ARITHMETIC TO BEAT, STATED BEFORE THE RUN
  A +4.58 index-point edge times 0.6 delta is +2.75 option points. Round-trip cost at Rs25/lot/side
  on a 65 lot is 0.77 premium points, plus 0.5/side slippage = 1.77. That leaves +0.98 before theta,
  and theta on a 0.6-delta short-dated option over a 2-hour hold is routinely 2-6 points. On the mean
  this loses. The reason to run it anyway is that a 1:1.5 HARVEST does not depend on the mean - it
  depends on the HIT RATE clearing 40%. That is the actual hypothesis under test.

EXITS - pathsafe-enforced, so the +3.03/-0.46 and 226%/0.7% class of error cannot recur
  lib/pathsafe.simulate_exit returns BOTH intra-bar resolutions and summarize() REFUSES to collapse
  them to one number when they disagree by more than 25%. Target is a resting limit (exact fill);
  the stop resolves ADVERSELY. Quoted results are always the pessimistic bound.

COSTS/CONVENTIONS  lot 65, Rs25/lot/side => 0.385 prem pts/side, slippage 0.5 pts/side => 1.77 rt.
  Capital for a long option = premium x qty. Scheduled event days excluded (measured 4-8x tail cut).
  2026 held out and reported separately.
"""
from __future__ import annotations

import gc
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm

warnings.filterwarnings("ignore")
BASE = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, BASE + r"\intraday_options_strategy\buying")
sys.path.insert(0, BASE + r"\Shreyas_Ionic_AMC\04_RND_LAB\lib")
import chain                                    # noqa: E402
from pathsafe import simulate_exit, summarize    # noqa: E402

OUT = Path(__file__).parent
OUT.mkdir(parents=True, exist_ok=True)
LOT, R = 65, 0.065
COST = 0.385 * 2 + 0.5 * 2          # 1.77 premium points round trip, lot 65
SCH = {"2024-06-04", "2024-06-03", "2024-02-01", "2023-02-01", "2022-02-01",
       "2025-02-01", "2026-02-01", "2024-07-23"}
HELDOUT = pd.Timestamp("2026-01-01")
FWD_CAP = 150                       # max minutes held; flat by 15:20 regardless
STRIKES = ["delta0.60", "itm100", "itm50"]
STOPS = [10, 15, 20, 25]            # premium points; target = 1.5 x stop  (RR 1:1.5 exactly)


def bs(S, K, T, sig, typ):
    if T <= 0 or sig <= 0:
        return max(0.0, (S - K) if typ == "CE" else (K - S))
    d1 = (np.log(S / K) + (R + 0.5 * sig * sig) * T) / (sig * np.sqrt(T))
    d2 = d1 - sig * np.sqrt(T)
    if typ == "CE":
        return S * norm.cdf(d1) - K * np.exp(-R * T) * norm.cdf(d2)
    return K * np.exp(-R * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def iv_of(px, S, K, T, typ):
    if px <= 0.05 or T <= 0:
        return np.nan
    intr = max(0.0, (S - K) if typ == "CE" else (K - S))
    if px < intr - 0.01:
        return np.nan
    try:
        return brentq(lambda s: bs(S, K, T, s, typ) - px, 1e-4, 5.0, maxiter=80, xtol=1e-6)
    except Exception:
        return np.nan


def delta_of(S, K, T, sig, typ):
    if T <= 0 or not np.isfinite(sig) or sig <= 0:
        return 1.0 if ((typ == "CE" and S > K) or (typ == "PE" and S < K)) else 0.0
    d1 = (np.log(S / K) + (R + 0.5 * sig * sig) * T) / (sig * np.sqrt(T))
    return float(norm.cdf(d1)) if typ == "CE" else float(norm.cdf(d1) - 1.0)


# ---------------------------------------------------------------- index-side gates (PIT)
print("[gates] building index features", flush=True)
ix = chain.load_index()
ix = ix[(ix.index.time >= pd.Timestamp("09:15").time()) &
        (ix.index.time <= pd.Timestamp("15:30").time())]
ix["d"] = ix.index.normalize()
dl = ix.groupby("d").agg(h=("high", "max"), l=("low", "min"), c=("close", "last"))
dl["ph"], dl["pl"], dl["pc"] = dl.h.shift(), dl.l.shift(), dl.c.shift()
dl["ret"] = dl.c.pct_change()
dl["rv10"] = dl.ret.rolling(10).std() * np.sqrt(252)      # realised vol, the RV in IV/RV
dl["rv20"] = dl.ret.rolling(20).std() * np.sqrt(252)


def day_signals(day):
    """Per-bar PIT triggers for one session. Returns DataFrame indexed by minute."""
    g = ix[ix.d == pd.Timestamp(day)]
    if len(g) < 120:
        return None
    D = dl.loc[pd.Timestamp(day)] if pd.Timestamp(day) in dl.index else None
    if D is None or not np.isfinite(D.rv10) or not np.isfinite(D.ph):
        return None
    c = g["close"].to_numpy(float); h = g["high"].to_numpy(float); lw = g["low"].to_numpy(float)
    n = len(c)
    tp = (h + lw + c) / 3.0
    vwap = np.cumsum(tp) / np.arange(1, n + 1)
    runmax = np.maximum.accumulate(h)
    runmin = np.minimum.accumulate(lw)
    # A6 VWAP CONTINUE: above VWAP and making a fresh session high (or mirror below)
    a6 = np.where((c > vwap) & (h >= runmax - 1e-9), 1,
                  np.where((c < vwap) & (lw <= runmin + 1e-9), -1, 0))
    # C1/C2 SWEEP-RECLAIM: prior-day extreme pierced, then reclaimed within W minutes
    def sweep(W):
        out = np.zeros(n, dtype=int)
        pierced_lo = pierced_hi = -10**9
        for k in range(n):
            if lw[k] < D.pl:
                pierced_lo = k
            if h[k] > D.ph:
                pierced_hi = k
            if 0 <= k - pierced_lo <= W and c[k] > D.pl:
                out[k] = 1                     # swept the low then reclaimed -> long
            elif 0 <= k - pierced_hi <= W and c[k] < D.ph:
                out[k] = -1                    # swept the high then lost it -> short
        return out
    return pd.DataFrame({"c": c, "A6": a6, "C1": sweep(30), "C2": sweep(45)}, index=g.index), D


# ---------------------------------------------------------------- main loop
mapping, exps = chain.build_expiry_index()
print(f"[run] {len(exps)} expiries", flush=True)
trades = []
iv_hist = []          # (day, atm_iv/rv) to build the trailing IV-state tercile PIT

for ei, exp in enumerate(exps):
    try:
        df = chain.load_expiry(exp)
    except Exception as e:
        print(f"  [skip] {exp}: {e}", flush=True)
        chain.load_expiry.cache_clear(); gc.collect(); continue
    for day_s, dg in df.groupby("trading_day"):
        day = pd.Timestamp(day_s)
        dte = (pd.Timestamp(exp) - day).days
        if not (0 <= dte <= 7) or day_s in SCH:
            continue
        sig = day_signals(day)
        if sig is None:
            continue
        sg, D = sig
        # ---- ATM IV at 09:45 -> the IV/RV state for the whole session (PIT, decided once)
        t0 = day + pd.Timedelta(hours=9, minutes=45)
        snap = dg[dg.t == t0]
        if snap.empty or t0 not in sg.index:
            continue
        spot0 = float(sg.at[t0, "c"])
        T0 = max(((pd.Timestamp(exp) + pd.Timedelta(hours=15, minutes=30)) - t0)
                 .total_seconds() / (365 * 24 * 3600), 1e-6)
        katm = round(spot0 / 50) * 50
        a = snap[(snap.strike == katm) & (snap.option_type == "CE")]
        if a.empty:
            continue
        aiv = iv_of(float(a.close.iloc[0]), spot0, katm, T0, "CE")
        if not np.isfinite(aiv):
            continue
        ivrv = aiv / D.rv10 if D.rv10 > 0 else np.nan
        if not np.isfinite(ivrv):
            continue
        iv_hist.append({"day": day, "ivrv": ivrv})
        # ---- take every trigger firing between 09:45 and 13:00
        win = sg[(sg.index >= t0) & (sg.index <= day + pd.Timedelta(hours=13))]
        for trig in ("A6", "C1", "C2"):
            v = win[trig].to_numpy()
            fires = np.where(v != 0)[0]
            if len(fires) == 0:
                continue
            # one trade per trigger per day: the FIRST firing (no cherry-picking among fires)
            k = int(fires[0])
            tt = win.index[k]
            side = int(v[k])
            spot = float(win["c"].iloc[k])
            typ = "CE" if side > 0 else "PE"
            snap2 = dg[(dg.t == tt) & (dg.option_type == typ)]
            if snap2.empty:
                continue
            T = max(((pd.Timestamp(exp) + pd.Timedelta(hours=15, minutes=30)) - tt)
                    .total_seconds() / (365 * 24 * 3600), 1e-6)
            snap2 = snap2[snap2.close > 0.05]
            if snap2.empty:
                continue
            # measured delta for each listed strike, from its own traded price
            cand = []
            for _, rr in snap2.iterrows():
                K = float(rr.strike)
                iv = iv_of(float(rr.close), spot, K, T, typ)
                if not np.isfinite(iv):
                    continue
                dl_ = abs(delta_of(spot, K, T, iv, typ))
                cand.append((K, float(rr.close), iv, dl_))
            if not cand:
                continue
            cd = pd.DataFrame(cand, columns=["K", "px", "iv", "dl"])
            picks = {}
            # (a) 0.6 delta -- nearest measured delta to 0.60 inside 0.50-0.70
            b = cd[(cd.dl >= 0.50) & (cd.dl <= 0.70)]
            if not b.empty:
                picks["delta0.60"] = b.iloc[(b.dl - 0.60).abs().argmin()]
            # (b)(c) ITM by 100 / 50 index points
            for lbl, off in (("itm100", 100), ("itm50", 50)):
                Kt = (spot - off) if typ == "CE" else (spot + off)
                Kt = round(Kt / 50) * 50
                m = cd[cd.K == Kt]
                if not m.empty:
                    picks[lbl] = m.iloc[0]
            for lbl, row in picks.items():
                K, entry = float(row.K), float(row.px)
                if entry < 5.0:            # measured inert for buying, but keeps junk out
                    continue
                # the option's OWN forward 1-min path -> pathsafe resolves the stop/target
                leg = dg[(dg.strike == K) & (dg.option_type == typ) & (dg.t > tt)]
                leg = leg[leg.t <= min(day + pd.Timedelta(hours=15, minutes=20),
                                       tt + pd.Timedelta(minutes=FWD_CAP))]
                if len(leg) < 10:
                    continue
                bars = leg.set_index("t")[["high", "low", "close"]].astype(float)
                for sl in STOPS:
                    if sl >= entry * 0.95:      # cannot stop below zero premium
                        continue
                    res = simulate_exit(bars, entry, +1, stop=float(sl), target=1.5 * float(sl))
                    trades.append(dict(
                        day=day, ds=day_s, exp=str(exp), dte=dte, trig=trig, strike_rule=lbl,
                        stop=sl, side=side, typ=typ, K=K, entry=entry, iv=float(row.iv),
                        delta=float(row.dl), ivrv=ivrv, spot=spot, t=tt,
                        pnl_p=res.pnl_pessimistic - COST, pnl_o=res.pnl_optimistic - COST,
                        why=res.reason_pessimistic, amb=res.n_ambiguous_bars, nbar=res.n_bars))
    chain.load_expiry.cache_clear(); gc.collect()
    if ei % 25 == 0:
        print(f"  [{ei}/{len(exps)}] {exp}  trades so far {len(trades):,}", flush=True)

T = pd.DataFrame(trades)
T.to_parquet(OUT / "trades.parquet")
print(f"\n[done] {len(T):,} trade-rows", flush=True)
if T.empty:
    sys.exit("no trades")

# ---------------------------------------------------------------- IV-state, PIT trailing tercile
iv = pd.DataFrame(iv_hist).drop_duplicates("day").set_index("day").sort_index()
iv["lo"] = iv.ivrv.expanding(120).quantile(1 / 3).shift(1)
iv["hi"] = iv.ivrv.expanding(120).quantile(2 / 3).shift(1)
T = T.merge(iv[["lo", "hi"]], left_on="day", right_index=True, how="left")
T["ivstate"] = np.where(T.ivrv <= T.lo, "CHEAP",
                        np.where(T.ivrv >= T.hi, "RICH", "MID"))
T.loc[T.lo.isna(), "ivstate"] = "n/a"


def block(sub, lbl, out):
    if len(sub) < 40:
        return
    s = summarize([type("R", (), dict(pnl_pessimistic=float(a), pnl_optimistic=float(b),
                                     reason_pessimistic="", reason_optimistic="",
                                     n_ambiguous_bars=0, n_bars=1,
                                     is_ambiguous=(a != b)))()
                   for a, b in zip(sub.pnl_p, sub.pnl_o)], verbose=False)
    hit = float((sub.why == "target").mean())
    wins = sub[sub.pnl_p > 0].pnl_p
    loss = sub[sub.pnl_p <= 0].pnl_p
    pf = float(wins.sum() / abs(loss.sum())) if loss.sum() else np.nan
    # per-day aggregation for a defensible t and Calmar
    dd = sub.groupby("ds").pnl_p.sum()
    eq = dd.cumsum()
    mdd = float((eq - eq.cummax()).min())
    yrs = max((sub.day.max() - sub.day.min()).days / 365.25, .05)
    ppy = sub.pnl_p.sum() / yrs
    tst = float(dd.mean() / dd.std() * np.sqrt(len(dd))) if dd.std() > 0 else np.nan
    row = dict(cell=lbl, n=len(sub), hit_target=round(hit, 4),
               mean_p=round(float(sub.pnl_p.mean()), 3), med_p=round(float(sub.pnl_p.median()), 3),
               mean_o=round(float(sub.pnl_o.mean()), 3),
               spread_frac=round(s.spread_frac, 3), reliable=s.reliable,
               win_rate=round(float((sub.pnl_p > 0).mean()), 4), PF=round(pf, 3) if pf else None,
               pts_per_yr=round(ppy, 1), maxDD=round(mdd, 1),
               Calmar=round(ppy / abs(mdd), 3) if mdd else None, t_day=round(tst, 2))
    out.append(row)
    print(f"{lbl:<44}{len(sub):>6}{hit:>8.1%}{sub.pnl_p.mean():>9.2f}{sub.pnl_p.median():>8.2f}"
          f"{float((sub.pnl_p > 0).mean()):>8.1%}{(pf if pf else 0):>7.2f}{ppy:>9.1f}"
          f"{mdd:>9.1f}{(ppy / abs(mdd) if mdd else 0):>8.3f}{tst:>7.2f}"
          f"{'  OK' if s.reliable else '  *AMBIG*'}", flush=True)


IS = T[T.day < HELDOUT]
HO = T[T.day >= HELDOUT]
hdr = (f"{'cell':<44}{'n':>6}{'hit%':>8}{'mean':>9}{'med':>8}{'win%':>8}{'PF':>7}"
       f"{'pts/yr':>9}{'maxDD':>9}{'Calmar':>8}{'t':>7}")
rep = []
for tag, D_ in (("IS 2021-2025", IS), ("HELDOUT 2026", HO)):
    print("\n" + "=" * 132)
    print(f"{tag}   RR fixed at 1:1.5 (target = 1.5 x stop).  BREAKEVEN HIT RATE = 40.0%")
    print("=" * 132); print(hdr); print("-" * 132)
    for trig in ("A6", "C1", "C2"):
        for sr in STRIKES:
            for st in STOPS:
                block(D_[(D_.trig == trig) & (D_.strike_rule == sr) & (D_.stop == st)],
                      f"{tag[:2]} {trig} {sr} stop{st}", rep)
    print("-" * 132)
    print("  IV-STATE SPLIT (the B2 gate). RICH is the CONTROL: if it matches CHEAP, B2 was noise.")
    for st_ in ("CHEAP", "MID", "RICH"):
        for sr in STRIKES:
            block(D_[(D_.ivstate == st_) & (D_.strike_rule == sr) & (D_.stop == 15)],
                  f"{tag[:2]} IV={st_} {sr} stop15 (all trig)", rep)

pd.DataFrame(rep).to_csv(OUT / "cells.csv", index=False)
json.dump(dict(n_trades=int(len(T)), cost_rt=COST, lot=LOT, rr="1:1.5",
               breakeven_hit=0.40, heldout_from=str(HELDOUT.date()),
               triggers="A6 vwap-continue, C1/C2 sweep-reclaim 30/45min",
               iv_gate="B2 IV/RV trailing tercile, RICH carried as control",
               n_cells=len(rep)), open(OUT / "meta.json", "w"), indent=2)
print("\nwrote trades.parquet, cells.csv, meta.json", flush=True)
print("\nREAD hit% AGAINST 40%. At RR 1:1.5 nothing else decides whether buying pays.", flush=True)
