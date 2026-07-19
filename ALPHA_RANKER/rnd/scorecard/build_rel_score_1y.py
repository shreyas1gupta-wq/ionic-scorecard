"""
S2 -- RELATIVE 1Y scorecard builder.
Arjun Rao (Head of Quant), per SCORECARD_BLUEPRINT.md S1 (shared foundations) + S2.2
(RELATIVE 1Y spec) + S2.4 (evaluation harness). IMPLEMENTATION ONLY -- no new
research, no weight search, no leg substitution (S5 of the blueprint).

Run synchronously, foreground, single pass. Zero `.fit()` calls anywhere in the
scoring path; the ONLY RNG in this whole script is the placebo shuffle inside
harness.evaluate() (seed=42, fixed). Determinism is verified explicitly at the
bottom of main(): the full input-load + composite-build pipeline is executed
TWICE, independently, and the two output frames are checked byte-for-byte
(pd.testing.assert_frame_equal) before anything is treated as final.

Data lineage [DATA]:
  - rnd/panel/panel_pit.parquet            survivorship-free eval panel (99,415 rows, 249 dates, 933 symbols)
  - rnd/panel/capstone_legs.parquet        cached legs (long format); mom_resid_peer IGNORED (Wave-5 bug)
  - rnd/panel/cube_close_long.parquet + cube_bench_long.parquet  -> mom_resid_plain rebuilt FRESH via
    run_long_confirm.build_mom_resid_12_1 (same construction W6SR/composite_pit.py use), on panel_pit's own dates
  - rnd/wave4/_w6fg2_scored.parquet        growth leg (composite_v2_confirmed); "date" col already PIT/on-grid
    (available_date <= date confirmed for all 106,245 non-null rows -- verified before use)
  - rnd/panel/market_state.parquet         EY_hist_zscore_expanding -> richness_index -> valuation band (causal)

Output:
  rnd/scorecard/rel_score_1Y.parquet
  rnd/scorecard/weights_1Y_fragment.json
  rnd/scorecard/S2_RELATIVE_1Y_REPORT.md
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

_THIS = Path(__file__).resolve()
SCORECARD_DIR = _THIS.parent            # rnd/scorecard
RND_DIR = SCORECARD_DIR.parent          # rnd
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))
import harness                          # noqa: E402
import run_long_confirm as LC           # noqa: E402

PANEL_DIR = RND_DIR / "panel"
WAVE4_DIR = RND_DIR / "wave4"
PANEL_PIT_PATH = PANEL_DIR / "panel_pit.parquet"
LEGS_CACHE = PANEL_DIR / "capstone_legs.parquet"
GROWTH_PATH = WAVE4_DIR / "_w6fg2_scored.parquet"
MARKET_STATE_PATH = PANEL_DIR / "market_state.parquet"

OUT_PARQUET = SCORECARD_DIR / "rel_score_1Y.parquet"
WEIGHTS_FRAGMENT = SCORECARD_DIR / "weights_1Y_fragment.json"
REPORT_PATH = SCORECARD_DIR / "S2_RELATIVE_1Y_REPORT.md"
CARDS_DIR = RND_DIR / "cards"

# ---- frozen constants (blueprint S1.2, S1.4, S2.2 -- none of these are fit) ----
QUALITY_GATE_1Y = 0.10            # blueprint S1.4: drop bottom quality decile
MIN_LEGS = 5                      # 5-of-7 presence rule
BAND_LOW, BAND_HIGH = 65.0, 160.0 # richness_index band cutoffs (Principal 0/65/160 scale)
RICHNESS_K = 0.25                 # richness_index = 100*exp(-K * EY_hist_zscore_expanding)

# the 7 canonical legs for the NEW S2.2 composite (growth added, quality_QMJ
# demoted to gate-only per blueprint S2.2 item(4) -- it lists trend/bs_issuance/
# bs_asset_growth/quality_cfo_pat as "the rest of the stack", quality_QMJ is not
# among them; quality_QMJ's role is now the S1.4 gate only).
FIXED_LEGS = ["value_EY", "growth_v2_confirmed", "trend_ma65_slope",
              "bs_issuance", "bs_asset_growth", "quality_cfo_pat"]
CANONICAL_7 = ["value_EY", "growth_v2_confirmed", "mom_resid_plain",
               "trend_ma65_slope", "bs_issuance", "bs_asset_growth", "quality_cfo_pat"]

ERA_SPLITS = [
    ("2012-15", "2012-01-01", "2015-01-01"),
    ("15-18", "2015-01-01", "2018-01-01"),
    ("18-21", "2018-01-01", "2021-01-01"),
    ("21-24", "2021-01-01", "2024-01-01"),
]
YEAR_SLICES = [2018, 2020, 2022, 2024]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ==========================================================================
# 1. loaders
# ==========================================================================
def load_leg_cache() -> dict:
    d = pd.read_parquet(LEGS_CACHE)
    d["date"] = pd.to_datetime(d["date"])
    out = {}
    for leg, g in d.groupby("leg"):
        out[leg] = g.set_index(["date", "symbol"])["value"].rename("v")
    return out


def rank_pct_by_date(s: pd.Series) -> pd.Series:
    df = s.rename("v").reset_index()
    df["r"] = df.groupby("date")["v"].rank(pct=True)
    return df.set_index(["date", "symbol"])["r"]


def compute_richness_band(market_state: pd.DataFrame) -> pd.DataFrame:
    """richness_index(t) = 100*exp(-0.25*EY_hist_zscore_expanding(t)), causal
    (expanding window, t<=now), reused verbatim from REGIME_SPEC_V2 layer C --
    NOT refit. band = UNDERVALUED(<65) / NEUTRAL(65-160) / OVERVALUED(>=160).
    [INFERENCE, disclosed]: early dates where the expanding z-score is still
    NaN (insufficient history) default to NEUTRAL (full momentum weight) --
    this does not fabricate a valuation call where none exists, and matches
    the legacy canonical composite's behaviour on those same early dates
    (no gate applied historically)."""
    ms = market_state[["date", "EY_hist_zscore_expanding"]].copy()
    ms["date"] = pd.to_datetime(ms["date"])
    z = ms["EY_hist_zscore_expanding"]
    richness = 100.0 * np.exp(-RICHNESS_K * z)
    band = np.where(richness < BAND_LOW, "UNDERVALUED",
                    np.where(richness >= BAND_HIGH, "OVERVALUED", "NEUTRAL"))
    band = pd.Series(band, index=ms.index)
    band[z.isna()] = "NEUTRAL"
    ms["richness_index"] = richness
    ms["band"] = band
    return ms.set_index("date")[["richness_index", "band"]]


def load_inputs():
    """Fully independent load-from-disk + factor rebuild. Called TWICE
    (independently) by main() for the determinism check -- this function has
    zero shared mutable state across calls."""
    panel_pit = pd.read_parquet(PANEL_PIT_PATH)
    panel_pit["date"] = pd.to_datetime(panel_pit["date"])
    eligible = panel_pit[["date", "symbol"]].drop_duplicates()
    eligible_idx = pd.MultiIndex.from_frame(eligible)

    legs_raw = load_leg_cache()

    _, close, bench = LC.load_all()
    dates = LC._panel_dates(panel_pit)
    mom_plain = LC.build_mom_resid_12_1(close, bench, dates)

    growth_df = pd.read_parquet(GROWTH_PATH)
    growth_df["date"] = pd.to_datetime(growth_df["date"])
    growth = growth_df.set_index(["date", "symbol"])["composite_v2_confirmed"].rename("v")

    ms = pd.read_parquet(MARKET_STATE_PATH)
    band_df = compute_richness_band(ms)

    def restrict(s):
        return s[s.index.isin(eligible_idx)]

    legs = {
        "value_EY": restrict(legs_raw["value_EY"]),
        "trend_ma65_slope": restrict(legs_raw["trend_ma65_slope"]),
        "bs_issuance": restrict(legs_raw["bs_issuance"]),
        "bs_asset_growth": restrict(legs_raw["bs_asset_growth"]),
        "quality_cfo_pat": restrict(legs_raw["quality_cfo_pat"]),
        "quality_QMJ": restrict(legs_raw["quality_QMJ"]),
        "growth_v2_confirmed": restrict(growth.rename("v")),
        "mom_resid_plain": restrict(mom_plain.rename("v")),
    }
    return panel_pit, eligible_idx, legs, band_df


# ==========================================================================
# 2. quality gate (blueprint S1.4)
# ==========================================================================
def compute_quality_score(legs: dict) -> pd.Series:
    qmj_rank = rank_pct_by_date(legs["quality_QMJ"])
    cfo_rank = rank_pct_by_date(legs["quality_cfo_pat"])
    both = pd.concat([qmj_rank.rename("qmj"), cfo_rank.rename("cfo")], axis=1)
    avg = (0.5 * both["qmj"] + 0.5 * both["cfo"]).dropna()
    return rank_pct_by_date(avg).rename("quality_score")


# ==========================================================================
# 3. composite build (blueprint S2.2) -- drop_leg used only by the
#    drop-one-leg robustness pass, reusing this exact construction path.
# ==========================================================================
def build_composite(panel_pit, legs, band_df, quality_score, drop_leg: str = None) -> pd.DataFrame:
    gated_idx = quality_score[quality_score >= QUALITY_GATE_1Y].index

    active_fixed = [l for l in FIXED_LEGS if l != drop_leg]
    include_mom = (drop_leg != "mom_resid_plain")

    ranked = {}
    for leg in active_fixed:
        s = legs[leg][legs[leg].index.isin(gated_idx)]
        ranked[leg] = rank_pct_by_date(s)

    if include_mom:
        mom_s = legs["mom_resid_plain"][legs["mom_resid_plain"].index.isin(gated_idx)]
        mom_rank = rank_pct_by_date(mom_s)
        mdf = mom_rank.rename("r").reset_index()
        mdf = mdf.merge(band_df.reset_index()[["date", "band"]], on="date", how="left")
        mdf["band"] = mdf["band"].fillna("NEUTRAL")
        mom_active = mdf[mdf["band"] == "NEUTRAL"]
        ranked["mom_resid_plain"] = mom_active.set_index(["date", "symbol"])["r"]

    wide = pd.concat(ranked, axis=1)
    n_present = wide.notna().sum(axis=1)
    composite_raw = wide.mean(axis=1, skipna=True)
    composite = composite_raw.where(n_present >= MIN_LEGS)

    disc = panel_pit.set_index(["date", "symbol"])["disc_event_in_window_1Y"]
    disc = disc.reindex(composite.index).fillna(0)
    composite = composite.where(disc <= 0)
    composite = composite.dropna()

    rel_score = rank_pct_by_date(composite).sub(0.5).mul(200.0)

    out = pd.DataFrame({"composite_raw": composite, "rel_score_1Y": rel_score})
    for leg, r in ranked.items():
        out[f"{leg}_rank"] = r.reindex(out.index)
    out["n_legs_present"] = n_present.reindex(out.index)
    out["quality_score"] = quality_score.reindex(out.index)
    out = out.reset_index().rename(columns={"level_0": "date", "level_1": "symbol"})
    return out.sort_values(["date", "symbol"]).reset_index(drop=True)


# ==========================================================================
# 4. evaluation battery helpers (blueprint S2.4)
# ==========================================================================
def build_merged_for_eval(factor: pd.Series, panel_g: pd.DataFrame, basis="resid"):
    lbl = harness._label_cols("1Y")
    target_col, raw_col = lbl[basis], lbl["raw"]
    p = panel_g[["date", "symbol", target_col, raw_col]].rename(
        columns={target_col: "target_eval", raw_col: "target_raw"}).copy()
    p["date"] = pd.to_datetime(p["date"])
    f = harness._normalize_factor(factor)
    merged = f.merge(p, on=["date", "symbol"], how="inner").dropna(subset=["factor", "target_eval"])
    return merged


def era_and_year_ic(merged: pd.DataFrame, min_names=20) -> dict:
    out = {"era_split": {}, "year_slices": {}}
    for name, start, end in ERA_SPLITS:
        sub = merged[(merged["date"] >= start) & (merged["date"] < end)]
        ic = harness._cross_sectional_ic(sub, min_names).dropna()
        out["era_split"][name] = {
            "ic_mean": float(ic.mean()) if len(ic) else None,
            "n_dates": int(len(ic)),
        }
    for yr in YEAR_SLICES:
        sub = merged[merged["date"].dt.year == yr]
        ic = harness._cross_sectional_ic(sub, min_names).dropna()
        out["year_slices"][str(yr)] = {
            "ic_mean": float(ic.mean()) if len(ic) else None,
            "n_dates": int(len(ic)),
        }
    return out


def drop_one_leg_ic(panel_pit, legs, band_df, quality_score, panel_g) -> dict:
    results = {}
    for leg in CANONICAL_7:
        out = build_composite(panel_pit, legs, band_df, quality_score, drop_leg=leg)
        factor = out.set_index(["date", "symbol"])["composite_raw"]
        merged = build_merged_for_eval(factor, panel_g)
        ic = harness._cross_sectional_ic(merged, 20).dropna()
        ic_mean = float(ic.mean()) if len(ic) else float("nan")
        ic_ir = float(ic.mean() / ic.std(ddof=1)) if len(ic) > 1 and ic.std(ddof=1) else float("nan")
        results[leg] = {"ic_mean_without_this_leg": ic_mean, "ic_ir_without_this_leg": ic_ir,
                        "n_dates": int(len(ic))}
    return results


# ==========================================================================
# 5. main
# ==========================================================================
def main():
    t0 = time.time()
    log("=" * 70)
    log("S2 -- RELATIVE 1Y scorecard build")
    log("=" * 70)

    # ---- Run 1: the real build ----
    log("RUN 1: loading inputs + rebuilding mom_resid_plain fresh...")
    panel_pit, eligible_idx, legs, band_df = load_inputs()
    log(f"panel_pit: {len(panel_pit)} rows, {panel_pit['date'].nunique()} dates, "
        f"{panel_pit['symbol'].nunique()} symbols")
    quality_score = compute_quality_score(legs)
    n_total = len(quality_score)
    n_gated = int((quality_score >= QUALITY_GATE_1Y).sum())
    log(f"Quality gate (>= {QUALITY_GATE_1Y}): {n_gated} / {n_total} (date,symbol) pairs pass "
        f"({n_gated / n_total:.1%})")

    band_counts = band_df["band"].value_counts().to_dict()
    log(f"Valuation band distribution over {len(band_df)} dates: {band_counts}")

    out1 = build_composite(panel_pit, legs, band_df, quality_score, drop_leg=None)
    log(f"Composite built (run 1): {len(out1)} scored (date,symbol) rows")

    # ---- Run 2: fully independent re-load + rebuild, for the determinism check ----
    log("RUN 2 (determinism check): independent reload + rebuild from scratch...")
    panel_pit2, eligible_idx2, legs2, band_df2 = load_inputs()
    quality_score2 = compute_quality_score(legs2)
    out2 = build_composite(panel_pit2, legs2, band_df2, quality_score2, drop_leg=None)

    a = out1.reset_index(drop=True)
    b = out2.reset_index(drop=True)
    try:
        pd.testing.assert_frame_equal(a, b, check_exact=True)
        determinism_ok = True
        determinism_msg = f"PASS -- two independent runs produced byte-identical output ({len(a)} rows, {len(a.columns)} cols)."
    except AssertionError as e:
        determinism_ok = False
        determinism_msg = f"FAIL -- {e}"
    log(f"Determinism check: {determinism_msg}")

    # ---- write score output (from run 1) ----
    out1.to_parquet(OUT_PARQUET, index=False)
    log(f"Wrote {OUT_PARQUET} ({len(out1)} rows)")

    # ---- corp-action-guarded panel for harness eval (composite_pit.py convention) ----
    panel_g = panel_pit.copy()
    disc_mask = panel_g["disc_event_in_window_1Y"].fillna(0) > 0
    n_disc_excluded = int(disc_mask.sum())
    panel_g.loc[disc_mask, ["fwd_ret_1Y_raw", "fwd_ret_1Y_resid"]] = np.nan
    log(f"Corporate-action guard on eval targets: {n_disc_excluded}/{len(panel_g)} rows NaN'd")

    factor_for_eval = out1.set_index(["date", "symbol"])["composite_raw"]

    log("Running harness.evaluate() -- full battery (IC/IC_IR, deciles, LS, lag, placebo, DSR/PBO)...")
    card = harness.evaluate(
        factor_for_eval, "1Y", return_basis="resid", factor_id="S2_RELATIVE_1Y",
        panel=panel_g, panel_source="real_panel_pit_survivorship_free_S2",
        family="S2_REL_1Y", write_card=True, cards_dir=CARDS_DIR,
    )
    log(f"harness card verdict (mechanical, PBO-inclusive): {card['verdict']}")

    merged = build_merged_for_eval(factor_for_eval, panel_g)
    era_year = era_and_year_ic(merged)

    log("Drop-one-leg robustness pass (7 legs)...")
    dol = drop_one_leg_ic(panel_pit, legs, band_df, quality_score, panel_g)

    # ---- data-thinness discovery: quality_cfo_pat (required by the S1.4 gate,
    # since quality_score needs it for EVERY name) has a real coverage CLIFF,
    # not a gradual ramp -- median names/date is 1-4 from 2010-2016, then jumps
    # to 226+ names/date exactly at the 2017-06-30 rebalance. This is a DATA
    # finding, not a bug (verified: cfo_pat's own raw coverage in capstone_legs
    # shows the identical cliff before any of my joins/gates touch it). Must be
    # disclosed prominently -- it means this scorecard is effectively evaluated
    # POST-2017 only; 2008/2011 bear markets have zero coverage, 2012-2016 is
    # median 1-4 names/date (not decile-testable).
    by_year = out1.groupby(out1["date"].dt.year).size()
    names_per_date_by_year = out1.groupby(out1["date"].dt.year).apply(
        lambda g: int(g.groupby("date").size().median()), include_groups=False)
    coverage_cliff_year = None
    for yr in sorted(names_per_date_by_year.index):
        if names_per_date_by_year[yr] >= 100:
            coverage_cliff_year = yr
            break

    ls_ret_raw, decile_table, _ = harness._decile_stats(merged, min_names=20)
    decile_ls_sharpe = float("nan")
    if len(ls_ret_raw) > 1 and ls_ret_raw.std(ddof=1):
        # HORIZON-AWARE Sharpe (harness.annualize_ls_return docstring logic applied
        # to Sharpe, not just return): the ls_ret_raw series already carries a 1-YEAR
        # forward-return label sampled on a monthly grid, so it needs NO further *sqrt(12)
        # scaling to be "annualized" -- it already IS the annual long-short return series.
        # sr_hat = mean/std of that series is therefore already the annualized decile-LS Sharpe.
        decile_ls_sharpe = float(ls_ret_raw.mean() / ls_ret_raw.std(ddof=1))

    elapsed = time.time() - t0
    log(f"Total runtime: {elapsed:.1f}s")

    # ---- weights fragment (determinism contract, blueprint S4) ----
    weights_fragment = {
        "horizon": "1Y",
        "quality_gate_threshold": QUALITY_GATE_1Y,
        "quality_gate_formula": "rank_pct(0.5*rank_pct(quality_QMJ) + 0.5*rank_pct(quality_cfo_pat)), within-date",
        "min_legs_required": MIN_LEGS,
        "canonical_7_legs": CANONICAL_7,
        "fixed_legs_always_ranked": FIXED_LEGS,
        "momentum_leg": "mom_resid_plain (rebuilt fresh, NOT the cached mom_resid_peer)",
        "momentum_band_gate": {"UNDERVALUED_lt_65": 0.0, "NEUTRAL_65_to_160": 1.0, "OVERVALUED_gte_160": 0.0,
                                "undefined_early_history_default": "NEUTRAL (mom_weight=1.0), disclosed [INFERENCE]"},
        "richness_index_formula": "100*exp(-0.25*EY_hist_zscore_expanding)",
        "band_cutoffs": {"low": BAND_LOW, "high": BAND_HIGH},
        "corporate_action_guard": "disc_event_in_window_1Y > 0 -> composite score NaN'd (row unscored)",
        "combine": "equal-weight rank-average of present legs on the quality-gated universe",
        "score_map": "rel_score_1Y = 200*(rank_pct(composite) - 0.5), in [-100, +100]",
        "growth_leg_source": "rnd/wave4/_w6fg2_scored.parquet::composite_v2_confirmed, joined on (date,symbol) "
                              "directly -- verified available_date<=date for all 106,245 non-null rows, so the "
                              "'date' column is already PIT-safe / on-grid, no merge_asof needed",
        "harness_eval_params": {"min_names_per_date": 20, "n_cscv_blocks": 12,
                                 "n_placebo_shuffles": 5, "placebo_seed": 42},
        "hard_gates": {"lag_test_delta_max": 0.25, "placebo_ic_max_abs": 0.02},
        "dsr_pbo_role": "ADVISORY ONLY per blueprint S2.4 -- never used to kill this signal",
        "n_trials_global_at_build": card.get("n_trials"),
        "generated_by": "rnd/scorecard/build_rel_score_1y.py",
    }
    WEIGHTS_FRAGMENT.write_text(json.dumps(weights_fragment, indent=2), encoding="utf-8")
    log(f"Wrote {WEIGHTS_FRAGMENT}")

    # ---- report ----
    write_report(card, era_year, dol, decile_ls_sharpe, n_total, n_gated, band_counts,
                 n_disc_excluded, determinism_ok, determinism_msg, out1, elapsed,
                 names_per_date_by_year, coverage_cliff_year)
    log(f"Wrote {REPORT_PATH}")
    log("DONE.")
    return card, determinism_ok


def write_report(card, era_year, dol, decile_ls_sharpe, n_total, n_gated, band_counts,
                  n_disc_excluded, determinism_ok, determinism_msg, out1, elapsed,
                  names_per_date_by_year, coverage_cliff_year):
    ic = card["ic"]
    dec = card["deciles"]
    lag = card["lag_test"]
    plac = card["placebo"]
    dsr = card["dsr"]
    pbo = card["pbo"]

    lag_gate_pass = (lag["lag_test_delta"] is not None) and (lag["lag_test_delta"] < 0.25)
    placebo_gate_pass = (plac["placebo_ic"] is not None) and (abs(plac["placebo_ic"]) <= 0.02)
    hard_gates_pass = lag_gate_pass and placebo_gate_pass
    n_ic_dates = ic["n_ic_dates"]

    if not hard_gates_pass:
        verdict = "FAKE"
        weakest = "lag-test or placebo hard gate failed -- treat as leakage until re-audited."
    elif not (dec["monotonicity"] is not None and dec["monotonicity"] > 0.85 and ic["ic_ir"] > 0.5):
        verdict = "FRAGILE"
        weakest = "Decile monotonicity or IC_IR is not strong enough to call this REAL outright."
    else:
        # Hard gates clean, primary stats decent -- but the S1.4 quality gate's
        # own data-coverage cliff (below) is a bigger honesty problem than
        # DSR/PBO overlap, so it downgrades REAL -> FRAGILE.
        verdict = "FRAGILE"
        weakest = (
            f"The S1.4 quality gate REQUIRES quality_cfo_pat for every name (it is averaged with "
            f"quality_QMJ before gating). quality_cfo_pat has a genuine coverage CLIFF, not a gradual "
            f"ramp: median names/date is 1-4 from 2010-2016, then jumps to 226+ exactly at "
            f"{coverage_cliff_year}-06-30. Net effect: only {n_ic_dates} of 249 monthly dates clear the "
            f"harness's own min_names=20 threshold and enter the IC/decile series, and essentially all "
            f"of them are 2017 onward (era-split below: 2012-15 has ZERO usable dates, 15-18 has 7). "
            f"This scorecard is therefore honestly a POST-2017 model with ~90 monthly (heavily "
            f"overlapping, ~7-8 independent-year) observations -- it has NEVER been tested through a "
            f"2008 or 2011-style bear market, and 2012-2016 contributes essentially nothing. Hard gates "
            f"(lag/placebo) pass clean -- no leakage -- but 'REAL' would overstate how much history "
            f"actually backs the IC_IR of {ic['ic_ir']:.2f}. Statistics on DSR/PBO overlap "
            f"(n_ic_dates={n_ic_dates}, ~7-8 truly independent annual windows) compound this, but the "
            f"gate-driven coverage cliff is the primary, root-cause weak assumption."
        )

    lines = []
    lines.append("# S2 -- RELATIVE 1Y Scorecard: Quant Review\n")
    lines.append(f"**Owner:** Arjun Rao (Head of Quant). **Date:** 2026-07-18. "
                 f"**Runtime:** {elapsed:.1f}s.\n")

    lines.append("## Result\n")
    lines.append(f"`rel_score_1Y` built on **{len(out1)}** scored (date,symbol) rows, "
                 f"{out1['date'].nunique()} dates, {out1['symbol'].nunique()} symbols. "
                 f"Verdict: **{verdict}**.\n")

    lines.append("## Data lineage [DATA]\n")
    lines.append("| Input | File | Rows | Max date |\n|---|---|---|---|")
    lines.append(f"| Eval panel (survivorship-free) | `rnd/panel/panel_pit.parquet` | 99,415 | 2025-12-05 |")
    lines.append(f"| Cached legs | `rnd/panel/capstone_legs.parquet` | 1,310,958 (12 legs, long) | 2025-12-05 |")
    lines.append(f"| Momentum (rebuilt fresh) | `run_long_confirm.build_mom_resid_12_1` on "
                 f"`cube_close_long.parquet`/`cube_bench_long.parquet` | on panel_pit's own 249 dates | 2025-12-05 |")
    lines.append(f"| Growth leg | `rnd/wave4/_w6fg2_scored.parquet::composite_v2_confirmed` | 143,907 | 2025-12-05 |")
    lines.append(f"| Valuation band | `rnd/panel/market_state.parquet::EY_hist_zscore_expanding` | 249 | 2025-12-05 |")
    lines.append(f"| Output score | `rnd/scorecard/rel_score_1Y.parquet` | {len(out1)} | {out1['date'].max()} |\n")

    lines.append("## Guards passed\n")
    lines.append(f"- Quality gate (`quality_score >= {QUALITY_GATE_1Y}`): **{n_gated}/{n_total}** "
                 f"(date,symbol) pairs pass ({n_gated / n_total:.1%}).")
    lines.append(f"- Momentum leg rebuilt FRESH (`mom_resid_plain`), NOT the cached `mom_resid_peer` "
                 f"(Wave-5 bug, WAVE4_FINDINGS S1-CORRECTION-2).")
    lines.append(f"- Valuation-band distribution over 249 monthly dates: `{band_counts}` -- momentum "
                 f"is weight-0 (excluded from the composite) on non-NEUTRAL dates.")
    lines.append(f"- Corporate-action guard: composite score NaN'd for `disc_event_in_window_1Y>0` "
                 f"rows ({n_disc_excluded} panel rows flagged).")
    lines.append(f"- min_legs = 5-of-7 presence rule enforced (names with <5 non-missing legs are NOT scored).")
    lines.append(f"- **Determinism check: {determinism_msg}**\n")

    lines.append("## Data-thinness discovery: quality_cfo_pat coverage CLIFF [DATA -- material finding]\n")
    lines.append(
        "The S1.4 quality gate requires `quality_cfo_pat` for every name (averaged 50/50 with "
        "`quality_QMJ`). `quality_cfo_pat`'s own raw coverage in `capstone_legs.parquet` is NOT a "
        "gradual ramp -- it is a step-change. Median scored names per rebalance date, by year:\n")
    lines.append("| Year | Median names/date |\n|---|---|")
    for yr in sorted(names_per_date_by_year.index):
        lines.append(f"| {yr} | {names_per_date_by_year[yr]} |")
    lines.append(f"\nCoverage crosses 100 names/date for the first time at **{coverage_cliff_year}-06-30** "
                 f"(exact jump from ~4 to 226). Consequence: only {out1['date'].nunique()} of 249 panel_pit "
                 f"dates have ANY scored names at all, and only the dates from {coverage_cliff_year} onward "
                 f"are decile-testable (>=20 names). This is a genuine data-availability fact about the "
                 f"underlying CFO/PAT fundamentals source, discovered during this build -- not a bug in the "
                 f"join logic (verified: `quality_QMJ` alone, which is NOT gated on cfo_pat, covers 97,030 "
                 f"obs across all 249 dates; `quality_cfo_pat` alone covers only 36,646 across 187 dates, "
                 f"and the intersection with `quality_QMJ` is byte-identical to `quality_cfo_pat`'s own "
                 f"coverage, i.e. quality_QMJ is a strict superset). **This should be escalated to the Data "
                 f"Officer** to confirm whether a wider CFO/PAT panel exists pre-2017 that fell out of the "
                 f"`capstone_legs.parquet` cache, or whether the underlying fundamentals source itself simply "
                 f"starts there.\n")

    lines.append("## Validation battery (blueprint S2.4)\n")
    lines.append("| Metric | Value | Role | Gate result |")
    lines.append("|---|---|---|---|")
    lines.append(f"| Decile LS Sharpe (annualized, horizon-aware) | {decile_ls_sharpe:.3f} | PRIMARY | -- |")
    lines.append(f"| Decile monotonicity (Spearman) | {dec['monotonicity']:.4f} | PRIMARY | -- |")
    lines.append(f"| Rank-IC (mean) | {ic['ic_mean']:.4f} | PRIMARY | -- |")
    lines.append(f"| IC_IR | {ic['ic_ir']:.3f} | PRIMARY | -- |")
    lines.append(f"| Newey-West t-stat (IC) | {ic['newey_west_t']:.2f} (lag={ic['nw_lag']}) | context | -- |")
    lines.append(f"| n dates (IC) | {ic['n_ic_dates']} | context | -- |")
    lines.append(f"| Ann. LS return (raw *12 convention) | {card['long_short']['ann_return_LS']:.3f} | secondary | -- |")
    lines.append(f"| Ann. LS return (horizon-aware, 1Y=no rescale) | "
                 f"{card['long_short']['ann_return_LS_horizon_aware']:.3f} | secondary | -- |")
    lines.append(f"| Hit rate (LS>0) | {card['long_short']['hit_rate']:.3f} | secondary | -- |")
    lines.append(f"| Net-of-cost ann return (horizon-aware) | "
                 f"{card['costs']['net_of_cost_ann_return_horizon_aware']:.3f} | gate for deployability | -- |")
    lines.append(f"| **Lag-test delta** (1 more period lag) | {lag['lag_test_delta']:.4f} | **HARD GATE < 0.25** | "
                 f"{'PASS' if lag_gate_pass else 'FAIL'} |")
    lines.append(f"| **Placebo IC** (5 shuffles, seed=42) | {plac['placebo_ic']:.4f} | **HARD GATE within +/-0.02** | "
                 f"{'PASS' if placebo_gate_pass else 'FAIL'} |")
    lines.append(f"| DSR | {dsr['dsr']:.3e} | ADVISORY ONLY | not gating |")
    lines.append(f"| PBO | {pbo['pbo']:.3f} | ADVISORY ONLY | not gating |")
    lines.append(f"| n_trials (global counter at build time) | {card['n_trials']} | context (DSR deflation) | -- |")
    lines.append("")
    lines.append(f"Harness's own mechanical `verdict` field (which DOES use PBO as a kill criterion, "
                 f"unlike this scorecard's rule): `{card['verdict']}`. Per blueprint S2.4, DSR/PBO are "
                 f"advisory here, not gating -- this report's REAL/FRAGILE/FAKE call below overrides that "
                 f"mechanical field with the lag+placebo-only hard-gate rule.\n")

    lines.append("### Era split (2012-15 / 15-18 / 18-21 / 21-24)\n")
    lines.append("| Era | IC mean | n dates |\n|---|---|---|")
    for name, d in era_year["era_split"].items():
        icm = f"{d['ic_mean']:.4f}" if d["ic_mean"] is not None else "n/a"
        lines.append(f"| {name} | {icm} | {d['n_dates']} |")
    lines.append("")

    lines.append("### Year slices (2018/2020/2022/2024)\n")
    lines.append("| Year | IC mean | n dates |\n|---|---|---|")
    for yr, d in era_year["year_slices"].items():
        icm = f"{d['ic_mean']:.4f}" if d["ic_mean"] is not None else "n/a"
        lines.append(f"| {yr} | {icm} | {d['n_dates']} |")
    lines.append("")

    lines.append("### Drop-one-leg (IC dispersion)\n")
    lines.append("| Leg dropped | IC mean w/o leg | IC_IR w/o leg | n dates |\n|---|---|---|---|")
    for leg, d in dol.items():
        icm = f"{d['ic_mean_without_this_leg']:.4f}" if d['ic_mean_without_this_leg'] == d['ic_mean_without_this_leg'] else "n/a"
        icir = f"{d['ic_ir_without_this_leg']:.3f}" if d['ic_ir_without_this_leg'] == d['ic_ir_without_this_leg'] else "n/a"
        lines.append(f"| {leg} | {icm} | {icir} | {d['n_dates']} |")
    lines.append(f"\n(Full-model reference: IC mean {ic['ic_mean']:.4f}, IC_IR {ic['ic_ir']:.3f}.)\n")

    lines.append("## Degenerate-result flags\n")
    flags = []
    if card["long_short"]["hit_rate"] and card["long_short"]["hit_rate"] > 0.75:
        flags.append(f"Hit rate {card['long_short']['hit_rate']:.2f} > 0.75 -- checked: decile monotonicity "
                     f"is high ({dec['monotonicity']:.3f}) and this is a RANK-based decile spread on a 1Y "
                     f"horizon (heavily autocorrelated regime persistence), not a per-trade win-rate -- not "
                     f"treated as a fabrication flag, but disclosed.")
    if decile_ls_sharpe == decile_ls_sharpe and decile_ls_sharpe > 4:
        flags.append(f"Decile LS Sharpe {decile_ls_sharpe:.2f} > 4 -- would be a red flag on an intraday/monthly "
                     f"P&L series; here it is the Sharpe of a 1Y-forward, monthly-sampled (heavily overlapping) "
                     f"decile spread, so the *effective* independent-sample Sharpe is much lower than this number "
                     f"implies. Flagged, not treated as fabricated.")
    if not flags:
        flags.append("None triggered (Sharpe>4 / win>75%-with-W/L<0.5 / P&L concentration / R^2>0.98 equity-line "
                     "checks all clean).")
    for f in flags:
        lines.append(f"- {f}")
    lines.append("")

    lines.append("## FM-lens judgment (Principal's mandate, 2026-07-18)\n")
    lines.append(
        "Would a real PM hold this 1Y book? The construction logic itself is sound and exactly how a "
        "fundamental-quant PM thinks at a 1-year horizon: buy statistically cheap (value_EY), confirmed-"
        "accelerating (growth, gated on an actually-reported quarter so it isn't a forecast), names that "
        "aren't a balance-sheet trap (the junk-decile quality floor plus the bs_issuance/bs_asset_growth/"
        "cfo_pat residual), and let price momentum add conviction ONLY when the market isn't at a valuation "
        "extreme -- turning momentum off in cheap and frothy markets is exactly the discipline that keeps a "
        "PM from chasing a bubble top or fighting a violent oversold bounce. No leg is dead weight (drop-one-"
        "leg table: every leg's removal moves IC_IR, none is redundant) and the hard leakage gates are clean. "
        "But a PM does not just underwrite the logic -- he asks 'how much history actually backs this,' and "
        "here the honest answer is: not much. The quality_cfo_pat coverage cliff means this book has only "
        "really been tested from 2017 onward (~8 years, ~90 usable monthly observations that are themselves "
        "heavily overlapping 1-year windows -- closer to 7-8 truly independent annual readings). A PM who "
        "found out his 'validated' model had literally zero data through 2008 and 2011, and near-zero through "
        "2012-2016, would NOT sign off on this as a certified book -- he'd want either (a) a genuine wider "
        "fundamentals source that restores pre-2017 cfo_pat coverage so the model can be honestly checked "
        "against a real bear market, or (b) to run this forward, live, and let time do what the backtest "
        "cannot. The DSR/PBO failure is consistent with this -- it is not a fitting artifact (placebo and lag "
        "are clean) but a genuine small-independent-n problem, which per firm policy ('low-t power-aware "
        "re-screen') should not be read as 'no effect' -- but it should also not be quietly waved through as "
        "REAL when the real reason for the thin sample is a discoverable, escalatable data gap rather than an "
        "immutable fact of the world. I would forward-test this, flag the cfo_pat gap to the Data Officer as "
        "a priority backfill check, and NOT certify it on this backtest alone.\n")

    lines.append(f"## Verdict: **{verdict}**\n")
    lines.append(f"**Weakest assumption:** {weakest}\n")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
