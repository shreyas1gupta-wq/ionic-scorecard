# -*- coding: utf-8 -*-
"""gate_drag_full_check.py - verify/refute the -3.26 (D3) / +1.45 (D10) gate-drag claim.
Nikhil Bose, red team, 2026-08-06.

The Principal's number comes from bt_decile_diagnose.py's decomposition.csv, POOLED OVER ONLY 5
FORMATIONS (2023-03-31, 2023-09-30, 2024-03-31, 2024-09-30, 2025-03-31; n=2,156). observations.csv
already has BOTH `final` and `composite_3y` for every one of the 35 rolling formations (n=14,943) --
7x the formations, no extra scoring run needed. gate_drag = final - composite_3y, same definition,
recomputed independently here and checked against decomposition.csv's 5-formation numbers.
"""
import os
import numpy as np
import pandas as pd

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
SC750 = os.path.dirname(os.path.dirname(HERE))
OBS = os.path.join(SC750, "results", "DECILE_ROLLING_20260805", "observations.csv")
OUT = HERE


def main():
    d = pd.read_csv(OBS)
    d["gate_drag"] = d["final"] - d["composite_3y"]
    print(f"loaded {len(d)} rows, {d['formation'].nunique()} formations")

    g = d.groupby("dec_final", observed=True)
    tab = pd.DataFrame({
        "n": g.size(),
        "gate_drag_mean": g["gate_drag"].mean().round(3),
        "gate_drag_median": g["gate_drag"].median().round(3),
        "pct_negative_drag": (g["gate_drag"].apply(lambda x: (x < 0).mean()) * 100).round(1),
        "pct_zero_drag": (g["gate_drag"].apply(lambda x: (x == 0).mean()) * 100).round(1),
    })
    print("\n=== gate_drag by decile, ALL 35 formations (n=14,943) ===")
    print(tab.to_string())
    tab.to_csv(os.path.join(OUT, "gate_drag_full35.csv"))

    print(f"\nclaim check: D3 gate_drag = {tab.loc[3,'gate_drag_mean']:+.2f}  "
          f"(Principal claimed -3.26 on a 5-formation subsample)")
    print(f"claim check: D10 gate_drag = {tab.loc[10,'gate_drag_mean']:+.2f}  "
          f"(Principal claimed +1.45 on a 5-formation subsample)")

    # per-formation stability: is D3's negative drag / D10's positive drag consistent across
    # formations, or is the pooled mean carried by a few formations?
    per_f = d.groupby(["formation", "dec_final"], observed=True)["gate_drag"].mean().unstack()
    print(f"\nD3 gate_drag by formation: negative in {int((per_f[3] < 0).sum())}/{per_f.shape[0]} formations "
          f"(mean {per_f[3].mean():+.2f}, range {per_f[3].min():+.2f} to {per_f[3].max():+.2f})")
    print(f"D10 gate_drag by formation: positive in {int((per_f[10] > 0).sum())}/{per_f.shape[0]} formations "
          f"(mean {per_f[10].mean():+.2f}, range {per_f[10].min():+.2f} to {per_f[10].max():+.2f})")
    per_f.to_csv(os.path.join(OUT, "gate_drag_by_formation.csv"))

    # WHY: what fraction of each decile is actually gated (red/amber) at all -- the mechanism claim
    # decomposition.csv doesn't carry red/amber flags; check via de/intcov thresholds directly.
    fin_note = ("(is_fin unavailable in observations.csv; de/intcov not banked either -- this reruns "
                 "the ORIGINAL score_asof would be needed for a flag-level breakdown. Deferred to the "
                 "gate-ablation run, which banks red_flag/amber_flag per row.)")
    print(f"\nnote: {fin_note}")


if __name__ == "__main__":
    main()
