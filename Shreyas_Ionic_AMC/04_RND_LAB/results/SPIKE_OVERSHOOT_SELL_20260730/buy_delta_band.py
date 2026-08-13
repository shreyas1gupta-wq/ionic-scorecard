"""PURE DIRECTIONAL NAKED BUYING IN THE 0.4-0.8 DELTA BAND. Principal's corrected spec.

*"0.2-0.4 delta was the range to sell from — I gave that for selling naked. Recheck all correctly.
For buying try 0.4-0.8 delta ranges. Not that it means use spread — always directional naked buying,
with SL."*

MY ERROR THIS CORRECTS: every buying test today used the SELLING band (0.2-0.4 delta) or a fixed 100pt
ITM offset (which at short DTE is delta ~0.85, ABOVE the intended upper bound). So directional buying
has never been tested inside the Principal's actual 0.4-0.8 range — the band with the best
delta-to-theta trade-off for a buyer.

WHY SELECTING BY DELTA MATTERS (rather than by strike offset): delta depends on DTE and vol, so a fixed
"100 points ITM" is delta 0.75 at 5 DTE and 0.95 at 0 DTE. Selecting by MEASURED delta is the faithful
implementation. Delta is backed out from the real traded price via Black-Scholes.

STRUCTURE: naked long option, NO hedge, NO spread. Hard SL. Exits are only the honest ones —
  A) endpoint +60 / +120 min .............. exact
  B) target T / stop SL ................... target = resting LIMIT (exact); stop resolves ADVERSELY
  C) candle trail = low of last N 5-min completed bars ... no intra-bar assumption possible
The favourable fixed-distance trail is EXCLUDED: it produced +3.03 pts on identical data where the
conservative candle trail gave -0.46, i.e. it was a fill-convention artifact.
Costs Rs25/lot/side => 0.67 prem pts + 0.5/side slippage = 1.67 round trip. Capital = premium x qty,
lot = 65. Scheduled event days excluded. 2026 held out and reported separately.
"""
from __future__ import annotations

import gc
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm

warnings.filterwarnings("ignore")
sys.path.insert(0, r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
                   r"\NIFTY 500\intraday_options_strategy\buying")
import chain  # noqa: E402

OUT = Path(__file__).parent
LOT, STEP, COST, R = 65, 50, 1.67, 0.065
SCH = {"2024-06-04", "2024-06-03", "2024-02-01", "2023-02-01", "2022-02-01",
       "2025-02-01", "2026-02-01", "2024-07-23"}
BANDS = [("0.40-0.55", 0.40, 0.55), ("0.55-0.70", 0.55, 0.70), ("0.70-0.80", 0.70, 0.80)]


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
    if px < max(0.0, (S - K) if typ == "CE" else (K - S)) - 0.5:
        return np.nan
    try:
        return brentq(lambda s: bs(S, K, T, s, typ) - px, 1e-4, 5.0, maxiter=50, xtol=1e-5)
    except Exception:
        return np.nan


def delta_of(S, K, T, sig, typ):
    if T <= 0 or sig <= 0:
        return 1.0 if ((typ == "CE" and S > K) or (typ == "PE" and S < K)) else 0.0
    d1 = (np.log(S / K) + (R + 0.5 * sig * sig) * T) / (sig * np.sqrt(T))
    return float(norm.cdf(d1)) if typ == "CE" else float(abs(norm.cdf(d1) - 1.0))


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
        chain.load_expiry.cache_clear(); gc.collect(); continue
    df = df[df["volume"] > 0]
    for _, e in grp.iterrows():
        t0, S0, d = e["t0"], float(e["S0"]), int(e["dirn"])
        typ = "CE" if d > 0 else "PE"
        T0 = max((pd.Timestamp(exp) + pd.Timedelta(hours=15, minutes=30) - t0
                  ).total_seconds() / (365.25 * 24 * 3600), 1e-6)
        atm = round(S0 / STEP) * STEP
        # candidates: ATM out to 300 pts ITM (the 0.4-0.8 band lives here)
        cands = [(atm - k * STEP) if typ == "CE" else (atm + k * STEP) for k in range(0, 7)]
        picked = {}
        for K in cands:
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
            sig = iv_of(entry, S0, K, T0, typ)
            if not np.isfinite(sig):
                continue
            dl = delta_of(S0, K, T0, sig, typ)
            for name, lo_d, hi_d in BANDS:
                if lo_d <= dl < hi_d and name not in picked:
                    picked[name] = (K, entry, intr, dl, seg)
        for name, (K, entry, intr, dl, seg) in picked.items():
            hi = seg["high"].to_numpy(); lo = seg["low"].to_numpy(); cl = seg["close"].to_numpy()
            rec = {"day": e["day"], "t0": t0, "era": e["era"], "split": e["split"],
                   "dte_band": e["dte_band"], "band": name, "strike": int(K), "delta": round(dl, 3),
                   "entry": entry, "ex_pct": round(100 * (entry - intr) / max(entry, 1e-9), 1)}
            n60 = min(60, len(cl) - 1); n120 = min(120, len(cl) - 1)
            rec["end60"] = float(cl[n60]) - entry - COST
            rec["end120"] = float(cl[n120]) - entry - COST
            for T, SLv in ((40, 25), (60, 30), (80, 40)):
                res = None
                for k in range(1, len(cl)):
                    if lo[k] - entry <= -SLv:
                        res = -float(SLv); break
                    if hi[k] - entry >= T:
                        res = float(T); break
                if res is None:
                    res = float(cl[-1]) - entry
                rec[f"tgt{T}_sl{SLv}"] = res - COST
            rs = seg.resample("5min", label="right", closed="right").agg(
                {"high": "max", "low": "min", "close": "last"}).dropna()
            if len(rs) > 5:
                L = rs["low"].to_numpy(); C = rs["close"].to_numpy()
                for N in (3, 5):
                    res = None
                    for k in range(N, len(rs)):
                        tr = float(np.min(L[k - N:k]))
                        if L[k] <= tr:
                            res = tr - entry; break
                    if res is None:
                        res = float(C[-1]) - entry
                    rec[f"ctrail{N}"] = res - COST
            rows.append(rec)
    chain.load_expiry.cache_clear(); gc.collect()
    if i % 60 == 0:
        print(f"  [{i}] {exp} rows {len(rows):,}", flush=True)

r = pd.DataFrame(rows)
r.to_csv(OUT / "buy_delta_band.csv", index=False)
print(f"\n[built] {len(r):,}\n", flush=True)
if r.empty:
    sys.exit(0)

EX = [c for c in ("end60", "end120", "tgt40_sl25", "tgt60_sl30", "tgt80_sl40",
                  "ctrail3", "ctrail5") if c in r.columns]
print("=" * 128)
print("NAKED DIRECTIONAL BUYING, 0.4-0.8 DELTA BAND (mean net premium pts). NO hedge, NO spread.")
print("=" * 128)
head = "delta band".ljust(12) + "n".rjust(6) + "delta".rjust(7) + "prem".rjust(7) + "ex%".rjust(6)
for c in EX:
    head += c.rjust(12)
print(head); print("-" * len(head))
for name, _, _ in BANDS:
    d = r[r.band == name]
    if len(d) < 150:
        continue
    line = name.ljust(12) + str(len(d)).rjust(6) + f"{d.delta.mean():.2f}".rjust(7) + \
        f"{d.entry.mean():.0f}".rjust(7) + f"{d.ex_pct.mean():.0f}".rjust(6)
    for c in EX:
        v = d[c].dropna()
        line += (f"{v.mean():.2f}" if len(v) > 50 else "n/a").rjust(12)
    print(line)

print()
print("=" * 128)
print("BEST EXIT PER BAND + PRINCIPAL CRITERIA (median > +5 pts, RR >= 1.5)")
print("=" * 128)
print("band".ljust(12) + "best exit".ljust(13) + "mean".rjust(8) + "median".rjust(9) +
      "win%".rjust(7) + "RR".rjust(7) + "ROI%".rjust(8) + "worst".rjust(9) + "   criteria")
print("-" * 128)
summ = []
for name, _, _ in BANDS:
    d = r[r.band == name]
    if len(d) < 150:
        continue
    best, bv = None, -1e9
    for c in EX:
        v = d[c].dropna()
        if len(v) > 50 and v.mean() > bv:
            best, bv = c, v.mean()
    if best is None:
        continue
    x = d[best].dropna(); w, l = x[x > 0], x[x <= 0]
    rr = float(w.mean() / abs(l.mean())) if len(l) and l.mean() != 0 else np.nan
    med = float(x.median())
    ok = "PASSES BOTH" if (med > 5 and rr >= 1.5) else ("fails median" if rr >= 1.5 else "fails median + RR")
    print(name.ljust(12) + best.ljust(13) + f"{x.mean():.2f}".rjust(8) + f"{med:.2f}".rjust(9) +
          f"{100*(x>0).mean():.1f}%".rjust(7) + f"{rr:.2f}".rjust(7) +
          f"{100*x.mean()/max(d.entry.mean(),1e-9):.2f}%".rjust(8) + f"{x.min():.1f}".rjust(9) +
          "   " + ok)
    summ.append((name, best, float(x.mean())))

if summ:
    name, best, _ = max(summ, key=lambda z: z[2])
    d = r[r.band == name]
    print()
    print("=" * 128)
    print(f"BEST BAND: {name} / {best} — era, held-out, DTE, economics")
    print("=" * 128)
    for by in ("era", "split", "dte_band"):
        g = d.groupby(by)[best].agg(n="size", mean="mean", med="median",
                                    win=lambda s: 100 * (s > 0).mean(), worst="min").round(2)
        print(f"  by {by}:"); print(g.to_string())
    x = d[best].dropna()
    dd = d.assign(p=x).groupby("day")["p"].sum()
    mdd = float((dd.cumsum() - dd.cumsum().cummax()).min())
    mo = max(len(pd.to_datetime(d.day).dt.to_period("M").unique()), 1)
    per_mo = len(d) / mo
    print(f"\n  {per_mo:.1f} trades/mo | edge {x.mean():+.2f} pts | premium {d.entry.mean():.0f} pts "
          f"= Rs{d.entry.mean()*LOT:,.0f}/lot | maxDD@1lot {mdd:.0f} pts")
    for L in (1, 2, 3, 5, 8):
        rs_mo = per_mo * x.mean() * LOT * L
        mdd_pct = 100 * mdd * LOT * L / 1_000_000
        cagr = 100 * ((1 + rs_mo / 1_000_000) ** 12 - 1) if rs_mo > -1_000_000 else float("nan")
        print(f"    {L} lot/trade: {100*rs_mo/1_000_000:>6.2f}%/mo -> CAGR {cagr:>9.1f}%  "
              f"maxDD {mdd_pct:>7.1f}%  {'OK' if abs(mdd_pct)<=25 else 'BREACHES 25%'}")
    for m in (1.5, 2.0):
        print(f"  {m:.1f}x cost: mean {(x - COST*(m-1)).mean():+.2f} pts")
print("\nwrote buy_delta_band.csv")
