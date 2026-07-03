"""Forward Factor calendar v2 — CORRECT measurement.

Fixes over v1: (a) normalize P&L by the BACK-leg premium (stable denom) NOT the net debit
(which -> 0 exactly when FF is high, inflating returns); (b) keep ALL FF trades; (c) close
BOTH legs at market ~2 sessions before front expiry (not intrinsic); (d) realistic per-leg
slippage. Structure = SELL front / BUY back calendar (net long calendar). Sweep FF threshold,
single vs double (CE+PE) calendar, 2 slippage levels. Also builds an equity curve.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import dispersion_strategy as ds
from forward_factor_strategy import forward_vol

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
SOPT = ds.SOPT
SPLIT = dt.date(2024, 12, 31)
CHECKPOINTS = [30, 25, 20, 15, 12]     # trading-days-before-M1 to scan for peak FF


def leg_px(df, k, o, day):
    return ds.price_asof(df, k, o, day)


def run_once(start, end):
    C = ds.stock_close()
    stocks = sorted({p.name for p in SOPT.iterdir() if p.is_dir()})
    recs = []
    for sym in stocks:
        if sym not in C.columns:
            continue
        cser = C[sym].dropna()
        exp_files = {dt.date.fromisoformat(p.stem): p for p in (SOPT / sym).glob("*.parquet")}
        exps = sorted(exp_files)
        for i in range(len(exps) - 1):
            m1_exp, m2_exp = exps[i], exps[i + 1]
            if not (start <= m1_exp <= end):
                continue
            try:
                d1 = pq.read_table(exp_files[m1_exp]).to_pandas(); d1["trading_day"] = d1["trading_day"].astype(str)
                d2 = pq.read_table(exp_files[m2_exp]).to_pandas(); d2["trading_day"] = d2["trading_day"].astype(str)
            except Exception:
                continue
            tdays1 = sorted(pd.to_datetime(d1["trading_day"].unique()))
            tdays2 = sorted(pd.to_datetime(d2["trading_day"].unique()))
            if len(tdays1) < 12 or not tdays2:
                continue
            m2_start = tdays2[0].date()
            # peak-FF entry
            best = None
            for lead in CHECKPOINTS:
                if lead + 1 >= len(tdays1):
                    continue
                cand = max(tdays1[-lead - 1].date(), m2_start)
                if cand >= m1_exp:
                    continue
                spot = cser.asof(pd.Timestamp(cand))
                if not np.isfinite(spot):
                    continue
                iv1 = ds.atm_iv_asof(d1, spot, cand, m1_exp)
                iv2 = ds.atm_iv_asof(d2, spot, cand, m2_exp)
                if iv1 is None or iv2 is None:
                    continue
                fv = forward_vol(iv1, max((m1_exp - cand).days / 365, 1e-4),
                                 iv2, max((m2_exp - cand).days / 365, 1e-4))
                if not fv or fv <= 0:
                    continue
                ff = (iv1 - fv) / fv
                if best is None or ff > best[0]:
                    best = (ff, cand, spot, iv1, iv2)
            if best is None:
                continue
            ff, entry, spot, iv1, iv2 = best
            dte1 = (m1_exp - entry).days
            # exit ~2 sessions before front expiry
            exit_cands = [d.date() for d in tdays1 if entry < d.date() < m1_exp]
            if len(exit_cands) < 2:
                continue
            exit_day = exit_cands[-2]     # ~2 sessions before expiry
            common = sorted(set(d1["strike"].unique()) & set(d2["strike"].unique()))
            if not common:
                continue
            k = min(common, key=lambda x: abs(x - spot))

            rec = {"sym": sym, "m1_exp": m1_exp, "entry": entry, "strike": k, "ff": ff,
                   "dte1": dte1, "dte2": (m2_exp - entry).days}
            ok = True
            for side in ("CE", "PE"):
                f_e = leg_px(d1, k, side, entry); b_e = leg_px(d2, k, side, entry)
                f_x = leg_px(d1, k, side, exit_day); b_x = leg_px(d2, k, side, exit_day)
                if not all(np.isfinite(x) and x > 0 for x in (f_e, b_e, f_x, b_x)):
                    ok = False; break
                rec[f"{side}_fe"] = f_e; rec[f"{side}_be"] = b_e
                rec[f"{side}_fx"] = f_x; rec[f"{side}_bx"] = b_x
            if not ok:
                continue
            recs.append(rec)
    return pd.DataFrame(recs)


def pnl(rec, sides, slip):
    """P&L per spread (rupees) and back-premium, for a calendar: sell front / buy back."""
    total_pnl = 0.0; back_prem = 0.0
    for s in sides:
        f_e, b_e = rec[f"{s}_fe"], rec[f"{s}_be"]
        f_x, b_x = rec[f"{s}_fx"], rec[f"{s}_bx"]
        # sell front @ entry (recv -slip), buy back @ entry (pay +slip)
        # buy front @ exit  (pay +slip),  sell back @ exit (recv -slip)
        total_pnl += (f_e * (1 - slip) - b_e * (1 + slip)
                      - f_x * (1 + slip) + b_x * (1 - slip))
        back_prem += b_e
    return total_pnl, back_prem


def evaluate(D, sides, slip, ff_min):
    sub = D[D["ff"] >= ff_min].copy()
    if sub.empty:
        return None
    res = sub.apply(lambda r: pnl(r, sides, slip), axis=1, result_type="expand")
    sub["pnl"] = res[0]; sub["back_prem"] = res[1]
    sub["ret"] = sub["pnl"] / sub["back_prem"]        # STABLE denominator
    b = sub[pd.to_datetime(sub["entry"]).dt.date <= SPLIT]
    f = sub[pd.to_datetime(sub["entry"]).dt.date > SPLIT]
    return dict(n=len(sub), mean=sub["ret"].mean(), med=sub["ret"].median(),
                hit=(sub["ret"] > 0).mean(), build=b["ret"].mean() if len(b) else np.nan,
                fwd=f["ret"].mean() if len(f) else np.nan,
                pnl_pts=sub["pnl"].mean(), sub=sub)


if __name__ == "__main__":
    D = run_once(dt.date(2021, 1, 1), dt.date(2026, 6, 2))
    D.to_parquet(ROOT / "intraday_options_strategy/buying/forward_factor_v2.parquet")
    print(f"[events] {len(D)} calendar candidates | avg dte1={D['dte1'].mean():.0f} dte2={D['dte2'].mean():.0f} "
          f"| FF med {D['ff'].median():.2f}")
    for slip in (0.005, 0.015):
        print(f"\n############## slippage {slip:.1%}/leg ##############")
        for struct, sides in [("single-CE calendar", ["CE"]), ("double calendar (CE+PE)", ["CE", "PE"])]:
            print(f"\n--- {struct} --- (ret = P&L / back-leg premium; stable denom)")
            print(f"  {'FF>=':>6} {'n':>4} {'mean':>7} {'med':>7} {'hit':>5} {'build':>7} {'fwd':>7} {'pnl_pts':>8}")
            for T in [0.0, 0.10, 0.20, 0.30, 0.50]:
                r = evaluate(D, sides, slip, T)
                if r is None or r["n"] < 8:
                    continue
                print(f"  {T:>6.2f} {r['n']:>4d} {r['mean']:>+7.1%} {r['med']:>+7.1%} {r['hit']:>5.0%} "
                      f"{r['build']:>+7.1%} {r['fwd']:>+7.1%} {r['pnl_pts']:>+8.1f}")
