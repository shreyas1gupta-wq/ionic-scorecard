"""
Worker driver for H001 / H002 / H042 (65DMA-vs-50DMA bucket).
Runs each pre-registered variant through the shared harness (rnd/lib/harness.py)
exactly once, writes rnd/cards/<id>.json, and dumps a summary table to
rnd/reports/H001_H002_H042_summary.json for the result-card writeup.

Run: python run_ma_hypotheses.py
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import harness  # noqa: E402
import builders_ma as bma  # noqa: E402

HORIZONS = ["1M", "1Y"]
SWEEP_PERIODS = [20, 30, 40, 50, 55, 60, 65, 75, 100, 120, 150, 200]

results = []


def run_one(factor_id, family, builder, horizon, panel, panel_source):
    factor = builder(panel)
    card = harness.evaluate(
        factor, horizon, return_basis="resid", factor_id=factor_id,
        panel=panel, panel_source=panel_source, family=family,
    )
    row = {
        "id": factor_id, "family": family, "horizon": horizon,
        "status": card.get("status"),
        "ic_mean": card.get("ic", {}).get("ic_mean"),
        "ic_ir": card.get("ic", {}).get("ic_ir"),
        "n_dates": card.get("n_dates"),
        "mono": card.get("deciles", {}).get("monotonicity"),
        "ann_ls_gross": card.get("long_short", {}).get("ann_return_LS"),
        "net_of_cost": card.get("costs", {}).get("net_of_cost_ann_return"),
        "dsr": card.get("dsr", {}).get("dsr") if isinstance(card.get("dsr"), dict) else None,
        "pbo": card.get("pbo", {}).get("pbo") if isinstance(card.get("pbo"), dict) else None,
        "lag_delta": card.get("lag_test", {}).get("lag_test_delta"),
        "placebo_ic": card.get("placebo", {}).get("placebo_ic"),
        "verdict": card.get("verdict"),
    }
    results.append(row)
    print(f"{factor_id:30s} {horizon:3s} IC_IR={row['ic_ir']!s:>8} DSR={row['dsr']!s:>8} "
          f"PBO={row['pbo']!s:>6} lag={row['lag_delta']!s:>6} verdict={row['verdict']}")
    return card


def main():
    panel, panel_source = harness.load_panel()
    print(f"panel_source={panel_source} shape={panel.shape}")

    # ---------------- H001: 65DMA vs 50DMA (dist, slope, stack) ----------------
    for horizon in HORIZONS:
        for n, tag in [(50, "50"), (65, "65")]:
            run_one(f"H001_dist{tag}_{horizon}", "H001", bma.dma_distance_factor(n), horizon, panel, panel_source)
            run_one(f"H001_slope{tag}_{horizon}", "H001", bma.dma_slope_factor(n), horizon, panel, panel_source)
            run_one(f"H001_stack{tag}_{horizon}", "H001", bma.dma_stack_factor(n), horizon, panel, panel_source)

    # ---------------- H002: MA-period sweep (dist + slope) ----------------
    for horizon in HORIZONS:
        for n in SWEEP_PERIODS:
            run_one(f"H002_dist{n}_{horizon}", "H002", bma.dma_distance_factor(n), horizon, panel, panel_source)
            run_one(f"H002_slope{n}_{horizon}", "H002", bma.dma_slope_factor(n), horizon, panel, panel_source)

    # ---------------- H042: slope vs distance robustness (65DMA, 1M only) ----------------
    run_one("H042_dist65_1M", "H042", bma.dma_distance_factor(65), "1M", panel, panel_source)
    run_one("H042_slope65_1M", "H042", bma.dma_slope_factor(65), "1M", panel, panel_source)

    out_path = Path(__file__).resolve().parent / "reports" / "H001_H002_H042_summary.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nwrote {len(results)} rows -> {out_path}")


if __name__ == "__main__":
    main()
