"""
ALPHA_RANKER worker: Growth-family factor builders (H024, H025, H026, H044, H027).
Owner: worker session, per RESEARCH_PROTOCOL.md S3-4 / rnd/backlog.json.

Every builder returns a pandas Series indexed by (date, symbol) suitable for
harness.evaluate()/run_experiment(). All fundamentals joins are PIT: a panel
rebalance date t is matched to the latest fundamentals row with
available_date <= t via merge_asof(direction='backward'); nothing after t is
ever read into a factor value at t.

Data sources:
  - ALPHA_RANKER/data/fundamentals/MASTER_fundamentals_pit.parquet
        LONG, annual (fiscal-year) PL rows, has available_date. Used for H024
        (3y/5y CAGR) and H044 (OPM/NPM YoY) and the H027 'A' leg.
  - datasets/earnings_pit/unified_quarterly_pit.parquet (repo root, AMC-side)
        LONG-ish quarterly rows with a genuine PIT available_date
        (nse_broadcast / board_meeting / conservative_lag_50d sourced).
        Used for H025 (growth acceleration), H026 (PEAD/surprise), H027 'C' leg.
        NOTE: ALPHA_RANKER's own data/fundamentals/consolidated/quarterly_results.parquet
        has NO available_date column at all -> would be a lookahead landmine if
        used for PIT factors, so it is deliberately NOT used here.
  - ALPHA_RANKER/rnd/panel/cube_close.parquet, cube_volume.parquet
        date x symbol matrices, used for H027 'N'/'S'/'L' legs (trailing-only).
  - ALPHA_RANKER/data/fundamentals/consolidated/shareholding.parquet
        FII/DII/Promoter % by (symbol, quarter period label). NO available_date
        column -> PIT lag is an ASSUMED [INFERENCE] ~45-day disclosure lag,
        applied explicitly and disclosed (not silent).
"""
from __future__ import annotations
import re
from pathlib import Path

import numpy as np
import pandas as pd

_LIB_DIR = Path(__file__).resolve().parent
ALPHA_ROOT = _LIB_DIR.parents[1]          # .../ALPHA_RANKER
REPO_ROOT = ALPHA_ROOT.parent             # .../NIFTY 500

MASTER_FUND_PATH = ALPHA_ROOT / "data/fundamentals/MASTER_fundamentals_pit.parquet"
UNIFIED_Q_PATH = REPO_ROOT / "datasets/earnings_pit/unified_quarterly_pit.parquet"
SHAREHOLDING_PATH = ALPHA_ROOT / "data/fundamentals/consolidated/shareholding.parquet"
CUBE_CLOSE_PATH = ALPHA_ROOT / "rnd/panel/cube_close.parquet"
CUBE_VOLUME_PATH = ALPHA_ROOT / "rnd/panel/cube_volume.parquet"

_SHAREHOLDING_LAG_DAYS = 45  # [INFERENCE] disclosed assumed disclosure lag


# ==========================================================================
# 0. helpers
# ==========================================================================
def _winsorize(s: pd.Series, p=0.01) -> pd.Series:
    lo, hi = s.quantile(p), s.quantile(1 - p)
    return s.clip(lo, hi)


def _zscore_by_date(df: pd.DataFrame, col: str) -> pd.Series:
    def _z(g):
        v = _winsorize(g[col].astype(float))
        sd = v.std(ddof=0)
        if not sd or np.isnan(sd) or sd == 0:
            return pd.Series(np.nan, index=g.index)
        return (v - v.mean()) / sd
    return df.groupby("date", group_keys=False).apply(_z, include_groups=False)


def _asof_join(panel_ds: pd.DataFrame, right: pd.DataFrame, right_time_col: str) -> pd.DataFrame:
    """panel_ds: unique (date,symbol) pairs. right: has 'symbol', right_time_col,
    and value columns. Returns panel_ds rows matched to the latest right row per
    symbol with right_time_col <= date (backward asof), no lookahead."""
    left = panel_ds[["date", "symbol"]].drop_duplicates().sort_values(["date", "symbol"]).reset_index(drop=True)
    left = left.assign(date=pd.to_datetime(left["date"]).astype("datetime64[ns]"),
                        symbol=left["symbol"].astype(str))
    r = right.rename(columns={right_time_col: "_asof_time"}).sort_values(["_asof_time", "symbol"]).reset_index(drop=True)
    r = r.assign(_asof_time=pd.to_datetime(r["_asof_time"]).astype("datetime64[ns]"),
                 symbol=r["symbol"].astype(str))
    out = pd.merge_asof(left.sort_values("date"), r, left_on="date", right_on="_asof_time",
                         by="symbol", direction="backward")
    return out


# ==========================================================================
# 1. annual fundamentals (MASTER_fundamentals_pit) -> per (symbol, fiscal_year)
# ==========================================================================
_ANNUAL_CACHE = None


def _load_annual() -> pd.DataFrame:
    global _ANNUAL_CACHE
    if _ANNUAL_CACHE is not None:
        return _ANNUAL_CACHE
    mf = pd.read_parquet(MASTER_FUND_PATH)
    ann = mf[(mf.statement == "PL") & (mf.metric_norm.isin(
        ["sales", "eps in rs", "opm %", "net profit"]))].copy()
    # keep clean full-year labels ("Mon YYYY"); drop stub/partial periods (e.g. "Mar 2022  8m")
    ann = ann[ann.period_label.str.match(r"^[A-Za-z]{3} \d{4}$", na=False)]
    piv = ann.pivot_table(index=["nse_symbol", "fiscal_year"], columns="metric_norm",
                           values="value", aggfunc="last")
    avail = ann.groupby(["nse_symbol", "fiscal_year"])["available_date"].max()
    piv = piv.join(avail).reset_index().rename(columns={"nse_symbol": "symbol"})
    piv = piv.rename(columns={"eps in rs": "eps", "opm %": "opm_pct", "net profit": "net_profit"})
    piv["npm_pct"] = np.where(piv["sales"] > 0, piv["net_profit"] / piv["sales"] * 100.0, np.nan)
    piv["available_date"] = pd.to_datetime(piv["available_date"])
    _ANNUAL_CACHE = piv.sort_values(["symbol", "fiscal_year"]).reset_index(drop=True)
    return _ANNUAL_CACHE


def _annual_asof(panel_ds: pd.DataFrame) -> pd.DataFrame:
    """Returns panel_ds + latest FY (as of date) sales/eps/opm_pct/net_profit/npm_pct
    + fiscal_year of that FY, plus the same 4 fields for fiscal_year-3 and
    fiscal_year-5 (direct lookup on strictly earlier, already-known FYs)."""
    ann = _load_annual()
    m = _asof_join(panel_ds, ann[["symbol", "fiscal_year", "sales", "eps", "opm_pct",
                                  "net_profit", "npm_pct", "available_date"]], "available_date")
    m = m.rename(columns={"fiscal_year": "fy_latest", "sales": "sales_latest", "eps": "eps_latest",
                           "opm_pct": "opm_latest", "net_profit": "np_latest", "npm_pct": "npm_latest"})
    # fy_latest is float64 (asof join introduces NaN for unmatched rows) -- the
    # lookup index must match that dtype exactly, else a dtype-mismatched
    # MultiIndex .join() silently fans out (observed bug: int64 vs float64
    # fiscal_year levels produced a 13x row-count blowup instead of erroring).
    # NOTE: DataFrame.join() on a MultiIndex where the LEFT side has duplicate
    # labels was observed to silently fan out (538455 rows from a 40201-row
    # left, no error) even with matching dtypes and a confirmed-unique RIGHT
    # index -- reproduced in isolation, root cause not chased further; a plain
    # merge() on reset-index columns is the well-supported equivalent and was
    # verified to return exactly len(key) rows, so it is used here instead.
    lookup = ann.assign(fiscal_year=ann["fiscal_year"].astype(float),
                         symbol=ann["symbol"].astype(str))[
        ["symbol", "fiscal_year", "sales", "eps", "opm_pct", "net_profit", "npm_pct"]]

    def _lookup(offset, suffix):
        key = m[["symbol", "fy_latest"]].copy()
        key["symbol"] = key["symbol"].astype(str)
        key["fiscal_year"] = key["fy_latest"] - offset
        joined = key.merge(lookup, on=["symbol", "fiscal_year"], how="left")
        assert len(joined) == len(key), f"unexpected merge fanout: {len(joined)} vs {len(key)}"
        for c in ["sales", "eps", "opm_pct", "net_profit", "npm_pct"]:
            m[f"{c}_{suffix}"] = joined[c].values

    _lookup(1, "fy1ago")
    _lookup(3, "fy3ago")
    _lookup(5, "fy5ago")
    return m


# ==========================================================================
# 2. quarterly PIT (unified_quarterly_pit.parquet, repo-root AMC dataset)
# ==========================================================================
_QUARTERLY_CACHE = None


def _load_quarterly() -> pd.DataFrame:
    global _QUARTERLY_CACHE
    if _QUARTERLY_CACHE is not None:
        return _QUARTERLY_CACHE
    df = pd.read_parquet(UNIFIED_Q_PATH)
    df = df[["symbol", "quarter_end", "available_date", "sales", "net_profit", "op_profit"]].copy()
    df["quarter_end"] = pd.to_datetime(df["quarter_end"])
    df["available_date"] = pd.to_datetime(df["available_date"])
    df = df.dropna(subset=["quarter_end", "available_date"]).drop_duplicates(["symbol", "quarter_end"])
    df = df.sort_values(["symbol", "quarter_end"]).reset_index(drop=True)

    # same-quarter-prior-year match via nearest asof on (quarter_end - 365d), tolerance 45d
    df["q_target"] = df["quarter_end"] - pd.DateOffset(days=365)
    prior = df[["symbol", "quarter_end", "sales", "net_profit"]].rename(
        columns={"quarter_end": "q_prior_end", "sales": "sales_py", "net_profit": "np_py"})
    left = df.sort_values("q_target")
    right = prior.sort_values("q_prior_end")
    m = pd.merge_asof(left, right, left_on="q_target", right_on="q_prior_end", by="symbol",
                       direction="nearest", tolerance=pd.Timedelta(days=45))
    m = m.sort_values(["symbol", "quarter_end"]).reset_index(drop=True)
    m["sales_yoy"] = np.where(m["sales_py"] > 0, m["sales"] / m["sales_py"] - 1, np.nan)
    m["np_yoy"] = np.where(m["np_py"] > 0, m["net_profit"] / m["np_py"] - 1, np.nan)

    # acceleration = this quarter's YoY minus the immediately preceding reported quarter's YoY
    m["sales_yoy_accel"] = m.groupby("symbol")["sales_yoy"].diff()
    m["np_yoy_accel"] = m.groupby("symbol")["np_yoy"].diff()

    # own-trend expectation for PEAD: expected = same-quarter-last-year * (1 + trailing
    # avg YoY growth of the preceding 4 reported quarters, EXCLUDING the current print)
    m["np_yoy_trail_avg"] = m.groupby("symbol")["np_yoy"].transform(lambda s: s.shift(1).rolling(4, min_periods=2).mean())
    m["np_expected"] = m["np_py"] * (1 + m["np_yoy_trail_avg"])
    m["np_surprise"] = np.where(m["np_expected"].abs() > 0, (m["net_profit"] - m["np_expected"]) / m["np_expected"].abs(), np.nan)

    _QUARTERLY_CACHE = m
    return _QUARTERLY_CACHE


def _quarterly_asof(panel_ds: pd.DataFrame, cols: list[str], extra_gap_col: bool = False) -> pd.DataFrame:
    q = _load_quarterly()
    m = _asof_join(panel_ds, q[["symbol", "available_date"] + cols], "available_date")
    if extra_gap_col:
        m["days_since_release"] = (m["date"] - m["_asof_time"]).dt.days
    return m


# ==========================================================================
# 3. H024 — sales/EPS CAGR 3y & 5y
# ==========================================================================
def build_h024(panel_df: pd.DataFrame) -> pd.Series:
    m = _annual_asof(panel_df[["date", "symbol"]])

    def _cagr(latest, base, n):
        ok = (latest > 0) & (base > 0)
        out = pd.Series(np.nan, index=latest.index)
        out[ok] = (latest[ok] / base[ok]) ** (1.0 / n) - 1.0
        return out

    m["sales_cagr_3y"] = _cagr(m["sales_latest"], m["sales_fy3ago"], 3)
    m["eps_cagr_3y"] = _cagr(m["eps_latest"], m["eps_fy3ago"], 3)
    m["sales_cagr_5y"] = _cagr(m["sales_latest"], m["sales_fy5ago"], 5)
    m["eps_cagr_5y"] = _cagr(m["eps_latest"], m["eps_fy5ago"], 5)

    legs = ["sales_cagr_3y", "eps_cagr_3y", "sales_cagr_5y", "eps_cagr_5y"]
    for leg in legs:
        m[f"z_{leg}"] = _zscore_by_date(m[["date", leg]], leg)
    m["factor"] = m[[f"z_{leg}" for leg in legs]].mean(axis=1, skipna=True)
    m = m.dropna(subset=["factor"])
    return m.set_index(["date", "symbol"])["factor"]


# ==========================================================================
# 4. H025 — growth acceleration (latest YoY - prior YoY, sales & EPS/net-profit)
# ==========================================================================
def build_h025(panel_df: pd.DataFrame) -> pd.Series:
    m = _quarterly_asof(panel_df[["date", "symbol"]], ["sales_yoy_accel", "np_yoy_accel"])
    m["z_sales"] = _zscore_by_date(m[["date", "sales_yoy_accel"]], "sales_yoy_accel")
    m["z_np"] = _zscore_by_date(m[["date", "np_yoy_accel"]], "np_yoy_accel")
    m["factor"] = m[["z_sales", "z_np"]].mean(axis=1, skipna=True)
    m = m.dropna(subset=["factor"])
    return m.set_index(["date", "symbol"])["factor"]


# ==========================================================================
# 5. H026 — earnings surprise / PEAD (own-trend expectation, drift window)
# ==========================================================================
def build_h026(panel_df: pd.DataFrame, drift_window_days: int = 45) -> pd.Series:
    m = _quarterly_asof(panel_df[["date", "symbol"]], ["np_surprise"], extra_gap_col=True)
    # only keep observations inside the post-earnings drift window; outside it
    # there is no active event and the factor should not be defined that month
    m = m[(m["days_since_release"] >= 0) & (m["days_since_release"] <= drift_window_days)]
    m["z"] = _zscore_by_date(m[["date", "np_surprise"]], "np_surprise")
    m = m.dropna(subset=["z"])
    return m.set_index(["date", "symbol"])["z"]


# ==========================================================================
# 6. H044 — margin expansion (OPM/NPM YoY change, annual PIT)
# ==========================================================================
def build_h044(panel_df: pd.DataFrame) -> pd.Series:
    m = _annual_asof(panel_df[["date", "symbol"]])
    m["d_opm"] = m["opm_latest"] - m["opm_pct_fy1ago"]
    m["d_npm"] = m["npm_latest"] - m["npm_pct_fy1ago"]
    m["z_opm"] = _zscore_by_date(m[["date", "d_opm"]], "d_opm")
    m["z_npm"] = _zscore_by_date(m[["date", "d_npm"]], "d_npm")
    m["factor"] = m[["z_opm", "z_npm"]].mean(axis=1, skipna=True)
    m = m.dropna(subset=["factor"])
    return m.set_index(["date", "symbol"])["factor"]


# ==========================================================================
# 7. H027 — O'Neil CANSLIM composite (proxies) + individual legs
# ==========================================================================
_CUBE_CLOSE = None
_CUBE_VOLUME = None


def _load_cubes():
    global _CUBE_CLOSE, _CUBE_VOLUME
    if _CUBE_CLOSE is None:
        _CUBE_CLOSE = pd.read_parquet(CUBE_CLOSE_PATH)
        _CUBE_VOLUME = pd.read_parquet(CUBE_VOLUME_PATH)
    return _CUBE_CLOSE, _CUBE_VOLUME


def _price_technical_legs(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """N (new-high proximity), S (relative volume), L (RS vs cross-section),
    all trailing-only (no lookahead) off cube_close/cube_volume."""
    close, vol = _load_cubes()
    dates = sorted(pd.DatetimeIndex(dates).unique())
    roll_max_252 = close.rolling(252, min_periods=100).max()
    ret_126 = close / close.shift(126) - 1
    vol_avg_21 = vol.rolling(21, min_periods=10).mean()
    vol_avg_252 = vol.rolling(252, min_periods=100).mean()

    rows = []
    for d in dates:
        if d not in close.index:
            continue
        n_leg = (close.loc[d] / roll_max_252.loc[d])
        s_leg = (vol_avg_21.loc[d] / vol_avg_252.loc[d])
        l_leg = ret_126.loc[d]
        l_leg = l_leg - l_leg.median()  # RS vs cross-sectional median, per date
        df = pd.DataFrame({"symbol": close.columns, "n_leg": n_leg.values,
                            "s_leg": s_leg.values, "l_leg": l_leg.values})
        df["date"] = d
        rows.append(df)
    return pd.concat(rows, ignore_index=True)


_SHAREHOLDING_CACHE = None


def _load_shareholding_delta():
    global _SHAREHOLDING_CACHE
    if _SHAREHOLDING_CACHE is not None:
        return _SHAREHOLDING_CACHE
    sh = pd.read_parquet(SHAREHOLDING_PATH)
    sh = sh[sh.metric.isin(["FIIs", "DIIs"])].copy()
    inst = sh.groupby(["symbol", "period"])["value"].sum().reset_index().rename(columns={"value": "inst_pct"})
    # period is a "Mon YYYY" quarter label -> parse to a period-end date, then
    # apply an assumed disclosure lag since this table carries no available_date
    inst["period_end"] = pd.to_datetime(inst["period"], format="%b %Y", errors="coerce") + pd.offsets.MonthEnd(0)
    inst = inst.dropna(subset=["period_end"]).sort_values(["symbol", "period_end"])
    inst["inst_pct_delta"] = inst.groupby("symbol")["inst_pct"].diff()
    inst["available_date"] = inst["period_end"] + pd.Timedelta(days=_SHAREHOLDING_LAG_DAYS)  # [INFERENCE]
    _SHAREHOLDING_CACHE = inst
    return inst


def _institutional_leg(panel_ds: pd.DataFrame) -> pd.DataFrame:
    inst = _load_shareholding_delta()
    return _asof_join(panel_ds, inst[["symbol", "available_date", "inst_pct_delta"]], "available_date")


def build_h027_legs(panel_df: pd.DataFrame) -> pd.DataFrame:
    """Returns a DataFrame (date,symbol,...) with each raw+z-scored CANSLIM leg,
    for both the composite factor and a parts-vs-whole comparison."""
    ds = panel_df[["date", "symbol"]].drop_duplicates()

    ann = _annual_asof(ds)
    ann["a_leg"] = np.where((ann["eps_latest"] > 0) & (ann["eps_fy1ago"] > 0),
                             ann["eps_latest"] / ann["eps_fy1ago"] - 1, np.nan)

    q = _quarterly_asof(ds, ["np_yoy"]).rename(columns={"np_yoy": "c_leg"})

    tech = _price_technical_legs(ds["date"].unique())

    inst = _institutional_leg(ds).rename(columns={"inst_pct_delta": "i_leg"})

    regime = panel_df[["date", "symbol", "regime_trend"]].drop_duplicates()
    regime_map = {"bull": 1.0, "sideways": 0.0, "bear": -1.0}
    regime["m_leg"] = regime["regime_trend"].map(regime_map)

    out = ds.merge(ann[["date", "symbol", "a_leg"]], on=["date", "symbol"], how="left") \
            .merge(q[["date", "symbol", "c_leg"]], on=["date", "symbol"], how="left") \
            .merge(tech[["date", "symbol", "n_leg", "s_leg", "l_leg"]], on=["date", "symbol"], how="left") \
            .merge(inst[["date", "symbol", "i_leg"]], on=["date", "symbol"], how="left") \
            .merge(regime[["date", "symbol", "m_leg"]], on=["date", "symbol"], how="left")

    leg_cols = ["c_leg", "a_leg", "n_leg", "s_leg", "l_leg", "i_leg", "m_leg"]
    for leg in leg_cols:
        out[f"z_{leg}"] = _zscore_by_date(out[["date", leg]], leg)
    return out


def build_h027(panel_df: pd.DataFrame) -> pd.Series:
    out = build_h027_legs(panel_df)
    z_cols = [f"z_{c}" for c in ["c_leg", "a_leg", "n_leg", "s_leg", "l_leg", "i_leg", "m_leg"]]
    out["factor"] = out[z_cols].mean(axis=1, skipna=True)
    out = out.dropna(subset=["factor"])
    return out.set_index(["date", "symbol"])["factor"]


def build_h027_leg_series(panel_df: pd.DataFrame, leg: str) -> pd.Series:
    """leg in {c,a,n,s,l,i,m} -> single-leg factor Series for parts-vs-whole comparison."""
    out = build_h027_legs(panel_df)
    col = f"z_{leg}_leg"
    out = out.dropna(subset=[col])
    return out.set_index(["date", "symbol"])[col]
