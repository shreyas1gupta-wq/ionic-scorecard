"""ARM 2 (BEARISH) step 1: build the six pre-registered bearish trigger tables.

Trigger generators are REUSED VERBATIM from
  04_RND_LAB/results/EMA_INTRADAY_BUYING_20260729/signal_budget/measure_signal_budget.py
(imported, not copied) so the signals here are byte-identical to the ones whose spot-level
edge was measured earlier today. Only the bearish SUBSET is taken (see PRE_REGISTRATION.md
section 4). T6 is the registered FADE of an inverted signal: raw dir=+1 traded at -1.

Writes bearish_signals.csv (t, direction, tag) -> consumed by run_arm.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]                      # Shreyas_Ionic_AMC/
SIGDIR = ROOT / "04_RND_LAB" / "results" / "EMA_INTRADAY_BUYING_20260729" / "signal_budget"
STAGE1 = SIGDIR.parent
for p in (str(SIGDIR), str(STAGE1)):
    if p not in sys.path:
        sys.path.insert(0, p)

from stage1_signal_test import load_spot, resample          # noqa: E402
import measure_signal_budget as M                            # noqa: E402


def main() -> int:
    spot = load_spot()
    print(f"[spot] {len(spot):,} bars {spot.index[0]} .. {spot.index[-1]}", flush=True)
    bars15 = resample(spot, "15min")
    daily = M.daily_bars(spot)
    wk_lv, mo_lv = M.week_month_levels(daily)

    frames = []

    # ---- T1 sweep_priorday_reclaim, bearish half (swept ABOVE prior-day high, closed back below)
    sweeps = M.sweep_signals(bars15)
    pdr = sweeps["priorday_reclaim"]
    t1 = pdr[pdr["dir"] == -1][["t"]].copy()
    t1["direction"] = -1
    t1["tag"] = "T1_sweep_priorday_reclaim_bear"
    frames.append(t1)

    # ---- T6 sweep_intraday_reclaim FADE: raw dir=+1 rows traded at -1 (registered inversion)
    isr = sweeps["intraday_reclaim"]
    t6 = isr[isr["dir"] == 1][["t"]].copy()
    t6["direction"] = -1
    t6["tag"] = "T6_sweep_intraday_reclaim_FADE_bear"
    frames.append(t6)

    # ---- T2/T3 supertrend 15m bear flips
    for period, mult, tag in [(10, 3, "T2_supertrend15m_ATR10x3_bear"),
                              (14, 3, "T3_supertrend15m_ATR14x3_bear")]:
        st = M.supertrend_flips(bars15, period, mult)
        s = st[st["dir"] == -1][["t"]].copy()
        s["direction"] = -1
        s["tag"] = tag
        frames.append(s)

    # ---- T2b AMENDMENT-1 (2026-07-29, recorded in PRE_REGISTRATION.md before any option
    #      P&L was computed): the pre-registered 15-min supertrend bear flips are
    #      structurally near-absent (n=5 and n=1 -- 15m/ATR10x3 splits 165 bull vs 5 bear;
    #      15m/ATR14x3 splits 83 vs 1), so T2/T3 are UNTESTABLE, not failing. The 5-min
    #      supertrend was in the same prior measurement table (supertrend_5m_ATR10x3,
    #      n=1269, +0.0236%, t=2.76) and has 383 bear flips. Added on SIGNAL-COUNT grounds
    #      only -- a P&L-blind criterion.
    st5 = M.supertrend_flips(resample(spot, "5min"), 10, 3)
    s = st5[st5["dir"] == -1][["t"]].copy()
    s["direction"] = -1
    s["tag"] = "T2b_supertrend5m_ATR10x3_bear"
    frames.append(s)

    # ---- T4/T5 S/R rejections from resistance
    _, wk_rej = M.level_breakout_reject(bars15, wk_lv)
    _, mo_rej = M.level_breakout_reject(bars15, mo_lv)
    for df, tag in [(wk_rej, "T4_sr_week_reject_bear"), (mo_rej, "T5_sr_month_reject_bear")]:
        s = df[df["dir"] == -1][["t"]].copy()
        s["direction"] = -1
        s["tag"] = tag
        frames.append(s)

    out = pd.concat(frames, ignore_index=True).sort_values(["t", "tag"]).reset_index(drop=True)
    out["t"] = pd.to_datetime(out["t"])
    out.to_csv(HERE / "bearish_signals.csv", index=False)

    print("\n[signal counts]")
    out["date"] = out["t"].dt.date
    for tag, g in out.groupby("tag"):
        b = (pd.to_datetime(g["t"]) <= "2025-12-31").sum()
        print(f"  {tag:42s} total={len(g):6d}  build={b:6d}  forward={len(g)-b:5d}")
    print(f"  {'TOTAL':42s} total={len(out):6d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
