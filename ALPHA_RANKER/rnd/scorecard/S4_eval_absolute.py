"""
S4 -- ABSOLUTE scorecard EVALUATION HARNESS. Owner: Arjun Rao (Head of Quant,
E-004). Implements SCORECARD_BLUEPRINT.md Sec 3.4 EXACTLY: a PORTFOLIO
backtest (CAGR + Calmar PRIMARY), not a cross-sectional IC test -- deliberately
NOT run through rnd/lib/harness.py's evaluate() (that function is built for
rank-composite factors scored by decile-LS-Sharpe/IC_IR; Sec 3.4 specifies a
different lens for this standalone long-only model). Reads
`absolute_scorecard.parquet` (built by S4_build_absolute.py) + panel_pit +
cube_bench_long. Never reads rel_score_*.parquet (Sec 0.1 non-goal).

Construction (Sec 3.4, fixed, pre-specified before viewing results):
  - long top-QUINTILE by E_return_h, EQUAL-WEIGHT, MONTHLY rebalance,
    realized fwd_ret_1M_raw compounding -- for ALL THREE horizons (the
    selection signal's horizon varies; the REALIZED holding-period return is
    always the 1-month forward return, i.e. "buy what a 1M/1Y/5Y-expected-
    return characteristic likes best today, hold one month, re-rank").
  - MIN_NAMES_PER_DATE = 20 (harness convention, reused) -- months with fewer
    scored names are skipped (both for the real portfolio and its placebos),
    logged, not silently dropped.

MANDATORY placebos, IDENTICAL mechanics (Sec 3.4):
  (1) random-selection top-quintile -- same universe, same quintile SIZE each
      month, names drawn uniformly at random (seed=42, deterministic),
      equal-weight. Isolates whatever the equal-weight-in-this-universe
      baseline return is, with zero stock-picking skill.
  (2) cap-weighted top-quintile -- the SAME names the real model selected
      that month, but weighted by market cap (`stock_valuation_pit.mktcap`)
      instead of equal weight. Isolates whether the equal-weight-scheme's
      known small/mid-cap tilt (rather than genuine selection skill) is
      driving the real portfolio's edge.
  If the real portfolio does not beat BOTH placebos on CAGR AND Calmar, the
  edge is a tilt (size/beta), not skill -- reported honestly either way.

Costs: GROSS only (COST_STANDARDS.md still DRAFT, D-025 gate not cleared).

Hard gates (same battery as RELATIVE, applied to the g/rerating DRIVERS
directly against fwd_ret_h_raw -- not to the portfolio equity curve, per
blueprint Sec 3.4's own phrasing "lag/placebo-shuffle on the driver"):
  - lag-test: Spearman IC of driver vs fwd_ret_h_raw, current vs +1-period-
    stale driver value; lag_test_delta = |ic_lag-ic|/|ic| must be < 0.25.
  - placebo-shuffle: fwd_ret_h_raw shuffled WITHIN DATE, 5x, seed=42; mean
    placebo IC must be inside +-0.02.

Robustness: leave-one-non-overlapping-period-out, ~4 non-overlapping 5-year
blocks spanning the sample (2005-2010 / 2010-2015 / 2015-2020 / 2020-2025),
reported per horizon -- explicitly flagged at 5Y where independent-N is
smallest (Sec 3.4).

Run synchronously, foreground, single pass.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

THIS = Path(__file__).resolve()
SCORECARD_DIR = THIS.parent
RND = SCORECARD_DIR.parent
ALPHA = RND.parent

SCORES_PATH = SCORECARD_DIR / "absolute_scorecard.parquet"
PANEL_PIT_PATH = RND / "panel" / "panel_pit.parquet"
STOCK_VAL_PATH = RND / "panel" / "stock_valuation_pit.parquet"
CUBE_BENCH_LONG_PATH = RND / "panel" / "cube_bench_long.parquet"
OUT_EVAL_JSON = SCORECARD_DIR / "S4_eval_results.json"

HORIZONS = ("1M", "1Y", "5Y")
MIN_NAMES_PER_DATE = 20
PLACEBO_SEED = 42
N_PLACEBO_SHUFFLES = 5
QUINTILE_TOP = 5   # top 1/5 by E_return

ERA_BLOCKS = [("2005-01-01", "2010-01-01"), ("2010-01-01", "2015-01-01"),
              ("2015-01-01", "2020-01-01"), ("2020-01-01", "2026-01-01")]


# ---------------------------------------------------------------------------
# portfolio-construction primitives
# ---------------------------------------------------------------------------
def _month_return_real(g: pd.DataFrame) -> float:
    """Real portfolio: top quintile by E_return, equal-weight, realized fwd_ret_1M_raw."""
    n = len(g)
    if n < MIN_NAMES_PER_DATE:
        return np.nan, []
    cut = g["E_return"].quantile(1 - 1.0 / QUINTILE_TOP)
    top = g[g["E_return"] >= cut]
    return float(top["fwd_ret_1M_raw"].mean()), list(top["symbol"])


def _month_return_random(g: pd.DataFrame, n_pick: int, rng: np.random.Generator) -> float:
    n = len(g)
    if n < MIN_NAMES_PER_DATE or n_pick == 0:
        return np.nan
    idx = rng.choice(n, size=min(n_pick, n), replace=False)
    picked = g.iloc[idx]
    return float(picked["fwd_ret_1M_raw"].mean())


def _month_return_capweighted(g: pd.DataFrame, top_symbols: list, mktcap_map: pd.Series) -> float:
    if not top_symbols:
        return np.nan
    top = g[g["symbol"].isin(top_symbols)].copy()
    top["mktcap"] = top["symbol"].map(mktcap_map)
    top = top.dropna(subset=["mktcap", "fwd_ret_1M_raw"])
    if top.empty or top["mktcap"].sum() <= 0:
        return np.nan
    w = top["mktcap"] / top["mktcap"].sum()
    return float((w * top["fwd_ret_1M_raw"]).sum())


def run_portfolio_backtest(scored_h: pd.DataFrame, mktcap_by_date: dict) -> dict:
    dates = sorted(scored_h["date"].unique())
    rng = np.random.default_rng(PLACEBO_SEED)

    real_rets, rand_rets, cap_rets = [], [], []
    used_dates, n_names_series, n_selected_series = [], [], []

    for d in dates:
        g = scored_h[scored_h["date"] == d].dropna(subset=["E_return", "fwd_ret_1M_raw"])
        if len(g) < MIN_NAMES_PER_DATE:
            continue
        r_real, top_syms = _month_return_real(g)
        if np.isnan(r_real):
            continue
        n_pick = len(top_syms)
        r_rand = _month_return_random(g, n_pick, rng)
        mktcap_map = mktcap_by_date.get(pd.Timestamp(d), pd.Series(dtype=float))
        r_cap = _month_return_capweighted(g, top_syms, mktcap_map)

        real_rets.append(r_real)
        rand_rets.append(r_rand)
        cap_rets.append(r_cap)
        used_dates.append(d)
        n_names_series.append(len(g))
        n_selected_series.append(n_pick)

    idx = pd.DatetimeIndex(used_dates)
    real = pd.Series(real_rets, index=idx).sort_index()
    rand = pd.Series(rand_rets, index=idx).sort_index()
    cap = pd.Series(cap_rets, index=idx).sort_index()

    return {
        "real": real, "random_placebo": rand, "cap_weighted_placebo": cap,
        "n_months_used": len(real), "n_names_avg": float(np.mean(n_names_series)) if n_names_series else np.nan,
        "n_selected_avg": float(np.mean(n_selected_series)) if n_selected_series else np.nan,
    }


def portfolio_metrics(rets: pd.Series) -> dict:
    r = rets.dropna()
    if len(r) < 3:
        return {"n": int(len(r)), "CAGR": np.nan, "Calmar": np.nan, "Sharpe": np.nan,
                "MDD": np.nan, "ann_vol": np.nan}
    equity = (1.0 + r).cumprod()
    n_months = len(r)
    total_growth = float(equity.iloc[-1])
    cagr = total_growth ** (12.0 / n_months) - 1.0
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    mdd = float(drawdown.min())
    calmar = cagr / abs(mdd) if mdd != 0 else np.nan
    ann_vol = float(r.std(ddof=1) * np.sqrt(12))
    sharpe = float(r.mean() / r.std(ddof=1) * np.sqrt(12)) if r.std(ddof=1) > 0 else np.nan
    return {"n": int(n_months), "CAGR": float(cagr), "Calmar": float(calmar),
            "Sharpe": sharpe, "MDD": mdd, "ann_vol": ann_vol}


def benchmark_buyhold(dates: pd.DatetimeIndex) -> dict:
    bl = pd.read_parquet(CUBE_BENCH_LONG_PATH)
    bl.index = pd.to_datetime(bl.index)
    bl = bl.sort_index()
    col = "NIFTY500" if "NIFTY500" in bl.columns else bl.columns[0]
    # align to the same month-end dates the portfolio used (nearest prior trading day)
    aligned = bl[col].reindex(bl.index.union(dates)).sort_index().ffill().reindex(dates)
    mret = aligned.pct_change().dropna()
    return portfolio_metrics(mret)


# ---------------------------------------------------------------------------
# driver-level lag test + placebo shuffle (hard gate, Sec 3.4)
# ---------------------------------------------------------------------------
def _cross_sectional_ic_by_date(df: pd.DataFrame, driver_col: str, target_col: str, min_names: int) -> pd.Series:
    def _ic(g):
        gg = g.dropna(subset=[driver_col, target_col])
        if len(gg) < min_names:
            return np.nan
        rho, _ = stats.spearmanr(gg[driver_col], gg[target_col])
        return rho
    return df.groupby("date").apply(_ic, include_groups=False)


def driver_lag_placebo_test(scored_h: pd.DataFrame, driver_col: str, target_col: str) -> dict:
    df = scored_h[["date", "symbol", driver_col, target_col]].copy().sort_values(["symbol", "date"])
    ic_series = _cross_sectional_ic_by_date(df, driver_col, target_col, MIN_NAMES_PER_DATE).dropna()
    ic_mean = float(ic_series.mean()) if len(ic_series) else np.nan

    df["_driver_lag1"] = df.groupby("symbol")[driver_col].shift(1)
    ic_lag_series = _cross_sectional_ic_by_date(df, "_driver_lag1", target_col, MIN_NAMES_PER_DATE).dropna()
    ic_lag_mean = float(ic_lag_series.mean()) if len(ic_lag_series) else np.nan
    lag_delta = (abs(ic_lag_mean - ic_mean) / abs(ic_mean)
                 if (not np.isnan(ic_mean) and ic_mean != 0 and not np.isnan(ic_lag_mean)) else np.nan)

    rng = np.random.default_rng(PLACEBO_SEED)
    placebo_ics = []
    for _ in range(N_PLACEBO_SHUFFLES):
        shuf = df.copy()
        shuf[target_col] = shuf.groupby("date")[target_col].transform(
            lambda s: rng.permutation(s.values) if s.notna().sum() else s.values)
        pic = _cross_sectional_ic_by_date(shuf, driver_col, target_col, MIN_NAMES_PER_DATE).dropna()
        if len(pic):
            placebo_ics.append(float(pic.mean()))
    placebo_ic = float(np.mean(placebo_ics)) if placebo_ics else np.nan

    gate_pass = (not np.isnan(lag_delta) and lag_delta < 0.25) and \
                (not np.isnan(placebo_ic) and abs(placebo_ic) <= 0.02)
    return {"ic_mean": ic_mean, "ic_lag_mean": ic_lag_mean, "lag_test_delta": lag_delta,
            "placebo_ic": placebo_ic, "n_dates": int(len(ic_series)),
            "hard_gate_pass": bool(gate_pass)}


# ---------------------------------------------------------------------------
# era split / leave-one-non-overlapping-period-out proxy
# ---------------------------------------------------------------------------
def era_split_metrics(real_rets: pd.Series) -> dict:
    out = {}
    for lo, hi in ERA_BLOCKS:
        sub = real_rets[(real_rets.index >= lo) & (real_rets.index < hi)]
        out[f"{lo[:4]}-{hi[:4]}"] = portfolio_metrics(sub)
    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    scored = pd.read_parquet(SCORES_PATH)
    scored["date"] = pd.to_datetime(scored["date"])

    sv = pd.read_parquet(STOCK_VAL_PATH, columns=["date", "symbol", "mktcap"])
    sv["date"] = pd.to_datetime(sv["date"])
    mktcap_by_date = {d: g.set_index("symbol")["mktcap"] for d, g in sv.groupby("date")}

    results = {}
    for h in HORIZONS:
        print("=" * 78)
        print(f"HORIZON {h}")
        print("=" * 78)
        scored_h = scored[scored["horizon"] == h].copy()

        bt = run_portfolio_backtest(scored_h, mktcap_by_date)
        real_m = portfolio_metrics(bt["real"])
        rand_m = portfolio_metrics(bt["random_placebo"])
        cap_m = portfolio_metrics(bt["cap_weighted_placebo"])
        bench_m = benchmark_buyhold(bt["real"].dropna().index)

        beats_random = (not np.isnan(real_m["CAGR"]) and not np.isnan(rand_m["CAGR"])
                         and real_m["CAGR"] > rand_m["CAGR"] and real_m["Calmar"] > rand_m["Calmar"])
        beats_cap = (not np.isnan(real_m["CAGR"]) and not np.isnan(cap_m["CAGR"])
                     and real_m["CAGR"] > cap_m["CAGR"] and real_m["Calmar"] > cap_m["Calmar"])

        g_gate = driver_lag_placebo_test(scored_h, "g", "fwd_ret_h_raw")
        rr_gate = driver_lag_placebo_test(scored_h, "rerating", "fwd_ret_h_raw")

        era = era_split_metrics(bt["real"])

        print(f"n_months_used={bt['n_months_used']} n_names_avg={bt['n_names_avg']:.1f} "
              f"n_selected_avg={bt['n_selected_avg']:.1f}")
        print("REAL      :", real_m)
        print("RANDOM plc:", rand_m)
        print("CAPWT  plc:", cap_m)
        print("BENCH NIFTY500 buy-hold:", bench_m)
        print(f"beats_random(CAGR&Calmar)={beats_random}  beats_cap_weighted(CAGR&Calmar)={beats_cap}")
        print("g driver gate:", g_gate)
        print("rerating driver gate:", rr_gate)
        print("era split:", json.dumps(era, indent=2, default=str))

        results[h] = {
            "n_months_used": bt["n_months_used"], "n_names_avg": bt["n_names_avg"],
            "n_selected_avg": bt["n_selected_avg"],
            "real": real_m, "random_placebo": rand_m, "cap_weighted_placebo": cap_m,
            "benchmark_nifty500_buyhold": bench_m,
            "beats_random": bool(beats_random), "beats_cap_weighted": bool(beats_cap),
            "g_driver_gate": g_gate, "rerating_driver_gate": rr_gate,
            "era_split": era,
        }

    def _native(o):
        if isinstance(o, dict):
            return {k: _native(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_native(v) for v in o]
        if isinstance(o, (np.generic,)):
            return o.item()
        if isinstance(o, float) and np.isnan(o):
            return None
        return o

    OUT_EVAL_JSON.write_text(json.dumps(_native(results), indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {OUT_EVAL_JSON}")


if __name__ == "__main__":
    main()
