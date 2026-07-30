"""Dev-only: sanity-check every signal-generator function before trusting the queued
155_indicator_mine_signals.py run. Not for the queue."""
from __future__ import annotations
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
QUEUE_FILE = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/BACKTEST_QUEUE_20260730/queue/155_indicator_mine_signals.py"
sys.path.insert(0, str(QUEUE_FILE.parent))
import importlib.util
spec = importlib.util.spec_from_file_location("mine155", QUEUE_FILE)
mine155 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mine155)

t0 = time.time()
spot = mine155.load_spot()
print("spot", len(spot), spot.index[0], spot.index[-1])
feat = mine155.load_feat()
print("feat", len(feat), feat['bucket'].min(), feat['bucket'].max())
print(feat[['ce_vol','pe_vol','ce_oi','pe_oi','conc_ce','conc_pe','spot_ref']].describe())

# sanity: reproduce sweep_priorday_reclaim @ 15min, compare n to published n=1775 (build window)
sig15 = mine155.sweep_priorday_reclaim(spot, "15min")
sig15b = sig15[pd.to_datetime(sig15['t']).dt.date <= mine155.BUILD_END]
print("\nsweep_priorday_reclaim @15min build n =", len(sig15b), "(published reference: 1775)")

sig30 = mine155.sweep_priorday_reclaim(spot, "30min")
sig45 = mine155.sweep_priorday_reclaim(spot, "45min")
print("30min n=", len(sig30), "45min n=", len(sig45))

for label, fn in [
    ("A1_call_heavy", lambda: mine155.imbalance_signals(feat, "call_heavy")),
    ("A2_put_heavy", lambda: mine155.imbalance_signals(feat, "put_heavy")),
    ("A3_conc_call", lambda: mine155.concentration_signals(feat, "call")),
    ("A4_conc_put", lambda: mine155.concentration_signals(feat, "put")),
    ("A5_vwap_reclaim", lambda: mine155.vwap_proxy_band_signals(feat, spot, "reclaim")),
    ("A6_vwap_continue", lambda: mine155.vwap_proxy_band_signals(feat, spot, "continue")),
    ("A7_long_buildup", lambda: mine155.oi_quadrant_signals(feat, "long_buildup")),
    ("A8_short_covering", lambda: mine155.oi_quadrant_signals(feat, "short_covering")),
    ("A9_short_buildup", lambda: mine155.oi_quadrant_signals(feat, "short_buildup")),
    ("A10_long_unwind", lambda: mine155.oi_quadrant_signals(feat, "long_unwind")),
]:
    try:
        sig = fn()
        print(f"{label}: n={len(sig)}", sig.head(2).to_dict('records') if len(sig) else "")
    except Exception as e:
        print(f"{label}: ERROR {type(e).__name__} {e}")
        import traceback; traceback.print_exc()

vix = mine155.load_vix()
print("\nvix", len(vix), vix.index.min(), vix.index.max())
for label, fn in [
    ("B1_high", lambda: mine155.vix_rv_divergence_signals(spot, vix, "high")),
    ("B2_low", lambda: mine155.vix_rv_divergence_signals(spot, vix, "low")),
    ("B3_roc", lambda: mine155.vix_roc_spike_signals(spot, vix)),
]:
    try:
        sig = fn()
        print(f"{label}: n={len(sig)}")
    except Exception as e:
        print(f"{label}: ERROR {type(e).__name__} {e}")
        import traceback; traceback.print_exc()

print(f"\nelapsed {time.time()-t0:.1f}s")
