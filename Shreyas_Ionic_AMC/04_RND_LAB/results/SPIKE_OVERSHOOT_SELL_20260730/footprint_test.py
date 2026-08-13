"""INSTITUTIONAL-FOOTPRINT TEST (Principal's idea, 2026-07-30 16:06).

His words: *"check pattern in which option price is moving abnormally to the underlying spot — moving
too much or too little — showcasing institutional footprints, and we can buy in that direction with
smart SL."*

KEY REALISATION: the overshoot already measured IS that abnormality.
    overshoot = px_now - fair(iv_pre, S_post, T_post)
             = "how much more did the option move than DELTA and TIME alone can explain"
A large POSITIVE overshoot = someone paid up aggressively (option moved TOO MUCH).
A large NEGATIVE overshoot = the option moved TOO LITTLE / was sold into (51.4% of events, mean -3.99).

So there are two OPPOSED readings of the same number, and the data decides between them:
  * MISPRICING reading -> the excess is panic/liquidity, it reverts, so SELL the rich option.
  * FOOTPRINT reading (Principal's) -> the excess is INFORMED FLOW, so FOLLOW it (buy in that direction).
The discriminator is what SPOT does next, NOT what the option does:
  fwd_spot_move = dirn * (S_t - S0)   (dirn = +1 if the spike was up / CE inflated)
  fwd_spot_move > 0  => spot CONTINUED  => footprint reading wins, follow the flow
  fwd_spot_move < 0  => spot REVERTED   => mispricing reading wins, fade it
Tested separately for "moved too much" (overshoot > 0) and "moved too little" (overshoot < 0), because
the Principal explicitly named both, and by symmetry an option that moves TOO LITTLE on a spike may
signal informed SELLING into the move.

No new data is needed — `overshoot_measured.csv` already carries S0, S_15/30/60 and overshoot.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
OUT = Path(__file__).parent
r = pd.read_csv(OUT / "overshoot_measured.csv")
r["t0"] = pd.to_datetime(r["t0"])
r["dirn"] = np.where(r["typ"] == "CE", 1, -1)
have = [c for c in ("S_15", "S_30", "S_60") if c in r.columns]
if not have:
    raise SystemExit("need S_15/S_30/S_60 — rerun measure_overshoot.py (px/S storage patch)")
for mm in (15, 30, 60):
    if f"S_{mm}" in r:
        r[f"fwd_{mm}"] = r["dirn"] * (r[f"S_{mm}"] - r["S0"])     # >0 = spot CONTINUED the spike


def nw_t(x, lags=5):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 20: return np.nan
    m = x.mean(); d = x - m; n = len(x); v = (d @ d) / n
    for L in range(1, lags + 1):
        v += 2 * (1 - L / (lags + 1)) * ((d[L:] @ d[:-L]) / n)
    return m / np.sqrt(v / n) if v > 0 else np.nan


print("=" * 118)
print("DOES SPOT CONTINUE OR REVERT AFTER AN ABNORMAL OPTION MOVE?")
print("  fwd > 0  => spot CONTINUED  => FOOTPRINT reading (follow the flow, BUY the direction)")
print("  fwd < 0  => spot REVERTED   => MISPRICING reading (fade it, SELL the rich option)")
print("=" * 118)
BUCKETS = [
    ("moved MUCH too little  (<= -14)", lambda x: x.overshoot <= -14),
    ("moved too little  (-14..-3)", lambda x: x.overshoot.between(-14, -3)),
    ("near fair  (-3..+3)", lambda x: x.overshoot.between(-3, 3)),
    ("moved too much  (+3..+14)", lambda x: x.overshoot.between(3, 14)),
    ("moved MUCH too much  (>= +14)", lambda x: x.overshoot >= 14),
]
print(f"{'abnormality bucket':<34}{'n':>6}{'fwd15':>9}{'fwd30':>9}{'fwd60':>9}{'t(fwd60)':>10}"
      f"{'cont%60':>9}   read")
print("-" * 118)
rows = []
for lbl, f in BUCKETS:
    d = r[f(r)].dropna(subset=["fwd_60"])
    if len(d) < 30:
        continue
    t60 = nw_t(d["fwd_60"].values)
    cont = 100 * (d["fwd_60"] > 0).mean()
    read = ("CONTINUES -> follow" if (d.fwd_60.mean() > 0 and abs(t60) > 1.5)
            else "REVERTS -> fade" if (d.fwd_60.mean() < 0 and abs(t60) > 1.5)
            else "no signal")
    print(f"{lbl:<34}{len(d):>6}{d.fwd_15.mean():>9.1f}{d.fwd_30.mean():>9.1f}"
          f"{d.fwd_60.mean():>9.1f}{t60:>10.2f}{cont:>8.1f}%   {read}")
    rows.append(dict(bucket=lbl, n=len(d), fwd15=round(d.fwd_15.mean(), 2),
                     fwd30=round(d.fwd_30.mean(), 2), fwd60=round(d.fwd_60.mean(), 2),
                     t60=round(float(t60), 2), cont_pct=round(cont, 1), read=read))

print()
print("=" * 118)
print("SAME, SPLIT BY ERA AND HELD-OUT 2026 (the Principal's priority is 2025-2026)")
print("=" * 118)
for lbl, f in (("MUCH too much (>=+14)", lambda x: x.overshoot >= 14),
               ("MUCH too little (<=-14)", lambda x: x.overshoot <= -14)):
    d = r[f(r)].dropna(subset=["fwd_60"])
    if len(d) < 30: continue
    print(f"\n  {lbl}  (n={len(d)})")
    for by in ("era", "split", "dte_band"):
        if by in d:
            g = d.groupby(by)["fwd_60"].agg(n="size", mean="mean",
                                            cont=lambda s: 100 * (s > 0).mean()).round(2)
            print(f"    by {by}:")
            for k, row in g.iterrows():
                print(f"      {str(k):<16} n={int(row['n']):>5}  fwd60 {row['mean']:>8.1f} pts  "
                      f"continued {row['cont']:>5.1f}%")

print()
print("=" * 118)
print("IF 'FOLLOW' WINS: what would a BUYER need? (premium-as-margin per Principal, lot=65)")
print("=" * 118)
LOT = 65
big = r[r.overshoot >= 14].dropna(subset=["fwd_60"])
if len(big) > 30:
    # a buyer of the already-inflated option pays px_now and needs the option to rise further
    if "px_60" in big:
        b = big.dropna(subset=["px_60"])
        pnl = (b["px_60"] - b["px_now"]) - 1.45
        print(f"  BUY the inflated option and hold 60min: mean {pnl.mean():>7.2f} pts  "
              f"win {100*(pnl>0).mean():.1f}%  worst {pnl.min():.1f}  n={len(b)}")
        print(f"    -> premium paid avg {b.px_now.mean():.1f} pts = Rs{b.px_now.mean()*LOT:,.0f}/lot margin")
        print(f"    -> return on premium: {100*pnl.mean()/max(b.px_now.mean(),1e-9):+.2f}% per trade")
    print(f"  FADE in futures instead (delta-1, no theta): mean {-big.fwd_60.mean():>7.2f} pts")
    print(f"  FOLLOW in futures (delta-1):                 mean {big.fwd_60.mean():>7.2f} pts")

pd.DataFrame(rows).to_csv(OUT / "footprint_test.csv", index=False)
print("\nwrote footprint_test.csv")
