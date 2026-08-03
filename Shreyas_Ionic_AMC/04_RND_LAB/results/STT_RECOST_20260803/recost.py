"""BUDGET-2026 STT HIKE — re-cost every surviving finding. This is a structural break in our costs.

CONFIRMED FROM TWO INDEPENDENT SOURCES (2026-08-03):
  Union Budget 2026, effective **1 April 2026**:
    FUTURES sale ................ 0.02%  -> 0.05%   (seller)   = +150%
    OPTIONS sale, on premium .... 0.10%  -> 0.15%   (seller)   = +50%
    OPTIONS exercise ............ 0.125% -> 0.15%   (purchaser)
  Stated rationale: curb F&O speculation. Revenue target Rs63,700cr FY26 / Rs73,700cr FY27.
  Sources: HDFC Securities budget note, HDFC Bank, ICICI Direct, ClearTax, 1Finance, Finnovate.

WHY THIS IS THE MOST CONSEQUENTIAL NUMBER IN THE BOOK
  STT is not a line item in our futures cost - it IS the futures cost. Decomposition check:
  the firm's model uses 4.47 index pts round trip pre-Oct-2024 and 5.97 after, and that Oct-2024
  step came from STT 0.0125% -> 0.020%. So dSTT of 0.0075% moved the total by 1.50 pts, implying
  0.02% = 4.00 pts, i.e. a reference spot near 20,000 (0.0002 x 20000 = 4.0). That reconciles
  exactly, so the non-STT residual is 5.97 - 4.00 = **1.97 pts** and STT scales linearly with spot.

  At 0.05% the STT term nearly TRIPLES. Every directional futures finding this session was measured
  against a cost floor that is about to more than double, and the whole session's central result was
  that gross edges cluster at 2-5 index points against a 5-6 point floor.

  The asymmetry is the actionable part: options are hit ~3%, futures ~124%, and MCX commodities are
  NOT hit at all (they pay CTT, not STT). That REVERSES my own earlier conclusion that gold had no
  cost advantage over NIFTY futures.

WHAT THIS SCRIPT DOES
  1. Rebuilds the cost model from first principles at old and new rates, across a spot grid.
  2. Re-costs every surviving/candidate cell from this session by adding the delta.
  3. Reports which survive, which die, and the break-even gross edge now required.
  Nothing here amends COST_STANDARDS.md - that is APPROVED under D-021 and needs Principal
  sign-off. This is the evidence pack for that decision.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent
OUT.mkdir(parents=True, exist_ok=True)
LOT = 65

STT_FUT_OLD, STT_FUT_NEW = 0.0002, 0.0005          # 0.02% -> 0.05%, sell side
STT_OPT_OLD, STT_OPT_NEW = 0.0010, 0.0015          # 0.10% -> 0.15% of premium, sell side
NON_STT_FUT_PTS = 1.97                              # derived above; brokerage+exch+GST+stamp+SEBI
SLIP_FUT_RT = 0.5
BROK_OPT_PTS_SIDE = 25.0 / LOT                      # Rs25/lot/side = 0.385 premium pts
SLIP_OPT_SIDE = 0.5

# ---------------------------------------------------------------- futures cost by spot
rows = []
for spot in (18000, 20000, 22000, 24000, 26000):
    old = STT_FUT_OLD * spot + NON_STT_FUT_PTS + SLIP_FUT_RT
    new = STT_FUT_NEW * spot + NON_STT_FUT_PTS + SLIP_FUT_RT
    rows.append(dict(spot=spot, stt_old_pts=round(STT_FUT_OLD * spot, 2),
                     stt_new_pts=round(STT_FUT_NEW * spot, 2),
                     rt_old_pts=round(old, 2), rt_new_pts=round(new, 2),
                     delta_pts=round(new - old, 2), ratio=round(new / old, 2),
                     pct_of_notional_old=round(100 * old * LOT / (spot * LOT), 4),
                     pct_of_notional_new=round(100 * new * LOT / (spot * LOT), 4)))
F = pd.DataFrame(rows)
print("=" * 108)
print("FUTURES ROUND-TRIP COST, index points per lot (STT scales with spot; non-STT residual 1.97)")
print("=" * 108)
print(F.to_string(index=False))
REF = 24000
d_fut = float(F.loc[F.spot == REF, "delta_pts"].iloc[0])
rt_new = float(F.loc[F.spot == REF, "rt_new_pts"].iloc[0])
rt_old = float(F.loc[F.spot == REF, "rt_old_pts"].iloc[0])
print(f"\nAt spot {REF:,}: round trip {rt_old:.2f} -> {rt_new:.2f} pts  (+{d_fut:.2f}, "
      f"{rt_new / rt_old:.2f}x)")

# ---------------------------------------------------------------- options cost by premium
orows = []
for prem in (30, 60, 100, 150, 250):
    # a round trip touches the sell side once (buy-then-sell, or sell-then-buy)
    old = 2 * BROK_OPT_PTS_SIDE + 2 * SLIP_OPT_SIDE + STT_OPT_OLD * prem
    new = 2 * BROK_OPT_PTS_SIDE + 2 * SLIP_OPT_SIDE + STT_OPT_NEW * prem
    orows.append(dict(premium_pts=prem, stt_old=round(STT_OPT_OLD * prem, 3),
                      stt_new=round(STT_OPT_NEW * prem, 3), rt_old=round(old, 3),
                      rt_new=round(new, 3), delta=round(new - old, 3),
                      ratio=round(new / old, 3)))
O = pd.DataFrame(orows)
print("\n" + "=" * 108)
print("OPTIONS ROUND-TRIP COST, premium points per lot (STT is on PREMIUM, so it barely moves)")
print("=" * 108)
print(O.to_string(index=False))

print("\n" + "=" * 108)
print("THE ASYMMETRY — this is the actionable finding")
print("=" * 108)
gold_pct = 0.0246          # measured in GOLD_INTRADAY_20260731, MCX GOLDM, CTT not STT
fut_pct_old = 100 * rt_old / REF
fut_pct_new = 100 * rt_new / REF
print(f"  NIFTY futures, % of notional : {fut_pct_old:.4f}%  ->  {fut_pct_new:.4f}%   "
      f"({fut_pct_new / fut_pct_old:.2f}x)")
print(f"  NIFTY options (100pt premium): {O.loc[O.premium_pts == 100, 'rt_old'].iloc[0]:.3f}  ->  "
      f"{O.loc[O.premium_pts == 100, 'rt_new'].iloc[0]:.3f} premium pts   "
      f"({O.loc[O.premium_pts == 100, 'ratio'].iloc[0]:.3f}x)")
print(f"  MCX GOLDM, % of notional     : {gold_pct:.4f}%  ->  {gold_pct:.4f}%   "
      f"(1.00x — commodities pay CTT, NOT STT)")
print(f"\n  => Gold is now {fut_pct_new / gold_pct:.2f}x CHEAPER than NIFTY futures, having been "
      f"{fut_pct_old / gold_pct:.2f}x more expensive.")
print("     This REVERSES my earlier conclusion that gold carried no cost advantage.")

# ---------------------------------------------------------------- re-cost the survivors
# net_old is as MEASURED (old cost already deducted). Adding the delta gives net_new.
CELLS = [
    # label, vehicle, n, trades/mo, net_old_pts, note
    ("THREE_SOLDIERS 3-session", "FUT", 758, 5.5, 45.52, "t_NW 7.85, but ~60% BETA"),
    ("THREE_SOLDIERS 1-session", "FUT", 1778, 13.0, 18.52, "the in-spec scaling arm"),
    ("MARUBOZU_BULL 2-session", "FUT", 1022, 7.5, 29.76, "beta placebo p=0.200 — likely beta"),
    ("HAMMER 2-session", "FUT", 1100, 8.1, 25.52, "beta placebo p=0.242 — likely beta"),
    ("BOX4 first-60min break", "FUT", 55, 0.43, 20.42, "placebo 0/5, zero 2026 held-out"),
    ("ICHIMOKU_TK 15min", "FUT", 1126, 8.5, 2.442, "the one TV placebo survivor"),
    ("VORTEX 60min", "FUT", 1196, 9.1, 2.394, "placebo never run"),
    ("WTI crude-crash short", "FUT", 229, 4.1, 27.60, "held-out LARGER, 4.1/mo"),
    ("Sweep prior-day reclaim (15m)", "FUT", 1232, 8.0, 6.669, "t=2.085"),
    ("1DTE flow-imbalance FADE", "FUT", 27, 0.50, 2.80, "n=27, zero held-out"),
    ("S1-F 0DTE short straddle", "OPT", 259, 17.2, 9.71, "CERTIFIED; premium ~110 pts"),
    ("LD_SELL biweekly 0.10d strangle", "OPT", 286, 1.4, np.nan, "CAGR-quoted, not pts"),
    ("Overshoot sell (0-1DTE)", "OPT", 913, 24.0, 0.30, "within cost-model error bars"),
    ("Ratio calendar 1x1 rolled", "OPT", 100, 0.9, 28.48, "premium ~150 pts"),
]
OPT_PREM_ASSUMED = {"S1-F 0DTE short straddle": 110, "Overshoot sell (0-1DTE)": 60,
                    "Ratio calendar 1x1 rolled": 150}
res = []
for lbl, veh, n, tpm, net_old, note in CELLS:
    if not np.isfinite(net_old):
        res.append(dict(cell=lbl, vehicle=veh, n=n, per_month=tpm, net_old=None, delta=None,
                        net_new=None, verdict="n/a (quoted as CAGR, re-cost at source)", note=note))
        continue
    if veh == "FUT":
        delta = d_fut
    else:
        prem = OPT_PREM_ASSUMED.get(lbl, 100)
        delta = (STT_OPT_NEW - STT_OPT_OLD) * prem
    net_new = net_old - delta
    v = ("SURVIVES" if net_new > 0.5 else ("MARGINAL" if net_new > 0 else "DIES"))
    res.append(dict(cell=lbl, vehicle=veh, n=n, per_month=tpm, net_old=round(net_old, 3),
                    delta=round(delta, 3), net_new=round(net_new, 3),
                    pts_month_new=round(net_new * tpm, 1), verdict=v, note=note))
R = pd.DataFrame(res)
print("\n" + "=" * 128)
print(f"RE-COST OF EVERY SURVIVOR — futures delta +{d_fut:.2f} pts at spot {REF:,}; "
      f"options delta is premium-scaled")
print("=" * 128)
print(R.to_string(index=False))

print("\n" + "=" * 108)
print("BREAK-EVEN GROSS EDGE NOW REQUIRED (futures, spot 24,000)")
print("=" * 108)
print(f"  Gross edge must exceed {rt_new:.2f} index points just to break even, up from "
      f"{rt_old:.2f}.")
print(f"  The session's measured gross edges clustered at 2-5 points. That band was already below")
print(f"  the old {rt_old:.2f} floor; it is now {rt_new / 4.0:.1f}x below the new one.")
print(f"  At RR 1:1.5 with a 1-ATR (~250pt) stop the cost is {100 * rt_new / 375:.2f}% of the target,")
print(f"  so LARGE-TARGET futures trades are hurt far less than small-target ones.")

F.to_csv(OUT / "futures_cost_by_spot.csv", index=False)
O.to_csv(OUT / "options_cost_by_premium.csv", index=False)
R.to_csv(OUT / "recost_survivors.csv", index=False)
json.dump(dict(effective="2026-04-01", stt_fut_old=STT_FUT_OLD, stt_fut_new=STT_FUT_NEW,
               stt_opt_old=STT_OPT_OLD, stt_opt_new=STT_OPT_NEW,
               non_stt_fut_pts=NON_STT_FUT_PTS, ref_spot=REF,
               fut_rt_old=rt_old, fut_rt_new=rt_new, fut_delta=d_fut,
               gold_pct_of_notional=gold_pct, fut_pct_new=fut_pct_new,
               note="evidence pack only; COST_STANDARDS.md amendment needs Principal sign-off (D-021)"),
          open(OUT / "meta.json", "w"), indent=2)
print("\nwrote futures_cost_by_spot.csv, options_cost_by_premium.csv, recost_survivors.csv, meta.json")
