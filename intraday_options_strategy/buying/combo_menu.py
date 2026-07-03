"""Same-month FUTURE/stock + OPTIONS combo menu on Indian single-stock options.

Enter ~30 DTE, hold to monthly expiry (all legs same expiry -> no cross-month liquidity issue).
Underlying ('future') proxied by the stock (basis ~ small carry). P&L as % of spot, with
option slippage + stock slippage. Build 2021-2024H1 / forward 2024H2-2026.

Structures tested:
  covered_call     : long stock + short ~3% OTM call        (buy-write, short-vol+drift)
  short_put_csp    : short ~3% OTM put (cash-secured)        (synthetic covered call)
  protective_put   : long stock + long ~3% OTM put          (insured long)
  collar           : long stock + short OTM call + long OTM put
  long_call        : long ATM call                          (long delta+vol)
  short_call       : short ATM call                         (short delta+vol)
  call_ratio_back  : buy 2 OTM calls + sell 1 ATM call       (net long convexity, user's idea)
  put_ratio_back   : buy 2 OTM puts  + sell 1 ATM put
  call_ratio_spread: sell 2 OTM calls + buy 1 ATM call       (net short, inverse of above)
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import dispersion_strategy as ds

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
SOPT = ds.SOPT
OSLIP = 0.015      # option slippage per leg
SSLIP = 0.001      # stock slippage per side
OTM = 0.03         # OTM distance
SPLIT = dt.date(2024, 6, 30)


def near(strikes, target):
    return min(strikes, key=lambda x: abs(x - target)) if strikes else None


def run(start, end):
    C = ds.stock_close()
    stocks = sorted({p.name for p in SOPT.iterdir() if p.is_dir()})
    recs = []
    for sym in stocks:
        if sym not in C.columns:
            continue
        cser = C[sym].dropna()
        for p in sorted((SOPT / sym).glob("*.parquet")):
            exp = dt.date.fromisoformat(p.stem)
            if not (start <= exp <= end):
                continue
            try:
                df = pq.read_table(p).to_pandas(); df["trading_day"] = df["trading_day"].astype(str)
            except Exception:
                continue
            tdays = sorted(pd.to_datetime(df["trading_day"].unique()))
            if len(tdays) < 8:
                continue
            target = exp - dt.timedelta(days=30)
            cands = [d for d in tdays if d.date() >= target and d.date() < exp]
            entry = (cands[0] if cands else tdays[0]).date()
            spot_e = cser.asof(pd.Timestamp(entry)); spot_x = cser.asof(pd.Timestamp(exp))
            if not (np.isfinite(spot_e) and np.isfinite(spot_x) and spot_e > 0):
                continue
            strikes = sorted(df["strike"].unique())
            k_atm = near(strikes, spot_e)
            k_oc = near(strikes, spot_e * (1 + OTM))
            k_op = near(strikes, spot_e * (1 - OTM))
            if None in (k_atm, k_oc, k_op) or k_oc <= k_atm or k_op >= k_atm:
                continue

            def px(k, o):
                return ds.price_asof(df, k, o, entry)
            # entry option prices
            c_atm, p_atm = px(k_atm, "CE"), px(k_atm, "PE")
            c_oc, p_op = px(k_oc, "CE"), px(k_op, "PE")
            if not all(np.isfinite(x) and x > 0 for x in (c_atm, p_atm, c_oc, p_op)):
                continue
            # intrinsics at expiry
            def cintr(k):
                return max(0.0, spot_x - k)
            def pintr(k):
                return max(0.0, k - spot_x)
            stock_ret = spot_x - spot_e
            stk_cost = (spot_e + spot_x) * SSLIP     # round-trip stock slippage (pts)

            def sell(prem, intr):   # short option pnl (pts)
                return prem * (1 - OSLIP) - intr * (1 + OSLIP)
            def buy(prem, intr):    # long option pnl
                return intr * (1 - OSLIP) - prem * (1 + OSLIP)

            s = {}
            s["covered_call"] = (stock_ret - stk_cost) + sell(c_oc, cintr(k_oc))
            s["short_put_csp"] = sell(p_op, pintr(k_op))
            s["protective_put"] = (stock_ret - stk_cost) + buy(p_op, pintr(k_op))
            s["collar"] = (stock_ret - stk_cost) + sell(c_oc, cintr(k_oc)) + buy(p_op, pintr(k_op))
            s["long_call"] = buy(c_atm, cintr(k_atm))
            s["short_call"] = sell(c_atm, cintr(k_atm))
            s["call_ratio_back"] = 2 * buy(c_oc, cintr(k_oc)) + sell(c_atm, cintr(k_atm))
            s["put_ratio_back"] = 2 * buy(p_op, pintr(k_op)) + sell(p_atm, pintr(k_atm))
            s["call_ratio_spread"] = 2 * sell(c_oc, cintr(k_oc)) + buy(c_atm, cintr(k_atm))
            rec = {"sym": sym, "exp": exp, "entry": entry, "spot": spot_e}
            for name, pnl in s.items():
                rec[name] = pnl / spot_e     # % of spot
            recs.append(rec)
    return pd.DataFrame(recs)


if __name__ == "__main__":
    D = run(dt.date(2021, 1, 1), dt.date(2026, 6, 2))
    D.to_parquet(ROOT / "intraday_options_strategy/buying/combo_menu.parquet")
    print(f"[events] {len(D)} monthly combos, {D['exp'].min()}..{D['exp'].max()}\n")
    structs = ["covered_call", "short_put_csp", "protective_put", "collar", "long_call",
               "short_call", "call_ratio_back", "put_ratio_back", "call_ratio_spread"]
    print(f"  {'structure':20s} {'mean%spot':>10} {'median':>8} {'hit':>5} {'build':>8} {'fwd':>8} {'worst':>8}")
    rows = []
    for st in structs:
        x = D[st]; b = D[D["exp"] <= SPLIT][st]; f = D[D["exp"] > SPLIT][st]
        rows.append((st, x.mean(), f.mean()))
        print(f"  {st:20s} {x.mean():>+10.3%} {x.median():>+8.3%} {(x>0).mean():>5.0%} "
              f"{b.mean():>+8.3%} {f.mean():>+8.3%} {x.min():>+8.1%}")
    print("\nRanked by forward mean:")
    for st, m, fm in sorted(rows, key=lambda r: -r[2]):
        print(f"  {st:20s} all {m:+.3%} | fwd {fm:+.3%}")
