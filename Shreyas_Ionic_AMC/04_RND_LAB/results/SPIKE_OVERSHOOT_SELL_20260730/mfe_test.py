"""MFE/MAE EXCURSION TEST — does the price action support directional buying with a trailing stop?

Principal: *"we generally get 50-70 pt moves and then a 10-30 point sideways or consolidation followed
by another move, sometimes 150 point direct move also... trade only if risk reward >1.5 and trail
dynamically."*

WHY THIS IS THE RIGHT TEST AND WHY IT WAS MISSING:
every measurement today used a FIXED-TIME ENDPOINT (price at +15/30/60 min). If moves come as
impulse -> consolidation -> impulse, an endpoint lands mid-consolidation and UNDERSTATES what a
trailing exit would have captured. The correct measure is the excursion:
    MFE = max favourable excursion  = max over window of  dirn*(S_t - S0)
    MAE = max adverse excursion     = min over window of  dirn*(S_t - S0)
    MFE/|MAE| > ~1.3 => genuinely capturable convexity; ~1.0 => symmetric, no trailing edge.
NOTE the prior firm study found MFE/|MAE| = 1.00 (zero convexity) but that was measured on ORB/BREAKOUT
signals, NOT on this sweep/overshoot family. So this is untested here, not a re-run.

Also directly tests the Principal's magnitudes: what FRACTION of events reach 50, 70, 150 points MFE?
"""
from __future__ import annotations
import gc, warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
OUT = Path(__file__).parent
IDX = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
       r"\NIFTY 500\intraday_options_strategy\datasets\raw\hf_index_options_1m\index\NIFTY.parquet")
SCH = {"2024-06-04","2024-06-03","2024-02-01","2023-02-01","2022-02-01","2025-02-01","2026-02-01","2024-07-23"}

sp = pd.read_parquet(IDX, columns=["timestamp","high","low","close"])
sp["t"] = pd.to_datetime(sp["timestamp"]).dt.tz_localize(None)
sp = sp.drop_duplicates("t").set_index("t").sort_index()
sp = sp[(sp.index.time >= pd.Timestamp("09:15").time()) & (sp.index.time <= pd.Timestamp("15:30").time())]
gc.collect()
print(f"[spot] {len(sp):,} 1-min bars", flush=True)

ev = pd.read_csv(OUT / "overshoot_measured.csv")
ev["t0"] = pd.to_datetime(ev["t0"]); ev["day"] = ev["t0"].dt.date.astype(str)
ev["dirn"] = np.where(ev["typ"] == "CE", 1, -1)
ev = ev[~ev["day"].isin(SCH)]
print(f"[events] {len(ev):,} ex-event spikes", flush=True)

H = (30, 60, 120, 240)
hi = sp["high"].to_numpy(); lo = sp["low"].to_numpy(); idx = sp.index.to_numpy()
recs = []
for _, e in ev.iterrows():
    p = np.searchsorted(idx, np.datetime64(e["t0"]))
    if p >= len(idx) - 5: continue
    S0, d = float(e["S0"]), int(e["dirn"])
    row = dict(day=e["day"], t0=e["t0"], overshoot=e["overshoot"], era=e["era"],
               split=e["split"], dte_band=e["dte_band"], dirn=d)
    for h in H:
        q = min(p + h, len(idx) - 1)
        seg_hi, seg_lo = hi[p:q + 1], lo[p:q + 1]
        if len(seg_hi) < 3: continue
        if d > 0:
            mfe = float(np.nanmax(seg_hi) - S0); mae = float(np.nanmin(seg_lo) - S0)
        else:
            mfe = float(S0 - np.nanmin(seg_lo)); mae = float(S0 - np.nanmax(seg_hi))
        row[f"mfe{h}"] = mfe; row[f"mae{h}"] = mae
    recs.append(row)
r = pd.DataFrame(recs)
r.to_csv(OUT / "mfe_mae.csv", index=False)
print(f"[built] {len(r):,}\n", flush=True)

print("=" * 118)
print("MFE / MAE ON THE UNDERLYING  (favourable vs adverse excursion, index points)")
print("  ratio > ~1.3 => capturable convexity for a trailing exit;  ~1.0 => symmetric, no edge")
print("=" * 118)
print(f"{'horizon':<10}{'n':>6}{'MFE':>9}{'|MAE|':>9}{'ratio':>8}{'med MFE':>10}"
      f"{'>=50pt':>9}{'>=70pt':>9}{'>=150pt':>10}")
print("-" * 118)
for h in H:
    c = f"mfe{h}"
    if c not in r: continue
    d = r.dropna(subset=[c, f"mae{h}"])
    mfe, mae = d[c], d[f"mae{h}"].abs()
    print(f"{h:>4} min  {len(d):>6}{mfe.mean():>9.1f}{mae.mean():>9.1f}{mfe.mean()/max(mae.mean(),1e-9):>8.2f}"
          f"{mfe.median():>10.1f}{100*(mfe>=50).mean():>8.1f}%{100*(mfe>=70).mean():>8.1f}%"
          f"{100*(mfe>=150).mean():>9.1f}%")

print()
print("=" * 118)
print("PRINCIPAL'S RR>=1.5 TEST — if we trail, what RR is actually achievable?")
print("  achieved RR = MFE / |MAE|  per trade; also % of trades where MFE >= 1.5x |MAE|")
print("=" * 118)
for h in (60, 120):
    c, m = f"mfe{h}", f"mae{h}"
    if c not in r: continue
    d = r.dropna(subset=[c, m])
    rr = d[c] / d[m].abs().clip(lower=1.0)
    print(f"  {h} min: median RR {rr.median():.2f} | mean {rr.mean():.2f} | "
          f"share RR>=1.5 {100*(rr>=1.5).mean():.1f}% | share RR>=2 {100*(rr>=2).mean():.1f}%")

print()
print("=" * 118)
print("SIMULATED TRAILING EXIT on the UNDERLYING (does trailing beat a fixed endpoint?)")
print("  trail T pts from the running peak; entry at S0; compare to the +60min endpoint")
print("=" * 118)
# reconstruct per-trade trailing outcome from MFE/MAE approximation is unsafe -> use真 path
hiA, loA = hi, lo
for T in (15, 25, 40):
    outs = []
    for _, e in ev.iterrows():
        p = np.searchsorted(idx, np.datetime64(e["t0"]))
        if p >= len(idx) - 5: continue
        S0, d = float(e["S0"]), int(e["dirn"])
        q = min(p + 120, len(idx) - 1)
        peak = 0.0; res = None
        for k in range(p + 1, q + 1):
            fav = (hiA[k] - S0) if d > 0 else (S0 - loA[k])
            adv = (loA[k] - S0) if d > 0 else (S0 - hiA[k])
            peak = max(peak, fav)
            if peak > T and (peak - fav) >= T:
                res = peak - T; break
            if adv <= -T:
                res = -T; break
        if res is None:
            res = (sp["close"].to_numpy()[q] - S0) * d
        outs.append(res)
    o = pd.Series(outs)
    print(f"  trail {T:>2}pt: mean {o.mean():>7.2f} pts | median {o.median():>7.2f} | "
          f"win {100*(o>0).mean():>5.1f}% | worst {o.min():>7.1f} | "
          f"net after 5.5pt fut cost {o.mean()-5.5:>+6.2f}")
print("\nwrote mfe_mae.csv")
