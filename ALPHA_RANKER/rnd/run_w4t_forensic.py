"""
NEXT-SLEEVE candidate test: W4-01 (NOA), W4F-01 (depreciation laxity), W4F-02
(clean-surplus). Arjun Rao (Quant Head), 2026-07-17. Explicitly NOT for the
frozen 7-leg composite -- research only, per task brief.

Pipeline per factor:
  1. harness.evaluate() at 1Y/resid on panel_long.parquet (disc_event_in_window_1Y
     rows NaN'd, same guard as run_long_confirm.py) -- one BASE trial, plus one
     REFINEMENT trial where pre-registered (W4-01 dNOA, W4F-02 dividend-adjusted
     on the 749-firm subset). W4F-01 has no separate refinement (see
     builders_w4t_forensic.py docstring -- the construction field already bakes
     in the hypotheses' own refinement note).
  2. HARD GATES (per task): lag_test_delta <= 0.25 AND |placebo_ic| <= 0.02.
     FAIL either = KILL, independent of harness's own ic_ir-threshold verdict
     string (which uses a positive-only IC_IR gate not applicable here since
     these are honest signed-IC factors, not sign-flipped-for-scoreboard ones).
  3. Incremental value vs the canonical 7-leg composite:
       (a) corr of candidate rank vs canonical_7leg_scores.parquet's
           composite_rank_avg (cross-sectional Spearman, averaged over dates)
       (b) reconstruct the 7-leg equal-weight rank-average from
           capstone_legs.parquet (value_EY, mom_resid_peer, trend_ma65_slope,
           quality_QMJ, bs_issuance, bs_asset_growth, quality_cfo_pat,
           min_legs=5, same convention as CANONICAL_7LEG_1Y.json), evaluate its
           IC_IR, then add the candidate as an 8th leg (min_legs=6) and
           re-evaluate -- delta_IC_IR is the incremental read.
  4. Net-of-cost magnitude with the HORIZON-ANNUALIZATION FIX (per task brief
     and run_incremental_value.py's net_v2 precedent): harness's
     ann_return_LS = mean(ls_ret_raw)*12 unconditionally, which is WRONG for a
     1Y-horizon return series (each ls_ret_raw obs already IS an annual return;
     x12 fabricates a 12x-inflated number). Correct: net_v2 = mean(ls_ret_raw)
     (no x12, since HORIZON_YEARS['1Y']=1.0) minus the (also-uncorrected)
     ann_cost_drag rescaled the same way.
  5. (Any factor whose combined read is SURVIVOR-grade) gets a panel_pit.parquet
     survivorship-free robustness re-run.

Cards written to rnd/cards/W4T_*.json. Results appended to
rnd/wave4/WAVE4_TEST_RESULTS.md.
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))

import harness  # noqa: E402
import run_long_confirm as LC  # noqa: E402
import builders_w4t_forensic as BF  # noqa: E402

CARDS_DIR = RND_DIR / "cards"
REPORTS_DIR = RND_DIR / "reports"
WAVE4_DIR = RND_DIR / "wave4"
CANON_PATH = RND_DIR / "panel" / "canonical_7leg_scores.parquet"
LEGS_CACHE = RND_DIR / "panel" / "capstone_legs.parquet"
PANEL_PIT_PATH = RND_DIR / "panel" / "panel_pit.parquet"
HORIZON = "1Y"
HORIZON_YEARS = {"1M": 1 / 12, "1Y": 1.0, "5Y": 5.0}
SEVEN_LEGS = ["value_EY", "mom_resid_peer", "trend_ma65_slope", "quality_QMJ",
              "bs_issuance", "bs_asset_growth", "quality_cfo_pat"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def net_v2(card: dict) -> float:
    """Horizon-annualization fix: undo harness's blind x12, re-annualize by HORIZON_YEARS."""
    ann_old = card.get("long_short", {}).get("ann_return_LS", np.nan)
    cost_drag_old = card.get("costs", {}).get("ann_cost_drag", 0.0)
    if ann_old is None or not np.isfinite(ann_old):
        return float("nan")
    gross_v2 = (ann_old / 12.0) / HORIZON_YEARS[HORIZON]
    cost_v2 = (cost_drag_old / 12.0) / HORIZON_YEARS[HORIZON] if cost_drag_old is not None and np.isfinite(cost_drag_old) else 0.0
    return gross_v2 - cost_v2


def hard_gates(card: dict) -> dict:
    lag_delta = card.get("lag_test", {}).get("lag_test_delta")
    placebo_ic = card.get("placebo", {}).get("placebo_ic")
    lag_ok = lag_delta is not None and np.isfinite(lag_delta) and lag_delta <= 0.25
    placebo_ok = placebo_ic is not None and np.isfinite(placebo_ic) and abs(placebo_ic) <= 0.02
    return {"lag_test_delta": lag_delta, "lag_pass": bool(lag_ok),
            "placebo_ic": placebo_ic, "placebo_pass": bool(placebo_ok),
            "gates_pass": bool(lag_ok and placebo_ok)}


def avg_spearman(a: pd.Series, b: pd.Series, min_names: int = 20) -> tuple[float, int]:
    sa = a.rename("a").reset_index(); sa.columns = ["date", "symbol", "a"]
    sb = b.rename("b").reset_index(); sb.columns = ["date", "symbol", "b"]
    m = sa.merge(sb, on=["date", "symbol"], how="inner")
    corrs = []
    for _, g in m.groupby("date"):
        if len(g) < min_names:
            continue
        rho, _ = stats.spearmanr(g["a"], g["b"])
        if rho == rho:
            corrs.append(rho)
    return (float(np.mean(corrs)) if corrs else float("nan")), len(corrs)


def rank_avg_from_cache(legs: dict, names: list, min_legs: int) -> pd.Series:
    frames = []
    for n in names:
        r = legs[n].rename("factor").reset_index()
        r.columns = ["date", "symbol", n]
        r[n] = r.groupby("date")[n].rank(pct=True)
        frames.append(r.set_index(["date", "symbol"])[n])
    wide = pd.concat(frames, axis=1)
    combo = wide.mean(axis=1, skipna=True)
    n_present = wide.notna().sum(axis=1)
    combo = combo.where(n_present >= min_legs)
    return combo.dropna().rename("factor")


def eval_with_disc_guard(factor, panel, factor_id, family):
    lbl_raw, lbl_resid = "fwd_ret_1Y_raw", "fwd_ret_1Y_resid"
    disc_col = "disc_event_in_window_1Y"
    p2 = panel.copy()
    mask = p2[disc_col].fillna(0) > 0
    p2.loc[mask, [lbl_raw, lbl_resid]] = np.nan
    card = harness.evaluate(
        factor, HORIZON, return_basis="resid", factor_id=factor_id,
        panel=p2, panel_source="real_panel_long_capstone",
        family=family, write_card=True, cards_dir=CARDS_DIR,
    )
    return card


def summarize(card: dict) -> dict:
    ic = card.get("ic", {})
    dec = card.get("deciles", {})
    return {
        "factor_id": card.get("factor_id"), "ic_mean": ic.get("ic_mean"), "ic_ir": ic.get("ic_ir"),
        "n_ic_dates": ic.get("n_ic_dates"), "mono": dec.get("monotonicity"),
        "net_v2_ann_return": net_v2(card), "dsr": card.get("dsr", {}).get("dsr"),
        "pbo": card.get("pbo", {}).get("pbo"), "n_obs": card.get("n_obs"),
        **hard_gates(card),
    }


def main():
    log("Loading panel_long...")
    panel, close, bench = LC.load_all()
    log(f"panel_long: {panel.shape}, {panel['date'].nunique()} dates, {panel['symbol'].nunique()} symbols")

    log("Loading canonical 7-leg composite scores + capstone_legs cache...")
    canon = pd.read_parquet(CANON_PATH)[["date", "symbol", "composite_rank_avg"]]
    legs_df = pd.read_parquet(LEGS_CACHE)
    legs = {name: g.set_index(["date", "symbol"])["value"].rename("factor") for name, g in legs_df.groupby("leg")}
    missing_legs = [l for l in SEVEN_LEGS if l not in legs]
    if missing_legs:
        raise RuntimeError(f"7-leg reconstruction missing: {missing_legs}")

    log("Reconstructing 7-leg base (min_legs=5, same convention as CANONICAL_7LEG_1Y.json)...")
    base7_factor = rank_avg_from_cache(legs, SEVEN_LEGS, min_legs=5)
    base7_card = eval_with_disc_guard(base7_factor, panel, "W4T_BASE7_RECONSTRUCTED_1Y", "W4T_INCR")
    base7_summary = summarize(base7_card)
    log(f"  7-leg reconstructed IC_IR={base7_summary['ic_ir']:.4f} mono={base7_summary['mono']}")

    log("Building candidate factors...")
    factors = {
        "W4T_01_noa_neg": BF.build_noa_neg(panel),
        "W4T_01_dnoa_neg_refine": BF.build_dnoa_neg(panel),
        "W4TF_01_dep_health": BF.build_dep_health(panel),
        "W4TF_02_clean_surplus_health": BF.build_clean_surplus_health(panel),
        "W4TF_02_clean_surplus_divadj_refine": BF.build_clean_surplus_health_divadj(panel),
    }
    diag = BF._diagnostic_counts()
    log(f"  annual-table diagnostics: {diag}")

    family_map = {
        "W4T_01_noa_neg": "W4T_NOA", "W4T_01_dnoa_neg_refine": "W4T_NOA",
        "W4TF_01_dep_health": "W4T_DEP",
        "W4TF_02_clean_surplus_health": "W4T_CS", "W4TF_02_clean_surplus_divadj_refine": "W4T_CS",
    }
    # which factors get the 8th-leg incremental-value + corr-vs-composite test
    # (the pre-registered BASE construction of each of the 3 hypotheses; refinements
    # get gates+IC only, to keep the trial count disciplined)
    do_incremental = {"W4T_01_noa_neg", "W4TF_01_dep_health", "W4TF_02_clean_surplus_health"}

    rows = []
    for fid, factor in factors.items():
        n_obs = len(factor)
        log(f"Evaluating {fid} ({n_obs} (date,symbol) obs)...")
        card = eval_with_disc_guard(factor, panel, fid, family_map[fid])
        s = summarize(card)
        log(f"  -> IC_IR={s['ic_ir']} lag_delta={s['lag_test_delta']} placebo_ic={s['placebo_ic']} "
            f"gates_pass={s['gates_pass']}")

        corr_composite, n_corr_dates = avg_spearman(factor, canon.set_index(["date", "symbol"])["composite_rank_avg"])

        incr = None
        if fid in do_incremental:
            log(f"  Testing {fid} as 8th equal-weight leg (min_legs=6)...")
            r = factor.rename("factor").reset_index()
            r.columns = ["date", "symbol", fid]
            r[fid] = r.groupby("date")[fid].rank(pct=True)
            cand_ranked = r.set_index(["date", "symbol"])[fid]
            combo8_frames = []
            for n in SEVEN_LEGS:
                rr = legs[n].rename("factor").reset_index()
                rr.columns = ["date", "symbol", n]
                rr[n] = rr.groupby("date")[n].rank(pct=True)
                combo8_frames.append(rr.set_index(["date", "symbol"])[n])
            combo8_frames.append(cand_ranked.rename("factor").to_frame(fid)[fid])
            wide8 = pd.concat(combo8_frames, axis=1)
            combo8 = wide8.mean(axis=1, skipna=True)
            n_present8 = wide8.notna().sum(axis=1)
            combo8 = combo8.where(n_present8 >= 6).dropna().rename("factor")
            card8 = eval_with_disc_guard(combo8, panel, f"W4T_BASE7_plus_{fid}_1Y", "W4T_INCR")
            s8 = summarize(card8)
            delta_ic_ir = s8["ic_ir"] - base7_summary["ic_ir"] if s8["ic_ir"] is not None and base7_summary["ic_ir"] is not None else float("nan")
            incr = {"ic_ir_7leg_base": base7_summary["ic_ir"], "ic_ir_8leg_with_candidate": s8["ic_ir"],
                    "delta_ic_ir": delta_ic_ir, "raises_ir": bool(np.isfinite(delta_ic_ir) and delta_ic_ir > 0)}
            log(f"  -> 8-leg IC_IR={s8['ic_ir']:.4f} vs 7-leg={base7_summary['ic_ir']:.4f} delta={delta_ic_ir:.4f}")

        rows.append({
            "factor_id": fid, "family": family_map[fid], **s,
            "corr_vs_composite": corr_composite, "n_corr_dates": n_corr_dates,
            "incremental_8leg": incr,
        })

    # ---- verdicts ----
    def verdict_for(row):
        if not row["gates_pass"]:
            return "KILL (hard gate fail)"
        corr = row["corr_vs_composite"]
        orth = np.isfinite(corr) and abs(corr) < 0.3
        net = row["net_v2_ann_return"]
        econ_ok = np.isfinite(net) and net > 0
        raises_ir = row["incremental_8leg"]["raises_ir"] if row["incremental_8leg"] else None
        if orth and econ_ok and (raises_ir is True):
            return "SURVIVOR"
        if econ_ok or orth:
            return "CANDIDATE"
        return "KILL (weak/redundant)"

    for r in rows:
        r["verdict"] = verdict_for(r)

    # ---- panel_pit robustness for any SURVIVOR ----
    survivors = [r for r in rows if r["verdict"] == "SURVIVOR"]
    if survivors and PANEL_PIT_PATH.exists():
        log(f"Running panel_pit.parquet (survivorship-free) robustness on {len(survivors)} survivor(s)...")
        panel_pit = pd.read_parquet(PANEL_PIT_PATH)
        panel_pit["date"] = pd.to_datetime(panel_pit["date"])
        builder_fn_map = {
            "W4T_01_noa_neg": BF.build_noa_neg, "W4T_01_dnoa_neg_refine": BF.build_dnoa_neg,
            "W4TF_01_dep_health": BF.build_dep_health,
            "W4TF_02_clean_surplus_health": BF.build_clean_surplus_health,
            "W4TF_02_clean_surplus_divadj_refine": BF.build_clean_surplus_health_divadj,
        }
        BF._CACHE.pop("annual", None)  # force rebuild against panel_pit's symbol/sector universe
        for r in survivors:
            fid = r["factor_id"]
            factor_pit = builder_fn_map[fid](panel_pit)
            card_pit = eval_with_disc_guard(factor_pit, panel_pit, f"{fid}_PIT_robustness", family_map[fid])
            r["pit_robustness"] = summarize(card_pit)
            log(f"  {fid} PIT robustness: IC_IR={r['pit_robustness']['ic_ir']} gates_pass={r['pit_robustness']['gates_pass']}")
        BF._CACHE.pop("annual", None)  # restore for any downstream re-use against panel_long

    # ---- write outputs ----
    out_json = REPORTS_DIR / "W4T_forensic_next_sleeve_results.json"
    out_json.write_text(json.dumps({"base7_reconstructed": base7_summary, "candidates": rows},
                                    indent=2, default=str), encoding="utf-8")
    log(f"Wrote {out_json}")

    md_path = WAVE4_DIR / "WAVE4_TEST_RESULTS.md"
    lines = []
    if not md_path.exists():
        lines.append("# WAVE-4 Test Results\n\n")
        lines.append("| Factor | Horizon | Signed IC_IR (1Y) | Gates (lag/placebo) | Corr vs 7-leg composite | Incremental IR delta (8th leg) | Verdict |\n")
        lines.append("|---|---|---|---|---|---|---|\n")
    lines.append(f"\n## {time.strftime('%Y-%m-%d')} -- NEXT-SLEEVE forensic candidates (Arjun Rao)\n\n")
    lines.append("Base 7-leg reconstructed (min_legs=5, capstone_legs.parquet cache) for reference: "
                  f"IC_IR={base7_summary['ic_ir']:.4f}, mono={base7_summary['mono']}, "
                  f"gates_pass={base7_summary['gates_pass']} (frozen composite itself is NOT touched; "
                  f"this is a research-only recombination).\n\n")
    lines.append("| Factor | Horizon | Signed IC_IR (1Y) | Gates (lag<=0.25 / |placebo|<=0.02) | Corr vs 7-leg composite | Incremental IR delta (8th leg) | Verdict |\n")
    lines.append("|---|---|---|---|---|---|---|\n")
    for r in rows:
        incr_str = f"{r['incremental_8leg']['delta_ic_ir']:.4f}" if r["incremental_8leg"] else "n/a (refinement, not tested)"
        gates_str = f"lag={r['lag_test_delta']:.3f}({'P' if r['lag_pass'] else 'F'})/placebo={r['placebo_ic']:.4f}({'P' if r['placebo_pass'] else 'F'})"
        corr_str = f"{r['corr_vs_composite']:.3f}" if np.isfinite(r["corr_vs_composite"]) else "n/a"
        lines.append(f"| {r['factor_id']} ({r['family']}) | 1Y | {r['ic_ir']:.4f} | {gates_str} | {corr_str} | {incr_str} | {r['verdict']} |\n")
    with md_path.open("a", encoding="utf-8") as f:
        f.writelines(lines)
    log(f"Appended to {md_path}")

    # ---- individual W4T_ cards (per-factor summary, distinct from harness's raw *.json cards) ----
    for r in rows:
        card_path = CARDS_DIR / f"{r['factor_id']}_SUMMARY.json"
        card_path.write_text(json.dumps(r, indent=2, default=str), encoding="utf-8")
    log("Wrote per-factor W4T_*_SUMMARY.json cards")

    print("\n" + "=" * 100)
    for r in rows:
        print(f"{r['factor_id']:45s} IC_IR={r['ic_ir']:+.4f}  gates_pass={r['gates_pass']!s:5s}  "
              f"corr_composite={r['corr_vs_composite']:+.3f}  verdict={r['verdict']}")
    print("=" * 100)


if __name__ == "__main__":
    main()
