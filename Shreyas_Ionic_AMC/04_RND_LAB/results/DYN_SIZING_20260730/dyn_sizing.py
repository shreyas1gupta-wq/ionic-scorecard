"""DRAWDOWN-BUDGETED DYNAMIC SIZING ENGINE (2026-07-30).

Principal ask: "scale conservatively instead of fixed lot over profits with a mdd (20% buffer)".

THE MECHANIC — CPPI-style drawdown floor. PREDICTION-FREE by design, which is the whole point:
    HWM     = running high-water mark of equity
    FLOOR   = HWM * (1 - MDD_BUDGET)          MDD_BUDGET = 0.20
    CUSHION = equity - FLOOR
    risk_rs = k * CUSHION            ->  lots = floor(risk_rs / (stop_pts * LOT))
Size grows out of REALISED profit and shrinks to zero as equity approaches the floor, so the 20% cap is
enforced by construction rather than by forecast. Two floor policies tested:
    ratchet  : FLOOR only ever rises with HWM (never lowered) - strictest
    reset    : FLOOR = current HWM*(1-b) recomputed, so it falls back after a recovery
CONTROL, always reported alongside: FIXED 1 LOT FOREVER (what the dossier numbers use).

WHY A SIZING LAYER CANNOT BE EXPECTED TO ADD ALPHA (stated so results are read correctly):
already measured on this flagship - leverage does NOT improve risk-adjusted return (Calmar flat
0.66-1.36 across a 10x size range; Sharpe PEAKS near 0.75% risk/trade then DEGRADES). So the honest job
of this layer is (a) cap drawdown, (b) compound realised profit. Any Sharpe/Calmar gain would be
suspicious, not gratifying.

HONESTY REQUIREMENTS BUILT IN
 - realised maxDD vs the 20% budget, and BREACH count/size (a "hard" cap that silently breaches is worse
   than an honest soft one; gaps and overnight moves can jump the floor).
 - drawdown DURATION as well as depth (the book's weakest dimension: Book A 325d, Book B 576d underwater).
 - era splits pre-2019 / 2019-2024 / 2024+ (two known structural breaks).
 - cost scales with lots: the CSV `cost` col is for 1 lot; brokerage (Rs40) is flat, the rest is
   proportional to turnover, so cost(lots) = (cost_1lot - 40)*lots + 40.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
R = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
         r"\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results")
OUT = Path(__file__).parent
OUT.mkdir(parents=True, exist_ok=True)

LOT, CARRY_M = 75, 0.005
CAP0 = 10_00_000.0
MDD_BUDGET = 0.20
MARGIN_PCT = 0.10
MAX_LOTS = 25
FLAT_BROK = 40.0

# ---------------------------------------------------------------- load flagship trades
t = pd.read_csv(R / "SWEEP_11YR_20260729" / "trades_E_swing3_trail60_1lot.csv")
t["date"] = pd.to_datetime(t["date"])
t = t.sort_values("t").reset_index(drop=True)
carry = t["entry"] * (CARRY_M / 30.0) * np.maximum(t["hold_min"] / 375.0, 0.5)
t["pts_adj"] = t["gross_pts"] - np.sign(t["dir"]) * carry     # longs pay, shorts receive
t["cost1"] = t["cost"]
STOP_PTS = 60.0


def dd_stats(eq: pd.Series):
    pk = eq.cummax()
    dd = (eq - pk) / pk
    under = (dd < -1e-9).values
    longest = cur = 0
    for u in under:
        cur = cur + 1 if u else 0
        longest = max(longest, cur)
    return float(dd.min()), int(longest)


def run(policy: str, k: float = 0.15, profit_step: float | None = None):
    """policy: fixed1 | ratchet | reset | profit_step"""
    eq = CAP0
    hwm = CAP0
    floor_r = CAP0 * (1 - MDD_BUDGET)
    rows = []
    for _, r in t.iterrows():
        if policy == "fixed1":
            lots = 1
        elif policy == "profit_step":
            # add 1 lot per `profit_step` of realised profit above start; never below 1; never add in DD
            gain = max(eq - CAP0, 0.0)
            lots = 1 + int(gain // profit_step)
            if eq < hwm:                       # in drawdown -> do not add size
                lots = min(lots, 1 + int(max(hwm - CAP0, 0.0) // profit_step))
                lots = max(1, min(lots, 1 + int(gain // profit_step)))
        elif policy == "cppi_min1":
            # BUGFIX VARIANT: cushion sizing but NEVER below 1 lot, so the sleeve can recover.
            # The pure-floor version (below) permanently freezes at 0 lots the first time cushion
            # hits zero -- equity can then never grow, so the strategy is dead forever. That is
            # correct CPPI behaviour for a capital guarantee but useless for a trading sleeve.
            fl = hwm * (1 - MDD_BUDGET)
            cushion = eq - fl
            lots = max(1, int(np.floor(k * cushion / (STOP_PTS * LOT)))) if cushion > 0 else 1
        elif policy == "cppi_trailing_hwm":
            # "reset" done properly: reference peak is a TRAILING 1-yr high, not the all-time HWM.
            # NOTE the earlier defect: because all-time HWM never DECREASES, a floor defined off it
            # never decreases either -- so my "reset" and "ratchet" variants were mathematically
            # IDENTICAL. A trailing peak is what actually lets the floor fall back after a recovery.
            recent = [q["equity"] for q in rows[-250:]] or [CAP0]
            ref = max(max(recent), CAP0)
            cushion = eq - ref * (1 - MDD_BUDGET)
            lots = max(1, int(np.floor(k * cushion / (STOP_PTS * LOT)))) if cushion > 0 else 1
        else:
            fl = floor_r if policy == "ratchet" else hwm * (1 - MDD_BUDGET)
            cushion = eq - fl
            if cushion <= 0:
                rows.append({"date": r["date"], "lots": 0, "net": 0.0, "equity": eq,
                             "cushion": cushion}); continue
            lots = int(np.floor(k * cushion / (STOP_PTS * LOT)))
        lots = max(0, min(lots, MAX_LOTS,
                          int(np.floor(eq / max(r["notional"] * MARGIN_PCT, 1)))))
        if lots < 1:
            rows.append({"date": r["date"], "lots": 0, "net": 0.0, "equity": eq,
                         "cushion": eq - hwm * (1 - MDD_BUDGET)}); continue
        gross = r["pts_adj"] * LOT * lots
        cost = (r["cost1"] - FLAT_BROK) * lots + FLAT_BROK
        net = gross - cost
        eq += net
        hwm = max(hwm, eq)
        floor_r = max(floor_r, hwm * (1 - MDD_BUDGET))
        rows.append({"date": r["date"], "lots": lots, "net": net, "equity": eq,
                     "cushion": eq - hwm * (1 - MDD_BUDGET)})
        if eq <= 0:
            break
    d = pd.DataFrame(rows)
    return d


def metrics(d: pd.DataFrame, label: str, lo=None, hi=None) -> dict:
    x = d.copy()
    if lo is not None:
        x = x[(x.date >= lo) & (x.date <= hi)]
    if len(x) < 20 or x["net"].abs().sum() == 0:
        return {"policy": label, "n": len(x)}
    daily = x.groupby("date")["net"].sum().sort_index()
    # equity path: continue from the true tracked path so DD is on the real curve
    start = float(x["equity"].iloc[0] - x["net"].iloc[0])
    eq = start + daily.cumsum()
    mdd, longest = dd_stats(eq)
    yrs = max((daily.index.max() - daily.index.min()).days / 365.25, .01)
    end = float(eq.iloc[-1])
    cagr = (end / start) ** (1 / yrs) - 1 if end > 0 and start > 0 else np.nan
    r_ = daily / start
    sh = float(r_.mean() / r_.std() * np.sqrt(252)) if r_.std() > 0 else np.nan
    mo = daily.resample("ME").sum()
    w, l = daily[daily > 0], daily[daily <= 0]
    # breach of the 20% budget measured on the running HWM of THIS path
    pk = eq.cummax()
    ddser = (eq - pk) / pk
    breaches = int((ddser < -MDD_BUDGET).sum())
    worst_breach = float(ddser.min() + MDD_BUDGET) if breaches else 0.0
    return {"policy": label, "n": int(len(x)), "years": round(yrs, 2),
            "median_lots": int(x[x.lots > 0]["lots"].median()) if (x.lots > 0).any() else 0,
            "max_lots": int(x["lots"].max()), "zero_lot_trades": int((x.lots == 0).sum()),
            "end_equity": round(end), "CAGR_pct": round(100 * cagr, 2) if np.isfinite(cagr) else None,
            "maxDD_pct": round(100 * mdd, 2),
            "budget_breach_days": breaches,
            "worst_excess_over_budget_pp": round(100 * worst_breach, 2),
            "longest_DD_days": longest,
            "Calmar": round(float(cagr / abs(mdd)), 2) if mdd and np.isfinite(cagr) else None,
            "Sharpe": round(sh, 2),
            "PF": round(float(w.sum() / abs(l.sum())), 2) if l.sum() else None,
            "month_win_pct": round(100 * float((mo > 0).mean()), 1),
            "worst_month_pct_of_start": round(100 * float(mo.min() / start), 2)}


CONFIGS = [
    ("fixed1_CONTROL", dict(policy="fixed1")),
    ("cppi_ratchet_k0.10", dict(policy="ratchet", k=0.10)),
    ("cppi_ratchet_k0.15", dict(policy="ratchet", k=0.15)),
    ("cppi_ratchet_k0.25", dict(policy="ratchet", k=0.25)),
    ("cppi_reset_k0.15", dict(policy="reset", k=0.15)),
    ("cppi_reset_k0.25", dict(policy="reset", k=0.25)),
    ("profit_step_5L", dict(policy="profit_step", profit_step=5_00_000.0)),
    ("cppi_min1_k0.15", dict(policy="cppi_min1", k=0.15)),
    ("cppi_min1_k0.25", dict(policy="cppi_min1", k=0.25)),
    ("cppi_trailHWM_k0.15", dict(policy="cppi_trailing_hwm", k=0.15)),
    ("cppi_trailHWM_k0.25", dict(policy="cppi_trailing_hwm", k=0.25)),
]

ERAS = [("FULL_2015_2026", None, None),
        ("pre2019", pd.Timestamp("2015-01-01"), pd.Timestamp("2018-12-31")),
        ("2019_2024", pd.Timestamp("2019-01-01"), pd.Timestamp("2024-09-30")),
        ("post_Oct2024", pd.Timestamp("2024-10-01"), pd.Timestamp("2026-12-31"))]

all_rows = []
paths = {}
for name, kw in CONFIGS:
    d = run(**kw)
    paths[name] = d
    for era, lo, hi in ERAS:
        m = metrics(d, name, lo, hi)
        m["era"] = era
        all_rows.append(m)

res = pd.DataFrame(all_rows)
res.to_csv(OUT / "dyn_sizing_results.csv", index=False)

show = ["policy", "median_lots", "max_lots", "zero_lot_trades", "CAGR_pct", "maxDD_pct",
        "budget_breach_days", "worst_excess_over_budget_pp", "longest_DD_days", "Calmar",
        "Sharpe", "PF", "month_win_pct"]
for era, _, _ in ERAS:
    sub = res[res.era == era]
    if sub["n"].max() < 20:
        continue
    print("=" * 132)
    print(f"ERA: {era}    (MDD budget = {int(100*MDD_BUDGET)}%,  flagship = SWEEP_E, start Rs{CAP0:,.0f})")
    print("=" * 132)
    print(sub[[c for c in show if c in sub.columns]].to_string(index=False))
    print()

# lot-growth trace for the recommended policy
for nm in ("cppi_min1_k0.15", "cppi_trailHWM_k0.25"):
    d = paths[nm]
    yr = d.assign(y=d.date.dt.year).groupby("y").agg(
        med_lots=("lots", "median"), max_lots=("lots", "max"),
        zero=("lots", lambda s: int((s == 0).sum())),
        eq_end=("equity", "last"), net=("net", "sum")).round(0)
    print(f"--- yearly lot trace: {nm} ---")
    print(yr.to_string())
    print()

print("wrote dyn_sizing_results.csv")
