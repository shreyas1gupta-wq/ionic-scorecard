"""Does a hard STOP-LOSS cap the FF-calendar tail? Walk each trade's daily EOD MTM from
entry to scheduled exit; if MTM/back-premium <= -STOP on any close, exit that day (with
slippage). Compare tail/mean/hit vs no-stop, for several stop levels. FF>=0.25 (user floor).
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


def eod(df, k, otype):
    sub = df[(df["strike"] == k) & (df["option_type"] == otype)]
    s = sub.groupby("trading_day")["close"].last()
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


def run(stops=(0.30, 0.40, 0.50)):
    ff = pd.read_parquet(ROOT / "intraday_options_strategy/buying/forward_factor_v2.parquet")
    ff = ff[ff["ff"] >= 0.25].copy()
    ff["entry"] = pd.to_datetime(ff["entry"]); ff["m1_exp"] = pd.to_datetime(ff["m1_exp"])

    out = {s: [] for s in stops}; base = []
    for sym, g in ff.groupby("sym"):
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
                d2 = pq.read_table(exp_files[m2]).to_pandas(); d2["trading_day"] = d2["trading_day"].astype(str)
            except Exception:
                continue
            k = t["strike"]
            fce, bce = eod(d1, k, "CE"), eod(d2, k, "CE")
            f_e, b_e = t["CE_fe"], t["CE_be"]
            # scheduled exit values (from parquet) => baseline ret
            base_ret = (f_e * (1 - SLIP) - b_e * (1 + SLIP) - t["CE_fx"] * (1 + SLIP) + t["CE_bx"] * (1 - SLIP)) / b_e
            base.append(base_ret)
            # walk days strictly between entry and scheduled exit
            days = [d for d in fce.index if t["entry"] < d < t["m1_exp"]]
            for stop in stops:
                hit = None
                for d in days:
                    if d not in fce.index or d not in bce.index:
                        continue
                    fx, bx = fce.loc[d], bce.loc[d]
                    if not (np.isfinite(fx) and np.isfinite(bx)):
                        continue
                    mtm = (f_e * (1 - SLIP) - b_e * (1 + SLIP) - fx * (1 + SLIP) + bx * (1 - SLIP)) / b_e
                    if mtm <= -stop:
                        hit = mtm; break
                out[stop].append(hit if hit is not None else base_ret)
    return np.array(base), {s: np.array(v) for s, v in out.items()}


def stats(r, lab):
    r = r[np.isfinite(r)]
    print(f"  {lab:22s} n={len(r):3d} mean {r.mean():>+7.1%} hit {(r>0).mean():>4.0%} "
          f"worst {r.min():>+6.0%} p5 {np.quantile(r,.05):>+6.0%} blow<-50% {int((r<-0.5).sum())}")


if __name__ == "__main__":
    base, res = run()
    print("=== FF calendar: STOP-LOSS test (EOD MTM, FF>=0.25) ===")
    stats(base, "NO STOP (baseline)")
    for s in sorted(res):
        stats(res[s], f"stop @ -{s:.0%}")
