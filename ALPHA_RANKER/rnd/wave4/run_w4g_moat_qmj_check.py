"""
Follow-up micro-check, Aditya Verma (R&D), 2026-07-17.
The W4G gap batch (run_w4g_gaps.py) already fully completed (log timestamp
14:04:57, all 4 candidates KILLed) -- it did NOT actually background-exit
early as suspected. What that run did NOT compute was moat_margin_stability's
correlation vs the QMJ leg specifically (it only checked vs mom_resid_peer
and vs the full canonical_7leg composite). This script computes ONLY that
one missing number, synchronously, foreground, cheap (rebuild moat factor +
one per-date Spearman vs quality_QMJ from the existing capstone_legs cache).
No re-run of the harness, no new IC/DSR/PBO computation.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pandas as pd
from scipy import stats
import numpy as np

RND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))

import builders_w4g_gaps as W4G  # noqa: E402

PANEL_LONG_PATH = RND_DIR / "panel" / "panel_long.parquet"
LEGS_CACHE = RND_DIR / "panel" / "capstone_legs.parquet"
CARDS_DIR = RND_DIR / "cards"


def per_date_spearman(factor_a: pd.Series, factor_b: pd.Series, min_names: int = 20) -> dict:
    a = factor_a.rename("a").reset_index()
    b = factor_b.rename("b").reset_index()
    a.columns = ["date", "symbol", "a"]
    b.columns = ["date", "symbol", "b"]
    m = a.merge(b, on=["date", "symbol"], how="inner").dropna()
    rows = []
    for d, g in m.groupby("date"):
        if len(g) < min_names:
            continue
        rho, _ = stats.spearmanr(g["a"], g["b"])
        if np.isfinite(rho):
            rows.append(rho)
    if not rows:
        return {"mean_corr": float("nan"), "n_dates": 0}
    return {"mean_corr": float(np.mean(rows)), "n_dates": len(rows)}


def main():
    print("Loading panel_long + capstone_legs (QMJ leg)...", flush=True)
    panel = pd.read_parquet(PANEL_LONG_PATH)
    panel["date"] = pd.to_datetime(panel["date"])
    legs_raw = pd.read_parquet(LEGS_CACHE)
    legs_raw["date"] = pd.to_datetime(legs_raw["date"])
    print(f"panel_long rows={len(panel)}, capstone_legs rows={len(legs_raw)}", flush=True)

    qmj_leg_names = [l for l in legs_raw["leg"].unique() if "qmj" in l.lower() or "quality" in l.lower()]
    print(f"candidate QMJ-like legs found: {qmj_leg_names}", flush=True)
    assert "quality_QMJ" in legs_raw["leg"].unique(), "quality_QMJ leg missing from capstone_legs.parquet"
    qmj = legs_raw.loc[legs_raw["leg"] == "quality_QMJ"].set_index(["date", "symbol"])["value"].rename("factor")
    print(f"quality_QMJ leg: n_obs={len(qmj)}, n_dates={qmj.index.get_level_values('date').nunique()}", flush=True)

    print("Rebuilding moat_margin_stability factor (same builder as the gap batch)...", flush=True)
    moat = W4G.build_moat_margin_stability_factor(panel[["date", "symbol"]])
    print(f"moat factor: n_obs={len(moat)}, n_dates={moat.index.get_level_values('date').nunique()}", flush=True)

    corr_qmj = per_date_spearman(moat, qmj)
    print(f"corr vs quality_QMJ leg: {corr_qmj}", flush=True)

    full_card_path = CARDS_DIR / "W4G_moat_margin_stability_full.json"
    card = json.loads(full_card_path.read_text(encoding="utf-8"))
    card["corr_vs_QMJ_leg"] = corr_qmj
    full_card_path.write_text(json.dumps(card, indent=2, default=str), encoding="utf-8")
    print(f"appended corr_vs_QMJ_leg to {full_card_path}", flush=True)

    out_path = RND_DIR / "wave4" / "GAPS_BATCH_RESULTS.md"
    text = out_path.read_text(encoding="utf-8")
    marker = "## moat_margin_stability\n"
    idx = text.find(marker)
    assert idx != -1, "moat_margin_stability section not found in GAPS_BATCH_RESULTS.md"
    # insert the QMJ-corr line right after the existing mom_resid_peer corr line
    insert_after = "- corr vs mom_resid_peer leg:"
    line_start = text.find(insert_after, idx)
    line_end = text.find("\n", line_start)
    new_line = f"\n- corr vs QMJ leg (quality_QMJ, orthogonality check): {corr_qmj}"
    if "corr vs QMJ leg" not in text:
        text = text[:line_end] + new_line + text[line_end:]
        out_path.write_text(text, encoding="utf-8")
        print(f"appended QMJ corr line to {out_path}", flush=True)
    else:
        print("QMJ corr line already present, skipped md edit", flush=True)

    print("DONE.", flush=True)


if __name__ == "__main__":
    main()
