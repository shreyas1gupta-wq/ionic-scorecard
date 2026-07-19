"""WAVE-3 resurrection #2: regime-GATED quality (SIZING use of the regime insight,
not blending). Hypothesis: QMJ (CAPSTONE_quality_QMJ, PROMOTE* standalone, IC_IR
0.77/1Y 1.74/5Y) is long ONLY when regime_trend=='bear' OR regime_vol=='high',
flat (NaN, no position) otherwise -- causal, uses only the panel's own regime_*
columns which are built off trailing/contemporaneous vol & MA state (no forward
info). Question: does this produce a CLEAN positive result in exactly the
windows it's active (not just "same as always-on"), i.e. does the regime tag
correctly select QMJ's best-earning dates?

Reuses build_qmj_composite() unmodified (no re-fit) -- only the DATE MASK changes.
Runs at 1Y and 5Y (QMJ's two working horizons per CONSOLIDATION.md) on panel_long
(21yr, has bear/high-vol regime dates unlike the 5yr panel).
"""
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(_LIB))

import pandas as pd
import builders_w2_profq as bprofq
from harness import evaluate

PANEL_LONG_PATH = _LIB.parent / "panel" / "panel_long.parquet"
panel = pd.read_parquet(PANEL_LONG_PATH)
source = "real_panel_long_w3qualgate"
print(f"panel loaded: source={source}, shape={panel.shape}")

qmj = bprofq.build_qmj_composite(panel)  # Series indexed (date,symbol), full history
print("qmj raw n_obs:", qmj.notna().sum())

# regime mask, keyed by (date,symbol) -- built from the SAME panel rows (no lookahead:
# regime_trend/regime_vol at panel.parquet build time are trailing/contemporaneous state)
reg = panel.set_index(["date", "symbol"])[["regime_trend", "regime_vol"]]
gate = (reg["regime_trend"] == "bear") | (reg["regime_vol"] == "high")
gate = gate.reindex(qmj.index).fillna(False)

qmj_gated = qmj[gate]
print("gated n_obs (bear OR high-vol dates only):", qmj_gated.notna().sum(),
      f"({qmj_gated.notna().sum() / qmj.notna().sum():.1%} of always-on)")

results = {}
for horizon in ["1Y", "5Y"]:
    card = evaluate(qmj_gated, horizon, return_basis="resid", factor_id=f"W3_qualgate_{horizon}",
                     panel=panel, panel_source=source, family="W3_qualgate", write_card=True)
    ic = card.get("ic", {})
    ls = card.get("long_short", {})
    costs = card.get("costs", {})
    lag = card.get("lag_test", {})
    placebo = card.get("placebo", {})
    dec = card.get("deciles", {})
    print(f"\n=== W3_qualgate_{horizon} (bear OR high-vol dates only) ===")
    print("n_dates/n_obs:", card.get("n_dates"), card.get("n_obs"))
    print("ic_mean/ic_ir:", ic.get("ic_mean"), ic.get("ic_ir"))
    print("monotonicity:", dec.get("monotonicity"))
    print("ann_return_LS (gross):", ls.get("ann_return_LS"))
    print("net_of_cost_ann_return:", costs.get("net_of_cost_ann_return"))
    print("turnover:", card.get("turnover", {}).get("avg_turnover"))
    print("lag_test_delta:", lag.get("lag_test_delta"))
    print("placebo_ic:", placebo.get("placebo_ic"))
    print("pbo:", card.get("pbo", {}).get("pbo"), "(advisory)")
    print("dsr:", card.get("dsr", {}).get("dsr"), "(advisory)")
    print("verdict:", card.get("verdict"))
    results[horizon] = card

# ---- reference: CAPSTONE_quality_QMJ_1Y.json's own regime_breakdown (always-on
# QMJ's per-regime mean IC, already computed and on disk) -- context for whether
# the GATE's IC (above) roughly matches "bear+high-vol" or is worse/better than
# a naive average of those two conditional ICs.
for h in ["1Y", "5Y"]:
    ref_path = Path(__file__).resolve().parent.parent / "cards" / f"CAPSTONE_quality_QMJ_{h}.json"
    if ref_path.exists():
        import json
        ref = json.loads(ref_path.read_text(encoding="utf-8"))
        rb = ref.get("regime_breakdown", {})
        print(f"\n[{h}] always-on QMJ regime_breakdown (reference, from {ref_path.name}): {rb}")
