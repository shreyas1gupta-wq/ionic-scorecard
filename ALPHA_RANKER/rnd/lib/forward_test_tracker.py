"""
FORWARD-TEST TRACKER -- ALPHA_RANKER canonical 7-leg composite.
Arjun Rao (Head of Quant), 2026-07-17. Final-burst Task 1.

WHY THIS EXISTS: FINAL_MODEL.md S5-RISKOFFICE is explicit that in-sample
compute cannot certify this composite -- after 456 logged trials, DSR is
~0 and CSCV-PBO is ~0.92 (both universes, biased and survivorship-PIT-free).
More re-runs, more sensitivity batteries, more perturbation tests CANNOT fix
a multiple-testing problem -- deflation only gets worse with more trials, not
better. The ONE gate that escapes multiple-testing is genuine calendar-time
OOS: freeze the composite, bank predictions, wait, grade ONCE. That is what
this script does. It does not re-open, re-tune, or re-select anything.

THIS SCRIPT NEVER SELF-GRADES. It (1) content-hashes composite_final.py so
the frozen spec is tamper-evident, (2) records the exact construction, and
(3) scores the CURRENT cross-section as of the latest available date, saving
predictions for a SEPARATE, later, one-time grading pass. Evaluating early
or repeatedly against these banked scores would recreate the exact
multiple-testing problem this tracker exists to escape -- see
rnd/forward_test/FROZEN_SPEC.md for the pre-registered protocol.

No new leg/data construction happens here: legs, rank_avg(), min_legs, and
the score map are IMPORTED from composite_final.py (the certified single
source of truth per its own module docstring) -- this script cannot
silently drift from the canonical build.
"""
from __future__ import annotations
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))

import composite_final as CF  # noqa: E402  -- single source of truth for TRUE7/MIN_LEGS/rank_avg
import run_long_confirm as LC  # noqa: E402

FORWARD_DIR = RND_DIR / "forward_test"
CARDS_DIR = RND_DIR / "cards"
UNIVERSE_CSV = RND_DIR.parent / "data" / "universe" / "nifty_total_market_750.csv"
COMPOSITE_FINAL_PY = RND_DIR / "lib" / "composite_final.py"


def log(msg):
    print(f"[forward_test_tracker] {msg}", flush=True)


def content_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_freeze_manifest() -> dict:
    """Content-hash composite_final.py (NOT a git commit -- do not commit
    anything from this task) + record the exact construction so the spec
    is tamper-evident: any future edit to composite_final.py changes this
    hash, proving the frozen spec was (or was not) altered."""
    h = content_hash(COMPOSITE_FINAL_PY)
    manifest = {
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_by": "Arjun Rao (Head of Quant), E-004",
        "source_file": str(COMPOSITE_FINAL_PY),
        "source_sha256": h,
        "note": "This is a content hash of the .py file bytes, NOT a git commit hash -- "
                "no commit was made for this freeze (per task instruction). Any future edit "
                "to composite_final.py, even whitespace, changes this hash and is detectable "
                "by re-running content_hash() and diffing against this manifest.",
        "legs": list(CF.TRUE7),
        "min_legs_required": CF.MIN_LEGS,
        "construction": {
            "weighting": "equal-weight rank-average (rank_pct per date per leg, mean across "
                         "available legs) -- zero fitted parameters",
            "min_legs_rule": f"min_legs={CF.MIN_LEGS}-of-{len(CF.TRUE7)} required to emit a "
                             f"composite value for a (date,symbol) -- refuses to score a "
                             f"data-thin date/name as 'the 7-leg composite'",
            "decile_construction": "harness.evaluate() built-in DECILE (10-bin) portfolio "
                                   "construction (official card convention, unchanged)",
            "corporate_action_guard": "disc_event_in_window_1Y>0 rows NaN'd from the forward-return "
                                      "TARGET during historical evaluation -- not applicable to "
                                      "live scoring (no forward target exists yet for today's cross-"
                                      "section); recorded for completeness of the frozen construction",
            "universe": "panel_long.parquet as-is (PIT survivorship-controlled fundamentals+price "
                        "panel), cross-referenced against nifty_total_market_750.csv for the "
                        "current-universe snapshot below",
        },
        "score_map": "score = 200*(rank_pct(composite) - 0.5) in [-100, +100], per FINAL_MODEL.md S2",
        "canonical_card_at_freeze_time": "rnd/cards/CANONICAL_7LEG_1Y.json (IC_IR 1.345, biased "
                                         "universe) / rnd/cards/CANONICAL_7LEG_PIT_1Y.json (IC_IR "
                                         "1.760, survivorship-free) -- both PARK/KILL per DSR/PBO, "
                                         "see FINAL_MODEL.md S5-RISKOFFICE",
    }
    return manifest


def score_current_universe():
    """Reproduce composite_final.py's exact leg-build + rank_avg(min_legs=5)
    pipeline, then take ONLY the latest available date's cross-section --
    this is 'today's predictions' in the PIT sense: the latest date at which
    the underlying fundamentals+price panel actually has data, not the
    calendar date this script happens to run on. Disclosed explicitly below,
    not silently backfilled."""
    log("Loading panel_long + long cubes + cached capstone legs (identical to composite_final.py)...")
    panel, close, bench = LC.load_all()
    legs = CF.load_cached_legs()

    log("Building PLAIN residual momentum fresh (identical call to composite_final.py)...")
    legs["mom_resid_plain"] = LC.build_mom_resid_12_1(close, bench, LC._panel_dates(panel))

    missing = [n for n in CF.TRUE7 if n not in legs]
    if missing:
        raise RuntimeError(f"Canonical 7 legs missing from cache: {missing}")

    latest_date = max(legs[n].index.get_level_values("date").max() for n in CF.TRUE7)
    log(f"Latest available date across all 7 legs: {latest_date.date()}")

    # ---- per-leg rank_pct at the latest date (subscores) ----
    per_leg_frames = []
    for n in CF.TRUE7:
        s = legs[n].rename("factor").reset_index()
        s.columns = ["date", "symbol", n]
        s[n + "_rankpct"] = s.groupby("date")[n].rank(pct=True)
        latest = s[s["date"] == latest_date][["symbol", n, n + "_rankpct"]].set_index("symbol")
        latest[f"subscore_{n}"] = 200.0 * (latest[n + "_rankpct"] - 0.5)
        per_leg_frames.append(latest[[f"subscore_{n}"]])
    subscores = pd.concat(per_leg_frames, axis=1)

    # ---- composite via the imported, canonical rank_avg() ----
    log(f"Building canonical composite via composite_final.rank_avg(min_legs={CF.MIN_LEGS})...")
    factor = CF.rank_avg(legs, CF.TRUE7, min_legs=CF.MIN_LEGS)
    factor_latest = factor.reset_index()
    factor_latest = factor_latest[factor_latest["date"] == latest_date].set_index("symbol")

    n_legs_present = subscores.notna().sum(axis=1)

    out = subscores.join(factor_latest[["factor"]], how="left")
    out = out.rename(columns={"factor": "composite_rank_avg"})
    out["n_legs_present"] = n_legs_present
    out["scored_as_true7"] = out["composite_rank_avg"].notna()  # min_legs>=5 satisfied
    out["score"] = np.nan
    scored_mask = out["scored_as_true7"]
    out.loc[scored_mask, "score"] = 200.0 * (
        out.loc[scored_mask, "composite_rank_avg"].rank(pct=True) - 0.5)
    # decile: 1=lowest composite, 10=highest, computed only among scored names
    out["decile"] = np.nan
    if scored_mask.sum() >= 20:
        out.loc[scored_mask, "decile"] = pd.qcut(
            out.loc[scored_mask, "composite_rank_avg"].rank(method="first"),
            10, labels=False, duplicates="drop") + 1

    out = out.reset_index()
    out.insert(0, "date", latest_date)
    return out, latest_date


def universe_snapshot(scores_df: pd.DataFrame, latest_date) -> pd.DataFrame:
    """Cross-reference against the current nifty_total_market_750.csv universe
    file so it's disclosed how many of today's ~750 listed constituents
    actually clear the 5-of-7-leg data bar vs how many are silently absent
    (thin fundamentals coverage, not a construction choice)."""
    uni = pd.read_csv(UNIVERSE_CSV)
    sym_col = "Symbol" if "Symbol" in uni.columns else uni.columns[0]
    universe_syms = set(uni[sym_col].astype(str).str.strip())
    scored_syms = set(scores_df.loc[scores_df["scored_as_true7"], "symbol"].astype(str))

    snap = pd.DataFrame({"symbol": sorted(universe_syms)})
    snap["in_current_universe_csv"] = True
    snap["scored_as_true7_composite"] = snap["symbol"].isin(scored_syms)
    # append any scored symbol that isn't in the universe csv (panel_long can carry
    # extra/legacy names) -- disclose rather than silently drop
    extra = scored_syms - universe_syms
    if extra:
        extra_df = pd.DataFrame({"symbol": sorted(extra)})
        extra_df["in_current_universe_csv"] = False
        extra_df["scored_as_true7_composite"] = True
        snap = pd.concat([snap, extra_df], ignore_index=True)

    snap.insert(0, "asof_date", latest_date)
    return snap


def main():
    FORWARD_DIR.mkdir(parents=True, exist_ok=True)

    log("Step 1/3: freeze manifest (content-hash composite_final.py)...")
    manifest = build_freeze_manifest()
    manifest_path = FORWARD_DIR / "freeze_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    log(f"Wrote {manifest_path} -- sha256={manifest['source_sha256'][:16]}...")

    log("Step 2/3: score current universe at latest available date...")
    scores_df, latest_date = score_current_universe()
    date_tag = pd.Timestamp(latest_date).strftime("%Y%m%d")
    scores_path = FORWARD_DIR / f"scores_asof_{date_tag}.parquet"
    scores_df.to_parquet(scores_path, index=False)
    n_scored = int(scores_df["scored_as_true7"].sum())
    n_total = len(scores_df)
    log(f"Wrote {scores_path} -- {n_total} names total, {n_scored} scored as full TRUE7 (>=5-of-7 legs)")

    log("Step 3/3: universe snapshot (cross-ref current 750-name universe csv)...")
    snap_df = universe_snapshot(scores_df, latest_date)
    snap_path = FORWARD_DIR / f"universe_snapshot_asof_{date_tag}.csv"
    snap_df.to_csv(snap_path, index=False)
    log(f"Wrote {snap_path} -- {len(snap_df)} rows "
        f"({snap_df['scored_as_true7_composite'].sum()} scored)")

    banked = {
        "asof_date": str(pd.Timestamp(latest_date).date()),
        "banked_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_names_total_in_output": n_total,
        "n_names_scored_true7": n_scored,
        "scores_file": str(scores_path),
        "universe_snapshot_file": str(snap_path),
        "freeze_manifest_file": str(manifest_path),
        "freeze_manifest_sha256": manifest["source_sha256"],
        "disclosure": "asof_date is the LATEST date at which the underlying fundamentals+price "
                      "panel (panel_long.parquet) actually has data -- this is a PIT constraint of "
                      "the fundamentals source, not a calendar 'today'. If asof_date is materially "
                      "before the freeze date, that lag itself must be disclosed in the IC memo / "
                      "any forward-test grading write-up (it shortens the true elapsed forward window).",
        "grading_rule": "THIS FILE / SCRIPT NEVER SELF-GRADES. See rnd/forward_test/FROZEN_SPEC.md "
                        "for the pre-registered, evaluate-ONCE protocol.",
    }
    banked_path = FORWARD_DIR / "BANKED_SCORES_INDEX.json"
    # append-only index across freezes (in case this is re-run for a later refresh)
    existing = []
    if banked_path.exists():
        try:
            existing = json.loads(banked_path.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                existing = [existing]
        except Exception:
            existing = []
    existing.append(banked)
    banked_path.write_text(json.dumps(existing, indent=2, default=str), encoding="utf-8")
    log(f"Wrote/updated {banked_path}")

    log(json.dumps(banked, indent=2))
    log("DONE. Tracker built + today's scores banked. Grading happens LATER, ONCE, per FROZEN_SPEC.md.")


if __name__ == "__main__":
    main()
