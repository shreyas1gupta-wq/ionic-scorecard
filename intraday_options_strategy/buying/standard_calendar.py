"""STANDARD double calendar (opposite of reverse): SELL near straddle / BUY far straddle.
Same universe/timing/measurement as reverse_calendar.py for a true apples-to-apples compare.
Slippage is applied in the CORRECT direction on every leg (NOT a sign-flip of the reverse).
Net debit position (far costs more than near credit). Exit at near expiry: near settles
intrinsic, far sold back. P&L as % of spot. + P&L graph.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import dispersion_strategy as ds
from forward_factor_strategy import forward_vol

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
SOPT = ds.SOPT
SLIP = 0.02
SPLIT = dt.date(2024, 12, 31)
TARGET_DTE = 30


def straddle_asof(df, k, day):
    ce = ds.price_asof(df, k, "CE", day); pe = ds.price_asof(df, k, "PE", day)
    if not (np.isfinite(ce) and np.isfinite(pe) and ce > 0 and pe > 0):
        return None
    return ce + pe


def run(start, end):
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
            if len(tdays1) < 10 or not tdays2:
                continue
            target = m1_exp - dt.timedelta(days=TARGET_DTE)
            cands = [d for d in tdays1 if d.date() >= max(target, tdays2[0].date()) and d.date() < m1_exp]
            if not cands:
                continue
            entry_day = cands[0].date()
            dte1 = (m1_exp - entry_day).days; dte2 = (m2_exp - entry_day).days
            spot = cser.asof(pd.Timestamp(entry_day))
            if not np.isfinite(spot) or spot <= 0:
                continue
            common = sorted(set(d1["strike"].unique()) & set(d2["strike"].unique()))
            if not common:
                continue
            k = min(common, key=lambda x: abs(x - spot))
            m1_e = straddle_asof(d1, k, entry_day)
            m2_e = straddle_asof(d2, k, entry_day)
            if m1_e is None or m2_e is None:
                continue
            iv1 = ds.atm_iv_asof(d1, spot, entry_day, m1_exp)
            iv2 = ds.atm_iv_asof(d2, spot, entry_day, m2_exp)
            ff = np.nan
            if iv1 and iv2:
                fv = forward_vol(iv1, max(dte1 / 365, 1e-4), iv2, max(dte2 / 365, 1e-4))
                if fv and fv > 0:
                    ff = (iv1 - fv) / fv
            spot_exp = cser.asof(pd.Timestamp(m1_exp))
            if not np.isfinite(spot_exp):
                continue
            m1_x = abs(spot_exp - k)                 # near settles intrinsic
            m2_x = straddle_asof(d2, k, m1_exp)
            if m2_x is None:
                continue
            # STANDARD: sell near (recv), buy far (pay); exit: buy back near intrinsic, sell far
            recd = m1_e * (1 - SLIP)                  # sell near straddle
            paid = m2_e * (1 + SLIP)                  # buy far straddle
            near_close = m1_x * (1 + SLIP)            # buy back near at intrinsic
            far_out = m2_x * (1 - SLIP)               # sell far
            pnl_pts = (recd - near_close) + (far_out - paid)
            recs.append({"sym": sym, "m1_exp": m1_exp, "entry": entry_day, "strike": k,
                        "dte1": dte1, "dte2": dte2, "spot": spot, "ff": ff,
                        "net_debit": paid - recd, "pnl_pts": pnl_pts, "pnl_pct_spot": pnl_pts / spot})
    return pd.DataFrame(recs)


def rep(sub, name):
    if len(sub) < 8:
        print(f"  {name:34s}: n={len(sub)} (too few)"); return
    b = sub[sub["entry"] <= SPLIT]; f = sub[sub["entry"] > SPLIT]
    print(f"  {name:34s}: pnl/spot ALL {sub['pnl_pct_spot'].mean():+.3%} med {sub['pnl_pct_spot'].median():+.3%} "
          f"hit {(sub['pnl_pct_spot']>0).mean():.0%} n={len(sub):4d} | BUILD {b['pnl_pct_spot'].mean():+.3%} "
          f"| FWD {f['pnl_pct_spot'].mean():+.3%}")


if __name__ == "__main__":
    D = run(dt.date(2021, 1, 1), dt.date(2026, 6, 2))
    if D.empty:
        print("0 trades"); raise SystemExit
    D.to_parquet(ROOT / "intraday_options_strategy/buying/standard_calendar.parquet")
    print(f"[events] {len(D)} standard-calendar trades | avg dte1={D['dte1'].mean():.0f} dte2={D['dte2'].mean():.0f} "
          f"| avg net_debit(pts)={D['net_debit'].mean():+.1f}")
    print()
    rep(D, "ALL standard calendars (sell near/buy far)")
    print("\n=== by Forward Factor bucket (does it prefer HIGH FF = near rich)? ===")
    Dff = D.dropna(subset=["ff"])
    if len(Dff) >= 20:
        Dff["ffb"] = pd.qcut(Dff["ff"], 4, labels=["Q1 lowest", "Q2", "Q3", "Q4 highest FF"])
        for b in ["Q1 lowest", "Q2", "Q3", "Q4 highest FF"]:
            rep(Dff[Dff["ffb"] == b], b)
    print(f"\nmean pnl_pts {D['pnl_pts'].mean():+.2f}  median {D['pnl_pts'].median():+.2f}")

    # equity graph
    CAP = 3_00_000.0; NOTIONAL = 30_000.0
    D2 = D.sort_values("m1_exp").copy(); D2["pnl_rs"] = D2["pnl_pct_spot"] * NOTIONAL
    daily = D2.groupby("m1_exp")["pnl_rs"].sum(); eq = CAP + daily.cumsum()
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(pd.to_datetime(eq.index), eq.values, lw=1.6, color="#15803d",
            label="Standard calendar (SELL near / BUY far)")
    ax.axhline(CAP, color="black", lw=0.6, alpha=0.4)
    ax.axvline(pd.Timestamp(SPLIT), color="gray", ls=":", lw=1)
    ax.text(pd.Timestamp(SPLIT), ax.get_ylim()[0], " fwd >", color="gray", fontsize=9)
    ax.set_title("Standard double-calendar on Indian stocks (SELL near / BUY far straddle)",
                 fontsize=12, fontweight="bold")
    ax.set_ylabel(f"Equity (Rs., {NOTIONAL:,.0f}/trade notional)"); ax.legend(fontsize=9)
    fig.autofmt_xdate(); fig.tight_layout()
    out = ROOT / "intraday_options_strategy/buying/standard_calendar_pnl.png"
    fig.savefig(out, dpi=130)
    print(f"\n[equity] net Rs.{daily.sum():,.0f} on Rs.{CAP:,.0f} ({daily.sum()/CAP:+.1%})")
    print(f"saved graph -> {out}")
