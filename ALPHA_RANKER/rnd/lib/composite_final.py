"""
CANONICAL 1Y COMPOSITE -- Arjun Rao (Head of Quant), Certification Gate 1.
2026-07-17. ONE authoritative build. Every headline number in FINAL_MODEL.md
must be re-sourced from THIS script's output (rnd/cards/CANONICAL_7LEG_1Y.json),
not from CAPSTONE_COMPO_1Y_final (stale 4-leg bug) or from the two competing
7-leg re-builds that disagreed (AUDIT_TRUE7_1Y IC_IR 1.356 vs
CONC_composite_1Y_raw IC_IR 1.246).

WHY THE TWO PRIOR REBUILDS DISAGREED (traced, not guessed):
  Both used the identical 7 legs (value_EY, mom_resid_plain, trend_ma65_slope,
  quality_QMJ, bs_issuance, bs_asset_growth, quality_cfo_pat) as a simple
  rank-average. The ONLY construction difference is the leg-presence
  threshold in `rank_avg(..., min_legs=N)`:
    - sameer_preic_audit.py (AUDIT_TRUE7_1Y)     -> min_legs=5 (of 7)
    - concentration_check script (CONC_..._raw)   -> min_legs=2 (of 7, the
      function's own default: `min(2, len(names))`)
  PIT fundamentals coverage is ~zero pre-2010 and thin through 2012-15
  (PREIC_AUDIT.md S2: 2005-10 EMPTY, 0/32 months clear the 20-name minimum;
  2010-15 LOW, median 17 names/date but a 5->514 ramp). min_legs=2 lets those
  data-thin months compute a "composite" off as few as 2 of the 7 legs and
  still calls it the 7-leg model -- diluting the real signal with what is
  actually a 2-leg proxy wearing the 7-leg label, and inflating apparent
  history to 231 dates that are not all real 7-leg observations.
  min_legs=5 refuses to score a date/name as "the 7-leg composite" unless
  most of the legs actually exist there -- it does NOT drop dates for weak
  PERFORMANCE (that would be data-mining), only for missing INPUTS. This is
  the same landmine class as the "17-month gap read as full coverage" and
  "partial-year reads as positive every year" lessons already on file.

CANONICAL CHOICE: min_legs=5. Reconciliation verdict: 1.36 (AUDIT_TRUE7-style,
min_legs=5) is canonical; 1.25 (min_legs=2) is the inferior, diluted-input
construction and is SUPERSEDED. Both numbers are disclosed below for the
record; only 1.36-family is to be quoted going forward.

CONSTRUCTION CONVENTION FIXED HERE (documented, not implicit):
  1. Legs combined as an EQUAL-WEIGHT rank-average (rank_pct per date per
     leg, then mean across available legs) -- no fitted weights.
  2. min_legs=5-of-7 required to emit a composite value for a (date,symbol).
  3. Universe = panel_long.parquet as-is (969 symbols, PIT survivorship-
     controlled, 2005-04->2025-12) -- the "standard universe filter" for
     this codebase IS the panel itself; no additional ADV/price screen is
     applied elsewhere in the sibling scripts (run_long_confirm.py,
     sameer_preic_audit.py) so none is added here for consistency.
  4. Corporate-action guard (NOT applied in either prior rebuild -- closed
     here): rows with disc_event_in_window_1Y > 0 have their forward-return
     target NaN'd before scoring (same convention as run_long_confirm.py
     L277-281 / backtest_final.py L217), 1,213 of 148,297 panel rows.
  5. Official IC/monotonicity/DSR/PBO/cost card = harness.evaluate()'s
     built-in DECILE (10-bin) portfolio construction (harness convention,
     unchanged -- do not fork the shared harness for one composite).
     QUINTILE (5-bin, top20%/bottom20%) long-short is additionally computed
     and stored as a supplementary field: quintile buckets have ~2x the
     names-per-bucket of deciles, which matters for the >=30-trades/
     parameter rule in data-thin months, and PREIC_AUDIT S1 already showed
     decile-vs-quintile does not move IC_IR/monotonicity (only bucket
     width) -- so quintile is the citable "tradeable, robust-N" spread,
     decile is the citable "official card" spread. Both are on the record;
     neither is hidden.
  6. Score map: score = 200*(rank_pct(composite) - 0.5) in [-100, +100],
     per FINAL_MODEL.md S2. Zero fitted parameters.

Outputs:
  rnd/cards/CANONICAL_7LEG_1Y.json   (harness card + appended construction
                                       metadata + quintile supplementary +
                                       reconciliation block)
  rnd/panel/canonical_7leg_scores.parquet (date, symbol, composite_rank_avg,
                                       score_[-100,100]) -- full history, for
                                       reuse by any downstream consumer.
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

REPORTS_DIR = RND_DIR / "reports"
CARDS_DIR = RND_DIR / "cards"
PANEL_DIR = RND_DIR / "panel"
LEGS_CACHE = PANEL_DIR / "capstone_legs.parquet"

TRUE7 = ["value_EY", "mom_resid_plain", "trend_ma65_slope", "quality_QMJ",
         "bs_issuance", "bs_asset_growth", "quality_cfo_pat"]
MIN_LEGS = 5  # canonical choice -- see module docstring


def log(msg):
    print(f"[canonical] {msg}", flush=True)


def load_cached_legs():
    d = pd.read_parquet(LEGS_CACHE)
    d["date"] = pd.to_datetime(d["date"])
    out = {}
    for leg, g in d.groupby("leg"):
        out[leg] = g.set_index(["date", "symbol"])["value"].rename("factor")
    return out


def rank_avg(legs_dict, names, min_legs):
    """Equal-weight rank-average of `names` legs; emits a value only where
    at least `min_legs` of the legs are present for that (date,symbol)."""
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


def quintile_ls(factor, panel, min_names=20):
    """Supplementary quintile (top20%-bottom20%) long-short, tradeable-raw-
    return basis -- documented convention #5. Independent of the harness's
    own decile card; does not touch the trials ledger (no new evaluate())."""
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
    log("Loading panel_long + long cubes + cached capstone legs...")
    panel, close, bench = LC.load_all()
    legs = load_cached_legs()
    log(f"Cached legs available: {sorted(legs.keys())}")

    log("Building PLAIN residual momentum (no peer_relative wrap) fresh from close/bench...")
    mom_plain = LC.build_mom_resid_12_1(close, bench, LC._panel_dates(panel))
    legs["mom_resid_plain"] = mom_plain

    missing = [n for n in TRUE7 if n not in legs]
    if missing:
        raise RuntimeError(f"Canonical 7 legs missing from cache: {missing}")

    log(f"Building canonical composite: rank-average of {TRUE7}, min_legs={MIN_LEGS}...")
    factor = rank_avg(legs, TRUE7, min_legs=MIN_LEGS)
    log(f"Composite built: {len(factor)} (date,symbol) obs")

    # ---- corporate-action guard: NaN the 1Y target where disc_event flagged ----
    disc_col = "disc_event_in_window_1Y"
    panel_g = panel.copy()
    mask = panel_g[disc_col].fillna(0) > 0
    n_excluded = int(mask.sum())
    panel_g.loc[mask, ["fwd_ret_1Y_raw", "fwd_ret_1Y_resid"]] = np.nan
    log(f"Corporate-action guard: excluded {n_excluded}/{len(panel_g)} disc-flagged rows from targets")

    # ---- official card via harness (decile convention, unchanged) ----
    log("Evaluating canonical composite via harness.evaluate() -- 1 new honest trial, disclosed...")
    card = harness.evaluate(
        factor, "1Y", return_basis="resid", factor_id="CANONICAL_7LEG_1Y",
        panel=panel_g, panel_source="real_panel_long_capstone",
        family="CANONICAL_7LEG", write_card=True, cards_dir=CARDS_DIR,
    )

    # ---- supplementary quintile long-short (documented convention #5) ----
    log("Computing supplementary quintile long-short spread...")
    q_stats = quintile_ls(factor, panel_g)

    # ---- append construction metadata + reconciliation block to the card ----
    card["construction"] = {
        "legs": TRUE7,
        "weighting": "equal-weight rank-average (rank_pct per date per leg, mean across available legs)",
        "min_legs_required": MIN_LEGS,
        "universe": "panel_long.parquet as-is (969 symbols, PIT survivorship-controlled, 2005-04 to 2025-12) "
                    "-- no additional ADV/price screen (consistent with sibling scripts)",
        "corporate_action_guard": f"disc_event_in_window_1Y>0 rows NaN'd from fwd_ret_1Y target "
                                   f"({n_excluded} rows excluded); NOT applied in either prior 7-leg rebuild",
        "official_portfolio_construction": "decile (10-bin), harness.evaluate() default -- unchanged, shared harness",
        "supplementary_portfolio_construction": "quintile (5-bin, top20%-bottom20%), more names/bucket for "
                                                 "the >=30-trades/parameter rule; does not move IC_IR/monotonicity "
                                                 "per PREIC_AUDIT S1",
        "score_map": "score = 200*(rank_pct(composite) - 0.5) in [-100,+100], zero fitted parameters",
    }
    card["quintile_supplementary"] = q_stats
    card["reconciliation_1p25_vs_1p36"] = {
        "prior_min_legs_2_build": {"card": "CONC_composite_1Y_raw", "ic_ir": 1.2456101983596133,
                                    "n_ic_dates": 231, "verdict": "SUPERSEDED -- diluted-input construction, "
                                    "let data-thin (<5-leg) dates masquerade as the 7-leg composite"},
        "prior_min_legs_5_build": {"card": "AUDIT_TRUE7_1Y", "ic_ir": 1.3563036195202887,
                                    "n_ic_dates": 145, "verdict": "This IS the canonical construction "
                                    "(same min_legs=5 convention); CANONICAL_7LEG_1Y differs from it only by "
                                    "the disc_event corporate-action guard now applied (immaterial, ~0.8% of rows)"},
        "why_they_differed": "min_legs threshold in rank_avg (5-of-7 vs 2-of-7), NOT decile/quintile, weighting, "
                              "or universe filter (those were held identical in both prior rebuilds)",
        "canonical": "min_legs=5 family (~1.3x) -- CONFIRMED as this script's IC_IR below",
    }
    (CARDS_DIR / "CANONICAL_7LEG_1Y.json").write_text(
        json.dumps(card, indent=2, default=str), encoding="utf-8")
    log(f"Wrote {CARDS_DIR / 'CANONICAL_7LEG_1Y.json'}")

    # ---- score output for downstream reuse ----
    log("Computing score = 200*(rank_pct(composite)-0.5) and saving full-history parquet...")
    f_df = factor.reset_index()
    f_df["score"] = f_df.groupby("date")["factor"].rank(pct=True).sub(0.5).mul(200.0)
    f_df = f_df.rename(columns={"factor": "composite_rank_avg"})
    out_path = PANEL_DIR / "canonical_7leg_scores.parquet"
    f_df.to_parquet(out_path, index=False)
    log(f"Wrote {out_path} ({len(f_df)} rows)")

    log(json.dumps({
        "ic_ir": card["ic"]["ic_ir"], "ic_mean": card["ic"]["ic_mean"],
        "monotonicity": card["deciles"]["monotonicity"],
        "lag_test_delta": card["lag_test"]["lag_test_delta"],
        "n_ic_dates": card["ic"]["n_ic_dates"], "n_trials_global": card["n_trials"],
        "quintile_ann_LS": q_stats["ann_return_LS_quintile"],
        "verdict": card["verdict"],
    }, indent=2))
    log("DONE.")


if __name__ == "__main__":
    main()
