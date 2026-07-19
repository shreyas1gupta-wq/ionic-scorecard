"""
WAVE-3 runner: rank-band hysteresis (+ slower p_bear) on the continuous
regime overlay vs static momentum vs un-banded overlay vs discrete switch,
on BOTH panel.parquet (5yr) and panel_long.parquet (21yr), horizon=1Y,
basis=resid only (per task scope -- money-first, 1Y is the horizon the
overlay's bear-IC edge showed up on).

Reuses the ALREADY-EVALUATED baseline cards (un-banded continuous overlay,
static momentum, discrete switch -- all already on the SAME panel/horizon/
basis from the prior W2_contoverlay run) instead of re-running the harness
on unchanged factor definitions -- same convention as _run_w2_contoverlay.py.
"""
import sys, json, traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pandas as pd
from harness import evaluate, load_panel
import builders_w2_overlayband as B

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


horizon = "1Y"

# ---- baselines (reused, already evaluated on the same panel/horizon/basis) ----
# short panel: cont_short_{h} is a real card; staticmom/discrete short were
# themselves reused (not written) in _run_w2_contoverlay.py from these originals.
reuse(f"W2_overlayband_staticmom_short_{horizon}", f"W2_static_momentum_{horizon}")
reuse(f"W2_overlayband_cont_unbanded_short_{horizon}", f"W2_contoverlay_cont_short_{horizon}")
reuse(f"W2_overlayband_discrete_short_{horizon}", f"W2_regimeswitch_trend_{horizon}")
# long panel: all three are real cards written by _run_w2_contoverlay.py.
reuse(f"W2_overlayband_staticmom_long_{horizon}", f"W2_contoverlay_staticmom_long_{horizon}")
reuse(f"W2_overlayband_cont_unbanded_long_{horizon}", f"W2_contoverlay_cont_long_{horizon}")
reuse(f"W2_overlayband_discrete_long_{horizon}", f"W2_contoverlay_discrete_long_{horizon}")

# ---- SHORT panel (5yr) new variants ----
variants_short = {
    "b05": lambda p: B.build_overlay_band_short_b05(p),
    "b10": lambda p: B.build_overlay_band_short_b10(p),
    "b15": lambda p: B.build_overlay_band_short_b15(p),
    "slow63": lambda p: B.build_overlay_slowscore_short(p, smooth_days=63),
    "slow63_b10": lambda p: B.build_overlay_slowscore_band_short(p, smooth_days=63, band=0.10),
}
for tag, fn in variants_short.items():
    fid = f"W2_overlayband_{tag}_short_{horizon}"
    try:
        run(fid, fn(panel_short), horizon, panel_short, src_short)
    except Exception as e:
        results[fid] = {"status": "ERROR", "error": str(e)}
        traceback.print_exc()

# ---- LONG panel (21yr) new variants ----
variants_long = {
    "b05": lambda p: B.build_overlay_band_long_b05(p),
    "b10": lambda p: B.build_overlay_band_long_b10(p),
    "b15": lambda p: B.build_overlay_band_long_b15(p),
    "slow63": lambda p: B.build_overlay_slowscore_long(p, smooth_days=63),
    "slow63_b10": lambda p: B.build_overlay_slowscore_band_long(p, smooth_days=63, band=0.10),
}
for tag, fn in variants_long.items():
    fid = f"W2_overlayband_{tag}_long_{horizon}"
    try:
        run(fid, fn(panel_long), horizon, panel_long, "real_long_panel_long_history")
    except Exception as e:
        results[fid] = {"status": "ERROR", "error": str(e)}
        traceback.print_exc()

out_path = REPORTS_DIR / "W2_overlayband_results.json"
out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
print("wrote", out_path, flush=True)
