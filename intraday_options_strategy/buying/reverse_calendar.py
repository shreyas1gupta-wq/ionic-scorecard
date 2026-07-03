"""REVERSE double calendar on Indian stocks (user spec: buy 30DTE, sell 60DTE, ATM, CE+PE).

  BUY  near-month (M1, ~30 DTE) ATM straddle  (long near gamma/vega)
  SELL far-month  (M2, ~60 DTE) ATM straddle  (short far vega)  -> usually net CREDIT
Enter ~30 calendar days before M1 expiry (M1~30DTE, M2~60DTE). Exit at M1 expiry
(M1 settles intrinsic; buy back M2). P&L reported as % OF SPOT (stable denominator --
avoids the tiny-debit inflation that plagued the standard calendar). Also bucketed by
Forward Factor to see if the reverse calendar prefers LOW FF (near cheap vs forward).
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
SLIP = 0.02
SPLIT = dt.date(2024, 12, 31)
TARGET_DTE = 30      # enter when M1 has ~this many days to expiry (M2 ~ +30 more)


def straddle_asof(df, k, day):
    ce = ds.price_asof(df, k, "CE", day)
    pe = ds.price_asof(df, k, "PE", day)
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
            # entry ~TARGET_DTE calendar days before M1 expiry, and >= M2 listing
            target = m1_exp - dt.timedelta(days=TARGET_DTE)
            cands = [d for d in tdays1 if d.date() >= max(target, tdays2[0].date()) and d.date() < m1_exp]
            if not cands:
                continue
            entry_day = cands[0].date()
            dte1 = (m1_exp - entry_day).days
            dte2 = (m2_exp - entry_day).days
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
            # Forward Factor context (front=M1, back=M2)
            iv1 = ds.atm_iv_asof(d1, spot, entry_day, m1_exp)
            iv2 = ds.atm_iv_asof(d2, spot, entry_day, m2_exp)
            ff = np.nan
            if iv1 and iv2:
                fv = forward_vol(iv1, max(dte1/365, 1e-4), iv2, max(dte2/365, 1e-4))
                if fv and fv > 0:
                    ff = (iv1 - fv) / fv

            # exit at M1 expiry: M1 -> intrinsic, buy back M2
            spot_exp = cser.asof(pd.Timestamp(m1_exp))
            if not np.isfinite(spot_exp):
                continue
            m1_x = abs(spot_exp - k)                       # long straddle intrinsic at expiry
            m2_x = straddle_asof(d2, k, m1_exp)
            if m2_x is None:
                continue
            # P&L per unit: long M1 (buy@paid, sell@intrinsic) + short M2 (sell@recd, buyback@cost)
            paid = m1_e * (1 + SLIP)
            recd = m2_e * (1 - SLIP)
            m1_out = m1_x * (1 - SLIP)
            m2_out = m2_x * (1 + SLIP)
            pnl_pts = (m1_out - paid) + (recd - m2_out)
            recs.append({"sym": sym, "m1_exp": m1_exp, "entry": entry_day, "strike": k,
                        "dte1": dte1, "dte2": dte2, "spot": spot, "ff": ff,
                        "net_credit": recd - paid, "pnl_pts": pnl_pts,
                        "pnl_pct_spot": pnl_pts / spot})
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
    D.to_parquet(ROOT / "intraday_options_strategy/buying/reverse_calendar.parquet")
    print(f"[events] {len(D)} reverse-calendar trades, {D['entry'].min()}..{D['entry'].max()}")
    print(f"[dte]   avg dte1={D['dte1'].mean():.0f} dte2={D['dte2'].mean():.0f} | avg net_credit(pts)={D['net_credit'].mean():+.1f}")
    print()
    rep(D, "ALL reverse double-calendars")
    print("\n=== by Forward Factor bucket (does reverse cal prefer LOW FF = near cheap?) ===")
    Dff = D.dropna(subset=["ff"])
    Dff["ffb"] = pd.qcut(Dff["ff"], 4, labels=["Q1 lowest FF", "Q2", "Q3", "Q4 highest FF"])
    for b in ["Q1 lowest FF", "Q2", "Q3", "Q4 highest FF"]:
        rep(Dff[Dff["ffb"] == b], b)
    print("\n=== reference: mean absolute P&L in option points/unit ===")
    print(f"  mean pnl_pts {D['pnl_pts'].mean():+.2f}  median {D['pnl_pts'].median():+.2f}  "
          f"(short-vol/short-far side would flip sign)")

    # ---- P&L equity graph (fixed notional per trade, booked on M1 expiry) ----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    CAP = 3_00_000.0
    NOTIONAL = 30_000.0     # fixed rupee notional per reverse-calendar (long-straddle scale)
    D2 = D.sort_values("m1_exp").copy()
    D2["pnl_rs"] = D2["pnl_pct_spot"] * NOTIONAL
    daily = D2.groupby("m1_exp")["pnl_rs"].sum()
    eq_long = CAP + daily.cumsum()                    # the reverse calendar (buy near / sell far)
    eq_short = CAP - daily.cumsum() + (CAP - (CAP))   # its inverse (sell near / buy far = std calendar)
    eq_short = CAP - (eq_long - CAP)
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(pd.to_datetime(eq_long.index), eq_long.values, lw=1.5, color="#d62728",
            label="Reverse calendar (BUY 30DTE / SELL 60DTE)")
    ax.plot(pd.to_datetime(eq_short.index), eq_short.values, lw=1.3, color="#1f77b4", ls="--",
            label="Inverse (SELL near / BUY far)")
    ax.axhline(CAP, color="black", lw=0.6, alpha=0.4)
    ax.axvline(pd.Timestamp(SPLIT), color="gray", ls=":", lw=1)
    ax.text(pd.Timestamp(SPLIT), ax.get_ylim()[0], " fwd >", color="gray", fontsize=9)
    ax.set_title("Reverse double-calendar on Indian stocks (buy near / sell far straddle)",
                 fontsize=12, fontweight="bold")
    ax.set_ylabel(f"Equity (Rs., {NOTIONAL:,.0f}/trade notional)")
    ax.legend(fontsize=9)
    fig.autofmt_xdate(); fig.tight_layout()
    out = ROOT / "intraday_options_strategy/buying/reverse_calendar_pnl.png"
    fig.savefig(out, dpi=130)
    tot = daily.sum()
    print(f"\n[equity] reverse-cal net Rs.{tot:,.0f} on Rs.{CAP:,.0f} ({tot/CAP:+.1%}); "
          f"inverse would be {-tot/CAP:+.1%}")
    print(f"saved graph -> {out}")
