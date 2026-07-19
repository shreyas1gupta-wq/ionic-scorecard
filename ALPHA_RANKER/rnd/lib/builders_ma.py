"""
Moving-average factor builders for H001 (65DMA vs 50DMA), H002 (MA-period
sweep), H042 (slope vs distance robustness).

Built from the CUBE (rnd/panel/cube_close.parquet), not the 751 per-symbol
parquets (per worker brief). All computations use only data <= t (rolling
windows ending at the panel rebalance date), no lookahead.

Each *_factor(...) function returns a `builder(panel_df) -> pd.Series`
closure suitable for `harness.run_experiment(factor_id, builder, horizon, ...)`
or `harness.evaluate(builder(panel), horizon, ...)`.

Definitions (pre-registered in backlog.json, not redefined post-hoc):
  - distance  = close(t) / MA_N(t) - 1                      (dist_from_NDMA)
  - slope     = MA_N(t) / MA_N(t - LOOKBACK) - 1            (LOOKBACK=21 trading
                days ~ 1 month; matches the "200dMA rising >=22 sessions"
                convention already in FRAMEWORK_CATALOG's Minervini entry)
  - stack     = count of {close>MA_fast, MA_fast>MA_mid, MA_mid>MA_slow}
                (0-3 ordinal "bullish alignment" score; mid=150, slow=200
                fixed per H001's "65>150>200 stack vs 50>150>200" construct)
"""
from __future__ import annotations

import functools
from pathlib import Path

import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent  # ALPHA_RANKER/rnd
CUBE_CLOSE_PATH = RND_DIR / "panel" / "cube_close.parquet"

SLOPE_LOOKBACK_DEFAULT = 21  # trading days (~1 month)
STACK_MID_N = 150
STACK_SLOW_N = 200


@functools.lru_cache(maxsize=1)
def load_close_cube() -> pd.DataFrame:
    df = pd.read_parquet(CUBE_CLOSE_PATH)
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


@functools.lru_cache(maxsize=None)
def _ma(n: int) -> pd.DataFrame:
    close = load_close_cube()
    return close.rolling(window=n, min_periods=n).mean()


def _panel_dates(panel_df: pd.DataFrame) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(sorted(pd.to_datetime(panel_df["date"].unique())))


def _to_long_factor(wide: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.Series:
    sub = wide.reindex(dates)
    f = sub.stack()  # drops NaN by default
    f.index.names = ["date", "symbol"]
    return f.rename("factor")


def dma_distance_factor(n: int):
    """distance = close/MA_n - 1, evaluated at panel rebalance dates."""
    def builder(panel_df: pd.DataFrame) -> pd.Series:
        close = load_close_cube()
        ma = _ma(n)
        dist = close / ma - 1.0
        return _to_long_factor(dist, _panel_dates(panel_df))
    builder.__name__ = f"dma_distance_{n}"
    return builder


def dma_slope_factor(n: int, lookback: int = SLOPE_LOOKBACK_DEFAULT):
    """slope = MA_n(t)/MA_n(t-lookback) - 1, evaluated at panel rebalance dates."""
    def builder(panel_df: pd.DataFrame) -> pd.Series:
        ma = _ma(n)
        slope = ma / ma.shift(lookback) - 1.0
        return _to_long_factor(slope, _panel_dates(panel_df))
    builder.__name__ = f"dma_slope_{n}_{lookback}"
    return builder


def dma_flag_factor(n: int):
    """price>MA boolean flag (0/1): close(t) > MA_n(t). Added for W2 MA-sweep
    (65DMA-vs-50DMA crowding deep-dive) -- distinct from dma_stack_factor's
    first term, evaluated standalone so its own IC/mono/turnover can be read
    in isolation rather than folded into the 3-term stack score."""
    def builder(panel_df: pd.DataFrame) -> pd.Series:
        close = load_close_cube()
        ma = _ma(n)
        flag = (close > ma).astype(float).where(ma.notna())
        return _to_long_factor(flag, _panel_dates(panel_df))
    builder.__name__ = f"dma_flag_{n}"
    return builder


def dma_stack_factor(fast_n: int, mid_n: int = STACK_MID_N, slow_n: int = STACK_SLOW_N):
    """ordinal 0-3 bullish-alignment score: close>MA_fast, MA_fast>MA_mid, MA_mid>MA_slow."""
    def builder(panel_df: pd.DataFrame) -> pd.Series:
        close = load_close_cube()
        ma_fast = _ma(fast_n)
        ma_mid = _ma(mid_n)
        ma_slow = _ma(slow_n)
        score = (close > ma_fast).astype(int) + (ma_fast > ma_mid).astype(int) + (ma_mid > ma_slow).astype(int)
        score = score.where(ma_fast.notna() & ma_mid.notna() & ma_slow.notna())
        return _to_long_factor(score, _panel_dates(panel_df))
    builder.__name__ = f"dma_stack_{fast_n}_{mid_n}_{slow_n}"
    return builder
