"""TWO TESTS: (A) BUY the CHEAP option (negative overshoot), (B) EVENT-DATE EXCLUSION.

(A) THE UNTESTED MIRROR. I tested buying the INFLATED option (-2.63 pts, loses: you pay the overshoot
    and it deflates). The mirror is untested and mechanically FAVOURABLE for a buyer:
    an option that moved LESS than delta predicted is CHEAP (overshoot < 0), and spot then CONTINUES
    (+5.2 pts at 60min, t=2.78 for the -14..-3 bucket). A buyer of a cheap option gets THREE tailwinds:
      cheap entry  +  directional continuation  +  IV normalising back UP
    This is the Principal's option-buying mandate expressed on the side of the data that favours it.
    Capital = premium x qty (his ruling), lot = 65 -> tiny capital per lot = the leverage that makes
    100%+ CAGR arithmetically reachable IF any edge exists.

(B) EVENT AVOIDANCE (Principal): elections/budgets/RBI are KNOWN IN ADVANCE, so excluding them requires
    a calendar, not a forecast -> legitimate, not curve-fitting. The -515pt election-day trade is
    exactly what this removes. Tested as an exclusion on every variant.
"""
from __future__ import annotations
import warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
OUT = Path(__file__).parent
LOT = 65
COST_OPT = 1.45      # premium pts round trip (Rs25/side + slippage)

# Known scheduled high-event dates in the sample (announced well in advance)
EVENTS = {
    "2024-06-04": "General election result",
    "2024-06-03": "election eve",
    "2024-02-01": "Union Budget", "2023-02-01": "Union Budget",
    "2022-02-01": "Union Budget", "2025-02-01": "Union Budget", "2026-02-01": "Union Budget",
    "2024-07-23": "Budget (full-year)",
    "2021-11-26": "Omicron shock",   # not scheduled - kept separate below
}
SCHEDULED = {d for d, v in EVENTS.items() if "Omicron" not in v}

r = pd.read_csv(OUT / "overshoot_measured.csv")
r["t0"] = pd.to_datetime(r["t0"]); r["day"] = r["t0"].dt.date.astype(str)
r["dirn"] = np.where(r["typ"] == "CE", 1, -1)
r = r.dropna(subset=["px_60", "S_60"])
for mm in (15, 30, 60):
    r[f"buy_{mm}"] = (r[f"px_{mm}"] - r["px_now"]) - COST_OPT     # BUYER pnl
    r[f"fwd_{mm}"] = r["dirn"] * (r[f"S_{mm}"] - r["S0"])

print("=" * 122)
print("(A) BUY THE OPTION — by how ABNORMAL it was.  buy_pnl = px_exit - px_entry - cost")
print("=" * 122)
print(f"{'bucket':<30}{'n':>6}{'buy15':>9}{'buy30':>9}{'buy60':>9}{'win60':>8}{'prem':>8}"
      f"{'ROI60%':>9}{'worst':>9}")
print("-" * 122)
B = [("MUCH too cheap (<=-14)", -1e9, -14), ("too cheap (-14..-3)", -14, -3),
     ("near fair (-3..+3)", -3, 3), ("too rich (+3..+14)", 3, 14),
     ("MUCH too rich (>=+14)", 14, 1e9)]
rows = []
for lbl, lo, hi in B:
    d = r[(r.overshoot > lo) & (r.overshoot <= hi)]
    if len(d) < 40: continue
    roi = 100 * d.buy_60.mean() / max(d.px_now.mean(), 1e-9)
    print(f"{lbl:<30}{len(d):>6}{d.buy_15.mean():>9.2f}{d.buy_30.mean():>9.2f}{d.buy_60.mean():>9.2f}"
          f"{100*(d.buy_60>0).mean():>7.1f}%{d.px_now.mean():>8.1f}{roi:>8.2f}%{d.buy_60.min():>9.1f}")
    rows.append(dict(bucket=lbl, n=len(d), buy60=round(d.buy_60.mean(), 2),
                     win=round(100*(d.buy_60 > 0).mean(), 1), roi=round(roi, 2)))

best = r[r.overshoot <= -3]
print(f"\n  COMBINED 'cheap' (overshoot <= -3): n={len(best)}  buy60 {best.buy_60.mean():+.2f} pts  "
      f"win {100*(best.buy_60>0).mean():.1f}%  prem {best.px_now.mean():.1f}  "
      f"ROI {100*best.buy_60.mean()/max(best.px_now.mean(),1e-9):+.2f}%")
for by in ("era", "split", "dte_band"):
    if by in best:
        g = best.groupby(by).apply(lambda d: pd.Series({
            "n": len(d), "buy60": d.buy_60.mean(), "win%": 100*(d.buy_60 > 0).mean(),
            "ROI%": 100*d.buy_60.mean()/max(d.px_now.mean(), 1e-9)}))
        print(f"    by {by}:"); print(g.round(2).to_string())

print()
print("=" * 122)
print("(B) EVENT-DATE EXCLUSION — does dropping scheduled events fix the tail?")
print("=" * 122)
r["is_event"] = r["day"].isin(SCHEDULED)
r["sell_unh"] = (r["px_now"] - r["px_60"]) - COST_OPT
r["sell_dn"] = (r["overshoot"] - r["exc_60"]) - COST_OPT - 1.20
for lbl, col, sub in (("SELL unhedged (>=3 rich)", "sell_unh", r[r.overshoot >= 3]),
                      ("SELL delta-neutral (>=3)", "sell_dn", r[r.overshoot >= 3]),
                      ("BUY cheap (<=-3)", "buy_60", r[r.overshoot <= -3])):
    a = sub[col]; b = sub[~sub.is_event][col]
    print(f"  {lbl:<26} ALL: n={len(a):>5} mean {a.mean():>7.2f} worst {a.min():>8.1f} | "
          f"EX-EVENTS: n={len(b):>5} mean {b.mean():>7.2f} worst {b.min():>8.1f}  "
          f"[{len(a)-len(b)} trades dropped]")
    dd_a = sub.assign(p=a).groupby("day")["p"].sum()
    dd_b = sub[~sub.is_event].assign(p=b).groupby("day")["p"].sum()
    print(f"    worst DAY: all {dd_a.min():>8.1f} pts  ->  ex-events {dd_b.min():>8.1f} pts")

print()
print("=" * 122)
print("(C) ECONOMICS OF THE BUY-CHEAP CELL at premium-as-margin (Principal ruling, lot=65)")
print("=" * 122)
c = r[(r.overshoot <= -3) & (~r.is_event)]
if len(c) > 50:
    mo = len(pd.to_datetime(c.day).dt.to_period("M").unique())
    per_mo = len(c)/max(mo, 1)
    prem = c.px_now.mean(); cap_lot = prem*LOT
    lots = int(1_000_000/max(cap_lot, 1))
    edge = c.buy_60.mean()
    rs_mo = per_mo*edge*LOT*lots
    print(f"  n={len(c)}  {per_mo:.1f} trades/mo  edge {edge:+.2f} pts  premium {prem:.1f} pts "
          f"= Rs{cap_lot:,.0f}/lot")
    print(f"  Rs10L / Rs{cap_lot:,.0f} = {lots} lots MAX (ignoring concurrency + prudence)")
    print(f"  Rs/month {rs_mo:,.0f} = {100*rs_mo/1_000_000:.2f}%/mo -> "
          f"{100*((1+rs_mo/1_000_000)**12-1):,.0f}% CAGR at FULL deployment")
    for frac in (0.10, 0.20, 0.30):
        m = rs_mo*frac
        print(f"    at {int(frac*100)}% deployment: {100*m/1_000_000:.2f}%/mo -> "
              f"{100*((1+m/1_000_000)**12-1):,.0f}% CAGR")
    worst_day = c.assign(p=c.buy_60).groupby("day")["p"].sum().min()
    print(f"  worst day {worst_day:.1f} pts; at 20% deployment ({int(lots*0.2)} lots) = "
          f"Rs{worst_day*LOT*int(lots*0.2):,.0f} ({100*worst_day*LOT*int(lots*0.2)/1_000_000:.1f}% of Rs10L)")
    print(f"  NOTE a BUYER's max loss per trade is the premium ({prem:.0f} pts) -> tail is BOUNDED,")
    print(f"  unlike the seller's unbounded tail. That is the structural advantage of buying.")
pd.DataFrame(rows).to_csv(OUT / "buy_cheap.csv", index=False)
print("\nwrote buy_cheap.csv")
