"""One-shot runner: IDG-I-02, IDG-I-03, IDG-I-04, IDG-I-06, IDG-I-07
(WAVE worker, India-QV money-first loop, 2026-07-17). basis='resid' throughout.
1Y on the short real panel (panel.parquet); 5Y (where pre-registered) on the
long-history panel (panel_long.parquet), disc-flagged rows excluded from the
5Y target column per PANEL_SCHEMA.md addendum convention (same as
run_long_confirm.py). Also runs each hypothesis's pre-registered incremental
control (single legs / ex-high-leverage subset) so the "must beat X" kill
conditions in backlog_scout.json are answered, not just the composite.
"""
import sys
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import load_panel, evaluate
import builders_w2_indiaqv as bq

RND_DIR = Path(__file__).resolve().parent.parent
CARDS_DIR = RND_DIR / "cards"
PANEL_LONG_PATH = RND_DIR / "panel" / "panel_long.parquet"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_long():
    p = pd.read_parquet(PANEL_LONG_PATH)
    p["date"] = pd.to_datetime(p["date"])
    return p


def run(fid, builder, horizon, panel, panel_source, family):
    factor = builder(panel)
    card = evaluate(factor, horizon, return_basis="resid", factor_id=fid,
                     panel=panel, panel_source=panel_source, family=family,
                     write_card=True, cards_dir=CARDS_DIR)
    ic = card.get("ic", {})
    return {
        "factor_id": fid, "horizon": horizon, "n_obs": card.get("n_obs"),
        "n_dates": card.get("n_dates"),
        "ic_mean": ic.get("ic_mean"), "ic_ir": ic.get("ic_ir"),
        "mono": card.get("deciles", {}).get("monotonicity"),
        "net_cost_ann": card.get("costs", {}).get("net_of_cost_ann_return"),
        "dsr": card.get("dsr", {}).get("dsr"), "pbo": card.get("pbo", {}).get("pbo"),
        "lag_delta": card.get("lag_test", {}).get("lag_test_delta"),
        "placebo_ic": card.get("placebo", {}).get("placebo_ic"),
        "verdict": card.get("verdict"),
    }


def main():
    panel, src = load_panel()
    log(f"short panel: {panel.shape}, src={src}")
    long_panel = load_long()
    log(f"long panel: {long_panel.shape}")

    results = []

    # ---- IDG-I-02 capital-efficiency-at-cycle (1Y + 5Y), + both legs alone ----
    for pnl, src_tag, horizon, suffix in [(panel, src, "1Y", ""), (long_panel, "real_long_panel_long_history", "5Y", "")]:
        p2 = pnl
        if horizon == "5Y":
            disc = p2["disc_event_in_window_5Y"].fillna(0) > 0
            p2 = p2.copy()
            p2.loc[disc, [c for c in p2.columns if c.startswith("fwd_ret_5Y")]] = np.nan
        results.append(run(f"IDG_I_02_capeff_{horizon}", bq.build_capeff_factor, horizon, p2, src_tag, "IDG_I_02"))
        results.append(run(f"IDG_I_02_turnoverslope_only_{horizon}", bq.build_turnover_slope_only, horizon, p2, src_tag, "IDG_I_02"))
        results.append(run(f"IDG_I_02_assetgrowth_only_{horizon}", bq.build_asset_growth_only, horizon, p2, src_tag, "IDG_I_02"))
    log("IDG-I-02 done")

    # ---- IDG-I-03 ROCE-longevity streak (1Y + 5Y) ----
    for pnl, src_tag, horizon in [(panel, src, "1Y"), (long_panel, "real_long_panel_long_history", "5Y")]:
        p2 = pnl
        if horizon == "5Y":
            disc = p2["disc_event_in_window_5Y"].fillna(0) > 0
            p2 = p2.copy()
            p2.loc[disc, [c for c in p2.columns if c.startswith("fwd_ret_5Y")]] = np.nan
        results.append(run(f"IDG_I_03_roce_streak_{horizon}", bq.build_roce_streak_factor, horizon, p2, src_tag, "IDG_I_03"))
    log("IDG-I-03 done")

    # ---- IDG-I-04 under-owned contrarian value (1Y only, per registration) ----
    results.append(run("IDG_I_04_underowned_value_1Y", bq.build_underowned_value_factor, "1Y", panel, src, "IDG_I_04"))
    cov = bq.coverage_report_i04(panel)
    log(f"IDG-I-04 ownership staleness: {cov}")
    log("IDG-I-04 done")

    # ---- IDG-I-06 deleveraging momentum (1Y only) + ex-high-lev control ----
    results.append(run("IDG_I_06_deleveraging_1Y", bq.build_deleveraging_factor, "1Y", panel, src, "IDG_I_06"))
    results.append(run("IDG_I_06_deleveraging_exhighlev_1Y", bq.build_deleveraging_ex_highlev_factor, "1Y", panel, src, "IDG_I_06"))
    log("IDG-I-06 done")

    # ---- IDG-I-07 cumulative CFO/PAT (1Y + 5Y) ----
    for pnl, src_tag, horizon in [(panel, src, "1Y"), (long_panel, "real_long_panel_long_history", "5Y")]:
        p2 = pnl
        if horizon == "5Y":
            disc = p2["disc_event_in_window_5Y"].fillna(0) > 0
            p2 = p2.copy()
            p2.loc[disc, [c for c in p2.columns if c.startswith("fwd_ret_5Y")]] = np.nan
        results.append(run(f"IDG_I_07_cumcfopat_{horizon}", bq.build_cum_cfo_pat_factor, horizon, p2, src_tag, "IDG_I_07"))
    log("IDG-I-07 done")

    df = pd.DataFrame(results)
    out_csv = RND_DIR / "reports" / "IDG_I_indiaqv_summary.csv"
    df.to_csv(out_csv, index=False)
    log(f"Saved summary: {out_csv}")
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(df.to_string())

    (RND_DIR / "reports" / "IDG_I_ownership_coverage.json").write_text(json.dumps(cov, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
