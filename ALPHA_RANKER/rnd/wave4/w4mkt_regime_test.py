"""
w4mkt_regime_test.py -- WAVE-4 MARKET_REGIME task (Cyrus Daruwalla, macro desk).

Builds a continuous "market richness" index (Principal's fair=100, ~60-70=cheap,
160+=crash-risk exponential-shape intuition) off the ALREADY-VALIDATED
EY_hist_zscore_expanding column in rnd/panel/market_state.parquet (see
W2_market_M1_EY_hist_zscore_expanding_{1Y,5Y}.json -- market-level, hard gates
clean, PROMOTE-CANDIDATE, rho=-0.30/-0.25 vs fwd market return already on file).
This script does NOT recompute EY from scratch -- it repurposes that column
(no lookahead change) into:
  1. richness_index = 100 * exp(-0.25 * EY_hist_zscore_expanding)   [INFERENCE:
     calibration constant 0.25 chosen so a +-2-sigma EY z-score lands at
     ~60-70 / ~160-165, matching the Principal's illustrative band -- a SHAPE
     match, not a fitted parameter (no fwd-return data used to pick 0.25).]
  2. forward-return + forward-drawdown + forward-vol predictive tests (soft,
     Spearman, drop-one / era-split robustness -- NOT t/DSR-gated per task brief).
  3. cross-asset ratios (smallcap/nifty50, smallcap/gold, nifty50/gold) as
     supplementary risk-appetite gauges.
  4. an exposure-scalar backtest: richness-scaled NIFTY500 exposure vs
     always-100%-invested.

NO LOOKAHEAD: all richness values at date t use only EY_hist_zscore_expanding
at t (itself an expanding stat, min_periods=24, already audited in
market_state.py). Forward returns/drawdowns/vol at t look at NAV data AFTER t
(that is the point -- predictive test), never before. Cross-asset ratios are
trailing-only (rolling backward).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RND = Path(__file__).resolve().parents[1]          # ALPHA_RANKER/rnd
ALPHA_ROOT = RND.parent                              # ALPHA_RANKER
sys.path.insert(0, str(RND / "lib"))
sys.path.insert(0, str(ALPHA_ROOT / "src" / "lib"))

import factor_bench  # noqa: E402

MARKET_STATE_PATH = RND / "panel" / "market_state.parquet"
NSE_ALL_IDX_PATH = ALPHA_ROOT.parent / "datasets" / "index_daily" / "nse_official_all_indices.parquet"
GOLD_EXT_PATH = ALPHA_ROOT.parent / "datasets" / "etf_gold_silver" / "goldbees_daily_ext.parquet"
CARDS_DIR = RND / "cards"
OUT_DIR = RND / "wave4"

RICHNESS_SCALE = 0.25  # calibration constant, see module docstring

# Known crash/crisis eras for drop-one / era-split robustness (dates the
# EY-zscore trough / market bottomed, per public record -- GFC low Mar-2009,
# COVID low Mar-2020, 2022 selloff trough mid-2022). market_state.parquet
# itself only starts 2005-04 with EY zscore needing min_periods=24 (i.e.
# usable from ~2007-04), so the 2008 GFC crash IS inside the usable window.
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
# 1. Build richness index
# ---------------------------------------------------------------------------
def build_richness(market: pd.DataFrame) -> pd.DataFrame:
    m = market.sort_values("date").reset_index(drop=True).copy()
    m["date"] = pd.to_datetime(m["date"])
    z = m["EY_hist_zscore_expanding"]
    m["richness_index"] = 100.0 * np.exp(-RICHNESS_SCALE * z)
    return m


# ---------------------------------------------------------------------------
# 2. Forward market return / drawdown / vol (NIFTY500 NAV, no lookahead)
# ---------------------------------------------------------------------------
def load_nav() -> pd.Series:
    nav = factor_bench.get_series("NIFTY500", "nav").sort_index()
    nav.index = pd.to_datetime(nav.index)
    return nav


def fwd_return(nav: pd.Series, n_days: int) -> pd.Series:
    return nav.shift(-n_days) / nav - 1.0


def fwd_max_drawdown(nav: pd.Series, n_days: int) -> pd.Series:
    """Max peak-to-trough drawdown realized WITHIN the forward n_days window
    starting at t (path-risk experienced along the way, measured from each
    window's own running peak -- NOT necessarily from t's price)."""
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


def fwd_worst_return_from_entry(nav: pd.Series, n_days: int) -> pd.Series:
    """Worst mark-to-market loss an investor BUYING AT t would have seen within
    the forward n_days window: min_k(nav[k]/nav[t] - 1). This is the more
    economically relevant 'crash risk if you are exposed at this valuation'
    metric than a within-window running-peak drawdown (which can be diluted
    by a rally happening first)."""
    vals = nav.values
    n = len(vals)
    out = np.full(n, np.nan)
    for i in range(n):
        j = min(i + n_days, n)
        if j - i < 20:
            continue
        window = vals[i:j]
        out[i] = (window / vals[i] - 1.0).min()
    return pd.Series(out, index=nav.index)


def fwd_realized_vol(nav: pd.Series, n_days: int) -> pd.Series:
    ret = nav.pct_change()
    fwd_std = ret.shift(-n_days + 1).rolling(n_days).std().shift(-(n_days - 1))
    # simpler robust approach: compute annualized std of the forward window directly
    vals = ret.values
    n = len(vals)
    out = np.full(n, np.nan)
    for i in range(n):
        j = min(i + n_days, n)
        w = vals[i:j]
        w = w[~np.isnan(w)]
        if len(w) < 20:
            continue
        out[i] = np.std(w) * np.sqrt(252)
    return pd.Series(out, index=nav.index)


def align_to_dates(series: pd.Series, dates: pd.Series) -> pd.Series:
    s = series.rename("value").reset_index()
    s.columns = ["nav_date", "value"]
    s["nav_date"] = pd.to_datetime(s["nav_date"])
    s = s.sort_values("nav_date")
    d = pd.DataFrame({"date": pd.to_datetime(dates)}).sort_values("date")
    merged = pd.merge_asof(d, s, left_on="date", right_on="nav_date", direction="backward",
                            tolerance=pd.Timedelta(days=10))
    return merged.set_index("date")["value"]


def predictive_tests(m: pd.DataFrame, nav: pd.Series) -> dict:
    horizons = {"1Y": 252, "5Y": 1260}
    out = {}
    for hz, ndays in horizons.items():
        fr = align_to_dates(fwd_return(nav, ndays), m["date"])
        dd = align_to_dates(fwd_max_drawdown(nav, ndays), m["date"])
        worst = align_to_dates(fwd_worst_return_from_entry(nav, ndays), m["date"])
        vol = align_to_dates(fwd_realized_vol(nav, ndays), m["date"])
        richness = m.set_index("date")["richness_index"]

        rho_ret, n_ret = spearman(richness, fr)
        rho_dd, n_dd = spearman(richness, dd)   # path-risk metric, from window's own peak
        rho_worst, n_worst = spearman(richness, worst)  # expect NEGATIVE: higher richness -> worse (more negative) entry-drawdown
        rho_vol, n_vol = spearman(richness, vol)

        # drop-one / era-split robustness on the return relationship (the
        # headline claim) -- exclude each crisis era in turn, recompute rho
        drop_one = {}
        for era, (start, end) in ERAS.items():
            mask = ~((m["date"] >= start) & (m["date"] <= end))
            sub_dates = m.loc[mask, "date"]
            r_sub = richness.loc[richness.index.isin(sub_dates)]
            f_sub = fr.loc[fr.index.isin(sub_dates)]
            rho_sub, n_sub = spearman(r_sub, f_sub)
            drop_one[era] = {"rho_excl": rho_sub, "n": n_sub}

        out[hz] = {
            "n_obs": n_ret,
            "rho_richness_vs_fwd_return": rho_ret,
            "rho_richness_vs_fwd_maxdrawdown_from_window_peak": rho_dd,
            "rho_richness_vs_fwd_worst_return_from_entry": rho_worst,
            "rho_richness_vs_fwd_vol": rho_vol,
            "drop_one_era": drop_one,
            "full_sample_rho": rho_ret,
        }
    return out


# ---------------------------------------------------------------------------
# 3. Cross-asset ratios
# ---------------------------------------------------------------------------
def load_cross_asset() -> pd.DataFrame:
    idx = pd.read_parquet(NSE_ALL_IDX_PATH)
    idx["date"] = pd.to_datetime(idx["date"])
    nifty50 = idx[idx["index_name"] == "Nifty 50"][["date", "close"]].rename(columns={"close": "nifty50"})
    smallcap = idx[idx["index_name"] == "NIFTY Smallcap 100"][["date", "close"]].rename(columns={"close": "smallcap100"})

    gold = pd.read_parquet(GOLD_EXT_PATH)[["timestamp", "close"]].rename(columns={"timestamp": "date", "close": "gold"})
    gold["date"] = pd.to_datetime(gold["date"]).dt.tz_localize(None)

    df = nifty50.merge(smallcap, on="date", how="inner").merge(gold, on="date", how="inner")
    df = df.sort_values("date").reset_index(drop=True)
    df["smallcap_nifty50"] = df["smallcap100"] / df["nifty50"]
    df["smallcap_gold"] = df["smallcap100"] / df["gold"]
    df["nifty50_gold"] = df["nifty50"] / df["gold"]
    return df


def cross_asset_predictive(daily: pd.DataFrame, m: pd.DataFrame, nav: pd.Series) -> dict:
    # resample to monthly (month-end) to align with market_state cadence
    monthly = daily.set_index("date").resample("ME").last()
    out = {}
    for ratio_col in ["smallcap_nifty50", "smallcap_gold", "nifty50_gold"]:
        ratio = monthly[ratio_col]
        # trailing 24m z-score (expanding-safe: only past 24m used, rolling not full-sample)
        roll_mean = ratio.rolling(24, min_periods=12).mean()
        roll_std = ratio.rolling(24, min_periods=12).std()
        z = (ratio - roll_mean) / roll_std

        horizons = {"1Y": 252, "5Y": 1260}
        ratio_out = {}
        z_dates = pd.Index(z.index.values, name=None)
        for hz, ndays in horizons.items():
            fr_mkt = align_to_dates(fwd_return(nav, ndays), z_dates)
            fr_small = None
            # smallcap forward return directly, for the smallcap-relevant ratios
            small_nav = monthly["smallcap100"]
            fr_small_full = small_nav.shift(-int(ndays / 21)) / small_nav - 1.0  # monthly-step approx
            rho_mkt, n_mkt = spearman(z, fr_mkt)
            rho_small, n_small = spearman(z, fr_small_full)
            ratio_out[hz] = {
                "rho_vs_fwd_market_return": rho_mkt, "n_mkt": n_mkt,
                "rho_vs_fwd_smallcap_return": rho_small, "n_small": n_small,
            }
        out[ratio_col] = {
            "n_months": int(ratio.notna().sum()),
            "latest_level": float(ratio.dropna().iloc[-1]) if ratio.notna().any() else None,
            "latest_z": float(z.dropna().iloc[-1]) if z.notna().any() else None,
            "predictive": ratio_out,
        }
    return out


# ---------------------------------------------------------------------------
# 4. Exposure-scalar backtest
# ---------------------------------------------------------------------------
def exposure_scalar_backtest(m: pd.DataFrame, nav: pd.Series) -> dict:
    """Monthly-rebalanced exposure scalar, soft/continuous, decreasing in
    richness (richness=100 -> scalar=1.0 'fair value, fully invested').
    TWO variants tested (both against the SAME always-100%-invested NIFTY500
    benchmark, same monthly return path, no costs modeled):
      (a) symmetric  : clip(1 - 0.5*(richness-100)/60, 0.2, 1.4) -- levers up
          when cheap, de-risks when expensive.
      (b) de-risk-only: same formula but capped at 1.0 (no leverage; a
          realistic AMC-book constraint per D-031/032 -- this desk does not
          run levered equity books) -- isolates whether the DE-RISK side
          alone (the crash-avoidance use case this task cares about) helps,
          without the leverage side's separate risk (buying more as valuation
          cheapens DURING an ongoing crash, before the eventual bottom, can
          amplify -- not dampen -- realized drawdown; see MARKET_REGIME.md)."""
    mm = m[["date", "richness_index"]].dropna().sort_values("date").reset_index(drop=True)
    mm["date"] = pd.to_datetime(mm["date"])
    nav_m = nav.resample("ME").last()
    nav_df = nav_m.rename("nav").reset_index()
    nav_df.columns = ["date", "nav"]
    nav_df["mret"] = nav_df["nav"].pct_change()

    merged = pd.merge_asof(mm.sort_values("date"), nav_df.sort_values("date"), on="date",
                            direction="nearest", tolerance=pd.Timedelta(days=20))
    raw_scalar = 1.0 - 0.5 * (merged["richness_index"] - 100.0) / 60.0
    merged["scalar_symmetric"] = raw_scalar.clip(0.2, 1.4)
    merged["scalar_derisk_only"] = raw_scalar.clip(0.2, 1.0)
    # apply THIS month's scalar (known at start of month, from PRIOR month-end
    # richness) to THIS month's forward return -- shift scalar by 1 to avoid
    # using the same month's EY (which itself uses price up to that date) to
    # scale that same month's return
    merged["scalar_symmetric_lag"] = merged["scalar_symmetric"].shift(1)
    merged["scalar_derisk_lag"] = merged["scalar_derisk_only"].shift(1)
    merged = merged.dropna(subset=["mret", "scalar_symmetric_lag", "scalar_derisk_lag"])

    bench_ret = merged["mret"]
    strat_sym = merged["mret"] * merged["scalar_symmetric_lag"]
    strat_derisk = merged["mret"] * merged["scalar_derisk_lag"]

    def stats_block(r: pd.Series) -> dict:
        ann_ret = (1 + r).prod() ** (12 / len(r)) - 1
        ann_vol = r.std() * np.sqrt(12)
        sharpe = ann_ret / ann_vol if ann_vol > 0 else np.nan
        cum = (1 + r).cumprod()
        running_max = cum.cummax()
        dd = (cum - running_max) / running_max
        max_dd = dd.min()
        return {"ann_return": float(ann_ret), "ann_vol": float(ann_vol),
                "sharpe": float(sharpe), "max_drawdown": float(max_dd), "n_months": int(len(r))}

    return {
        "always_invested": stats_block(bench_ret),
        "richness_scaled_symmetric_lever_and_derisk": stats_block(strat_sym),
        "richness_scaled_derisk_only_no_leverage": stats_block(strat_derisk),
        "avg_scalar_symmetric": float(merged["scalar_symmetric_lag"].mean()),
        "avg_scalar_derisk_only": float(merged["scalar_derisk_lag"].mean()),
        "scalar_range_symmetric": [float(merged["scalar_symmetric_lag"].min()), float(merged["scalar_symmetric_lag"].max())],
        "note": "monthly rebalance, scalar known at start of month (prior month-end richness, "
                "lagged by 1 to avoid same-month contamination), no transaction costs modeled "
                "(this is a sizing-value test, not a tradeable strategy claim).",
    }


# ---------------------------------------------------------------------------
def main():
    market = pd.read_parquet(MARKET_STATE_PATH)
    m = build_richness(market)
    nav = load_nav()

    pred = predictive_tests(m, nav)
    cross = None
    try:
        daily = load_cross_asset()
        cross = cross_asset_predictive(daily, m, nav)
    except Exception as e:
        cross = {"error": str(e)}

    expo = exposure_scalar_backtest(m, nav)

    results = {
        "richness_calibration": {"scale_const": RICHNESS_SCALE,
                                  "formula": "100*exp(-0.25*EY_hist_zscore_expanding)"},
        "latest": {
            "date": str(m["date"].iloc[-1].date()),
            "EY_hist_zscore_expanding": float(m["EY_hist_zscore_expanding"].iloc[-1]),
            "richness_index": float(m["richness_index"].iloc[-1]),
        },
        "predictive_tests": pred,
        "cross_asset": cross,
        "exposure_scalar_backtest": expo,
    }
    write_json(results, OUT_DIR / "w4mkt_regime_results.json")
    m[["date", "market_EY_eqw", "EY_hist_zscore_expanding", "richness_index"]].to_csv(
        OUT_DIR / "w4mkt_richness_series.csv", index=False
    )
    print(json.dumps(results, indent=2, default=_native))


if __name__ == "__main__":
    main()
