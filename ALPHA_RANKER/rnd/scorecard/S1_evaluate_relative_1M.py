"""
S1 -- RELATIVE 1M evaluation harness. Owner: Arjun Rao (Quant Head, E-004).
Runs the full battery from SCORECARD_BLUEPRINT.md Sec 2.4 on rel_score_1M.parquet
against rnd/panel/panel_pit.parquet (survivorship-free). Reuses rnd/lib/harness.py
for the PRIMARY metrics + HARD GATES (one code path, per RESEARCH_PROTOCOL S3).
Era-split and drop-one-leg are computed locally (harness.evaluate() does not
expose those) using the SAME per-date Spearman-IC methodology harness uses
internally, so numbers are comparable to the harness card's ic.ic_mean.
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

THIS = Path(__file__).resolve()
SCORECARD_DIR = THIS.parent
RND = SCORECARD_DIR.parent
ALPHA = RND.parent

sys.path.insert(0, str(RND / "lib"))
import harness

SCORES_PATH = SCORECARD_DIR / "rel_score_1M.parquet"
PANEL_PIT_PATH = RND / "panel" / "panel_pit.parquet"
OUT_CARD = SCORECARD_DIR / "S1_REL_1M_harness_card.json"

HORIZON = "1M"
RETURN_BASIS = "excess"
MIN_NAMES = 20
PERIODS_PER_YEAR = 12

ERA_BOUNDS = [
    ("2005-2011", "2005-01-01", "2011-12-31"),
    ("2012-2015", "2012-01-01", "2015-12-31"),
    ("2015-2018", "2015-01-01", "2018-12-31"),
    ("2018-2021", "2018-01-01", "2021-12-31"),
    ("2021-2024", "2021-01-01", "2024-12-31"),
    ("2024-2026", "2024-01-01", "2026-12-31"),
]
SLICE_YEARS = [2018, 2020, 2022, 2024, 2026]


def rank_pct(s: pd.Series) -> pd.Series:
    return s.rank(pct=True, method="average")


def load_panel():
    p = pd.read_parquet(PANEL_PIT_PATH)
    p["date"] = pd.to_datetime(p["date"])
    return p


def build_merged(factor_series: pd.Series, panel: pd.DataFrame) -> pd.DataFrame:
    f = harness._normalize_factor(factor_series)
    lbl = harness._label_cols(HORIZON)
    target_col, raw_col = lbl[RETURN_BASIS], lbl["raw"]
    p = panel[["date", "symbol", target_col, raw_col]].rename(
        columns={target_col: "target_eval", raw_col: "target_raw"})
    m = f.merge(p, on=["date", "symbol"], how="inner").dropna(subset=["factor", "target_eval"])
    return m


def ic_series_of(merged: pd.DataFrame) -> pd.Series:
    return harness._cross_sectional_ic(merged, MIN_NAMES).dropna()


def ls_sharpe_of(merged: pd.DataFrame) -> dict:
    ls_ret_raw, decile_table, _ = harness._decile_stats(merged, min_names=MIN_NAMES)
    if len(ls_ret_raw) < 3 or ls_ret_raw.std(ddof=1) == 0:
        return {"ls_sharpe_ann": float("nan"), "n_periods": int(len(ls_ret_raw))}
    sharpe_ann = float(ls_ret_raw.mean() / ls_ret_raw.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR))
    return {"ls_sharpe_ann": sharpe_ann, "ls_mean_monthly": float(ls_ret_raw.mean()),
            "ls_std_monthly": float(ls_ret_raw.std(ddof=1)), "n_periods": int(len(ls_ret_raw))}


def era_split(merged: pd.DataFrame) -> dict:
    ic = ic_series_of(merged)
    out = {}
    for label, lo, hi in ERA_BOUNDS:
        sub = ic[(ic.index >= lo) & (ic.index <= hi)]
        out[label] = {"ic_mean": float(sub.mean()) if len(sub) else None, "n_dates": int(len(sub))}
    slices = {}
    for yr in SLICE_YEARS:
        sub = ic[ic.index.year == yr]
        slices[str(yr)] = {"ic_mean": float(sub.mean()) if len(sub) else None, "n_dates": int(len(sub))}
    return {"era_buckets": out, "single_year_slices": slices}


def drop_one_leg(scores: pd.DataFrame, panel: pd.DataFrame, full_weights_neutral: dict,
                  full_weights_washout: dict) -> dict:
    """Rebuild composite dropping one leg at a time (weights renormalized to
    sum 1 among the remaining two), evaluate mean IC each way, report
    dispersion vs the full-model IC. Uses the leg-component columns already
    written into rel_score_1M.parquet (mom_1M_component, earn_1M,
    qual_floor_1M, washout, neg_news_flag)."""
    legs = ["mom", "earn", "qual"]
    col = {"mom": "mom_1M_component", "earn": "earn_1M", "qual": "qual_floor_1M"}
    results = {}
    for drop in legs:
        keep = [l for l in legs if l != drop]
        w_neu = {l: full_weights_neutral[l] for l in keep}
        w_was = {l: full_weights_washout[l] for l in keep}
        s_neu = sum(w_neu.values())
        s_was = sum(w_was.values())
        w_neu = {l: v / s_neu for l, v in w_neu.items()}
        w_was = {l: v / s_was for l, v in w_was.items()}

        df = scores.copy()
        present = df[[col[l] for l in keep]].notna().all(axis=1)
        w0 = np.where(df["washout"], w_was[keep[0]], w_neu[keep[0]])
        w1 = np.where(df["washout"], w_was[keep[1]], w_neu[keep[1]])
        weighted = w0 * df[col[keep[0]]] + w1 * df[col[keep[1]]]
        weighted = weighted.where(present, np.nan)
        df["_ws"] = weighted
        df["composite_dropone"] = df.groupby("date")["_ws"].transform(rank_pct)
        df["composite_dropone"] = df["composite_dropone"].where(df["neg_news_flag"] != 1, np.nan)
        df["score_dropone"] = df.groupby("date")["composite_dropone"].transform(
            lambda s: 200.0 * (rank_pct(s) - 0.5))

        factor = df.dropna(subset=["score_dropone"]).set_index(["date", "symbol"])["score_dropone"]
        merged = build_merged(factor, panel)
        ic = ic_series_of(merged)
        ls = ls_sharpe_of(merged)
        results[f"drop_{drop}"] = {
            "kept_legs": keep, "ic_mean": float(ic.mean()) if len(ic) else None,
            "ic_ir": float(ic.mean() / ic.std(ddof=1)) if len(ic) > 1 and ic.std(ddof=1) else None,
            "n_dates": int(len(ic)), "ls_sharpe_ann": ls.get("ls_sharpe_ann"),
        }
    return results


def fm_lens_paragraph() -> str:
    return (
        "FM LENS (Arjun Rao, mandatory per Principal 2026-07-18): a 1M "
        "momentum + earnings-surprise + news-screen combo is exactly the kind "
        "of tilt a real short-horizon PM already runs informally -- 'is this "
        "name still working, did it just beat and guide up, and is there a "
        "skeleton in the news I don't know about' is a Monday-morning "
        "checklist, not a fitted model. The skip-15 momentum leg avoids the "
        "classic 1-month reversal trap; gating earnings on a CONFIRMED "
        "(reported, PIT) reading rather than a forecast keeps it honest; the "
        "quality floor doing nothing but excluding junk (not selecting on it) "
        "matches how a PM actually uses ROE/CFO-PAT at this horizon -- as a "
        "screen, never a driver. Where this is economically hollow, not "
        "statistically clean: the no-neg-news gate, as built, is a 55-name "
        "island in a ~750-name sea -- it reads like a real risk control but "
        "for ~93% of the universe it is a no-op passed by construction, not "
        "by verification. A PM using this scorecard needs to know that the "
        "'no adverse news' badge is only meaningful for the large-cap 55 and "
        "is silent (not clean) everywhere else -- shipping it unlabeled would "
        "be the statistically-clean-but-economically-hollow failure mode this "
        "review exists to catch. Conversely, the WASHOUT/rev5d substitution is "
        "the piece most likely to look fragile on paper (n=25 BEAR_OVERSOLD "
        "dates, DSR/PBO fail at that n per the firm's own low-t rule) but is "
        "economically the most sound leg here -- it fires only in the "
        "specific 17% oversold-extreme regime where the certified rev5d has "
        "already survived per-episode drop-one, era-split, and 2x-cost tests "
        "in REGIME_SPEC_V2 Sec 0. That is a case where thin-sample statistics "
        "should NOT override sound logic + prior certification, per the "
        "firm's own low-t re-screen rule."
    )


def main():
    scores = pd.read_parquet(SCORES_PATH)
    panel = load_panel()

    factor = scores.dropna(subset=["rel_score_1M"]).set_index(["date", "symbol"])["rel_score_1M"]
    print(f"scored obs: {len(factor)}  dates: {factor.index.get_level_values('date').nunique()}")

    card = harness.evaluate(
        factor, horizon=HORIZON, return_basis=RETURN_BASIS, factor_id="S1_REL_1M",
        panel=panel, panel_source="panel_pit_survivorship_free", family="S1_REL_1M",
        min_names_per_date=MIN_NAMES, n_placebo_shuffles=5, placebo_seed=42,
        write_card=True, cards_dir=SCORECARD_DIR,
    )

    merged = build_merged(factor, panel)
    ls_extra = ls_sharpe_of(merged)
    era = era_split(merged)

    weights_neutral = {"mom": 0.45, "earn": 0.40, "qual": 0.15}
    weights_washout = {"mom": 0.55, "earn": 0.30, "qual": 0.15}
    dropone = drop_one_leg(scores, panel, weights_neutral, weights_washout)

    full_report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "harness_card": card,
        "ls_sharpe_extra": ls_extra,
        "era_split": era,
        "drop_one_leg": dropone,
    }
    OUT_CARD.write_text(json.dumps(full_report, indent=2, default=str), encoding="utf-8")
    print(f"wrote {OUT_CARD}")
    print(json.dumps({
        "verdict_harness": card["verdict"],
        "ic_mean": card["ic"]["ic_mean"], "ic_ir": card["ic"]["ic_ir"],
        "monotonicity": card["deciles"]["monotonicity"],
        "lag_test_delta": card["lag_test"]["lag_test_delta"],
        "placebo_ic": card["placebo"]["placebo_ic"],
        "dsr": card["dsr"]["dsr"], "pbo": card["pbo"]["pbo"],
        "n_trials": card["n_trials"],
        "ls_sharpe_ann": ls_extra["ls_sharpe_ann"],
    }, indent=2))

    (SCORECARD_DIR / "S1_fm_lens.txt").write_text(fm_lens_paragraph(), encoding="utf-8")


if __name__ == "__main__":
    main()
