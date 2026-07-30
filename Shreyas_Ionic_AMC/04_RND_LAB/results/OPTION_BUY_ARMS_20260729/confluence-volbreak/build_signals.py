"""ARM 3 step 1: build every pre-registered signal cell and measure SIGNED SPOT MOVE
as a function of the number of stacked conditions.

Pre-registered in PRE_REGISTRATION.md (written before this ran).
Signal generators are REUSED VERBATIM from the sibling
EMA_INTRADAY_BUYING_20260729/signal_budget/measure_signal_budget.py -- nothing is
re-derived or re-tuned here.

Outputs
  signals/<cell>.csv          t,dir  (all dates; the option runner does the split)
  signed_move.json            signed-move stats per cell, build vs held-out forward
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent
SIGDIR = OUT / "signals"
SIGDIR.mkdir(exist_ok=True)

RESULTS = OUT.parent.parent                      # .../04_RND_LAB/results
SB = RESULTS / "EMA_INTRADAY_BUYING_20260729" / "signal_budget"
sys.path.insert(0, str(SB))
sys.path.insert(0, str(SB.parent))

import measure_signal_budget as M                # noqa: E402  (reuses stage1 helpers too)

BUILD_END = dt.date(2025, 12, 31)


# ---------------------------------------------------------------------------
def cumulative_buckets(long_stack: pd.DataFrame) -> dict[int, pd.DataFrame]:
    """">= k conditions" view. Retail designs are specified this way ("all of these must
    be true"), so report it alongside the clean "exactly k" comparison."""
    out = {}
    for k in sorted(long_stack["stack_count"].unique()):
        sub = long_stack[long_stack["stack_count"] >= k][["t", "dir"]]
        out[int(k)] = M.clip_entry_window(sub.copy())
    return out


def stack_long(bars15, st_flips, atr_exp_15, sweep_frames, sr_frames) -> pd.DataFrame:
    """Same construction as M.confluence_buckets but returns the long table so both
    'exactly k' and '>= k' views come from ONE definition."""
    frames = []
    named = [("supertrend", st_flips), ("atr_expand", atr_exp_15),
             ("sweep", pd.concat(sweep_frames, ignore_index=True) if sweep_frames else pd.DataFrame()),
             ("sr", pd.concat(sr_frames, ignore_index=True) if sr_frames else pd.DataFrame())]
    for name, df in named:
        if df is None or df.empty:
            continue
        d = df[["t", "dir"]].drop_duplicates()
        d["cond"] = name
        frames.append(d)
    long = pd.concat(frames, ignore_index=True).sort_values("t")
    bar_index = pd.DataFrame({"t15": bars15.index}).sort_values("t15")
    long = pd.merge_asof(long, bar_index, left_on="t", right_on="t15", direction="backward")
    long = long.dropna(subset=["t15"])
    grp = long.groupby(["t15", "dir"])["cond"].nunique().reset_index(name="stack_count")
    return grp.rename(columns={"t15": "t"})


def signed_move_cell(spot: pd.DataFrame, sig: pd.DataFrame, label: str) -> dict:
    """Signed spot move via the sibling script's own forward_stats/summarize_cell, so the
    numbers are directly comparable to the already-published signal-budget table."""
    if sig is None or sig.empty:
        return {"label": label, "n_build": 0, "n_forward": 0}
    s = sig.copy()
    s["date"] = pd.to_datetime(s["t"]).dt.date
    b, fw = s[s["date"] <= BUILD_END], s[s["date"] > BUILD_END]
    fb = M.forward_stats(spot, b) if len(b) else pd.DataFrame()
    ff = M.forward_stats(spot, fw) if len(fw) else pd.DataFrame()
    cb = M.summarize_cell(fb) if len(fb) else {"n": 0}
    cf = M.summarize_cell(ff) if len(ff) else {"n": 0}
    rec = {"label": label, "n_build": int(len(b)), "n_forward": int(len(fw)),
           "build": cb, "forward": cf}
    # the single number the k-curve is about: signed move to 15:25, build set
    for tag, cell in (("build", cb), ("forward", cf)):
        h = cell.get("horizons", {}).get("to15:25")
        rec[f"{tag}_to1525"] = h if h else None
    return rec


def main():
    spot = M.load_spot()
    print(f"[spot] {len(spot):,} 1-min bars {spot.index[0]} .. {spot.index[-1]}", flush=True)
    bars5 = M.resample(spot, "5min")
    bars15 = M.resample(spot, "15min")
    daily = M.daily_bars(spot)
    wk_lv, mo_lv = M.week_month_levels(daily)

    cells: dict[str, pd.DataFrame] = {}

    # --- volatility-state triggers (native timeframes as originally measured) ---
    cells["volbrk_orb_volfilter"] = M.orb_vol_filter(bars5)
    cells["volbrk_atr_expansion"] = M.atr_expansion(bars5)
    cells["volbrk_keltner_squeeze_release"] = M.keltner_squeeze_release(bars5)

    # --- condition families for the stack (all on 15-min bars) ---
    st15 = M.supertrend_flips(bars15, 10, 3)
    atr15 = M.atr_expansion(bars15)
    sweeps = M.sweep_signals(bars15)
    wk_brk, wk_rej = M.level_breakout_reject(bars15, wk_lv)
    mo_brk, mo_rej = M.level_breakout_reject(bars15, mo_lv)
    rn_brk, rn_rej = M.round_number_levels(bars15)
    sr_all = [wk_brk, wk_rej, mo_brk, mo_rej, rn_brk, rn_rej]

    # STACK-A : zero selection, exactly the sibling script's families
    longA = stack_long(bars15, st15, atr15, list(sweeps.values()), sr_all)
    for k in sorted(longA["stack_count"].unique()):
        cells[f"stackA_exact{int(k)}"] = M.clip_entry_window(
            longA[longA["stack_count"] == k][["t", "dir"]].copy())
    for k, df in cumulative_buckets(longA).items():
        cells[f"stackA_ge{k}"] = df

    # STACK-B : sweep family restricted to the two build-positive variants.
    # FLAGGED: this uses build-set knowledge (in-sample informed), robustness only.
    sweepB = [sweeps["priorday_reclaim"], sweeps["intraday_continue"]]
    longB = stack_long(bars15, st15, atr15, sweepB, sr_all)
    for k in sorted(longB["stack_count"].unique()):
        cells[f"stackB_exact{int(k)}"] = M.clip_entry_window(
            longB[longB["stack_count"] == k][["t", "dir"]].copy())

    # --- persist + measure signed move ---
    report = {"pre_registration": "PRE_REGISTRATION.md",
              "build_end": str(BUILD_END), "cells": {}, "cell_counts": {}}
    for label, sig in cells.items():
        if sig is None or sig.empty:
            print(f"[{label}] EMPTY", flush=True)
            continue
        s = sig.rename(columns={"dir": "direction"})[["t", "direction"]].sort_values("t")
        s.to_csv(SIGDIR / f"{label}.csv", index=False)
        rec = signed_move_cell(spot, sig, label)
        report["cells"][label] = rec
        report["cell_counts"][label] = {"build": rec["n_build"], "forward": rec["n_forward"]}
        h = rec.get("build_to1525") or {}
        print(f"[{label:24s}] n_build={rec['n_build']:6d} n_fwd={rec['n_forward']:5d} "
              f"to15:25 {h.get('mean_pct')}% {h.get('mean_pts')}pts t={h.get('t_nw')} "
              f"hit={h.get('hit')}", flush=True)

    (OUT / "signed_move.json").write_text(json.dumps(report, indent=2, default=str),
                                          encoding="utf-8")
    print("\n[done] signed_move.json + signals/*.csv written", flush=True)


if __name__ == "__main__":
    sys.exit(main())
