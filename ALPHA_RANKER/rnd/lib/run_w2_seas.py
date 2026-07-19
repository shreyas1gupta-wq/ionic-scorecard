"""
Runner: evaluate IDG-G-10 (seasonality), IDG-G-13 (GARP/PEG), IDG-G-14
(earnings stability), IDG-I-05 (SMILE small-tier) against panel_long.parquet
(21yr) via the shared harness. Hard gates = lag_test + placebo (per WAVE
directive); PBO/DSR read as advisory only, matching CONSOLIDATION.md's
money-first fix (harness.verdict() itself still applies its academic
thresholds inside the written card -- this script's printed summary is the
money-first read layered on top, same convention as pragmatic_score_v2.py).
"""
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(__file__))
import harness
import builders_w2_seas as bws

PANEL_PATH = os.path.join(os.path.dirname(__file__), "..", "panel", "panel_long.parquet")


def main():
    import pandas as pd
    panel = pd.read_parquet(PANEL_PATH)
    panel["date"] = pd.to_datetime(panel["date"])
    print("panel_long loaded:", panel.shape, panel["date"].min(), panel["date"].max())

    jobs = [
        ("W2SEAS_seasonality", bws.build_seasonality, "1M"),
        ("W2SEAS_garp_peg", bws.build_garp_peg, "1Y"),
        ("W2SEAS_earn_stability", bws.build_earnings_stability, "1Y"),
        ("W2SEAS_smile_small", bws.build_smile_smallcap, "1Y"),
    ]

    results = {}
    for factor_id, builder_fn, horizon in jobs:
        try:
            factor = builder_fn(panel)
            n = len(factor)
            print(f"\n=== {factor_id} ({horizon}) === n_obs built: {n}")
            if n < 100:
                print("TOO FEW OBS, skipping evaluate()")
                results[factor_id] = {"status": "TOO_FEW_OBS", "n": n}
                continue
            card = harness.evaluate(factor, horizon, return_basis="resid", factor_id=factor_id,
                                     panel=panel, panel_source="real_long", family=factor_id.split("_")[0] + "_" + factor_id.split("_")[1])
            results[factor_id] = card
            ic = card.get("ic", {})
            cost = card.get("costs", {})
            lag = card.get("lag_test", {})
            plac = card.get("placebo", {})
            print(f"  ic_mean={ic.get('ic_mean'):.4f} ic_ir={ic.get('ic_ir'):.3f} "
                  f"mono={card.get('deciles', {}).get('monotonicity')} "
                  f"net_ann={cost.get('net_of_cost_ann_return')} "
                  f"lag_delta={lag.get('lag_test_delta')} placebo={plac.get('placebo_ic')} "
                  f"pbo={card.get('pbo', {}).get('pbo')} verdict={card.get('verdict')}")
        except Exception as e:
            print(f"FAILED {factor_id}: {e}")
            traceback.print_exc()
            results[factor_id] = {"status": "ERROR", "error": str(e)}

    print("\nDONE")


if __name__ == "__main__":
    main()
