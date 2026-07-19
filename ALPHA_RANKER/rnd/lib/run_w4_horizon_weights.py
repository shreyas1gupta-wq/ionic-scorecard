"""
WAVE-4 HORIZON-WEIGHTS AUDIT -- Arjun Rao (Head of Quant), 2026-07-17.

Principal's hypothesis: the 7-leg composite is currently an EQUAL-WEIGHT
rank-average used identically at 1M/1Y/5Y (per FINAL_MODEL.md S2), but
different factors should matter differently by horizon (momentum-heavy 1M,
balanced 1Y, value/quality-heavy 5Y). This script tests that on-disk, honestly:

1. CLOSES A REAL GAP: no CAPSTONE_*_1M card exists for value_EY / quality_QMJ /
   quality_cfo_pat / bs_issuance / bs_asset_growth -- only momentum has a
   long-history (21yr, panel_long) 1M card (MOMQ_plain_resid_1M). This script
   evaluates ALL 7 legs at 1M on the SAME 21-yr panel_long.parquet the 1Y/5Y
   CAPSTONE cards use (fwd_ret_1M_raw/resid columns exist there, 146,511/148,297
   populated) -- so the "1M has no 21yr cube" caveat is re-tested here for
   fundamentals specifically, not just repeated.
2. Builds THREE composites per horizon from coarse, NOT-FITTED weight tiers
   (economic priors only -- no grid search, no data-driven weight choice):
     - EQUAL:   all present legs weighted 1/n_present (today's production method)
     - MOM-HEAVY (for 1M):  momentum+trend get 2x weight, others 1x
     - VALUE/QUALITY-HEAVY (for 5Y): value+quality+asset-growth get 2x, others 1x
     - 1Y stays EQUAL (already validated as "balanced" -- no prior claims 1Y
       should be tilted, so equal-weight IS the prior-consistent choice there).
   Weights are FIXED integer tiers (1x/2x), chosen before looking at results,
   not tuned.
3. Compares EQUAL vs prior-tilted on IC_IR / decile monotonicity / quintile
   long-short spread -- same harness.evaluate() as every other card in this repo.

Honesty notes:
 - Same min_legs=5-of-7 convention as CANONICAL_7LEG_1Y (composite_final.py).
 - Same corporate-action guard (disc_event_in_window_<H> NaN's the target).
 - mom_resid_plain is rebuilt fresh from cube_close_long/cube_bench_long
   exactly as composite_final.py does (not read from the peer-relative
   capstone_legs cache, which CONSOLIDATION.md already flagged as a 5yr-bull
   artifact at 1Y -- same correction applies at every horizon here).
 - This is one MORE set of trials on an already-KILLed (DSR/PBO) composite
   family; it does not un-KILL the composite. It only tells us whether the
   WEIGHTING SCHEME direction is sound, for the day DSR/PBO clears on a fresh
   forward test (per FINAL_MODEL.md S5-RISKOFFICE).
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

CARDS_DIR = RND_DIR / "cards"
PANEL_DIR = RND_DIR / "panel"
WAVE4_DIR = RND_DIR / "wave4"
LEGS_CACHE = PANEL_DIR / "capstone_legs.parquet"

TRUE7 = ["value_EY", "mom_resid_plain", "trend_ma65_slope", "quality_QMJ",
         "bs_issuance", "bs_asset_growth", "quality_cfo_pat"]
MIN_LEGS = 5

TILT_TIERS = {
    "1M": {"mom_resid_plain": 2.0, "trend_ma65_slope": 2.0},   # momentum-heavy prior
    "1Y": {},                                                    # balanced == equal-weight prior
    "5Y": {"value_EY": 2.0, "quality_QMJ": 2.0, "bs_asset_growth": 2.0},  # value/quality-heavy prior
}


def log(msg):
    print(f"[w4hw] {msg}", flush=True)


def load_cached_legs():
    d = pd.read_parquet(LEGS_CACHE)
    d["date"] = pd.to_datetime(d["date"])
    out = {}
    for leg, g in d.groupby("leg"):
        out[leg] = g.set_index(["date", "symbol"])["value"].rename("factor")
    return out


def weighted_rank_avg(legs_dict, names, weights, min_legs):
    """Weighted rank-average: rank_pct per leg per date, then a WEIGHTED mean
    across available legs (weights renormalized to the present legs so a
    missing leg doesn't silently zero out its neighbors' contribution)."""
    frames = []
    for n in names:
        r = legs_dict[n].rename("factor").reset_index()
        r.columns = ["date", "symbol", n]
        r[n] = r.groupby("date")[n].rank(pct=True)
        frames.append(r.set_index(["date", "symbol"])[n])
    wide = pd.concat(frames, axis=1)
    w = pd.Series({n: weights.get(n, 1.0) for n in names})
    present = wide.notna()
    n_present = present.sum(axis=1)
    wsum = present.mul(w, axis=1).sum(axis=1)
    weighted_vals = wide.fillna(0.0).mul(w, axis=1).sum(axis=1)
    combo = weighted_vals.div(wsum)
    combo = combo.where(n_present >= min_legs)
    return combo.dropna().rename("factor")


def quintile_ls(factor, panel, horizon, min_names=20):
    lbl = harness._label_cols(horizon)
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

    q_series = merged.groupby("date").apply(_q, include_groups=False).dropna()
    return {"ann_return_LS_quintile": float(q_series.mean() * (12 if horizon != "5Y" else 12 / 5)),
            "n_dates_quintile": int(len(q_series))}


def guard_targets(panel, horizon):
    disc_col = f"disc_event_in_window_{horizon}"
    lbl = harness._label_cols(horizon)
    p = panel.copy()
    mask = p[disc_col].fillna(0) > 0
    p.loc[mask, [lbl["raw"], lbl["resid"]]] = np.nan
    return p, int(mask.sum())


def eval_single_legs(legs, panel):
    """Per-leg, per-horizon IC on the SAME 21yr panel_long -- closes the
    '1M fundamentals untested on long history' gap."""
    rows = []
    for horizon in ("1M", "1Y", "5Y"):
        panel_g, n_ex = guard_targets(panel, horizon)
        for leg_name in TRUE7:
            factor = legs[leg_name]
            fid = f"W4HW_leg_{leg_name}_{horizon}"
            card = harness.evaluate(
                factor, horizon, return_basis="resid", factor_id=fid,
                panel=panel_g, panel_source="real_panel_long_w4horizon",
                family="W4HW_leg", write_card=True, cards_dir=CARDS_DIR,
            )
            ic = card["ic"]; dec = card["deciles"]; lag = card["lag_test"]
            rows.append({
                "leg": leg_name, "horizon": horizon,
                "ic_mean": ic["ic_mean"], "ic_ir": ic["ic_ir"], "nw_t": ic["newey_west_t"],
                "n_ic_dates": ic["n_ic_dates"], "monotonicity": dec["monotonicity"],
                "lag_test_delta": lag["lag_test_delta"], "pbo": card["pbo"]["pbo"],
                "placebo_ic": card["placebo"]["placebo_ic"], "verdict": card["verdict"],
            })
            log(f"{fid}: ic_ir={ic['ic_ir']:.3f} mono={dec['monotonicity']:.3f} "
                f"lag_delta={lag['lag_test_delta']:.3f} n_ic_dates={ic['n_ic_dates']}")
    return pd.DataFrame(rows)


def eval_composites(legs, panel):
    """EQUAL vs prior-tilted composite, per horizon."""
    rows = []
    for horizon in ("1M", "1Y", "5Y"):
        panel_g, n_ex = guard_targets(panel, horizon)
        for scheme_name, weights in [("EQUAL", {}), ("TILT", TILT_TIERS[horizon])]:
            factor = weighted_rank_avg(legs, TRUE7, weights, MIN_LEGS)
            fid = f"W4HW_{scheme_name}_{horizon}"
            card = harness.evaluate(
                factor, horizon, return_basis="resid", factor_id=fid,
                panel=panel_g, panel_source="real_panel_long_w4horizon",
                family="W4HW_composite", write_card=True, cards_dir=CARDS_DIR,
            )
            q = quintile_ls(factor, panel_g, horizon)
            ic = card["ic"]; dec = card["deciles"]; lag = card["lag_test"]
            rows.append({
                "horizon": horizon, "scheme": scheme_name, "weights": json.dumps(weights),
                "ic_mean": ic["ic_mean"], "ic_ir": ic["ic_ir"], "nw_t": ic["newey_west_t"],
                "n_ic_dates": ic["n_ic_dates"], "monotonicity": dec["monotonicity"],
                "lag_test_delta": lag["lag_test_delta"], "pbo": card["pbo"]["pbo"],
                "ann_LS_decile": card["long_short"]["ann_return_LS"],
                "ann_LS_quintile": q["ann_return_LS_quintile"],
                "verdict": card["verdict"],
            })
            log(f"{fid}: ic_ir={ic['ic_ir']:.3f} mono={dec['monotonicity']:.3f} "
                f"quintile_LS={q['ann_return_LS_quintile']:.3f} n_ic_dates={ic['n_ic_dates']}")
    return pd.DataFrame(rows)


def main():
    log("Loading panel_long + long cubes + cached capstone legs...")
    panel, close, bench = LC.load_all()
    legs = load_cached_legs()

    log("Building PLAIN residual momentum fresh (same correction as composite_final.py)...")
    mom_plain = LC.build_mom_resid_12_1(close, bench, LC._panel_dates(panel))
    legs["mom_resid_plain"] = mom_plain

    missing = [n for n in TRUE7 if n not in legs]
    if missing:
        raise RuntimeError(f"Legs missing from cache: {missing}")

    log("=== PART 1: per-leg IC by horizon (1M/1Y/5Y), same 21yr panel ===")
    leg_df = eval_single_legs(legs, panel)
    leg_out = WAVE4_DIR / "w4hw_leg_by_horizon.csv"
    leg_df.to_csv(leg_out, index=False)
    log(f"Wrote {leg_out} ({len(leg_df)} rows)")

    log("=== PART 2: EQUAL vs prior-tilted composite, per horizon ===")
    comp_df = eval_composites(legs, panel)
    comp_out = WAVE4_DIR / "w4hw_composite_equal_vs_tilt.csv"
    comp_df.to_csv(comp_out, index=False)
    log(f"Wrote {comp_out} ({len(comp_df)} rows)")

    log("DONE.")


if __name__ == "__main__":
    main()
