"""
PRE-IC ADVERSARIAL BATTERY -- Dr. Sameer Bhat (Overfit & Sensitivity Analyst).
Audits the ALPHA_RANKER composite described in rnd/FINAL_MODEL.md before IC memo.

Does THREE things:
1. Builds the TRUE 7-leg composite as FINAL_MODEL.md actually describes it
   (EY + PLAIN residual momentum + MA65 + QMJ + net-issuance(-) + asset-growth(-) + CFO/PAT),
   which has NEVER been evaluated as a single card (run_capstone.py's "COMPO_1Y_final" uses
   only 4 legs incl. mom_resid_peer + value_smallcap_M2, NOT this 7-leg stack; run_incremental_
   value.py's BASE4 also uses mom_resid_peer, not PLAIN). One fresh honest harness.evaluate()
   call -- genuinely new hypothesis, disclosed as +1 trial.
2. Runs a lightweight (non-trial-incrementing) perturbation battery around that TRUE 7-leg
   composite: leg-weight tilts, decile vs quintile spread, rebalance-offset shift, universe
   subsample (random-20%-drop x5 seeds, drop-each-sector-once).
3. Era-split IC (2005-10 / 10-15 / 15-20 / 20-25) for the TRUE 7-leg composite.

Perturbation/era checks reuse harness internals (_normalize_factor, _cross_sectional_ic,
_decile_stats) directly -- NOT harness.evaluate() -- so they do not inflate the honest-trials
ledger; these are robustness re-checks of one already-counted hypothesis, not new trials.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))

import harness  # noqa: E402
import run_long_confirm as LC  # noqa: E402
import sector_analytics as SA  # noqa: E402
import builders_w2_profq as bprofq  # noqa: E402
import builders_w2_indiaqv as bindiaqv  # noqa: E402
import builders_w2_issuance as bissu  # noqa: E402

REPORTS_DIR = RND_DIR / "reports"
LEGS_CACHE = RND_DIR / "panel" / "capstone_legs.parquet"
UNIVERSE_PATH = RND_DIR.parent / "data" / "universe" / "nifty_total_market_750.csv"

OUT = {}


def log(msg):
    print(f"[audit] {msg}", flush=True)


def load_cached_legs():
    d = pd.read_parquet(LEGS_CACHE)
    d["date"] = pd.to_datetime(d["date"])
    out = {}
    for leg, g in d.groupby("leg"):
        out[leg] = g.set_index(["date", "symbol"])["value"].rename("factor")
    return out


def rank_avg(legs_dict, names, weights=None, min_legs=None):
    frames = []
    for n in names:
        r = legs_dict[n].rename("factor").reset_index()
        r.columns = ["date", "symbol", n]
        r[n] = r.groupby("date")[n].rank(pct=True)
        frames.append(r.set_index(["date", "symbol"])[n])
    wide = pd.concat(frames, axis=1)
    if weights is None:
        combo = wide.mean(axis=1, skipna=True)
    else:
        w = pd.Series({n: weights.get(n, 1.0) for n in names})
        combo = (wide * w).sum(axis=1, skipna=True) / wide.notna().mul(w, axis=1).sum(axis=1)
    n_present = wide.notna().sum(axis=1)
    thr = min_legs if min_legs is not None else min(2, len(names))
    combo = combo.where(n_present >= thr)
    return combo.dropna().rename("factor")


def quick_ic(factor, panel, horizon="1Y", min_names=20, drop_symbols=None, drop_dates_shift=0,
             quintile=False):
    """Lightweight IC/decile-spread computer, bypassing evaluate()'s trial increment."""
    lbl = harness._label_cols(horizon)
    base_cols = ["date", "symbol", "regime_trend", "regime_vol", "mktcap_log"]
    p = panel[base_cols + [lbl["resid"], lbl["raw"]]].copy().rename(
        columns={lbl["resid"]: "target_eval", lbl["raw"]: "target_raw"})
    p["date"] = pd.to_datetime(p["date"])
    if drop_symbols:
        p = p[~p["symbol"].isin(drop_symbols)]
    f = harness._normalize_factor(factor)
    if drop_symbols:
        f = f[~f["symbol"].isin(drop_symbols)]
    if drop_dates_shift:
        # shift factor forward/back by N rebalance periods relative to target (rebalance-offset test)
        dates = sorted(f["date"].unique())
        shift_map = {d: dates[i + drop_dates_shift] for i, d in enumerate(dates)
                     if 0 <= i + drop_dates_shift < len(dates)}
        f = f.copy()
        f["date"] = f["date"].map(shift_map)
        f = f.dropna(subset=["date"])
    merged = f.merge(p, on=["date", "symbol"], how="inner").dropna(subset=["factor", "target_eval"])
    ic_series = harness._cross_sectional_ic(merged, min_names=min_names)
    ic_mean = float(ic_series.mean())
    ic_std = float(ic_series.std(ddof=1))
    ic_ir = ic_mean / ic_std if ic_std > 0 else np.nan
    ls_ret_raw, decile_table, top_sets = harness._decile_stats(merged, min_names=min_names)
    ann_ls = float(ls_ret_raw.mean() * 12)
    if quintile:
        # recompute using quintiles (top20%-bottom20%) instead of deciles
        def _q(g):
            g = g.dropna(subset=["factor", "target_raw"])
            if len(g) < min_names:
                return np.nan
            q = pd.qcut(g["factor"].rank(method="first"), 5, labels=False)
            top = g.loc[q == 4, "target_raw"].mean()
            bot = g.loc[q == 0, "target_raw"].mean()
            return top - bot
        q_series = merged.groupby("date").apply(_q)
        ann_ls = float(q_series.mean() * 12)
    mono = np.nan
    if not decile_table.empty and decile_table.shape[1] > 2:
        dmo = decile_table.mean(axis=0)
        from scipy import stats as _st
        mono, _ = _st.spearmanr(dmo.index.values, dmo.values)
    return {"ic_mean": ic_mean, "ic_ir": ic_ir, "ann_LS_v1": ann_ls, "mono": float(mono),
            "n_dates": int(len(ic_series)), "n_obs": int(len(merged))}


def main():
    log("Loading panel_long + long cubes + cached capstone legs...")
    panel, close, bench = LC.load_all()
    dates = LC._panel_dates(panel)
    legs = load_cached_legs()
    log(f"Cached legs available: {sorted(legs.keys())}")

    log("Building PLAIN residual momentum (no peer_relative wrap) fresh from close/bench...")
    mom_plain = LC.build_mom_resid_12_1(close, bench, dates)
    legs["mom_resid_plain"] = mom_plain

    TRUE7 = ["value_EY", "mom_resid_plain", "trend_ma65_slope", "quality_QMJ",
             "bs_issuance", "bs_asset_growth", "quality_cfo_pat"]
    missing = [n for n in TRUE7 if n not in legs]
    log(f"TRUE7 legs missing from cache: {missing}")
    TRUE7 = [n for n in TRUE7 if n in legs]

    factor_true7 = rank_avg(legs, TRUE7, min_legs=5)
    log(f"TRUE7 composite built: {len(factor_true7)} (date,symbol) obs, legs={TRUE7}")

    # ---- 1. ONE fresh honest harness.evaluate() call (genuinely new hypothesis) ----
    log("Evaluating TRUE7 composite via full harness (1 new honest trial, disclosed)...")
    card = harness.evaluate(factor_true7, "1Y", return_basis="resid", factor_id="AUDIT_TRUE7_1Y",
                             panel=panel, panel_source="real_panel_long_capstone",
                             family="AUDIT_TRUE7", write_card=True, cards_dir=RND_DIR / "cards")
    OUT["true7_card_summary"] = {
        "factor_id": card["factor_id"], "n_trials": card["n_trials"],
        "ic_ir": card["ic"]["ic_ir"], "ic_mean": card["ic"]["ic_mean"],
        "mono": card["deciles"]["monotonicity"], "ann_LS": card["long_short"]["ann_return_LS"],
        "net_of_cost": card["costs"]["net_of_cost_ann_return"], "turnover": card["turnover"],
        "dsr": card["dsr"]["dsr"], "pbo": card["pbo"]["pbo"],
        "lag_delta": card["lag_test"]["lag_test_delta"], "placebo_ic": card["placebo"]["placebo_ic"],
        "regime_breakdown": card["regime_breakdown"], "verdict": card["verdict"],
    }
    log(json.dumps(OUT["true7_card_summary"], indent=2, default=str))

    # ---- 2. Perturbation battery (lightweight, no trial increment) ----
    log("PERTURBATION: baseline (equal weight, decile) ...")
    base = quick_ic(factor_true7, panel)
    OUT["perturb_baseline"] = base

    log("PERTURBATION: leg-weight tilts ...")
    tilts = {}
    equal_w = {n: 1.0 for n in TRUE7}
    tilt_specs = {
        "overweight_EY_2x": {**equal_w, "value_EY": 2.0},
        "overweight_mom_2x": {**equal_w, "mom_resid_plain": 2.0},
        "overweight_quality_block_2x": {**equal_w, "quality_QMJ": 2.0, "quality_cfo_pat": 2.0},
        "overweight_bs_block_2x": {**equal_w, "bs_issuance": 2.0, "bs_asset_growth": 2.0},
        "drop_weakest_leg_bs_issuance": {n: (0.0 if n == "bs_issuance" else 1.0) for n in TRUE7},
    }
    for name, w in tilt_specs.items():
        f = rank_avg(legs, [n for n in TRUE7 if w.get(n, 1.0) > 0], weights=w, min_legs=4)
        tilts[name] = quick_ic(f, panel)
    OUT["perturb_leg_weight_tilts"] = tilts

    log("PERTURBATION: quintile vs decile spread ...")
    OUT["perturb_quintile"] = quick_ic(factor_true7, panel, quintile=True)

    log("PERTURBATION: rebalance-offset shift (+/-1, +/-2 monthly periods; finer week-level"
        " shift NOT tested -- panel granularity is monthly-only, disclosed gap) ...")
    offsets = {}
    for k in [-2, -1, 1, 2]:
        offsets[f"offset_{k:+d}m"] = quick_ic(factor_true7, panel, drop_dates_shift=k)
    OUT["perturb_rebalance_offset"] = offsets

    log("PERTURBATION: universe subsample (drop random 20%, 5 seeds) ...")
    all_syms = panel["symbol"].unique()
    sub_results = {}
    rng_results = []
    for seed in range(5):
        rng = np.random.default_rng(seed)
        drop_n = int(0.20 * len(all_syms))
        dropped = set(rng.choice(all_syms, size=drop_n, replace=False))
        r = quick_ic(factor_true7, panel, drop_symbols=dropped)
        rng_results.append(r["ic_ir"])
        sub_results[f"seed_{seed}"] = r
    OUT["perturb_universe_drop20pct"] = sub_results
    OUT["perturb_universe_drop20pct_ic_ir_range"] = [min(rng_results), max(rng_results)]

    log("PERTURBATION: drop each sector once ...")
    uni = pd.read_csv(UNIVERSE_PATH)
    sym_col = "symbol" if "symbol" in uni.columns else uni.columns[0]
    sec_col = next((c for c in uni.columns if "sector" in c.lower()), None)
    sector_results = {}
    if sec_col:
        for sec, g in uni.groupby(sec_col):
            dropped = set(g[sym_col].astype(str))
            r = quick_ic(factor_true7, panel, drop_symbols=dropped)
            sector_results[str(sec)] = r
    OUT["perturb_drop_each_sector"] = sector_results

    # ---- 3. Era-split IC (5-year buckets) ----
    log("ERA SPLIT: 2005-10 / 10-15 / 15-20 / 20-25 ...")
    lbl = harness._label_cols("1Y")
    base_cols = ["date", "symbol", "regime_trend", "regime_vol"]
    p = panel[base_cols + [lbl["resid"]]].copy().rename(columns={lbl["resid"]: "target_eval"})
    p["date"] = pd.to_datetime(p["date"])
    f = harness._normalize_factor(factor_true7)
    merged = f.merge(p, on=["date", "symbol"], how="inner").dropna(subset=["factor", "target_eval"])
    eras = {"2005-10": ("2005-01-01", "2010-01-01"), "2010-15": ("2010-01-01", "2015-01-01"),
            "2015-20": ("2015-01-01", "2020-01-01"), "2020-25": ("2020-01-01", "2025-12-31")}
    era_results = {}
    for era, (lo, hi) in eras.items():
        sub = merged[(merged["date"] >= lo) & (merged["date"] < hi)]
        if sub.empty:
            era_results[era] = {"n_dates": 0}
            continue
        ic_series = harness._cross_sectional_ic(sub, min_names=20)
        ic_mean = float(ic_series.mean()) if len(ic_series) else np.nan
        ic_std = float(ic_series.std(ddof=1)) if len(ic_series) > 1 else np.nan
        ic_ir = ic_mean / ic_std if ic_std and ic_std > 0 else np.nan
        era_results[era] = {"ic_mean": ic_mean, "ic_ir": ic_ir, "n_dates": int(len(ic_series))}
    OUT["era_split_ic"] = era_results

    (REPORTS_DIR / "PREIC_AUDIT_results.json").write_text(
        json.dumps(OUT, indent=2, default=str), encoding="utf-8")
    log("Wrote PREIC_AUDIT_results.json")
    log("DONE.")


if __name__ == "__main__":
    main()
