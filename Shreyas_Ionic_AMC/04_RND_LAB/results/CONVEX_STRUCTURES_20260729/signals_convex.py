"""Signal loaders for the convex-structures arm. REUSES the sweep detector from
EMA_INTRADAY_BUYING_20260729/signal_budget/measure_signal_budget.py (per task instruction) --
does not reimplement sweep logic. Collapses each trigger to ONE signal per calendar day
(first qualifying bar) since these gate multi-day option structures, not intraday scalps.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

SIGBUD_DIR = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
                   r"\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\EMA_INTRADAY_BUYING_20260729"
                   r"\signal_budget")
sys.path.insert(0, str(SIGBUD_DIR))
from measure_signal_budget import sweep_signals  # noqa: E402
from stage1_signal_test import load_spot, resample  # noqa: E402


def daily_first_signals(label: str) -> pd.DataFrame:
    """label in {'priorday_reclaim','intraday_continue'} -> DataFrame[date, t, dir],
    ONE row per calendar day (first qualifying 15-min bar that day)."""
    spot = load_spot()
    bars15 = resample(spot, "15min")
    sweeps = sweep_signals(bars15)
    sig = sweeps[label].copy()
    if sig.empty:
        return sig
    sig["date"] = pd.to_datetime(sig["t"]).dt.date
    sig = sig.sort_values("t").groupby("date", as_index=False).first()
    return sig[["date", "t", "dir"]].reset_index(drop=True)


if __name__ == "__main__":
    for lbl in ["priorday_reclaim", "intraday_continue"]:
        d = daily_first_signals(lbl)
        print(f"{lbl}: {len(d)} signal-days, dir+1={int((d['dir']>0).sum())} "
              f"dir-1={int((d['dir']<0).sum())}, range {d['date'].min()}..{d['date'].max()}")
