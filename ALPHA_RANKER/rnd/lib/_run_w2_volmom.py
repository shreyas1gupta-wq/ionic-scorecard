"""
WAVE-2 runner: evaluate all vol-scaled-momentum refinement variants
(builders_w2_volmom.py) against the real panel, basis=resid, horizons 1M & 1Y.
Writes cards to rnd/cards/W2_volmom_*.json and prints a compact table.
"""
from __future__ import annotations
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness as H
import builders_w2_volmom as B

panel, panel_source = H.load_panel()
print(f"panel_source={panel_source} shape={panel.shape}")

VARIANTS = {
    "W2_volmom_blend3_6_12": B.build_volmom_blend_3_6_12,
    "W2_volmom_skip1m_12m": B.build_mom_sharpe12m_skip1m,
    "W2_volmom_rankband_b05_12m": B.build_rankband_sharpe12m_b05,
    "W2_volmom_rankband_b10_12m": B.build_rankband_sharpe12m_b10,
    "W2_volmom_rankband_b15_12m": B.build_rankband_sharpe12m_b15,
    "W2_volmom_winsor_12m": B.build_mom_sharpe12m_winsor,
    "W2_volmom_combo_blend_rankband10": B.build_combo_blend_rankband,
}

results = {}
for name, builder_fn in VARIANTS.items():
    print(f"building {name} ...")
    factor = builder_fn(panel)
    print(f"  factor obs: {len(factor)}")
    for horizon in ("1M", "1Y"):
        fid = f"{name}_{horizon}"
        card = H.evaluate(factor, horizon, return_basis="resid", factor_id=fid,
                           panel=panel, panel_source=panel_source, family="W2")
        results[fid] = card
        ic = card.get("ic", {})
        dec = card.get("deciles", {})
        ls = card.get("long_short", {})
        to = card.get("turnover", {})
        pbo = card.get("pbo", {})
        lag = card.get("lag_test", {})
        pla = card.get("placebo", {})
        cost = card.get("costs", {})
        print(f"  {fid:38s} IC_IR={ic.get('ic_ir'):.3f} mono={dec.get('monotonicity'):.3f} "
              f"hit={ls.get('hit_rate'):.3f} net_LS={cost.get('net_of_cost_ann_return'):.3f} "
              f"TO={to.get('avg_top_decile_turnover'):.3f} PBO={pbo.get('pbo'):.3f} "
              f"lag_d={lag.get('lag_test_delta'):.3f} placebo={pla.get('placebo_ic'):.4f} "
              f"-> {card.get('verdict')}")

out_path = Path(__file__).resolve().parents[1] / "cards" / "_W2_volmom_summary.json"
out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
print(f"\nsummary written: {out_path}")
