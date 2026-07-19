"""
WAVE-2 composite evaluation runner. Resume-safe (skips cards already on disk
with status OK), writes rnd/reports/WAVE2_COMPOSITE_results.json.
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import builders_composite as bc
from builders_ma import dma_stack_factor
from harness import run_experiment, load_panel, CARDS_DIR, evaluate

OUT = Path(__file__).parent.parent / "reports" / "WAVE2_COMPOSITE_results.json"

panel, src = load_panel()
print(f"panel_source={src} rows={len(panel)} dates={panel['date'].nunique()} symbols={panel['symbol'].nunique()}")

results = {}


def run(fid, builder, horizon, basis="resid", family=None):
    existing = CARDS_DIR / f"{fid}.json"
    if existing.exists():
        card = json.loads(existing.read_text(encoding="utf-8"))
        if card.get("status") == "OK":
            print(f"-- RESUME (already on disk): {fid}")
        else:
            print(f"-- running {fid} h={horizon} ...")
            card = run_experiment(fid, builder, horizon, basis=basis, panel=panel,
                                   panel_source=src, family=family)
    else:
        print(f"-- running {fid} h={horizon} ...")
        card = run_experiment(fid, builder, horizon, basis=basis, panel=panel,
                               panel_source=src, family=family)
    results[fid] = {
        "horizon": horizon, "status": card.get("status"), "verdict": card.get("verdict"),
        "ic_mean": card.get("ic", {}).get("ic_mean"), "ic_ir": card.get("ic", {}).get("ic_ir"),
        "n_obs": card.get("n_obs"), "n_dates": card.get("n_dates"),
        "monotonicity": card.get("deciles", {}).get("monotonicity"),
        "hit_rate": card.get("long_short", {}).get("hit_rate"),
        "gross_LS": card.get("long_short", {}).get("ann_return_LS"),
        "net_of_cost_ann_return": card.get("costs", {}).get("net_of_cost_ann_return"),
        "turnover": card.get("turnover", {}).get("avg_top_decile_turnover"),
        "pbo": card.get("pbo", {}).get("pbo"), "dsr": card.get("dsr", {}).get("dsr"),
        "lag_test_delta": card.get("lag_test", {}).get("lag_test_delta"),
        "placebo_ic": card.get("placebo", {}).get("placebo_ic"),
    }
    print(f"   -> {fid}: {results[fid]}")
    return card


for h in ["1M", "1Y"]:
    # -- single legs (reuse existing cards where present; H014/H021 need 1M runs) --
    run(f"H001_stack65_{h}", dma_stack_factor(65), h)
    run(f"H004_mom_sharpe12m_{h}", bc.build_mom_sharpe_12m, h)
    run(f"H014_earnings_yield_{h}" if h == "1M" else "H014_earnings_yield", bc.build_H014_earnings_yield, h)
    run(f"H021_grossprof_{h}" if h == "1M" else "H021_grossprof", bc.build_gross_profitability_factor, h)

    # -- composites --
    run(f"COMPO_eqw4_{h}", bc.build_COMPO_eqw4, h, family="COMPO")
    run(f"COMPO_eqw3_ex_quality_{h}", bc.build_COMPO_eqw3_ex_quality, h, family="COMPO")
    run(f"COMPO_turnover_band_{h}", bc.build_COMPO_turnover_band, h, family="COMPO")
    run(f"COMPO_turnover_band_ex_quality_{h}", bc.build_COMPO_turnover_band_ex_quality, h, family="COMPO")

# -- leg correlation matrix (RP-17 orthogonality) --
corr = bc.leg_correlation_matrix(panel, bc.DEFAULT_LEGS)
print("\nLeg correlation matrix (avg per-date Spearman):")
print(corr)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({
    "results": results,
    "leg_correlation_matrix": corr.round(4).to_dict(),
}, indent=2), encoding="utf-8")
print(f"\nWrote {OUT}")
