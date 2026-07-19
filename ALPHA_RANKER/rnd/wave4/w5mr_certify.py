"""
W5MR CERTIFY -- full certification pass on the "selective oversold mean-reversion"
regime-gold find (rev5d / rsi2_factor IC lift 2-3x when breadth <=20th expanding
percentile). Owner: Arjun Rao (Quant Head), 2026-07-17. ALPHA_RANKER.

Runs the 5 checks the task specified, on top of the existing research pass
(rnd/wave4/w5_regime_momentum_horizon.py / REGIME_MOMENTUM_HORIZON.md /
rnd/cards/W5RG_selective_mr.json):

  1. Full per-episode drop-one (does the >2x IC lift hold dropping ANY single
     oversold episode, not just an aggregate range)?
  2. Era-split (pre-/post- a fixed calendar cut, and thirds).
  3. DSR/PBO for the record (ADVISORY ONLY per RESEARCH_QUEUE's low-t rule --
     the hard gates that matter here are placebo+lag, already clean).
  4. Sensitivity to the breadth threshold (10th/20th/30th expanding pctile) --
     plateau or knife-edge?
  5. Net-of-cost, using ONLY the APPROVED COST_STANDARDS.md numbers (D-021),
     with the mandatory 2x stress (Promotion Rule).

Data lineage (verified row counts, same as REGIME_MOMENTUM_HORIZON.md):
  rnd/panel/panel_long.parquet      148297 rows, 31 cols -- date list only
  rnd/panel/cube_close_long.parquet   5131 x 976         -- momentum/reversal, built fresh
  rnd/panel/cube_bench_long.parquet   5131 x 1           -- NIFTY500 index, trend input
  rnd/panel/market_state.parquet       249 x 27          -- breadth_pct_above_200dma (reused, not recomputed)

No new PIT/lookahead surface: reuses the exact regime-classification and
factor-construction functions from w5_regime_momentum_horizon.py verbatim
(imported, not re-implemented) so causality guarantees carry over unchanged.
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

RND = Path(__file__).resolve().parents[1]        # ALPHA_RANKER/rnd
sys.path.insert(0, str(RND / "lib"))
sys.path.insert(0, str(RND / "wave4"))

import harness  # noqa: E402  -- for compute_dsr / compute_pbo_cscv (advisory)

# import the base research script as a module WITHOUT running its __main__
_spec = importlib.util.spec_from_file_location("w5rg_base", RND / "wave4" / "w5_regime_momentum_horizon.py")
w5rg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(w5rg)

CARDS_DIR = RND / "cards"
OUT_DIR = RND / "wave4"

FACTORS = ["rev5d", "rsi2_factor"]


def _native(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o.date())
    raise TypeError(str(type(o)))


def write_json(obj: dict, path: Path):
    path.write_text(json.dumps(obj, indent=2, default=_native), encoding="utf-8")


def log(msg):
    print(msg, flush=True)


def main():
    panel_long = pd.read_parquet(w5rg.PANEL_LONG_PATH, columns=["date"])
    dates = sorted(pd.to_datetime(panel_long["date"].unique()))
    log(f"[data] panel_long.parquet rows={len(panel_long)} (date-list only); "
        f"{len(dates)} monthly dates {dates[0].date()}->{dates[-1].date()}")

    regime_panel = w5rg.build_regime_panel(dates)
    log(f"[data] market_state.parquet rows={pd.read_parquet(w5rg.MARKET_STATE_PATH).shape}")

    cube = w5rg.load_cube()
    log(f"[data] cube_close_long.parquet shape={cube.shape}")
    factors = w5rg.build_monthly_factors(cube, dates)
    rsi2 = w5rg.build_rsi2(cube, dates)
    factors = factors.merge(rsi2, on=["date", "symbol"], how="left")
    log(f"[data] factors panel shape={factors.shape}")

    merged = factors.merge(
        regime_panel.reset_index().rename(columns={"index": "date"})[
            ["date", "regime", "oversold_extreme", "breadth_pctrank_exp"]],
        on="date", how="left")
    dates_sorted = sorted(merged["date"].unique())

    uncond = {}
    for fc in FACTORS:
        ic = w5rg.cross_sectional_ic(merged, fc, "fwd_ret_1m")
        uncond[fc] = float(ic.mean())
    log(f"[baseline] unconditional IC: {uncond}")

    results = {"data_lineage": {
        "panel_long_rows": int(len(panel_long)),
        "market_state_rows": int(pd.read_parquet(w5rg.MARKET_STATE_PATH).shape[0]),
        "cube_close_long_shape": list(cube.shape),
        "n_monthly_dates": len(dates),
        "date_range": [str(dates[0].date()), str(dates[-1].date())],
    }, "unconditional_ic": uncond}

    # =======================================================================
    # CHECK 1 -- full per-episode drop-one, explicit lift multiple
    # =======================================================================
    log("\n=== CHECK 1: per-episode drop-one, lift multiple ===")
    check1 = {}
    for fc in FACTORS:
        oversold = merged[merged["oversold_extreme"] == True]
        os_ic = w5rg.cross_sectional_ic(oversold, fc, "fwd_ret_1m")
        os_ic_mean = float(os_ic.mean())
        os_dates = pd.DatetimeIndex(oversold["date"].unique())
        dropone = w5rg.drop_one_by_episode(oversold, fc, "fwd_ret_1m", os_dates)
        episodes = {k: v for k, v in dropone.items() if k != "_episodes_found"}
        lift_table = {}
        min_lift, max_lift = np.inf, -np.inf
        n_below_2x = 0
        for k, v in episodes.items():
            ic_excl = v["ic_mean_excl"]
            lift = ic_excl / uncond[fc] if uncond[fc] else np.nan
            lift_table[k] = {"ic_mean_excl": ic_excl, "n_months_remaining": v["n_months_remaining"],
                              "lift_vs_unconditional": lift}
            min_lift, max_lift = min(min_lift, lift), max(max_lift, lift)
            if lift < 2.0:
                n_below_2x += 1
        check1[fc] = {
            "oversold_full_ic": os_ic_mean,
            "oversold_full_lift": os_ic_mean / uncond[fc],
            "n_episodes": len(episodes),
            "episodes": lift_table,
            "episodes_found": dropone["_episodes_found"],
            "min_lift_across_all_drop_one": float(min_lift),
            "max_lift_across_all_drop_one": float(max_lift),
            "n_episodes_where_lift_falls_below_2x": n_below_2x,
            "holds_for_every_single_episode_drop": bool(n_below_2x == 0),
        }
        log(f"  {fc}: full-lift={check1[fc]['oversold_full_lift']:.2f}x  "
            f"drop-one lift range=[{min_lift:.2f}x, {max_lift:.2f}x]  "
            f"episodes below 2x when dropped: {n_below_2x}/{len(episodes)}")

    # =======================================================================
    # CHECK 2 -- era split (fixed cut + thirds)
    # =======================================================================
    log("\n=== CHECK 2: era split ===")
    check2 = {}
    CUT = pd.Timestamp("2015-01-01")
    for fc in FACTORS:
        oversold = merged[merged["oversold_extreme"] == True]
        era_a = oversold[oversold["date"] < CUT]
        era_b = oversold[oversold["date"] >= CUT]
        ic_a = w5rg.cross_sectional_ic(era_a, fc, "fwd_ret_1m")
        ic_b = w5rg.cross_sectional_ic(era_b, fc, "fwd_ret_1m")
        # thirds, by distinct oversold dates
        os_dates_sorted = sorted(oversold["date"].unique())
        n = len(os_dates_sorted)
        thirds_edges = [os_dates_sorted[: n // 3], os_dates_sorted[n // 3: 2 * n // 3], os_dates_sorted[2 * n // 3:]]
        thirds = {}
        for i, edge in enumerate(thirds_edges):
            sub = oversold[oversold["date"].isin(edge)]
            ic_t = w5rg.cross_sectional_ic(sub, fc, "fwd_ret_1m")
            thirds[f"third_{i+1}"] = {
                "n_months": int(pd.Series(edge).nunique()),
                "date_range": [str(min(edge).date()), str(max(edge).date())] if edge else None,
                "ic_mean": float(ic_t.mean()) if len(ic_t.dropna()) else float("nan"),
            }
        check2[fc] = {
            "split_2015_01_01": {
                "era_pre_2015": {"n_months": int(era_a["date"].nunique()), "ic_mean": float(ic_a.mean())},
                "era_post_2015": {"n_months": int(era_b["date"].nunique()), "ic_mean": float(ic_b.mean())},
            },
            "thirds": thirds,
            "unconditional_ic_ref": uncond[fc],
        }
        log(f"  {fc}: pre-2015 IC={ic_a.mean():.4f} (n={era_a['date'].nunique()})  "
            f"post-2015 IC={ic_b.mean():.4f} (n={era_b['date'].nunique()})")
        for k, v in thirds.items():
            log(f"    {k}: IC={v['ic_mean']:.4f} n={v['n_months']} {v['date_range']}")

    # =======================================================================
    # CHECK 3 -- DSR / PBO, advisory only (harness.compute_dsr / compute_pbo_cscv)
    # =======================================================================
    log("\n=== CHECK 3: DSR/PBO (ADVISORY -- hard gates are placebo+lag, already clean) ===")
    check3 = {}
    trials = json.loads((RND / "trials_counter.json").read_text(encoding="utf-8"))
    fam = trials.get("by_family", {})
    n_trials_grid = {
        "N=1 (this exact test, no correction)": 1,
        "N=1_family_W5RG (own ledger, if logged)": max(1, fam.get("W5RG", fam.get("H034", 1))),
        f"N={len(fam)} (n distinct research families in program)": len(fam),
        f"N={trials.get('total_trials', 0)} (global program trial count)": trials.get("total_trials", 0),
    }
    for fc in FACTORS:
        oversold = merged[merged["oversold_extreme"] == True]
        os_ls = w5rg.decile_ls(oversold, fc, "fwd_ret_1m")  # monthly LS return series, n~42
        n_obs = int(os_ls.dropna().shape[0])
        dsr_rows = {}
        for label, nt in n_trials_grid.items():
            d = harness.compute_dsr(os_ls, n_trials=int(nt))
            dsr_rows[label] = d
        n_blocks = 6 if n_obs >= 12 else 4
        pbo = harness.compute_pbo_cscv(os_ls, n_blocks=n_blocks)
        check3[fc] = {"n_obs_ls_series": n_obs, "dsr_by_n_trials": dsr_rows, "pbo_cscv": pbo}
        log(f"  {fc}: n_obs={n_obs}  PBO(n_blocks={n_blocks})={pbo.get('pbo')}  "
            f"DSR@N=1={dsr_rows['N=1 (this exact test, no correction)']['dsr']:.4f}  "
            f"DSR@global={dsr_rows[list(n_trials_grid)[-1]]['dsr']:.4f}")

    # =======================================================================
    # CHECK 4 -- breadth threshold sensitivity (10/20/30 pct): plateau or knife-edge?
    # =======================================================================
    log("\n=== CHECK 4: breadth threshold sensitivity ===")
    check4 = {}
    for fc in FACTORS:
        cell = {}
        for pct in [0.10, 0.20, 0.30]:
            sub_flag = regime_panel["breadth_pctrank_exp"] <= pct
            sub_dates = regime_panel.index[sub_flag.fillna(False)]
            sub = merged[merged["date"].isin(sub_dates)]
            ic = w5rg.cross_sectional_ic(sub, fc, "fwd_ret_1m")
            ls = w5rg.decile_ls(sub, fc, "fwd_ret_1m")
            summ = w5rg.summarize(ic, ls)
            cell[f"pct_{int(pct*100)}"] = summ
            log(f"  {fc} @ {int(pct*100)}th pctile: n={summ['n_months']} IC={summ['ic_mean']:.4f} "
                f"LS_ann={summ['ls_ann_approx']:.4f}")
        ics = [cell[f"pct_{p}"]["ic_mean"] for p in (10, 20, 30)]
        # knife-edge if 10th differs from 20th/30th by >50% relative, or non-monotonic with a cliff
        rel_spread = (max(ics) - min(ics)) / abs(uncond[fc]) if uncond[fc] else np.nan
        cell["shape_verdict"] = (
            "PLATEAU (10/20/30th pctile IC broadly similar, all clearly > unconditional)"
            if (min(ics) > 1.5 * uncond[fc] and (max(ics) - min(ics)) < 0.5 * min(ics))
            else "KNIFE-EDGE-ish (material change across thresholds) -- see numbers"
        )
        check4[fc] = cell
        log(f"  {fc}: shape={cell['shape_verdict']}")

    # =======================================================================
    # CHECK 5 -- net-of-cost, APPROVED COST_STANDARDS.md only, 2x stress mandatory
    # =======================================================================
    log("\n=== CHECK 5: net-of-cost (approved COST_STANDARDS.md, D-021) ===")
    # Approved, APPROVED-status numbers only (06_TRADING_DESK/COST_STANDARDS.md):
    #   STT equity delivery: 0.1% BOTH sides (buy+sell) -> 0.20% round trip
    #   Slippage floor, mid-cap tier (conservative single tier for a cross-sectional
    #   NIFTY500 decile book -- most F&O/liquid names are large/mid, some small-cap
    #   tail): 20bps ONE-WAY -> 40bps round trip
    #   Brokerage Rs20/order + exchange txn ~0.003% + SEBI Rs10/crore + GST 18% on
    #   (brokerage+exch+SEBI): all negligible in bps terms on any real notional,
    #   included as a small fixed add-on, not modeled per-name (immaterial).
    STT_ROUNDTRIP = 0.0020          # 0.1% x2 sides
    SLIPPAGE_ONEWAY_MIDCAP = 0.0020  # 20bps
    SLIPPAGE_ROUNDTRIP = SLIPPAGE_ONEWAY_MIDCAP * 2
    MISC_ROUNDTRIP = 0.0003         # brokerage+exch+SEBI+GST, small notional-independent floor, bps-approx
    cost_per_leg_roundtrip_1x = STT_ROUNDTRIP + SLIPPAGE_ROUNDTRIP + MISC_ROUNDTRIP
    # A decile L-S position trades BOTH legs (long top decile, short bottom decile)
    # every active month -- each leg incurs its own full round-trip cost.
    cost_ls_1x = 2 * cost_per_leg_roundtrip_1x
    cost_ls_2x_stress = 2 * cost_ls_1x  # mandatory 2x stress, Promotion Rule

    check5 = {
        "cost_assumptions": {
            "source": "Shreyas_Ionic_AMC/06_TRADING_DESK/COST_STANDARDS.md (APPROVED, D-021)",
            "stt_equity_delivery_roundtrip": STT_ROUNDTRIP,
            "slippage_oneway_midcap_tier": SLIPPAGE_ONEWAY_MIDCAP,
            "slippage_roundtrip": SLIPPAGE_ROUNDTRIP,
            "misc_brokerage_exch_sebi_gst_roundtrip_approx": MISC_ROUNDTRIP,
            "cost_per_leg_roundtrip_1x": cost_per_leg_roundtrip_1x,
            "cost_LS_both_legs_1x": cost_ls_1x,
            "cost_LS_both_legs_2x_stress": cost_ls_2x_stress,
            "note": "MR fires ONLY in oversold-extreme months (rare, ~42/249=17% of history) -- "
                    "turnover is bounded to those active months, not a permanent monthly book. "
                    "Full decile re-rank assumed each active month (conservative: 100% turnover "
                    "per leg per active month, no partial-overlap credit).",
        },
    }
    for fc in FACTORS:
        oversold = merged[merged["oversold_extreme"] == True]
        os_ls = w5rg.decile_ls(oversold, fc, "fwd_ret_1m").dropna()
        gross_mean = float(os_ls.mean())
        gross_ann = float((1 + gross_mean) ** 12 - 1) if gross_mean > -1 else float("nan")
        net_1x_mean = gross_mean - cost_ls_1x
        net_2x_mean = gross_mean - cost_ls_2x_stress
        net_1x_ann = float((1 + net_1x_mean) ** 12 - 1) if net_1x_mean > -1 else float("nan")
        net_2x_ann = float((1 + net_2x_mean) ** 12 - 1) if net_2x_mean > -1 else float("nan")
        # active-months-only Sharpe-style IR (mean/std of the active-month series), not full-period
        ls_std = float(os_ls.std())
        ir_gross = gross_mean / ls_std if ls_std else float("nan")
        ir_net_2x = net_2x_mean / ls_std if ls_std else float("nan")
        check5[fc] = {
            "n_active_months": int(len(os_ls)),
            "gross_ls_mean_monthly": gross_mean,
            "gross_ls_ann_approx": gross_ann,
            "net_ls_mean_monthly_1x_cost": net_1x_mean,
            "net_ls_ann_approx_1x_cost": net_1x_ann,
            "net_ls_mean_monthly_2x_stress": net_2x_mean,
            "net_ls_ann_approx_2x_stress": net_2x_ann,
            "ir_active_months_gross": ir_gross,
            "ir_active_months_net_2x_stress": ir_net_2x,
            "survives_1x_cost": bool(net_1x_mean > 0),
            "survives_2x_stress": bool(net_2x_mean > 0),
        }
        log(f"  {fc}: gross monthly={gross_mean:.4%}  net@1x={net_1x_mean:.4%}  "
            f"net@2x_stress={net_2x_mean:.4%}  survives_2x={net_2x_mean > 0}")

    results["check1_dropone_lift"] = check1
    results["check2_era_split"] = check2
    results["check3_dsr_pbo_advisory"] = check3
    results["check4_threshold_sensitivity"] = check4
    results["check5_net_of_cost"] = check5

    write_json(results, OUT_DIR / "W5MR_CERT_results.json")
    write_json(check1, CARDS_DIR / "W5MR_cert_dropone.json")
    write_json(check2, CARDS_DIR / "W5MR_cert_era.json")
    write_json(check3, CARDS_DIR / "W5MR_cert_dsr_pbo.json")
    write_json(check4, CARDS_DIR / "W5MR_cert_threshold.json")
    write_json(check5, CARDS_DIR / "W5MR_cert_netcost.json")
    log("\n[done] wrote W5MR_CERT_results.json + 5 cards to rnd/cards/")


if __name__ == "__main__":
    main()
