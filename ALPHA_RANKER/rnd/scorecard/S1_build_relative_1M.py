"""
S1 -- RELATIVE 1M scorecard build. Owner: Arjun Rao (Quant Head, E-004).
ALPHA_RANKER. Implements SCORECARD_BLUEPRINT.md Sec 1 (shared foundations) +
Sec 2.1 (RELATIVE 1M spec) EXACTLY. This is an IMPLEMENTATION task per
blueprint Sec 5: no weight search, no new legs, no data-source swaps.

Components (each -> cross-sectional rank_pct within date):
  1. mom_1M   -- regime-conditional momentum, SKIP=15 trading days, L=252 (12m)
                 in BOOMING_BULL / NORMAL_CHOPPY (and OTHER/UNCLASSIFIED, a
                 disclosed default -- see JUDGMENT CALLS below). Replaced by
                 the certified rev5d oversold-MR switch under breadth washout
                 (breadth_pctrank_exp <= 0.20).
  2. earn_1M  -- rank_pct(z_accel) from _w6fg2_scored.parquet, gated on
                 earnings_confirm_v2==1; unconfirmed/absent -> neutral 0.5.
  3. qual_floor_1M -- rank_pct(0.5*rank_pct(quality_QMJ) + 0.5*rank_pct(quality_cfo_pat))
                 from capstone_legs.parquet.
  no_neg_news gate -- hard exclusion from no_negative_news_screen.parquet
                 (S6 output, 55-symbol coverage -- see report caveat).

Combine (frozen, NEUTRAL): composite_1M = rank_pct(0.45*mom_1M + 0.40*earn_1M + 0.15*qual_floor_1M)
Combine (frozen, WASHOUT/BEAR_OVERSOLD): 0.55*rev5d + 0.30*earn_1M + 0.15*qual_floor_1M
Final: rel_score_1M = 200*(rank_pct(composite_1M after no_neg_news exclusion) - 0.5)

JUDGMENT CALLS [MY CALL] (disclosed, one-line changes if the Principal rules
differently -- none require a rebuild):
  J1. Blueprint Table A only defines lookback for BOOMING_BULL/NORMAL_CHOPPY/
      BEAR_OVERSOLD. The classifier (reused verbatim from REGIME_SPEC_V2 via
      w5_regime_momentum_horizon.build_regime_panel) also emits OTHER and
      UNCLASSIFIED (the majority of history). Default L=252 (12m) for these
      too -- both defined cells agree on 12m, and NORMAL_CHOPPY is documented
      as "highest-IC cell" in REGIME_SPEC_V2 Table A, so 12m is the safe
      majority default, not a new fitted choice.
  J2. The blueprint's "oversold-extreme override" trigger is stated as the
      pure breadth check (breadth_pctrank_exp <= 0.20, Sec 1.3 WASHOUT), which
      is a SUPERSET of the compound BEAR_OVERSOLD regime tag (which additionally
      requires trend_dir<0). This script uses the literal breadth-only trigger
      for BOTH the mom->rev5d substitution AND the 0.55/0.30/0.15 weight-set
      switch (the blueprint's own text describes these as coinciding: "momentum
      is already suppressed in BEAR_OVERSOLD, so the switch fires exactly where
      momentum says do nothing"). The script logs how often washout fires
      without the compound BEAR_OVERSOLD tag also firing, so the divergence
      (if any) is visible, not silently assumed away.
  J3. qual_floor_1M: quality_cfo_pat has PIT coverage from only 208/249 dates
      (vs 249/249 for quality_QMJ). Where one leg is missing, the inner blend
      falls back to the single available leg (skipna mean) rather than NaN'ing
      the whole quality floor -- a coverage-driven fallback, not a re-weight.
  J4. earn_1M: rank_pct(z_accel) is computed over the FULL cross-section of
      names with a non-null z_accel that date (not restricted to the
      confirmed subset), then names with earnings_confirm_v2 != 1 (including
      absent-from-w6fg2 names) are overwritten to neutral 0.5. This matches
      "rank_pct of z_accel ... gated on ... confirmed" read as: compute the
      rank once, honor it only where confirmed.
  J5. Presence rule: a name-date is scored only if BOTH mom_1M and
      qual_floor_1M are non-null (earn_1M is never null by construction, J4).
      This is the 1M analogue of the canonical model's min-legs presence rule
      (the blueprint's own Sec 2 intro), sized down for a 3-component leg list.
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

sys.path.insert(0, str(RND / "wave4"))
sys.path.insert(0, str(RND / "lib"))

import w5_regime_momentum_horizon as w5rg   # reused: certified regime classifier
import harness                              # reused: shared evaluation harness

PANEL_PIT_PATH = RND / "panel" / "panel_pit.parquet"
CUBE_CLOSE_PATH = RND / "panel" / "cube_close_long.parquet"
CAPSTONE_PATH = RND / "panel" / "capstone_legs.parquet"
W6FG2_PATH = RND / "wave4" / "_w6fg2_scored.parquet"
NO_NEG_NEWS_PATH = RND / "scorecard" / "no_negative_news_screen.parquet"

OUT_SCORES = SCORECARD_DIR / "rel_score_1M.parquet"
OUT_WEIGHTS = SCORECARD_DIR / "weights_1M_fragment.json"
OUT_REPORT = SCORECARD_DIR / "S1_RELATIVE_1M_REPORT.md"

SKIP = 15            # trading days, frozen (blueprint Sec 6.2)
L_MOM = 252          # 12m lookback, BOOMING_BULL/NORMAL_CHOPPY (+ default, J1)
WASHOUT_PCTL = 0.20  # breadth washout threshold (Sec 1.3)

WEIGHTS_NEUTRAL = {"mom": 0.45, "earn": 0.40, "qual": 0.15}
WEIGHTS_WASHOUT = {"mom": 0.55, "earn": 0.30, "qual": 0.15}   # mom slot = rev5d

MIN_NAMES_PER_DATE = 20   # harness default, reused


def rank_pct(s: pd.Series) -> pd.Series:
    return s.rank(pct=True, method="average")


# ---------------------------------------------------------------------------
# 1. universe grid (from panel_pit -- survivorship-free, PIT)
# ---------------------------------------------------------------------------
def load_universe() -> pd.DataFrame:
    p = pd.read_parquet(PANEL_PIT_PATH, columns=["date", "symbol", "sector"])
    p["date"] = pd.to_datetime(p["date"])
    return p.drop_duplicates(["date", "symbol"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 2. mom_1M (skip=15, L=252) + rev5d, fresh from cube_close_long (long history)
# ---------------------------------------------------------------------------
def build_mom_and_rev5d(dates: list) -> pd.DataFrame:
    cube = pd.read_parquet(CUBE_CLOSE_PATH)
    cube.index = pd.to_datetime(cube.index)
    cube = cube.sort_index()
    idx = cube.index
    n = len(idx)
    vals = cube.to_numpy()
    symbols = cube.columns.to_numpy()

    rows = []
    for d in dates:
        loc = idx.get_loc(pd.Timestamp(d))
        i_skip, i_L, i_5d = loc - SKIP, loc - L_MOM, loc - 5
        if i_L < 0 or i_skip < 0 or i_5d < 0:
            continue
        p_now, p_skip, p_L, p_5d = vals[loc], vals[i_skip], vals[i_L], vals[i_5d]
        mom_1M_raw = p_skip / p_L - 1.0                 # cum ret t-L -> t-SKIP
        rev5d = -(p_now / p_5d - 1.0)                    # certified switch, verbatim formula
        df = pd.DataFrame({"symbol": symbols, "mom_1M_raw": mom_1M_raw, "rev5d": rev5d})
        df["date"] = d
        rows.append(df)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(
        columns=["symbol", "mom_1M_raw", "rev5d", "date"])


# ---------------------------------------------------------------------------
# 3. regime tag + washout flag (reused verbatim classifier)
# ---------------------------------------------------------------------------
def build_regime(dates: list) -> pd.DataFrame:
    reg = w5rg.build_regime_panel(dates)   # index=date; cols incl. regime, oversold_extreme, breadth_pctrank_exp
    reg = reg.reset_index().rename(columns={"index": "date"})
    reg["washout"] = reg["breadth_pctrank_exp"] <= WASHOUT_PCTL
    # cross-check: how often does washout diverge from the compound BEAR_OVERSOLD tag (J2)
    reg["bear_oversold_tag"] = reg["regime"] == "BEAR_OVERSOLD"
    return reg[["date", "regime", "washout", "bear_oversold_tag", "breadth_pctrank_exp"]]


# ---------------------------------------------------------------------------
# 4. earn_1M -- rank_pct(z_accel), gated on earnings_confirm_v2==1, PIT
# ---------------------------------------------------------------------------
def build_earn_1M(universe: pd.DataFrame) -> pd.DataFrame:
    w6 = pd.read_parquet(W6FG2_PATH, columns=[
        "date", "symbol", "available_date", "earnings_confirm_v2", "z_accel"])
    w6["date"] = pd.to_datetime(w6["date"])
    w6["available_date"] = pd.to_datetime(w6["available_date"])

    chk = w6.dropna(subset=["available_date"])
    assert (chk["date"] >= chk["available_date"]).all(), \
        "PIT VIOLATION: _w6fg2_scored.parquet has available_date > date rows"

    merged = universe.merge(w6, on=["date", "symbol"], how="left")
    merged["rank_z_accel"] = merged.groupby("date")["z_accel"].transform(rank_pct)
    confirmed = merged["earnings_confirm_v2"] == 1.0
    merged["earn_1M"] = np.where(confirmed, merged["rank_z_accel"], 0.5)
    merged["earn_1M"] = merged["earn_1M"].fillna(0.5)   # absent-from-w6fg2 -> neutral too
    return merged[["date", "symbol", "earn_1M"]]


# ---------------------------------------------------------------------------
# 5. qual_floor_1M -- rank_pct(0.5*rank_pct(QMJ) + 0.5*rank_pct(cfo_pat))
# ---------------------------------------------------------------------------
def build_qual_floor(universe: pd.DataFrame) -> pd.DataFrame:
    cl = pd.read_parquet(CAPSTONE_PATH)
    qmj = cl[cl["leg"] == "quality_QMJ"][["date", "symbol", "value"]].rename(
        columns={"value": "quality_QMJ"})
    cfo = cl[cl["leg"] == "quality_cfo_pat"][["date", "symbol", "value"]].rename(
        columns={"value": "quality_cfo_pat"})
    q = universe.merge(qmj, on=["date", "symbol"], how="left").merge(
        cfo, on=["date", "symbol"], how="left")
    q["r_qmj"] = q.groupby("date")["quality_QMJ"].transform(rank_pct)
    q["r_cfo"] = q.groupby("date")["quality_cfo_pat"].transform(rank_pct)
    inner = q[["r_qmj", "r_cfo"]].mean(axis=1, skipna=True)   # J3 fallback
    q["quality_score_inner"] = inner
    q["qual_floor_1M"] = q.groupby("date")["quality_score_inner"].transform(rank_pct)
    return q[["date", "symbol", "qual_floor_1M"]]


# ---------------------------------------------------------------------------
# 6. no_neg_news gate -- asof (backward) per symbol; missing coverage -> pass
# ---------------------------------------------------------------------------
def build_no_neg_news(universe: pd.DataFrame) -> pd.DataFrame:
    nn = pd.read_parquet(NO_NEG_NEWS_PATH, columns=["date", "symbol", "no_negative_news_flag"])
    nn["date"] = pd.to_datetime(nn["date"])
    nn = nn.sort_values(["symbol", "date"])

    out = []
    covered_symbols = set(nn["symbol"].unique())
    for sym, g in universe.groupby("symbol", sort=False):
        g = g.sort_values("date")
        if sym not in covered_symbols:
            g = g.copy()
            g["no_negative_news_flag"] = True
        else:
            sub = nn[nn["symbol"] == sym][["date", "no_negative_news_flag"]]
            g = pd.merge_asof(g, sub, on="date", direction="backward")
            g["no_negative_news_flag"] = g["no_negative_news_flag"].fillna(True)
        out.append(g)
    res = pd.concat(out, ignore_index=True)
    # NOTE: concatenating a scalar-assigned bool column with a merge_asof'd
    # (possibly object-dtype, post-fillna) column can leave this as dtype
    # object; `~` on an object Series of Python bools does BITWISE not
    # (~True == -2, ~False == -1), not logical negation -- caught by the
    # determinism/diagnostic pass (n_excluded_neg_news==0 was the tell).
    # Force a clean bool dtype before negating.
    flag_bool = res["no_negative_news_flag"].astype(bool)
    res["neg_news_flag"] = (~flag_bool).astype(int)
    return res[["date", "symbol", "neg_news_flag"]]


# ---------------------------------------------------------------------------
# 7. full build
# ---------------------------------------------------------------------------
def build_scores() -> tuple[pd.DataFrame, dict]:
    universe = load_universe()
    dates = sorted(universe["date"].unique())

    mom_df = build_mom_and_rev5d(dates)
    reg_df = build_regime(dates)
    earn_df = build_earn_1M(universe)
    qual_df = build_qual_floor(universe)
    news_df = build_no_neg_news(universe)

    df = universe.merge(mom_df, on=["date", "symbol"], how="left")
    df = df.merge(reg_df, on="date", how="left")
    df = df.merge(earn_df, on=["date", "symbol"], how="left")
    df = df.merge(qual_df, on=["date", "symbol"], how="left")
    df = df.merge(news_df, on=["date", "symbol"], how="left")

    df["mom_slot_raw"] = np.where(df["washout"], df["rev5d"], df["mom_1M_raw"])
    df["mom_1M_component"] = df.groupby("date")["mom_slot_raw"].transform(rank_pct)

    # presence rule (J5): need mom + qual present (earn is never null, J4)
    present = df["mom_1M_component"].notna() & df["qual_floor_1M"].notna()

    w_mom = np.where(df["washout"], WEIGHTS_WASHOUT["mom"], WEIGHTS_NEUTRAL["mom"])
    w_earn = np.where(df["washout"], WEIGHTS_WASHOUT["earn"], WEIGHTS_NEUTRAL["earn"])
    w_qual = np.where(df["washout"], WEIGHTS_WASHOUT["qual"], WEIGHTS_NEUTRAL["qual"])

    weighted = (w_mom * df["mom_1M_component"] + w_earn * df["earn_1M"]
                + w_qual * df["qual_floor_1M"])
    weighted = weighted.where(present, np.nan)

    df["_weighted_sum"] = weighted
    df["composite_1M"] = df.groupby("date")["_weighted_sum"].transform(rank_pct)

    # no_neg_news hard exclusion (post-combine, per blueprint text order)
    df["composite_1M_gated"] = df["composite_1M"].where(df["neg_news_flag"] != 1, np.nan)

    df["rel_score_1M"] = df.groupby("date")["composite_1M_gated"].transform(
        lambda s: 200.0 * (rank_pct(s) - 0.5))

    diag = {
        "n_rows_universe": int(len(df)),
        "n_dates": int(df["date"].nunique()),
        "n_symbols": int(df["symbol"].nunique()),
        "n_scored_final": int(df["rel_score_1M"].notna().sum()),
        "n_excluded_neg_news": int((df["neg_news_flag"] == 1).sum()),
        "n_missing_mom_or_qual": int((~present).sum()),
        "n_washout_rows": int(df["washout"].sum()),
        "n_bear_oversold_tag_rows": int(df["bear_oversold_tag"].sum()),
        "n_washout_not_bear_oversold": int((df["washout"] & ~df["bear_oversold_tag"]).sum()),
        "n_bear_oversold_not_washout": int((df["bear_oversold_tag"] & ~df["washout"]).sum()),
        "regime_counts_by_date": {k: int(v) for k, v in
                                   reg_df.drop_duplicates("date")["regime"].value_counts().items()},
    }
    out_cols = ["date", "symbol", "sector", "regime", "washout",
                "mom_1M_raw", "rev5d", "mom_1M_component", "earn_1M", "qual_floor_1M",
                "neg_news_flag", "composite_1M", "rel_score_1M"]
    return df[out_cols].sort_values(["date", "symbol"]).reset_index(drop=True), diag


def _hash_df(df: pd.DataFrame) -> str:
    return hashlib.sha256(pd.util.hash_pandas_object(df, index=True).values.tobytes()
                           + str(df.dtypes.to_dict()).encode()).hexdigest()


def write_weights_fragment(diag: dict):
    frag = {
        "horizon": "1M",
        "owner": "Arjun Rao (quant-head-arjun-rao)",
        "built": datetime.now(timezone.utc).isoformat(),
        "skip_trading_days": SKIP,
        "lookback_L_trading_days": {"BOOMING_BULL": L_MOM, "NORMAL_CHOPPY": L_MOM,
                                      "BEAR_OVERSOLD": 0, "OTHER_default_J1": L_MOM,
                                      "UNCLASSIFIED_default_J1": L_MOM},
        "washout_breadth_pctrank_threshold": WASHOUT_PCTL,
        "weights_neutral": WEIGHTS_NEUTRAL,
        "weights_washout_bear_oversold": WEIGHTS_WASHOUT,
        "quality_inner_blend": {"quality_QMJ": 0.5, "quality_cfo_pat": 0.5},
        "earn_neutral_fallback_rank": 0.5,
        "rev5d_formula": "-(P(t)/P(t-5) - 1.0), certified REGIME_SPEC_V2 Sec 0",
        "presence_rule": "score requires mom_1M_component AND qual_floor_1M non-null (J5)",
        "no_neg_news_source": str(NO_NEG_NEWS_PATH.relative_to(ALPHA)),
        "no_neg_news_coverage_symbols": 55,
        "no_neg_news_coverage_caveat": (
            "S6 screen covers 55/~750 large-cap names only; the ~445-695 "
            "uncovered names default no_negative_news_flag=True (pass) by "
            "construction -- a coverage gap, NOT a verified clean read."),
        "low_conviction_flag": True,
        "low_conviction_reason": "no 21-yr intra-month confirmation (FINAL_MODEL Sec 5.2); tilt/timing nudge, not a standalone thesis",
        "diagnostics_from_build": diag,
    }
    OUT_WEIGHTS.write_text(json.dumps(frag, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    print("=" * 78)
    print("S1 RELATIVE 1M -- build pass 1")
    print("=" * 78)
    scores1, diag1 = build_scores()
    print(f"rows={len(scores1)} scored_final={diag1['n_scored_final']} "
          f"excluded_neg_news={diag1['n_excluded_neg_news']} "
          f"missing_mom_or_qual={diag1['n_missing_mom_or_qual']}")
    print("regime counts by date:", diag1["regime_counts_by_date"])
    print("washout rows:", diag1["n_washout_rows"],
          "| washout-not-BEAR_OVERSOLD-tag:", diag1["n_washout_not_bear_oversold"],
          "| BEAR_OVERSOLD-tag-not-washout:", diag1["n_bear_oversold_not_washout"])

    scores1.to_parquet(OUT_SCORES, index=False)
    write_weights_fragment(diag1)
    print(f"wrote {OUT_SCORES}")
    print(f"wrote {OUT_WEIGHTS}")

    print("\n" + "=" * 78)
    print("DETERMINISM CHECK -- rebuilding from disk a second time")
    print("=" * 78)
    scores2, diag2 = build_scores()
    h1, h2 = _hash_df(scores1), _hash_df(scores2)
    equal_values = scores1.equals(scores2)
    print(f"hash1={h1[:16]}...  hash2={h2[:16]}...  sha256_match={h1 == h2}  "
          f"dataframe.equals={equal_values}")
    assert h1 == h2 and equal_values, "DETERMINISM FAILURE: two runs differ"
    print("DETERMINISM CHECK: PASS (byte-identical across two independent rebuilds)")
