"""
S4 -- ABSOLUTE (STANDALONE) scorecard build + evaluation. Owner: Arjun Rao
(Head of Quant, E-004). ALPHA_RANKER. Implements SCORECARD_BLUEPRINT.md Sec 1
(shared foundations) + Sec 3 (ABSOLUTE spec, full) + Sec 3.4 (evaluation
harness) EXACTLY. IMPLEMENTATION task per blueprint Sec 5: no weight search,
no new legs, no fitted P(up), and -- the hard non-goal (Sec 0.1) -- this
NEVER reads, transforms, or is seeded by the RELATIVE score (rel_score_1M/
1Y/5Y.parquet are not imported anywhere in this file).

Core formula (Sec 3.1), applied per (date, symbol, horizon h in {1M,1Y,5Y}):
    E[total_return_h] = (1+g_h)^H x (PE_fair/PE_current) - 1 + H*div_yield
    H = {1M: 1/12, 1Y: 1, 5Y: 5} years.
    div_yield = 0 -- NO dividend-yield PIT source is listed in blueprint Sec
    1.1's data lineage table; the formula labels this term "optional carry"
    and the builder must not add an unspecified data source (Sec 5). Disclosed
    zero-carry simplification, not a silent omission.

(A) g -- expected annual EPS growth (Sec 3.1-A), from `_w6fg2_scored.parquet`:
    trailing_growth = mean(op_growth_t, rev_growth_t), skipna, need >=1 present.
      [MY CALL, J1]: blueprint names both op_growth_t (op-profit/EPS growth)
      and rev_growth_t ("revenue via rev_growth_t") as constituting "trailing"
      without a stated split -- equal-weight mean is the frozen, non-fitted,
      most defensible reading (no economic prior favors one over the other at
      this stage; both are already-validated PIT growth reads).
    forward_proxy = rev_accel, GATED on earnings_confirm_v2==1.
      [MY CALL, J2]: blueprint names "rev_accel/z_accel" for the forward-proxy
      slot. z_accel is a CROSS-SECTIONAL Z-SCORE (unitless, checked: std~1.0,
      range +-26) -- dimensionally incompatible with an additive blend against
      a growth RATE (trailing_growth, checked: median ~10-12%/yr). rev_accel
      is itself rate-scaled (checked: median -1.5%, IQR comparable to
      op/rev_growth_t) so it is the dimensionally sound choice for the g blend;
      z_accel remains reserved for cross-sectional RANKING use (as S1's
      RELATIVE 1M build already does with it), not for this absolute-rate sum.
    g_base = 0.5*trailing_growth + 0.5*forward_proxy   IF earnings_confirm_v2==1
           = trailing_growth                             OTHERWISE (fallback to
             trailing ONLY, per blueprint's explicit text -- NOT 0.5*trailing).
    5Y growth-longevity boost (blueprint: "sub_op_persistent boosts g
    durability specifically at the 5Y horizon"):
      g_5Y_pre_clip = g_base + PERSISTENCE_BOOST_5Y  if sub_op_persistent==1
                    = g_base                           otherwise (incl. NaN)
      [MY CALL, J3]: PERSISTENCE_BOOST_5Y = +0.02 (2pp/yr) is a frozen,
      economically-small, disclosed constant -- not fitted. Applied ONLY at
      5Y (never 1M/1Y), matching the blueprint's explicit horizon-scoping.
    g_h = clip(g_*_pre_clip, g_floor=-0.20, g_cap=0.40)  -- frozen sanity clip,
    Sec 6.5, applied identically at all 3 horizons (the clip itself, not the
    boost, is horizon-invariant).

(B) PE_fair / PE_current (Sec 3.1-B), from `stock_valuation_pit.parquet` +
    `market_state.parquet`:
    PE_current = stock_valuation_pit.PE (per name, PIT).
    own_trailing_PE(t) = per-symbol EXPANDING (causal, min_periods=1) median
      of that symbol's own PE history up to and including t.
    sector_median_PE(t) = cross-sectional median PE within (date, sector) from
      the SAME stock_valuation_pit.parquet.
      [MY CALL, J4]: blueprint text says sector PE comes from
      `sector_context.parquet` / `market_state.PE_by_tier`. Neither file
      actually contains a per-SECTOR PE level (sector_context has
      sec_val_pctile/sec_mom/sec_earn_yoy/sec_breadth, no PE column;
      market_state.PE_by_tier is by CAP TIER, not sector). Computing the
      sector-median PE directly from stock_valuation_pit (same file as
      PE_current, same date, grouped by its own `sector` column) is the
      cleanest, most PIT-honest construction of "sector median PE" available
      on disk, and is what "sector median PE" most literally means. Disclosed
      substitution of data SOURCE for the same named quantity, not a new leg.
    PE_anchor = mean(own_trailing_PE, sector_median_PE), skipna (median of a
      2-element set IS the mean of the two; falls back to whichever of the two
      is present if one is missing, same coverage-fallback pattern as S1's J3).
    band(t) = UNDERVALUED/NEUTRAL/OVERVALUED from richness_index (Sec 1.2,
      market_state.EY_hist_zscore_expanding), merged on date (market_state's
      249 monthly dates match panel_pit's 249 monthly dates exactly).
    regime_multiplier = {UNDERVALUED: 1.10, NEUTRAL: 1.00, OVERVALUED: 0.85}
      (Sec 6.5, frozen). DISCLOSED: richness never crosses 160 in this sample
      (0/226 dates OVERVALUED per market_state -- Sec 1.2's own documented
      empirical gap) -- the 0.85 branch is precautionary, never fires here.
    PE_fair = PE_anchor * regime_multiplier(band).
    rerating_h = clip(PE_fair / PE_current, rr_floor=0.5, rr_cap=2.0).
    rerating is NOT horizon-scaled inside its own ratio (matches the literal
    formula) -- see the WEAKEST-ASSUMPTION discussion in
    S4_ABSOLUTE_REPORT.md Sec "1M mathematical property" for the consequence
    this has on displayed 1M/5Y INTENSITY magnitudes (ranking/quintile
    selection is unaffected -- intensity is a monotone transform of
    E[total_return_h] for fixed H, so portfolio construction is robust to this
    even though the raw magnitude is not directly comparable across horizons).

Presence rule: a (date,symbol,horizon) is SCORED only if g_h AND rerating_h
are both non-null (NaN otherwise -- unscored, not zero, same convention as the
RELATIVE builders).

P(up) lookup (Sec 3.2) -- FROZEN, built ONCE, zero .fit() calls:
    bucket = (tercile(g_h), sign(rerating_h - 1), band)   [3 x 2 x 3 = 18 cells
    per horizon]. g terciles are POOLED cutoffs (33rd/67th percentile of all
    scored g_h values for that horizon), computed once and frozen into
    pup_lookup_v1.parquet's own metadata sidecar (weights_absolute_fragment.
    json) -- NOT recomputed per date.
    P(up)_h[bucket] = fraction of (date,symbol) rows in that bucket with
    realized fwd_ret_h_raw > 0, computed from panel_pit.parquet (survivorship-
    free). Stored as rnd/scorecard/pup_lookup_v1.parquet. At scoring time this
    is a pure merge/lookup -- no refit.
    Coarse P(up) band from the looked-up probability: [MY CALL, J5] fixed
    absolute cutoffs strong-neg<0.35, neg[0.35,0.45), neutral[0.45,0.55),
    pos[0.55,0.65), strong-pos>=0.65 -- frozen, disclosed; NOT relative to each
    horizon's differing base rate (a caveat surfaced explicitly in the report,
    since 5Y's base "up" rate is far above 50% -- FM lens: a coarse band should
    say what the probability actually is, not merely whether it beats the
    horizon's own average).

Determinism: this script's build_everything() is called TWICE; SHA-256 of the
sorted output parquet bytes must match exactly, or the script asserts and
halts. Zero .fit() calls anywhere in the scoring path (the P(up) lookup build
is a one-time frozen computation over historical data, not a live fit -- same
distinction ABSOLUTE_MODEL_STANDALONE.md draws for its own honesty floor).

Run synchronously, foreground, single pass. See S4_ABSOLUTE_REPORT.md for the
portfolio-backtest results, both MANDATORY placebos, verdicts, and the FM lens.
"""
from __future__ import annotations

import hashlib
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
SCORECARD_DIR = THIS.parent                     # ALPHA_RANKER/rnd/scorecard
RND = SCORECARD_DIR.parent                        # ALPHA_RANKER/rnd
ALPHA = RND.parent                                # ALPHA_RANKER

PANEL_PIT_PATH = RND / "panel" / "panel_pit.parquet"
STOCK_VAL_PATH = RND / "panel" / "stock_valuation_pit.parquet"
MARKET_STATE_PATH = RND / "panel" / "market_state.parquet"
W6FG2_PATH = RND / "wave4" / "_w6fg2_scored.parquet"
CUBE_BENCH_LONG_PATH = RND / "panel" / "cube_bench_long.parquet"

OUT_SCORES = SCORECARD_DIR / "absolute_scorecard.parquet"
OUT_PUP_LOOKUP = SCORECARD_DIR / "pup_lookup_v1.parquet"
OUT_WEIGHTS = SCORECARD_DIR / "weights_absolute_fragment.json"
OUT_REPORT = SCORECARD_DIR / "S4_ABSOLUTE_REPORT.md"

HORIZONS = ("1M", "1Y", "5Y")
H_YEARS = {"1M": 1.0 / 12.0, "1Y": 1.0, "5Y": 5.0}

G_FLOOR, G_CAP = -0.20, 0.40                # Sec 6.5, frozen
RR_FLOOR, RR_CAP = 0.5, 2.0                 # Sec 6.5, frozen
REGIME_MULT = {"UNDERVALUED": 1.10, "NEUTRAL": 1.00, "OVERVALUED": 0.85}   # Sec 6.5, frozen
BAND_UNDER, BAND_OVER = 65.0, 160.0         # Sec 1.2, frozen
PERSISTENCE_BOOST_5Y = 0.02                 # J3, frozen, 5Y-only

PUP_BAND_CUTS = [0.35, 0.45, 0.55, 0.65]    # J5, frozen
PUP_BAND_LABELS = ["strong-neg", "neg", "neutral", "pos", "strong-pos"]

MIN_NAMES_PER_DATE = 20                      # harness convention, reused
PLACEBO_SEED = 42
N_PLACEBO_SHUFFLES = 5


def rank_pct(s: pd.Series) -> pd.Series:
    return s.rank(pct=True, method="average")


# ---------------------------------------------------------------------------
# 1. universe grid + forward-return labels (PIT, survivorship-free)
# ---------------------------------------------------------------------------
def load_universe() -> pd.DataFrame:
    cols = ["date", "symbol", "sector", "mktcap_log",
            "fwd_ret_1M_raw", "fwd_ret_1Y_raw", "fwd_ret_5Y_raw"]
    p = pd.read_parquet(PANEL_PIT_PATH, columns=cols)
    p["date"] = pd.to_datetime(p["date"])
    return p.drop_duplicates(["date", "symbol"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 2. g -- expected annual EPS growth (Sec 3.1-A)
# ---------------------------------------------------------------------------
def build_g(universe: pd.DataFrame) -> pd.DataFrame:
    w6 = pd.read_parquet(W6FG2_PATH, columns=[
        "date", "symbol", "available_date", "op_growth_t", "rev_growth_t",
        "rev_accel", "earnings_confirm_v2", "sub_op_persistent"])
    w6["date"] = pd.to_datetime(w6["date"])
    w6["available_date"] = pd.to_datetime(w6["available_date"])

    chk = w6.dropna(subset=["available_date"])
    assert (chk["date"] >= chk["available_date"]).all(), \
        "PIT VIOLATION: _w6fg2_scored.parquet has available_date > date rows"

    m = universe[["date", "symbol"]].merge(w6, on=["date", "symbol"], how="left")

    trailing = m[["op_growth_t", "rev_growth_t"]].mean(axis=1, skipna=True)  # J1
    confirmed = m["earnings_confirm_v2"] == 1.0
    forward_proxy = m["rev_accel"].where(confirmed)                          # J2

    blended = 0.5 * trailing + 0.5 * forward_proxy
    g_base = np.where(confirmed & forward_proxy.notna() & trailing.notna(),
                       blended, trailing)
    g_base = pd.Series(g_base, index=m.index)

    persistent_flag = (m["sub_op_persistent"] == 1.0)                         # J3
    g_5y_pre = g_base + np.where(persistent_flag, PERSISTENCE_BOOST_5Y, 0.0)

    out = m[["date", "symbol"]].copy()
    out["g_1M"] = g_base.clip(G_FLOOR, G_CAP)
    out["g_1Y"] = g_base.clip(G_FLOOR, G_CAP)
    out["g_5Y"] = pd.Series(g_5y_pre, index=m.index).clip(G_FLOOR, G_CAP)
    out["trailing_growth"] = trailing
    out["forward_proxy_confirmed"] = forward_proxy
    out["confirmed_flag"] = confirmed.astype(int)
    out["persistent_flag"] = persistent_flag.astype(int)
    return out


# ---------------------------------------------------------------------------
# 3. PE_fair / PE_current -- the multiple re-rating (Sec 3.1-B)
# ---------------------------------------------------------------------------
def build_rerating(universe: pd.DataFrame) -> pd.DataFrame:
    sv = pd.read_parquet(STOCK_VAL_PATH, columns=["date", "symbol", "sector", "PE", "mktcap"])
    sv["date"] = pd.to_datetime(sv["date"])
    sv = sv.sort_values(["symbol", "date"])

    # own trailing PE, expanding, causal, per symbol
    sv["own_trailing_PE"] = sv.groupby("symbol")["PE"].transform(
        lambda s: s.expanding(min_periods=1).median())

    # sector-median PE, cross-sectional, same date (J4)
    sec_med = sv.groupby(["date", "sector"])["PE"].median().rename("sector_median_PE")
    sv = sv.merge(sec_med, on=["date", "sector"], how="left")

    anchor = sv[["own_trailing_PE", "sector_median_PE"]].mean(axis=1, skipna=True)
    sv["PE_anchor"] = anchor

    ms = pd.read_parquet(MARKET_STATE_PATH, columns=["date", "EY_hist_zscore_expanding"])
    ms["date"] = pd.to_datetime(ms["date"])
    ms["richness_index"] = 100.0 * np.exp(-0.25 * ms["EY_hist_zscore_expanding"])
    ms["band"] = np.select(
        [ms["richness_index"] < BAND_UNDER, ms["richness_index"] >= BAND_OVER],
        ["UNDERVALUED", "OVERVALUED"], default="NEUTRAL")
    ms["regime_multiplier"] = ms["band"].map(REGIME_MULT)

    sv = sv.merge(ms[["date", "richness_index", "band", "regime_multiplier"]],
                  on="date", how="left")

    sv["PE_fair"] = sv["PE_anchor"] * sv["regime_multiplier"]
    raw_rerating = sv["PE_fair"] / sv["PE"]
    sv["rerating"] = raw_rerating.clip(RR_FLOOR, RR_CAP)

    out = universe[["date", "symbol"]].merge(
        sv[["date", "symbol", "PE", "own_trailing_PE", "sector_median_PE",
            "PE_anchor", "band", "regime_multiplier", "PE_fair", "rerating"]],
        on=["date", "symbol"], how="left")
    out = out.rename(columns={"PE": "PE_current"})
    return out


# ---------------------------------------------------------------------------
# 4. combine -> E[total_return_h], intensity_h
# ---------------------------------------------------------------------------
def combine_scores(universe: pd.DataFrame, g_df: pd.DataFrame, rr_df: pd.DataFrame) -> pd.DataFrame:
    df = universe.merge(g_df, on=["date", "symbol"], how="left").merge(
        rr_df, on=["date", "symbol"], how="left")

    rows = []
    for h in HORIZONS:
        H = H_YEARS[h]
        g_h = df[f"g_{h}"]
        rerating = df["rerating"]
        present = g_h.notna() & rerating.notna()
        e_total = (1.0 + g_h) ** H * rerating - 1.0   # div_yield term = 0, disclosed
        e_total = e_total.where(present, np.nan)
        intensity = (1.0 + e_total) ** (1.0 / H) - 1.0
        sub = pd.DataFrame({
            "date": df["date"], "symbol": df["symbol"], "sector": df["sector"],
            "horizon": h, "g": g_h, "rerating": rerating, "band": df["band"],
            "PE_current": df["PE_current"], "PE_fair": df["PE_fair"],
            "E_return": e_total, "intensity": intensity,
            "mktcap_log": df["mktcap_log"],
            "fwd_ret_h_raw": df[f"fwd_ret_{h}_raw"],
            "fwd_ret_1M_raw": df["fwd_ret_1M_raw"],
        })
        rows.append(sub)
    long = pd.concat(rows, ignore_index=True)
    return long


# ---------------------------------------------------------------------------
# 5. P(up) lookup -- FROZEN, built once
# ---------------------------------------------------------------------------
def build_pup_lookup(scored: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    lookup_rows = []
    tercile_cuts = {}
    for h in HORIZONS:
        sub = scored[(scored["horizon"] == h) & scored["g"].notna() &
                     scored["rerating"].notna() & scored["fwd_ret_h_raw"].notna()].copy()
        q1, q2 = sub["g"].quantile([1 / 3, 2 / 3])
        tercile_cuts[h] = {"q1": float(q1), "q2": float(q2)}
        sub["g_tercile"] = np.select(
            [sub["g"] <= q1, sub["g"] <= q2], ["Low", "Mid"], default="High")
        sub["rerating_sign"] = np.where(sub["rerating"] >= 1.0, "Up", "Down")
        grp = sub.groupby(["g_tercile", "rerating_sign", "band"], dropna=False)
        agg = grp["fwd_ret_h_raw"].agg(
            p_up=lambda s: float((s > 0).mean()), n_obs="size").reset_index()
        agg.insert(0, "horizon", h)
        lookup_rows.append(agg)
    lookup = pd.concat(lookup_rows, ignore_index=True)
    lookup["p_up"] = lookup["p_up"].astype(float)
    lookup["n_obs"] = lookup["n_obs"].astype(int)
    return lookup.sort_values(["horizon", "g_tercile", "rerating_sign", "band"]).reset_index(drop=True), tercile_cuts


def pup_band_from_prob(p: float) -> str:
    if pd.isna(p):
        return "unscored"
    for cut, lab in zip(PUP_BAND_CUTS, PUP_BAND_LABELS[:-1]):
        if p < cut:
            return lab
    return PUP_BAND_LABELS[-1]


def apply_pup_lookup(scored: pd.DataFrame, lookup: pd.DataFrame, tercile_cuts: dict) -> pd.DataFrame:
    out = scored.copy()
    out["g_tercile"] = None
    for h, cuts in tercile_cuts.items():
        m = out["horizon"] == h
        out.loc[m, "g_tercile"] = np.select(
            [out.loc[m, "g"] <= cuts["q1"], out.loc[m, "g"] <= cuts["q2"]],
            ["Low", "Mid"], default="High")
    out["rerating_sign"] = np.where(out["rerating"] >= 1.0, "Up", "Down")
    out = out.merge(lookup[["horizon", "g_tercile", "rerating_sign", "band", "p_up", "n_obs"]],
                     on=["horizon", "g_tercile", "rerating_sign", "band"], how="left")
    out["pup_band"] = out["p_up"].apply(pup_band_from_prob)
    out.loc[out["g"].isna() | out["rerating"].isna(), "pup_band"] = "unscored"
    return out


# ---------------------------------------------------------------------------
# 6. full build
# ---------------------------------------------------------------------------
def build_everything() -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    universe = load_universe()
    g_df = build_g(universe)
    rr_df = build_rerating(universe)
    scored_long = combine_scores(universe, g_df, rr_df)
    lookup, tercile_cuts = build_pup_lookup(scored_long)
    final = apply_pup_lookup(scored_long, lookup, tercile_cuts)

    diag = {}
    for h in HORIZONS:
        sub = final[final["horizon"] == h]
        diag[h] = {
            "n_rows": int(len(sub)),
            "n_scored": int(sub["E_return"].notna().sum()),
            "n_dates": int(sub["date"].nunique()),
            "band_counts": sub["band"].value_counts(dropna=False).to_dict(),
            "g_tercile_cuts": tercile_cuts[h],
        }

    out_cols = ["date", "symbol", "sector", "horizon", "E_return", "intensity",
                "pup_band", "g", "rerating", "band", "p_up", "PE_current",
                "PE_fair", "fwd_ret_h_raw", "fwd_ret_1M_raw", "mktcap_log"]
    final_out = final[out_cols].sort_values(["horizon", "date", "symbol"]).reset_index(drop=True)
    return final_out, lookup, tercile_cuts, diag


def _hash_df(df: pd.DataFrame) -> str:
    return hashlib.sha256(pd.util.hash_pandas_object(df, index=True).values.tobytes()
                           + str(df.dtypes.to_dict()).encode()).hexdigest()


def write_weights_fragment(diag: dict, tercile_cuts: dict):
    frag = {
        "horizon_scope": "ALL (1M, 1Y, 5Y) -- absolute scorecard",
        "owner": "Arjun Rao (quant-head-arjun-rao)",
        "built": datetime.now(timezone.utc).isoformat(),
        "standalone_non_goal": "NEVER reads/transforms/is seeded by the RELATIVE score (Blueprint Sec 0.1)",
        "g_floor": G_FLOOR, "g_cap": G_CAP,
        "rr_floor": RR_FLOOR, "rr_cap": RR_CAP,
        "regime_multiplier": REGIME_MULT,
        "band_cutoffs": {"UNDERVALUED_lt": BAND_UNDER, "OVERVALUED_gte": BAND_OVER},
        "persistence_boost_5Y_only": PERSISTENCE_BOOST_5Y,
        "trailing_growth_blend": {"op_growth_t": 0.5, "rev_growth_t": 0.5},
        "g_blend_confirmed": {"trailing": 0.5, "forward_proxy_rev_accel": 0.5},
        "g_fallback_unconfirmed": "trailing_growth only (not blended with 0)",
        "pup_band_cuts": PUP_BAND_CUTS, "pup_band_labels": PUP_BAND_LABELS,
        "pup_g_tercile_cuts_by_horizon": tercile_cuts,
        "div_yield": 0.0,
        "div_yield_note": "No dividend-yield PIT source in Blueprint Sec 1.1 lineage; optional carry term set to 0, disclosed.",
        "judgment_calls": {
            "J1": "trailing_growth = mean(op_growth_t, rev_growth_t), skipna equal-weight -- blueprint names both, no split given.",
            "J2": "forward_proxy = rev_accel (rate-scaled), NOT z_accel (unitless z-score) -- dimensional fit for additive blend against a growth rate.",
            "J3": "PERSISTENCE_BOOST_5Y = +0.02 (2pp/yr), frozen constant, 5Y-only, when sub_op_persistent==1.",
            "J4": "sector-median PE computed directly from stock_valuation_pit.parquet (groupby date,sector), not sector_context.parquet / market_state.PE_by_tier (neither contains a per-sector PE level on disk).",
            "J5": "P(up) coarse-band cutoffs [0.35,0.45,0.55,0.65] are fixed absolute probability levels, not relative to each horizon's differing base 'up' rate.",
        },
        "diagnostics_from_build": diag,
    }
    OUT_WEIGHTS.write_text(json.dumps(frag, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    print("=" * 78)
    print("S4 ABSOLUTE -- build pass 1")
    print("=" * 78)
    scores1, lookup1, cuts1, diag1 = build_everything()
    for h in HORIZONS:
        print(f"[{h}] n_scored={diag1[h]['n_scored']}/{diag1[h]['n_rows']} "
              f"n_dates={diag1[h]['n_dates']} band_counts={diag1[h]['band_counts']} "
              f"g_tercile_cuts={diag1[h]['g_tercile_cuts']}")

    scores1.to_parquet(OUT_SCORES, index=False)
    lookup1.to_parquet(OUT_PUP_LOOKUP, index=False)
    write_weights_fragment(diag1, cuts1)
    print(f"wrote {OUT_SCORES}  rows={len(scores1)}")
    print(f"wrote {OUT_PUP_LOOKUP}  rows={len(lookup1)}")
    print(f"wrote {OUT_WEIGHTS}")
    print("\nP(up) lookup table (frozen):")
    print(lookup1.to_string())

    print("\n" + "=" * 78)
    print("DETERMINISM CHECK -- rebuilding from disk a second time")
    print("=" * 78)
    scores2, lookup2, cuts2, diag2 = build_everything()
    h1s, h2s = _hash_df(scores1), _hash_df(scores2)
    h1l, h2l = _hash_df(lookup1), _hash_df(lookup2)
    eq_scores = scores1.equals(scores2)
    eq_lookup = lookup1.equals(lookup2)
    print(f"scores  hash1={h1s[:16]}...  hash2={h2s[:16]}...  sha256_match={h1s == h2s}  equals={eq_scores}")
    print(f"lookup  hash1={h1l[:16]}...  hash2={h2l[:16]}...  sha256_match={h1l == h2l}  equals={eq_lookup}")
    assert h1s == h2s and eq_scores, "DETERMINISM FAILURE: scores differ across two runs"
    assert h1l == h2l and eq_lookup, "DETERMINISM FAILURE: pup_lookup differs across two runs"
    print("DETERMINISM CHECK: PASS (byte-identical scores AND pup_lookup across two independent rebuilds)")
