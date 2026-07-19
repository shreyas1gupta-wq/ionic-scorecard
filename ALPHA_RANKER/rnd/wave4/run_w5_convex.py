"""
W5 priority-H convex/forensic hypothesis test: W5-01 (cost-elasticity discipline),
W5-02 (implied borrowing cost), W5-04 (net financial slack). Sanjay Kulkarni
task, 2026-07-17, per rnd/wave4/hypotheses_w5.json.

Pipeline per factor (mirrors run_w4t_forensic.py):
  1. harness.evaluate() at 1Y/resid on panel_long.parquet (disc_event guard),
     one BASE trial + pre-registered refinements (W5-01 >=3-down-year gate;
     W5-04 x W5-02 interaction, run ONLY if both bases individually pass gates).
  2. HARD GATES: lag_test_delta <= 0.25 AND |placebo_ic| <= 0.02. PBO/DSR
     reported but ADVISORY only (low-t rule: logic + effect + drop-one, not
     significance thresholds) per task brief.
  3. corr vs 7-leg composite (canonical_7leg_scores.parquet) AND corr vs each
     of the 7 individual legs (nearest-leg identified explicitly, not assumed).
  4. Incremental 8-leg IC_IR delta (BASE constructions only, per trial discipline).
  5. PAYOFF SHAPE per TAIL_CONVEXITY.md method: monthly top-quintile-minus-
     bottom-quintile LS on fwd_ret_1M_raw (disc-event guard), skew, hit rate,
     worst-decile-market-month conditional mean, GFC/COVID/2022 episode means.
     Horizon annualization uses harness.annualize_ls_return (the 2026-07-17
     Manoj Pillai fix) for the honest 1Y-horizon-aware net return.

Cards -> rnd/cards/W5_*.json. Results -> rnd/wave4/GAPS_BATCH_RESULTS.md (new
section) + rnd/wave4/W5_RESULTS.json (raw).
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
WAVE4_DIR = _THIS.parent
RND_DIR = WAVE4_DIR.parent
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))

import harness  # noqa: E402
import run_long_confirm as LC  # noqa: E402
import builders_w5 as BW  # noqa: E402

CARDS_DIR = RND_DIR / "cards"
REPORTS_DIR = RND_DIR / "wave4"
CANON_PATH = RND_DIR / "panel" / "canonical_7leg_scores.parquet"
LEGS_CACHE = RND_DIR / "panel" / "capstone_legs.parquet"
HORIZON = "1Y"
SEVEN_LEGS = ["value_EY", "mom_resid_peer", "trend_ma65_slope", "quality_QMJ",
              "bs_issuance", "bs_asset_growth", "quality_cfo_pat"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def hard_gates(card: dict) -> dict:
    lag_delta = card.get("lag_test", {}).get("lag_test_delta")
    placebo_ic = card.get("placebo", {}).get("placebo_ic")
    lag_ok = lag_delta is not None and np.isfinite(lag_delta) and lag_delta <= 0.25
    placebo_ok = placebo_ic is not None and np.isfinite(placebo_ic) and abs(placebo_ic) <= 0.02
    return {"lag_test_delta": lag_delta, "lag_pass": bool(lag_ok),
            "placebo_ic": placebo_ic, "placebo_pass": bool(placebo_ok),
            "gates_pass": bool(lag_ok and placebo_ok)}


def net_v2(card: dict) -> float:
    """Horizon-aware net return using harness.annualize_ls_return (already
    correct for 1Y: divides by HORIZON_YEARS['1Y']=1.0, i.e. no scaling)."""
    ls = card.get("long_short", {})
    ann_hz = ls.get("ann_return_LS_horizon_aware")
    cost_hz = card.get("costs", {}).get("net_of_cost_ann_return_horizon_aware")
    return cost_hz if cost_hz is not None else ann_hz


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
        "net_v2_horizon_aware_ann_return": net_v2(card), "dsr": card.get("dsr", {}).get("dsr"),
        "pbo": card.get("pbo", {}).get("pbo"), "n_obs": card.get("n_obs"),
        **hard_gates(card),
    }


# ==========================================================================
# payoff-shape (TAIL_CONVEXITY.md method), 1M horizon
# ==========================================================================
def ls_series_1m(factor: pd.Series, panel_ret: pd.DataFrame, q: int = 5) -> tuple[pd.Series, int]:
    f = factor.rename("factor").reset_index()
    f.columns = ["date", "symbol", "factor"]
    sub = f.merge(panel_ret, on=["date", "symbol"], how="inner").dropna(subset=["factor", "fwd_ret_1M_raw"])
    out = {}
    n_dropped = 0
    for d, g in sub.groupby("date"):
        if len(g) < 15:
            n_dropped += 1
            continue
        try:
            g = g.copy()
            g["qtile"] = pd.qcut(g["factor"], q, labels=False, duplicates="drop")
        except ValueError:
            n_dropped += 1
            continue
        qmax = g["qtile"].max()
        top = g.loc[g["qtile"] == qmax, "fwd_ret_1M_raw"].mean()
        bot = g.loc[g["qtile"] == 0, "fwd_ret_1M_raw"].mean()
        out[d] = top - bot
    return pd.Series(out).sort_index(), n_dropped


def payoff_shape(factor: pd.Series, panel_ret: pd.DataFrame, mkt_fwd: pd.Series,
                  worst_decile_dates: set, episodes: dict) -> dict:
    ls, n_dropped = ls_series_1m(factor, panel_ret)
    if len(ls) < 12:
        return {"error": f"insufficient dates n={len(ls)}"}
    wins, losses = ls[ls > 0], ls[ls < 0]
    hit_rate = len(wins) / len(ls)
    avg_win = float(wins.mean()) if len(wins) else None
    avg_loss = float(losses.mean()) if len(losses) else None
    skew = float(stats.skew(ls.values))
    tail_dates = [d for d in ls.index if d in worst_decile_dates]
    tail_mean = float(ls.loc[tail_dates].mean()) if tail_dates else None
    ep_stats = {}
    for name, dates in episodes.items():
        dd = [d for d in dates if d in ls.index]
        ep_stats[name] = {
            "n_months": len(dd),
            "mean_LS": float(ls.loc[dd].mean()) if dd else None,
            "worst_LS": float(ls.loc[dd].min()) if dd else None,
        }
    return {
        "n_dates": int(len(ls)), "n_dates_dropped_thin": int(n_dropped),
        "mean_LS_monthly": float(ls.mean()), "hit_rate": float(hit_rate),
        "avg_win": avg_win, "avg_loss": avg_loss, "skew": skew,
        "worst_month_LS": float(ls.min()), "worst_month_date": str(ls.idxmin().date()),
        "best_month_LS": float(ls.max()),
        "mean_LS_worst_decile_mkt_months": tail_mean,
        "episodes": ep_stats,
    }


def classify_shape(shape: dict) -> str:
    if "error" in shape:
        return "CANNOT ASSESS"
    skew = shape["skew"]
    ep = shape["episodes"]
    covid = ep.get("COVID_2020-02_03", {}).get("mean_LS")
    selloff = ep.get("SELLOFF_2022", {}).get("mean_LS")
    gfc = ep.get("GFC_2008-09", {}).get("mean_LS")
    crash_means = [x for x in (covid, selloff, gfc) if x is not None]
    n_pos_crash = sum(1 for x in crash_means if x > 0)
    if skew > 0.5 and crash_means and n_pos_crash >= max(1, len(crash_means) - 1):
        return "CONVEX-leaning"
    if skew < -0.5:
        return "CONCAVE"
    return "LINEAR/mixed"


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

    log("Reconstructing 7-leg base (min_legs=5)...")
    base7_factor = rank_avg_from_cache(legs, SEVEN_LEGS, min_legs=5)
    base7_card = eval_with_disc_guard(base7_factor, panel, "W5_BASE7_RECONSTRUCTED_1Y", "W5_INCR")
    base7_summary = summarize(base7_card)
    log(f"  7-leg reconstructed IC_IR={base7_summary['ic_ir']:.4f} mono={base7_summary['mono']}")

    log("Building W5 candidate factors (annual table build is the slow step)...")
    t0 = time.time()
    factors = {
        "W5_01_cost_elasticity_base": BW.build_w501_base(panel),
        "W5_01_cost_elasticity_refine": BW.build_w501_refine(panel),
        "W5_02_implied_borrow_cost_base": BW.build_w502_base(panel),
        "W5_04_net_fin_slack_base": BW.build_w504_base(panel),
    }
    diag = BW._diagnostic_counts()
    log(f"  annual-table diagnostics: {diag}  (build took {time.time()-t0:.1f}s)")
    for k, v in factors.items():
        log(f"  {k}: n_obs={len(v)}")

    family_map = {
        "W5_01_cost_elasticity_base": "W5_01", "W5_01_cost_elasticity_refine": "W5_01",
        "W5_02_implied_borrow_cost_base": "W5_02",
        "W5_04_net_fin_slack_base": "W5_04",
    }
    do_incremental = {"W5_01_cost_elasticity_base", "W5_02_implied_borrow_cost_base", "W5_04_net_fin_slack_base"}

    rows = []
    for fid, factor in factors.items():
        log(f"Evaluating {fid} ({len(factor)} (date,symbol) obs)...")
        card = eval_with_disc_guard(factor, panel, fid, family_map[fid])
        s = summarize(card)
        log(f"  -> IC_IR={s['ic_ir']} lag_delta={s['lag_test_delta']} placebo_ic={s['placebo_ic']} gates_pass={s['gates_pass']}")

        corr_composite, n_corr_dates = avg_spearman(factor, canon.set_index(["date", "symbol"])["composite_rank_avg"])
        corr_vs_legs = {}
        for leg_name in SEVEN_LEGS:
            c, _ = avg_spearman(factor, legs[leg_name])
            corr_vs_legs[leg_name] = c
        nearest_leg = max(corr_vs_legs, key=lambda k: abs(corr_vs_legs[k]) if corr_vs_legs[k] == corr_vs_legs[k] else -1)

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
            card8 = eval_with_disc_guard(combo8, panel, f"W5_BASE7_plus_{fid}_1Y", "W5_INCR")
            s8 = summarize(card8)
            delta_ic_ir = (s8["ic_ir"] - base7_summary["ic_ir"]
                           if s8["ic_ir"] is not None and base7_summary["ic_ir"] is not None else float("nan"))
            incr = {"ic_ir_7leg_base": base7_summary["ic_ir"], "ic_ir_8leg_with_candidate": s8["ic_ir"],
                    "delta_ic_ir": delta_ic_ir, "raises_ir": bool(np.isfinite(delta_ic_ir) and delta_ic_ir > 0)}
            log(f"  -> 8-leg IC_IR={s8['ic_ir']:.4f} vs 7-leg={base7_summary['ic_ir']:.4f} delta={delta_ic_ir:.4f}")

        rows.append({
            "factor_id": fid, "family": family_map[fid], **s,
            "corr_vs_composite": corr_composite, "n_corr_dates": n_corr_dates,
            "corr_vs_legs": corr_vs_legs, "nearest_leg": nearest_leg,
            "nearest_leg_corr": corr_vs_legs[nearest_leg],
            "incremental_8leg": incr,
        })

    # ---- W5-04 x W5-02 interaction refinement, only if BOTH bases pass hard gates ----
    row02 = next(r for r in rows if r["factor_id"] == "W5_02_implied_borrow_cost_base")
    row04 = next(r for r in rows if r["factor_id"] == "W5_04_net_fin_slack_base")
    interaction_result = None
    if row02["gates_pass"] and row04["gates_pass"]:
        log("Both W5-02 and W5-04 bases pass hard gates -> running interaction refinement...")
        f02 = factors["W5_02_implied_borrow_cost_base"].rename("f02").reset_index()
        f02.columns = ["date", "symbol", "f02"]
        f04 = factors["W5_04_net_fin_slack_base"].rename("f04").reset_index()
        f04.columns = ["date", "symbol", "f04"]
        inter = f02.merge(f04, on=["date", "symbol"], how="inner")
        inter["f02_rank"] = inter.groupby("date")["f02"].rank(pct=True)
        inter["f04_rank"] = inter.groupby("date")["f04"].rank(pct=True)
        inter["interaction"] = inter[["f02_rank", "f04_rank"]].mean(axis=1)
        inter_factor = inter.set_index(["date", "symbol"])["interaction"]
        card_int = eval_with_disc_guard(inter_factor, panel, "W5_04x02_interaction_refine", "W5_04")
        interaction_result = summarize(card_int)
        log(f"  -> interaction IC_IR={interaction_result['ic_ir']} gates_pass={interaction_result['gates_pass']}")
    else:
        log(f"Interaction refinement SKIPPED (W5-02 gates_pass={row02['gates_pass']}, "
            f"W5-04 gates_pass={row04['gates_pass']}) -- per hypothesis, 'only if both bases pass individually'.")

    # ---- payoff shape (1M, all base+refine factors) ----
    log("Building 1M market-forward series + crash episodes for payoff-shape...")
    bench_nifty500 = bench["NIFTY500"] if isinstance(bench, pd.DataFrame) else bench
    bench_nifty500.index = pd.to_datetime(bench_nifty500.index)
    panel_dates = sorted(panel["date"].unique())
    mkt_fwd = {}
    for i, d in enumerate(panel_dates[:-1]):
        d_next = panel_dates[i + 1]
        if d in bench_nifty500.index and d_next in bench_nifty500.index:
            mkt_fwd[d] = bench_nifty500.loc[d_next] / bench_nifty500.loc[d] - 1.0
    mkt_fwd = pd.Series(mkt_fwd).sort_index()
    worst_decile_cut = mkt_fwd.quantile(0.10)
    worst_decile_dates = set(mkt_fwd[mkt_fwd <= worst_decile_cut].index)
    EPISODES = {
        "GFC_2008-09": [d for d in panel_dates if pd.Timestamp("2008-08-01") <= d <= pd.Timestamp("2009-03-01")],
        "COVID_2020-02_03": [d for d in panel_dates if pd.Timestamp("2020-01-15") <= d <= pd.Timestamp("2020-03-31")],
        "SELLOFF_2022": [d for d in panel_dates if pd.Timestamp("2021-12-15") <= d <= pd.Timestamp("2022-06-30")],
    }
    log(f"worst-decile cutoff={worst_decile_cut:.4f}, n_worst_decile_months={len(worst_decile_dates)}")

    panel_ret = panel[["date", "symbol", "fwd_ret_1M_raw", "disc_event_in_window_1M"]].copy()
    mask1m = panel_ret["disc_event_in_window_1M"].fillna(0) > 0
    panel_ret.loc[mask1m, "fwd_ret_1M_raw"] = np.nan
    panel_ret = panel_ret[["date", "symbol", "fwd_ret_1M_raw"]]

    shapes = {}
    for fid, factor in factors.items():
        log(f"Payoff-shape for {fid}...")
        shp = payoff_shape(factor, panel_ret, mkt_fwd, worst_decile_dates, EPISODES)
        shapes[fid] = shp
        shapes[fid]["shape_class"] = classify_shape(shp)
        if "error" not in shp:
            log(f"  n={shp['n_dates']} skew={shp['skew']:+.2f} hit={shp['hit_rate']:.2f} "
                f"worst_decile_mean={shp['mean_LS_worst_decile_mkt_months']} class={shapes[fid]['shape_class']}")
    if interaction_result is not None:
        shp = payoff_shape(inter_factor, panel_ret, mkt_fwd, worst_decile_dates, EPISODES)
        shp["shape_class"] = classify_shape(shp)
        shapes["W5_04x02_interaction_refine"] = shp

    # ---- verdicts ----
    def verdict_for(row):
        if not row["gates_pass"]:
            return "KILL (hard gate fail)"
        corr = row["corr_vs_composite"]
        orth = np.isfinite(corr) and abs(corr) < 0.3
        net = row["net_v2_horizon_aware_ann_return"]
        econ_ok = net is not None and np.isfinite(net) and net > 0
        raises_ir = row["incremental_8leg"]["raises_ir"] if row["incremental_8leg"] else None
        shp = shapes.get(row["factor_id"], {})
        convex_hedge_candidate = shp.get("shape_class") == "CONVEX-leaning"
        if orth and (econ_ok or convex_hedge_candidate) and (raises_ir is True or raises_ir is None):
            return "CANDIDATE (convex-hedge)" if (convex_hedge_candidate and not econ_ok) else "CANDIDATE"
        if not orth:
            return "KILL (redundant, corr>=0.3)"
        return "PARK (weak linear + not convex)"

    for r in rows:
        r["verdict"] = verdict_for(r)
        r["convex_hedge_candidate"] = shapes.get(r["factor_id"], {}).get("shape_class") == "CONVEX-leaning"

    # ---- write outputs ----
    out_json = REPORTS_DIR / "W5_RESULTS.json"
    out_json.write_text(json.dumps({
        "base7_reconstructed": base7_summary,
        "candidates": rows,
        "interaction_refinement": interaction_result,
        "payoff_shapes": shapes,
        "diagnostics": diag,
        "worst_decile_cutoff": float(worst_decile_cut),
        "n_worst_decile_months": len(worst_decile_dates),
    }, indent=2, default=str), encoding="utf-8")
    log(f"Wrote {out_json}")

    md_path = WAVE4_DIR / "GAPS_BATCH_RESULTS.md"
    lines = []
    lines.append(f"\n\n## {time.strftime('%Y-%m-%d')} -- W5 priority-H convex/forensic candidates (Sanjay Kulkarni task)\n\n")
    lines.append("Base 7-leg reconstructed (min_legs=5, capstone_legs.parquet cache) for reference: "
                  f"IC_IR={base7_summary['ic_ir']:.4f}, mono={base7_summary['mono']}, "
                  f"gates_pass={base7_summary['gates_pass']} (frozen composite itself is NOT touched -- research only).\n\n")
    lines.append("| Factor | Signed IC_IR (1Y) | Hard gates (lag<=0.25/|placebo|<=0.02) | Corr vs composite | Nearest leg (corr) | Incr. 8-leg IR delta | Skew (1M LS) | Crash-episode mean (COVID/2022/GFC) | Shape | Verdict |\n")
    lines.append("|---|---|---|---|---|---|---|---|---|---|\n")
    for r in rows:
        incr_str = f"{r['incremental_8leg']['delta_ic_ir']:.4f}" if r["incremental_8leg"] else "n/a"
        gates_str = f"lag={r['lag_test_delta']:.3f}({'P' if r['lag_pass'] else 'F'})/placebo={r['placebo_ic']:.4f}({'P' if r['placebo_pass'] else 'F'})"
        corr_str = f"{r['corr_vs_composite']:.3f}" if np.isfinite(r["corr_vs_composite"]) else "n/a"
        nearest_str = f"{r['nearest_leg']} ({r['nearest_leg_corr']:.3f})"
        shp = shapes.get(r["factor_id"], {})
        if "error" in shp:
            skew_str, crash_str, shape_str = "n/a", "n/a", shp.get("shape_class", "n/a")
        else:
            skew_str = f"{shp['skew']:+.2f}"
            ep = shp["episodes"]
            def em(k):
                v = ep.get(k, {}).get("mean_LS")
                return f"{v*100:+.1f}%" if v is not None else "no data"
            crash_str = f"COVID {em('COVID_2020-02_03')} / 2022 {em('SELLOFF_2022')} / GFC {em('GFC_2008-09')}"
            shape_str = shp["shape_class"]
        lines.append(f"| {r['factor_id']} | {r['ic_ir']:.4f} | {gates_str} | {corr_str} | {nearest_str} | {incr_str} | {skew_str} | {crash_str} | {shape_str} | {r['verdict']} |\n")
    if interaction_result:
        lines.append(f"| W5_04x02_interaction_refine | {interaction_result['ic_ir']:.4f} | "
                     f"lag={interaction_result['lag_test_delta']:.3f}({'P' if interaction_result['lag_pass'] else 'F'})/"
                     f"placebo={interaction_result['placebo_ic']:.4f}({'P' if interaction_result['placebo_pass'] else 'F'}) | "
                     f"n/a | n/a | n/a | n/a | n/a | n/a | ran-conditionally |\n")
    lines.append(f"\nDiagnostics: {json.dumps(diag)}\n")
    lines.append(f"Worst-decile market-month cutoff: {worst_decile_cut:.4f} ({len(worst_decile_dates)} months).\n")
    with md_path.open("a", encoding="utf-8") as f:
        f.writelines(lines)
    log(f"Appended to {md_path}")

    for r in rows:
        card_path = CARDS_DIR / f"{r['factor_id']}_SUMMARY.json"
        card_path.write_text(json.dumps({**r, "payoff_shape": shapes.get(r["factor_id"])}, indent=2, default=str), encoding="utf-8")
    log("Wrote per-factor W5_*_SUMMARY.json cards")

    print("\n" + "=" * 110)
    for r in rows:
        print(f"{r['factor_id']:35s} IC_IR={r['ic_ir']:+.4f}  gates_pass={r['gates_pass']!s:5s}  "
              f"corr_composite={r['corr_vs_composite']:+.3f}  nearest={r['nearest_leg']}({r['nearest_leg_corr']:+.3f})  "
              f"shape={shapes.get(r['factor_id'],{}).get('shape_class')}  verdict={r['verdict']}")
    print("=" * 110)


if __name__ == "__main__":
    main()
