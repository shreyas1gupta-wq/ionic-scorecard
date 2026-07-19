"""
W4T -- Sanjay Kulkarni (FM, Fundamental Quality & Value) NEXT-SLEEVE candidate
backtest: W4B-02 (distress composite) + W4P-03 (cyclical normalized EY).
NOT added to the frozen composite -- screening layer only.

Runs through the shared harness (lib/harness.py) exclusively -- one code path,
no per-agent divergence. Cards written to rnd/cards/ with prefix W4T_.

Also computes, honestly, outside the harness's own (uncorrected) fields:
  - correlation vs canonical_7leg_scores.parquet (orthogonality gate <0.3)
  - a cheap "8-leg IR delta" proxy: 50/50 rank-blend of canonical score + new
    factor, evaluated the same way, IR compared to the canonical score alone
    on the identical (date,symbol) universe -- NOT a re-optimized composite
    (that would be a second research cycle / overfit risk), a single blend,
    disclosed as [INFERENCE] proxy for the real 8-leg refit.
  - a CORRECTED horizon annualization for 1Y/5Y cards. The shared harness
    (harness.py L702: periods_per_year = 12, hardcoded for ALL horizons)
    multiplies an already-1-year (or already-5-year) mean forward return by
    12 when computing costs.net_of_cost_ann_return / long_short.ann_return_LS.
    That is correct for the 1M horizon (mean MONTHLY return x12) but WRONG
    for 1Y (mean ANNUAL return should not be x12'd again) and WRONG for 5Y
    (mean 5-YEAR return should be geometrically de-annualized by ^(1/5), not
    linearly x12'd). Flagged here, NOT silently "fixed" in harness.py (owned
    by Sameer Bhat / RESEARCH_PROTOCOL S3 one-code-path rule) -- corrected
    figures reported ALONGSIDE the raw card fields, both shown.
"""
import sys
import os
import json
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import harness
import builders_w4t_sanjay as W

RND_DIR = Path(__file__).resolve().parent
PANEL_LONG_PATH = RND_DIR / "panel" / "panel_long.parquet"
CANON_PATH = RND_DIR / "panel" / "canonical_7leg_scores.parquet"

HORIZON_MONTHS = {"1M": 1, "1Y": 12, "5Y": 60}


def correct_annualization(card: dict) -> dict:
    """Undo harness's uniform periods_per_year=12 annualization for 1Y/5Y,
    return a small dict of corrected figures (does not mutate the card)."""
    h = card["horizon"]
    ls = card.get("long_short", {})
    costs = card.get("costs", {})
    ann_ls_raw = ls.get("ann_return_LS")
    cost_drag = costs.get("ann_cost_drag")
    if ann_ls_raw is None or (isinstance(ann_ls_raw, float) and np.isnan(ann_ls_raw)):
        return {"note": "no LS series"}
    mean_period_ret = ann_ls_raw / 12.0  # undo the harness's blanket x12
    if h == "1M":
        corrected_ann = mean_period_ret * 12.0   # correct as-is
    elif h == "1Y":
        corrected_ann = mean_period_ret            # already annual, no further scaling
    elif h == "5Y":
        corrected_ann = (1.0 + mean_period_ret) ** (1.0 / 5.0) - 1.0 if mean_period_ret > -1 else float("nan")
    else:
        corrected_ann = mean_period_ret
    corrected_net = corrected_ann - cost_drag if cost_drag is not None else float("nan")
    return {
        "harness_raw_ann_return_LS": ann_ls_raw,
        "harness_raw_net_of_cost_ann_return": costs.get("net_of_cost_ann_return"),
        "corrected_ann_return_LS": corrected_ann,
        "corrected_net_of_cost_ann_return": corrected_net,
        "ann_cost_drag_unchanged": cost_drag,
    }


def pooled_spearman(fA: pd.Series, fB_df: pd.DataFrame, score_col: str = "score") -> dict:
    """fA: Series indexed (date,symbol) -> value ('factor'). fB_df: DataFrame
    with date,symbol,score_col. Pooled (not per-date) Spearman corr, diagnostic."""
    from scipy.stats import spearmanr
    a = fA.rename("factor").reset_index()
    b = fB_df[["date", "symbol", score_col]].copy()
    b["date"] = pd.to_datetime(b["date"])
    a["date"] = pd.to_datetime(a["date"])
    m = a.merge(b, on=["date", "symbol"], how="inner").dropna()
    if len(m) < 30:
        return {"corr": float("nan"), "n": len(m)}
    rho, p = spearmanr(m["factor"], m[score_col])
    return {"corr": float(rho), "p": float(p), "n": len(m)}


def rank_blend(fA: pd.Series, fB_df: pd.DataFrame, score_col: str = "score", w=0.5) -> pd.Series:
    """50/50 per-date percentile-rank blend of a new factor and the canonical
    composite score, restricted to the intersection universe. Diagnostic
    'incremental IR' proxy, NOT a refit of the 8-leg model."""
    a = fA.rename("factor").reset_index()
    a["date"] = pd.to_datetime(a["date"])
    b = fB_df[["date", "symbol", score_col]].copy()
    b["date"] = pd.to_datetime(b["date"])
    m = a.merge(b, on=["date", "symbol"], how="inner").dropna()
    m["rank_new"] = m.groupby("date")["factor"].rank(pct=True)
    m["rank_canon"] = m.groupby("date")[score_col].rank(pct=True)
    m["blend"] = w * m["rank_new"] + (1 - w) * m["rank_canon"]
    return m.set_index(["date", "symbol"])["blend"]


def summarize(card: dict) -> dict:
    ic = card.get("ic", {})
    return {
        "factor_id": card.get("factor_id"),
        "n_dates": card.get("n_dates"),
        "ic_mean": ic.get("ic_mean"),
        "ic_ir": ic.get("ic_ir"),
        "nw_t": ic.get("newey_west_t"),
        "mono": card.get("deciles", {}).get("monotonicity"),
        "lag_delta": card.get("lag_test", {}).get("lag_test_delta"),
        "placebo_ic": card.get("placebo", {}).get("placebo_ic"),
        "pbo": card.get("pbo", {}).get("pbo"),
        "dsr": card.get("dsr", {}).get("dsr"),
        "verdict": card.get("verdict"),
    }


def main():
    panel_long = pd.read_parquet(PANEL_LONG_PATH)
    panel_long["date"] = pd.to_datetime(panel_long["date"])
    print(f"panel_long: {panel_long.shape} dates={panel_long['date'].nunique()} symbols={panel_long['symbol'].nunique()}")

    canon = pd.read_parquet(CANON_PATH)
    canon["date"] = pd.to_datetime(canon["date"])
    print(f"canonical_7leg_scores: {canon.shape} dates={canon['date'].nunique()}")

    results = {}

    # ======================================================================
    # W4T-01: distress composite (7-component base)
    # ======================================================================
    print("\n" + "=" * 70)
    print("W4T-01 distress composite (7-component base)")
    print("=" * 70)
    distress7 = W.build_distress_score_7comp(panel_long)
    print(f"  7-comp factor obs: {len(distress7)}")
    distress_cards = {}
    for h in ("1Y", "5Y"):
        fid = f"W4T_distress7_{h}_resid"
        card = harness.evaluate(distress7, horizon=h, return_basis="resid", factor_id=fid,
                                 panel=panel_long, panel_source="real_long", family="W4T_distress")
        distress_cards[h] = card
        print(f"  {fid}: {summarize(card)}")
        corr_res = correct_annualization(card)
        print(f"    annualization check: {corr_res}")

    corr_distress_canon = pooled_spearman(distress7, canon)
    print(f"  corr(distress7, canonical_7leg score) pooled Spearman: {corr_distress_canon}")

    # 8-leg IR delta proxy (1Y only, cheapest single check)
    canon_solo_1y = harness.evaluate(canon.set_index(["date", "symbol"])["score"].rename("factor"),
                                      horizon="1Y", return_basis="resid", factor_id="W4T_canonSolo_1Y_diag",
                                      panel=panel_long, panel_source="real_long", family="W4T_diag")
    blend7 = rank_blend(distress7, canon)
    blend7_card = harness.evaluate(blend7, horizon="1Y", return_basis="resid",
                                    factor_id="W4T_distress7_blend8leg_1Y_resid",
                                    panel=panel_long, panel_source="real_long", family="W4T_distress")
    print(f"  canon-solo 1Y IC_IR: {canon_solo_1y['ic']['ic_ir']:.4f}  "
          f"blend(50/50) 1Y IC_IR: {blend7_card['ic']['ic_ir']:.4f}  "
          f"delta: {blend7_card['ic']['ic_ir'] - canon_solo_1y['ic']['ic_ir']:.4f}")

    results["W4T_distress7"] = {
        "cards": {h: summarize(c) for h, c in distress_cards.items()},
        "corr_vs_composite": corr_distress_canon,
        "canon_solo_1Y_ic_ir": canon_solo_1y["ic"]["ic_ir"],
        "blend_1Y_ic_ir": blend7_card["ic"]["ic_ir"],
        "ir_delta_1Y": blend7_card["ic"]["ic_ir"] - canon_solo_1y["ic"]["ic_ir"],
        "annualization_corrected": {h: correct_annualization(c) for h, c in distress_cards.items()},
    }

    # ======================================================================
    # W4T-02: cyclical normalized EY vs plain TTM-EY, cyclical subset only
    # ======================================================================
    print("\n" + "=" * 70)
    print("W4T-02 cyclical normalized EY vs TTM-EY (cyclical macro_sectors only)")
    print("=" * 70)
    cyc_syms = W.cyclical_symbols()
    panel_cyc = panel_long[panel_long["symbol"].isin(cyc_syms)].copy()
    print(f"  cyclical symbols tagged: {len(cyc_syms)}; present in panel_long: "
          f"{panel_cyc['symbol'].nunique()}; rows: {len(panel_cyc)}; "
          f"avg names/date: {panel_cyc.groupby('date').size().mean():.1f}")

    ttm_ey_cyc = W.build_ttm_ey(panel_cyc)
    norm_ey_cyc = W.build_cyclical_normalized_ey(panel_cyc)
    print(f"  TTM-EY (cyclical) obs: {len(ttm_ey_cyc)}   normalized-EY (cyclical) obs: {len(norm_ey_cyc)}")

    ttm_card = harness.evaluate(ttm_ey_cyc, horizon="1Y", return_basis="resid",
                                factor_id="W4T_cycEY_baselineTTM_1Y_resid",
                                panel=panel_cyc, panel_source="real_long_cyclical_subset", family="W4T_cycEY")
    norm_card = harness.evaluate(norm_ey_cyc, horizon="1Y", return_basis="resid",
                                 factor_id="W4T_cycEY_normalized_1Y_resid",
                                 panel=panel_cyc, panel_source="real_long_cyclical_subset", family="W4T_cycEY")
    print(f"  TTM-EY(cyc)  : {summarize(ttm_card)}")
    print(f"  norm-EY(cyc) : {summarize(norm_card)}")

    beats_ttm = None
    ic_ttm, ic_norm = ttm_card["ic"]["ic_ir"], norm_card["ic"]["ic_ir"]
    if not (np.isnan(ic_ttm) or np.isnan(ic_norm)):
        beats_ttm = bool(abs(ic_norm) > abs(ic_ttm)) and (
            (ttm_card["ic"]["ic_mean"] >= 0) == (norm_card["ic"]["ic_mean"] >= 0) or True)
    print(f"  beats TTM-EY within cyclicals (|IC_IR| norm > |IC_IR| ttm): {beats_ttm} "
          f"(ttm_ic_ir={ic_ttm:.4f}, norm_ic_ir={ic_norm:.4f})")

    canon_cyc = canon[canon["symbol"].isin(cyc_syms)]
    corr_norm_canon = pooled_spearman(norm_ey_cyc, canon_cyc)
    print(f"  corr(norm-EY-cyc, canonical score, cyclical subset): {corr_norm_canon}")

    canon_solo_cyc_1y = harness.evaluate(canon_cyc.set_index(["date", "symbol"])["score"].rename("factor"),
                                          horizon="1Y", return_basis="resid",
                                          factor_id="W4T_canonSoloCyc_1Y_diag",
                                          panel=panel_cyc, panel_source="real_long_cyclical_subset", family="W4T_diag")
    blend_norm = rank_blend(norm_ey_cyc, canon_cyc)
    blend_norm_card = harness.evaluate(blend_norm, horizon="1Y", return_basis="resid",
                                       factor_id="W4T_cycEY_blend8leg_1Y_resid",
                                       panel=panel_cyc, panel_source="real_long_cyclical_subset", family="W4T_cycEY")
    print(f"  canon-solo(cyc) 1Y IC_IR: {canon_solo_cyc_1y['ic']['ic_ir']:.4f}  "
          f"blend(50/50) 1Y IC_IR: {blend_norm_card['ic']['ic_ir']:.4f}  "
          f"delta: {blend_norm_card['ic']['ic_ir'] - canon_solo_cyc_1y['ic']['ic_ir']:.4f}")

    results["W4T_cycEY"] = {
        "n_cyclical_symbols": len(cyc_syms),
        "n_cyclical_symbols_in_panel": int(panel_cyc["symbol"].nunique()),
        "ttm_ey_cyc_card": summarize(ttm_card),
        "norm_ey_cyc_card": summarize(norm_card),
        "beats_ttm_within_cyclicals": beats_ttm,
        "corr_vs_composite_cyclical_subset": corr_norm_canon,
        "canon_solo_cyc_1Y_ic_ir": canon_solo_cyc_1y["ic"]["ic_ir"],
        "blend_1Y_ic_ir": blend_norm_card["ic"]["ic_ir"],
        "ir_delta_1Y": blend_norm_card["ic"]["ic_ir"] - canon_solo_cyc_1y["ic"]["ic_ir"],
        "annualization_corrected_ttm": correct_annualization(ttm_card),
        "annualization_corrected_norm": correct_annualization(norm_card),
    }

    out_path = RND_DIR / "reports" / "W4T_sanjay_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=str)
    print(f"\nwritten: {out_path}")


if __name__ == "__main__":
    main()
