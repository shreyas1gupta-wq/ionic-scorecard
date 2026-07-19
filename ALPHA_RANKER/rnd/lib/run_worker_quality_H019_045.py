"""One-shot runner: H019, H020, H021, H022, H023, H045 (quality worker assignment).
All at basis='resid'. H019/H021 tested at 1Y only (5Y deferred, panel_long pending).
H023 tested at 1Y as a disclosed out-of-registration substitute for its 5Y-only
pre-registration (5Y forward returns are 100% NaN in this panel build).
"""
import sys, time, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import load_panel, run_experiment
import builders_quality as bq

panel, src = load_panel()
print(f"panel_source={src} rows={len(panel)} dates={panel['date'].nunique()} symbols={panel['symbol'].nunique()}")

jobs = [
    ("H019_roic", bq.build_roic_factor, "1Y"),
    ("H020_piotroski", bq.build_piotroski_factor, "1Y"),
    ("H021_grossprof", bq.build_gross_profitability_factor, "1Y"),
    ("H022_accruals", bq.build_accruals_factor, "1Y"),
    ("H023_earnstab", bq.build_earnings_stability_factor, "1Y"),
    ("H045_cashconv", bq.build_cash_conversion_factor, "1Y"),
]

results = {}
for fid, builder, horizon in jobs:
    t0 = time.time()
    card = run_experiment(fid, builder, horizon, basis="resid", panel=panel, panel_source=src)
    dt = time.time() - t0
    results[fid] = {
        "verdict": card.get("verdict"), "status": card.get("status"),
        "n_obs": card.get("n_obs"), "n_dates": card.get("n_dates"),
        "ic_mean": card.get("ic", {}).get("ic_mean"), "ic_ir": card.get("ic", {}).get("ic_ir"),
        "mono": card.get("deciles", {}).get("monotonicity"),
        "dsr": card.get("dsr", {}).get("dsr"), "pbo": card.get("pbo", {}).get("pbo"),
        "lag_delta": card.get("lag_test", {}).get("lag_test_delta"),
        "placebo_ic": card.get("placebo", {}).get("placebo_ic"),
        "net_cost_ann": card.get("costs", {}).get("net_of_cost_ann_return"),
    }
    print(f"{fid} [{horizon}]  ({dt:.1f}s) ->", json.dumps(results[fid]))

print("\n=== SUMMARY ===")
for fid, r in results.items():
    print(fid, r["verdict"])
