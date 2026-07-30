"""Assemble the final cells.csv (superset schema covering both predictive-regression cells and
structure/P&L cells) from predictive_cells.csv, structure_cells.csv, strangle_cells.csv,
atm_calendar_cells.csv. One row per (cell, era). Bonferroni bar stated per the firm convention.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent

pred = pd.read_csv(HERE / "predictive_cells.csv")
pred["kind"] = "predictive"
pred["structure"] = "regression: " + pred["signal"] + " -> " + pred["target"]
pred["mean"] = pred["beta"]
pred["win"] = np.nan
pred["rr"] = np.nan
pred["trades_per_month"] = np.nan

struct = pd.read_csv(HERE / "structure_cells.csv")
struct["kind"] = "structure"
struct["signal"] = "front skew25 richness"
struct["structure"] = struct["cell"]
struct["placebo_bar"] = np.nan

strangle = pd.read_csv(HERE / "strangle_cells.csv")
strangle["kind"] = "structure"
strangle["cell"] = "sell_25d_strangle_" + strangle["cond"].astype(str)
strangle["signal"] = "iv_rv percentile"
strangle["structure"] = strangle["cell"]

atmcal = pd.read_csv(HERE / "atm_calendar_cells.csv")
atmcal["kind"] = "structure"
atmcal["signal"] = np.where(atmcal["cell"].str.contains("calendar"), "term_slope", "iv_rv/level")
atmcal["structure"] = atmcal["cell"]

cols = ["kind", "cell", "signal", "structure", "era", "n", "trades_per_month", "mean", "win",
        "rr", "t", "placebo_bar", "placebo_p", "verdict", "conc_max_frac"]


def align(df):
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan
    return df[cols]


allc = pd.concat([align(pred), align(struct), align(strangle), align(atmcal)], ignore_index=True)
allc.to_csv(HERE / "cells.csv", index=False)
print(f"wrote cells.csv shape={allc.shape}")
print(f"unique cell definitions (trials, pre era-split): "
      f"{pred['cell'].nunique() + struct['cell'].nunique() + strangle['cell'].nunique() + atmcal['cell'].nunique()}")
