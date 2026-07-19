"""
WAVE-3 runner: continuous regime-probability overlay vs static momentum vs
discrete regime-switch, on BOTH panel.parquet (5yr) and panel_long.parquet
(21yr, real bears). Money-first: hard gates = lag_test + placebo only; PBO
reported but advisory (per CONSOLIDATION.md "HARNESS FIXES NEEDED #1").

Reuses existing cards where the comparator was ALREADY evaluated on the SAME
short panel by prior workers (W2_static_momentum_*, W2_regimeswitch_trend_*)
instead of re-running the harness (same factor definition, same panel -- a
re-run would just burn another honest-trial count for no new information).
"""
import sys, json, traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pandas as pd
from harness import evaluate, load_panel
import builders_w2_contoverlay as C

RND_DIR = Path(__file__).parent.parent
CARDS_DIR = RND_DIR / "cards"
REPORTS_DIR = RND_DIR / "reports"

panel_short, src_short = load_panel()
panel_long = pd.read_parquet(RND_DIR / "panel" / "panel_long.parquet")
panel_long["date"] = pd.to_datetime(panel_long["date"])
print(f"panel_short {panel_short.shape} src={src_short}", flush=True)
print(f"panel_long {panel_long.shape} dates={panel_long['date'].nunique()}", flush=True)

results = {}


def _extract(card):
    key = {
        "status": card.get("status"),
        "n_obs": card.get("n_obs"),
        "harness_verdict": card.get("verdict"),
        "ic_ir": card.get("ic", {}).get("ic_ir"),
        "ic_mean": card.get("ic", {}).get("ic_mean"),
        "mono": card.get("deciles", {}).get("monotonicity"),
        "turnover": card.get("turnover", {}).get("avg_top_decile_turnover"),
        "net_of_cost_ann": card.get("costs", {}).get("net_of_cost_ann_return"),
        "lag_delta": card.get("lag_test", {}).get("lag_test_delta"),
        "placebo_ic": card.get("placebo", {}).get("placebo_ic"),
        "pbo": card.get("pbo", {}).get("pbo"),
        "regime_breakdown": card.get("regime_breakdown"),
    }
    lag_ok = key["lag_delta"] is not None and key["lag_delta"] <= 0.25
    placebo_ok = key["placebo_ic"] is not None and abs(key["placebo_ic"]) <= 0.02
    key["money_first_hard_gates"] = "PASS" if (lag_ok and placebo_ok) else "FAIL"
    key["money_first_note"] = "PBO advisory only (not a kill), per CONSOLIDATION.md fix #1"
    return key


def run(fid, factor, horizon, panel, src, family="W2"):
    print(f"-- running {fid} ...", flush=True)
    card = evaluate(factor, horizon, return_basis="resid", factor_id=fid,
                     panel=panel, panel_source=src, family=family, cards_dir=CARDS_DIR)
    key = _extract(card)
    results[fid] = key
    print(fid, key, flush=True)
    return card


def reuse(fid_new, existing_card_name):
    path = CARDS_DIR / f"{existing_card_name}.json"
    card = json.loads(path.read_text(encoding="utf-8"))
    results[fid_new] = _extract(card)
    results[fid_new]["_reused_from"] = existing_card_name
    print(f"-- reused {fid_new} <- {existing_card_name}: {results[fid_new]}", flush=True)


for horizon in ["1M", "1Y"]:
    # ---- SHORT panel (5yr) ----
    try:
        run(f"W2_contoverlay_cont_short_{horizon}", C.build_continuous_overlay_short(panel_short),
            horizon, panel_short, src_short)
    except Exception as e:
        results[f"W2_contoverlay_cont_short_{horizon}"] = {"status": "ERROR", "error": str(e)}
        traceback.print_exc()
    reuse(f"W2_contoverlay_staticmom_short_{horizon}", f"W2_static_momentum_{horizon}")
    reuse(f"W2_contoverlay_discrete_short_{horizon}", f"W2_regimeswitch_trend_{horizon}")

    # ---- LONG panel (21yr, real bears) ----
    try:
        run(f"W2_contoverlay_cont_long_{horizon}", C.build_continuous_overlay_long(panel_long),
            horizon, panel_long, "real_long_panel_long_history")
    except Exception as e:
        results[f"W2_contoverlay_cont_long_{horizon}"] = {"status": "ERROR", "error": str(e)}
        traceback.print_exc()
    try:
        run(f"W2_contoverlay_staticmom_long_{horizon}", C.build_static_momentum_long(panel_long),
            horizon, panel_long, "real_long_panel_long_history")
    except Exception as e:
        results[f"W2_contoverlay_staticmom_long_{horizon}"] = {"status": "ERROR", "error": str(e)}
        traceback.print_exc()
    try:
        run(f"W2_contoverlay_discrete_long_{horizon}", C.build_discrete_switch_long(panel_long),
            horizon, panel_long, "real_long_panel_long_history")
    except Exception as e:
        results[f"W2_contoverlay_discrete_long_{horizon}"] = {"status": "ERROR", "error": str(e)}
        traceback.print_exc()

out_path = REPORTS_DIR / "W2_contoverlay_results.json"
out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
print("wrote", out_path, flush=True)
