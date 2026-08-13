"""TWO STRUCTURES AIMED DIRECTLY AT THE >100% CAGR / <25% MDD MANDATE.

CONTEXT — what is already measured (all ex-events unless noted):
  sell spike-side option, UNHEDGED ....... -0.51 pts (+0.02 ex-events)  <- two effects OPPOSE
  sell spike-side option, DELTA-HEDGED ... +0.76 pts                    <- only positive expression
  buy spike-side option .................. -2.63 pts (rich) / +0.55 (cheap bucket)
  delta-1 fade of the spike .............. -4.03 pts  => SPOT CONTINUES, it does not revert
  => the seller's vol-crush GAIN is cancelled by the continuation LOSS. Hedging removes the
     continuation but costs ~1.20 pts of futures round-trip.

STRUCTURE 1 — "OPPOSITE-SIDE SELL" (the Principal's double-trade with the sign corrected).
  After an UP spike, sell the PUT (not the call):
     * vol crush        -> IV rises on BOTH wings in a spike, so the put is also inflated -> seller GAINS
     * spot CONTINUES up -> the put decays faster                                        -> seller GAINS
  Both legs pay the same way, so no delta hedge is needed and no hedge cost is paid.
  This is the structure the measured facts actually imply, and it has never been tested.

STRUCTURE 2 — "CREDIT SPREAD" on the opposite side (capital efficiency + capped tail).
  Sell the near-OTM option, buy a further-OTM wing, same expiry.
     * capital at risk = (width - credit) x LOT, roughly Rs4-7k/lot vs Rs162,500 for a naked short
       => ~30x more positions per rupee, which is the only route to triple-digit CAGR
     * max loss is CAPPED by construction -> directly fixes the -515pt election-day problem
     * cost: 2 legs (Rs25/lot/side each) and the wing gives back some premium
  Both structures are scored on CAGR *and* maxDD, at the Principal's margin rules, ex-events.

MEMORY: chain.load_expiry is lru_cache(maxsize=64) x ~40MB => 2.5GB. Process one expiry, then
cache_clear() + gc. Two jobs already segfaulted (rc 0xC0000005) from this.
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
LOT, STEP = 65, 50
COST_LEG = 1.45          # premium pts round trip per leg
HOLD_MIN = 60
SCHEDULED = {"2024-06-04", "2024-06-03", "2024-02-01", "2023-02-01", "2022-02-01",
             "2025-02-01", "2026-02-01", "2024-07-23"}

ev = pd.read_csv(OUT / "overshoot_measured.csv")
ev["t0"] = pd.to_datetime(ev["t0"])
ev["day"] = ev["t0"].dt.date.astype(str)
ev["expiry_d"] = pd.to_datetime(ev["expiry"]).dt.date
ev = ev[~ev["day"].isin(SCHEDULED)]                     # event avoidance, Principal rule
ev = ev[ev["overshoot"] >= 3]                            # richness filter (mechanism-motivated)
print(f"[events] {len(ev):,} rich+ex-event spikes | expiries {ev.expiry_d.nunique()}", flush=True)

rows = []
for i, (exp, grp) in enumerate(ev.groupby("expiry_d"), 1):
    try:
        df = chain.load_expiry(exp)
    except Exception:
        chain.load_expiry.cache_clear(); gc.collect(); continue
    df = df[df["volume"] > 0]
    for _, e in grp.iterrows():
        t0, S0 = e["t0"], float(e["S0"])
        spike_up = (e["typ"] == "CE")            # CE inflated => spike was UP
        opp = "PE" if spike_up else "CE"         # OPPOSITE side
        t_exit = t0 + pd.Timedelta(minutes=HOLD_MIN)
        atm = round(S0 / STEP) * STEP
        # opposite-side short strike ~2 steps OTM; wing 4 steps further out
        k_short = atm - 2 * STEP if opp == "PE" else atm + 2 * STEP
        k_wing = k_short - 4 * STEP if opp == "PE" else k_short + 4 * STEP

        def leg(K, typ):
            s = df[(df["strike"] == K) & (df["option_type"] == typ)]
            if s.empty:
                return None
            s = s.set_index("t")[["close", "volume"]].sort_index()
            a = s[(s.index >= t0) & (s.index <= t0 + pd.Timedelta(minutes=2))]
            b = s[(s.index > t0) & (s.index <= t_exit)]
            if a.empty or b.empty:
                return None
            return float(a["close"].iloc[0]), float(b["close"].iloc[-1]), float(a["volume"].iloc[0])

        L1 = leg(k_short, opp)
        L2 = leg(k_wing, opp)
        if L1 is None:
            continue
        e1, x1, v1 = L1
        if e1 < 1.0:
            continue                              # avoid near-zero premium legs
        # STRUCTURE 1: naked opposite-side short
        naked = (e1 - x1) - COST_LEG
        # STRUCTURE 2: credit spread (short k_short, long k_wing)
        spread = np.nan; cap_at_risk = np.nan; credit = np.nan
        if L2 is not None:
            e2, x2, _ = L2
            credit = e1 - e2
            if credit > 0.5:
                spread = (e1 - x1) - (e2 - x2) - 2 * COST_LEG
                width = abs(k_short - k_wing)
                cap_at_risk = max(width - credit, 1.0)     # points at risk per lot
        rows.append(dict(day=e["day"], t0=t0, era=e["era"], split=e["split"],
                         dte_band=e["dte_band"], overshoot=e["overshoot"], spike_up=spike_up,
                         opp=opp, k_short=k_short, prem_short=e1,
                         naked=naked, spread=spread, credit=credit,
                         cap_at_risk=cap_at_risk, vol_short=v1))
    chain.load_expiry.cache_clear(); gc.collect()
    if i % 40 == 0:
        print(f"  [{i}] {exp} rows {len(rows):,}", flush=True)

r = pd.DataFrame(rows)
r.to_csv(OUT / "opposite_spread_trades.csv", index=False)
print(f"\n[built] {len(r):,} trades\n", flush=True)


def block(x, lbl, cap_pts=None):
    x = x.dropna()
    if len(x) < 40:
        print(f"  {lbl:<34} n={len(x)} too thin"); return None
    w, l = x[x > 0], x[x <= 0]
    pf = float(w.sum() / abs(l.sum())) if l.sum() else np.nan
    print(f"  {lbl:<34} n={len(x):>5} mean {x.mean():>7.2f} med {x.median():>7.2f} "
          f"win {100*(x>0).mean():>5.1f}% worst {x.min():>8.1f} PF {pf:>5.2f}")
    return x


print("=" * 122)
print("STRUCTURE 1 — NAKED OPPOSITE-SIDE SHORT (no delta hedge; both effects aligned)")
print("=" * 122)
n_all = block(r["naked"], "ALL")
for by in ("era", "split", "dte_band"):
    for k, g in r.groupby(by):
        block(g["naked"], f"  {by}={k}")

print()
print("=" * 122)
print("STRUCTURE 2 — CREDIT SPREAD on the opposite side (capped tail, capital-efficient)")
print("=" * 122)
s_all = block(r["spread"], "ALL")
for by in ("era", "split", "dte_band"):
    for k, g in r.groupby(by):
        block(g["spread"], f"  {by}={k}")

print()
print("=" * 122)
print("ECONOMICS — CAGR / maxDD at Principal margin rules (lot=65, spot~25000)")
print("=" * 122)
mo = max(len(pd.to_datetime(r.day).dt.to_period("M").unique()), 1)


def econ(col, cap_per_lot, lbl, dep=(1.0, 0.5, 0.25)):
    d = r.dropna(subset=[col])
    if len(d) < 40:
        return
    per_mo = len(d) / mo
    edge = d[col].mean()
    lots_max = max(int(1_000_000 / max(cap_per_lot, 1)), 1)
    dd = d.groupby("day")[col].sum()
    eqp = dd.cumsum()
    mdd_pts = float((eqp - eqp.cummax()).min())
    print(f"\n  {lbl}: {per_mo:.1f} trades/mo  edge {edge:+.2f} pts  capital Rs{cap_per_lot:,.0f}/lot "
          f"-> max {lots_max} lots")
    for f in dep:
        lots = max(int(lots_max * f), 1)
        rs_mo = per_mo * edge * LOT * lots
        cagr = 100 * ((1 + rs_mo / 1_000_000) ** 12 - 1) if rs_mo > -1_000_000 else float("nan")
        mdd_rs = mdd_pts * LOT * lots
        mdd_pct = 100 * mdd_rs / 1_000_000
        ok = "OK" if abs(mdd_pct) <= 25 else "BREACHES 25%"
        print(f"    {int(f*100):>3}% dep ({lots:>3} lots): {100*rs_mo/1_000_000:>6.2f}%/mo -> "
              f"CAGR {cagr:>8.1f}%   maxDD {mdd_pct:>7.1f}%  {ok}")


econ("naked", 0.10 * 25000 * LOT, "NAKED OPPOSITE SHORT (10% margin)")
med_cap = r["cap_at_risk"].median()
if np.isfinite(med_cap):
    econ("spread", med_cap * LOT, f"CREDIT SPREAD (capital = width-credit ~ {med_cap:.0f} pts)")
print("\nwrote opposite_spread_trades.csv")
