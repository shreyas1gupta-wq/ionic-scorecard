"""
Factor builders for O'Neil / Minervini / Weinstein / volume-price technical
hypotheses (H006, H007, H008, H009, H036) — ALPHA_RANKER research loop.

Each builder takes the panel DataFrame (only used to read the target
(date,symbol) grid — 61 monthly rebalance dates, all present in the cube
index, verified) and returns a factor Series indexed by (date,symbol),
computed from the daily CUBE (rnd/panel/cube_close.parquet,
cube_volume.parquet, cube_bench.parquet). All rolling windows use only
data <= t (min_periods enforced = full window, no partial-window leak-in),
so values at panel rebalance date t are PIT.

[DATA] cube_close/cube_volume: (1238 dates x 751 symbols), 2021-07-16 ->
2026-07-16, daily. cube_bench: NSEI daily close, same range.
[INFERENCE] cube_close is a Close-only cube (no OHLC) — true ATR (needs
High/Low) is not computable from this data; H008's "ATR%" is proxied by
close-to-close realized vol (same construction as panel's vol_21/63/126/252
columns), documented at the point of use, not silently substituted.

Multi-condition constructs (H008, H009) are combined via per-date RANK
averaging (not raw-value summation), so components with different scales/
units don't let one dominate the composite by magnitude alone — a rank sum
only reflects each component's own cross-sectional ordering.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent  # ALPHA_RANKER/rnd
PANEL_DIR = RND_DIR / "panel"


def _load_cubes():
    close = pd.read_parquet(PANEL_DIR / "cube_close.parquet")
    volume = pd.read_parquet(PANEL_DIR / "cube_volume.parquet")
    bench = pd.read_parquet(PANEL_DIR / "cube_bench.parquet")["NSEI"]
    close.index = pd.to_datetime(close.index)
    volume.index = pd.to_datetime(volume.index)
    bench.index = pd.to_datetime(bench.index)
    return close, volume, bench


def _panel_dates(panel: pd.DataFrame) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(sorted(pd.to_datetime(panel["date"]).unique()))


def _stack_at_dates(wide: pd.DataFrame, dates: pd.DatetimeIndex, name: str = "factor") -> pd.Series:
    """Select rows at `dates` (must already exist in wide.index — verified for
    all 61 panel dates against the cube) and stack to a (date,symbol) Series."""
    sel = wide.reindex(dates)
    s = sel.stack(future_stack=True) if hasattr(sel, "stack") else sel.stack()
    s.index.names = ["date", "symbol"]
    return s.rename(name)


def _rank_combine(components: list[pd.DataFrame], dates: pd.DatetimeIndex) -> pd.Series:
    """Per-date, per-column cross-sectional percentile rank, averaged across
    components, then stacked to (date,symbol). NaN in ANY component at a
    given (date,symbol) drops that cell (row-wise nanmean over available
    components only, matching how each gate below sets NaN to mean 'not
    eligible')."""
    ranked = []
    for comp in components:
        sel = comp.reindex(dates)
        r = sel.rank(axis=1, pct=True, na_option="keep")
        ranked.append(r)
    stacked = [c.stack(future_stack=True) if hasattr(c, "stack") else c.stack() for c in ranked]
    combo = pd.concat(stacked, axis=1).mean(axis=1, skipna=True)
    combo.index.names = ["date", "symbol"]
    return combo.rename("factor")


# --------------------------------------------------------------------------
# H006 — 52-week-high proximity (O'Neil), horizon 1M
# --------------------------------------------------------------------------
def build_h006_52w_high(panel: pd.DataFrame) -> pd.Series:
    close, _volume, _bench = _load_cubes()
    dates = _panel_dates(panel)
    roll_high_252 = close.rolling(252, min_periods=252).max()
    proximity = close / roll_high_252  # in (0,1], 1.0 = at/above trailing 252d high
    return _stack_at_dates(proximity, dates, "factor")


# --------------------------------------------------------------------------
# H007 — RS-line new high while price bases (O'Neil), horizon 1Y
# --------------------------------------------------------------------------
def build_h007_rsline_newhigh(panel: pd.DataFrame) -> pd.Series:
    close, _volume, bench = _load_cubes()
    dates = _panel_dates(panel)
    rs = close.div(bench, axis=0)  # stock/NIFTY ratio (RS-line)
    rs_roll_max_126 = rs.rolling(126, min_periods=126).max()
    rs_proximity = rs / rs_roll_max_126  # 1.0 = RS-line at a new 6m high

    roll_max_126 = close.rolling(126, min_periods=126).max()
    roll_min_126 = close.rolling(126, min_periods=126).min()
    roll_mean_126 = close.rolling(126, min_periods=126).mean()
    price_range_pct = (roll_max_126 - roll_min_126) / roll_mean_126  # wide range = NOT basing
    basing_score = -price_range_pct  # higher (less negative) = tighter base

    return _rank_combine([rs_proximity, basing_score], dates)


# --------------------------------------------------------------------------
# H008 — VCP: declining vol% ("ATR% proxy") + volume dry-up within uptrend
# (price>200DMA), horizon 1M
# --------------------------------------------------------------------------
def build_h008_vcp(panel: pd.DataFrame) -> pd.Series:
    close, volume, _bench = _load_cubes()
    dates = _panel_dates(panel)

    ret = close.pct_change()
    vol21 = ret.rolling(21, min_periods=21).std()
    vol63 = ret.rolling(63, min_periods=63).std()
    contraction_score = (vol63 - vol21) / vol63  # >0 when recent vol << baseline vol ("ATR% declining")

    vavg21 = volume.rolling(21, min_periods=21).mean()
    vavg63 = volume.rolling(63, min_periods=63).mean()
    dryup_score = (vavg63 - vavg21) / vavg63  # >0 when recent volume below baseline

    ma200 = close.rolling(200, min_periods=200).mean()
    uptrend_gate = close > ma200  # Minervini stage-2 prerequisite

    contraction_score = contraction_score.where(uptrend_gate)
    dryup_score = dryup_score.where(uptrend_gate)

    return _rank_combine([contraction_score, dryup_score], dates)


# --------------------------------------------------------------------------
# H009 — Weinstein stage-2: price>30wk MA & MA rising & RS positive, horizon 1Y
# --------------------------------------------------------------------------
def build_h009_stage2(panel: pd.DataFrame) -> pd.Series:
    close, _volume, bench = _load_cubes()
    dates = _panel_dates(panel)

    ma150 = close.rolling(150, min_periods=150).mean()  # ~30 trading weeks
    above_ma = close / ma150 - 1.0
    ma_slope = ma150 / ma150.shift(21) - 1.0  # 1M rate of change of the MA itself
    stock_126 = close / close.shift(126) - 1.0
    bench_126 = bench / bench.shift(126) - 1.0
    rs = stock_126.sub(bench_126, axis=0)  # relative strength vs NIFTY, trailing 6m

    stage2_gate = (above_ma > 0) & (ma_slope > 0) & (rs > 0)  # Weinstein stage-2 definition

    above_ma_g = above_ma.where(stage2_gate)
    ma_slope_g = ma_slope.where(stage2_gate)
    rs_g = rs.where(stage2_gate)

    return _rank_combine([above_ma_g, ma_slope_g, rs_g], dates)


# --------------------------------------------------------------------------
# H036 — OBV / volume-price divergence, horizon 1M
# --------------------------------------------------------------------------
def build_h036_obv_divergence(panel: pd.DataFrame) -> pd.Series:
    close, volume, _bench = _load_cubes()
    dates = _panel_dates(panel)

    price_chg = close.diff()
    signed_vol = volume.where(price_chg > 0, -volume).where(price_chg != 0, 0.0)
    obv = signed_vol.cumsum()

    obv_chg_21 = obv - obv.shift(21)
    vol_sum_21 = volume.rolling(21, min_periods=21).sum()
    obv_norm_chg = obv_chg_21 / vol_sum_21  # OBV change as a fraction of 21d turnover (comparable across stocks)

    price_chg_21 = close / close.shift(21) - 1.0

    # divergence = accumulation strength (OBV) exceeding price strength -> "+"
    # bullish signal not yet reflected in price. Per-date rank difference.
    r_obv = obv_norm_chg.reindex(dates).rank(axis=1, pct=True, na_option="keep")
    r_price = price_chg_21.reindex(dates).rank(axis=1, pct=True, na_option="keep")
    divergence = r_obv - r_price
    s = divergence.stack(future_stack=True) if hasattr(divergence, "stack") else divergence.stack()
    s.index.names = ["date", "symbol"]
    return s.rename("factor")
