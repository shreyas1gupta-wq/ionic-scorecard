"""
test_market_state.py -- M1/M2/M3 validation battery for the market-state /
valuation-breadth layer (WAVE-2 worker, ALPHA_RANKER).

M1 (market-level, TIME SERIES, not cross-sectional): does cheap-market-vs-
   own-history (EY_hist_zscore_expanding) predict the forward MARKET return,
   1Y and 5Y? harness.evaluate() requires a cross-sectional (multi-symbol)
   panel per date to compute Spearman IC -- it does not fit a single market-
   level series. Custom test here mirrors the harness's HARD GATES (lag test
   +1 period, placebo = shuffle the target across dates) applied to a
   univariate time-series correlation instead of a per-date cross-sectional
   IC. PBO/DSR are not computed (advisory-only per task brief; N/A for a
   univariate series in any case).

M2 (cross-sectional, small-cap subset): small-cap-TIER relative valuation ->
   small-cap forward returns. Uses harness.evaluate() directly, panel
   filtered to cap_tier=='small' rows only -- the harness's own per-date
   Spearman IC across ONLY the small-cap names that date IS the tier-relative
   ranking (no separate demeaning needed).

M3 (cross-sectional, full universe, 5Y): per-stock feature = valuation vs its
   OWN cap-tier (that date) + market-state overlay (EY_hist_zscore_expanding,
   broadcast to all names that date). Uses harness.evaluate() at horizon=5Y.

NO LOOKAHEAD: M1's forward market return is the same NIFTY500 NAV series
already used by market_state.py's add_market_vol (through factor_bench),
shifted forward on the NAV's own trading-day index (never re-estimated with
future information). M2/M3 forward returns are panel_long's own
fwd_ret_{1Y,5Y}_raw/resid columns, PIT by construction (see PANEL_SCHEMA.md).
"""
from __future__ import annotations

import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RND = Path(__file__).resolve().parents[1]
ALPHA_ROOT = RND.parent
sys.path.insert(0, str(RND / "lib"))
sys.path.insert(0, str(ALPHA_ROOT / "src" / "lib"))

import harness  # noqa: E402
import factor_bench  # noqa: E402

MARKET_STATE_PATH = RND / "panel" / "market_state.parquet"
STOCK_VAL_PATH = RND / "panel" / "stock_valuation_pit.parquet"
PANEL_LONG_PATH = RND / "panel" / "panel_long.parquet"
CARDS_DIR = RND / "cards"
BACKLOG_SCOUT_PATH = RND / "backlog_scout.json"

HORIZON_TRADING_DAYS = {"1M": 21, "1Y": 252, "5Y": 1260}


# ==========================================================================
# M1 -- market-level time-series test (custom, mirrors harness hard gates)
# ==========================================================================
def _market_fwd_return(horizon: str) -> pd.Series:
    nav = factor_bench.get_series("NIFTY500", "nav").sort_index()
    n = HORIZON_TRADING_DAYS[horizon]
    fwd = nav.shift(-n) / nav - 1.0
    return fwd


def _align_to_market_state_dates(series: pd.Series, ms_dates: pd.Series) -> pd.Series:
    """merge_asof backward: each market_state date gets the nearest prior/exact
    NAV-calendar date's value -- never a future NAV date."""
    s = series.rename("value").reset_index()
    s.columns = ["nav_date", "value"]
    s["nav_date"] = pd.to_datetime(s["nav_date"])
    s = s.sort_values("nav_date")
    d = pd.DataFrame({"date": pd.to_datetime(ms_dates)}).sort_values("date")
    merged = pd.merge_asof(d, s, left_on="date", right_on="nav_date", direction="backward",
                            tolerance=pd.Timedelta(days=10))
    return merged.set_index("date")["value"]


def _spearman(a: pd.Series, b: pd.Series) -> tuple[float, int]:
    m = a.notna() & b.notna()
    if m.sum() < 8:
        return float("nan"), int(m.sum())
    rho, _ = stats.spearmanr(a[m], b[m])
    return float(rho), int(m.sum())


def run_m1(market: pd.DataFrame, horizon: str, factor_col: str = "EY_hist_zscore_expanding",
           n_placebo: int = 200, placebo_seed: int = 42) -> dict:
    market = market.sort_values("date").reset_index(drop=True)
    fwd_full = _market_fwd_return(horizon)
    fwd_aligned = _align_to_market_state_dates(fwd_full, market["date"])
    factor = market.set_index("date")[factor_col]

    rho, n_obs = _spearman(factor, fwd_aligned)

    # lag test: shift factor +1 rebalance period (same convention as harness)
    factor_lag = factor.shift(1)
    rho_lag, _ = _spearman(factor_lag, fwd_aligned)
    lag_delta = (abs(rho_lag - rho) / abs(rho)) if (rho and not np.isnan(rho) and rho != 0
                                                     and not np.isnan(rho_lag)) else float("nan")

    # placebo: shuffle the target across dates, breaking the date alignment
    rng = np.random.default_rng(placebo_seed)
    valid_idx = factor.index[factor.notna() & fwd_aligned.notna()]
    placebo_rhos = []
    for _ in range(n_placebo):
        shuffled_fwd = pd.Series(rng.permutation(fwd_aligned.loc[valid_idx].values), index=valid_idx)
        prho, _ = _spearman(factor.loc[valid_idx], shuffled_fwd)
        if not np.isnan(prho):
            placebo_rhos.append(prho)
    placebo_ic = float(np.mean(placebo_rhos)) if placebo_rhos else float("nan")

    lag_pass = (not np.isnan(lag_delta)) and lag_delta <= 0.25
    placebo_pass = (not np.isnan(placebo_ic)) and abs(placebo_ic) <= 0.02
    hard_gates_pass = bool(lag_pass and placebo_pass)

    card = {
        "factor_id": f"W2_market_M1_{factor_col}_{horizon}",
        "test": "M1_market_ey_vs_history_predicts_market_fwd_return",
        "horizon": horizon,
        "factor_col": factor_col,
        "n_obs": n_obs,
        "spearman_rho": rho,
        "lag_test": {"rho_lag": rho_lag, "lag_test_delta": lag_delta, "pass": lag_pass},
        "placebo": {"placebo_ic": placebo_ic, "n_shuffles": n_placebo, "pass": placebo_pass},
        "hard_gates_pass": hard_gates_pass,
        "pbo_dsr": "N/A -- univariate time-series test, not cross-sectional; PBO/DSR advisory-only per task brief",
        "note": ("custom test, NOT harness.evaluate() -- M1 is a single market-level "
                 "series (no cross-section to rank per date), the harness's per-date "
                 "Spearman-IC machinery does not apply; hard gates (lag+placebo) "
                 "reimplemented with the same logic/thresholds as harness.verdict()."),
        "verdict": ("PROMOTE-CANDIDATE (hard gates clean, |rho|=%.3f)" % abs(rho) if hard_gates_pass and not np.isnan(rho)
                    else "KILL (hard gate fail)" if not hard_gates_pass
                    else "INCONCLUSIVE"),
    }
    return card


# ==========================================================================
# M2 -- small-cap-tier relative valuation -> small-cap forward returns
# ==========================================================================
def run_m2(stock_val: pd.DataFrame, panel_long: pd.DataFrame, horizon: str = "1Y",
           basis: str = "resid", metric: str = "EY") -> dict:
    small = stock_val[stock_val["cap_tier"] == "small"][["date", "symbol", metric]].dropna()
    small = small.rename(columns={metric: "factor"})
    keys = set(zip(small["date"], small["symbol"]))
    pl = panel_long.copy()
    pl["date"] = pd.to_datetime(pl["date"])
    small["date"] = pd.to_datetime(small["date"])
    pl_small = pl[pl.set_index(["date", "symbol"]).index.isin(keys)]
    factor_id = f"W2_market_M2_smallcap_{metric}_{horizon}_{basis}"
    card = harness.evaluate(
        small.set_index(["date", "symbol"])["factor"],
        horizon=horizon, return_basis=basis, factor_id=factor_id,
        panel=pl_small, panel_source="real_panel_long_smallcap_subset",
        family="W2market_M2", write_card=True, cards_dir=CARDS_DIR,
    )
    return card


# ==========================================================================
# M3 -- per-stock 5Y feature: valuation vs cap-tier + market state
# ==========================================================================
def build_m3_factor(stock_val: pd.DataFrame, market: pd.DataFrame, metric: str = "EY") -> pd.Series:
    df = stock_val[["date", "symbol", "cap_tier", metric]].copy()
    df["date"] = pd.to_datetime(df["date"])
    # tier-relative: stock's EY minus the median EY of its OWN cap tier, that date
    # (i.e. cheap relative to size-matched peers, not the whole market at once)
    tier_med = df.groupby(["date", "cap_tier"])[metric].transform("median")
    tier_std = df.groupby(["date", "cap_tier"])[metric].transform("std")
    df["tier_rel_z"] = (df[metric] - tier_med) / tier_std.replace(0, np.nan)

    mkt = market[["date", "EY_hist_zscore_expanding"]].copy()
    mkt["date"] = pd.to_datetime(mkt["date"])
    df = df.merge(mkt, on="date", how="left")
    # composite: both terms use "higher = cheap = bullish" sign convention
    # (EY higher -> cheaper; EY_hist_zscore higher -> market cheap vs its own
    # history). Simple sum, per RESEARCH_PROTOCOL's "rank-average, don't force
    # learned weights" discipline (CONSOLIDATION.md).
    df["m3_factor"] = df["tier_rel_z"] + df["EY_hist_zscore_expanding"]
    return df.set_index(["date", "symbol"])["m3_factor"].dropna()


def run_m3(stock_val: pd.DataFrame, market: pd.DataFrame, panel_long: pd.DataFrame,
           horizon: str = "5Y", basis: str = "resid", metric: str = "EY") -> dict:
    factor = build_m3_factor(stock_val, market, metric)
    pl = panel_long.copy()
    pl["date"] = pd.to_datetime(pl["date"])
    factor_id = f"W2_market_M3_tiervalue_marketstate_{metric}_{horizon}_{basis}"
    card = harness.evaluate(
        factor, horizon=horizon, return_basis=basis, factor_id=factor_id,
        panel=pl, panel_source="real", family="W2market_M3",
        write_card=True, cards_dir=CARDS_DIR,
    )
    return card


def _write_json(obj: dict, path: Path):
    def _native(o):
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        raise TypeError(str(type(o)))
    path.write_text(json.dumps(obj, indent=2, default=_native), encoding="utf-8")


def main():
    market = pd.read_parquet(MARKET_STATE_PATH)
    stock_val = pd.read_parquet(STOCK_VAL_PATH)
    panel_long = pd.read_parquet(PANEL_LONG_PATH)

    results = {}

    for h in ("1Y", "5Y"):
        c = run_m1(market, h)
        _write_json(c, CARDS_DIR / f"{c['factor_id']}.json")
        results[f"M1_{h}"] = c
        print(f"M1 {h}: rho={c['spearman_rho']:.4f} n={c['n_obs']} lag_delta={c['lag_test']['lag_test_delta']} "
              f"placebo={c['placebo']['placebo_ic']:.4f} verdict={c['verdict']}")

    for h in ("1M", "1Y"):
        c = run_m2(stock_val, panel_long, horizon=h)
        results[f"M2_{h}"] = c
        ic = c.get("ic", {})
        print(f"M2 {h}: status={c.get('status')} ic_ir={ic.get('ic_ir')} verdict={c.get('verdict')}")

    for basis in ("raw", "resid"):
        c = run_m3(stock_val, market, panel_long, horizon="5Y", basis=basis)
        results[f"M3_5Y_{basis}"] = c
        ic = c.get("ic", {})
        print(f"M3 5Y {basis}: status={c.get('status')} ic_ir={ic.get('ic_ir')} verdict={c.get('verdict')}")

    (RND / "reports" / "W2_market_state_results.json").write_text(
        json.dumps(results, indent=2, default=str), encoding="utf-8"
    )
    return results


if __name__ == "__main__":
    main()
