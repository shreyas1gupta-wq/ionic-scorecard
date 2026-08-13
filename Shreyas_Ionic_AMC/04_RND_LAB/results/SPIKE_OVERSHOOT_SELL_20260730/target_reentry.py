"""TARGET + RE-ENTRY ON PULLBACK — the Principal's exit architecture, honestly measurable.

His words: *"we can use 60-70 pt target and re-entry with 10-15 pt pullbacks... or consolidations."*

WHY THIS IS STRUCTURALLY BETTER TO MEASURE THAN A TRAIL (the reason it is worth testing even after
the trail results died): a TARGET is a resting LIMIT order. If a bar's HIGH exceeds the target, the
limit filled -- no assumption about intra-bar sequencing is needed on the profit side. Only the STOP
carries ambiguity, and that is resolved ADVERSELY here. So the profit side is exact and the loss side
is pessimistic: any edge that survives is not a fill-convention artifact.
This matters because the candle-trail test just showed my +3.03 ITM trail result WAS such an artifact
(conservative candle trail: -0.46 pts vs favourable fixed trail: +3.03).

ARCHITECTURE per event (100-pt ITM option, spike direction, real 1-min option prices):
  1. enter at t0
  2. exit at +T premium pts (limit; exact fill) OR at -SL (conservative: stop wins ties)
  3. after a TARGET hit, watch for a pullback of P pts from the running peak, then RE-ENTER (limit)
  4. repeat up to MAX_RE times, all inside the same session
  Grid (small, pre-specified): T in {40, 60, 70} x P in {10, 15} x SL 25, MAX_RE 2.
Cost 1.67 premium pts PER LEG -- re-entries are charged, so the architecture must earn its turnover.
"""
from __future__ import annotations
import gc, sys, warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
                   r"\NIFTY 500\intraday_options_strategy\buying")
import chain  # noqa
OUT = Path(__file__).parent
LOT, STEP, COST = 65, 50, 1.67
SL, MAX_RE = 25.0, 2
SCH = {"2024-06-04","2024-06-03","2024-02-01","2023-02-01","2022-02-01","2025-02-01","2026-02-01","2024-07-23"}

ev = pd.read_csv(OUT / "overshoot_measured.csv")
ev["t0"] = pd.to_datetime(ev["t0"]); ev["day"] = ev["t0"].dt.date.astype(str)
ev["dirn"] = np.where(ev["typ"] == "CE", 1, -1)
ev["expiry_d"] = pd.to_datetime(ev["expiry"]).dt.date
ev = ev[~ev["day"].isin(SCH)]
print(f"[events] {len(ev):,}", flush=True)

def run_leg(hi, lo, cl, start, entry, T):
    """returns (pnl_gross, exit_idx, peak_reached). Target=limit(exact). Stop conservative."""
    peak = 0.0
    for k in range(start + 1, len(cl)):
        peak = max(peak, hi[k] - entry)
        if lo[k] - entry <= -SL:            # conservative: stop resolves first
            return -SL, k, peak
        if hi[k] - entry >= T:              # limit fill, exact
            return T, k, peak
    return float(cl[-1]) - entry, len(cl) - 1, peak

rows = []
for i, (exp, grp) in enumerate(ev.groupby("expiry_d"), 1):
    try:
        df = chain.load_expiry(exp)
    except Exception:
        chain.load_expiry.cache_clear(); gc.collect(); continue
    df = df[df["volume"] > 0]
    for _, e in grp.iterrows():
        t0, S0, d = e["t0"], float(e["S0"]), int(e["dirn"])
        typ = "CE" if d > 0 else "PE"
        atm = round(S0 / STEP) * STEP
        K = atm - 100 if typ == "CE" else atm + 100
        s = df[(df["strike"] == K) & (df["option_type"] == typ)]
        if s.empty: continue
        s = s.set_index("t")[["high","low","close"]].sort_index()
        seg = s[(s.index >= t0) & (s.index <= t0 + pd.Timedelta(minutes=180))]
        if len(seg) < 20: continue
        entry0 = float(seg["close"].iloc[0])
        intr = max(0.0, (S0 - K) if typ == "CE" else (K - S0))
        if entry0 < intr * 0.9 or entry0 <= 1: continue
        hi = seg["high"].to_numpy(); lo = seg["low"].to_numpy(); cl = seg["close"].to_numpy()
        rec = dict(day=e["day"], t0=t0, era=e["era"], split=e["split"], dte_band=e["dte_band"],
                   late=bool(e["t0"].hour >= 12), entry=entry0)
        for T in (40.0, 60.0, 70.0):
            for P in (10.0, 15.0):
                tot = 0.0; legs = 0; k = 0; ent = entry0
                for _ in range(MAX_RE + 1):
                    pnl, k, peak = run_leg(hi, lo, cl, k, ent, T)
                    tot += pnl - COST; legs += 1
                    if pnl < T or k >= len(cl) - 2:
                        break
                    # after a TARGET hit, wait for a P-pt pullback from the running peak, then re-enter
                    pk = ent + peak; re_at = None
                    for j in range(k + 1, len(cl)):
                        pk = max(pk, hi[j])
                        if pk - lo[j] >= P:
                            re_at = pk - P; k = j; break
                    if re_at is None: break
                    ent = re_at
                rec[f"T{int(T)}_P{int(P)}"] = tot
                rec[f"T{int(T)}_P{int(P)}_legs"] = legs
        rows.append(rec)
    chain.load_expiry.cache_clear(); gc.collect()
    if i % 60 == 0: print(f"  [{i}] {exp} rows {len(rows):,}", flush=True)

r = pd.DataFrame(rows); r.to_csv(OUT / "target_reentry.csv", index=False)
print(f"\n[built] {len(r):,}\n", flush=True)
if r.empty: sys.exit(0)
cells = [c for c in r.columns if c.startswith("T") and not c.endswith("legs")]
print("=" * 118)
print("TARGET + RE-ENTRY (exact limit target, conservative stop, cost 1.67/leg)")
print("  benchmarks: endpoint -1.69 | conservative candle trail -0.46 | (discredited) fav. trail +3.03")
print("=" * 118)
print(f"{'rule':<12}{'n':>6}{'mean':>9}{'median':>9}{'win%':>8}{'worst':>9}{'PF':>7}{'RR':>7}{'legs':>7}")
print("-" * 118)
res = []
for c in sorted(cells):
    x = r[c].dropna()
    if len(x) < 200: continue
    w, l = x[x > 0], x[x <= 0]
    pf = float(w.sum()/abs(l.sum())) if l.sum() else np.nan
    rr = w.mean()/abs(l.mean()) if len(l) else np.nan
    lg = r[f"{c}_legs"].mean()
    print(f"{c:<12}{len(x):>6}{x.mean():>9.2f}{x.median():>9.2f}{100*(x>0).mean():>7.1f}%"
          f"{x.min():>9.1f}{pf:>7.2f}{rr:>7.2f}{lg:>7.2f}")
    res.append((c, x.mean(), x.median(), pf, rr))
if res:
    b = max(res, key=lambda z: z[1])[0]
    print(f"\n--- BEST: {b} ---")
    for by in ("era", "split", "dte_band", "late"):
        if by in r:
            g = r.groupby(by)[b].agg(n="size", mean="mean", med="median",
                                     win=lambda s: 100*(s>0).mean(), worst="min").round(2)
            print(f"  by {by}:"); print(g.to_string())
    x = r[b].dropna()
    print(f"\n  PRINCIPAL CRITERIA: median {x.median():+.2f} (needs >+5) | "
          f"RR {(x[x>0].mean()/abs(x[x<=0].mean())):.2f} (needs >=1.5)")
    for m in (1.0, 1.5, 2.0):
        print(f"  {m:.1f}x cost: mean {(x - 1.67*(m-1)*r[f'{b}_legs'].mean()).mean():+.2f} pts")
print("\nwrote target_reentry.csv")
