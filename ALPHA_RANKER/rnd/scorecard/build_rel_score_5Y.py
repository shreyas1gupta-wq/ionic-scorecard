"""
S3 -- RELATIVE 5Y SCORECARD BUILDER.
Arjun Rao (Head of Quant), 2026-07-18. Implements SCORECARD_BLUEPRINT.md S2.3
mechanically -- no new research, no weight search, no leg swaps (blueprint S5).

Universe gate  -> quality_score >= 0.20 (S1.4) AND >=5-of-7 canonical legs present.
Two limbs on the gated universe:
  (a) sr_5Y        -- SR-v1 recipe (SECTOR_RELATIVE_REBUILD.md): 5 legs sector-
                       neutral (value_EY, mom_resid_plain, trend_ma65_slope,
                       quality_QMJ, bs_issuance), AG + cfo-pat RAW, PLUS an
                       8th component (growth-longevity) added per S2.3, with
                       value_EY + growth-longevity overweighted and mom/trend
                       downweighted relative to baseline [MY CALL on the exact
                       weight numbers -- S2.3 gives direction, not magnitudes;
                       see S3_RELATIVE_5Y_REPORT.md].
  (b) abs_merit_5Y -- same signals, FULL-universe (pooled, not sector-split)
                      ranks, valuation + growth-longevity weighted heavily.
Blend (frozen prior, S2.3): composite_5Y = 0.60*sr_5Y + 0.40*abs_merit_5Y.

mom_resid_plain is REBUILT FRESH via run_long_confirm.build_mom_resid_12_1 --
the capstone_legs.parquet cache holds mom_resid_peer, which is NOT used here
(S1.1 caveat / WAVE4_FINDINGS S1-CORRECTION-2 lesson).

Determinism: every transform is .rank(pct=True) / deterministic weighted
mean / clip. Zero .fit() calls. The only RNG is harness.evaluate()'s placebo
shuffle, fixed seed=42. This script runs its own build pipeline TWICE and
asserts byte-identical output before writing anything to disk.

Run synchronously, foreground, single pass. Log -> C:\\tmp\\s3_rel5y_run.log
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
SCORECARD_DIR = _THIS.parent
RND_DIR = SCORECARD_DIR.parent
ALPHA_DIR = RND_DIR.parent
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))

import harness as H  # noqa: E402
import run_long_confirm as LC  # noqa: E402

PANEL_DIR = RND_DIR / "panel"
WAVE4_DIR = RND_DIR / "wave4"
CARDS_DIR = SCORECARD_DIR / "cards_S3_rel5Y"
CARDS_DIR.mkdir(parents=True, exist_ok=True)

HORIZON = "5Y"
MIN_NAMES = 20            # harness convention, min names per date for IC
MIN_SECTOR_PEERS = 5       # SR-v1 convention
MIN_LEGS = 5               # of 7 canonical legs, blueprint S1.1 / min_legs rule
QUALITY_GATE_5Y = 0.20     # blueprint S1.4 -- drop bottom quality quintile

TRUE7 = ["value_EY", "mom_resid_plain", "trend_ma65_slope", "quality_QMJ",
         "bs_issuance", "bs_asset_growth", "quality_cfo_pat"]
SECTOR_NEUTRAL_LEGS = ["value_EY", "mom_resid_plain", "trend_ma65_slope",
                       "quality_QMJ", "bs_issuance"]   # SR-v1 recipe
RAW_LEGS = ["bs_asset_growth", "quality_cfo_pat"]       # SR-v1: left raw

# [MY CALL, disclosed in report] -- sr_5Y internal weights. Blueprint S2.3
# mandates the DIRECTION (overweight value_EY + growth-longevity, downweight
# momentum/trend legs) but not exact numbers. Baseline weight = 1.0;
# overweight = 2.0; downweight = 0.5. quality/issuance/AG/cfo-pat stay at
# baseline (untouched, not part of the mandate's overweight/downweight call).
SR5Y_WEIGHTS = {
    "value_EY": 2.0, "growth_longevity": 2.0,
    "mom_resid_plain": 0.5, "trend_ma65_slope": 0.5,
    "quality_QMJ": 1.0, "bs_issuance": 1.0,
    "bs_asset_growth": 1.0, "quality_cfo_pat": 1.0,
}
# [MY CALL, disclosed] -- abs_merit_5Y weights. Quality already gates the
# universe (S1.4); weighting it heavily AGAIN inside abs_merit would double-
# count the same QMJ/cfo-pat legs. Valuation + growth-longevity carry the
# mandate's "weighted heavily" instruction; quality gets a light residual
# weight (it already did its job as a floor).
ABS_MERIT_WEIGHTS = {"value_EY": 0.45, "growth_longevity": 0.45, "quality_score": 0.10}

BLEND_SR = 0.60
BLEND_ABS = 0.40

PLACEBO_SEED = 42


def log(msg):
    print(f"[s3_rel5y {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def to_native(o):
    if isinstance(o, dict):
        return {str(k): to_native(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_native(v) for v in o]
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o.date())
    return o


def write_json(path: Path, obj):
    path.write_text(json.dumps(to_native(obj), indent=2), encoding="utf-8")
    log(f"wrote {path}")


# ==========================================================================
# 0. LOAD -- data lineage
# ==========================================================================
def load_data():
    panel = pd.read_parquet(PANEL_DIR / "panel_pit.parquet")
    panel["date"] = pd.to_datetime(panel["date"])
    legs_raw = pd.read_parquet(PANEL_DIR / "capstone_legs.parquet")
    legs_raw["date"] = pd.to_datetime(legs_raw["date"])
    fg2 = pd.read_parquet(WAVE4_DIR / "_w6fg2_scored.parquet")
    fg2["date"] = pd.to_datetime(fg2["date"])
    return panel, legs_raw, fg2


# ==========================================================================
# rank helpers -- all restricted to a `univ_idx` MultiIndex(date,symbol)
# ==========================================================================
def rank_pct_within_date(s: pd.Series) -> pd.Series:
    df = s.rename("v").reset_index()
    df["date"] = pd.to_datetime(df["date"])
    df["r"] = df.groupby("date")["v"].rank(pct=True)
    return df.set_index(["date", "symbol"])["r"]


def pooled_rank_restricted(legs: dict, name: str, univ_df: pd.DataFrame) -> pd.Series:
    """Full-universe (pooled, not sector-split) per-date pct rank, restricted
    to the gated universe rows (inner join BEFORE ranking, per blueprint S2.2/
    S2.3 'all ranks recomputed WITHIN the gated cross-section')."""
    r = legs[name].rename("factor").reset_index()
    r["date"] = pd.to_datetime(r["date"])
    r = r.merge(univ_df[["date", "symbol"]], on=["date", "symbol"], how="inner")
    r["rank"] = r.groupby("date")["factor"].rank(pct=True)
    return r.set_index(["date", "symbol"])["rank"].rename(name)


def sector_rank_restricted(legs: dict, name: str, univ_df: pd.DataFrame, sym_sector: pd.Series,
                            min_peers: int = MIN_SECTOR_PEERS) -> pd.Series:
    """Per-(date,sector) pct rank, restricted to gated universe. Sector-date
    buckets smaller than min_peers are DROPPED (not fabricated), same
    convention as SECTOR_RELATIVE_REBUILD.md's sector_rank_col."""
    r = legs[name].rename("factor").reset_index()
    r["date"] = pd.to_datetime(r["date"])
    r = r.merge(univ_df[["date", "symbol"]], on=["date", "symbol"], how="inner")
    r["sector"] = r["symbol"].map(sym_sector)
    r = r.dropna(subset=["sector"])
    cnt = r.groupby(["date", "sector"])["factor"].transform("count")
    r = r[cnt >= min_peers].copy()
    r["rank"] = r.groupby(["date", "sector"])["factor"].rank(pct=True)
    return r.set_index(["date", "symbol"])["rank"].rename(name)


def weighted_combine(idx: pd.MultiIndex, cols: dict, weights: dict) -> pd.Series:
    """Weighted skip-na mean over `idx`. cols: {name: Series indexed (date,symbol)}."""
    wide = pd.DataFrame(index=idx)
    for name, s in cols.items():
        wide[name] = s.reindex(idx)
    present = wide.notna()
    w = pd.Series(weights)
    wsum = present.mul(w, axis=1).sum(axis=1)
    weighted_vals = wide.fillna(0.0).mul(w, axis=1).sum(axis=1)
    combo = weighted_vals.div(wsum.where(wsum > 0))
    return combo


# ==========================================================================
# MAIN BUILD PIPELINE (called twice for the determinism check)
# ==========================================================================
def build_all(panel: pd.DataFrame, legs_raw: pd.DataFrame, fg2: pd.DataFrame, verbose: bool = True):
    _log = log if verbose else (lambda *a, **k: None)

    # ---- sector map: panel_pit.sector is static per symbol (verified) ----
    sym_sector = panel.dropna(subset=["sector"]).groupby("symbol")["sector"].agg(lambda s: s.mode().iat[0])
    n_sectors = panel["sector"].nunique()
    _log(f"sym_sector: {len(sym_sector)} symbols classified into {n_sectors} sectors "
         f"(panel_pit.sector, static per-symbol)")

    # ---- assemble legs dict ----
    legs = {}
    for leg, g in legs_raw.groupby("leg"):
        legs[leg] = g.set_index(["date", "symbol"])["value"]

    _log("building mom_resid_plain FRESH via run_long_confirm.build_mom_resid_12_1 "
         "(NOT the cached mom_resid_peer)...")
    _, close, bench = LC.load_all()
    dates = pd.DatetimeIndex(sorted(panel["date"].unique()))
    legs["mom_resid_plain"] = LC.build_mom_resid_12_1(close, bench, dates)
    _log(f"mom_resid_plain: {len(legs['mom_resid_plain'])} obs")

    for n in TRUE7:
        assert n in legs, f"missing leg {n}"

    # ---- quality_score (S1.4), FULL universe, per date ----
    qmj_r = rank_pct_within_date(legs["quality_QMJ"])
    cfo_r = rank_pct_within_date(legs["quality_cfo_pat"])
    q_wide = pd.concat({"qmj": qmj_r, "cfo": cfo_r}, axis=1)
    q_raw = q_wide.mean(axis=1, skipna=True)
    quality_score = rank_pct_within_date(q_raw)  # full-universe, per date

    # ---- min_legs presence count on RAW TRUE7 legs ----
    presence = pd.concat({n: legs[n] for n in TRUE7}, axis=1).notna()
    leg_count = presence.sum(axis=1)

    qs_df = quality_score.rename("quality_score").reset_index()
    lc_df = leg_count.rename("leg_count").reset_index()
    gate_df = qs_df.merge(lc_df, on=["date", "symbol"], how="inner")
    gate_df["date"] = pd.to_datetime(gate_df["date"])
    n_before_gate = len(gate_df)
    gated = gate_df[(gate_df["quality_score"] >= QUALITY_GATE_5Y) & (gate_df["leg_count"] >= MIN_LEGS)].copy()
    n_after_quality_only = int((gate_df["quality_score"] >= QUALITY_GATE_5Y).sum())
    n_after_gate = len(gated)
    univ_df = gated[["date", "symbol"]].drop_duplicates()
    idx = pd.MultiIndex.from_frame(univ_df)
    _log(f"universe gate: {n_before_gate} (date,symbol) pairs with quality_score computed -> "
         f"{n_after_quality_only} pass quality>=0.{int(QUALITY_GATE_5Y*100)} -> "
         f"{n_after_gate} pass quality AND >=5-of-7 legs (final gated universe)")

    # ---- growth-longevity (composite_v2_confirmed + sub_op_persistent) ----
    f = fg2[["date", "symbol", "composite_v2_confirmed", "sub_op_persistent"]].copy()
    f = f.merge(univ_df, on=["date", "symbol"], how="inner")
    f["r_comp"] = f.groupby("date")["composite_v2_confirmed"].rank(pct=True)
    f["r_pers"] = f.groupby("date")["sub_op_persistent"].rank(pct=True)
    f["raw"] = f[["r_comp", "r_pers"]].mean(axis=1, skipna=True)
    f["gl"] = f.groupby("date")["raw"].rank(pct=True)
    growth_longevity = f.set_index(["date", "symbol"])["gl"].rename("growth_longevity")
    n_gl = growth_longevity.notna().sum()
    _log(f"growth_longevity: {n_gl}/{len(univ_df)} gated rows have a scored value "
         f"(coverage gap = fg2 fundamentals not available for every panel row)")

    # ---- (a) SR-v1 sector-neutral legs (restricted to gated universe) ----
    sr_cols = {}
    for leg in SECTOR_NEUTRAL_LEGS:
        sr_cols[leg] = sector_rank_restricted(legs, leg, univ_df, sym_sector, MIN_SECTOR_PEERS)
    for leg in RAW_LEGS:
        sr_cols[leg] = pooled_rank_restricted(legs, leg, univ_df)
    sr_cols["growth_longevity"] = growth_longevity

    sr_5Y_raw = weighted_combine(idx, sr_cols, SR5Y_WEIGHTS)
    sr_5Y = rank_pct_within_date(sr_5Y_raw.dropna())
    sr_5Y = sr_5Y.reindex(idx)

    # ---- (b) absolute-merit limb (FULL universe / pooled ranks, gated) ----
    value_full = pooled_rank_restricted(legs, "value_EY", univ_df)
    quality_full = rank_pct_within_date(quality_score.reindex(idx).dropna())  # re-rank WITHIN gated set
    quality_full = quality_full.reindex(idx)
    abs_cols = {"value_EY": value_full, "growth_longevity": growth_longevity, "quality_score": quality_full}
    abs_merit_5Y_raw = weighted_combine(idx, abs_cols, ABS_MERIT_WEIGHTS)
    abs_merit_5Y = rank_pct_within_date(abs_merit_5Y_raw.dropna())
    abs_merit_5Y = abs_merit_5Y.reindex(idx)

    # ---- blend ----
    composite_5Y = BLEND_SR * sr_5Y + BLEND_ABS * abs_merit_5Y
    composite_5Y = composite_5Y.where(sr_5Y.notna() & abs_merit_5Y.notna())

    valid = composite_5Y.dropna()
    rel_rank = rank_pct_within_date(valid)
    rel_score_5Y = 200.0 * (rel_rank - 0.5)
    rel_score_5Y = rel_score_5Y.reindex(idx)

    out = pd.DataFrame(index=idx)
    out["sr_5Y"] = sr_5Y
    out["abs_merit_5Y"] = abs_merit_5Y
    out["composite_5Y"] = composite_5Y
    out["rel_score_5Y"] = rel_score_5Y
    out = out.reset_index()
    out = out.sort_values(["date", "symbol"]).reset_index(drop=True)

    diag = {
        "n_panel_rows": len(panel), "n_panel_symbols": int(panel["symbol"].nunique()),
        "panel_date_min": str(panel["date"].min().date()), "panel_date_max": str(panel["date"].max().date()),
        "n_legs_raw_rows": len(legs_raw), "legs_present": sorted(legs_raw["leg"].unique().tolist()),
        "n_fg2_rows": len(fg2),
        "n_sectors": int(n_sectors),
        "n_before_gate": n_before_gate, "n_after_quality_only": n_after_quality_only,
        "n_after_gate": n_after_gate,
        "n_scored_sr_5Y": int(sr_5Y.notna().sum()),
        "n_scored_abs_merit_5Y": int(abs_merit_5Y.notna().sum()),
        "n_scored_composite_5Y": int(composite_5Y.notna().sum()),
        "n_growth_longevity_covered": int(n_gl),
    }
    return out, legs, sym_sector, univ_df, idx, quality_score, growth_longevity, diag


# ==========================================================================
# direct IC helper (for drop-one / era-split diagnostics, NOT routed through
# harness.evaluate -- same disclosed convention as SECTOR_RELATIVE_REBUILD.md:
# diagnostics on an already-evaluated composite are not a new signal search)
# ==========================================================================
def compute_ic_direct(factor_series: pd.Series, tgt: pd.DataFrame, min_names: int = MIN_NAMES) -> pd.Series:
    f = factor_series.rename("factor").reset_index()
    f["date"] = pd.to_datetime(f["date"])
    m = f.merge(tgt, on=["date", "symbol"], how="inner")
    ic_rows = []
    for d, g in m.groupby("date"):
        gg = g.dropna(subset=["factor", "target_eval"])
        if len(gg) < min_names:
            continue
        rho, _ = stats.spearmanr(gg["factor"], gg["target_eval"])
        if not np.isnan(rho):
            ic_rows.append((d, rho))
    return pd.Series(dict(ic_rows)).dropna().sort_index()


def main():
    log("=" * 70)
    log("S3 RELATIVE 5Y SCORECARD BUILD -- start")
    log("=" * 70)

    panel, legs_raw, fg2 = load_data()
    log(f"panel_pit: {len(panel)} rows, {panel['symbol'].nunique()} symbols, "
        f"{panel['date'].min().date()} to {panel['date'].max().date()}")
    log(f"capstone_legs: {len(legs_raw)} rows, legs={sorted(legs_raw['leg'].unique())}")
    log(f"_w6fg2_scored: {len(fg2)} rows")

    # ---- corp-action guard on the 5Y evaluation targets ----
    disc_col = "disc_event_in_window_5Y"
    panel_g = panel.copy()
    mask = panel_g[disc_col].fillna(0) > 0
    n_guard = int(mask.sum())
    panel_g.loc[mask, ["fwd_ret_5Y_raw", "fwd_ret_5Y_resid", "fwd_ret_5Y_excess"]] = np.nan
    log(f"corp-action guard: NaN'd {n_guard}/{len(panel)} disc-flagged rows from 5Y targets")

    # ==========================================================================
    # DETERMINISM CHECK -- run the full build pipeline TWICE from scratch,
    # assert byte-identical output, before writing anything else to disk.
    # ==========================================================================
    log("DETERMINISM CHECK: running build_all() twice from scratch...")
    out1, legs, sym_sector, univ_df, idx, quality_score, growth_longevity, diag1 = build_all(
        panel, legs_raw, fg2, verbose=True)
    out2, *_rest2, diag2 = build_all(panel, legs_raw, fg2, verbose=False)

    identical = out1.equals(out2)
    if not identical:
        # localize any float tolerance issues (should be none -- no randomness)
        try:
            pd.testing.assert_frame_equal(out1, out2, check_exact=True)
            identical = True
        except AssertionError as e:
            log(f"DETERMINISM CHECK FAILED: {e}")
    log(f"DETERMINISM CHECK: {'PASS (byte-identical)' if identical else 'FAIL'} -- "
        f"run1 shape={out1.shape} run2 shape={out2.shape}")
    assert identical, "Determinism contract violated -- build_all() is not reproducible"

    out = out1
    diag = diag1

    # ---- write scored parquet ----
    out_path = SCORECARD_DIR / "rel_score_5Y.parquet"
    out.to_parquet(out_path, index=False)
    log(f"wrote {out_path} ({len(out)} rows)")

    # ==========================================================================
    # HARNESS EVALUATION -- sr_5Y, abs_merit_5Y, composite_5Y, each at 5Y,
    # return_basis=resid (matches SECTOR_RELATIVE_REBUILD.md convention)
    # ==========================================================================
    log("HARNESS: evaluating sr_5Y, abs_merit_5Y, composite_5Y (5Y, resid basis)...")
    sr_series = out.set_index(["date", "symbol"])["sr_5Y"].dropna()
    abs_series = out.set_index(["date", "symbol"])["abs_merit_5Y"].dropna()
    comp_series = out.set_index(["date", "symbol"])["composite_5Y"].dropna()

    card_sr = H.evaluate(sr_series, HORIZON, return_basis="resid", factor_id="S3_REL5Y_sr_5Y",
                          panel=panel_g, panel_source="panel_pit_survivorship_free",
                          family="S3_REL5Y", write_card=True, cards_dir=CARDS_DIR)
    card_abs = H.evaluate(abs_series, HORIZON, return_basis="resid", factor_id="S3_REL5Y_abs_merit_5Y",
                           panel=panel_g, panel_source="panel_pit_survivorship_free",
                           family="S3_REL5Y", write_card=True, cards_dir=CARDS_DIR)
    card_comp = H.evaluate(comp_series, HORIZON, return_basis="resid", factor_id="S3_REL5Y_composite_5Y",
                            panel=panel_g, panel_source="panel_pit_survivorship_free",
                            family="S3_REL5Y", write_card=True, cards_dir=CARDS_DIR)

    for name, card in (("sr_5Y", card_sr), ("abs_merit_5Y", card_abs), ("composite_5Y", card_comp)):
        log(f"{name:16s} n_obs={card.get('n_obs')} IC_mean={card['ic']['ic_mean']:.4f} "
            f"IC_IR={card['ic']['ic_ir']:.4f} mono={card['deciles']['monotonicity']} "
            f"ann_LS_horizon_aware={card['long_short']['ann_return_LS_horizon_aware']:.4f} "
            f"lag_delta={card['lag_test']['lag_test_delta']:.4f} "
            f"placebo_IC={card['placebo']['placebo_ic']:.4f} "
            f"DSR(global)={card['dsr']['dsr']:.3e} PBO={card['pbo']['pbo']:.4f} "
            f"-> {card['verdict']}")

    # ---- honest local-trial-count DSR (n_trials=3, this script only) ----
    def local_dsr(card, n_local=3):
        d = card["dsr"]
        return H.dsr_from_stats(d["sr_hat"], d["skew"], d["kurtosis"], d["n_obs"], n_local)

    dsr_local = {"sr_5Y": local_dsr(card_sr), "abs_merit_5Y": local_dsr(card_abs),
                 "composite_5Y": local_dsr(card_comp)}
    log(f"local DSR (n_trials=3): sr_5Y={dsr_local['sr_5Y']['dsr']:.4f} "
        f"abs_merit_5Y={dsr_local['abs_merit_5Y']['dsr']:.4f} "
        f"composite_5Y={dsr_local['composite_5Y']['dsr']:.4f}")

    # ==========================================================================
    # DROP-ONE-LEG (sr_5Y: 8 slots incl. growth_longevity; abs_merit_5Y: 3
    # slots; blend: drop-limb = the two limbs' own solo IC, already computed
    # above as card_sr / card_abs)
    # ==========================================================================
    log("DROP-ONE: sr_5Y (8 components) and abs_merit_5Y (3 components)...")
    tgt = panel_g[["date", "symbol", "fwd_ret_5Y_raw", "fwd_ret_5Y_resid"]].dropna(
        subset=["fwd_ret_5Y_resid", "fwd_ret_5Y_raw"]).rename(columns={"fwd_ret_5Y_resid": "target_eval"})

    def rebuild_sr_dropone(drop_key):
        weights = {k: v for k, v in SR5Y_WEIGHTS.items() if k != drop_key}
        cols = {}
        for leg in SECTOR_NEUTRAL_LEGS:
            if leg == drop_key:
                continue
            cols[leg] = sector_rank_restricted(legs, leg, univ_df, sym_sector, MIN_SECTOR_PEERS)
        for leg in RAW_LEGS:
            if leg == drop_key:
                continue
            cols[leg] = pooled_rank_restricted(legs, leg, univ_df)
        if drop_key != "growth_longevity":
            cols["growth_longevity"] = growth_longevity
        combo = weighted_combine(idx, cols, weights)
        return combo.dropna()

    def rebuild_abs_dropone(drop_key):
        weights = {k: v for k, v in ABS_MERIT_WEIGHTS.items() if k != drop_key}
        cols = {}
        if drop_key != "value_EY":
            cols["value_EY"] = pooled_rank_restricted(legs, "value_EY", univ_df)
        if drop_key != "growth_longevity":
            cols["growth_longevity"] = growth_longevity
        if drop_key != "quality_score":
            cols["quality_score"] = rank_pct_within_date(quality_score.reindex(idx).dropna()).reindex(idx)
        combo = weighted_combine(idx, cols, weights)
        return combo.dropna()

    dropone_sr = {}
    for leg in list(SR5Y_WEIGHTS.keys()):
        combo = rebuild_sr_dropone(leg)
        ic = compute_ic_direct(combo, tgt)
        dropone_sr[leg] = {"ic_mean": float(ic.mean()) if len(ic) else float("nan"), "n_dates": int(len(ic))}
        log(f"  sr_5Y drop {leg:18s}: ic_mean={dropone_sr[leg]['ic_mean']:.4f} (n={dropone_sr[leg]['n_dates']})")

    dropone_abs = {}
    for leg in list(ABS_MERIT_WEIGHTS.keys()):
        combo = rebuild_abs_dropone(leg)
        ic = compute_ic_direct(combo, tgt)
        dropone_abs[leg] = {"ic_mean": float(ic.mean()) if len(ic) else float("nan"), "n_dates": int(len(ic))}
        log(f"  abs_merit_5Y drop {leg:18s}: ic_mean={dropone_abs[leg]['ic_mean']:.4f} (n={dropone_abs[leg]['n_dates']})")

    sr_dropone_vals = np.array([v["ic_mean"] for v in dropone_sr.values() if not np.isnan(v["ic_mean"])])
    abs_dropone_vals = np.array([v["ic_mean"] for v in dropone_abs.values() if not np.isnan(v["ic_mean"])])
    dropone_summary = {
        "sr_5Y": dropone_sr, "abs_merit_5Y": dropone_abs,
        "sr_5Y_std": float(np.nanstd(sr_dropone_vals, ddof=1)) if len(sr_dropone_vals) > 1 else float("nan"),
        "abs_merit_5Y_std": float(np.nanstd(abs_dropone_vals, ddof=1)) if len(abs_dropone_vals) > 1 else float("nan"),
        "blend_dropone_note": "drop-limb IC = the solo limb IC already computed via harness (card_sr, card_abs)",
        "blend_drop_sr": {"ic_mean": card_abs["ic"]["ic_mean"]},   # blend w/o sr = abs_merit alone
        "blend_drop_abs": {"ic_mean": card_sr["ic"]["ic_mean"]},   # blend w/o abs_merit = sr alone
    }

    # ==========================================================================
    # ERA SPLIT (4-way auto, matches SECTOR_RELATIVE_REBUILD.md convention)
    # ==========================================================================
    log("ERA SPLIT (4-way, sr_5Y / abs_merit_5Y / composite_5Y)...")
    sr_ic_m = compute_ic_direct(sr_series, tgt)
    abs_ic_m = compute_ic_direct(abs_series, tgt)
    comp_ic_m = compute_ic_direct(comp_series, tgt)
    all_dates = sorted(set(sr_ic_m.index) | set(abs_ic_m.index) | set(comp_ic_m.index))
    era_edges = np.array_split(np.array(all_dates), 4)
    era_result = {}
    for i, e in enumerate(era_edges):
        if len(e) == 0:
            continue
        lbl = f"era{i+1}_{pd.Timestamp(e[0]).year}-{pd.Timestamp(e[-1]).year}"
        sr_v = sr_ic_m.reindex(e).dropna()
        abs_v = abs_ic_m.reindex(e).dropna()
        comp_v = comp_ic_m.reindex(e).dropna()
        era_result[lbl] = {
            "sr_5Y_ic": float(sr_v.mean()) if len(sr_v) else float("nan"),
            "abs_merit_5Y_ic": float(abs_v.mean()) if len(abs_v) else float("nan"),
            "composite_5Y_ic": float(comp_v.mean()) if len(comp_v) else float("nan"),
            "n": int(len(comp_v)),
        }
        log(f"  {lbl}: sr={era_result[lbl]['sr_5Y_ic']:.4f} abs={era_result[lbl]['abs_merit_5Y_ic']:.4f} "
            f"comp={era_result[lbl]['composite_5Y_ic']:.4f} n={era_result[lbl]['n']}")

    # ---- single-year regime slices (2018/2020/2022/2024/2026), best-effort --
    log("YEAR SLICES (2018/2020/2022/2024/2026, best-effort -- 5Y label needs "
        "data through t+5y, so coverage thins after ~2020)...")
    year_slices = {}
    for yr in (2018, 2020, 2022, 2024, 2026):
        ydates = [d for d in all_dates if pd.Timestamp(d).year == yr]
        if not ydates:
            year_slices[str(yr)] = {"n": 0, "note": "no dates with a scored composite in this year"}
            continue
        sr_v = sr_ic_m.reindex(ydates).dropna()
        comp_v = comp_ic_m.reindex(ydates).dropna()
        year_slices[str(yr)] = {
            "sr_5Y_ic": float(sr_v.mean()) if len(sr_v) else float("nan"),
            "composite_5Y_ic": float(comp_v.mean()) if len(comp_v) else float("nan"),
            "n": int(len(comp_v)),
        }
        log(f"  {yr}: comp_ic={year_slices[str(yr)]['composite_5Y_ic']} n={year_slices[str(yr)]['n']}")

    # ==========================================================================
    # WRITE weights fragment + cards summary
    # ==========================================================================
    fragment = {
        "S3_relative_5Y": {
            "quality_gate_threshold": QUALITY_GATE_5Y,
            "min_legs_of_7": MIN_LEGS,
            "min_sector_peers": MIN_SECTOR_PEERS,
            "min_names_per_date": MIN_NAMES,
            "sector_grain": "panel_pit.sector (22-bucket macro_sector, static per symbol)",
            "sector_neutral_legs": SECTOR_NEUTRAL_LEGS,
            "raw_legs": RAW_LEGS,
            "mom_resid_plain_source": "rebuilt fresh via run_long_confirm.build_mom_resid_12_1, "
                                      "NOT the cached mom_resid_peer",
            "growth_longevity_construction": "rank_pct(0.5*rank_pct(composite_v2_confirmed) + "
                                              "0.5*rank_pct(sub_op_persistent)), computed within the "
                                              "gated universe [MY CALL -- mirrors the S1.4 quality_score pattern]",
            "sr5Y_weights": SR5Y_WEIGHTS,
            "abs_merit5Y_weights": ABS_MERIT_WEIGHTS,
            "blend": {"sr_5Y": BLEND_SR, "abs_merit_5Y": BLEND_ABS},
            "placebo_seed": PLACEBO_SEED,
            "n_placebo_shuffles": 5,
            "output_range": "rel_score_5Y in [-100, +100] = 200*(rank_pct(composite_5Y) - 0.5)",
            "data_thinness_flag": "pre-2012 fundamentals thin; 5Y magnitudes are DIRECTIONAL (blueprint S2.3)",
        },
        "determinism_check": {"pass": bool(identical), "run1_shape": list(out1.shape), "run2_shape": list(out2.shape)},
        "diagnostics": diag,
    }
    write_json(SCORECARD_DIR / "weights_5Y_fragment.json", fragment)

    summary = {
        "sr_5Y": card_sr, "abs_merit_5Y": card_abs, "composite_5Y": card_comp,
        "dsr_local_n3": dsr_local, "dropone": dropone_summary,
        "era_split": era_result, "year_slices": year_slices,
    }
    write_json(CARDS_DIR / "S3_REL5Y_SUMMARY.json", summary)

    log("DONE. Cards -> " + str(CARDS_DIR))
    log("Parquet -> " + str(out_path))
    log("Weights fragment -> " + str(SCORECARD_DIR / "weights_5Y_fragment.json"))

    return {
        "card_sr": card_sr, "card_abs": card_abs, "card_comp": card_comp,
        "dsr_local": dsr_local, "dropone": dropone_summary, "era": era_result,
        "year_slices": year_slices, "diag": diag, "identical": identical,
    }


if __name__ == "__main__":
    result = main()
