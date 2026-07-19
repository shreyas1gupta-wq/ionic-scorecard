"""
W6SR -- SECTOR-RELATIVE COMPOSITE REBUILD.
Arjun Rao (Head of Quant), 2026-07-17. Run synchronously, foreground, single pass.

Trigger: SECTOR_BIAS_AUDIT.md (W6SB) found ~41% of the 7-leg capstone
composite's edge is a sector bet, ~59% genuine stock selection. Per that
audit's recommendation, this script REBUILDS the composite sector-relative
for the contaminated legs (priority order by IC lost): bs_issuance (worst,
39.7% retention), mom_resid_plain, trend_ma65_slope, quality_QMJ, value_EY.
quality_cfo_pat is left RAW (no sector tilt found, 117% retention).
bs_asset_growth is borderline (71.8% retention) -- tested BOTH ways.

DETERMINISM: all ranks are pandas .rank(pct=True) on cached/rebuilt factor
values (no fitting, no randomness) except the 5 placebo shuffles inside
harness.evaluate(), which use a FIXED seed (42, harness default). Same input
data -> bit-identical output every run.

Cards -> rnd/wave4/cards_w6sr/W6SR_*.json (via harness.evaluate, official,
trial-counted) plus W6SR_DROPONE / W6SR_ERA (direct IC computation, NOT
routed through harness.evaluate -- these are robustness DIAGNOSTICS on
already-evaluated composites, not new signal searches, so they are not
given their own inflated trial count; this choice is disclosed here and in
the memo).
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
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))

import harness as H  # noqa: E402
import run_long_confirm as LC  # noqa: E402

PANEL_DIR = RND_DIR / "panel"
CARDS_DIR = RND_DIR / "wave4" / "cards_w6sr"
CARDS_DIR.mkdir(parents=True, exist_ok=True)

MIN_NAMES = 20
MIN_SECTOR_PEERS = 5
MIN_LEGS = 5
HORIZON = "1Y"

TRUE7 = ["value_EY", "mom_resid_plain", "trend_ma65_slope", "quality_QMJ",
         "bs_issuance", "bs_asset_growth", "quality_cfo_pat"]
LEG_LABELS = {
    "value_EY": "EY", "mom_resid_plain": "mom-resid", "trend_ma65_slope": "MA65",
    "quality_QMJ": "QMJ", "bs_issuance": "issuance", "bs_asset_growth": "asset-growth",
    "quality_cfo_pat": "cfo-pat",
}
# priority order from SECTOR_BIAS_AUDIT.md Task 3 (worst IC-retention first)
SECTOR_NEUTRAL_LEGS = ["bs_issuance", "mom_resid_plain", "trend_ma65_slope",
                       "quality_QMJ", "value_EY"]
ALWAYS_RAW_LEGS = ["quality_cfo_pat"]
TEST_BOTH_LEG = "bs_asset_growth"

OFFICIAL_IC_IR = 1.3450288630259197
OFFICIAL_IC_MEAN = 0.1889984545699352
OFFICIAL_ANN_LS = 3.695972572048369
OFFICIAL_N_IC_DATES = 145


def log(msg):
    print(f"[w6sr {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def to_native(o):
    if isinstance(o, dict):
        return {k: to_native(v) for k, v in o.items()}
    if isinstance(o, list):
        return [to_native(v) for v in o]
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o.date())
    return o


def write_json(name, obj):
    p = CARDS_DIR / f"{name}.json"
    p.write_text(json.dumps(to_native(obj), indent=2), encoding="utf-8")
    log(f"wrote {p}")


# ==========================================================================
# 0. LOAD -- data lineage
# ==========================================================================
log("loading panel_long.parquet, capstone_legs.parquet, canonical_7leg_scores.parquet...")
panel = pd.read_parquet(PANEL_DIR / "panel_long.parquet")
panel["date"] = pd.to_datetime(panel["date"])
legs_raw = pd.read_parquet(PANEL_DIR / "capstone_legs.parquet")
legs_raw["date"] = pd.to_datetime(legs_raw["date"])
canon_scores = pd.read_parquet(PANEL_DIR / "canonical_7leg_scores.parquet")

n_panel_rows = len(panel)
n_panel_symbols = panel["symbol"].nunique()
panel_date_min, panel_date_max = panel["date"].min(), panel["date"].max()
log(f"panel_long: {n_panel_rows} rows, {n_panel_symbols} symbols, "
    f"{panel_date_min.date()} to {panel_date_max.date()}")
log(f"capstone_legs: {len(legs_raw)} rows, legs={sorted(legs_raw['leg'].unique())}")
log(f"canonical_7leg_scores.parquet (reference, not recomputed from): {len(canon_scores)} rows")

# ---- corporate-action guard (identical convention to CANONICAL_7LEG_1Y) ----
disc_col = "disc_event_in_window_1Y"
panel_g = panel.copy()
mask = panel_g[disc_col].fillna(0) > 0
n_guard_dropped = int(mask.sum())
panel_g.loc[mask, ["fwd_ret_1Y_raw", "fwd_ret_1Y_resid"]] = np.nan
log(f"corp-action guard: NaN'd {n_guard_dropped}/{n_panel_rows} disc-flagged rows from 1Y targets")

# sector classification: panel_long.sector (macro_sector, 22 buckets) --
# SAME grain as SECTOR_BIAS_AUDIT.md so this rebuild's numbers are directly
# comparable to that audit's Task 3 (fully-neutral) reference figures.
# data/universe/sector_map.parquet (42 finer sub-buckets) exists but is NOT
# used here -- switching grain would break comparability with the audit
# this rebuild implements, and is disclosed as a methodology choice, not a
# silent substitution.
sym_sector = panel.dropna(subset=["sector"]).groupby("symbol")["sector"] \
    .agg(lambda s: s.mode().iat[0])
log(f"sym_sector: {len(sym_sector)} symbols classified, {panel['sector'].nunique()} sectors "
    f"(source: panel_long.sector, static per-symbol mode)")

legs = {}
for leg, g in legs_raw.groupby("leg"):
    legs[leg] = g.set_index(["date", "symbol"])["value"]

log("building mom_resid_plain FRESH (matches CANONICAL_7LEG_1Y construction, "
    "NOT the cached sub_sector-peer-relative mom_resid_peer)...")
_, close, bench = LC.load_all()
dates = LC._panel_dates(panel)
legs["mom_resid_plain"] = LC.build_mom_resid_12_1(close, bench, dates)
log(f"mom_resid_plain: {len(legs['mom_resid_plain'])} obs")

for n in TRUE7:
    assert n in legs, f"missing leg {n}"

lineage = {
    "panel_long.parquet": {"rows": n_panel_rows, "symbols": n_panel_symbols,
                            "date_min": str(panel_date_min.date()), "date_max": str(panel_date_max.date())},
    "capstone_legs.parquet": {"rows": len(legs_raw), "legs_present": sorted(legs_raw["leg"].unique().tolist())},
    "canonical_7leg_scores.parquet": {"rows": len(canon_scores), "used_as": "reference only, not recomputed from"},
    "sector_map.parquet": {"used": False,
                            "reason": "panel_long.sector (22-bucket macro_sector) used instead, to match "
                                      "SECTOR_BIAS_AUDIT.md Task 3 grain for direct comparability"},
    "corp_action_guard_rows_dropped": n_guard_dropped,
    "mom_resid_plain_source": "rebuilt fresh via run_long_confirm.build_mom_resid_12_1 (NOT cached "
                               "mom_resid_peer, which is already sub_sector peer-relative-z upstream)",
}

# ==========================================================================
# rank helpers
# ==========================================================================
def raw_rank_col(name: str) -> pd.Series:
    """Full-universe per-date percentile rank of leg `name`."""
    r = legs[name].rename("factor").reset_index()
    r["date"] = pd.to_datetime(r["date"])
    r["rank"] = r.groupby("date")["factor"].rank(pct=True)
    return r.set_index(["date", "symbol"])["rank"].rename(name)


def sector_rank_col(name: str, min_peers: int = MIN_SECTOR_PEERS) -> pd.Series:
    """Per-(date, sector) percentile rank of leg `name`. Sector-date buckets
    smaller than min_peers are DROPPED (not fabricated). PIT-safe: this is a
    cross-sectional (same-date) transform only, no lookahead across time."""
    r = legs[name].rename("factor").reset_index()
    r["date"] = pd.to_datetime(r["date"])
    r["sector"] = r["symbol"].map(sym_sector)
    r = r.dropna(subset=["sector"])
    cnt = r.groupby(["date", "sector"])["factor"].transform("count")
    r = r[cnt >= min_peers].copy()
    r["rank"] = r.groupby(["date", "sector"])["factor"].rank(pct=True)
    return r.set_index(["date", "symbol"])["rank"].rename(name)


def build_composite(leg_treatment: dict, min_legs: int = MIN_LEGS) -> pd.Series:
    """leg_treatment: {leg_name: 'raw'|'sector'}. Equal-weight mean of
    per-leg percentile-rank columns (mixed raw/sector-neutral scales, all on
    [0,1] -- same combination convention as composite_pit.py / the audit's
    build_sector_neutral_composite)."""
    frames = []
    for name, kind in leg_treatment.items():
        col = raw_rank_col(name) if kind == "raw" else sector_rank_col(name)
        frames.append(col)
    wide = pd.concat(frames, axis=1)
    combo = wide.mean(axis=1, skipna=True)
    n_present = wide.notna().sum(axis=1)
    combo = combo.where(n_present >= min_legs)
    return combo.dropna().rename("factor")


RAW_TREATMENT = {n: "raw" for n in TRUE7}
SR_V1_TREATMENT = {n: ("sector" if n in SECTOR_NEUTRAL_LEGS else "raw") for n in TRUE7}  # AG raw
SR_V2_TREATMENT = dict(SR_V1_TREATMENT)
SR_V2_TREATMENT[TEST_BOTH_LEG] = "sector"  # AG also sector-neutral

log(f"RAW_TREATMENT={RAW_TREATMENT}")
log(f"SR_V1_TREATMENT (AG raw)={SR_V1_TREATMENT}")
log(f"SR_V2_TREATMENT (AG sector-neutral)={SR_V2_TREATMENT}")

# ==========================================================================
# STEP 1 -- SANITY CHECK: rebuild raw 7-leg composite, must reproduce
# official IC_IR=1.345 / ann_LS=3.696 on matched dates
# ==========================================================================
log("STEP 1: sanity check -- rebuild raw composite, compare to official CANONICAL_7LEG_1Y...")
raw_combo = build_composite(RAW_TREATMENT, min_legs=MIN_LEGS)
card_sanity = H.evaluate(
    raw_combo, HORIZON, return_basis="resid", factor_id="W6SR_SANITY_raw7",
    panel=panel_g, panel_source="real_panel_long_capstone_w6sr_sanity",
    family="W6SR_SANITY", write_card=True, cards_dir=CARDS_DIR,
)
sanity_ic_ir = card_sanity["ic"]["ic_ir"]
sanity_ic_mean = card_sanity["ic"]["ic_mean"]
sanity_ann_ls = card_sanity["long_short"]["ann_return_LS"]
sanity_n_dates = card_sanity["ic"]["n_ic_dates"]
sanity_ok = (abs(sanity_ic_ir - OFFICIAL_IC_IR) < 0.02 and abs(sanity_ann_ls - OFFICIAL_ANN_LS) < 0.05)
log(f"SANITY: rebuilt ic_ir={sanity_ic_ir:.4f} (official {OFFICIAL_IC_IR:.4f}), "
    f"ann_LS={sanity_ann_ls:.4f} (official {OFFICIAL_ANN_LS:.4f}), n_dates={sanity_n_dates} "
    f"(official {OFFICIAL_N_IC_DATES}) -- {'PASS' if sanity_ok else 'FAIL'}")

# ==========================================================================
# STEP 2 -- build + evaluate sector-relative composite variants
# ==========================================================================
log("STEP 2: building sector-relative composite variants (v1=AG raw, v2=AG sector-neutral)...")
sr_v1 = build_composite(SR_V1_TREATMENT, min_legs=MIN_LEGS)
sr_v2 = build_composite(SR_V2_TREATMENT, min_legs=MIN_LEGS)

card_v1 = H.evaluate(
    sr_v1, HORIZON, return_basis="resid", factor_id="W6SR_COMPOSITE_v1_AGraw",
    panel=panel_g, panel_source="real_panel_long_capstone_w6sr",
    family="W6SR", write_card=True, cards_dir=CARDS_DIR,
)
card_v2 = H.evaluate(
    sr_v2, HORIZON, return_basis="resid", factor_id="W6SR_COMPOSITE_v2_AGneutral",
    panel=panel_g, panel_source="real_panel_long_capstone_w6sr",
    family="W6SR", write_card=True, cards_dir=CARDS_DIR,
)
log(f"SR-v1 (AG raw):      ic_mean={card_v1['ic']['ic_mean']:.4f} ic_ir={card_v1['ic']['ic_ir']:.4f} "
    f"ann_LS={card_v1['long_short']['ann_return_LS']:.4f} n_dates={card_v1['ic']['n_ic_dates']} "
    f"turnover={card_v1['turnover']['avg_top_decile_turnover']:.4f} "
    f"net_of_cost={card_v1['costs']['net_of_cost_ann_return']:.4f} verdict={card_v1['verdict']}")
log(f"SR-v2 (AG neutral):  ic_mean={card_v2['ic']['ic_mean']:.4f} ic_ir={card_v2['ic']['ic_ir']:.4f} "
    f"ann_LS={card_v2['long_short']['ann_return_LS']:.4f} n_dates={card_v2['ic']['n_ic_dates']} "
    f"turnover={card_v2['turnover']['avg_top_decile_turnover']:.4f} "
    f"net_of_cost={card_v2['costs']['net_of_cost_ann_return']:.4f} verdict={card_v2['verdict']}")

# ==========================================================================
# STEP 3 -- honest-trials-count DSR recompute (harness's GLOBAL trial
# counter is shared across the entire research program -- 662+ trials
# before this script ran -- and crushes DSR toward 0 for anyone. This
# rebuild made exactly 3 NEW confirmatory trials (sanity + v1 + v2), not a
# search over hundreds of variants, so we ALSO report a family-local DSR
# with that honest small count, per harness.dsr_from_stats() -- the same
# mechanism pragmatic_score_v2.py uses. Both numbers are disclosed; neither
# replaces the other.)
# ==========================================================================
log("STEP 3: honest-trials-count DSR recompute (n_trials=3, this rebuild only)...")


def local_dsr(card, n_trials_local=3):
    d = card["dsr"]
    return H.dsr_from_stats(d["sr_hat"], d["skew"], d["kurtosis"], d["n_obs"], n_trials_local)


dsr_local_sanity = local_dsr(card_sanity)
dsr_local_v1 = local_dsr(card_v1)
dsr_local_v2 = local_dsr(card_v2)
log(f"local DSR (n_trials=3): sanity={dsr_local_sanity['dsr']:.4f} v1={dsr_local_v1['dsr']:.4f} "
    f"v2={dsr_local_v2['dsr']:.4f}  |  global-trial-count DSR (n_trials={card_v1['dsr']['n_trials']}): "
    f"sanity={card_sanity['dsr']['dsr']:.2e} v1={card_v1['dsr']['dsr']:.2e} v2={card_v2['dsr']['dsr']:.2e}")

# ==========================================================================
# STEP 4 -- ROBUSTNESS: drop-one leg, RAW vs SECTOR-RELATIVE (v1)
# ==========================================================================
log("STEP 4: drop-one leg robustness (RAW7 vs SR-v1), direct IC (not routed "
    "through harness.evaluate -- diagnostic on already-evaluated composites, "
    "not a new signal search; disclosed, not double-counted as a trial)...")

tgt = panel_g[["date", "symbol", "sector", "fwd_ret_1Y_raw", "fwd_ret_1Y_resid", disc_col]].copy()
tgt = tgt.dropna(subset=["fwd_ret_1Y_resid", "fwd_ret_1Y_raw"])
tgt = tgt.rename(columns={"fwd_ret_1Y_resid": "target_eval", "fwd_ret_1Y_raw": "target_raw"})


def compute_ic_direct(factor_series, min_names=MIN_NAMES):
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
    s = pd.Series(dict(ic_rows)).dropna().sort_index()
    return s


def dropone_ic(treatment: dict, drop_leg: str):
    remaining = {k: v for k, v in treatment.items() if k != drop_leg}
    combo = build_composite(remaining, min_legs=max(4, MIN_LEGS - 1))
    s = compute_ic_direct(combo)
    return float(s.mean()) if len(s) else float("nan"), int(len(s))


dropone_raw = {}
dropone_sr = {}
for leg in TRUE7:
    ic_r, n_r = dropone_ic(RAW_TREATMENT, leg)
    ic_s, n_s = dropone_ic(SR_V1_TREATMENT, leg)
    dropone_raw[LEG_LABELS[leg]] = {"ic_mean_dropping_this_leg": ic_r, "n_dates": n_r}
    dropone_sr[LEG_LABELS[leg]] = {"ic_mean_dropping_this_leg": ic_s, "n_dates": n_s}
    log(f"  drop {LEG_LABELS[leg]:12s}: RAW ic={ic_r:.4f} (n={n_r})  |  SR-v1 ic={ic_s:.4f} (n={n_s})")

raw_dropone_vals = np.array([v["ic_mean_dropping_this_leg"] for v in dropone_raw.values()])
sr_dropone_vals = np.array([v["ic_mean_dropping_this_leg"] for v in dropone_sr.values()])
raw_dropone_std = float(np.nanstd(raw_dropone_vals, ddof=1))
sr_dropone_std = float(np.nanstd(sr_dropone_vals, ddof=1))
raw_dropone_range = float(np.nanmax(raw_dropone_vals) - np.nanmin(raw_dropone_vals))
sr_dropone_range = float(np.nanmax(sr_dropone_vals) - np.nanmin(sr_dropone_vals))
more_robust_dropone = sr_dropone_std < raw_dropone_std

log(f"drop-one dispersion: RAW std={raw_dropone_std:.4f} range={raw_dropone_range:.4f}  |  "
    f"SR-v1 std={sr_dropone_std:.4f} range={sr_dropone_range:.4f}  -> "
    f"{'SR-v1 MORE robust' if more_robust_dropone else 'RAW MORE (or equally) robust'}")

# ==========================================================================
# STEP 5 -- ERA TEST: split sample into 4 eras, IC per era, RAW vs SR-v1
# ==========================================================================
log("STEP 5: era-split IC stability (RAW7 vs SR-v1)...")
raw_combo_m = compute_ic_direct(raw_combo)
sr_v1_m = compute_ic_direct(sr_v1)
all_dates = sorted(set(raw_combo_m.index) | set(sr_v1_m.index))
era_edges = np.array_split(np.array(all_dates), 4)
era_labels = [f"era{i+1}_{pd.Timestamp(e[0]).year}-{pd.Timestamp(e[-1]).year}" for i, e in enumerate(era_edges) if len(e)]

era_ic_raw, era_ic_sr = {}, {}
for i, e in enumerate(era_edges):
    if len(e) == 0:
        continue
    lbl = f"era{i+1}_{pd.Timestamp(e[0]).year}-{pd.Timestamp(e[-1]).year}"
    r_vals = raw_combo_m.reindex(e).dropna()
    s_vals = sr_v1_m.reindex(e).dropna()
    era_ic_raw[lbl] = {"ic_mean": float(r_vals.mean()) if len(r_vals) else float("nan"), "n": int(len(r_vals))}
    era_ic_sr[lbl] = {"ic_mean": float(s_vals.mean()) if len(s_vals) else float("nan"), "n": int(len(s_vals))}
    log(f"  {lbl}: RAW ic={era_ic_raw[lbl]['ic_mean']:.4f} (n={era_ic_raw[lbl]['n']})  |  "
        f"SR-v1 ic={era_ic_sr[lbl]['ic_mean']:.4f} (n={era_ic_sr[lbl]['n']})")

raw_era_vals = np.array([v["ic_mean"] for v in era_ic_raw.values() if not np.isnan(v["ic_mean"])])
sr_era_vals = np.array([v["ic_mean"] for v in era_ic_sr.values() if not np.isnan(v["ic_mean"])])
raw_era_std = float(np.nanstd(raw_era_vals, ddof=1)) if len(raw_era_vals) > 1 else float("nan")
sr_era_std = float(np.nanstd(sr_era_vals, ddof=1)) if len(sr_era_vals) > 1 else float("nan")
raw_era_min = float(np.nanmin(raw_era_vals)) if len(raw_era_vals) else float("nan")
sr_era_min = float(np.nanmin(sr_era_vals)) if len(sr_era_vals) else float("nan")
more_robust_era = (sr_era_std < raw_era_std) if not (np.isnan(sr_era_std) or np.isnan(raw_era_std)) else None

log(f"era dispersion: RAW std={raw_era_std:.4f} min={raw_era_min:.4f}  |  "
    f"SR-v1 std={sr_era_std:.4f} min={sr_era_min:.4f}  -> "
    f"{'SR-v1 MORE robust' if more_robust_era else 'RAW MORE (or equally) robust'}")

# ==========================================================================
# WRITE ALL DIAGNOSTIC CARDS
# ==========================================================================
write_json("W6SR_DATA_LINEAGE", lineage)
write_json("W6SR_SANITY_CHECK", {
    "official_reference": {"ic_ir": OFFICIAL_IC_IR, "ic_mean": OFFICIAL_IC_MEAN,
                            "ann_LS": OFFICIAL_ANN_LS, "n_ic_dates": OFFICIAL_N_IC_DATES},
    "rebuilt": {"ic_ir": sanity_ic_ir, "ic_mean": sanity_ic_mean, "ann_LS": sanity_ann_ls,
                "n_ic_dates": sanity_n_dates},
    "sanity_ok": bool(sanity_ok),
})
write_json("W6SR_DSR_LOCAL_VS_GLOBAL", {
    "note": "global counter shared across whole research program (662+ trials before this "
            "script), crushes DSR toward 0 regardless of true skill; local = honest count of "
            "the 3 NEW trials this rebuild made (sanity, v1, v2)",
    "global_trial_count_at_run": card_v1["dsr"]["n_trials"],
    "sanity": {"local_dsr_n3": dsr_local_sanity, "global_dsr": card_sanity["dsr"]},
    "v1_AGraw": {"local_dsr_n3": dsr_local_v1, "global_dsr": card_v1["dsr"]},
    "v2_AGneutral": {"local_dsr_n3": dsr_local_v2, "global_dsr": card_v2["dsr"]},
})
write_json("W6SR_DROPONE", {
    "RAW7": dropone_raw, "SR_v1": dropone_sr,
    "raw_std": raw_dropone_std, "sr_v1_std": sr_dropone_std,
    "raw_range": raw_dropone_range, "sr_v1_range": sr_dropone_range,
    "more_robust": "SR_v1" if more_robust_dropone else "RAW7",
})
write_json("W6SR_ERA", {
    "RAW7": era_ic_raw, "SR_v1": era_ic_sr,
    "raw_std": raw_era_std, "sr_v1_std": sr_era_std,
    "raw_min": raw_era_min, "sr_v1_min": sr_era_min,
    "more_robust": ("SR_v1" if more_robust_era else "RAW7") if more_robust_era is not None else "INCONCLUSIVE",
})
write_json("W6SR_SUMMARY", {
    "sanity": {"ic_ir": sanity_ic_ir, "ann_LS": sanity_ann_ls, "sanity_ok": bool(sanity_ok)},
    "raw7_official": {"ic_ir": OFFICIAL_IC_IR, "ic_mean": OFFICIAL_IC_MEAN, "ann_LS": OFFICIAL_ANN_LS,
                       "turnover": card_sanity["turnover"]["avg_top_decile_turnover"],
                       "net_of_cost_ann_return": card_sanity["costs"]["net_of_cost_ann_return"],
                       "official_verdict_from_CANONICAL_7LEG_1Y_json": "KILL (PBO 0.909 > 0.5)"},
    "sr_v1_AGraw": {"ic_mean": card_v1["ic"]["ic_mean"], "ic_ir": card_v1["ic"]["ic_ir"],
                     "ann_LS": card_v1["long_short"]["ann_return_LS"],
                     "n_ic_dates": card_v1["ic"]["n_ic_dates"],
                     "turnover": card_v1["turnover"]["avg_top_decile_turnover"],
                     "net_of_cost_ann_return": card_v1["costs"]["net_of_cost_ann_return"],
                     "verdict": card_v1["verdict"]},
    "sr_v2_AGneutral": {"ic_mean": card_v2["ic"]["ic_mean"], "ic_ir": card_v2["ic"]["ic_ir"],
                         "ann_LS": card_v2["long_short"]["ann_return_LS"],
                         "n_ic_dates": card_v2["ic"]["n_ic_dates"],
                         "turnover": card_v2["turnover"]["avg_top_decile_turnover"],
                         "net_of_cost_ann_return": card_v2["costs"]["net_of_cost_ann_return"],
                         "verdict": card_v2["verdict"]},
    "audit_reference_full7neutral": {"ic_mean": 0.11323376575711633, "ic_ir": 1.4394182629691228,
                                      "ann_LS": 1.5318342949307846,
                                      "note": "SECTOR_BIAS_AUDIT.md Task 3 COMPOSITE_7LEG neutral -- ALL "
                                              "7 legs sector-neutral (incl. cfo-pat, AG); this rebuild's v1/v2 "
                                              "keep cfo-pat raw per the audit's own leg-priority recommendation, "
                                              "so a small delta from this reference is expected, not an error"},
    "dropone_more_robust": "SR_v1" if more_robust_dropone else "RAW7",
    "era_more_robust": ("SR_v1" if more_robust_era else "RAW7") if more_robust_era is not None else "INCONCLUSIVE",
})

log("DONE. All cards written to " + str(CARDS_DIR))
