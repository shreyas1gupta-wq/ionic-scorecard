"""
W5IN: earnings-suppression-then-bounce (+ turnaround) -- 2x-sure battery.
Sanjay Kulkarni task, 2026-07-17. Foreground, synchronous, single run.

Evaluated against rnd/panel/panel_long.parquet (969 symbols, 2005-04-29 ->
2025-12-05, real fwd_ret_1Y/5Y) so 5Y has genuine non-NaN coverage and an
era-split is meaningful.

Battery per factor (signed IC/IR, monotonicity, lag+placebo, DSR/PBO via
harness.evaluate() for the CARD; drop-one-sector, drop-one-year, era-split,
orthogonality-vs-(bs_asset_growth, canonical_7leg composite), and
incremental-after-residualization computed here directly against
harness._cross_sectional_ic, following the sameer_preic_audit2.py /
dropone_summary.json precedent conventions already in this repo).
"""
from __future__ import annotations
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
ALPHA_DIR = RND_DIR.parent
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))

import harness  # noqa: E402
import builders_w5in as W  # noqa: E402

PANEL_LONG_PATH = RND_DIR / "panel" / "panel_long.parquet"
LEGS_PATH = RND_DIR / "panel" / "capstone_legs.parquet"
C7_PATH = RND_DIR / "panel" / "canonical_7leg_scores.parquet"
UNIVERSE_PATH = ALPHA_DIR / "data" / "universe" / "nifty_total_market_750.csv"
CARDS_DIR = RND_DIR / "cards"
WAVE4_DIR = RND_DIR / "wave4"
OUT_JSON = WAVE4_DIR / "W5IN_battery_results.json"
OUT_MD = WAVE4_DIR / "EARNINGS_INFLECTION.md"

HORIZONS = ["1Y", "5Y"]
MIN_NAMES = 20
MIN_NAMES_TURNAROUND = 10  # event-conditional subset, thinner per-date breadth expected


# ==========================================================================
# helpers
# ==========================================================================
def load_panel():
    p = pd.read_parquet(PANEL_LONG_PATH)
    p["date"] = pd.to_datetime(p["date"])
    return p


def quick_ic(factor: pd.Series, panel: pd.DataFrame, horizon: str, min_names=MIN_NAMES,
             drop_symbols=None, only_dates=None) -> dict:
    lbl = harness._label_cols(horizon)
    p = panel[["date", "symbol", lbl["resid"]]].copy().rename(columns={lbl["resid"]: "target_eval"})
    p["date"] = pd.to_datetime(p["date"])
    if drop_symbols:
        p = p[~p["symbol"].isin(drop_symbols)]
    if only_dates is not None:
        p = p[p["date"].isin(only_dates)]
    f = harness._normalize_factor(factor)
    if drop_symbols:
        f = f[~f["symbol"].isin(drop_symbols)]
    if only_dates is not None:
        f = f[f["date"].isin(only_dates)]
    merged = f.merge(p, on=["date", "symbol"], how="inner").dropna(subset=["factor", "target_eval"])
    ic_series = harness._cross_sectional_ic(merged, min_names=min_names).dropna()
    ic_mean = float(ic_series.mean()) if len(ic_series) else float("nan")
    ic_std = float(ic_series.std(ddof=1)) if len(ic_series) > 1 else float("nan")
    ic_ir = ic_mean / ic_std if ic_std and ic_std > 0 else float("nan")
    return {"ic_mean": ic_mean, "ic_ir": ic_ir, "n_dates_scored": int(len(ic_series)),
            "n_obs": int(len(merged))}


def era_split(factor: pd.Series, panel: pd.DataFrame, horizon: str, min_names=MIN_NAMES) -> dict:
    f = harness._normalize_factor(factor)
    all_dates = sorted(f["date"].unique())
    if len(all_dates) < 8:
        return {"pre": None, "post": None, "both_hold": False, "note": "too few dates"}
    mid = all_dates[len(all_dates) // 2]
    pre_dates = [d for d in all_dates if d < mid]
    post_dates = [d for d in all_dates if d >= mid]
    pre = quick_ic(factor, panel, horizon, min_names=min_names, only_dates=pre_dates)
    post = quick_ic(factor, panel, horizon, min_names=min_names, only_dates=post_dates)
    both_hold = (not np.isnan(pre["ic_mean"]) and not np.isnan(post["ic_mean"])
                 and pre["ic_mean"] > 0 and post["ic_mean"] > 0)
    return {"split_date": str(pd.Timestamp(mid).date()), "pre": pre, "post": post,
            "both_hold_positive_sign": bool(both_hold)}


def drop_one_sector(factor: pd.Series, panel: pd.DataFrame, horizon: str, full_ic: float,
                     min_names=MIN_NAMES) -> dict:
    uni = pd.read_csv(UNIVERSE_PATH)
    sec_col, sym_col = "Industry", "Symbol"
    results = {}
    for sec, g in uni.groupby(sec_col):
        dropped = set(g[sym_col].astype(str))
        r = quick_ic(factor, panel, horizon, min_names=min_names, drop_symbols=dropped)
        results[str(sec)] = r
    valid = {k: v for k, v in results.items() if not np.isnan(v["ic_mean"])}
    n_sign_flips = sum(1 for v in valid.values() if np.sign(v["ic_mean"]) != np.sign(full_ic))
    worst = min(valid.items(), key=lambda kv: kv[1]["ic_mean"]) if valid else (None, {})
    return {"per_sector": results, "n_sign_flips": n_sign_flips, "n_sectors": len(valid),
            "worst_sector_drop": [worst[0], worst[1].get("ic_mean")] if valid else None}


def drop_one_year(factor: pd.Series, panel: pd.DataFrame, horizon: str, full_ic: float,
                   min_names=MIN_NAMES) -> dict:
    f = harness._normalize_factor(factor)
    years = sorted(f["date"].dt.year.unique())
    results = {}
    for yr in years:
        dates_keep = [d for d in panel["date"].unique() if pd.Timestamp(d).year != yr]
        r = quick_ic(factor, panel, horizon, min_names=min_names, only_dates=dates_keep)
        results[int(yr)] = r
    valid = {k: v for k, v in results.items() if not np.isnan(v["ic_mean"])}
    n_sign_flips = sum(1 for v in valid.values() if np.sign(v["ic_mean"]) != np.sign(full_ic))
    worst = min(valid.items(), key=lambda kv: kv[1]["ic_mean"]) if valid else (None, {})
    return {"n_sign_flips": n_sign_flips, "n_years": len(valid),
            "worst_year_drop": [worst[0], worst[1].get("ic_mean")] if valid else None}


def orthogonality(factor: pd.Series, panel: pd.DataFrame) -> dict:
    legs = pd.read_parquet(LEGS_PATH)
    legs["date"] = pd.to_datetime(legs["date"])
    ag = legs[legs["leg"] == "bs_asset_growth"].set_index(["date", "symbol"])["value"].rename("asset_growth")
    c7 = pd.read_parquet(C7_PATH)
    c7["date"] = pd.to_datetime(c7["date"])
    c7s = c7.set_index(["date", "symbol"])["score"].rename("composite7")

    f = harness._normalize_factor(factor).set_index(["date", "symbol"])["factor"]
    m = pd.concat([f, ag, c7s], axis=1).dropna()
    corr_ag = float(stats.spearmanr(m["factor"], m["asset_growth"])[0]) if len(m) > 5 else float("nan")
    corr_c7 = float(stats.spearmanr(m["factor"], m["composite7"])[0]) if len(m) > 5 else float("nan")
    return {"n_overlap": int(len(m)), "corr_vs_bs_asset_growth": corr_ag,
            "corr_vs_canonical_7leg_composite": corr_c7}


def incremental_ic(factor: pd.Series, panel: pd.DataFrame, horizon: str, min_names=MIN_NAMES) -> dict:
    """Cross-sectional per-date OLS residualize `factor` against
    [bs_asset_growth, canonical_7leg composite], then re-score IC of the
    residual -- 'does this add anything the book doesn't already own'."""
    legs = pd.read_parquet(LEGS_PATH)
    legs["date"] = pd.to_datetime(legs["date"])
    ag = legs[legs["leg"] == "bs_asset_growth"].set_index(["date", "symbol"])["value"].rename("asset_growth")
    c7 = pd.read_parquet(C7_PATH)
    c7["date"] = pd.to_datetime(c7["date"])
    c7s = c7.set_index(["date", "symbol"])["score"].rename("composite7")

    f = harness._normalize_factor(factor).set_index(["date", "symbol"])["factor"]
    m = pd.concat([f, ag, c7s], axis=1).dropna().reset_index()

    def _resid(g):
        if len(g) < 15:
            return pd.Series(np.nan, index=g.index)
        X = np.column_stack([np.ones(len(g)), g["asset_growth"].values, g["composite7"].values])
        y = g["factor"].values
        try:
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        except np.linalg.LinAlgError:
            return pd.Series(np.nan, index=g.index)
        return pd.Series(y - X @ beta, index=g.index)

    m["resid_factor"] = m.groupby("date", group_keys=False).apply(_resid, include_groups=False)
    resid_series = m.set_index(["date", "symbol"])["resid_factor"].dropna()
    ic = quick_ic(resid_series, panel, horizon, min_names=min_names)
    ic["n_used_for_residualization"] = int(len(m))
    return ic


def payoff_skew(card: dict) -> float:
    return card.get("dsr", {}).get("skew")


# ==========================================================================
# main
# ==========================================================================
def main():
    panel = load_panel()
    print(f"panel_long: rows={len(panel)} dates={panel['date'].nunique()} symbols={panel['symbol'].nunique()}")

    diag = W.flag_coverage_diagnostics()
    print("coverage diagnostics:", diag)

    factors = {
        "W5IN_supp_raw": W.build_suppression_raw(panel),
        "W5IN_cond_noqual": W.build_conditional_no_quality(panel),
        "W5IN_cond_full": W.build_conditional_full(panel),
        "W5IN_turnaround": W.build_turnaround(panel),
    }
    for name, s in factors.items():
        print(f"{name}: n_obs={len(s)} n_dates={s.reset_index()['date'].nunique() if len(s) else 0}")

    # sanity: confirm the raw asset-growth leg IS negative on THIS panel/harness
    legs = pd.read_parquet(LEGS_PATH)
    legs["date"] = pd.to_datetime(legs["date"])
    ag_leg = legs[legs["leg"] == "bs_asset_growth"].set_index(["date", "symbol"])["value"].rename("factor")
    ag_check = {h: quick_ic(ag_leg, panel, h) for h in HORIZONS}
    print("bs_asset_growth leg sanity check (repo convention: this leg is -z(assetgrowth), "
          "so POSITIVE ic_mean here = confirms low-growth-good / high-growth-bad):", ag_check)

    results = {"panel": {"rows": len(panel), "dates": int(panel["date"].nunique()),
                          "symbols": int(panel["symbol"].nunique())},
               "coverage_diagnostics": diag,
               "bs_asset_growth_leg_sanity_check": ag_check,
               "factors": {}}

    min_names_map = {"W5IN_turnaround": MIN_NAMES_TURNAROUND}

    for fname, fseries in factors.items():
        min_names = min_names_map.get(fname, MIN_NAMES)
        results["factors"][fname] = {}
        for h in HORIZONS:
            print(f"\n=== {fname} / {h} ===")
            card = harness.evaluate(fseries, horizon=h, return_basis="resid", factor_id=f"{fname}_{h}",
                                     family="W5IN", panel=panel, panel_source="panel_long",
                                     min_names_per_date=min_names, cards_dir=CARDS_DIR)
            full_ic = card.get("ic", {}).get("ic_mean", float("nan"))
            era = era_split(fseries, panel, h, min_names=min_names)
            do_sec = drop_one_sector(fseries, panel, h, full_ic, min_names=min_names)
            do_yr = drop_one_year(fseries, panel, h, full_ic, min_names=min_names)
            orth = orthogonality(fseries, panel)
            incr = incremental_ic(fseries, panel, h, min_names=min_names)

            summary = {
                "verdict_harness": card.get("verdict"),
                "ic_mean": card.get("ic", {}).get("ic_mean"),
                "ic_ir": card.get("ic", {}).get("ic_ir"),
                "newey_west_t": card.get("ic", {}).get("newey_west_t"),
                "n_dates": card.get("n_dates"), "n_obs": card.get("n_obs"),
                "monotonicity": card.get("deciles", {}).get("monotonicity"),
                "ann_return_LS_horizon_aware": card.get("long_short", {}).get("ann_return_LS_horizon_aware"),
                "net_of_cost_ann_return_horizon_aware": card.get("costs", {}).get("net_of_cost_ann_return_horizon_aware"),
                "hit_rate": card.get("long_short", {}).get("hit_rate"),
                "lag_test_delta": card.get("lag_test", {}).get("lag_test_delta"),
                "placebo_ic": card.get("placebo", {}).get("placebo_ic"),
                "dsr": card.get("dsr", {}).get("dsr"),
                "pbo": card.get("pbo", {}).get("pbo"),
                "skew": payoff_skew(card),
                "era_split": era,
                "drop_one_sector": {"n_sign_flips": do_sec["n_sign_flips"], "n_sectors": do_sec["n_sectors"],
                                     "worst_sector_drop": do_sec["worst_sector_drop"]},
                "drop_one_year": {"n_sign_flips": do_yr["n_sign_flips"], "n_years": do_yr["n_years"],
                                   "worst_year_drop": do_yr["worst_year_drop"]},
                "orthogonality": orth,
                "incremental_after_residualization": incr,
            }
            results["factors"][fname][h] = summary
            print(json.dumps(summary, indent=2, default=str))

    OUT_JSON.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\nwritten: {OUT_JSON}")
    return results


if __name__ == "__main__":
    main()
