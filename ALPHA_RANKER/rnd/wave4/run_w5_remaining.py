"""
Remaining buildable W5 forensic/quality hypotheses (Sanjay Kulkarni task,
2026-07-17): W5-05 (treasury bloat / diworsification), W5-06 (dividend
continuity under earnings stress), W5-07 (borrowed dividends red flag),
W5-08 (moat proxy: OPM level x stability, 5Y). Per rnd/wave4/hypotheses_w5.json.

Reuses run_w5_convex.py's helper functions (hard_gates, avg_spearman,
rank_avg_from_cache, eval_with_disc_guard, summarize, payoff_shape,
classify_shape) -- ONE code path for the harness contract, no re-derivation.

Pipeline per factor:
  1. harness.evaluate() at 1Y/resid (disc_event guard) -- BASE trial +
     pre-registered refinement only where specified (W5-07 CFO condition).
     W5-08 additionally evaluated at 5Y (its own stated PRIMARY horizon;
     1Y kept as the secondary/comparable-to-composite cut).
  2. HARD GATES: lag_test_delta <= 0.25 AND |placebo_ic| <= 0.02 (PBO/DSR
     advisory only, low-t rule).
  3. corr vs 7-leg composite (canonical_7leg_scores.parquet) AND vs each of
     the 7 individual legs (nearest leg identified explicitly).
  4. Incremental 8-leg IC_IR delta -- BUT gated on a FRESH sanity check that
     this run's own 7-leg reconstruction reproduces the official IC_IR=1.345
     before any 8-leg number is trusted (per task brief -- prior W5-01/02/04
     run reconstructed 1.3374, a ~0.6% miss on min_legs=5 cache method; this
     run recomputes it again, does not assume the prior number still holds).
  5. PAYOFF SHAPE (TAIL_CONVEXITY.md method): monthly top-minus-bottom
     quintile LS on fwd_ret_1M_raw (disc-event guard), skew, hit rate,
     worst-decile-market-month mean, GFC/COVID/2022 episode means.

Cards -> rnd/cards/W5_*.json. Results -> rnd/wave4/W5_RESULTS.md (new file,
this batch only) + rnd/wave4/W5_RESULTS_REMAINING.json (raw).
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
WAVE4_DIR = _THIS.parent
RND_DIR = WAVE4_DIR.parent
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))

import harness  # noqa: E402
import run_long_confirm as LC  # noqa: E402
import builders_w5 as BW  # noqa: E402
import run_w5_convex as R1  # noqa: E402  (reuse the shared W5 harness-wrapper helpers)

CARDS_DIR = RND_DIR / "cards"
REPORTS_DIR = WAVE4_DIR
CANON_PATH = RND_DIR / "panel" / "canonical_7leg_scores.parquet"
LEGS_CACHE = RND_DIR / "panel" / "capstone_legs.parquet"
SEVEN_LEGS = R1.SEVEN_LEGS
OFFICIAL_BASE7_IC_IR = 1.345


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def eval_5y_with_disc_guard(factor, panel, factor_id, family):
    lbl_raw, lbl_resid = "fwd_ret_5Y_raw", "fwd_ret_5Y_resid"
    disc_col = "disc_event_in_window_5Y"
    p2 = panel.copy()
    mask = p2[disc_col].fillna(0) > 0
    p2.loc[mask, [lbl_raw, lbl_resid]] = np.nan
    card = harness.evaluate(
        factor, "5Y", return_basis="resid", factor_id=factor_id,
        panel=p2, panel_source="real_panel_long_capstone",
        family=family, write_card=True, cards_dir=CARDS_DIR,
    )
    return card


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

    log("SANITY CHECK: reconstructing 7-leg base fresh (must reproduce official IC_IR~1.345 before trusting any 8-leg number)...")
    base7_factor = R1.rank_avg_from_cache(legs, SEVEN_LEGS, min_legs=5)
    base7_card = R1.eval_with_disc_guard(base7_factor, panel, "W5REM_BASE7_RECONSTRUCTED_1Y", "W5_INCR")
    base7_summary = R1.summarize(base7_card)
    base7_delta_vs_official = base7_summary["ic_ir"] - OFFICIAL_BASE7_IC_IR
    base7_sanity_ok = abs(base7_delta_vs_official) < 0.05  # within ~4% relative
    log(f"  7-leg reconstructed IC_IR={base7_summary['ic_ir']:.4f} vs official {OFFICIAL_BASE7_IC_IR} "
        f"(delta={base7_delta_vs_official:+.4f}, sanity_ok={base7_sanity_ok}) mono={base7_summary['mono']}")
    if not base7_sanity_ok:
        log("  WARNING: base-7 reconstruction does not tightly reproduce the official IC_IR -- "
            "incremental-IR deltas below are reported RELATIVE TO THIS RUN'S OWN reconstruction, "
            "not the official number, and are flagged as such in every incremental result.")

    log("Building W5-05/06/07/08 candidate factors (annual table build)...")
    t0 = time.time()
    factors = {
        "W5_05_treasury_bloat_base": BW.build_w505_base(panel),
        "W5_06_div_continuity_base": BW.build_w506_base(panel),
        "W5_07_borrowed_div_base": BW.build_w507_base(panel),
        "W5_07_borrowed_div_refine": BW.build_w507_refine(panel),
        "W5_08_moat_1Y": BW.build_w508_base(panel),
    }
    diag = BW._diagnostic_counts_v2()
    log(f"  annual-table diagnostics: {diag}  (build took {time.time()-t0:.1f}s)")
    for k, v in factors.items():
        log(f"  {k}: n_obs={len(v)}")

    family_map = {
        "W5_05_treasury_bloat_base": "W5_05",
        "W5_06_div_continuity_base": "W5_06",
        "W5_07_borrowed_div_base": "W5_07", "W5_07_borrowed_div_refine": "W5_07",
        "W5_08_moat_1Y": "W5_08",
    }
    # incremental-8-leg test -- ONE base trial per family, per trial discipline
    # (mirrors run_w5_convex.py: bases only, not refinements)
    do_incremental = {"W5_05_treasury_bloat_base", "W5_06_div_continuity_base",
                       "W5_07_borrowed_div_base", "W5_08_moat_1Y"}

    rows = []
    for fid, factor in factors.items():
        log(f"Evaluating {fid} ({len(factor)} (date,symbol) obs) at 1Y...")
        card = R1.eval_with_disc_guard(factor, panel, fid, family_map[fid])
        s = R1.summarize(card)
        log(f"  -> IC_IR={s['ic_ir']} lag_delta={s['lag_test_delta']} placebo_ic={s['placebo_ic']} gates_pass={s['gates_pass']}")

        corr_composite, n_corr_dates = R1.avg_spearman(factor, canon.set_index(["date", "symbol"])["composite_rank_avg"])
        corr_vs_legs = {}
        for leg_name in SEVEN_LEGS:
            c, _ = R1.avg_spearman(factor, legs[leg_name])
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
            card8 = R1.eval_with_disc_guard(combo8, panel, f"W5_BASE7_plus_{fid}_1Y", "W5_INCR")
            s8 = R1.summarize(card8)
            delta_ic_ir = (s8["ic_ir"] - base7_summary["ic_ir"]
                           if s8["ic_ir"] is not None and base7_summary["ic_ir"] is not None else float("nan"))
            incr = {"ic_ir_7leg_base_this_run": base7_summary["ic_ir"], "ic_ir_8leg_with_candidate": s8["ic_ir"],
                    "delta_ic_ir": delta_ic_ir, "raises_ir": bool(np.isfinite(delta_ic_ir) and delta_ic_ir > 0),
                    "base7_sanity_ok_vs_official_1.345": base7_sanity_ok,
                    "base7_delta_vs_official": base7_delta_vs_official}
            log(f"  -> 8-leg IC_IR={s8['ic_ir']:.4f} vs 7-leg={base7_summary['ic_ir']:.4f} delta={delta_ic_ir:.4f}")

        rows.append({
            "factor_id": fid, "family": family_map[fid], **s,
            "corr_vs_composite": corr_composite, "n_corr_dates": n_corr_dates,
            "corr_vs_legs": corr_vs_legs, "nearest_leg": nearest_leg,
            "nearest_leg_corr": corr_vs_legs[nearest_leg],
            "incremental_8leg": incr,
        })

    # ---- W5-08 5Y PRIMARY horizon confirmation ----
    log("Evaluating W5_08_moat at 5Y (stated PRIMARY horizon)...")
    card_5y = eval_5y_with_disc_guard(factors["W5_08_moat_1Y"], panel, "W5_08_moat_5Y", "W5_08")
    ic5, dec5 = card_5y.get("ic", {}), card_5y.get("deciles", {})
    s5 = {"factor_id": "W5_08_moat_5Y", "ic_mean": ic5.get("ic_mean"), "ic_ir": ic5.get("ic_ir"),
          "n_ic_dates": ic5.get("n_ic_dates"), "mono": dec5.get("monotonicity"),
          "net_v2_horizon_aware_ann_return": R1.net_v2(card_5y), "dsr": card_5y.get("dsr", {}).get("dsr"),
          "pbo": card_5y.get("pbo", {}).get("pbo"), "n_obs": card_5y.get("n_obs"), **R1.hard_gates(card_5y)}
    log(f"  -> 5Y IC_IR={s5['ic_ir']} n_ic_dates={s5['n_ic_dates']} lag_delta={s5['lag_test_delta']} "
        f"placebo_ic={s5['placebo_ic']} gates_pass={s5['gates_pass']}")

    # ---- payoff shape (1M, all base+refine factors incl. the 5Y-horizon factor series is the same signal) ----
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
        shp = R1.payoff_shape(factor, panel_ret, mkt_fwd, worst_decile_dates, EPISODES)
        shapes[fid] = shp
        shapes[fid]["shape_class"] = R1.classify_shape(shp)
        if "error" not in shp:
            # NaN skew with hit_rate==0 and mean_LS_monthly==0 exactly == a
            # degenerate LS spread (top/bottom quintile ties every month,
            # not a real convex or linear shape) -- relabel honestly rather
            # than let classify_shape's default fall through to "LINEAR/mixed".
            if shp["hit_rate"] == 0.0 and shp["mean_LS_monthly"] == 0.0 and not np.isfinite(shp["skew"]):
                shapes[fid]["shape_class"] = "DEGENERATE/CANNOT ASSESS (thin subset, LS spread ties at 0 every month)"
            log(f"  n={shp['n_dates']} skew={shp['skew']:+.2f} hit={shp['hit_rate']:.2f} "
                f"worst_decile_mean={shp['mean_LS_worst_decile_mkt_months']} class={shapes[fid]['shape_class']}")

    # ---- verdicts ----
    # IMPORTANT: sign discipline first. The repo convention is "higher=better"
    # (factors are ALREADY built/sign-flipped so long-top-decile == the
    # hypothesis's intended long leg). A NEGATIVE signed IC_IR therefore means
    # the thesis, AS REGISTERED, does not hold -- possibly inverted -- and is
    # an automatic KILL regardless of net_v2 (a single linear top-minus-bottom
    # decile spread number can disagree in sign with the full-cross-section
    # rank IC when the relationship is non-monotonic; rank IC + monotonicity
    # are the more reliable read and are checked here). No post-hoc sign
    # flip is applied -- that would be exactly the sign-fishing this firm's
    # protocol forbids; an inverted result is logged as a KILL + finding,
    # not silently re-registered with the opposite sign.
    def verdict_for(row):
        if not row["gates_pass"]:
            return "KILL (hard gate fail)"
        ic_ir = row["ic_ir"]
        sign_ok = ic_ir is not None and np.isfinite(ic_ir) and ic_ir > 0
        corr = row["corr_vs_composite"]
        orth = np.isfinite(corr) and abs(corr) < 0.3
        nearest_corr = row["nearest_leg_corr"]
        orth_leg = np.isfinite(nearest_corr) and abs(nearest_corr) < 0.3
        net = row["net_v2_horizon_aware_ann_return"]
        econ_ok = net is not None and np.isfinite(net) and net > 0
        raises_ir = row["incremental_8leg"]["raises_ir"] if row["incremental_8leg"] else None
        shp = shapes.get(row["factor_id"], {})
        convex_hedge_candidate = shp.get("shape_class") == "CONVEX-leaning"
        if not sign_ok and not convex_hedge_candidate:
            direction = "inverted (material negative IC_IR)" if (ic_ir is not None and np.isfinite(ic_ir) and ic_ir < -0.15) else "weak/noise (sign not confirmed)"
            return f"KILL ({direction} vs hypothesis-as-registered, no post-hoc sign flip)"
        if not orth:
            return "KILL (redundant vs composite, corr>=0.3)"
        if not orth_leg:
            return f"KILL (redundant vs nearest leg {row['nearest_leg']}, corr>=0.3)"
        if convex_hedge_candidate and not econ_ok:
            return "CONVEX-HEDGE-CANDIDATE"
        if sign_ok and econ_ok and (raises_ir is True or raises_ir is None):
            return "IC-ADD-CANDIDATE" if (raises_ir is True) else "IC-ADD-CANDIDATE (weak/no incremental data)"
        if sign_ok and econ_ok and raises_ir is False:
            return "PARK (positive econ, does not raise 8-leg IR)"
        return "KILL (weak linear, not convex)"

    for r in rows:
        r["verdict"] = verdict_for(r)
        r["convex_hedge_candidate"] = shapes.get(r["factor_id"], {}).get("shape_class") == "CONVEX-leaning"

    # ---- write raw JSON ----
    out_json = REPORTS_DIR / "W5_RESULTS_REMAINING.json"
    out_json.write_text(json.dumps({
        "base7_reconstructed_this_run": base7_summary,
        "base7_sanity_check": {"official_ic_ir": OFFICIAL_BASE7_IC_IR, "reconstructed_ic_ir": base7_summary["ic_ir"],
                               "delta": base7_delta_vs_official, "sanity_ok": base7_sanity_ok},
        "candidates": rows,
        "w5_08_5y_primary": s5,
        "payoff_shapes": shapes,
        "diagnostics": diag,
        "worst_decile_cutoff": float(worst_decile_cut),
        "n_worst_decile_months": len(worst_decile_dates),
    }, indent=2, default=str), encoding="utf-8")
    log(f"Wrote {out_json}")

    # ---- write W5_RESULTS.md (new file, this batch) ----
    md_path = WAVE4_DIR / "W5_RESULTS.md"
    lines = []
    if not md_path.exists():
        lines.append("# W5 Forensic/Quality Hypotheses -- Results Log\n\n"
                      "Per rnd/wave4/hypotheses_w5.json. W5-01/02/04 (priority-H) results live in "
                      "rnd/wave4/W5_RESULTS.json + GAPS_BATCH_RESULTS.md (run_w5_convex.py, 2026-07-17). "
                      "This file logs the remaining buildable hypotheses: W5-05/06/07/08.\n")
    lines.append(f"\n\n## {time.strftime('%Y-%m-%d')} -- W5-05/06/07/08 (Sanjay Kulkarni task)\n\n")
    lines.append(f"**Base-7 sanity check** (must precede any 8-leg trust, per task brief): this run's fresh "
                 f"reconstruction (min_legs=5, capstone_legs.parquet cache, identical method to run_w5_convex.py) "
                 f"gives IC_IR={base7_summary['ic_ir']:.4f} vs official 1.345 "
                 f"(delta={base7_delta_vs_official:+.4f}, {'WITHIN tolerance -- incremental deltas below are trustworthy' if base7_sanity_ok else 'OUTSIDE tolerance -- incremental deltas below are RELATIVE TO THIS RECONSTRUCTION ONLY, flagged'}).\n\n")
    lines.append("| Factor | Signed IC_IR (1Y) | Hard gates (lag<=0.25/\\|placebo\\|<=0.02) | Corr vs composite | Nearest leg (corr) | Incr. 8-leg IR delta | Skew (1M LS) | Crash-episode mean (COVID/2022/GFC) | Shape | Verdict |\n")
    lines.append("|---|---|---|---|---|---|---|---|---|---|\n")
    for r in rows:
        incr_str = f"{r['incremental_8leg']['delta_ic_ir']:.4f}" if r["incremental_8leg"] else "n/a (refinement, not tested incremental)"
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
    lines.append(f"\n**W5-08 5Y primary-horizon confirmation**: IC_IR(5Y)={s5['ic_ir']:.4f} "
                 f"(n_ic_dates={s5['n_ic_dates']}), mono={s5['mono']}, gates_pass={s5['gates_pass']} "
                 f"vs 1Y secondary IC_IR={next(r['ic_ir'] for r in rows if r['factor_id']=='W5_08_moat_1Y'):.4f}.\n")
    lines.append(f"\nDiagnostics (W5-05/06/07/08 annual-table coverage): {json.dumps(diag)}\n")
    lines.append(f"Worst-decile market-month cutoff: {worst_decile_cut:.4f} ({len(worst_decile_dates)} months).\n")
    with md_path.open("a", encoding="utf-8") as f:
        f.writelines(lines)
    log(f"Appended/created {md_path}")

    for r in rows:
        card_path = CARDS_DIR / f"{r['factor_id']}_SUMMARY.json"
        card_path.write_text(json.dumps({**r, "payoff_shape": shapes.get(r["factor_id"])}, indent=2, default=str), encoding="utf-8")
    card_path5 = CARDS_DIR / "W5_08_moat_5Y_SUMMARY.json"
    card_path5.write_text(json.dumps(s5, indent=2, default=str), encoding="utf-8")
    log("Wrote per-factor W5_*_SUMMARY.json cards")

    print("\n" + "=" * 110)
    for r in rows:
        print(f"{r['factor_id']:35s} IC_IR={r['ic_ir']:+.4f}  gates_pass={r['gates_pass']!s:5s}  "
              f"corr_composite={r['corr_vs_composite']:+.3f}  nearest={r['nearest_leg']}({r['nearest_leg_corr']:+.3f})  "
              f"shape={shapes.get(r['factor_id'],{}).get('shape_class')}  verdict={r['verdict']}")
    print(f"{'W5_08_moat_5Y (primary)':35s} IC_IR={s5['ic_ir']:+.4f}  gates_pass={s5['gates_pass']!s:5s}")
    print("=" * 110)


if __name__ == "__main__":
    main()
