"""THE DECISIVE FOLLOW-UP: unhedged vs delta-neutral vs delta-1 fade, plus the CRISIS-DATE TAIL TEST.

Two questions this answers:

A) THE PRINCIPAL'S MAIN COURSE. Everything measured so far is the DELTA-NEUTRAL vol capture — his
   "extra 3-10 points" bonus only. His actual trade is *"10-30 point pullback + this extra 3-10 points"*,
   i.e. UNHEDGED: sell the inflated option outright and collect BOTH the vol crush AND the directional
   retracement.  Unhedged seller P&L = px_at_t0 - px_at_exit.
   Three-way comparison decides what this trade actually IS:
     - if UNHEDGED >> DELTA-NEUTRAL  -> most of the edge is DIRECTIONAL (a mean-reversion trade wearing
       options), and it must be benchmarked against the far simpler delta-1 fade;
     - if UNHEDGED ~= DELTA-NEUTRAL  -> the edge is genuinely the VOL OVERSHOOT (harder to crowd, more
       durable, and delta-hedgeable so the tail can be controlled);
     - if UNHEDGED << DELTA-NEUTRAL  -> spot CONTINUES after these spikes and the directional leg is a
       liability, so only the hedged version is viable.
   DELTA-1 FADE benchmark = fade the spike in futures over the same window: pnl = -dir * (S_exit - S0).

B) THE TAIL, ON THE DAYS THAT MATTER. This trade is structurally short exactly when a move keeps going.
   Worst single trade already measured at -75.5 pts vs a 3.41 mean gain (22x). Named crisis dates are
   the specific test: Omicron 2021-11-26, Ukraine 2022-02-24, Budget/election 2024-06-04, plus the
   worst continuation days in the sample. **If the strategy is unsurvivable on these, nothing else
   matters.**

Cost model: Rs25/lot/side => 0.67 premium pts round trip, + ~0.4 pts/side slippage = ~1.45 pts total.
Applied per leg: the unhedged option trade pays it once; the delta-neutral version pays option cost PLUS
futures hedge cost, so it is charged more (stated explicitly, not hidden).
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
OUT = Path(__file__).parent
LOT = 75
COST_OPT = 1.45          # premium pts, round trip, one option leg
COST_HEDGE = 1.20        # index pts, round trip, futures hedge leg (delta-neutral version pays this too)
CRISIS = {"2021-11-26": "Omicron", "2022-02-24": "Ukraine invasion",
          "2024-06-04": "Election result", "2020-03-23": "COVID bottom",
          "2025-04-07": "Apr-2025 selloff"}

r = pd.read_csv(OUT / "overshoot_measured.csv")
r["t0"] = pd.to_datetime(r["t0"])
r["day"] = r["t0"].dt.date.astype(str)
need = [c for c in ("px_60", "S_60", "exc_60") if c not in r.columns]
if need:
    raise SystemExit(f"missing columns {need} — rerun measure_overshoot.py first")
r = r.dropna(subset=["px_60", "S_60", "exc_60"])
r["dirn"] = np.where(r["typ"] == "CE", 1, -1)      # CE inflated => spike was UP

# --- the three expressions, all as PREMIUM/INDEX POINTS per lot, net of cost
r["pnl_unhedged"] = (r["px_now"] - r["px_60"]) - COST_OPT                    # sell option, buy back
r["pnl_deltaneutral"] = (r["overshoot"] - r["exc_60"]) - COST_OPT - COST_HEDGE
r["pnl_delta1_fade"] = (-r["dirn"] * (r["S_60"] - r["S0"])) - COST_HEDGE     # fade spike in futures

F = r[r["overshoot"] >= 3].copy()      # the mechanism-motivated richness filter
print("=" * 116)
print(f"THREE-WAY COMPARISON on the >=3pt overshoot filter   n={len(F):,}  "
      f"({100*len(F)/len(r):.1f}% of {len(r):,} events)")
print("=" * 116)
print(f"{'expression':<24}{'mean':>9}{'median':>9}{'win%':>8}{'std':>9}{'worst':>10}{'PF':>7}"
      f"{'worst/mean':>12}")
print("-" * 116)
rows = []
for lbl, col in (("UNHEDGED (sell option)", "pnl_unhedged"),
                 ("DELTA-NEUTRAL (vol only)", "pnl_deltaneutral"),
                 ("DELTA-1 FADE (futures)", "pnl_delta1_fade")):
    x = F[col].dropna()
    w, l = x[x > 0], x[x <= 0]
    pf = float(w.sum() / abs(l.sum())) if l.sum() else np.nan
    print(f"{lbl:<24}{x.mean():>9.2f}{x.median():>9.2f}{100*(x>0).mean():>7.1f}%{x.std():>9.2f}"
          f"{x.min():>10.1f}{pf:>7.2f}{abs(x.min())/max(x.mean(),1e-9):>12.1f}x")
    rows.append(dict(expr=lbl, mean=round(x.mean(), 2), median=round(x.median(), 2),
                     win=round(100*(x > 0).mean(), 1), worst=round(x.min(), 1), PF=round(pf, 2)))

print()
print("VERDICT ON WHAT THIS TRADE IS:")
u, dn, d1 = F.pnl_unhedged.mean(), F.pnl_deltaneutral.mean(), F.pnl_delta1_fade.mean()
if u > dn * 1.5 and u > d1 * 1.2:
    print(f"  UNHEDGED ({u:.2f}) >> DELTA-NEUTRAL ({dn:.2f}) -> edge is mostly DIRECTIONAL,")
    print(f"  but it also beats the plain delta-1 fade ({d1:.2f}), so the option adds something.")
elif u > dn * 1.5:
    print(f"  UNHEDGED ({u:.2f}) >> DELTA-NEUTRAL ({dn:.2f}) -> mostly DIRECTIONAL; compare vs")
    print(f"  delta-1 fade ({d1:.2f}) — if the fade is comparable, use FUTURES, not options.")
elif abs(u - dn) < 0.5 * max(abs(dn), 1e-9):
    print(f"  UNHEDGED ({u:.2f}) ~= DELTA-NEUTRAL ({dn:.2f}) -> the edge IS the VOL OVERSHOOT.")
    print("  That is the more durable finding: hedgeable, so the tail can be controlled.")
else:
    print(f"  UNHEDGED ({u:.2f}) < DELTA-NEUTRAL ({dn:.2f}) -> spot CONTINUES after these spikes;")
    print("  the directional leg is a LIABILITY. Only the hedged expression is viable.")

for by in ("era", "split", "dte_band"):
    if by in F:
        print(f"\n--- by {by} (net pts) ---")
        g = F.groupby(by)[["pnl_unhedged", "pnl_deltaneutral", "pnl_delta1_fade"]].mean().round(2)
        g["n"] = F.groupby(by).size()
        print(g.to_string())

print()
print("=" * 116)
print("★ CRISIS-DATE TAIL TEST — the days this trade is structurally short")
print("=" * 116)
hit = F[F["day"].isin(CRISIS)]
if hit.empty:
    print("  No filtered events on the named crisis dates. Checking the worst days in-sample instead.")
else:
    for dy, g in hit.groupby("day"):
        print(f"  {dy} ({CRISIS[dy]:<16}) n={len(g):>3}  unhedged {g.pnl_unhedged.mean():>8.2f}  "
              f"worst {g.pnl_unhedged.min():>8.1f}  delta-neutral {g.pnl_deltaneutral.mean():>7.2f}")

print("\n  WORST 10 SINGLE TRADES (unhedged) — is any one of them account-threatening?")
w10 = F.nsmallest(10, "pnl_unhedged")[["day", "typ", "strike", "overshoot", "pnl_unhedged",
                                       "pnl_deltaneutral", "pnl_delta1_fade"]]
print(w10.to_string(index=False))

print("\n  DAILY AGGREGATION (a real book takes every signal that day, so single-day loss is what bites)")
dd = F.groupby("day")["pnl_unhedged"].agg(n="size", total="sum").sort_values("total")
print(f"    worst day total: {dd.total.min():>8.1f} pts across {int(dd.iloc[0]['n'])} trades "
      f"on {dd.index[0]}")
print(f"    p01 / p05 of daily totals: {dd.total.quantile(.01):.1f} / {dd.total.quantile(.05):.1f} pts")
print(f"    mean daily total: {dd.total.mean():.2f} pts over {len(dd)} trading days")
rs = 187_500  # margin per lot at 10% of notional, spot~25000
print(f"\n    at 10% margin (~Rs{rs:,}/lot) a Rs10L account holds ~{int(1_000_000/rs)} lots")
print(f"    worst day in rupees at that size: Rs{dd.total.min()*LOT*int(1_000_000/rs):,.0f} "
      f"({100*dd.total.min()*LOT*int(1_000_000/rs)/1_000_000:.1f}% of Rs10L)")

pd.DataFrame(rows).to_csv(OUT / "three_way_comparison.csv", index=False)
F.to_csv(OUT / "filtered_trades.csv", index=False)
print("\nwrote three_way_comparison.csv, filtered_trades.csv")
