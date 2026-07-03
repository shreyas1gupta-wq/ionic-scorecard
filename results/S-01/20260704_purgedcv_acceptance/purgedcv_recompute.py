# -*- coding: utf-8 -*-
"""S-01 DSR + PBO recompute with purgedcv v0.1.2 (D-M6 acceptance, 2026-07-04).

Rebuild the EXACT S-01 inputs from validate_S01.py:
  slice = iv_rv>=1.4 & iv<1.0 of rv_iv_vol.parquet
  monthly EW series booked on EXIT month (short_ret)
  9-cell grid {1.2,1.4,1.6} x {0.8,1.0,1.2}, N_trials=13, var_sharpe=0.0517
Then call purgedcv.deflated_sharpe_ratio and purgedcv.probability_of_backtest_overfitting
and compare to hand-rolled DSR 0.687 / PBO 55.3%.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd
import purgedcv

ROOT = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500"
DATA = os.path.join(ROOT, "intraday_options_strategy", "buying", "rv_iv_vol.parquet")
OUT = Path(ROOT) / "results" / "S-01" / "20260704_purgedcv_acceptance"
RET = "short_ret"

df = pd.read_parquet(DATA)
for c in ("exp", "entry", "exit"):
    df[c + "_dt"] = pd.to_datetime(df[c])
df["exit_ym"] = df["exit_dt"].dt.to_period("M")


def slice_it(d, ir, ic):
    return d[(d["iv_rv"] >= ir) & (d["iv"] < ic)].copy()


def monthly_series(sl):
    return sl.groupby("exit_ym")[RET].mean().sort_index()


S01 = slice_it(df, 1.4, 1.0)
port = monthly_series(S01)                       # the S-01 monthly EW series (T months)
grid_ivrv = [1.2, 1.4, 1.6]; grid_ivcap = [0.8, 1.0, 1.2]
grid = [(a, b) for a in grid_ivrv for b in grid_ivcap]

# trial Sharpes across the 9 grid cells (per-period), same as hand-rolled
grid_sr = []
for (ir, ic) in grid:
    ms = monthly_series(slice_it(df, ir, ic))
    if len(ms) >= 3:
        grid_sr.append(ms.mean() / ms.std(ddof=1))
grid_sr = np.array(grid_sr)
var_sharpe_grid = float(np.var(grid_sr, ddof=1))
N_TRIALS = 13
VAR_SHARPE_HANDROLLED = 0.0517                    # value the hand-rolled battery used

r = port.values.astype(float)
r = r[~np.isnan(r)]
T = len(r)
sr_pp = r.mean() / r.std(ddof=1)

log = []
def P(*a):
    s = " ".join(str(x) for x in a); print(s); log.append(s)

P("=" * 74)
P("S-01 purgedcv v%s ACCEPTANCE — DSR + PBO recompute" % getattr(purgedcv, "__version__", "?"))
P("=" * 74)
P(f"slice iv_rv>=1.4 & iv<1.0 : rows={len(S01)}  months(T)={T}  SR/period={sr_pp:.4f}")
P(f"grid trial SRs (n={len(grid_sr)}): var_sharpe(grid)={var_sharpe_grid:.4f}  handrolled used={VAR_SHARPE_HANDROLLED}")

# ---------------- DSR via purgedcv ----------------
# CRITICAL UNITS: grid_sr are PER-PERIOD (per-month) Sharpes, so var_sharpe=0.0517 is ALREADY
# per-observation. Do NOT pass bars_per_year (that would wrongly divide by 12). This matches
# the hand-rolled convention exactly (both operate in per-period Sharpe units).
dsr_correct = purgedcv.deflated_sharpe_ratio(r, n_trials=N_TRIALS, var_sharpe=var_sharpe_grid)
# what the (wrong) bars_per_year=12 call gave, for the record
dsr_wrong_bpy = purgedcv.deflated_sharpe_ratio(r, n_trials=N_TRIALS, var_sharpe=var_sharpe_grid, bars_per_year=12)
try:
    full = purgedcv.deflated_sharpe_ratio_full(r, n_trials=N_TRIALS, var_sharpe=var_sharpe_grid)
    full_d = {k: (float(getattr(full, k)) if isinstance(getattr(full, k), (int, float, np.floating)) else getattr(full, k))
              for k in dir(full) if not k.startswith("_") and not callable(getattr(full, k))}
except Exception as e:
    full_d = {"err": repr(e)}

P("\n--- DEFLATED SHARPE (correct per-observation units, NO bars_per_year) ---")
P(f"  purgedcv DSR (var_sharpe={var_sharpe_grid:.4f} per-period) = {dsr_correct:.4f}   <-- comparable to hand-rolled")
P(f"  purgedcv DSR with WRONG bars_per_year=12 (double-scaled)   = {dsr_wrong_bpy:.4f}   (units error, do NOT use)")
P(f"  hand-rolled DSR                                            = 0.6870")
P(f"  diagnostics (correct call): {json.dumps(full_d, default=str)}")

# ---------------- PBO via purgedcv CSCV ----------------
# build months x 9-config return matrix, same as hand-rolled
all_months = sorted(df["exit_ym"].unique())
cols = {}
for (ir, ic) in grid:
    cols[f"{ir}_{ic}"] = monthly_series(slice_it(df, ir, ic)).reindex(all_months)
M = pd.DataFrame(cols).dropna(how="all")
# purgedcv wants per-period returns of n_configs candidates. Default metric = sharpe. n_splits=S.
# hand-rolled used S=12 blocks. purgedcv CSCV n_splits must be even; try 12, fallback 10/16.
# purgedcv expects (n_configs, n_obs) = 9 configs x 47 months -> TRANSPOSE M (which is months x configs)
Mfill = M.fillna(0.0)                       # missing config-month -> flat 0 return (same spirit as hand-rolled)
mat = Mfill.values.T                         # (9, 47)
P(f"  PBO input matrix: {mat.shape} = (n_configs, n_obs)")
pbo_results = {}
for S in (16, 12, 8):                        # even n_splits over the 47-month axis; hand-rolled used 12
    try:
        res = purgedcv.probability_of_backtest_overfitting(mat, n_splits=S)
        pbo_val = float(getattr(res, "pbo", getattr(res, "value", np.nan)))
        pbo_results[S] = {"pbo": pbo_val, "attrs": [a for a in dir(res) if not a.startswith("_")]}
        P(f"\n--- PBO (purgedcv CSCV, n_splits={S}) --- PBO={pbo_val:.4f}")
        for a in dir(res):
            if a.startswith("_"): continue
            v = getattr(res, a)
            if isinstance(v, (int, float, np.floating)):
                P(f"      {a} = {float(v):.4f}")
    except Exception as e:
        pbo_results[S] = {"err": repr(e)}
        P(f"\n--- PBO n_splits={S}: ERROR {e!r}")

P("\n  hand-rolled PBO (CSCV, S=12, ranking-logit) = 0.5530")

out = {
    "purgedcv_version": getattr(purgedcv, "__version__", "?"),
    "slice_rows": int(len(S01)), "T_months": int(T), "sr_per_period": float(sr_pp),
    "n_trials": N_TRIALS, "var_sharpe_grid": var_sharpe_grid,
    "var_sharpe_handrolled": VAR_SHARPE_HANDROLLED,
    "dsr_purgedcv_correct": float(dsr_correct),
    "dsr_purgedcv_wrong_bars_per_year": float(dsr_wrong_bpy),
    "dsr_handrolled": 0.687,
    "dsr_full_diagnostics": full_d,
    "pbo_purgedcv": {str(k): v for k, v in pbo_results.items()},
    "pbo_handrolled": 0.553,
}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "recompute.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
(OUT / "recompute_raw.txt").write_text("\n".join(log), encoding="utf-8")
print("\nsaved recompute.json, recompute_raw.txt ->", OUT)
