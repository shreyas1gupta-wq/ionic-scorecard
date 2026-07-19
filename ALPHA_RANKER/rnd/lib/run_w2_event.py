"""Run the 3 W2 event-driven factors through the shared harness. One-shot script,
writes rnd/cards/W2_event_*.json. Not a library module; run directly."""
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(_LIB))

import builders_w2_event as w2
from harness import run_experiment, load_panel

panel, source = load_panel()
print(f"panel loaded: source={source}, shape={panel.shape}")

specs = [
    ("W2_event_pead_sign_1M", w2.build_w2_event_pead_sign, "1M"),
    ("W2_event_gapcont_1M", w2.build_w2_event_gapcont, "1M"),
    ("W2_event_accel_1M", w2.build_w2_event_accel, "1M"),
]

for factor_id, fn, horizon in specs:
    card = run_experiment(factor_id, fn, horizon, basis="resid", panel=panel,
                          panel_source=source, family="W2_event")
    ic = card.get("ic", {})
    ls = card.get("long_short", {})
    costs = card.get("costs", {})
    lag = card.get("lag_test", {})
    placebo = card.get("placebo", {})
    print(f"\n=== {factor_id} ===")
    print("status:", card.get("status"))
    print("n_dates/n_obs:", card.get("n_dates"), card.get("n_obs"))
    print("ic_mean/ic_ir:", ic.get("ic_mean"), ic.get("ic_ir"))
    print("mono:", card.get("deciles", {}).get("monotonicity"))
    print("hit_rate:", ls.get("hit_rate"))
    print("net_of_cost_ann_return:", costs.get("net_of_cost_ann_return"))
    print("lag_test_delta:", lag.get("lag_test_delta"))
    print("placebo_ic:", placebo.get("placebo_ic"))
    print("pbo:", card.get("pbo", {}).get("pbo"))
    print("dsr:", card.get("dsr", {}).get("dsr"))
    print("verdict:", card.get("verdict"))
