"""
W4G runner -- coverage-map GAP-UNTESTED cheap-test batch, Aditya Verma (R&D).
2026-07-17. Tests 4 distinct-mechanism candidates from coverage_map.json's
GAP-UNTESTED list, each ONCE (+ at most one pre-registered refinement),
through the shared harness (rnd/lib/harness.py). Frozen model is READ ONLY.

For each candidate:
  1. standalone harness.evaluate() card (signed IC/IC_IR, deciles, lag_test,
     placebo, DSR/PBO -- all from the ONE shared harness, hard gates included)
  2. corr vs canonical_7leg composite score (per-date Spearman, averaged)
  3. corr vs mom_resid_peer leg (per-date Spearman, averaged) -- the
     "or is it just momentum re-labeled" check
  4. incremental 8-leg IR delta: TRUE7 + candidate (min_legs=6-of-8) vs a
     freshly-recomputed TRUE7-only baseline (min_legs=5-of-7), same corporate-
     action-guarded panel, same horizon -- isolates the marginal IC_IR effect
     of adding this ONE candidate leg to the canonical construction.

Horizons: Hurst + TS-abs-momentum tested at 1Y (matches H003/mom_resid_plain's
own primary horizon, the natural comparison point). Reinvestment-runway +
moat tested at 5Y (per task spec: 5Y horizon fundamentals-flavored ideas) --
panel_long.parquet is used throughout (NOT panel.parquet, which is 100% NaN
on fwd_ret_5Y per PANEL_SCHEMA.md).

Outputs: rnd/cards/W4G_*.json (standalone, harness-native) + rnd/cards/W4G_*_full.json
(standalone + corr + incremental, this script's own write) + rnd/wave4/GAPS_BATCH_RESULTS.md
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
RND_DIR = _THIS.parent.parent
ALPHA_DIR = RND_DIR.parent
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))

import harness  # noqa: E402
import builders_w4g_gaps as W4G  # noqa: E402

PANEL_LONG_PATH = RND_DIR / "panel" / "panel_long.parquet"
CUBE_CLOSE_LONG = RND_DIR / "panel" / "cube_close_long.parquet"
CUBE_BENCH_LONG = RND_DIR / "panel" / "cube_bench_long.parquet"
LEGS_CACHE = RND_DIR / "panel" / "capstone_legs.parquet"
CANON_SCORES = RND_DIR / "panel" / "canonical_7leg_scores.parquet"
CARDS_DIR = RND_DIR / "cards"
OUT_MD = RND_DIR / "wave4" / "GAPS_BATCH_RESULTS.md"

TRUE7 = ["value_EY", "mom_resid_plain", "trend_ma65_slope", "quality_QMJ",
         "bs_issuance", "bs_asset_growth", "quality_cfo_pat"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_all():
    panel = pd.read_parquet(PANEL_LONG_PATH)
    panel["date"] = pd.to_datetime(panel["date"])
    close = pd.read_parquet(CUBE_CLOSE_LONG)
    close.index = pd.to_datetime(close.index)
    canon = pd.read_parquet(CANON_SCORES)
    canon["date"] = pd.to_datetime(canon["date"])
    legs = pd.read_parquet(LEGS_CACHE)
    legs["date"] = pd.to_datetime(legs["date"])
    mom_peer = None
    if "mom_resid_peer" in legs["leg"].unique():
        mom_peer = legs.loc[legs["leg"] == "mom_resid_peer"].set_index(["date", "symbol"])["value"].rename("factor")
    return panel, close, canon, legs, mom_peer


def guard_disc_events(panel: pd.DataFrame, horizon: str) -> pd.DataFrame:
    """Same corporate-action guard convention as composite_final.py: NaN the
    forward-return TARGET (not the factor) where a >40% flagged discontinuity
    falls inside that row's forward window."""
    col = f"disc_event_in_window_{horizon}"
    p = panel.copy()
    mask = p[col].fillna(0) > 0
    for suffix in ("raw", "excess", "resid"):
        tcol = f"fwd_ret_{horizon}_{suffix}"
        if tcol in p.columns:
            p.loc[mask, tcol] = np.nan
    return p, int(mask.sum())


def rank_avg(legs_dict: dict, names: list, min_legs: int) -> pd.Series:
    """Identical convention to composite_final.rank_avg: equal-weight rank
    average, emits a value only where >= min_legs of `names` are present."""
    frames = []
    for n in names:
        r = legs_dict[n].rename("factor").reset_index()
        r.columns = ["date", "symbol", n]
        r[n] = r.groupby("date")[n].rank(pct=True)
        frames.append(r.set_index(["date", "symbol"])[n])
    wide = pd.concat(frames, axis=1)
    combo = wide.mean(axis=1, skipna=True)
    n_present = wide.notna().sum(axis=1)
    combo = combo.where(n_present >= min_legs)
    return combo.dropna().rename("factor")


def per_date_spearman(factor_a: pd.Series, factor_b: pd.Series, min_names: int = 20) -> dict:
    """Per-date cross-sectional Spearman corr between two (date,symbol)-
    indexed series, averaged across dates. Same min-names-per-date convention
    as the harness's own IC calculation."""
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


def load_capstone_legs_dict(legs_df: pd.DataFrame) -> dict:
    out = {}
    for leg, g in legs_df.groupby("leg"):
        out[leg] = g.set_index(["date", "symbol"])["value"].rename("factor")
    return out


def build_and_add_mom_plain(legs_dict: dict, close: pd.DataFrame, bench: pd.Series, dates) -> dict:
    """TRUE7 needs mom_resid_plain fresh (composite_final.py builds it fresh
    too, not from the legs cache) -- reuse the exact same construction."""
    if "mom_resid_plain" in legs_dict:
        return legs_dict
    daily_ret = close.pct_change()
    bench_ret = bench.pct_change()
    cov = daily_ret.rolling(252, min_periods=126).cov(bench_ret)
    var = bench_ret.rolling(252, min_periods=126).var()
    beta = cov.div(var, axis=0)
    resid = daily_ret.sub(beta.mul(bench_ret, axis=0))
    idx = resid.index
    rows = []
    for d in dates:
        if d not in idx:
            continue
        loc = idx.get_loc(d)
        if loc < 273:
            continue
        window = resid.iloc[loc - 251: loc - 20]
        cov_ok = window.notna().mean() >= 0.80
        cum = (1.0 + window.fillna(0.0)).prod() - 1.0
        cum = cum.where(cov_ok)
        for sym, val in cum.dropna().items():
            rows.append((d, sym, val))
    out = pd.DataFrame(rows, columns=["date", "symbol", "factor"])
    legs_dict["mom_resid_plain"] = out.set_index(["date", "symbol"])["factor"]
    return legs_dict


def composite_ic_ir(legs_dict: dict, names: list, min_legs: int, panel_guarded: pd.DataFrame,
                     panel_source: str, horizon: str, family: str, factor_id: str) -> dict:
    factor = rank_avg(legs_dict, names, min_legs=min_legs)
    card = harness.evaluate(factor, horizon, return_basis="resid", factor_id=factor_id,
                            panel=panel_guarded, panel_source=panel_source, family=family,
                            write_card=True, cards_dir=CARDS_DIR)
    return card


def run_candidate(name: str, factor: pd.Series, horizon: str, basis: str, family: str,
                   panel_guarded: pd.DataFrame, panel_source: str, canon: pd.DataFrame,
                   mom_peer: pd.Series, legs_dict: dict, baseline_card: dict, n_excluded: int) -> dict:
    log(f"=== {name}: standalone evaluate() at {horizon}/{basis} ===")
    standalone = harness.evaluate(factor, horizon, return_basis=basis, factor_id=f"W4G_{name}",
                                   panel=panel_guarded, panel_source=panel_source, family=f"W4G_{name}",
                                   write_card=True, cards_dir=CARDS_DIR)
    log(f"    verdict={standalone['verdict']}  ic_ir={standalone['ic']['ic_ir']}")

    canon_f = canon.set_index(["date", "symbol"])["score"].rename("factor")
    corr_composite = per_date_spearman(factor, canon_f)
    log(f"    corr vs canonical_7leg score: {corr_composite}")

    corr_momentum = {"mean_corr": float("nan"), "n_dates": 0}
    if mom_peer is not None:
        corr_momentum = per_date_spearman(factor, mom_peer)
        log(f"    corr vs mom_resid_peer leg: {corr_momentum}")

    log(f"    building 8-leg composite (TRUE7 + {name}, min_legs=6-of-8) at {horizon}...")
    legs8 = dict(legs_dict)
    legs8[name] = factor
    card8 = composite_ic_ir(legs8, TRUE7 + [name], min_legs=6, panel_guarded=panel_guarded,
                             panel_source=panel_source, horizon=horizon, family=f"W4G_8leg_{name}",
                             factor_id=f"W4G_8leg_{name}_{horizon}")
    base_ir = baseline_card["ic"]["ic_ir"]
    new_ir = card8["ic"]["ic_ir"]
    delta = (new_ir - base_ir) if (np.isfinite(base_ir) and np.isfinite(new_ir)) else float("nan")
    log(f"    baseline_7leg_ic_ir={base_ir:.4f}  8leg_ic_ir={new_ir:.4f}  delta={delta:.4f}")

    if np.isnan(delta):
        incr_verdict = "inconclusive (NaN IC_IR)"
    elif delta > 0.10:
        incr_verdict = "adds"
    elif delta < -0.05:
        incr_verdict = "hurts (dilutive)"
    else:
        incr_verdict = "redundant (no material delta)"

    full_card = {
        "factor_id": f"W4G_{name}", "horizon": horizon, "return_basis": basis,
        "family": f"W4G_{name}", "standalone": standalone,
        "corr_vs_canonical_7leg_composite": corr_composite,
        "corr_vs_mom_resid_peer": corr_momentum,
        "incremental_8leg": {"baseline_7leg_ic_ir": base_ir, "8leg_ic_ir": new_ir,
                              "delta_ic_ir": delta, "verdict": incr_verdict,
                              "min_legs_baseline": "5-of-7", "min_legs_8leg": "6-of-8"},
        "n_disc_events_excluded": n_excluded,
        "panel_source": panel_source,
    }
    (CARDS_DIR / f"W4G_{name}_full.json").write_text(
        json.dumps(full_card, indent=2, default=str), encoding="utf-8")
    return full_card


def main():
    log("Loading panel_long, cube_close_long, cube_bench_long, capstone legs, canonical scores...")
    panel = pd.read_parquet(PANEL_LONG_PATH)
    panel["date"] = pd.to_datetime(panel["date"])
    close = pd.read_parquet(CUBE_CLOSE_LONG)
    close.index = pd.to_datetime(close.index)
    bench = pd.read_parquet(CUBE_BENCH_LONG)["NIFTY500"]
    bench.index = pd.to_datetime(bench.index)
    canon = pd.read_parquet(CANON_SCORES)
    canon["date"] = pd.to_datetime(canon["date"])
    legs_raw = pd.read_parquet(LEGS_CACHE)
    legs_raw["date"] = pd.to_datetime(legs_raw["date"])
    legs_dict = load_capstone_legs_dict(legs_raw)
    mom_peer = legs_dict.get("mom_resid_peer")

    dates = pd.DatetimeIndex(sorted(panel["date"].unique()))
    legs_dict = build_and_add_mom_plain(legs_dict, close, bench, dates)

    panel_1y, n_excl_1y = guard_disc_events(panel, "1Y")
    panel_5y, n_excl_5y = guard_disc_events(panel, "5Y")
    panel_source = "real_panel_long"

    log("Recomputing fresh 7-leg baseline at 1Y (min_legs=5-of-7)...")
    base7_1y = composite_ic_ir(legs_dict, TRUE7, min_legs=5, panel_guarded=panel_1y,
                                panel_source=panel_source, horizon="1Y", family="W4G_baseline7",
                                factor_id="W4G_baseline7_1Y")
    log(f"    baseline 7-leg 1Y ic_ir={base7_1y['ic']['ic_ir']}")

    log("Recomputing fresh 7-leg baseline at 5Y (min_legs=5-of-7)...")
    base7_5y = composite_ic_ir(legs_dict, TRUE7, min_legs=5, panel_guarded=panel_5y,
                                panel_source=panel_source, horizon="5Y", family="W4G_baseline7",
                                factor_id="W4G_baseline7_5Y")
    log(f"    baseline 7-leg 5Y ic_ir={base7_5y['ic']['ic_ir']}")

    results = {}

    # ---- 1. Hurst ----
    log("Building Hurst / GHE trend-persistence factor...")
    hurst = W4G.build_hurst_factor(close, dates)
    log(f"    hurst obs: {len(hurst)}")
    results["hurst"] = run_candidate("hurst", hurst, "1Y", "resid", "W4G_hurst",
                                      panel_1y, panel_source, canon, mom_peer, legs_dict,
                                      base7_1y, n_excl_1y)

    # ---- 2. TS absolute momentum ----
    log("Building time-series (absolute) momentum factor (RAW basis)...")
    ts_mom = W4G.build_ts_abs_mom_factor(close, dates)
    log(f"    ts_mom obs: {len(ts_mom)}")
    results["ts_abs_mom"] = run_candidate("ts_abs_mom", ts_mom, "1Y", "raw", "W4G_ts_abs_mom",
                                           panel_1y, panel_source, canon, mom_peer, legs_dict,
                                           base7_1y, n_excl_1y)

    # ---- 3. Reinvestment runway (H038) ----
    log("Building reinvestment-runway (H038) factor...")
    reinv = W4G.build_reinvestment_runway_factor(panel[["date", "symbol"]])
    log(f"    reinvestment_runway obs: {len(reinv)}")
    results["reinvestment_runway"] = run_candidate("reinvestment_runway", reinv, "5Y", "resid",
                                                    "W4G_reinvestment_runway", panel_5y, panel_source,
                                                    canon, mom_peer, legs_dict, base7_5y, n_excl_5y)

    # ---- 4. Moat / margin-stability ----
    log("Building moat proxy (5yr operating-margin level x stability) factor...")
    moat = W4G.build_moat_margin_stability_factor(panel[["date", "symbol"]])
    log(f"    moat obs: {len(moat)}")
    results["moat_margin_stability"] = run_candidate("moat_margin_stability", moat, "5Y", "resid",
                                                      "W4G_moat", panel_5y, panel_source,
                                                      canon, mom_peer, legs_dict, base7_5y, n_excl_5y)

    log("Writing GAPS_BATCH_RESULTS.md...")
    write_md(results, base7_1y, base7_5y)
    log("DONE.")


def write_md(results: dict, base7_1y: dict, base7_5y: dict):
    lines = []
    lines.append("# W4G -- coverage-map GAP-UNTESTED cheap-test batch results")
    lines.append("")
    lines.append("Aditya Verma (R&D), 2026-07-17. Four distinct-mechanism candidates from "
                 "`coverage_map.json`'s GAP-UNTESTED list, each tested ONCE through the shared "
                 "harness (`rnd/lib/harness.py`). Frozen 7-leg model read-only, never edited.")
    lines.append("")
    lines.append(f"Fresh 7-leg baseline (recomputed this run, min_legs=5-of-7, corp-action-guarded): "
                 f"1Y IC_IR={base7_1y['ic']['ic_ir']:.4f} (n_dates={base7_1y['ic']['n_ic_dates']}); "
                 f"5Y IC_IR={base7_5y['ic']['ic_ir']:.4f} (n_dates={base7_5y['ic']['n_ic_dates']}).")
    lines.append("")
    for name, r in results.items():
        s = r["standalone"]
        lines.append(f"## {name}")
        lines.append("")
        lines.append(f"- horizon/basis: {r['horizon']}/{r['return_basis']}")
        lines.append(f"- n_obs={s.get('n_obs')}, n_dates={s.get('n_dates')}, panel_source={s.get('panel_source')}")
        ic = s.get("ic", {})
        lines.append(f"- IC_mean={ic.get('ic_mean')}, IC_IR={ic.get('ic_ir')}, NW_t={ic.get('newey_west_t')}")
        lines.append(f"- decile monotonicity={s.get('deciles', {}).get('monotonicity')}")
        lt = s.get("lag_test", {})
        pb = s.get("placebo", {})
        lines.append(f"- lag_test_delta={lt.get('lag_test_delta')} (gate <=0.25); "
                     f"placebo_IC={pb.get('placebo_ic')} (gate <=0.02 abs)")
        lines.append(f"- DSR={s.get('dsr', {}).get('dsr')}, PBO={s.get('pbo', {}).get('pbo')} (advisory only, low-t rule)")
        lines.append(f"- harness verdict: **{s.get('verdict')}**")
        lines.append(f"- corr vs canonical_7leg composite score: {r['corr_vs_canonical_7leg_composite']}")
        lines.append(f"- corr vs mom_resid_peer leg: {r['corr_vs_mom_resid_peer']}")
        inc = r["incremental_8leg"]
        lines.append(f"- incremental 8-leg: baseline_ic_ir={inc['baseline_7leg_ic_ir']}, "
                     f"8leg_ic_ir={inc['8leg_ic_ir']}, delta={inc['delta_ic_ir']} -> **{inc['verdict']}**")
        lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
