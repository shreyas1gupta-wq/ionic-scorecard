"""100-PT ITM OPTION BUYING WITH A TRAILING EXIT — the Principal's proposal, on real 1-min prices.

His words: *"for option buying i think 100 pt ITM makes more sense... but check basis data."*

WHY IT COULD WORK (and why every OTM/ATM buying test failed):
  deep ITM  -> delta ~0.8-0.9, so it tracks the underlying; extrinsic (the part theta eats) is a SMALL
  fraction of premium, so the theta bleed that killed ATM/OTM buying is much smaller in % terms.
  Capital = premium x qty (Principal rule) ~= Rs7-8k/lot vs Rs162,500 for a futures lot => ~20x more
  positions per rupee, with loss BOUNDED at the premium.
ESTABLISHED BASIS FOR THE TRAIL (measured on the underlying, ex-events, n=4,569):
  a 40-pt trailing exit on the spike direction returns +11.47 pts gross, +5.97 NET of futures cost.
  MFE(60m)=53.9 vs |MAE|=49.4 (ratio 1.09 - symmetric, so the trail is doing the work, not convexity).
THIS TEST: express that same trailing rule through a ~100-pt ITM option, on real 1-min option prices,
and compare head-to-head against the futures version. Direction = the spike direction (dirn).

Costs: Rs25/lot/side => 0.67 premium pts round trip, plus slippage. ITM options are wider in absolute
terms, so slippage is charged at 0.5 pt/side (vs 0.4 for ATM) = 1.67 pts total. Stated, not hidden.
MEMORY: one expiry at a time + cache_clear (two jobs segfaulted from chain.py's lru_cache).
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
LOT, STEP = 65, 50
COST = 1.67
SCH = {"2024-06-04","2024-06-03","2024-02-01","2023-02-01","2022-02-01","2025-02-01","2026-02-01","2024-07-23"}
TRAIL_PREM = {15: 0.0, 25: 0.0, 40: 0.0}   # trail in PREMIUM pts, set below per config
HOLD_MAX = 120

ev = pd.read_csv(OUT / "overshoot_measured.csv")
ev["t0"] = pd.to_datetime(ev["t0"]); ev["day"] = ev["t0"].dt.date.astype(str)
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
        atm = round(S0 / STEP) * STEP
        # ~100 pts ITM: for a CE that is a strike 100 BELOW spot; for a PE, 100 ABOVE
        K = atm - 100 if typ == "CE" else atm + 100
        s = df[(df["strike"] == K) & (df["option_type"] == typ)]
        if s.empty: continue
        s = s.set_index("t")[["open","high","low","close","volume"]].sort_index()
        seg = s[(s.index >= t0) & (s.index <= t0 + pd.Timedelta(minutes=HOLD_MAX))]
        if len(seg) < 5: continue
        entry = float(seg["close"].iloc[0])
        intrinsic = max(0.0, (S0 - K) if typ == "CE" else (K - S0))
        if entry < intrinsic * 0.9 or entry <= 1: continue
        extrinsic = entry - intrinsic
        hi = seg["high"].to_numpy(); lo = seg["low"].to_numpy(); cl = seg["close"].to_numpy()
        rec = dict(day=e["day"], t0=t0, era=e["era"], split=e["split"], dte_band=e["dte_band"],
                   strike=int(K), typ=typ, entry=entry, intrinsic=round(intrinsic,1),
                   extrinsic=round(extrinsic,1), ex_pct=round(100*extrinsic/max(entry,1e-9),1),
                   vol0=float(seg["volume"].iloc[0]))
        # trailing exit in PREMIUM points (the option's own P&L path)
        for T in (10, 15, 25):
            peak = 0.0; res = None
            for k in range(1, len(cl)):
                fav = hi[k] - entry
                adv = lo[k] - entry
                peak = max(peak, fav)
                if peak > T and (peak - fav) >= T:
                    res = peak - T; break
                if adv <= -T:
                    res = -T; break
            if res is None: res = float(cl[-1]) - entry
            rec[f"trail{T}"] = res - COST
        rec["endpoint"] = float(cl[-1]) - entry - COST
        rows.append(rec)
    chain.load_expiry.cache_clear(); gc.collect()
    if i % 50 == 0: print(f"  [{i}] {exp} rows {len(rows):,}", flush=True)

r = pd.DataFrame(rows)
r.to_csv(OUT / "itm_trail.csv", index=False)
print(f"\n[built] {len(r):,} ITM trades  | mean premium {r.entry.mean():.1f} pts "
      f"(intrinsic {r.intrinsic.mean():.1f}, extrinsic {r.extrinsic.mean():.1f} = {r.ex_pct.mean():.1f}%)\n", flush=True)
if r.empty: sys.exit(0)

print("=" * 118)
print("100-PT ITM OPTION BUYING, TRAILING EXIT (premium pts, net of 1.67 cost)")
print("=" * 118)
print(f"{'exit rule':<16}{'n':>6}{'mean':>9}{'median':>9}{'win%':>8}{'worst':>9}{'PF':>7}{'ROI%':>8}")
print("-" * 118)
for c in ("trail10","trail15","trail25","endpoint"):
    if c not in r: continue
    x = r[c].dropna(); w,l = x[x>0], x[x<=0]
    pf = float(w.sum()/abs(l.sum())) if l.sum() else np.nan
    print(f"{c:<16}{len(x):>6}{x.mean():>9.2f}{x.median():>9.2f}{100*(x>0).mean():>7.1f}%"
          f"{x.min():>9.1f}{pf:>7.2f}{100*x.mean()/max(r.entry.mean(),1e-9):>7.2f}%")

best = "trail25" if "trail25" in r else "trail15"
print(f"\n--- {best} broken down ---")
for by in ("era","split","dte_band"):
    if by in r:
        g = r.groupby(by)[best].agg(n="size", mean="mean", med="median",
                                    win=lambda s: 100*(s>0).mean(), worst="min").round(2)
        print(f"  by {by}:"); print(g.to_string())

print()
print("=" * 118)
print("ECONOMICS vs FUTURES (Principal margin: option = premium x qty; futures = 10% notional)")
print("=" * 118)
mo = max(len(pd.to_datetime(r.day).dt.to_period("M").unique()), 1)
per_mo = len(r)/mo
edge = r[best].mean()
cap_opt = r.entry.mean()*LOT
cap_fut = 0.10*25000*LOT
print(f"  {per_mo:.1f} trades/mo | ITM edge {edge:+.2f} prem pts | premium {r.entry.mean():.1f} pts = Rs{cap_opt:,.0f}/lot")
print(f"  futures equivalent edge (measured on underlying, 40pt trail): +5.97 pts, Rs{cap_fut:,.0f}/lot")
for name, cap, ed in (("ITM OPTION", cap_opt, edge), ("FUTURES", cap_fut, 5.97)):
    lots_max = max(int(1_000_000/max(cap,1)), 1)
    for f in (1.0, 0.25, 0.10):
        lots = max(int(lots_max*f), 1)
        rs_mo = per_mo*ed*LOT*lots
        cagr = 100*((1+rs_mo/1_000_000)**12-1) if rs_mo > -1_000_000 else float("nan")
        dd = r.groupby("day")[best].sum() if name=="ITM OPTION" else None
        mdd = (dd.cumsum()-dd.cumsum().cummax()).min()*LOT*lots/1_000_000*100 if dd is not None else float("nan")
        print(f"    {name:<11} {int(f*100):>3}% dep ({lots:>4} lots): {100*rs_mo/1_000_000:>7.2f}%/mo "
              f"-> CAGR {cagr:>9.1f}%   maxDD {mdd:>8.1f}%")
print("\nwrote itm_trail.csv")
