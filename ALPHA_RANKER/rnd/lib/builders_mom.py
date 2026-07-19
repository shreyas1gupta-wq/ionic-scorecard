"""
Momentum factor builders for the ALPHA_RANKER research loop — worker hypotheses
H003 (12-1 residual momentum), H004 (vol-scaled momentum 3/6/12m),
H005 (raw vs residual 12-1 horse-race), H041 (52w-high vs 12-1 horse-race),
H043 (beta-adjusted momentum).

PIT discipline: every builder uses only cube_close/cube_bench/panel data with
index position <= the panel rebalance date t (RESEARCH_PROTOCOL.md S1 "no
lookahead"). Rolling betas use a trailing window ENDING at t (same convention
documented in PANEL_SCHEMA.md for beta_252 / ff_beta_*: "uses only data <= t").

Data: ALPHA_RANKER/rnd/panel/cube_close.parquet (1238 dates x 751 symbols,
adjusted close), cube_bench.parquet (NSEI benchmark close, 1234 dates).
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
PANEL_DIR = RND_DIR / "panel"

_CUBE_CLOSE = None
_CUBE_BENCH = None
_DAILY_RET = None
_BENCH_RET = None
_ROLL_BETA = None
_RESID_DAILY = None
_ROLL_MAX_252 = None


def _load_cubes():
    global _CUBE_CLOSE, _CUBE_BENCH, _DAILY_RET, _BENCH_RET
    if _CUBE_CLOSE is None:
        _CUBE_CLOSE = pd.read_parquet(PANEL_DIR / "cube_close.parquet")
        _CUBE_BENCH = pd.read_parquet(PANEL_DIR / "cube_bench.parquet")["NSEI"]
        _DAILY_RET = _CUBE_CLOSE.pct_change()
        _BENCH_RET = _CUBE_BENCH.pct_change()
    return _CUBE_CLOSE, _CUBE_BENCH, _DAILY_RET, _BENCH_RET


def _rolling_daily_beta() -> pd.DataFrame:
    """Trailing 252d (min126) daily-frequency CAPM beta to NSEI, per stock.
    [INFERENCE]: window ENDS at t (includes day t), matching PANEL_SCHEMA.md's
    documented beta_252 convention ("uses only data <= t"), not a t-1 shift."""
    global _ROLL_BETA
    if _ROLL_BETA is None:
        _, _, daily_ret, bench_ret = _load_cubes()
        cov = daily_ret.rolling(252, min_periods=126).cov(bench_ret)
        var = bench_ret.rolling(252, min_periods=126).var()
        _ROLL_BETA = cov.div(var, axis=0)
    return _ROLL_BETA


def _residual_daily_returns() -> pd.DataFrame:
    """daily_ret_i(t) - beta_i(t)*bench_ret(t), beta known at t (min126 obs)."""
    global _RESID_DAILY
    if _RESID_DAILY is None:
        _, _, daily_ret, bench_ret = _load_cubes()
        beta = _rolling_daily_beta()
        _RESID_DAILY = daily_ret.sub(beta.mul(bench_ret, axis=0))
    return _RESID_DAILY


def _roll_max_252() -> pd.DataFrame:
    global _ROLL_MAX_252
    if _ROLL_MAX_252 is None:
        close, *_ = _load_cubes()
        _ROLL_MAX_252 = close.rolling(252, min_periods=252).max()
    return _ROLL_MAX_252


def _panel_dates_symbols(panel: pd.DataFrame):
    dates = sorted(pd.to_datetime(panel["date"].unique()))
    symbols = sorted(panel["symbol"].unique())
    return dates, symbols


def _series_from_rows(rows) -> pd.Series:
    out = pd.DataFrame(rows, columns=["date", "symbol", "factor"])
    return out.set_index(["date", "symbol"])["factor"]


# --------------------------------------------------------------------------
# H003 / H005 baseline: raw 12-1 momentum (independent of panel columns —
# rebuilt from cube_close, not a tautology).
# --------------------------------------------------------------------------
def build_mom_raw_12_1(panel: pd.DataFrame) -> pd.Series:
    """Classic 12-1 momentum: p[t-21]/p[t-252]-1 on RAW adjusted close."""
    close, *_ = _load_cubes()
    dates, symbols = _panel_dates_symbols(panel)
    cols = [s for s in symbols if s in close.columns]
    rows = []
    for d in dates:
        if d not in close.index:
            continue
        loc = close.index.get_loc(d)
        if loc < 252:
            continue
        p_t21 = close.iloc[loc - 21][cols]
        p_t252 = close.iloc[loc - 252][cols]
        mom = (p_t21 / p_t252 - 1.0).dropna()
        for sym, val in mom.items():
            rows.append((d, sym, val))
    return _series_from_rows(rows)


# --------------------------------------------------------------------------
# H003: 12-1 momentum built on RESIDUAL daily returns (beta*mkt stripped from
# every day in the window, then compounded) — distinct from H043's single-
# point-beta adjustment.
# --------------------------------------------------------------------------
def build_mom_resid_12_1(panel: pd.DataFrame) -> pd.Series:
    resid = _residual_daily_returns()
    dates, symbols = _panel_dates_symbols(panel)
    cols = [s for s in symbols if s in resid.columns]
    rows = []
    for d in dates:
        if d not in resid.index:
            continue
        loc = resid.index.get_loc(d)
        if loc < 273:  # need 252+21 trading days of history
            continue
        window = resid.iloc[loc - 251: loc - 20][cols]  # (t-251 .. t-21) inclusive, 231 obs
        cov_ok = window.notna().mean() >= 0.80
        cum = (1.0 + window.fillna(0.0)).prod() - 1.0
        cum = cum.where(cov_ok)
        for sym, val in cum.dropna().items():
            rows.append((d, sym, val))
    return _series_from_rows(rows)


# --------------------------------------------------------------------------
# H004: trailing-N-day return / panel's own realized-vol column (no skip
# month — plain trailing return per backlog construct).
# --------------------------------------------------------------------------
def build_vol_scaled_mom(panel: pd.DataFrame, window_days: int, vol_col: str) -> pd.Series:
    close, *_ = _load_cubes()
    dates, symbols = _panel_dates_symbols(panel)
    cols = [s for s in symbols if s in close.columns]
    vol_lookup = panel.set_index(["date", "symbol"])[vol_col]
    rows = []
    for d in dates:
        if d not in close.index:
            continue
        loc = close.index.get_loc(d)
        if loc < window_days:
            continue
        p_t = close.iloc[loc][cols]
        p_t0 = close.iloc[loc - window_days][cols]
        ret = (p_t / p_t0 - 1.0).dropna()
        for sym, val in ret.items():
            vol = vol_lookup.get((d, sym), np.nan)
            if pd.isna(vol) or vol <= 0:
                continue
            rows.append((d, sym, val / vol))
    return _series_from_rows(rows)


def build_mom_sharpe_3m(panel: pd.DataFrame) -> pd.Series:
    return build_vol_scaled_mom(panel, 63, "vol_63")


def build_mom_sharpe_6m(panel: pd.DataFrame) -> pd.Series:
    return build_vol_scaled_mom(panel, 126, "vol_126")


def build_mom_sharpe_12m(panel: pd.DataFrame) -> pd.Series:
    return build_vol_scaled_mom(panel, 252, "vol_252")


# --------------------------------------------------------------------------
# H041: 52-week-high proximity (O'Neil) — close(t)/rolling-252d-high(t).
# --------------------------------------------------------------------------
def build_52w_high_proximity(panel: pd.DataFrame) -> pd.Series:
    close, *_ = _load_cubes()
    roll_max = _roll_max_252()
    dates, symbols = _panel_dates_symbols(panel)
    cols = [s for s in symbols if s in close.columns]
    rows = []
    for d in dates:
        if d not in close.index:
            continue
        c = close.loc[d, cols]
        m = roll_max.loc[d, cols]
        ratio = (c / m).dropna()
        for sym, val in ratio.items():
            rows.append((d, sym, val))
    return _series_from_rows(rows)


# --------------------------------------------------------------------------
# H043: 12-1 raw momentum minus (point beta_252(t) x market's own 12-1 return
# over the same window) — single-beta point adjustment, distinct from H003's
# daily-compounded residual construction.
# --------------------------------------------------------------------------
def build_beta_adjusted_mom(panel: pd.DataFrame) -> pd.Series:
    close, bench, *_ = _load_cubes()
    dates, symbols = _panel_dates_symbols(panel)
    cols = [s for s in symbols if s in close.columns]
    beta_lookup = panel.set_index(["date", "symbol"])["beta_252"]
    rows = []
    for d in dates:
        if d not in close.index or d not in bench.index:
            continue
        loc = close.index.get_loc(d)
        loc_b = bench.index.get_loc(d)
        if loc < 252 or loc_b < 252:
            continue
        p_t21 = close.iloc[loc - 21][cols]
        p_t252 = close.iloc[loc - 252][cols]
        mom = (p_t21 / p_t252 - 1.0).dropna()
        mkt_t21 = bench.iloc[loc_b - 21]
        mkt_t252 = bench.iloc[loc_b - 252]
        mkt_mom = mkt_t21 / mkt_t252 - 1.0
        for sym, val in mom.items():
            b = beta_lookup.get((d, sym), np.nan)
            if pd.isna(b):
                continue
            rows.append((d, sym, val - b * mkt_mom))
    return _series_from_rows(rows)
