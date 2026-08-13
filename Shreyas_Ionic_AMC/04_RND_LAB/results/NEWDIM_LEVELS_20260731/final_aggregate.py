"""Combine all dimension cells.csv into one master table, compute this study's own Bonferroni
bar, and select the top-10 to return."""
import sys
import pandas as pd
import numpy as np

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NEWDIM_LEVELS_20260731"
sys.path.insert(0, OUT)
from common_stats import bonferroni_bar  # noqa: E402


def main():
    parts = []
    for f in ["volprofile_cells.csv", "vwap_cells.csv", "compression_cells.csv", "orderflow_cells.csv"]:
        d = pd.read_csv(f"{OUT}/{f}")
        parts.append(d)
    cells = pd.concat(parts, ignore_index=True, sort=False)
    cells.to_csv(f"{OUT}/cells.csv", index=False)
    m = len(cells)
    bar = bonferroni_bar(m)
    print(f"TOTAL CELLS (this study's own trials ledger): {m}")
    print(f"Bonferroni bar at m={m}: |t| >= {bar:.3f}")
    clearing = cells[cells["t"].abs() >= bar]
    print(f"\ncells clearing Bonferroni: {len(clearing)}")
    print(clearing[["dimension", "cell", "n", "mean_pts", "t", "placebo_p"]].sort_values("t").to_string())
    print(f"\nby dimension counts:\n{cells['dimension'].value_counts()}")
    print(f"\npositive-mean cells clearing |t|>=3.0 with n>=30:")
    pos = cells[(cells["mean_pts"] > 0) & (cells["t"].abs() >= 3.0) & (cells["n"] >= 30)]
    print(pos[["dimension", "cell", "n", "mean_pts", "t", "placebo_p"]].to_string())
    print(f"\nall positive-mean cells with t>=2.0 (candidate zone), n>=20:")
    pos2 = cells[(cells["mean_pts"] > 0) & (cells["t"] >= 2.0) & (cells["n"] >= 20)]
    print(pos2[["dimension", "cell", "n", "trades_per_month", "mean_pts", "t", "t_build", "t_recent",
                "n_holdout", "mean_holdout", "placebo_p"]].sort_values("t", ascending=False).to_string())


if __name__ == "__main__":
    main()
