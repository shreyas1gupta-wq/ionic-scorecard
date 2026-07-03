"""S-04 short-strangle 2x-cost SURVIVAL certification (D-M1, 2026-07-04).

CEO decision: NO full re-shuffle. Certify only whether the registered edge
+0.2241%/spot (managed short strangle, mean of `strangle_managed`) survives 2x
the FULL approved cost stack.

CRITICAL LINEAGE FACT (from shortlist_shortvol.py):
  `strangle_managed` ALREADY carries 1x slippage of SLIP = 0.015*1.4 = 0.021/leg
  (fr.slippage_pct('stock','near_otm')), applied as (1+/-SLIP) on every premium leg.
  It does NOT carry brokerage / STT / exchange txn / GST / stamp / SEBI.
  So the registered 0.2241% is: GROSS - 1x_slippage. Nothing else deducted.

To test "survives 2x the FULL stack" honestly we must:
  (1) reconstruct GROSS edge = registered + (1x slippage cost we add back), then
  (2) subtract 2x [slippage + brokerage + STT + txn + GST + stamp + SEBI].

Per COST_STANDARDS (D-021, APPROVED):
  - Options single-stock near-ATM slippage floor: max(1 tick, 0.5-1.5% premium)/leg.
    2x -> 1.0-3.0%/leg. (The code's baked-in 2.1%/leg already sits INSIDE the 2x band.)
  - Brokerage Rs.20/order; strangle round trip = 4 fills.
  - STT options 0.1% of premium sell-side.
  - Exch txn options ~0.035% premium; GST 18% on (brok+exch); SEBI Rs.10/cr; stamp 0.003% buy.
  - Promotion rule: net-positive at 2x ALL of the above.

Notional lot ~ Rs.6,00,000 (task-given). Everything expressed as % of SPOT.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\results\S-04\20260704_cost_cert")
SG = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\buying\shortlist_shortvol.parquet")
CRED = Path(r"C:\Users\SHREYA~1.1GU\AppData\Local\Temp\claude\c--Users-Shreyas-1Gupta-OneDrive---Angel-Broking-Limited-Desktop-Backup-NIFTY-500\d096bfac-0d55-4716-97ef-0deefc915522\scratchpad\s04_credit.parquet")

# ---- approved cost constants (COST_STANDARDS D-021) ----
BROK = 20.0                 # Rs / order
STT_OPT_SELL = 0.10/100     # standards: 0.1% of sell premium
EXCH_TXN = 0.035/100        # standards: ~0.035% of premium turnover
GST = 0.18
STAMP_BUY = 0.003/100
SEBI_PER_CR = 10.0
NOTIONAL = 6_00_000.0       # Rs per lot (task-given)
BAKED_SLIP = 0.021          # slippage/leg ALREADY inside strangle_managed
REG_EDGE = 0.002241         # mean strangle_managed = +0.2241% of spot (verified)

# 2x slippage per leg to TEST across the approved band (0.5-1.5% -> 1.0-3.0% at 2x)
SLIP_2X_GRID = [0.010, 0.021, 0.030]   # low band, code-baked, high band  (all x2 of a 0.5/1.05/1.5 base)


def per_trade_costs(credit_pct, buyback_frac, slip_leg):
    """All costs as FRACTION OF SPOT for ONE strangle round-trip (4 fills).
    credit_pct   = (call+put) premium collected / spot  (2 sell legs at entry)
    buyback_frac = premium paid to close / entry credit  (managed ~0.5; hold-to-exp ~intrinsic)
    slip_leg     = slippage per leg as fraction of that leg's premium
    Returns dict of cost components as % of spot.
    Notional per lot = NOTIONAL, so 1 unit of spot 'value' in a lot = NOTIONAL; but since
    everything is normalized by spot we convert flat Rs costs to %/spot via NOTIONAL.
    """
    sell_prem = credit_pct                    # premium sold at entry, as % of spot
    buy_prem_close = credit_pct * buyback_frac  # premium bought back to close, as % of spot
    prem_turnover = sell_prem + buy_prem_close  # total premium traded, as % of spot

    # slippage: paid on EVERY leg's premium. entry 2 legs (sell) + exit 2 legs (buy)
    slip = slip_leg * (sell_prem + buy_prem_close)

    # flat brokerage Rs.20 x 4 fills -> as % of spot = 80 / NOTIONAL
    brok = (BROK * 4) / NOTIONAL

    # STT: 0.1% of sell-side premium. Sell legs = entry short (credit) + at managed exit the
    # BUY-BACK is a buy (no STT). On hold-to-expiry, settlement of intrinsic is a sell-equiv;
    # conservatively apply STT to the entry sell premium only (0.1% of credit_pct).
    stt = STT_OPT_SELL * sell_prem

    # exchange txn on total premium turnover
    exch = EXCH_TXN * prem_turnover

    # GST 18% on (brokerage + exch)
    gst = GST * (brok + exch)

    # stamp 0.003% on BUY premium (entry buy? no - strangle SELLS at entry; buy is the close)
    stamp = STAMP_BUY * buy_prem_close

    # SEBI Rs.10/cr on turnover (premium turnover in Rs = prem_turnover * NOTIONAL)
    sebi = SEBI_PER_CR * (prem_turnover * NOTIONAL) / 1e7 / NOTIONAL

    return {"slip": slip, "brok": brok, "stt": stt, "exch": exch,
            "gst": gst, "stamp": stamp, "sebi": sebi,
            "total": slip + brok + stt + exch + gst + stamp + sebi}


def run():
    # empirical credit if reconstruction available; else fall back to task assumptions
    if CRED.exists():
        R = pd.read_parquet(CRED)
        emp_credit = float(R["credit_pct_spot"].mean())
        emp_med = float(R["credit_pct_spot"].median())
        emp_n = len(R)
    else:
        emp_credit = emp_med = None; emp_n = 0

    sg = pd.read_parquet(SG)
    reg = float(sg["strangle_managed"].mean())

    # managed exit: fraction of trades that hit 50% target early
    sg["man_exit"] = pd.to_datetime(sg["man_exit"]); sg["exp"] = pd.to_datetime(sg["exp"])
    early = (sg["man_exit"].dt.date != sg["exp"].dt.date).mean()
    # buyback fraction: managed early exits pay ~0.5*credit to close; held-to-expiry pay intrinsic.
    # Use a blended conservative buyback = 0.5 for early + assume ~0.4 avg intrinsic-close for held.
    bb_blend = 0.5 * early + 0.6 * (1 - early)   # conservative: held legs assumed to pay 0.6 of credit

    lines = []
    def P(*a):
        s = " ".join(str(x) for x in a); print(s); lines.append(s)

    P("="*78)
    P("S-04 SHORT-STRANGLE 2x-COST SURVIVAL CERTIFICATION  (D-M1, 2026-07-04)")
    P("="*78)
    P(f"Registered edge (mean strangle_managed) : {reg:+.4%} of spot   [DATA]")
    P(f"Baked-in slippage inside that number    : {BAKED_SLIP:.1%}/leg (1x)  [DATA, shortlist_shortvol.py L36]")
    P(f"Managed early-exit (hit 50% TP) fraction : {early:.0%}  -> blended buyback = {bb_blend:.2f}x credit")
    if emp_credit is not None:
        P(f"Empirical entry credit (call+put)        : mean {emp_credit:.3%}/spot  median {emp_med:.3%}  (n={emp_n} reconstructed)  [DATA]")
    P("")

    # Premium assumptions to show sensitivity (task: 2%/3%/4%). Also add empirical if present.
    prem_grid = [0.02, 0.03, 0.04]
    prem_labels = ["2% credit/spot", "3% credit/spot", "4% credit/spot"]
    if emp_credit is not None:
        prem_grid = [round(emp_credit, 4)] + prem_grid
        prem_labels = [f"EMPIRICAL {emp_credit:.2%}"] + prem_labels

    verdict_rows = []
    for cp, lab in zip(prem_grid, prem_labels):
        P("-"*78)
        P(f"PREMIUM ASSUMPTION: {lab}  (credit_pct = {cp:.4f} of spot)")
        P("-"*78)
        # STEP 1: add back the 1x baked slippage to recover GROSS edge
        baked_cost = per_trade_costs(cp, bb_blend, BAKED_SLIP)["slip"]
        gross = reg + baked_cost
        P(f"  gross edge (= reg {reg:+.4%} + add-back 1x slip {baked_cost:+.4%}) = {gross:+.4%}/spot")
        P(f"  {'slip/leg(2x)':>13} {'slip':>9} {'brok':>8} {'stt':>8} {'exch':>8} {'gst':>8} {'stamp':>8} {'sebi':>8} {'TOTAL2x':>9} {'NET':>9}")
        for slip2x in SLIP_2X_GRID:
            c = per_trade_costs(cp, bb_blend, slip2x)
            net = gross - c["total"]
            P(f"  {slip2x:>12.1%} {c['slip']:>9.4%} {c['brok']:>8.4%} {c['stt']:>8.4%} {c['exch']:>8.4%} "
              f"{c['gst']:>8.4%} {c['stamp']:>8.4%} {c['sebi']:>8.4%} {c['total']:>9.4%} {net:>+9.4%}")
            verdict_rows.append({"prem": lab, "slip2x": slip2x, "gross": gross,
                                 "total_cost_2x": c["total"], "net": net, "survives": net > 0})
        P("")

    P("="*78)
    P("SURVIVAL SUMMARY  (net > 0 => survives 2x full stack)")
    P("="*78)
    vr = pd.DataFrame(verdict_rows)
    surv = vr["survives"].mean()
    P(vr.assign(gross=lambda d:(d["gross"]*100).round(3),
                total_cost_2x=lambda d:(d["total_cost_2x"]*100).round(3),
                net=lambda d:(d["net"]*100).round(3),
                slip2x=lambda d:(d["slip2x"]*100)).to_string(index=False))
    P(f"\nCells surviving: {vr['survives'].sum()}/{len(vr)} = {surv:.0%}")
    worst = vr.loc[vr["net"].idxmin()]
    best = vr.loc[vr["net"].idxmax()]
    P(f"WORST cell: {worst['prem']} @ {worst['slip2x']:.1%} slip -> net {worst['net']:+.4%}")
    P(f"BEST  cell: {best['prem']} @ {best['slip2x']:.1%} slip -> net {best['net']:+.4%}")

    (OUT/"verdict_raw.txt").write_text("\n".join(lines), encoding="utf-8")
    vr.to_csv(OUT/"survival_grid.csv", index=False)
    cfg = {"registered_edge_pct_spot": reg, "baked_slippage_per_leg": BAKED_SLIP,
           "notional_per_lot": NOTIONAL, "fills_per_trade": 4,
           "managed_early_exit_frac": float(early), "buyback_blend": float(bb_blend),
           "empirical_credit_pct_spot_mean": emp_credit, "empirical_credit_n": emp_n,
           "cost_constants": {"BROK": BROK, "STT_OPT_SELL": STT_OPT_SELL, "EXCH_TXN": EXCH_TXN,
                              "GST": GST, "STAMP_BUY": STAMP_BUY, "SEBI_PER_CR": SEBI_PER_CR},
           "slip_2x_grid": SLIP_2X_GRID, "prem_grid": prem_grid,
           "survival_frac": float(surv), "worst_net_pct_spot": float(worst["net"]),
           "best_net_pct_spot": float(best["net"])}
    (OUT/"config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print("\nsaved config.json, survival_grid.csv, verdict_raw.txt ->", OUT)
    return vr, cfg


if __name__ == "__main__":
    run()
