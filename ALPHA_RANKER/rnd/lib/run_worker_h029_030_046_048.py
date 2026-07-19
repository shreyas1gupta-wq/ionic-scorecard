"""
Worker runner: H029, H030, H046, H048.
Prompt directive: horizons 1M & 1Y only (5Y forward returns are 100% NaN in
panel.parquet per PANEL_SCHEMA.md staleness note — 5Y horizon substituted
with 1M/1Y, disclosed here and in the card notes rather than silently
producing an all-NaN 5Y result for H030/H046 whose backlog entries name 5Y).
Writes one JSON summary + prints a compact verdict table; individual cards
land in rnd/cards/<id>.json via the shared harness.
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import builders_interact as bi
from harness import run_experiment, load_panel, CARDS_DIR

OUT = Path(__file__).parent.parent / "reports" / "WORKER_H029_030_046_048_results.json"

panel, src = load_panel()
print(f"panel_source={src} rows={len(panel)} dates={panel['date'].nunique()} symbols={panel['symbol'].nunique()}")

results = {}

def run(fid, builder, horizon, basis="resid"):
    existing = CARDS_DIR / f"{fid}.json"
    if existing.exists():
        card = json.loads(existing.read_text(encoding="utf-8"))
        if card.get("status") == "OK":
            print(f"-- RESUME (already on disk, not re-run): {fid}")
        else:
            print(f"-- running {fid} h={horizon} basis={basis} ...")
            card = run_experiment(fid, builder, horizon, basis=basis, panel=panel, panel_source=src)
    else:
        print(f"-- running {fid} h={horizon} basis={basis} ...")
        card = run_experiment(fid, builder, horizon, basis=basis, panel=panel, panel_source=src)
    results[fid] = {
        "horizon": horizon, "status": card.get("status"),
        "verdict": card.get("verdict"),
        "ic_mean": card.get("ic", {}).get("ic_mean"),
        "ic_ir": card.get("ic", {}).get("ic_ir"),
        "n_obs": card.get("n_obs"), "n_dates": card.get("n_dates"),
        "net_of_cost_ann_return": card.get("costs", {}).get("net_of_cost_ann_return"),
        "monotonicity": card.get("deciles", {}).get("monotonicity"),
        "pbo": card.get("pbo", {}).get("pbo"),
        "lag_test_delta": card.get("lag_test", {}).get("lag_test_delta"),
        "placebo_ic": card.get("placebo", {}).get("placebo_ic"),
    }
    print(f"   -> {results[fid]}")
    return card

for h in ["1M", "1Y"]:
    # H029: quality x momentum
    run(f"H029_quality_only_{h}", bi.h029_quality, h)
    run(f"H029_momentum_only_{h}", bi.h029_momentum, h)
    run(f"H029_interact_{h}", bi.h029_interaction, h)

    # H030: value x quality (QARP) -- 5Y substituted with 1M/1Y (see docstring)
    run(f"H030_value_only_{h}", bi.h030_value, h)
    run(f"H030_quality_only_{h}", bi.h030_quality, h)
    run(f"H030_interact_{h}", bi.h030_interaction, h)

    # H046: EY x growth (GARP) -- 5Y substituted with 1M/1Y
    run(f"H046_ey_only_{h}", bi.h046_ey, h)
    run(f"H046_growth_only_{h}", bi.h046_growth, h)
    run(f"H046_interact_{h}", bi.h046_interaction, h)

# H048: sector-neutral diagnostic -- report variance share + IC raw vs sector-neutral
diag = {}
for name, raw_fn, sn_fn in [("quality", bi.h048_quality_raw, bi.h048_quality_sector_neutral),
                             ("momentum", bi.h048_momentum_raw, bi.h048_momentum_sector_neutral)]:
    raw_factor = raw_fn(panel)
    sector_var_share = bi.sector_variance_share(raw_factor, panel)
    for h in ["1M", "1Y"]:
        card_raw = run(f"H048_{name}_raw_{h}", raw_fn, h)
        card_sn = run(f"H048_{name}_sector_neutral_{h}", sn_fn, h)
        diag[f"{name}_{h}"] = {
            "sector_variance_share_of_raw_factor": sector_var_share,
            "ic_raw": card_raw.get("ic", {}).get("ic_mean"),
            "ic_sector_neutral": card_sn.get("ic", {}).get("ic_mean"),
        }

results["_H048_diagnostic"] = diag
OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"\nWROTE {OUT}")
