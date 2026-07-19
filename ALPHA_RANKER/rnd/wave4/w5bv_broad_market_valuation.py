"""
W5-BV: BROAD-MARKET valuation gauge (Cyrus Daruwalla, macro desk), rebuilding the
market-valuation-band M-term input on a broad-market (equal-weight + breadth) basis
instead of the cap-weighted index-EY the prior pass (`market_state.EY_hist_zscore_expanding`
-> w4mkt_regime_test.py richness_index, `MARKET_REGIME.md`) used.

WHY REBUILD: the prior richness index z-scored `market_EY_eqw` (a single cross-sectional
MEDIAN EY number per date) against its OWN expanding mean/std. That is already
"equal-weight" in the sense of not being cap-weighted, BUT it collapses the entire
cross-section to one number BEFORE any dispersion/breadth information is used, and its
z-score gets permanently compressed by the 2008 outlier sitting in the window forever
(documented in MARKET_REGIME.md #1: observed range 47-122, never reached the Principal's
160 band). This pass adds two things the prior pass did not have:
  1. PER-STOCK valuation-vs-OWN-history percentile (not vs the cross-section, vs itself
     over time) -- multi-metric (EY, PE, PB), composited per stock, THEN the cross-
     sectional level statistic taken as the MEDIAN of those percentiles.
  2. BREADTH: % of the universe sitting in its own top-decile/quintile richest reading
     AT THE SAME TIME -- a fundamentally different signal (synchronized cross-sectional
     froth) that a single aggregate median cannot see (a broad melt-up where everything
     is simultaneously expensive looks identical, in a pure median-EY series, to a
     narrow rally in a few large/liquid names -- breadth disambiguates the two).

NO LOOKAHEAD:
  - Per-stock percentile-vs-own-history is an EXPANDING computation: at date t, stock i's
    percentile uses only {v_i(t') : t' <= t}, min_periods=24 (2yr) monthly observations
    before a reading is emitted (same convention as market_state.py's EY_hist_zscore_expanding
    and EY_hist_pctrank_expanding, min_periods=24).
  - Cross-sectional aggregates (median-of-percentiles, breadth fractions) at date t use only
    stocks with a valid (already-expanding, already-PIT) percentile at t -- no forward info.
  - The final richness index's own z-score is ALSO an expanding stat (own history to date),
    identical discipline to the prior pass, so this file is comparing like-for-like on the
    lookahead axis; the change is in WHAT is being aggregated, not the PIT discipline.
  - Underlying EY/PE/PB per stock/date already PIT (merge_asof backward on available_date),
    inherited unchanged from `market_state.py` / `stock_valuation_pit.parquet`.

Source: `rnd/panel/stock_valuation_pit.parquet` (date, symbol, EY, PE, PB, cap_tier, mktcap).
EV/EBITDA: NOT built. `MASTER_fundamentals_pit.parquet` has "operating profit" (screener.in
convention = EBITDA) and "borrowing(s)" (gross debt) but NO cash/cash-equivalent line item
anywhere in its 34 metrics (confirmed, PANEL_SCHEMA.md's own shares-outstanding search found
none of that class of balance-sheet item either) -- an EV built as mktcap+borrowings with no
cash netted off would systematically OVERSTATE EV for every cash-rich company (common in India:
IT/pharma/FMCG sit on large investment books), a real distortion, not a rounding error. Per
task instruction ("PB/EV-EBITDA where available") and "no fabrication" -- skipped, disclosed,
not silently patched with a fabricated cash assumption. EY+PE+PB is the multi-metric composite.

Outputs:
  rnd/wave4/BROAD_MARKET_VALUATION.md      -- writeup (author fills in after run)
  rnd/wave4/w5bv_broad_richness_series.csv -- the gauge series (date-indexed)
  rnd/panel/w5bv_broad_richness.parquet    -- same, parquet
  rnd/wave4/w5bv_results.json              -- raw predictive-test numbers
  rnd/cards/W5BV_*.json                    -- one per test, firm card convention
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RND = Path(__file__).resolve().parents[1]           # ALPHA_RANKER/rnd
ALPHA_ROOT = RND.parent                              # ALPHA_RANKER
sys.path.insert(0, str(RND / "lib"))
sys.path.insert(0, str(ALPHA_ROOT / "src" / "lib"))

import factor_bench  # noqa: E402

STOCK_VAL_PATH = RND / "panel" / "stock_valuation_pit.parquet"
MARKET_STATE_PATH = RND / "panel" / "market_state.parquet"
OLD_RICHNESS_CSV = RND / "wave4" / "w4mkt_richness_series.csv"
CARDS_DIR = RND / "cards"
OUT_DIR = RND / "wave4"
OUT_PANEL_DIR = RND / "panel"

MIN_PERIODS_OWN_HIST = 24   # 2yr of monthly obs before a per-stock percentile is trusted
K_SHAPE = 0.2351            # solves 100*exp(2*k)=160 -> ±2sigma combined_z maps to ~62.6/160,
                             # a SHAPE match to the Principal's illustrative bands, picked from
                             # the band numbers themselves -- NOT fit to any forward-return data.
ERAS = {
    "2008_GFC": ("2007-09-01", "2009-06-30"),
    "2020_COVID": ("2020-01-01", "2020-12-31"),
    "2022_SELLOFF": ("2022-01-01", "2022-12-31"),
}


def _native(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o.date())
    raise TypeError(str(type(o)))


def write_json(obj: dict, path: Path):
    path.write_text(json.dumps(obj, indent=2, default=_native), encoding="utf-8")


def spearman(a: pd.Series, b: pd.Series) -> tuple[float, int]:
    m = a.notna() & b.notna()
    if m.sum() < 8:
        return float("nan"), int(m.sum())
    rho, _ = stats.spearmanr(a[m], b[m])
    return float(rho), int(m.sum())


# ---------------------------------------------------------------------------
# 1. Per-stock expanding percentile-vs-own-history (vectorized, no lookahead)
# ---------------------------------------------------------------------------
def expanding_pctrank_matrix(values: np.ndarray, min_periods: int) -> np.ndarray:
    """values: 1D array, chronological order (one stock's time series, possibly
    with NaN gaps). Returns, at each index t, the fraction of {values[0..t] that
    are non-NaN} which are <= values[t] -- i.e. this observation's percentile
    rank WITHIN ITS OWN HISTORY UP TO AND INCLUDING t. NaN until >= min_periods
    non-NaN observations exist up to and including t. O(T^2) per stock via a
    single broadcast compare (T <= ~250 monthly obs for this dataset -- cheap)."""
    T = len(values)
    out = np.full(T, np.nan)
    valid = ~np.isnan(values)
    if valid.sum() < min_periods:
        return out
    # lower-triangular compare: comp[t, i] = 1 if values[i] <= values[t] and i <= t
    v = values
    cmp = v[None, :] <= v[:, None]          # cmp[t, i] = values[i] <= values[t]
    tri = np.tril(np.ones((T, T), dtype=bool))
    valid_i = valid[None, :] & tri           # only count valid, i<=t entries
    count_le = (cmp & valid_i).sum(axis=1)
    count_valid = valid_i.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        pct = count_le / count_valid
    pct[count_valid < min_periods] = np.nan
    pct[~valid] = np.nan
    return pct


def build_stock_percentiles(stock_val: pd.DataFrame) -> pd.DataFrame:
    """For each of EY, PE, PB: per-stock expanding percentile-of-EXPENSIVENESS
    (0=cheapest-ever-for-this-stock, 1=richest-ever-for-this-stock), inverted
    for EY (high EY = cheap, so expensiveness_pctile_EY = 1 - pctrank(EY))."""
    df = stock_val.sort_values(["symbol", "date"]).reset_index(drop=True)
    out_frames = []
    for sym, g in df.groupby("symbol", sort=False):
        g = g.sort_values("date")
        row = {"date": g["date"].values, "symbol": sym}
        ey = g["EY"].to_numpy(dtype=float)
        pe = g["PE"].to_numpy(dtype=float)
        pb = g["PB"].to_numpy(dtype=float)
        pct_ey = expanding_pctrank_matrix(ey, MIN_PERIODS_OWN_HIST)
        pct_pe = expanding_pctrank_matrix(pe, MIN_PERIODS_OWN_HIST)
        pct_pb = expanding_pctrank_matrix(pb, MIN_PERIODS_OWN_HIST)
        row["expensive_pctile_EY"] = 1.0 - pct_ey   # high EY=cheap -> invert
        row["expensive_pctile_PE"] = pct_pe          # high PE=expensive -> as-is
        row["expensive_pctile_PB"] = pct_pb          # high PB=expensive -> as-is
        out_frames.append(pd.DataFrame(row))
    result = pd.concat(out_frames, ignore_index=True)
    result["composite_expensive_pctile"] = result[
        ["expensive_pctile_EY", "expensive_pctile_PE", "expensive_pctile_PB"]
    ].median(axis=1, skipna=True)
    n_metrics_avail = result[
        ["expensive_pctile_EY", "expensive_pctile_PE", "expensive_pctile_PB"]
    ].notna().sum(axis=1)
    result.loc[n_metrics_avail == 0, "composite_expensive_pctile"] = np.nan
    result["n_metrics_avail"] = n_metrics_avail
    return result


# ---------------------------------------------------------------------------
# 2. Cross-sectional aggregation: level + breadth
# ---------------------------------------------------------------------------
def aggregate_broad_market(stock_pct: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for date, g in stock_pct.groupby("date"):
        c = g["composite_expensive_pctile"].dropna()
        row = {
            "date": date,
            "n_valid": len(c),
            "broad_median_pctile": c.median() if len(c) >= 20 else np.nan,
            "breadth_top_decile": (c >= 0.90).mean() if len(c) >= 20 else np.nan,
            "breadth_top_quintile": (c >= 0.80).mean() if len(c) >= 20 else np.nan,
            "breadth_bottom_decile": (c <= 0.10).mean() if len(c) >= 20 else np.nan,
            "breadth_bottom_quintile": (c <= 0.20).mean() if len(c) >= 20 else np.nan,
        }
        rows.append(row)
    out = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    return out


def build_richness(market: pd.DataFrame) -> pd.DataFrame:
    m = market.sort_values("date").reset_index(drop=True).copy()
    m["date"] = pd.to_datetime(m["date"])
    for col in ["broad_median_pctile", "breadth_top_quintile"]:
        exp_mean = m[col].expanding(min_periods=MIN_PERIODS_OWN_HIST).mean()
        exp_std = m[col].expanding(min_periods=MIN_PERIODS_OWN_HIST).std()
        m[f"z_{col}"] = (m[col] - exp_mean) / exp_std
    # combined_z: equal-weight average of the two z-scores (EXPLICIT choice,
    # not fit) -- level (how rich is the typical stock vs its own history) and
    # breadth (how synchronized is that richness across the universe) are
    # deliberately given equal say; require BOTH available (else the combined
    # signal quietly degrades to a 1-input z on days one side is still warming up).
    m["combined_z"] = m[["z_broad_median_pctile", "z_breadth_top_quintile"]].mean(axis=1, skipna=False)
    m["broad_richness_index"] = 100.0 * np.exp(K_SHAPE * m["combined_z"])
    return m


# ---------------------------------------------------------------------------
# 3. Predictive tests (reusing w4mkt_regime_test.py's forward-return/dd/vol machinery)
# ---------------------------------------------------------------------------
def load_nav() -> pd.Series:
    nav = factor_bench.get_series("NIFTY500", "nav").sort_index()
    nav.index = pd.to_datetime(nav.index)
    return nav


def fwd_return(nav: pd.Series, n_days: int) -> pd.Series:
    return nav.shift(-n_days) / nav - 1.0


def fwd_max_drawdown(nav: pd.Series, n_days: int) -> pd.Series:
    vals = nav.values
    n = len(vals)
    out = np.full(n, np.nan)
    for i in range(n):
        j = min(i + n_days, n)
        if j - i < 20:
            continue
        window = vals[i:j]
        running_max = np.maximum.accumulate(window)
        dd = (window - running_max) / running_max
        out[i] = dd.min()
    return pd.Series(out, index=nav.index)


def align_to_dates(series: pd.Series, dates) -> pd.Series:
    s = series.rename("value").reset_index()
    s.columns = ["nav_date", "value"]
    s["nav_date"] = pd.to_datetime(s["nav_date"])
    s = s.sort_values("nav_date")
    d = pd.DataFrame({"date": pd.to_datetime(pd.Index(dates))}).sort_values("date")
    merged = pd.merge_asof(d, s, left_on="date", right_on="nav_date", direction="backward",
                            tolerance=pd.Timedelta(days=10))
    return merged.set_index("date")["value"]


def predictive_tests(m: pd.DataFrame, nav: pd.Series, richness_col: str) -> dict:
    horizons = {"1Y": 252, "5Y": 1260}
    out = {}
    richness = m.set_index("date")[richness_col]
    for hz, ndays in horizons.items():
        fr = align_to_dates(fwd_return(nav, ndays), m["date"])
        dd = align_to_dates(fwd_max_drawdown(nav, ndays), m["date"])

        rho_ret, n_ret = spearman(richness, fr)
        rho_dd, n_dd = spearman(richness, dd)

        drop_one = {}
        for era, (start, end) in ERAS.items():
            mask = ~((m["date"] >= start) & (m["date"] <= end))
            sub_dates = m.loc[mask, "date"]
            r_sub = richness.loc[richness.index.isin(sub_dates)]
            f_sub = fr.loc[fr.index.isin(sub_dates)]
            rho_sub, n_sub = spearman(r_sub, f_sub)
            drop_one[era] = {"rho_excl": rho_sub, "n": n_sub}

        # boundary test: is being BELOW 65 vs BELOW 80 differently predictive of
        # a POSITIVE forward return (sign-only, no magnitude claim)
        boundary = {}
        for b in (65, 80):
            below = richness < b
            if below.sum() >= 8:
                sub_fr = fr.loc[richness.index[below]]
                boundary[f"below_{b}"] = {
                    "n": int(below.sum()),
                    "mean_fwd_return": float(sub_fr.mean()) if sub_fr.notna().sum() else float("nan"),
                    "pct_positive": float((sub_fr.dropna() > 0).mean()) if sub_fr.notna().sum() else float("nan"),
                }
            else:
                boundary[f"below_{b}"] = {"n": int(below.sum()), "mean_fwd_return": None, "pct_positive": None}
        above160 = richness >= 160
        if above160.sum() >= 8:
            sub_fr = fr.loc[richness.index[above160]]
            boundary["above_160"] = {
                "n": int(above160.sum()),
                "mean_fwd_return": float(sub_fr.mean()) if sub_fr.notna().sum() else float("nan"),
                "pct_positive": float((sub_fr.dropna() > 0).mean()) if sub_fr.notna().sum() else float("nan"),
            }
        else:
            boundary["above_160"] = {"n": int(above160.sum()), "mean_fwd_return": None, "pct_positive": None}

        out[hz] = {
            "n_obs": n_ret,
            "rho_richness_vs_fwd_return": rho_ret,
            "rho_richness_vs_fwd_maxdrawdown_from_window_peak": rho_dd,
            "drop_one_era": drop_one,
            "boundary_tests": boundary,
        }
    return out


def era_split(m: pd.DataFrame, nav: pd.Series, richness_col: str) -> dict:
    """First-half vs second-half of the gauge's OWN valid date range, sign check."""
    valid = m.dropna(subset=[richness_col])
    if len(valid) < 40:
        return {}
    mid = valid["date"].iloc[len(valid) // 2]
    out = {}
    for hz, ndays in {"1Y": 252, "5Y": 1260}.items():
        fr = align_to_dates(fwd_return(nav, ndays), valid["date"])
        richness = valid.set_index("date")[richness_col]
        first = valid[valid["date"] < mid]["date"]
        second = valid[valid["date"] >= mid]["date"]
        rho1, n1 = spearman(richness.loc[richness.index.isin(first)], fr.loc[fr.index.isin(first)])
        rho2, n2 = spearman(richness.loc[richness.index.isin(second)], fr.loc[fr.index.isin(second)])
        out[hz] = {"first_half": {"rho": rho1, "n": n1}, "second_half": {"rho": rho2, "n": n2}, "split_date": str(mid.date())}
    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    print("=== loading stock_valuation_pit.parquet ===")
    stock_val = pd.read_parquet(STOCK_VAL_PATH, columns=["date", "symbol", "EY", "PE", "PB"])
    stock_val["date"] = pd.to_datetime(stock_val["date"])
    print(stock_val.shape, stock_val["date"].min(), stock_val["date"].max())

    print("=== per-stock expanding percentile-vs-own-history (this is O(T^2) per stock, ~800-1200 symbols) ===")
    stock_pct = build_stock_percentiles(stock_val)
    print("stock_pct rows:", len(stock_pct), "non-null composite:", stock_pct["composite_expensive_pctile"].notna().sum())

    print("=== cross-sectional aggregation (level + breadth) ===")
    market = aggregate_broad_market(stock_pct)
    print(market.tail(10).to_string())

    print("=== richness index (combined level+breadth z, shape-matched exp constant) ===")
    market = build_richness(market)
    print(market[["date", "n_valid", "broad_median_pctile", "breadth_top_quintile", "combined_z", "broad_richness_index"]].describe())

    # persist gauge series
    market.to_csv(OUT_DIR / "w5bv_broad_richness_series.csv", index=False)
    market.to_parquet(OUT_PANEL_DIR / "w5bv_broad_richness.parquet", index=False)
    stock_pct.to_parquet(OUT_PANEL_DIR / "w5bv_stock_percentiles.parquet", index=False)

    rng = market["broad_richness_index"].dropna()
    print(f"\n=== OBSERVED RANGE: min={rng.min():.1f} max={rng.max():.1f} n={len(rng)} ===")
    print("min date:", market.loc[market['broad_richness_index'].idxmin(), 'date'] if len(rng) else None)
    print("max date:", market.loc[market['broad_richness_index'].idxmax(), 'date'] if len(rng) else None)
    crosses_below_80 = (rng < 80).sum()
    crosses_below_65 = (rng < 65).sum()
    crosses_above_160 = (rng >= 160).sum()
    print(f"months <80: {crosses_below_80}, months <65: {crosses_below_65}, months >=160: {crosses_above_160}")

    # known episode readings
    episodes = {}
    for label, (s, e) in {
        "2008_GFC": ("2008-01-01", "2009-06-30"),
        "2017_2018_smallmid_froth": ("2017-06-01", "2018-03-31"),
        "2020_COVID_trough": ("2020-02-01", "2020-05-31"),
        "2024_froth": ("2024-01-01", "2024-12-31"),
    }.items():
        sub = market[(market["date"] >= s) & (market["date"] <= e)]
        episodes[label] = {
            "n_months": int(len(sub)),
            "min_richness": float(sub["broad_richness_index"].min()) if len(sub) else None,
            "max_richness": float(sub["broad_richness_index"].max()) if len(sub) else None,
            "mean_richness": float(sub["broad_richness_index"].mean()) if sub["broad_richness_index"].notna().any() else None,
            "min_n_valid_stocks": float(sub["n_valid"].min()) if len(sub) else None,
        }
        print(label, episodes[label])

    print("\n=== predictive tests vs forward NIFTY500 returns/drawdown ===")
    nav = load_nav()
    pred = predictive_tests(market, nav, "broad_richness_index")
    print(json.dumps(pred, indent=2, default=_native))

    print("\n=== era-split (own valid-range first-half vs second-half) ===")
    era = era_split(market, nav, "broad_richness_index")
    print(json.dumps(era, indent=2, default=_native))

    print("\n=== contrast vs OLD cap-weighted-adjacent (market_EY_eqw z-score) richness index ===")
    old = pd.read_csv(OLD_RICHNESS_CSV, parse_dates=["date"])
    ms = pd.read_parquet(MARKET_STATE_PATH, columns=["date", "market_EY_capw", "market_EY_eqw"])
    ms["date"] = pd.to_datetime(ms["date"])
    cmp_df = market[["date", "broad_richness_index"]].merge(
        old[["date", "richness_index"]].rename(columns={"richness_index": "old_richness_index"}),
        on="date", how="inner",
    ).merge(ms, on="date", how="left")
    rho_old_new, n_cmp = spearman(cmp_df["broad_richness_index"], cmp_df["old_richness_index"])
    print(f"Spearman(new broad richness, old EY-eqw-zscore richness): rho={rho_old_new:.3f} n={n_cmp}")
    # divergence episodes: where new is high (>quantile 0.8) but old is low (<quantile 0.5) or vice versa
    cmp_df["new_pct"] = cmp_df["broad_richness_index"].rank(pct=True)
    cmp_df["old_pct"] = cmp_df["old_richness_index"].rank(pct=True)
    cmp_df["divergence"] = cmp_df["new_pct"] - cmp_df["old_pct"]
    top_diverge = cmp_df.reindex(cmp_df["divergence"].abs().sort_values(ascending=False).index).head(15)
    print(top_diverge[["date", "broad_richness_index", "old_richness_index", "new_pct", "old_pct", "divergence"]].to_string())

    # also raw cap-weighted-vs-eqw-EY divergence check (the Principal's literal "masking" claim)
    ms["capw_minus_eqw_EY"] = ms["market_EY_capw"] - ms["market_EY_eqw"]
    print("\ncapw EY - eqw EY (positive = cap-weighted index LOOKS CHEAPER than broad market):")
    print(ms[["date", "market_EY_capw", "market_EY_eqw", "capw_minus_eqw_EY"]].describe())
    print(ms.tail(5).to_string())

    # ---------------- persist everything ----------------
    results = {
        "observed_range": {"min": float(rng.min()), "max": float(rng.max()), "n": int(len(rng)),
                             "min_date": str(market.loc[market['broad_richness_index'].idxmin(), 'date'].date()),
                             "max_date": str(market.loc[market['broad_richness_index'].idxmax(), 'date'].date())},
        "months_below_80": int(crosses_below_80),
        "months_below_65": int(crosses_below_65),
        "months_above_160": int(crosses_above_160),
        "episodes": episodes,
        "predictive_tests": pred,
        "era_split": era,
        "corr_vs_old_richness": {"rho": rho_old_new, "n": n_cmp},
        "capw_minus_eqw_EY_summary": {
            "mean": float(ms["capw_minus_eqw_EY"].mean()),
            "median": float(ms["capw_minus_eqw_EY"].median()),
            "latest": float(ms["capw_minus_eqw_EY"].iloc[-1]),
            "latest_date": str(ms["date"].iloc[-1].date()),
        },
        "fundamentals_pre2012_caveat": "MASTER_fundamentals_pit.parquet has <110 symbols/year before 2012 "
                                        "(vs 1400-2300+ from 2012 on) -- 2008 GFC-era readings in this gauge "
                                        "rest on a thin, likely-survivorship-biased fundamentals cross-section; "
                                        "flagged, not smoothed over.",
    }
    write_json(results, OUT_DIR / "w5bv_results.json")

    for name, payload in [
        ("W5BV_observed_range", {"metric": "broad_richness_index range", **results["observed_range"],
                                   "months_below_80": crosses_below_80, "months_below_65": crosses_below_65,
                                   "months_above_160": crosses_above_160}),
        ("W5BV_episodes", episodes),
        ("W5BV_predictive_1Y", pred.get("1Y", {})),
        ("W5BV_predictive_5Y", pred.get("5Y", {})),
        ("W5BV_era_split", era),
        ("W5BV_vs_old_richness_corr", {"rho": rho_old_new, "n": n_cmp}),
    ]:
        write_json(payload, CARDS_DIR / f"{name}.json")

    print("\n=== DONE. Outputs written. ===")


if __name__ == "__main__":
    main()
