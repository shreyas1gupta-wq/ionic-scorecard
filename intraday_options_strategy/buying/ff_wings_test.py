"""Does a PRE-BOUGHT both-wing hedge cap the FF-calendar tail? For each FF>=0.25 trade,
in the FRONT month buy 1 far-OTM CE and 1 far-OTM PE (cheap crash/melt-up insurance) at
entry, sell them at the scheduled exit (~2 sessions before front expiry). Net return =
(calendar P&L + wing P&L) / back-premium. Sweep wing distance (5/10/15% OTM).
Compares hedged vs unhedged on mean / hit / WORST / blowups.
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
SLIP = 0.015


def run(wings=(0.05, 0.10, 0.15)):
    ff = pd.read_parquet(ROOT / "intraday_options_strategy/buying/forward_factor_v2.parquet")
    ff = ff[ff["ff"] >= 0.25].copy()
    ff["entry"] = pd.to_datetime(ff["entry"]); ff["m1_exp"] = pd.to_datetime(ff["m1_exp"])
    C = ds.stock_close()

    base = []; hedged = {w: [] for w in wings}
    for sym, g in ff.groupby("sym"):
        if sym not in C.columns:
            continue
        exp_files = {dt.date.fromisoformat(p.stem): p for p in (SOPT / sym).glob("*.parquet")}
        exps = sorted(exp_files)
        for _, t in g.iterrows():
            m1 = t["m1_exp"].date()
            if m1 not in exps:
                continue
            j = exps.index(m1)
            if j + 1 >= len(exps):
                continue
            m2 = exps[j + 1]
            try:
                d1 = pq.read_table(exp_files[m1]).to_pandas(); d1["trading_day"] = d1["trading_day"].astype(str)
            except Exception:
                continue
            tdays = sorted(pd.to_datetime(d1["trading_day"].unique()))
            fut = [d for d in tdays if t["entry"] < d < t["m1_exp"]]
            if len(fut) < 2:
                continue
            exit_day = fut[-2].date()
            k = t["strike"]
            b_e = t["CE_be"]
            base_ret = (t["CE_fe"] * (1 - SLIP) - b_e * (1 + SLIP)
                        - t["CE_fx"] * (1 + SLIP) + t["CE_bx"] * (1 - SLIP)) / b_e
            base.append(base_ret)
            spot = C[sym].asof(t["entry"])
            strikes = sorted(d1["strike"].unique())
            entry_d = t["entry"].date()
            for w in wings:
                kc = min(strikes, key=lambda x: abs(x - spot * (1 + w)))
                kp = min(strikes, key=lambda x: abs(x - spot * (1 - w)))
                ce_e = ds.price_asof(d1, kc, "CE", entry_d); ce_x = ds.price_asof(d1, kc, "CE", exit_day)
                pe_e = ds.price_asof(d1, kp, "PE", entry_d); pe_x = ds.price_asof(d1, kp, "PE", exit_day)
                if not all(np.isfinite(x) and x > 0 for x in (ce_e, ce_x, pe_e, pe_x)):
                    hedged[w].append(base_ret)      # couldn't price wing -> unhedged
                    continue
                # buy wings at entry (pay +slip), sell at exit (recv -slip)
                wing_pnl = (ce_x * (1 - SLIP) - ce_e * (1 + SLIP)) + (pe_x * (1 - SLIP) - pe_e * (1 + SLIP))
                hedged[w].append(base_ret + wing_pnl / b_e)
    return np.array(base), {w: np.array(v) for w, v in hedged.items()}


def stats(r, lab):
    r = r[np.isfinite(r)]
    print(f"  {lab:22s} n={len(r):3d} mean {r.mean():>+7.1%} hit {(r>0).mean():>4.0%} "
          f"worst {r.min():>+6.0%} p5 {np.quantile(r,.05):>+6.0%} blow<-50% {int((r<-0.5).sum())}")


if __name__ == "__main__":
    base, res = run()
    print("=== FF calendar: PRE-BOUGHT BOTH-WING hedge (front-month OTM CE+PE), FF>=0.25 ===")
    stats(base, "UNHEDGED (baseline)")
    for w in sorted(res):
        stats(res[w], f"+wings {w:.0%} OTM")
