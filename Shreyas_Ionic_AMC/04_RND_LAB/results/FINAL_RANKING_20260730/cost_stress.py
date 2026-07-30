"""COST-STRESS ROBUSTNESS (Principal refinement, 2026-07-30).

Principal: *"do not keep [top-decile-excluded breakeven] a hard fast rule, it depends upon frequency
of trades too... if no of trades too high we can double the cost of trading and then check."*

CORRECT AND ADOPTED. The right robustness test depends on trade frequency:
  * LOW frequency (few trades/mo)  -> top-decile-excluded test. You genuinely might miss 5 specific trades.
  * HIGH frequency (many trades/mo)-> COST STRESS. You cannot miss 438 trades if you trade mechanically,
    but you WILL face worse slippage/fills than modelled. Cost is the live degradation.
Reported here: net P&L at 1x / 1.5x / 2x / 3x modelled cost, plus the BREAKEVEN COST MULTIPLE
(how many times modelled cost the strategy can absorb before it stops making money) = the cost cushion.
"""
from __future__ import annotations
import warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

R = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
         r"\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results")
LOT, CARRY_M = 75, 0.005
SPLIT = pd.Timestamp("2024-10-01")
rows = []

def add(tag, gross, cost, dates, freq_note):
    g, c = np.asarray(gross, float), np.asarray(cost, float)
    d = pd.to_datetime(pd.Series(dates))
    mo = max((d.max() - d.min()).days / 30.44, 1)
    r = {"strategy": tag, "n": len(g), "trades_per_month": round(len(g) / mo, 1),
         "gross": round(float(g.sum())), "cost_1x": round(float(c.sum())),
         "cost_pct_of_gross": round(100 * float(c.sum() / max(g.sum(), 1)), 1), "freq": freq_note}
    for m in (1.0, 1.5, 2.0, 3.0):
        r[f"net_{m}x"] = round(float(g.sum() - m * c.sum()))
    # breakeven multiple
    r["breakeven_cost_mult"] = round(float(g.sum() / c.sum()), 2) if c.sum() > 0 else None
    # post-Oct-2024 at 2x
    post = d >= SPLIT
    if post.sum() > 10:
        r["post2024_net_2x"] = round(float(g[post.values].sum() - 2 * c[post.values].sum()))
    rows.append(r)

# SWEEP E / D — high frequency
for tag, fn in (("SWEEP_E", "trades_E_swing3_trail60_1lot.csv"),
                ("SWEEP_D", "trades_D_overnight1_trail40_1lot.csv")):
    t = pd.read_csv(R / "SWEEP_11YR_20260729" / fn)
    t["date"] = pd.to_datetime(t["date"])
    carry = t["entry"] * (CARRY_M / 30.0) * np.maximum(t["hold_min"] / 375.0, 0.5)
    gross = (t["gross_pts"] - np.sign(t["dir"]) * carry) * LOT
    add(tag, gross, t["cost"], t["date"], "HIGH -> cost stress is the right test")

# CALENDAR — low frequency
rc = pd.read_csv(R / "RATIO_CALENDAR_20260730" / "grid_a_trades_raw.csv")
c = rc[(rc.strike_struct == "ATM_ATM") & (rc.ratio == "1x1") & (rc.exit_variant == "3d_before")]
c = c.drop_duplicates(subset=["day0", "near_expiry"]).copy()
add("CALENDAR_1x1", c["gross_pts"] * LOT, c["friction_pts"] * LOT,
    pd.to_datetime(c["exit_day"]), "LOW -> top-decile test also applies")

# SWING — low frequency
sw = pd.read_csv(R / "SWING_DELTA1_20260729" / "all_trades.csv")
m = [x for x in sw["cell"].unique() if "priorweek" in x and "fixed_10" in x]
if m:
    q = sw[sw["cell"] == m[0]].copy()
    add("SWING_pw10", q["gross"], q["cost"], pd.to_datetime(q["exit_date"]),
        "LOW -> top-decile test also applies")

res = pd.DataFrame(rows)
res.to_csv("cost_stress.csv", index=False)
print("=" * 124)
print("COST-STRESS ROBUSTNESS — net P&L as modelled cost is multiplied")
print("=" * 124)
cols = ["strategy", "n", "trades_per_month", "cost_pct_of_gross", "net_1.0x", "net_1.5x",
        "net_2.0x", "net_3.0x", "breakeven_cost_mult", "post2024_net_2x"]
print(res[[c for c in cols if c in res.columns]].to_string(index=False))
print()
for _, r in res.iterrows():
    bm = r.get("breakeven_cost_mult")
    v = ("ROBUST — absorbs >3x modelled cost" if bm and bm > 3 else
         "OK — absorbs 2-3x" if bm and bm > 2 else
         "THIN — breaks below 2x" if bm and bm > 1 else "FAILS at modelled cost")
    print(f"  {r['strategy']:<14} {r['trades_per_month']:>6}/mo  breakeven at {bm}x cost -> {v}")
print(f"\n  {'freq guidance:':<14} " + " | ".join(f"{r['strategy']}={r['freq']}" for _, r in res.iterrows())[:100])
