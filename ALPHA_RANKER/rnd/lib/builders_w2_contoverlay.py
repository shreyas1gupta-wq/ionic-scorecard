"""
WAVE-3 worker: CONTINUOUS regime-PROBABILITY overlay -- the fix for
builders_w2_regimeswitch.py's discrete switch, per CONSOLIDATION.md REGIME MAP
caveat: "the naive DISCRETE regime-switch does NOT beat holding momentum
(doubles turnover, eats the gain) ... FIX for wave-3: continuous regime-
PROBABILITY overlay (magnitude-preserving) + re-test on the 21-yr panel where
bears are plentiful."

CONTINUOUS REGIME SCORE (date-level, causal by construction)
--------------------------------------------------------------------------
Built off results/regime_timeline.parquet (daily), reusing its already-audited
causal columns (src/regime/regime_classifier.py: ma200 = rolling(200,
min_periods=200).mean() -- trailing only; rv21_ann = rolling(21).std()*sqrt(252)
-- trailing only; both use data <= t by construction, never re-derived here):
  trend_strength(t) = nifty500(t)/ma200(t) - 1
  trend_z(t)        = EXPANDING (causal) z-score of trend_strength, i.e. only
                       trend_strength[0..t] feeds the mean/std used at t
  vol_pct(t)         = EXPANDING (causal) percentile rank of rv21_ann, i.e.
                       "what fraction of ALL rv21_ann values seen up to and
                       including t are below today's" -- same construction as
                       market_state.py's EY_hist_pctrank_expanding
  regime_score(t)    = sigmoid(trend_z(t) - 2*(vol_pct(t) - 0.5))  in (0,1)
       high score  = bull + calm  -> favor momentum
       low score   = bear + vol   -> favor defensive
No forward information anywhere in this chain -- score(t) is a function of
regime_timeline rows with date <= t only. Merged onto panel rebalance dates via
merge_asof(direction='backward'): the score used at rebalance date t is the
nearest PRIOR daily score, identical PIT contract to panel['regime_trend'] /
['regime_vol'] documented in PANEL_SCHEMA.md.

BLEND (magnitude-preserving, low-turnover by construction)
--------------------------------------------------------------------------
factor(t,i) = score(t)*mom_tilt(t,i) + (1-score(t))*def_tilt(t,i), where both
tilts are cross-sectionally z-scored per date BEFORE the blend (same
_avg_z/_zscore_by_date convention as builders_w2_regimeswitch.py) -- a convex
combination of two z-scored series never blows up scale, and because score(t)
is a smooth sigmoid of continuously-evolving inputs (not a 3-bucket step
function), the effective momentum/defensive mix drifts gently day to day
instead of jumping wholesale at a bucket boundary. That gradual drift is the
literal mechanism by which this is expected to cut the discrete switch's
turnover problem (CONSOLIDATION.md: switch "doubles turnover, eats the gain").

DEFENSIVE TILT INCLUDES VALUE (disclosed deviation from the discrete switch)
--------------------------------------------------------------------------
builders_w2_regimeswitch.build_defensive_tilt() deliberately EXCLUDED earnings
yield because in that 5yr (2021-26) sample EY looked bull-favoring (ic_bull
+0.065 > ic_bear -0.005 per its own docstring). CONSOLIDATION.md's durable-
model section, built from the FULL 21yr confirmation, says the opposite is
true across real cycles: EY is "the defensive workhorse ... HIGHER IC in bears
(0.156) than bulls (0.042)". Since this overlay is explicitly being re-tested
on the 21yr panel where bears are real and plentiful, repeating the 5yr
sample's narrow exclusion would silently re-import a bull-only artifact into a
bear-test. EY (H014) is added into the defensive tilt's z-avg here.

TWO PANELS, TWO IMPLEMENTATIONS
--------------------------------------------------------------------------
builders_mom.py / builders_ma.py / builders_value.py hard-code the SHORT price
cube (rnd/panel/cube_close.parquet, 2021-07->2026-07) -- they cannot be reused
as-is against panel_long.parquet (21yr, 2005-04->2025-12), which needs
cube_close_long.parquet. The short-panel functions below reuse those existing
modules directly; the long-panel functions replicate the identical factor
definitions against the long cube, following the same pattern already used
and disclosed in rnd/run_long_confirm.py (the WAVE-2 21yr bear-confirmation
worker) for MA-stack/slope/vol-scaled-mom/earnings-yield. build_h010_lowvol/
build_h011_idiovol (builders_vol.py) read panel columns (vol_252/idio_vol_252)
directly, not a cube, so they work unmodified on EITHER panel.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent          # ALPHA_RANKER/rnd
ALPHA_DIR = RND_DIR.parent              # ALPHA_RANKER
REGIME_TIMELINE_PATH = ALPHA_DIR / "results" / "regime_timeline.parquet"
CUBE_CLOSE_LONG = RND_DIR / "panel" / "cube_close_long.parquet"
FUND_PATH = ALPHA_DIR / "data" / "fundamentals" / "MASTER_fundamentals_pit.parquet"

from builders_mom import build_mom_sharpe_12m
from builders_ma import dma_stack_factor, dma_slope_factor
from builders_vol import build_h010_lowvol, build_h011_idiovol
from builders_value import build_H014_earnings_yield

_STACK_65 = dma_stack_factor(65)
_SLOPE_200 = dma_slope_factor(200, 21)

_LONG_CACHE: dict = {}


# --------------------------------------------------------------------------
# shared small utilities (same convention as builders_w2_regimeswitch.py)
# --------------------------------------------------------------------------
def _zscore_by_date(s: pd.Series) -> pd.Series:
    return s.groupby(level="date").transform(lambda x: (x - x.mean()) / (x.std(ddof=0) or float("nan")))


def _avg_z(components: list[pd.Series]) -> pd.Series:
    z = [_zscore_by_date(c) for c in components]
    df = pd.concat(z, axis=1, join="inner")
    return df.mean(axis=1).rename("factor")


# --------------------------------------------------------------------------
# continuous regime score (date-only, shared by both panels)
# --------------------------------------------------------------------------
def _load_regime_timeline() -> pd.DataFrame:
    df = pd.read_parquet(REGIME_TIMELINE_PATH, columns=["date", "nifty500", "ma200", "rv21_ann"])
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def continuous_score_daily(min_periods: int = 60) -> pd.DataFrame:
    """Daily continuous regime score in (0,1). See module docstring for the
    full causality argument. Returns columns [date, regime_score]."""
    df = _load_regime_timeline()
    trend = df["nifty500"] / df["ma200"] - 1.0
    trend_mean = trend.expanding(min_periods=min_periods).mean()
    trend_std = trend.expanding(min_periods=min_periods).std()
    trend_z = (trend - trend_mean) / trend_std

    rv = df["rv21_ann"]
    vol_pct = rv.expanding(min_periods=min_periods).apply(
        lambda s: (s.iloc[-1] > s.iloc[:-1]).mean() if len(s) > 1 else np.nan, raw=False
    )
    raw = trend_z - 2.0 * (vol_pct - 0.5)
    score = 1.0 / (1.0 + np.exp(-raw))
    out = pd.DataFrame({"date": df["date"], "regime_score": score})
    return out.dropna(subset=["regime_score"]).reset_index(drop=True)


def regime_score_for_dates(panel_dates) -> pd.Series:
    """merge_asof-backward the daily continuous score onto panel rebalance
    dates: score used at t is the nearest PRIOR daily score, never a future
    one. Same PIT contract as regime_trend/regime_vol (PANEL_SCHEMA.md)."""
    daily = continuous_score_daily()
    daily["date"] = daily["date"].astype("datetime64[ns]")
    dates_df = pd.DataFrame({"date": pd.DatetimeIndex(sorted(pd.to_datetime(pd.Series(panel_dates)).unique()))})
    dates_df["date"] = dates_df["date"].astype("datetime64[ns]")
    merged = pd.merge_asof(dates_df, daily, on="date", direction="backward")
    return merged.set_index("date")["regime_score"]


def _blend(mom_tilt: pd.Series, def_tilt: pd.Series, score_by_date: pd.Series) -> pd.Series:
    both = pd.concat([mom_tilt.rename("mom"), def_tilt.rename("def")], axis=1, join="inner").reset_index()
    both["w_mom"] = both["date"].map(score_by_date)
    both = both.dropna(subset=["w_mom"])
    both["factor"] = both["mom"] * both["w_mom"] + both["def"] * (1.0 - both["w_mom"])
    return both.set_index(["date", "symbol"])["factor"]


# --------------------------------------------------------------------------
# SHORT panel (panel.parquet + cube_close.parquet)
# --------------------------------------------------------------------------
def build_momentum_tilt_short(panel: pd.DataFrame) -> pd.Series:
    mom = build_mom_sharpe_12m(panel)
    stack = _STACK_65(panel)
    slope = _SLOPE_200(panel)
    return _avg_z([mom, stack, slope])


def build_defensive_tilt_short(panel: pd.DataFrame) -> pd.Series:
    lowvol = build_h010_lowvol(panel)
    idiovol = build_h011_idiovol(panel)
    beta = panel[["date", "symbol", "beta_252"]].dropna(subset=["beta_252"]).copy()
    beta["factor"] = -beta["beta_252"]
    inv_beta = beta.set_index(["date", "symbol"])["factor"]
    ey = build_H014_earnings_yield(panel)
    return _avg_z([lowvol, idiovol, inv_beta, ey])


def build_continuous_overlay_short(panel: pd.DataFrame) -> pd.Series:
    mom_tilt = build_momentum_tilt_short(panel)
    def_tilt = build_defensive_tilt_short(panel)
    score = regime_score_for_dates(panel["date"])
    return _blend(mom_tilt, def_tilt, score)


def build_static_momentum_short(panel: pd.DataFrame) -> pd.Series:
    return build_momentum_tilt_short(panel)


# --------------------------------------------------------------------------
# LONG panel (panel_long.parquet + cube_close_long.parquet) -- hand-rolled,
# same definitions, following rnd/run_long_confirm.py's established pattern.
# --------------------------------------------------------------------------
def _load_long_cube() -> pd.DataFrame:
    if "close" not in _LONG_CACHE:
        close = pd.read_parquet(CUBE_CLOSE_LONG)
        close.index = pd.to_datetime(close.index)
        _LONG_CACHE["close"] = close
    return _LONG_CACHE["close"]


def _panel_dates(panel_df: pd.DataFrame) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(sorted(pd.to_datetime(panel_df["date"].unique())))


def _to_long_factor(wide: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.Series:
    sub = wide.reindex(dates)
    f = sub.stack()
    f.index.names = ["date", "symbol"]
    return f.rename("factor")


def _dma_stack_long(close, dates, fast_n, mid_n=150, slow_n=200):
    ma_fast = close.rolling(fast_n, min_periods=fast_n).mean()
    ma_mid = close.rolling(mid_n, min_periods=mid_n).mean()
    ma_slow = close.rolling(slow_n, min_periods=slow_n).mean()
    score = (close > ma_fast).astype(int) + (ma_fast > ma_mid).astype(int) + (ma_mid > ma_slow).astype(int)
    score = score.where(ma_fast.notna() & ma_mid.notna() & ma_slow.notna())
    return _to_long_factor(score, dates)


def _dma_slope_long(close, dates, n, lookback=21):
    ma = close.rolling(n, min_periods=n).mean()
    slope = ma / ma.shift(lookback) - 1.0
    return _to_long_factor(slope, dates)


def _vol_scaled_mom_long(panel, close, dates, window_days=252, vol_col="vol_252"):
    vol_lookup = panel.set_index(["date", "symbol"])[vol_col]
    rows = []
    idx = close.index
    for d in dates:
        if d not in idx:
            continue
        loc = idx.get_loc(d)
        if loc < window_days:
            continue
        p_t = close.iloc[loc]
        p_t0 = close.iloc[loc - window_days]
        ret = (p_t / p_t0 - 1.0).dropna()
        for sym, val in ret.items():
            vol = vol_lookup.get((d, sym), np.nan)
            if pd.isna(vol) or vol <= 0:
                continue
            rows.append((d, sym, val / vol))
    out = pd.DataFrame(rows, columns=["date", "symbol", "factor"])
    return out.set_index(["date", "symbol"])["factor"]


def _earnings_yield_long(panel, dates):
    ds = panel[["date", "symbol"]].drop_duplicates()
    fund = pd.read_parquet(FUND_PATH)
    fund = fund[fund["nse_symbol"].notna()].copy()
    fund["available_date"] = pd.to_datetime(fund["available_date"])
    eps = fund[fund["metric_norm"] == "eps in rs"].dropna(subset=["value", "available_date"]).copy()
    eps = eps.sort_values(["nse_symbol", "fiscal_year", "is_fresh", "available_date"])
    eps = eps.drop_duplicates(["nse_symbol", "fiscal_year"], keep="last")
    eps = eps[["nse_symbol", "value", "available_date"]].rename(
        columns={"nse_symbol": "symbol", "value": "eps_ttm", "available_date": "date"}).sort_values("date")

    left = ds.sort_values("date").copy()
    left["symbol"] = left["symbol"].astype(str)
    right = eps.copy()
    right["symbol"] = right["symbol"].astype(str)
    m = pd.merge_asof(left, right, on="date", by="symbol", direction="backward")

    close = _load_long_cube()
    idx_name = close.index.name or "index"
    price_long = close.reset_index().melt(id_vars=idx_name, var_name="symbol", value_name="price")
    price_long = price_long.rename(columns={idx_name: "date"})
    price_long["date"] = pd.to_datetime(price_long["date"])
    price_long = price_long.dropna(subset=["price"])

    mm = m.merge(price_long, on=["date", "symbol"], how="inner")
    mm = mm[(mm["price"] > 0) & mm["eps_ttm"].notna()]
    mm["factor"] = mm["eps_ttm"] / mm["price"]
    return mm.set_index(["date", "symbol"])["factor"].replace([np.inf, -np.inf], np.nan).dropna()


def build_momentum_tilt_long(panel: pd.DataFrame) -> pd.Series:
    close = _load_long_cube()
    dates = _panel_dates(panel)
    mom = _vol_scaled_mom_long(panel, close, dates, 252, "vol_252")
    stack = _dma_stack_long(close, dates, fast_n=65)
    slope = _dma_slope_long(close, dates, n=200, lookback=21)
    return _avg_z([mom, stack, slope])


def build_defensive_tilt_long(panel: pd.DataFrame) -> pd.Series:
    lowvol = build_h010_lowvol(panel)
    idiovol = build_h011_idiovol(panel)
    beta = panel[["date", "symbol", "beta_252"]].dropna(subset=["beta_252"]).copy()
    beta["factor"] = -beta["beta_252"]
    inv_beta = beta.set_index(["date", "symbol"])["factor"]
    ey = _earnings_yield_long(panel, _panel_dates(panel))
    return _avg_z([lowvol, idiovol, inv_beta, ey])


def build_continuous_overlay_long(panel: pd.DataFrame) -> pd.Series:
    mom_tilt = build_momentum_tilt_long(panel)
    def_tilt = build_defensive_tilt_long(panel)
    score = regime_score_for_dates(panel["date"])
    return _blend(mom_tilt, def_tilt, score)


def build_static_momentum_long(panel: pd.DataFrame) -> pd.Series:
    return build_momentum_tilt_long(panel)


def build_discrete_switch_long(panel: pd.DataFrame, switch_col: str = "regime_trend") -> pd.Series:
    """Discrete-switch comparator on the 21yr panel -- none existed before
    (builders_w2_regimeswitch.py hard-codes the short cube). Same weight map
    as the short-panel discrete switch: bull->100% momentum, bear->100%
    defensive, sideways->50/50. This IS the model the continuous overlay must
    beat on the 21yr sample, replicated apples-to-apples."""
    mom_tilt = build_momentum_tilt_long(panel)
    def_tilt = build_defensive_tilt_long(panel)
    both = pd.concat([mom_tilt.rename("mom"), def_tilt.rename("def")], axis=1, join="inner")
    regime = panel[["date", switch_col]].drop_duplicates("date").set_index("date")[switch_col]
    both = both.reset_index()
    weight_map = {"bull": (1.0, 0.0), "bear": (0.0, 1.0), "sideways": (0.5, 0.5)}
    both["w_mom"] = both["date"].map(regime).map(lambda r: weight_map.get(r, (0.5, 0.5))[0])
    both["w_def"] = both["date"].map(regime).map(lambda r: weight_map.get(r, (0.5, 0.5))[1])
    both["factor"] = both["mom"] * both["w_mom"] + both["def"] * both["w_def"]
    return both.set_index(["date", "symbol"])["factor"]
