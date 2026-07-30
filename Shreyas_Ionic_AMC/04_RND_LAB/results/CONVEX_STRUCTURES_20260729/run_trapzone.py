"""Pure distributional trap-zone frequency: how often does NIFTY spot land BETWEEN a
1x2 ratio backspread's short strike and long strike at the scheduled exit point, using
the FULL weekly-expiry cadence (all 261 cycles) -- independent of whether any particular
signal fired. This is the market fact the task asked to quantify, not just note.
Spot-only, no option data, fast.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import lib_convex as lc  # noqa: E402

OUT = Path(__file__).parent
ENTRY_MIN_DTE, ENTRY_MAX_DTE = 4, 7
EXIT_DAYS_BEFORE_EXPIRY = 1
WIDTHS = [1, 2, 4]


def trading_calendar():
    idx = lc.spot_index()
    return sorted({d for d in idx.index.date})


def main():
    TCAL = trading_calendar()
    TCAL_POS = {d: i for i, d in enumerate(TCAL)}
    exps = lc.expiries()

    def exit_day_before(expiry, n):
        i = TCAL_POS.get(expiry)
        if i is None:
            cands = [d for d in TCAL if d <= expiry]
            if not cands:
                return None
            i = TCAL_POS[cands[-1]]
        j = i - n
        return TCAL[j] if j >= 0 else None

    seen = set()
    cycles = []
    for d in TCAL:
        exp = lc.near_weekly(d, ENTRY_MIN_DTE, ENTRY_MAX_DTE)
        if exp is None or exp in seen:
            continue
        cycles.append((d, exp))
        seen.add(exp)

    rows = []
    for entry_day, near_exp in cycles:
        t0 = lc.day_snapshot_time(entry_day, "09:20")
        spot_entry = lc.spot_close_asof(t0)
        if spot_entry is None:
            continue
        atm_k = lc.atm_strike(spot_entry)

        exit_day = exit_day_before(near_exp, EXIT_DAYS_BEFORE_EXPIRY)
        if exit_day is None:
            continue
        exit_spot_default = lc.spot_close_asof(lc.day_snapshot_time(exit_day, "15:15"))
        exit_spot_expiry = lc.spot_close_asof(lc.day_snapshot_time(near_exp, "15:29"))
        if exit_spot_default is None or exit_spot_expiry is None:
            continue

        for w in WIDTHS:
            for side, exit_spot, exit_label in [("default", exit_spot_default, f"exit_-{EXIT_DAYS_BEFORE_EXPIRY}d"),
                                                 ("expiry", exit_spot_expiry, "hold_to_expiry")]:
                ce_lo, ce_hi = atm_k, atm_k + w * lc.STEP
                pe_lo, pe_hi = atm_k - w * lc.STEP, atm_k
                rows.append({
                    "entry_day": entry_day, "near_exp": near_exp, "width": w,
                    "exit_convention": exit_label, "spot_entry": spot_entry, "atm_k": atm_k,
                    "exit_spot": exit_spot,
                    "ce_in_trap": bool(ce_lo <= exit_spot <= ce_hi),
                    "pe_in_trap": bool(pe_lo <= exit_spot <= pe_hi),
                    "abs_move_pts": abs(exit_spot - spot_entry),
                    "abs_move_pct": abs(exit_spot / spot_entry - 1),
                })

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "trapzone_full_history.csv", index=False)

    report = {"n_cycles": len(cycles)}
    for w in WIDTHS:
        for exit_label in [f"exit_-{EXIT_DAYS_BEFORE_EXPIRY}d", "hold_to_expiry"]:
            sub = df[(df["width"] == w) & (df["exit_convention"] == exit_label)]
            if sub.empty:
                continue
            key = f"w{w}_{exit_label}"
            report[key] = {
                "n": int(len(sub)),
                "ce_trap_freq": float(sub["ce_in_trap"].mean()),
                "pe_trap_freq": float(sub["pe_in_trap"].mean()),
                "either_trap_freq": float((sub["ce_in_trap"] | sub["pe_in_trap"]).mean()),
                "median_abs_move_pts": float(sub["abs_move_pts"].median()),
                "p75_abs_move_pts": float(sub["abs_move_pts"].quantile(0.75)),
            }
            print(f"[w={w} {exit_label}] n={report[key]['n']} "
                  f"CE_trap={report[key]['ce_trap_freq']:.1%} PE_trap={report[key]['pe_trap_freq']:.1%} "
                  f"either={report[key]['either_trap_freq']:.1%} "
                  f"median|move|={report[key]['median_abs_move_pts']:.0f}pts", flush=True)

    (OUT / "trapzone_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print("\nDONE -> trapzone_report.json")


if __name__ == "__main__":
    sys.exit(main())
