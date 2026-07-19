"""
W6DC — Downside Capture Ratio (trailing, 1m/3m/6m windows).
Owner: Dr. Sameer Bhat (Overfit & Sensitivity Analyst). Principal request via ALPHA_RANKER.

CONSTRUCT (pre-registered, computed once, not tuned after seeing results):
  At each monthly rebalance date d (panel_long.parquet grid, 249 dates 2005-2026),
  using ONLY trading days <= d (strictly trailing, no lookahead):
    down_days  = {t <= d : market daily log-return(t) < 0}, restricted to the
                 trailing N trading days window (N=21/63/126 for 1m/3m/6m).
    stock_down_cum = exp(sum of stock log-returns over down_days in window) - 1
    mkt_down_cum   = exp(sum of market log-returns over down_days in window) - 1
    downside_capture = stock_down_cum / mkt_down_cum
  <1 = defensive (falls less than market on down days); >1 = amplifies downside.
  Guards (pre-registered BEFORE computing results):
    - min 5 down-days in window else NaN (statistical validity floor)
    - |mkt_down_cum| >= 0.005 else NaN (avoid near-zero-denominator blowup)
  This is a pure O(1)-per-cell vectorized cumsum-diff trick: cumulative sum of
  (log_ret * down_mask) at t minus the same at t-N gives the compounded
  down-day-only return over the trailing N-day window — entirely backward-
  looking, uses only data available at close of date d.

DATA: cube_close_long.parquet (price levels, date x symbol), cube_bench_long.parquet
(NIFTY500 level, date), panel_long.parquet (monthly grid + fwd returns + regime tags),
capstone_legs.parquet (defensive_BAB leg for orthogonality).

OUTPUT: factor parquet (long: date,symbol,window,factor) + evaluate() cards via
rnd/lib/harness.py (the ONE evaluation code path, RESEARCH_PROTOCOL S3) written to
rnd/cards/W6DC_*.json, plus a results digest JSON for the memo.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sstats

THIS = Path(__file__).resolve()
ALPHA_DIR = THIS.parent.parent.parent   # ALPHA_RANKER
sys.path.insert(0, str(ALPHA_DIR / "rnd" / "lib"))
import harness  # noqa: E402

PANEL_DIR = ALPHA_DIR / "rnd" / "panel"
OUT_DIR = THIS.parent / "w6dc_support"
OUT_DIR.mkdir(parents=True, exist_ok=True)

WINDOWS = {"1m": 21, "3m": 63, "6m": 126}
MIN_DOWN_DAYS = 5
MIN_ABS_MKT_DOWN_CUM = 0.005
HORIZONS = ("1M", "1Y", "5Y")
BASIS = "resid"


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------------------
# 1. build downside-capture factor matrices (fully vectorized, trailing-only)
# ---------------------------------------------------------------------------
def _mkt_window_down_cum(bench: pd.Series, window: int) -> pd.Series:
    mkt_log_ret = np.log(bench / bench.shift(1))
    down_mask = (mkt_log_ret < 0).astype(float).where(mkt_log_ret.notna(), np.nan)
    masked = (mkt_log_ret * down_mask).where(mkt_log_ret.notna(), 0.0)
    cum = masked.cumsum()
    window_sum = cum - cum.shift(window)
    return np.exp(window_sum) - 1.0


def build_downside_capture_v2(cube: pd.DataFrame, bench: pd.Series, window: int) -> pd.DataFrame:
    """Corrected: market down-cum is a single scalar SERIES (indexed by date),
    broadcast (divided) into every stock column -- NOT computed per-column."""
    log_ret = np.log(cube / cube.shift(1))
    mkt_log_ret = np.log(bench / bench.shift(1))
    down_mask_mkt = (mkt_log_ret < 0)  # bool Series, NaN->False via comparison (NaN<0 is False)
    down_mask_mkt = down_mask_mkt.where(mkt_log_ret.notna(), other=False)

    valid_stock = log_ret.notna()
    stock_masked = log_ret.where(valid_stock, 0.0).mul(down_mask_mkt.astype(float), axis=0)
    cum_stock = stock_masked.cumsum()
    window_stock = cum_stock - cum_stock.shift(window)
    stock_down_cum = np.exp(window_stock) - 1.0

    mkt_down_cum = _mkt_window_down_cum(bench, window)  # Series indexed by date

    down_count = down_mask_mkt.astype(float).cumsum()
    window_down_count = (down_count - down_count.shift(window))

    valid_count = valid_stock.astype(float).cumsum()
    window_valid_count = valid_count - valid_count.shift(window)

    dc = stock_down_cum.div(mkt_down_cum, axis=0)

    bad_mkt = (window_down_count < MIN_DOWN_DAYS) | (mkt_down_cum.abs() < MIN_ABS_MKT_DOWN_CUM)
    bad = window_valid_count.lt(window)  # require full trailing history for the stock
    bad = bad.apply(lambda col: col | bad_mkt, axis=0) if isinstance(bad, pd.DataFrame) else bad
    dc = dc.where(~bad, np.nan)
    return dc


def main():
    log("loading cube_close_long, cube_bench_long, panel_long, capstone_legs ...")
    cube = pd.read_parquet(PANEL_DIR / "cube_close_long.parquet")
    cube.index = pd.to_datetime(cube.index)
    bench_df = pd.read_parquet(PANEL_DIR / "cube_bench_long.parquet")
    bench_df.index = pd.to_datetime(bench_df.index)
    bench = bench_df["NIFTY500"]
    panel = pd.read_parquet(PANEL_DIR / "panel_long.parquet")
    panel["date"] = pd.to_datetime(panel["date"])
    panel_dates = pd.to_datetime(sorted(panel["date"].unique()))
    legs = pd.read_parquet(PANEL_DIR / "capstone_legs.parquet")
    legs["date"] = pd.to_datetime(legs["date"])

    factors = {}
    for wname, wdays in WINDOWS.items():
        log(f"building downside_capture window={wname} ({wdays}d) ...")
        dc = build_downside_capture_v2(cube, bench, wdays)
        dc_sub = dc.reindex(panel_dates)
        n_valid = dc_sub.notna().sum().sum()
        log(f"  window={wname}: {n_valid} valid (date,symbol) cells on the {len(panel_dates)}-date panel grid")
        factors[wname] = dc_sub
        dc_sub.to_parquet(OUT_DIR / f"w6dc_factor_{wname}.parquet")

    # ---------------------------------------------------------------------
    # evaluate() through the harness, per window x horizon
    # ---------------------------------------------------------------------
    results = {}
    for wname in WINDOWS:
        dc_sub = factors[wname]
        long_f = dc_sub.stack().rename("factor")
        long_f.index.names = ["date", "symbol"]
        for hz in HORIZONS:
            fid = f"W6DC_dcr_{wname}_{hz}"
            card = harness.evaluate(
                long_f, horizon=hz, return_basis=BASIS, factor_id=fid,
                panel=panel, panel_source="real_panel_long_w6dc", family="W6DC",
                cards_dir=harness.CARDS_DIR,
            )
            results[f"{wname}_{hz}"] = card
            log(f"  {fid}: status={card.get('status')} ic_mean={card.get('ic',{}).get('ic_mean')} "
                f"ic_ir={card.get('ic',{}).get('ic_ir')} verdict={card.get('verdict')}")

    # ---------------------------------------------------------------------
    # LS return series (reuse harness internals) for skew + crash-month, 1M horizon
    # ---------------------------------------------------------------------
    ls_diag = {}
    for wname in WINDOWS:
        dc_sub = factors[wname]
        long_f = dc_sub.stack().rename("factor").reset_index()
        long_f.columns = ["date", "symbol", "factor"]
        lbl = harness._label_cols("1M")
        target_col, raw_col = lbl[BASIS], lbl["raw"]
        base_cols = ["date", "symbol", "regime_trend", "regime_vol", "mktcap_log"]
        p = panel[base_cols + [target_col, raw_col]].copy()
        p = p.rename(columns={target_col: "target_eval", raw_col: "target_raw"})
        merged = long_f.merge(p, on=["date", "symbol"], how="inner").dropna(subset=["factor", "target_eval"])
        ls_ret_raw, decile_table, top_sets = harness._decile_stats(merged, min_names=20)
        if len(ls_ret_raw) == 0:
            ls_diag[wname] = {"n": 0}
            continue
        skew = float(sstats.skew(ls_ret_raw.dropna(), bias=False)) if ls_ret_raw.dropna().shape[0] > 2 else float("nan")
        years = ls_ret_raw.index.year
        crash_mean = {}
        for yr in (2020, 2022):
            sub = ls_ret_raw[years == yr]
            crash_mean[str(yr)] = {"mean": float(sub.mean()) if len(sub) else float("nan"), "n": int(len(sub))}
        overall_mean = float(ls_ret_raw.mean())
        # drop-one-year robustness on the IC (not just LS return): recompute
        # ic_mean leaving out each calendar year, report min/max/std across years
        ic_by_year = {}
        merged["yr"] = merged["date"].dt.year
        for yr, g in merged.groupby("yr"):
            if g["date"].nunique() < 3:
                continue
            ic_series = harness._cross_sectional_ic(g, min_names=20).dropna()
            if len(ic_series):
                ic_by_year[int(yr)] = float(ic_series.mean())
        drop_one_year_ic = {}
        all_years = sorted(ic_by_year.keys())
        full_ic_series = harness._cross_sectional_ic(merged, min_names=20).dropna()
        full_ic_mean = float(full_ic_series.mean()) if len(full_ic_series) else float("nan")
        for yr in all_years:
            g_wo = merged[merged["yr"] != yr]
            ic_series_wo = harness._cross_sectional_ic(g_wo, min_names=20).dropna()
            drop_one_year_ic[str(yr)] = float(ic_series_wo.mean()) if len(ic_series_wo) else float("nan")
        drop_vals = [v for v in drop_one_year_ic.values() if not (isinstance(v, float) and np.isnan(v))]
        # half-sample era split
        mid = len(panel_dates) // 2
        first_half_dates = set(panel_dates[:mid])
        second_half_dates = set(panel_dates[mid:])
        g1 = merged[merged["date"].isin(first_half_dates)]
        g2 = merged[merged["date"].isin(second_half_dates)]
        ic1 = harness._cross_sectional_ic(g1, min_names=20).dropna()
        ic2 = harness._cross_sectional_ic(g2, min_names=20).dropna()
        ls_diag[wname] = {
            "n_periods": int(len(ls_ret_raw)),
            "skew": skew,
            "overall_ls_mean": overall_mean,
            "crash_month_mean": crash_mean,
            "full_ic_mean": full_ic_mean,
            "ic_by_year": ic_by_year,
            "drop_one_year_ic": drop_one_year_ic,
            "drop_one_year_ic_range": [float(np.min(drop_vals)), float(np.max(drop_vals))] if drop_vals else None,
            "era_split_ic": {
                "first_half_mean": float(ic1.mean()) if len(ic1) else float("nan"),
                "second_half_mean": float(ic2.mean()) if len(ic2) else float("nan"),
                "first_half_n_dates": int(len(ic1)), "second_half_n_dates": int(len(ic2)),
            },
        }
        log(f"  [{wname}] skew={skew:.3f} crash2020={crash_mean['2020']} crash2022={crash_mean['2022']} "
            f"era_split(first/second)={ls_diag[wname]['era_split_ic']['first_half_mean']:.4f}/"
            f"{ls_diag[wname]['era_split_ic']['second_half_mean']:.4f}")

    # ---------------------------------------------------------------------
    # orthogonality vs BAB leg and vs an independent trailing-vol ("low-vol") leg
    # ---------------------------------------------------------------------
    bab = legs[legs["leg"] == "defensive_BAB"][["date", "symbol", "value"]].rename(columns={"value": "bab"})
    lowvol_src = panel[["date", "symbol", "vol_252"]].copy()
    lowvol_src["lowvol"] = -1.0 * lowvol_src["vol_252"]  # low-vol = negative of trailing realized vol (distinct, simple construction, NOT the BAB leg)

    ortho = {}
    for wname in WINDOWS:
        dc_sub = factors[wname]
        long_f = dc_sub.stack().rename("factor").reset_index()
        long_f.columns = ["date", "symbol", "factor"]
        m_bab = long_f.merge(bab, on=["date", "symbol"], how="inner").dropna()
        m_lv = long_f.merge(lowvol_src[["date", "symbol", "lowvol"]], on=["date", "symbol"], how="inner").dropna()

        def _avg_daily_spearman(m, col):
            def _c(g):
                if len(g) < 20:
                    return np.nan
                rho, _ = sstats.spearmanr(g["factor"], g[col])
                return rho
            s = m.groupby("date").apply(_c, include_groups=False).dropna()
            return float(s.mean()) if len(s) else float("nan"), int(len(s))

        corr_bab, n_bab = _avg_daily_spearman(m_bab, "bab")
        corr_lv, n_lv = _avg_daily_spearman(m_lv, "lowvol")
        ortho[wname] = {"corr_vs_BAB": corr_bab, "n_dates_bab": n_bab,
                         "corr_vs_lowvol_trailingvol": corr_lv, "n_dates_lowvol": n_lv}
        log(f"  [{wname}] corr_vs_BAB={corr_bab:.3f} (n={n_bab})  corr_vs_lowvol={corr_lv:.3f} (n={n_lv})")

    digest = {"windows": list(WINDOWS.keys()), "horizons": list(HORIZONS), "basis": BASIS,
              "min_down_days": MIN_DOWN_DAYS, "min_abs_mkt_down_cum": MIN_ABS_MKT_DOWN_CUM,
              "results_by_window_horizon": {k: {kk: v.get(kk) for kk in
                    ("factor_id", "status", "n_dates", "n_obs", "ic", "deciles", "long_short",
                     "regime_breakdown", "lag_test", "placebo", "dsr", "pbo", "verdict")}
                    for k, v in results.items()},
              "ls_diagnostics": ls_diag, "orthogonality": ortho}
    with open(OUT_DIR / "w6dc_digest.json", "w", encoding="utf-8") as fh:
        json.dump(harness._to_native(digest), fh, indent=2)
    log(f"digest written: {OUT_DIR / 'w6dc_digest.json'}")


if __name__ == "__main__":
    main()
