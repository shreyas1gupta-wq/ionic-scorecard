"""
CANONICAL 1Y COMPOSITE -- SURVIVORSHIP-FREE (PIT) REBUILD.
Arjun Rao (Head of Quant), T5 remediation, 2026-07-17.

Re-runs composite_final.py's exact construction (TRUE7 legs, equal-weight
rank-average, min_legs=5-of-7, decile harness card, corporate-action guard)
but on `rnd/panel/panel_pit.parquet` (built by build_panel_pit.py) instead of
`panel_long.parquet` -- i.e. each date's cross-section is restricted to the
NIFTY500_TICKER_2005_2025_Final.xlsx PIT membership as-of that date, BEFORE
any per-date percentile ranking happens.

METHODOLOGICAL NOTE (why "restrict before rank", not "rank then subset"):
  Spearman IC is rank-invariant to subsetting for a SINGLE ranked series
  (subsetting a full-universe percentile column preserves the within-subset
  ORDER). But this composite AVERAGES multiple independently-percentiled
  legs. Averaging full-universe percentiles for a subset of names is NOT the
  same number as averaging percentiles computed WITHIN that subset (the two
  scales differ whenever the subset's leg-value distribution differs from
  the full universe's -- which survivorship removal by construction does).
  So the honest survivorship-free composite recomputes rank_pct restricted
  to the PIT-eligible names at each date, not a post-hoc subset of the
  already-biased ranks. This script does that.

Outputs:
  rnd/cards/CANONICAL_7LEG_PIT_1Y.json
  rnd/panel/canonical_7leg_pit_scores.parquet
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))

import harness  # noqa: E402
import run_long_confirm as LC  # noqa: E402

CARDS_DIR = RND_DIR / "cards"
PANEL_DIR = RND_DIR / "panel"
LEGS_CACHE = PANEL_DIR / "capstone_legs.parquet"
PANEL_PIT_PATH = PANEL_DIR / "panel_pit.parquet"

TRUE7 = ["value_EY", "mom_resid_plain", "trend_ma65_slope", "quality_QMJ",
         "bs_issuance", "bs_asset_growth", "quality_cfo_pat"]
MIN_LEGS = 5  # same canonical choice as composite_final.py


def log(msg):
    print(f"[canonical_pit] {msg}", flush=True)


def load_cached_legs():
    d = pd.read_parquet(LEGS_CACHE)
    d["date"] = pd.to_datetime(d["date"])
    out = {}
    for leg, g in d.groupby("leg"):
        out[leg] = g.set_index(["date", "symbol"])["value"].rename("factor")
    return out


def rank_avg_pit(legs_dict, names, min_legs, eligible_idx: pd.MultiIndex):
    """Equal-weight rank-average, RESTRICTED to eligible_idx (date,symbol)
    pairs BEFORE the per-date rank_pct -- see module docstring for why this
    order matters for a survivorship-free re-score."""
    frames = []
    for n in names:
        r = legs_dict[n].rename("factor").reset_index()
        r.columns = ["date", "symbol", n]
        # restrict to PIT-eligible pairs FIRST
        r = r.set_index(["date", "symbol"])
        r = r[r.index.isin(eligible_idx)].reset_index()
        r[n] = r.groupby("date")[n].rank(pct=True)
        frames.append(r.set_index(["date", "symbol"])[n])
    wide = pd.concat(frames, axis=1)
    combo = wide.mean(axis=1, skipna=True)
    n_present = wide.notna().sum(axis=1)
    combo = combo.where(n_present >= min_legs)
    return combo.dropna().rename("factor")


def quintile_ls(factor, panel, min_names=20):
    lbl = harness._label_cols("1Y")
    p = panel[["date", "symbol", lbl["raw"]]].rename(columns={lbl["raw"]: "target_raw"}).copy()
    p["date"] = pd.to_datetime(p["date"])
    f = harness._normalize_factor(factor)
    merged = f.merge(p, on=["date", "symbol"], how="inner").dropna(subset=["factor", "target_raw"])

    def _q(g):
        g = g.dropna(subset=["factor", "target_raw"])
        if len(g) < min_names:
            return np.nan
        q = pd.qcut(g["factor"].rank(method="first"), 5, labels=False, duplicates="drop")
        top = g.loc[q == q.max(), "target_raw"].mean()
        bot = g.loc[q == q.min(), "target_raw"].mean()
        return top - bot

    q_series = merged.groupby("date").apply(_q, include_groups=False)
    q_series = q_series.dropna()
    return {
        "ann_return_LS_quintile": float(q_series.mean() * 12),
        "n_dates_quintile": int(len(q_series)),
    }


def main():
    t0 = time.time()
    log("Loading panel_pit (survivorship-free universe) + long cubes + cached capstone legs...")
    panel_pit = pd.read_parquet(PANEL_PIT_PATH)
    panel_pit["date"] = pd.to_datetime(panel_pit["date"])
    _, close, bench = LC.load_all()  # cubes are raw-price-derived, independent of PIT filter
    legs = load_cached_legs()
    log(f"panel_pit: {len(panel_pit)} rows, {panel_pit['date'].nunique()} dates, "
        f"{panel_pit['symbol'].nunique()} symbols")
    log(f"Cached legs available: {sorted(legs.keys())}")

    eligible_idx = pd.MultiIndex.from_frame(panel_pit[["date", "symbol"]].drop_duplicates())

    log("Building PLAIN residual momentum fresh from close/bench, on panel_pit's own dates...")
    mom_plain = LC.build_mom_resid_12_1(close, bench, LC._panel_dates(panel_pit))
    legs["mom_resid_plain"] = mom_plain

    missing = [n for n in TRUE7 if n not in legs]
    if missing:
        raise RuntimeError(f"Canonical 7 legs missing from cache: {missing}")

    log(f"Building SURVIVORSHIP-FREE composite: rank-average of {TRUE7} "
        f"restricted to PIT-eligible names per date, min_legs={MIN_LEGS}...")
    factor = rank_avg_pit(legs, TRUE7, min_legs=MIN_LEGS, eligible_idx=eligible_idx)
    log(f"Composite built: {len(factor)} (date,symbol) obs (vs biased-universe composite ~166k)")

    # ---- corporate-action guard (identical convention to composite_final.py) ----
    disc_col = "disc_event_in_window_1Y"
    panel_g = panel_pit.copy()
    mask = panel_g[disc_col].fillna(0) > 0
    n_excluded = int(mask.sum())
    panel_g.loc[mask, ["fwd_ret_1Y_raw", "fwd_ret_1Y_resid"]] = np.nan
    log(f"Corporate-action guard: excluded {n_excluded}/{len(panel_g)} disc-flagged rows from targets")

    log("Evaluating survivorship-free composite via harness.evaluate() -- 1 new honest trial, disclosed...")
    card = harness.evaluate(
        factor, "1Y", return_basis="resid", factor_id="CANONICAL_7LEG_PIT_1Y",
        panel=panel_g, panel_source="real_panel_pit_survivorship_free",
        family="CANONICAL_7LEG_PIT", write_card=True, cards_dir=CARDS_DIR,
    )

    log("Computing supplementary quintile long-short spread...")
    q_stats = quintile_ls(factor, panel_g)

    card["construction"] = {
        "legs": TRUE7,
        "weighting": "equal-weight rank-average, RESTRICTED to PIT-eligible names per date "
                     "BEFORE rank_pct (survivorship-free re-rank, not a post-hoc subset)",
        "min_legs_required": MIN_LEGS,
        "universe": "panel_pit.parquet (PIT-membership-filtered panel_long, see build_panel_pit.py) -- "
                    "NIFTY500_TICKER_2005_2025_Final.xlsx nearest-prior-snapshot membership per date",
        "corporate_action_guard": f"disc_event_in_window_1Y>0 rows NaN'd from fwd_ret_1Y target "
                                   f"({n_excluded} rows excluded)",
        "official_portfolio_construction": "decile (10-bin), harness.evaluate() default -- unchanged, shared harness",
        "score_map": "score = 200*(rank_pct(composite) - 0.5) in [-100,+100], zero fitted parameters",
    }
    card["quintile_supplementary"] = q_stats
    card["comparison_vs_biased"] = {
        "biased_card": "CANONICAL_7LEG_1Y (panel_long, no PIT universe filter)",
        "biased_ic_ir": 1.3450288630259197,
        "biased_n_ic_dates": 145,
        "biased_verdict": "KILL (PBO 0.909 > 0.5)",
    }
    (CARDS_DIR / "CANONICAL_7LEG_PIT_1Y.json").write_text(
        json.dumps(card, indent=2, default=str), encoding="utf-8")
    log(f"Wrote {CARDS_DIR / 'CANONICAL_7LEG_PIT_1Y.json'}")

    f_df = factor.reset_index()
    f_df["score"] = f_df.groupby("date")["factor"].rank(pct=True).sub(0.5).mul(200.0)
    f_df = f_df.rename(columns={"factor": "composite_rank_avg"})
    out_path = PANEL_DIR / "canonical_7leg_pit_scores.parquet"
    f_df.to_parquet(out_path, index=False)
    log(f"Wrote {out_path} ({len(f_df)} rows)")

    log(json.dumps({
        "ic_ir": card["ic"]["ic_ir"], "ic_mean": card["ic"]["ic_mean"],
        "monotonicity": card["deciles"]["monotonicity"],
        "lag_test_delta": card["lag_test"]["lag_test_delta"],
        "n_ic_dates": card["ic"]["n_ic_dates"], "n_trials_global": card["n_trials"],
        "dsr": card["dsr"]["dsr"], "pbo": card["pbo"]["pbo"],
        "quintile_ann_LS": q_stats["ann_return_LS_quintile"],
        "verdict": card["verdict"],
    }, indent=2))
    log("DONE.")


if __name__ == "__main__":
    main()
