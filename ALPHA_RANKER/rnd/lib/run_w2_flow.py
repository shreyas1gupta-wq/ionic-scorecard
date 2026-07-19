"""Runner: W2S-03 (FII/DII accumulation drift) + W2S-04 (promoter buying
drift) through the shared harness. See builders_w2_flow.py for construction
+ DATA-TRUST disclosure. Writes rnd/cards/W2S_flow_*.json and a coverage
summary to rnd/reports/W2S_flow_run.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from harness import evaluate, load_panel
from builders_w2_flow import (
    build_w2s03_fii_dii_accum, build_w2s04_promoter_accum, coverage_report, STALENESS_CAP_DAYS,
)

RND_DIR = Path(__file__).resolve().parents[1]

def main():
    panel = pd.read_parquet(RND_DIR / "panel" / "panel_long.parquet")
    panel_source = "real_panel_long_21yr"
    cov = coverage_report(panel)

    results = {}
    factors = {
        "W2S_flow_fii_dii": build_w2s03_fii_dii_accum,
        "W2S_flow_promoter": build_w2s04_promoter_accum,
    }
    for fid, builder in factors.items():
        factor = builder(panel)
        for horizon in ("1M", "1Y"):
            card_id = f"{fid}_{horizon}"
            card = evaluate(factor, horizon=horizon, return_basis="resid", factor_id=card_id,
                             panel=panel, panel_source=panel_source, family="W2Sflow")
            results[card_id] = {
                "status": card.get("status"), "n_dates": card.get("n_dates"), "n_obs": card.get("n_obs"),
                "ic_ir": card.get("ic", {}).get("ic_ir"), "ic_mean": card.get("ic", {}).get("ic_mean"),
                "mono": card.get("deciles", {}).get("monotonicity"),
                "net_of_cost_ann_return": card.get("costs", {}).get("net_of_cost_ann_return"),
                "lag_test_delta": card.get("lag_test", {}).get("lag_test_delta"),
                "placebo_ic": card.get("placebo", {}).get("placebo_ic"),
                "pbo": card.get("pbo", {}).get("pbo"),
                "dsr": card.get("dsr", {}).get("dsr"),
                "harness_verdict": card.get("verdict"),
            }

    summary = {
        "staleness_cap_days": STALENESS_CAP_DAYS,
        "coverage_vs_full_21yr_panel": cov,
        "coverage_gate": "40pct of panel dates",
        "coverage_verdict": "PARK_THIN_COVERAGE (36.1% < 40% threshold, measured against the full 2005-2025 "
                             "panel_long — the honest denominator since evaluate() scores whatever panel is "
                             "passed in). Numbers below are advisory/diagnostic, not a promote signal.",
        "harness_results": results,
    }
    out_path = RND_DIR / "reports" / "W2S_flow_run.json"
    out_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
