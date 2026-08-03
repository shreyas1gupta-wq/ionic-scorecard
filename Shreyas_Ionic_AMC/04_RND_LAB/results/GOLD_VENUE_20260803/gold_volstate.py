"""GOLD_VENUE_20260803 -- volatility-state conditioning (ask #4). On NIFTY, trailing features
(realized vol at multiple horizons, ATR consumption, opening-range width) predict forward
realized vol OOS at AUC 0.85 (0.87 held-out). Test whether the SAME feature family predicts
GOLD's forward realized vol, sampled once per MCX day at a fixed 13:00 IST decision point (the
same cutoff used by the ATR_CONSUMPTION_BRK trigger in gold_venue_scan.py, so the feature and the
tradeable signal share one honest reference time).

FEATURES (all causal, computed ONLY from 09:00-13:00 data, no lookahead into the label window):
  trailing_rv_2h   : stdev of 1-min log returns, 11:00-13:00
  trailing_rv_4h   : stdev of 1-min log returns, 09:00-13:00
  atr_consumption  : (09:00-13:00 high-low)/session_open, over the CAUSAL 20-day trailing
                     average daily range (today excluded) -- same construction as the trigger
  or60_width_norm  : (09:00-10:00 high-low)/session_open, over the same trailing typical range
LABEL: forward_range_pct = (13:00-23:30 high-low)/session_open*100 (the afternoon+evening
  session's realized range -- the quantity a vol-conditioned entry would actually want to know).
  Binarised top-tercile vs bottom-tercile (build-period tercile cuts only) for the AUC read;
  Spearman rho reported on the continuous label as the primary, less arbitrary statistic.

Build = 2009-01-01..2025-06-30 (tercile cuts fit HERE only). HELD OUT = 2025-07-01..2025-12-31,
scored with the BUILD cuts, never refit.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score

warnings_ = None
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import gold_venue_lib as gvl  # noqa: E402

import gold_lib as gl  # noqa: E402

t0 = time.time()
# BUG FOUND 2026-08-03 (this is what run_log.txt's traceback caught -- gl.load_gold_ist()'s
# all-years concat OOM'd under today's system-wide memory pressure, "Unable to allocate 5.61 MiB"
# with free virtual memory measured at ~2GB at time of fix). gold_venue_scan.py was already
# patched by a prior pass to stream one year file at a time instead of loading the full 5.9M-row
# frame; this script was NOT -- fixed the same way here via gvl.compute_volstate_features_streaming(),
# which reproduces the exact same rv2h/rv4h/morning/OR60/afternoon panel this file's original draft
# computed off the full `spot` frame, just accumulated one year at a time.
print("[load] MCX daily stats + per-day trailing/afternoon features, streamed one year at a time "
      "(memory-light path)", flush=True)
daily = gvl.compute_daily_stats()
print(f"       daily table: {len(daily)} days  ({time.time()-t0:.1f}s)", flush=True)

feats = gvl.compute_volstate_features_streaming()
print(f"       feature table: {len(feats)} days  ({time.time()-t0:.1f}s)", flush=True)

panel = daily[["session_open", "typical_range_pct"]].copy()
panel = panel.join(feats)
panel = panel.dropna(subset=["session_open", "typical_range_pct", "m_hi", "m_lo", "a_hi", "a_lo"])
panel["atr_consumption"] = (panel["m_hi"] - panel["m_lo"]) / panel["session_open"] * 100 / panel["typical_range_pct"]
panel["or60_width_norm"] = (panel["o60_hi"] - panel["o60_lo"]) / panel["session_open"] * 100 / panel["typical_range_pct"]
panel["forward_range_pct"] = (panel["a_hi"] - panel["a_lo"]) / panel["session_open"] * 100
panel = panel.replace([np.inf, -np.inf], np.nan).dropna(
    subset=["trailing_rv_2h", "trailing_rv_4h", "atr_consumption", "or60_width_norm", "forward_range_pct"])
print(f"[panel] {len(panel)} usable MCX days  ({time.time()-t0:.1f}s)", flush=True)

build = panel[panel.index < gvl.HELDOUT_GOLD.date()]
ho = panel[panel.index >= gvl.HELDOUT_GOLD.date()]
print(f"  build n={len(build)}  held-out n={len(ho)}", flush=True)

FEATURES = ["trailing_rv_2h", "trailing_rv_4h", "atr_consumption", "or60_width_norm"]
q_lo, q_hi = build["forward_range_pct"].quantile([1/3, 2/3])
print(f"  build tercile cuts on forward_range_pct: lo={q_lo:.4f} hi={q_hi:.4f}", flush=True)

rows = []
for split_name, d in (("BUILD", build), ("HELDOUT", ho)):
    lbl_bin = pd.Series(np.nan, index=d.index)
    lbl_bin[d["forward_range_pct"] <= q_lo] = 0
    lbl_bin[d["forward_range_pct"] >= q_hi] = 1
    for feat in FEATURES:
        rho, p_rho = stats.spearmanr(d[feat], d["forward_range_pct"])
        sub = d.loc[lbl_bin.notna()]
        y = lbl_bin.loc[lbl_bin.notna()].astype(int)
        try:
            auc = roc_auc_score(y, sub[feat]) if y.nunique() == 2 else np.nan
        except Exception:
            auc = np.nan
        rows.append(dict(split=split_name, feature=feat, n=len(d), n_tercile=len(y),
                         spearman_rho=round(float(rho), 4), spearman_p=round(float(p_rho), 4),
                         auc_vs_forward_range_tercile=round(float(auc), 4) if np.isfinite(auc) else None))
        print(f"  [{split_name}] {feat:<18} rho={rho:+.4f} (p={p_rho:.4f})  AUC={auc:.4f}"
              if np.isfinite(auc) else f"  [{split_name}] {feat:<18} rho={rho:+.4f} (p={p_rho:.4f})  AUC=n/a",
              flush=True)

pd.DataFrame(rows).to_csv(HERE / "volstate.csv", index=False)
panel.to_csv(HERE / "volstate_panel.csv")
print(f"\n[done] elapsed {time.time()-t0:.1f}s -> volstate.csv, volstate_panel.csv", flush=True)
