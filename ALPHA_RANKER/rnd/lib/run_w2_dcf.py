"""
run_w2_dcf.py -- H017 reverse-DCF-implied-growth-gap + 2-stage-DCF value factor,
sensitivity grid (WACC in {11,13,15%} x g_terminal in {3,5%}), basis='resid',
5Y primary + 1Y secondary, evaluated on panel_long.parquet (21yr, has real
fwd_ret_5Y_*). Money-first scoring per task brief: hard gates = lag_test +
placebo; PBO reported but ADVISORY only (per CONSOLIDATION.md harness-fix #1 --
PBO structurally saturates near 1.0 on monthly overlapping-return samples and
was demoted to advisory across this research loop, not a special exception
invented for this factor).
"""
import sys
import time
import json
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import run_experiment  # noqa: E402
import builders_w2_dcf as bdcf  # noqa: E402

ALPHA_DIR = Path(__file__).resolve().parents[2]
PANEL_LONG_PATH = ALPHA_DIR / "rnd" / "panel" / "panel_long.parquet"
CARDS_DIR = ALPHA_DIR / "rnd" / "cards"

import pandas as pd  # noqa: E402

panel = pd.read_parquet(PANEL_LONG_PATH)
panel_source = "real_panel_long_21yr"
print(f"panel_long rows={len(panel)} dates={panel['date'].nunique()} symbols={panel['symbol'].nunique()} "
      f"range=({panel['date'].min()},{panel['date'].max()})")

WACC_GRID = [0.11, 0.13, 0.15]
GTERM_GRID = [0.03, 0.05]
HORIZONS = ["5Y", "1Y"]

results = []


def _money_first_gate(card: dict) -> str:
    """Hard gates = lag_test_delta<=0.25 AND |placebo_ic|<=0.02 (lookahead/
    noise controls). PBO reported, NOT a kill criterion (advisory, per
    CONSOLIDATION.md harness-fix #1)."""
    if card.get("status") != "OK":
        return f"NO_RUN ({card.get('status')})"
    lag = card.get("lag_test", {}).get("lag_test_delta")
    placebo = card.get("placebo", {}).get("placebo_ic")
    ic_ir = card.get("ic", {}).get("ic_ir")
    reasons = []
    if lag is not None and lag == lag and lag > 0.25:
        reasons.append(f"lag_delta {lag:.3f}>0.25")
    if placebo is not None and placebo == placebo and abs(placebo) > 0.02:
        reasons.append(f"|placebo_ic| {abs(placebo):.3f}>0.02")
    if reasons:
        return "KILL (" + "; ".join(reasons) + ")"
    if ic_ir is None or ic_ir != ic_ir:
        return "NO_IC"
    return "PASS"


for horizon in HORIZONS:
    for factor_kind, maker in (("dcfval", bdcf.make_dcf_value_builder),
                                ("revgap", bdcf.make_revgap_builder)):
        for wacc in WACC_GRID:
            for gterm in GTERM_GRID:
                fid = f"W2_dcf_{factor_kind}_w{int(wacc*100)}_g{int(gterm*100)}_{horizon}"
                builder = maker(wacc, gterm)
                t0 = time.time()
                try:
                    card = run_experiment(fid, builder, horizon, basis="resid",
                                           panel=panel, panel_source=panel_source)
                except Exception as e:
                    card = {"factor_id": fid, "status": "ERROR", "error": str(e)}
                    (CARDS_DIR / f"{fid}.json").write_text(json.dumps(card, indent=2))
                dt = time.time() - t0
                gate = _money_first_gate(card)
                row = {
                    "factor_id": fid, "kind": factor_kind, "wacc": wacc, "g_terminal": gterm,
                    "horizon": horizon, "status": card.get("status"),
                    "n_obs": card.get("n_obs"), "n_dates": card.get("n_dates"),
                    "ic_mean": card.get("ic", {}).get("ic_mean"),
                    "ic_ir": card.get("ic", {}).get("ic_ir"),
                    "mono": card.get("deciles", {}).get("monotonicity"),
                    "lag_delta": card.get("lag_test", {}).get("lag_test_delta"),
                    "placebo_ic": card.get("placebo", {}).get("placebo_ic"),
                    "pbo_advisory": card.get("pbo", {}).get("pbo"),
                    "dsr": card.get("dsr", {}).get("dsr"),
                    "net_cost_ann": card.get("costs", {}).get("net_of_cost_ann_return"),
                    "harness_verdict": card.get("verdict"),
                    "money_first_gate": gate,
                }
                results.append(row)
                print(f"{fid} ({dt:.1f}s) IC_IR={row['ic_ir']} gate={gate} harness={row['harness_verdict']}")

df = pd.DataFrame(results)
out_csv = CARDS_DIR / "W2_dcf_sensitivity_summary.csv"
df.to_csv(out_csv, index=False)
print(f"\nwrote {out_csv}")

print("\n=== ROBUSTNESS (sign stability across WACC x g_terminal grid) ===")
for kind in ("dcfval", "revgap"):
    for horizon in HORIZONS:
        sub = df[(df["kind"] == kind) & (df["horizon"] == horizon) & df["ic_ir"].notna()]
        if sub.empty:
            print(f"{kind} {horizon}: NO DATA")
            continue
        signs = set(np.sign(x) for x in sub["ic_ir"] if x == x)
        gates_pass = (sub["money_first_gate"] == "PASS").all()
        print(f"{kind} {horizon}: n={len(sub)} IC_IR range=[{sub['ic_ir'].min():.3f},{sub['ic_ir'].max():.3f}] "
              f"sign_stable={len(signs)<=1} all_gates_pass={gates_pass}")
