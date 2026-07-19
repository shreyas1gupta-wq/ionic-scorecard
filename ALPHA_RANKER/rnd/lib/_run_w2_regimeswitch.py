import sys, json, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from harness import evaluate, load_panel
from builders_w2_regimeswitch import (
    build_momentum_tilt, build_defensive_tilt, build_static_composite,
    build_regime_switched_trend, build_regime_switched_vol,
)
from builders_vol import build_h010_lowvol

panel, src = load_panel()
print("panel", panel.shape, src, flush=True)

JOBS = [
    ("W2_regimeswitch_trend", build_regime_switched_trend),
    ("W2_regimeswitch_vol", build_regime_switched_vol),
    ("W2_static_composite", build_static_composite),
    ("W2_static_momentum", build_momentum_tilt),
    ("W2_static_lowvol", lambda p: build_h010_lowvol(p)),
]

results = {}
for horizon in ["1M", "1Y"]:
    for name, fn in JOBS:
        fid = f"{name}_{horizon}"
        try:
            factor = fn(panel)
            card = evaluate(factor, horizon, return_basis="resid", factor_id=fid,
                             panel=panel, panel_source=src, family="W2",
                             cards_dir=Path(__file__).parent.parent / "cards")
            key_metrics = {
                "status": card.get("status"),
                "n_obs": card.get("n_obs"),
                "ic_ir": card.get("ic", {}).get("ic_ir"),
                "ic_mean": card.get("ic", {}).get("ic_mean"),
                "mono": card.get("deciles", {}).get("monotonicity"),
                "hit": card.get("long_short", {}).get("hit_rate"),
                "ann_return_LS_gross": card.get("long_short", {}).get("ann_return_LS"),
                "turnover": card.get("turnover", {}).get("avg_top_decile_turnover"),
                "net_of_cost_ann": card.get("costs", {}).get("net_of_cost_ann_return"),
                "dsr": card.get("dsr"),
                "pbo": card.get("pbo"),
                "lag_delta": card.get("lag_test", {}).get("lag_test_delta"),
                "placebo_ic": card.get("placebo", {}).get("placebo_ic"),
                "regime_breakdown": card.get("regime_breakdown"),
                "verdict": card.get("verdict"),
            }
            results[fid] = key_metrics
            print(fid, "OK", key_metrics["ic_ir"], key_metrics["net_of_cost_ann"], key_metrics["verdict"], flush=True)
        except Exception as e:
            results[fid] = {"status": "ERROR", "error": str(e)}
            print(fid, "ERROR", e, flush=True)
            traceback.print_exc()

out_path = Path(__file__).parent.parent / "reports" / "W2_regimeswitch_results.json"
out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
print("wrote", out_path, flush=True)
