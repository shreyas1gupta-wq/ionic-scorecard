"""
WAVE worker runner -- IDG-G-06 (BAB), IDG-G-07 (idio-vol), IDG-G-09 (MAX
lottery-demand) against panel_long.parquet (21yr), basis='resid', 1M+1Y,
via the shared harness (lag+placebo hard gates; PBO/DSR advisory per the
money-first pass -- see rnd/pragmatic_score_v2.py for the signed-IC
re-scoring these negative-sign factors need).
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import harness
import builders_w2_lowrisk as B

FACTORS = [
    ("IDG_G06_bab_beta", B.build_bab_beta),
    ("IDG_G07_idiovol", B.build_idiovol),
    ("IDG_G09_maxlottery", B.build_max_lottery),
]
HORIZONS = ["1M", "1Y"]


def main():
    panel = B.load_panel_long()
    print(f"panel_long: {panel.shape}, dates={panel['date'].nunique()}, "
          f"symbols={panel['symbol'].nunique()}")

    results = []
    for fam, builder_fn in FACTORS:
        factor = builder_fn(panel)
        print(f"\n{fam}: {len(factor)} obs")
        for h in HORIZONS:
            factor_id = f"{fam}_{h}_resid"
            card = harness.evaluate(
                factor, horizon=h, return_basis="resid", factor_id=factor_id,
                panel=panel, panel_source="real_long", family=fam,
            )
            results.append(card)
            ic = card.get("ic", {})
            reg = card.get("regime_breakdown", {})
            print(f"  {factor_id}: n_dates={card.get('n_dates')} "
                  f"ic_mean={ic.get('ic_mean'):.4f} ic_ir={ic.get('ic_ir'):.4f} "
                  f"mono={card.get('deciles', {}).get('monotonicity')} "
                  f"lag_delta={card.get('lag_test', {}).get('lag_test_delta'):.3f} "
                  f"placebo={card.get('placebo', {}).get('placebo_ic'):.4f} "
                  f"pbo={card.get('pbo', {}).get('pbo')} "
                  f"verdict_raw={card.get('verdict')}")
            print(f"    regime_trend IC: {reg.get('regime_trend')}")
            print(f"    regime_vol   IC: {reg.get('regime_vol')}")

    out_path = os.path.join(os.path.dirname(__file__), "reports", "W2_lowrisk_results.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nwritten: {out_path}")


if __name__ == "__main__":
    main()
