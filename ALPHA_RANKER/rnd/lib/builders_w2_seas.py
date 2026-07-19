"""
ALPHA_RANKER WAVE worker — seasonality + value-quality composite builders.
Owner: WAVE worker session, ALPHA_RANKER research loop. Never touches weights.

Hypotheses (rnd/backlog_scout.json):
  IDG-G-10  cross-sectional return seasonality (Heston-Sadka)      -- 1M, panel_long
  IDG-G-13  Lynch GARP / PEG                                        -- 1Y, panel_long
  IDG-G-14  earnings stability (inverse CoV of net-profit growth)   -- 1Y, panel_long
  IDG-I-05  Kedia SMILE small-tier composite                        -- 1Y, panel_long
  IDG-G-11  Greenblatt magic formula -- ALREADY BUILT as H018 (builders_value.py
            build_H018_greenblatt) and ALREADY EVALUATED (rnd/cards/H018_greenblatt.json,
            scoreboard_v2 verdict WEAK, net_LS_v2 negative) -- NOT rebuilt here, see
            rnd/reports/W2S_SEAS_COMPOSITE.md for the comparison vs H014 (EY-alone).

Data:
  - rnd/panel/panel_long.parquet          21yr month-end PIT panel (2005-04 -> 2025-12).
  - rnd/panel/stock_valuation_pit.parquet  SAME (date,symbol) grain as panel_long (148,297
    rows, verified identical row count) -- EXACT merge (not asof) is valid and used for
    cap_tier / PE / EY.
  - data/fundamentals/MASTER_fundamentals_pit.parquet (annual, PIT available_date) via
    builders_growth._load_annual()/_annual_asof() and builders_value._metric_pit_series()/
    _asof_align() -- reused, not re-derived, to keep one PIT-join code path.
  - datasets/earnings_pit/unified_quarterly_pit.parquet (quarterly PIT) via
    builders_growth._load_quarterly()/_quarterly_asof() -- reused for the SMILE sales-accel leg.

All joins PIT (asof backward on available_date, or exact-grain merge for stock_valuation_pit
which was itself built PIT). No factor value at date t reads information dated after t.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import builders_growth as bg
import builders_value as bv

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
VALUATION_PIT_PATH = RND_DIR / "panel" / "stock_valuation_pit.parquet"

_CACHE: dict = {}


def load_valuation_pit() -> pd.DataFrame:
    if "valpit" not in _CACHE:
        v = pd.read_parquet(VALUATION_PIT_PATH)
        v["date"] = pd.to_datetime(v["date"])
        _CACHE["valpit"] = v
    return _CACHE["valpit"]


def _zscore_by_date(df: pd.DataFrame, col: str) -> pd.Series:
    def _z(g):
        v = g[col].astype(float)
        lo, hi = v.quantile(0.01), v.quantile(0.99)
        v = v.clip(lo, hi)
        sd = v.std(ddof=0)
        if not sd or np.isnan(sd) or sd == 0:
            return pd.Series(np.nan, index=g.index)
        return (v - v.mean()) / sd
    return df.groupby("date", group_keys=False).apply(_z, include_groups=False)


# ==========================================================================
# IDG-G-10 -- cross-sectional return seasonality (Heston-Sadka)
# For each name: expanding mean of its OWN realized same-calendar-month return
# across strictly PRIOR years only (min_years occurrences required). Looked up
# at date t as the predictor for the return of month(t+1). Orthogonal
# construct to everything else in the panel (own-history seasonal, not
# cross-sectional value/momentum/quality).
# ==========================================================================
def build_seasonality(panel_df: pd.DataFrame, min_years: int = 3) -> pd.Series:
    df = panel_df[["date", "symbol", "fwd_ret_1M_raw"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"])
    # realized_ret = the 1M return that COMPLETED as of this row's date (the
    # forward return booked at the immediately preceding rebalance date) --
    # already-known information, no lookahead.
    df["realized_ret"] = df.groupby("symbol")["fwd_ret_1M_raw"].shift(1)
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year
    occ = df.dropna(subset=["realized_ret"]).sort_values(["symbol", "month", "year"]).copy()
    # PIT: shift(1) drops THIS year's occurrence before taking the expanding
    # mean, so the value stored for (symbol, month, year) uses only years < year.
    occ["seasonal_factor"] = occ.groupby(["symbol", "month"])["realized_ret"].transform(
        lambda s: s.shift(1).expanding(min_periods=min_years).mean())
    lookup = occ.dropna(subset=["seasonal_factor"])[["symbol", "month", "year", "seasonal_factor"]]

    ds = panel_df[["date", "symbol"]].drop_duplicates().copy()
    ds["date"] = pd.to_datetime(ds["date"])
    target = ds["date"] + pd.DateOffset(months=1)
    ds["month"] = target.dt.month
    ds["year"] = target.dt.year
    merged = ds.merge(lookup, on=["symbol", "month", "year"], how="inner")
    return merged.set_index(["date", "symbol"])["seasonal_factor"].replace([np.inf, -np.inf], np.nan).dropna()


# ==========================================================================
# IDG-G-13 -- Lynch GARP/PEG: PE / trailing-3y net_profit CAGR (%), low PEG
# preferred -> factor oriented so HIGHER = cheaper-relative-to-growth (=
# -PEG). Guard: growth must be > 1%/yr (drop, not impute, near-zero/negative
# growth where PEG is undefined/meaningless).
# ==========================================================================
def build_garp_peg(panel_df: pd.DataFrame, min_growth: float = 0.01) -> pd.Series:
    val = load_valuation_pit()[["date", "symbol", "PE"]]
    ds = panel_df[["date", "symbol"]].drop_duplicates().copy()
    ds["date"] = pd.to_datetime(ds["date"])
    m = ds.merge(val, on=["date", "symbol"], how="inner")

    ann = bg._annual_asof(ds)[["date", "symbol", "np_latest", "net_profit_fy3ago"]]
    ok = (ann["np_latest"] > 0) & (ann["net_profit_fy3ago"] > 0)
    ann["cagr_3y"] = np.nan
    ann.loc[ok, "cagr_3y"] = (ann.loc[ok, "np_latest"] / ann.loc[ok, "net_profit_fy3ago"]) ** (1 / 3) - 1

    m = m.merge(ann[["date", "symbol", "cagr_3y"]], on=["date", "symbol"], how="inner")
    m = m[(m["PE"] > 0) & (m["cagr_3y"] > min_growth)].copy()
    m["peg"] = m["PE"] / (m["cagr_3y"] * 100.0)
    m["factor"] = -m["peg"]
    return m.set_index(["date", "symbol"])["factor"].replace([np.inf, -np.inf], np.nan).dropna()


# ==========================================================================
# IDG-G-14 -- earnings stability: inverse coefficient-of-variation of
# trailing-5-fiscal-year annual net_profit YoY growth. High stability = high
# score. PIT via available_date asof (reuses bg._asof_join).
# ==========================================================================
def build_earnings_stability(panel_df: pd.DataFrame, min_periods: int = 4) -> pd.Series:
    ann = bg._load_annual().sort_values(["symbol", "fiscal_year"]).copy()
    ann["np_growth"] = ann.groupby("symbol")["net_profit"].pct_change()
    ann["np_growth"] = ann["np_growth"].replace([np.inf, -np.inf], np.nan)
    ann["roll_std"] = ann.groupby("symbol")["np_growth"].transform(
        lambda s: s.rolling(5, min_periods=min_periods).std(ddof=1))
    ann["roll_mean"] = ann.groupby("symbol")["np_growth"].transform(
        lambda s: s.rolling(5, min_periods=min_periods).mean())
    ann = ann[ann["roll_mean"].abs() > 0.02]  # guard: CoV undefined/explosive near-zero mean growth
    ann["cov"] = (ann["roll_std"] / ann["roll_mean"].abs()).clip(lower=0)
    ann["stability"] = -ann["cov"]  # higher = more stable (lower CoV)

    ds = panel_df[["date", "symbol"]].drop_duplicates()
    m = bg._asof_join(ds, ann[["symbol", "available_date", "stability"]], "available_date")
    m = m.dropna(subset=["stability"])
    z = _zscore_by_date(m[["date", "stability"]], "stability")
    m = m.assign(factor=z).dropna(subset=["factor"])
    return m.set_index(["date", "symbol"])["factor"].replace([np.inf, -np.inf], np.nan).dropna()


# ==========================================================================
# IDG-I-05 -- Kedia SMILE, small-cap_tier only (stock_valuation_pit.cap_tier
# == 'small', bottom mktcap tercile per the file's own PIT cross-sectional
# tiering). Rank-average of: (a) sales-growth acceleration (quarterly YoY
# delta, bg._load_quarterly sales_yoy_accel), (b) LOW net-debt/EBITDA
# (borrowings / (operating_profit+depreciation), builders_value PIT legs),
# (c) operating-margin EXPANSION (annual opm_latest - opm_pct_fy1ago).
# ==========================================================================
def build_smile_smallcap(panel_df: pd.DataFrame) -> pd.Series:
    val = load_valuation_pit()[["date", "symbol", "cap_tier"]]
    ds_all = panel_df[["date", "symbol"]].drop_duplicates().copy()
    ds_all["date"] = pd.to_datetime(ds_all["date"])
    small = ds_all.merge(val, on=["date", "symbol"], how="inner")
    small = small[small["cap_tier"] == "small"][["date", "symbol"]]
    if small.empty:
        return pd.Series(dtype=float)

    # (a) sales-growth acceleration (quarterly PIT)
    q = bg._quarterly_asof(small, ["sales_yoy_accel"])
    q_leg = _zscore_by_date(q[["date", "sales_yoy_accel"]], "sales_yoy_accel").rename("z_accel")
    leg_a = q[["date", "symbol"]].assign(z_accel=q_leg)

    # (b) net-debt/EBITDA, LOW preferred -> negate
    op = bv._metric_pit_series(["operating profit"])
    dep = bv._metric_pit_series(["depreciation"])
    debt = bv._metric_pit_series(["borrowings", "borrowing"])
    op_a = bv._asof_align(small, op, "op")
    dep_a = bv._asof_align(small, dep, "dep")
    debt_a = bv._asof_align(small, debt, "debt")
    nd = op_a.merge(dep_a, on=["date", "symbol"]).merge(debt_a, on=["date", "symbol"])
    nd["ebitda"] = nd["op"] + nd["dep"]
    nd = nd[nd["ebitda"] > 0]
    nd["nd_ebitda"] = nd["debt"].fillna(0.0) / nd["ebitda"]
    nd["z_nd"] = -_zscore_by_date(nd[["date", "nd_ebitda"]], "nd_ebitda")
    leg_b = nd[["date", "symbol", "z_nd"]]

    # (c) operating-margin expansion (annual PIT)
    ann = bg._annual_asof(small)
    ann["d_opm"] = ann["opm_latest"] - ann["opm_pct_fy1ago"]
    ann["z_opm"] = _zscore_by_date(ann[["date", "d_opm"]], "d_opm")
    leg_c = ann[["date", "symbol", "z_opm"]]

    m = leg_a.merge(leg_b, on=["date", "symbol"], how="outer").merge(leg_c, on=["date", "symbol"], how="outer")
    m["factor"] = m[["z_accel", "z_nd", "z_opm"]].mean(axis=1, skipna=True)
    m = m.dropna(subset=["factor"])
    return m.set_index(["date", "symbol"])["factor"].replace([np.inf, -np.inf], np.nan).dropna()
