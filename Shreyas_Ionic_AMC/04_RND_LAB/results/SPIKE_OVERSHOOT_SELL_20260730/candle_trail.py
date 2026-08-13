"""CANDLE-STRUCTURE TRAIL + BAR-SIZE TEST — and the HONEST replacement for my optimistic fixed trail.

Principal: *"we have seen 10d low as a good SL in stocks, can we find something in options also for trail
like 5 or 10 candle. also on 0dte i have seen people trading on 3min instead of 5-15min in the last 3hr
of trading, so check it out as well."*

WHY THIS IS A FIX, NOT AN ADDITION — the flaw it removes:
my ITM result (+3.03 pts, trail25) derives 100% of its edge from the trailing mechanism (the fixed-time
endpoint LOSES at -1.69). That trail was simulated on 1-min bars using each bar's HIGH and LOW, and I
cannot know which came first inside a bar -- I resolved favourably, so the number is OPTIMISTIC and the
optimism sits exactly where the whole edge lives.
A CANDLE-STRUCTURE trail removes that: the stop is the LOW OF THE LAST N COMPLETED BARS, so it can only
ever trigger on information that is fully known. No intra-bar sequencing assumption is required.
It also self-scales with volatility, which is the defect that broke the fixed 60-pt stop (range/stop
ratio drifted 1.5 -> 4.9 as NIFTY tripled).

ALSO TESTED: bar size {3, 5, 15 min} and the last-3-hours 0DTE window, per the Principal's observation
that 0DTE traders shorten their timeframe into the afternoon as gamma accelerates.

CONSERVATIVE-FILL CONVENTION (deliberate): the exit price is the trailing level itself, and a bar that
both makes a new high AND breaks the trail is resolved as a STOP (adverse first). That is the opposite
of my earlier favourable resolution, so any edge surviving here is not a bar-resolution artifact.
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
SCH = {"2024-06-04","2024-06-03","2024-02-01","2023-02-01","2022-02-01","2025-02-01","2026-02-01","2024-07-23"}

ev = pd.read_csv(OUT / "overshoot_measured.csv")
ev["t0"] = pd.to_datetime(ev["t0"]); ev["day"] = ev["t0"].dt.date.astype(str)
ev["dirn"] = np.where(ev["typ"] == "CE", 1, -1)
ev["expiry_d"] = pd.to_datetime(ev["expiry"]).dt.date
ev = ev[~ev["day"].isin(SCH)]
ev["hhmm"] = ev["t0"].dt.strftime("%H:%M")
ev["late"] = ev["t0"].dt.hour >= 12          # last ~3.5 hrs of the session
print(f"[events] {len(ev):,}  late-session {int(ev.late.sum()):,}", flush=True)

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
        s = s.set_index("t")[["open","high","low","close"]].sort_index()
        seg1 = s[(s.index >= t0) & (s.index <= t0 + pd.Timedelta(minutes=180))]
        if len(seg1) < 20: continue
        entry = float(seg1["close"].iloc[0])
        intr = max(0.0, (S0 - K) if typ == "CE" else (K - S0))
        if entry < intr * 0.9 or entry <= 1: continue
        rec = dict(day=e["day"], t0=t0, era=e["era"], split=e["split"], dte_band=e["dte_band"],
                   late=bool(e["late"]), entry=entry, ex_pct=round(100*(entry-intr)/max(entry,1e-9),1))
        for BAR in (3, 5, 15):
            rs = seg1.resample(f"{BAR}min", label="right", closed="right").agg(
                {"open":"first","high":"max","low":"min","close":"last"}).dropna()
            if len(rs) < 4:
                continue
            lows = rs["low"].to_numpy(); highs = rs["high"].to_numpy(); closes = rs["close"].to_numpy()
            for N in (2, 3, 5):
                if len(rs) <= N: continue
                res = None
                for k in range(N, len(rs)):
                    trail = float(np.min(lows[k-N:k]))       # low of the last N COMPLETED bars
                    # CONSERVATIVE: if this bar breaks the trail, we are stopped at the trail level,
                    # regardless of whether it also made a new high.
                    if lows[k] <= trail:
                        res = trail - entry; break
                if res is None:
                    res = float(closes[-1]) - entry
                rec[f"b{BAR}_n{N}"] = res - COST
        rows.append(rec)
    chain.load_expiry.cache_clear(); gc.collect()
    if i % 60 == 0: print(f"  [{i}] {exp} rows {len(rows):,}", flush=True)

r = pd.DataFrame(rows)
r.to_csv(OUT / "candle_trail.csv", index=False)
print(f"\n[built] {len(r):,}\n", flush=True)
if r.empty: sys.exit(0)

cols = [c for c in r.columns if c.startswith("b")]
print("=" * 118)
print("CANDLE-STRUCTURE TRAIL (stop = low of last N completed bars). CONSERVATIVE fill convention.")
print("  compare against my optimistic fixed trail25 = +3.03 pts and the losing endpoint = -1.69 pts")
print("=" * 118)
print(f"{'rule':<12}{'n':>6}{'mean':>9}{'median':>9}{'win%':>8}{'worst':>9}{'PF':>7}{'RR':>7}{'ROI%':>8}")
print("-" * 118)
out = []
for c in sorted(cols):
    x = r[c].dropna()
    if len(x) < 200: continue
    w, l = x[x > 0], x[x <= 0]
    pf = float(w.sum()/abs(l.sum())) if l.sum() else np.nan
    rr = w.mean()/abs(l.mean()) if len(l) else np.nan
    print(f"{c:<12}{len(x):>6}{x.mean():>9.2f}{x.median():>9.2f}{100*(x>0).mean():>7.1f}%"
          f"{x.min():>9.1f}{pf:>7.2f}{rr:>7.2f}{100*x.mean()/max(r.entry.mean(),1e-9):>7.2f}%")
    out.append((c, x.mean(), pf, rr, x.median()))

if out:
    best = max(out, key=lambda z: z[1])[0]
    print(f"\n--- BEST RULE: {best} ---")
    for by in ("era", "split", "dte_band", "late"):
        if by in r:
            g = r.groupby(by)[best].agg(n="size", mean="mean", med="median",
                                        win=lambda s: 100*(s>0).mean(), worst="min").round(2)
            print(f"  by {by}:"); print(g.to_string())
    print()
    print("  ** the Principal's 3-min / late-session hypothesis **")
    for BAR in (3, 5, 15):
        cc = [c for c in cols if c.startswith(f"b{BAR}_")]
        if not cc: continue
        for tag, sub in (("all", r), ("late-session (>=12:00)", r[r.late]),
                         ("late + 0-1DTE", r[r.late & (r.dte_band == "0-1DTE")])):
            vals = sub[cc].mean(numeric_only=True)
            if vals.notna().any():
                print(f"    {BAR:>2}min | {tag:<24} best {vals.max():+.2f} pts ({vals.idxmax()})  n={len(sub)}")
print("\nwrote candle_trail.csv")
