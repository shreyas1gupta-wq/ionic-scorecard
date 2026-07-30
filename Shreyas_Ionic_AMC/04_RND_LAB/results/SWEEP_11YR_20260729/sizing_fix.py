"""FIX for the broken 0.1-Kelly run in sweep_11yr.py.

DEFECT (disclosed, not hidden): apply_sizing(mode='kelly01') let lot count compound with
equity with no ruin constraint, so equity went NEGATIVE. That produced impossible metrics
(maxDD -266%/-319%/-409%, CAGR 8.2e10%/1.4e17%) because the drawdown formula divides by a
negative running peak. Those figures are ARTIFACTS and must never be quoted.

WHAT THIS DOES INSTEAD: proper fixed-fractional sizing swept across risk levels, with
  (a) a hard ruin floor — if equity drops below RUIN_FRAC of start, trading STOPS and the
      cell is reported as RUINED (not as a CAGR),
  (b) a margin cap (10% of notional per lot, Principal ruling) AND a max-lots cap,
  (c) drawdown computed on an equity path that cannot go negative.
Purpose: find the risk fraction that maximizes Calmar WITHOUT risk of ruin, which is the
actually useful answer, and show where Kelly-scale sizing tips into ruin.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent
LOT = 75
MARGIN_PCT = 0.10
CAPITAL = 10_00_000.0
RUIN_FRAC = 0.35          # equity < 35% of start => ruined, stop trading
MAX_LOTS = 200            # sanity cap (liquidity/practicality)
IS_A, IS_B = dt.date(2021, 5, 1), dt.date(2025, 12, 31)

BROK, EXCH, GST, STAMP, SEBI_CR = 20.0, 0.0019 / 100, 0.18, 0.002 / 100, 10.0
STT_OLD, STT_NEW, STT_SWITCH = 0.0125 / 100, 0.020 / 100, dt.date(2024, 10, 1)


def rt_cost(e, x, lots, d):
    qty = lots * LOT
    stt = (STT_OLD if d < STT_SWITCH else STT_NEW) * x * qty
    turn = (e + x) * qty
    brok = BROK * 2
    exch = EXCH * turn
    return brok + exch + stt + GST * (brok + exch) + STAMP * e * qty + SEBI_CR * turn / 1e7


def nw_t(x, lags=5):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 10: return np.nan
    m = x.mean(); dv = x - m; n = len(x); var = (dv @ dv) / n
    for L in range(1, min(lags, n - 1) + 1):
        var += 2 * (1 - L / (lags + 1)) * ((dv[L:] @ dv[:-L]) / n)
    return m / np.sqrt(var / n) if var > 0 else np.nan


def run(tr: pd.DataFrame, risk_frac: float, stop_pts: float):
    """Fixed-fractional: risk risk_frac of CURRENT equity per trade, sized off the stop."""
    tr = tr.sort_values("t").reset_index(drop=True)
    eq = CAPITAL
    rows = []
    ruined_at = None
    for _, r in tr.iterrows():
        if eq < RUIN_FRAC * CAPITAL:
            ruined_at = r["date"]; break
        per_lot_risk = max(stop_pts, 1.0) * LOT
        lots = int(np.floor(risk_frac * eq / per_lot_risk))
        lots = min(lots, int(np.floor(eq / (r["notional"] * MARGIN_PCT))), MAX_LOTS)
        if lots < 1:
            continue
        gross = r["gross_pts"] * LOT * lots
        cost = rt_cost(r["entry"], r["exit"], lots, r["date"])
        eq += gross - cost
        rows.append({"date": r["date"], "net": gross - cost, "gross": gross,
                     "cost": cost, "lots": lots, "equity": eq})
    if not rows:
        return {"risk_frac": risk_frac, "status": "no_trades"}
    d = pd.DataFrame(rows)
    # CORRECT: use the ACTUAL tracked compounding equity path, not CAPITAL+cumsum
    # (mixing compounding position sizes with an additive equity reconstruction was the bug
    #  that produced maxDD -266%/-409% and worst-day -844% of capital).
    eqs = d.groupby("date")["equity"].last()
    eqs = eqs.sort_index()
    peak = eqs.cummax()
    mdd = float(((eqs - peak) / peak).min())        # on the real path; cannot exceed -100%
    yrs = max((max(d["date"]) - min(d["date"])).days / 365.25, .01)
    endv = float(eqs.iloc[-1])
    cagr = (endv / CAPITAL) ** (1 / yrs) - 1 if endv > 0 else float("nan")
    # returns as pct change of the equity path (geometric), not rupees over fixed capital
    dr = eqs.pct_change().dropna()
    sh = float(dr.mean() / dr.std() * np.sqrt(252)) if len(dr) > 2 and dr.std() > 0 else np.nan
    # worst day as % of equity AT THAT TIME
    daily_net = d.groupby("date")["net"].sum()
    eq_prev = eqs.shift(1).fillna(CAPITAL)
    worst_day_pct = float((daily_net / eq_prev).min() * 100)
    w, l = d[d.net > 0]["net"], d[d.net <= 0]["net"]
    return {
        "risk_frac": risk_frac,
        "status": f"RUINED@{ruined_at}" if ruined_at else "ok",
        "n": len(d), "end_equity": round(endv),
        "CAGR_pct": round(100 * cagr, 2) if np.isfinite(cagr) else None,
        "maxDD_pct": round(100 * mdd, 2),
        "Calmar": round(float(cagr / abs(mdd)), 2) if mdd and np.isfinite(cagr) else None,
        "Sharpe": round(sh, 2), "PF": round(float(w.sum() / abs(l.sum())), 2) if l.sum() else None,
        "t_nw": round(float(nw_t(dr.values)), 2),
        "median_lots": int(d.lots.median()), "max_lots": int(d.lots.max()),
        "worst_day_pct_of_equity": round(worst_day_pct, 2),
    }


CFG_STOP = {"D_overnight1_trail40": 50, "E_swing3_trail60": 60}
# Kelly f* measured on IS was 0.161 (D) and 0.190 (E). 0.1x Kelly => ~1.6-1.9% risk/trade.
RISK_GRID = [0.0025, 0.005, 0.0075, 0.01, 0.016, 0.019, 0.03, 0.05]

def main():
    report = {"note": "fixed-fractional sizing sweep; replaces the invalid kelly01 output",
              "ruin_floor_frac": RUIN_FRAC, "capital": CAPITAL, "configs": {}}
    for cfg, stop in CFG_STOP.items():
        tr = pd.read_csv(OUT / f"trades_{cfg}_1lot.csv", parse_dates=["t"])
        tr["date"] = pd.to_datetime(tr["date"]).dt.date
        print(f"\n=== {cfg} (stop={stop}pts, n={len(tr)}) ===", flush=True)
        print(f"{'risk/trade':>11} {'status':>22} {'CAGR':>9} {'maxDD':>9} {'Calmar':>7} "
              f"{'Sharpe':>7} {'t':>6} {'medLots':>8} {'worstDay%':>10}")
        res = []
        for rf in RISK_GRID:
            m = run(tr, rf, stop)
            res.append(m)
            print(f"{100*rf:>10.2f}% {m.get('status','?'):>22} "
                  f"{str(m.get('CAGR_pct')):>8}% {str(m.get('maxDD_pct')):>8}% "
                  f"{str(m.get('Calmar')):>7} {str(m.get('Sharpe')):>7} {str(m.get('t_nw')):>6} "
                  f"{str(m.get('median_lots')):>8} {str(m.get("worst_day_pct_of_equity")):>9}%",
                  flush=True)
        report["configs"][cfg] = res
    (OUT / "sizing_fix_report.json").write_text(json.dumps(report, indent=2, default=str),
                                                encoding="utf-8")
    print("\nwrote sizing_fix_report.json", flush=True)


if __name__ == "__main__":
    main()
