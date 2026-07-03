"""FAITHFUL 'Forward Factor' strategy (the real video: 6ao3uXE5KhU) on Indian stocks.

Forward volatility:  sigma_f^2 = (sigma2^2*T2 - sigma1^2*T1) / (T2-T1)
Forward Factor:       FF = (IV_front - IV_forward) / IV_forward
Entry: FF >= threshold (0.20 recommended in source; we sweep for India).
Structure: SELL front-month ATM (call, or straddle) + BUY back-month ATM, SAME strike
           -- a CALENDAR (short front vega, long back vega), NOT long-both-legs.
Exit: just before front-month expiry. No earnings link -- pure term-structure signal,
scanned at several lead times through each M1/M2 pair's life (finds earliest FF>=T).
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import dispersion_strategy as ds   # reuse debugged atm_iv_asof / price_asof / stock_close

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
SOPT = ds.SOPT
SLIP = 0.02
SPLIT = dt.date(2024, 12, 31)
CHECKPOINTS = [30, 25, 20, 15, 10]     # trading-days-before-M1-expiry to scan (earliest hit wins)


def forward_vol(iv1, T1, iv2, T2):
    num = (iv2**2) * T2 - (iv1**2) * T1
    denom = T2 - T1
    if denom <= 0 or num < 0:
        return None
    return np.sqrt(num / denom)


def run_once(start, end):
    """Single pass: for each (stock, M1/M2 pair) find the PEAK-FF checkpoint in the
    scanned window, compute the calendar trade return at that entry. Thresholds are
    applied post-hoc by filtering the returned dataframe on the 'ff' column."""
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
            if len(tdays1) <= max(CHECKPOINTS) or not tdays2:
                continue
            m2_start = tdays2[0].date()

            best = None   # (ff, day, spot, iv1, iv2)
            for lead in CHECKPOINTS:
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
                T1 = max((m1_exp - cand).days / 365.0, 1e-4)
                T2 = max((m2_exp - cand).days / 365.0, 1e-4)
                fv = forward_vol(iv1, T1, iv2, T2)
                if fv is None or fv <= 0:
                    continue
                ff = (iv1 - fv) / fv
                if best is None or ff > best[0]:
                    best = (ff, cand, spot, iv1, iv2)
            if best is None:
                continue
            ff_val, entry_day, spot_e, iv1_e, iv2_e = best

            avail1 = sorted(d1["strike"].unique()); avail2 = sorted(d2["strike"].unique())
            common = sorted(set(avail1) & set(avail2))
            if not common:
                continue
            k = min(common, key=lambda x: abs(x - spot_e))

            # SELL front, BUY back (calendar) -- both CE and PE tested (call-calendar, put-calendar)
            for side in ("CE", "PE"):
                p1_e = ds.price_asof(d1, k, side, entry_day)
                p2_e = ds.price_asof(d2, k, side, entry_day)
                if not (np.isfinite(p1_e) and np.isfinite(p2_e) and p1_e > 0 and p2_e > 0):
                    continue
                debit_entry = p1_e * (-1 + SLIP) + p2_e * (1 + SLIP)   # pay to open (sell front +recv, buy back -pay)
                # net debit = buy_back_cost - sell_front_credit (with slippage both ways)
                debit_entry = (p2_e * (1 + SLIP)) - (p1_e * (1 - SLIP))
                exit_day = m1_exp - dt.timedelta(days=1)               # close just before front expiry
                p1_x = ds.price_asof(d1, k, side, exit_day, max_stale=5)
                p2_x = ds.price_asof(d2, k, side, exit_day, max_stale=5)
                if not (np.isfinite(p1_x) and np.isfinite(p2_x)):
                    continue
                exit_val = (p2_x * (1 - SLIP)) - (p1_x * (1 + SLIP))    # sell back, buy back front to close
                if debit_entry <= 0:
                    continue
                ret = (exit_val - debit_entry) / abs(debit_entry)
                recs.append({"sym": sym, "m1_exp": m1_exp, "entry": entry_day, "side": side,
                            "strike": k, "ff": ff_val, "iv1": iv1_e, "iv2": iv2_e,
                            "debit": debit_entry, "ret": np.clip(ret, -3.0, 5.0)})
    return pd.DataFrame(recs)


def rep(sub, name, split=SPLIT):
    if len(sub) < 8:
        print(f"  {name:34s}: n={len(sub)} (too few)"); return
    b = sub[sub["entry"] <= split]; f = sub[sub["entry"] > split]
    print(f"  {name:34s}: ALL {sub['ret'].mean():+7.1%} med {sub['ret'].median():+7.1%} "
          f"hit {(sub['ret']>0).mean():.0%} n={len(sub):4d} | BUILD {b['ret'].mean():+7.1%} n={len(b)} "
          f"| FWD {f['ret'].mean():+7.1%} n={len(f)}")


if __name__ == "__main__":
    D = run_once(dt.date(2021, 1, 1), dt.date(2026, 6, 2))
    D.to_parquet(ROOT / "intraday_options_strategy/buying/forward_factor_all.parquet")
    print(f"[events] {len(D)} calendar candidates (peak-FF per pair), "
          f"{D['entry'].min() if len(D) else None}..{D['entry'].max() if len(D) else None}")
    print(f"[ff] median {D['ff'].median():.2f}  max {D['ff'].max():.2f}")

    for T in [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]:
        sub = D[D["ff"] >= T]
        print(f"\n=== FF>={T:.2f}  n={len(sub)} ===")
        rep(sub, "ALL (CE+PE calendar)")
        rep(sub[sub["side"] == "CE"], "call-calendar")
        rep(sub[sub["side"] == "PE"], "put-calendar")
