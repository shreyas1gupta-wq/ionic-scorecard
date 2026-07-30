"""PURE DIRECTIONAL OPTION BUYING — ATM/ITM ladder. NO hedge, NO spreads. Principal's exact spec.

*"do not do credit spread for option buying, i wanted pure buy atm or itm no hedge, why hedging.
recheck all, no intraday spreads, only directional."*

THE GAP THIS FILLS: pure directional buying was tested at 0.2-0.4 delta and at exactly 100pt ITM, but
never across the STRIKE-DEPTH LADDER — and the ATM run crashed after 2 of 19 cells. Strike depth is the
most important axis for a buyer because it sets the theta drag:
    ATM      ~100% of premium is extrinsic (all of it decays)
    100 ITM   35.8% extrinsic (measured), delta ~0.85
    200 ITM   less still, delta ~0.95 — nearly a future, with a bounded loss
Deeper ITM cuts theta but costs more premium => fewer lots => less leverage. There should be an optimum.

EXITS — only the HONEST ones. The favourable fixed trail (+3.03) is DISCREDITED as a fill-convention
artifact (conservative candle trail on identical data: -0.46), so it is excluded here:
  A) endpoint at +60 / +120 min .......... exact, no assumptions
  B) target T / stop SL ................. target is a resting LIMIT (exact fill); stop resolves ADVERSELY
  C) candle trail (low of last N 5-min bars) ... can only fire on completed-bar information
Costs Rs25/lot/side = 0.67 prem pts + 0.5/side slippage => 1.67 round trip. Capital = premium x qty
(Principal rule), lot = 65. Scheduled event days excluded. 2026 held out, reported separately.
"""
from __future__ import annotations

import gc
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
                   r"\NIFTY 500\intraday_options_strategy\buying")
import chain  # noqa: E402

OUT = Path(__file__).parent
LOT, STEP, COST = 65, 50, 1.67
SCH = {"2024-06-04", "2024-06-03", "2024-02-01", "2023-02-01", "2022-02-01",
       "2025-02-01", "2026-02-01", "2024-07-23"}
DEPTHS = [("50_OTM", -50), ("ATM", 0), ("50_ITM", 50), ("100_ITM", 100),
          ("150_ITM", 150), ("200_ITM", 200)]

ev = pd.read_csv(OUT / "overshoot_measured.csv")
ev["t0"] = pd.to_datetime(ev["t0"])
ev["day"] = ev["t0"].dt.date.astype(str)
ev["dirn"] = np.where(ev["typ"] == "CE", 1, -1)
ev["expiry_d"] = pd.to_datetime(ev["expiry"]).dt.date
ev = ev[~ev["day"].isin(SCH)]
print(f"[events] {len(ev):,}", flush=True)

rows = []
for i, (exp, grp) in enumerate(ev.groupby("expiry_d"), 1):
    try:
        df = chain.load_expiry(exp)
    except Exception:
        chain.load_expiry.cache_clear()
        gc.collect()
        continue
    df = df[df["volume"] > 0]
    for _, e in grp.iterrows():
        t0, S0, d = e["t0"], float(e["S0"]), int(e["dirn"])
        typ = "CE" if d > 0 else "PE"
        atm = round(S0 / STEP) * STEP
        for name, depth in DEPTHS:
            K = (atm - depth) if typ == "CE" else (atm + depth)
            s = df[(df["strike"] == K) & (df["option_type"] == typ)]
            if s.empty:
                continue
            s = s.set_index("t")[["high", "low", "close"]].sort_index()
            seg = s[(s.index >= t0) & (s.index <= t0 + pd.Timedelta(minutes=180))]
            if len(seg) < 20:
                continue
            entry = float(seg["close"].iloc[0])
            intr = max(0.0, (S0 - K) if typ == "CE" else (K - S0))
            if entry <= 1 or entry < intr * 0.9:
                continue
            hi = seg["high"].to_numpy()
            lo = seg["low"].to_numpy()
            cl = seg["close"].to_numpy()
            rec = {"day": e["day"], "t0": t0, "era": e["era"], "split": e["split"],
                   "dte_band": e["dte_band"], "depth": name, "entry": entry,
                   "intrinsic": round(intr, 1),
                   "ex_pct": round(100 * (entry - intr) / max(entry, 1e-9), 1)}
            n60 = min(60, len(cl) - 1)
            n120 = min(120, len(cl) - 1)
            rec["end60"] = float(cl[n60]) - entry - COST
            rec["end120"] = float(cl[n120]) - entry - COST
            for T, SLv in ((40, 25), (60, 30), (80, 40)):
                res = None
                for k in range(1, len(cl)):
                    if lo[k] - entry <= -SLv:
                        res = -float(SLv)
                        break
                    if hi[k] - entry >= T:
                        res = float(T)
                        break
                if res is None:
                    res = float(cl[-1]) - entry
                rec[f"tgt{T}_sl{SLv}"] = res - COST
            rs = seg.resample("5min", label="right", closed="right").agg(
                {"high": "max", "low": "min", "close": "last"}).dropna()
            if len(rs) > 5:
                L = rs["low"].to_numpy()
                C = rs["close"].to_numpy()
                for N in (3, 5):
                    res = None
                    for k in range(N, len(rs)):
                        tr = float(np.min(L[k - N:k]))
                        if L[k] <= tr:
                            res = tr - entry
                            break
                    if res is None:
                        res = float(C[-1]) - entry
                    rec[f"ctrail{N}"] = res - COST
            rows.append(rec)
    chain.load_expiry.cache_clear()
    gc.collect()
    if i % 60 == 0:
        print(f"  [{i}] {exp} rows {len(rows):,}", flush=True)

r = pd.DataFrame(rows)
r.to_csv(OUT / "pure_directional.csv", index=False)
print(f"\n[built] {len(r):,}\n", flush=True)
if r.empty:
    sys.exit(0)

EX = [c for c in ("end60", "end120", "tgt40_sl25", "tgt60_sl30", "tgt80_sl40",
                  "ctrail3", "ctrail5") if c in r.columns]

print("=" * 128)
print("PURE DIRECTIONAL BUYING — STRIKE DEPTH x EXIT (mean net premium pts). NO hedge, NO spread.")
print("=" * 128)
head = "depth".ljust(10) + "n".rjust(6) + "prem".rjust(7) + "ex%".rjust(6)
for c in EX:
    head += c.rjust(12)
print(head)
print("-" * len(head))
for name, _ in DEPTHS:
    d = r[r.depth == name]
    if len(d) < 200:
        continue
    line = name.ljust(10) + str(len(d)).rjust(6) + f"{d.entry.mean():.0f}".rjust(7) + \
        f"{d.ex_pct.mean():.0f}".rjust(6)
    for c in EX:
        v = d[c].dropna()
        line += (f"{v.mean():.2f}" if len(v) > 50 else "n/a").rjust(12)
    print(line)

print()
print("=" * 128)
print("BEST EXIT PER DEPTH + PRINCIPAL CRITERIA (median > +5 pts, RR >= 1.5)")
print("=" * 128)
print("depth".ljust(10) + "best exit".ljust(13) + "mean".rjust(8) + "median".rjust(9) +
      "win%".rjust(7) + "RR".rjust(7) + "ROI%".rjust(8) + "worst".rjust(9) + "   criteria")
print("-" * 128)
summ = []
for name, _ in DEPTHS:
    d = r[r.depth == name]
    if len(d) < 200:
        continue
    best, bv = None, -1e9
    for c in EX:
        v = d[c].dropna()
        if len(v) > 50 and v.mean() > bv:
            best, bv = c, v.mean()
    if best is None:
        continue
    x = d[best].dropna()
    w, l = x[x > 0], x[x <= 0]
    rr = float(w.mean() / abs(l.mean())) if len(l) and l.mean() != 0 else np.nan
    med = float(x.median())
    ok = "PASSES BOTH" if (med > 5 and rr >= 1.5) else "fails median" if rr >= 1.5 else "fails median + RR"
    print(name.ljust(10) + best.ljust(13) + f"{x.mean():.2f}".rjust(8) + f"{med:.2f}".rjust(9) +
          f"{100*(x>0).mean():.1f}%".rjust(7) + f"{rr:.2f}".rjust(7) +
          f"{100*x.mean()/max(d.entry.mean(),1e-9):.2f}%".rjust(8) +
          f"{x.min():.1f}".rjust(9) + "   " + ok)
    summ.append((name, best, float(x.mean()), med, rr, float(d.entry.mean())))

if summ:
    top = max(summ, key=lambda z: z[2])
    name, best = top[0], top[1]
    d = r[r.depth == name]
    print()
    print("=" * 128)
    print(f"BEST DEPTH OVERALL: {name} / {best} — era, held-out and economics")
    print("=" * 128)
    for by in ("era", "split", "dte_band"):
        g = d.groupby(by)[best].agg(n="size", mean="mean", med="median",
                                    win=lambda s: 100 * (s > 0).mean(), worst="min").round(2)
        print(f"  by {by}:")
        print(g.to_string())
    x = d[best].dropna()
    dd = d.assign(p=x).groupby("day")["p"].sum()
    mdd = float((dd.cumsum() - dd.cumsum().cummax()).min())
    mo = max(len(pd.to_datetime(d.day).dt.to_period("M").unique()), 1)
    per_mo = len(d) / mo
    cap_lot = d.entry.mean() * LOT
    print(f"\n  {per_mo:.1f} trades/mo | edge {x.mean():+.2f} pts | premium {d.entry.mean():.0f} pts "
          f"= Rs{cap_lot:,.0f}/lot | maxDD@1lot {mdd:.0f} pts")
    for L in (1, 2, 3, 5, 8):
        rs_mo = per_mo * x.mean() * LOT * L
        mdd_pct = 100 * mdd * LOT * L / 1_000_000
        cagr = 100 * ((1 + rs_mo / 1_000_000) ** 12 - 1) if rs_mo > -1_000_000 else float("nan")
        flag = "OK" if abs(mdd_pct) <= 25 else "BREACHES 25%"
        print(f"    {L} lot/trade: {100*rs_mo/1_000_000:>6.2f}%/mo -> CAGR {cagr:>8.1f}%  "
              f"maxDD {mdd_pct:>7.1f}%  {flag}")
    for m in (1.5, 2.0):
        print(f"  {m:.1f}x cost: mean {(x - COST*(m-1)).mean():+.2f} pts")
print("\nwrote pure_directional.csv")
