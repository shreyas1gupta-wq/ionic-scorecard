"""
Follow-up: the global trials counter (666-674 by the time this family ran) is
a documented harness distortion (harness.py CONSOLIDATION note) that crushes
DSR toward 0 for EVERY family regardless of quality. Recompute DSR with the
HONEST family-only trial count (n_trials=9, this family's actual cards) using
harness.dsr_from_stats(), and separately verify PBO's known sign-flip-
invariance claim by direct recomputation on the TRADEABLE-direction series
(long low-downside-capture / short high-downside-capture = -1 * the raw
top-minus-bottom series the harness reports).
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats as sstats

THIS = Path(__file__).resolve()
ALPHA_DIR = THIS.parent.parent.parent.parent
sys.path.insert(0, str(ALPHA_DIR / "rnd" / "lib"))
import harness

PANEL_DIR = ALPHA_DIR / "rnd" / "panel"
SUPPORT_DIR = THIS.parent

panel = pd.read_parquet(PANEL_DIR / "panel_long.parquet")
panel["date"] = pd.to_datetime(panel["date"])

WINDOWS = {"1m": 21, "3m": 63, "6m": 126}
HORIZONS = ("1M", "1Y", "5Y")
FAMILY_N_TRIALS = 9  # this family's honest count: 3 windows x 3 horizons

out = {}
for wname in WINDOWS:
    dc_sub = pd.read_parquet(SUPPORT_DIR / f"w6dc_factor_{wname}.parquet")
    long_f = dc_sub.stack().rename("factor").reset_index()
    long_f.columns = ["date", "symbol", "factor"]
    for hz in HORIZONS:
        lbl = harness._label_cols(hz)
        target_col, raw_col = lbl["resid"], lbl["raw"]
        base_cols = ["date", "symbol", "regime_trend", "regime_vol", "mktcap_log"]
        p = panel[base_cols + [target_col, raw_col]].copy()
        p = p.rename(columns={target_col: "target_eval", raw_col: "target_raw"})
        merged = long_f.merge(p, on=["date", "symbol"], how="inner").dropna(subset=["factor", "target_eval"])
        ls_ret_raw, _, _ = harness._decile_stats(merged, min_names=20)
        tradeable = -1.0 * ls_ret_raw  # long low-DC / short high-DC, matches the negative-IC direction

        dsr_honest = harness.compute_dsr(tradeable, n_trials=FAMILY_N_TRIALS)
        pbo_tradeable = harness.compute_pbo_cscv(tradeable, n_blocks=12)
        pbo_original = harness.compute_pbo_cscv(ls_ret_raw, n_blocks=12)

        key = f"{wname}_{hz}"
        out[key] = {
            "sr_hat_tradeable": dsr_honest["sr_hat"], "skew_tradeable": dsr_honest["skew"],
            "kurtosis": dsr_honest["kurtosis"], "n_obs": dsr_honest["n_obs"],
            "dsr_honest_family_ntrials9": dsr_honest["dsr"],
            "sr0_expected_max_ntrials9": dsr_honest["sr0_expected_max"],
            "pbo_tradeable_direction": pbo_tradeable["pbo"],
            "pbo_original_direction": pbo_original["pbo"],
            "pbo_sign_flip_invariant": abs(pbo_tradeable["pbo"] - pbo_original["pbo"]) < 1e-9,
            "mean_tradeable": float(tradeable.mean()), "ann_mean_tradeable_x12": float(tradeable.mean() * 12),
        }
        print(key, out[key])

with open(SUPPORT_DIR / "w6dc_honest_dsr.json", "w", encoding="utf-8") as fh:
    json.dump(harness._to_native(out), fh, indent=2)
print("written:", SUPPORT_DIR / "w6dc_honest_dsr.json")
