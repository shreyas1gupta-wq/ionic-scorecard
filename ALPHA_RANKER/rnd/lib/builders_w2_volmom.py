"""
WAVE-2 worker — money-first refinement of the H004 vol-scaled (Sharpe)
momentum family into a lower-turnover, robust, tradeable factor.

Baseline being refined (rnd/scoreboard.csv / rnd/cards/H004_mom_sharpe12m_1Y.json):
  H004_mom_sharpe12m_1Y: IC_IR 0.789, mono 0.976, hit 75%, turnover 0.268 (resid basis).
Target: keep IC_IR high, cut turnover toward ~0.20.

Four refinements, each layered on the SAME PIT construction as H004
(build_vol_scaled_mom in builders_mom.py: trailing window_days return / panel's
own realized-vol column, index position <= t, no lookahead):

  (a) build_volmom_blend_3_6_12   -- cross-sectional z-score blend of 3/6/12m
      Sharpe-momentum. Averaging three windows smooths idiosyncratic re-ranking
      noise from any single window -> fewer names crossing decile boundaries
      each month -> lower turnover, by construction.
  (b) build_mom_sharpe12m_skip1m  -- skip the most recent 21 trading days
      (classic 12-1 momentum convention) before computing the Sharpe-scaled
      score, to strip short-term reversal contamination from the ranking.
  (c) build_rankband_*            -- rank-band hysteresis: a name's effective
      percentile rank only updates once it MOVES more than `band` from its
      last assigned rank; otherwise it carries forward. This directly targets
      decile-membership churn (the harness's turnover metric = fraction of the
      top-decile set that is NEW each rebalance), independent of any change to
      the underlying signal's informativeness.
  (d) build_mom_sharpe12m_winsor  -- winsorize the vol denominator at the
      [5th,95th] cross-sectional percentile each date before dividing, so a
      near-zero realized-vol print can't blow the ratio into a fake extreme
      score that reverses (and churns) next period.

  (e) build_combo_blend_rankband  -- combine (a)+(c): blend first (smoother
      base signal), then apply rank-band hysteresis on top (further turnover
      cut). Candidate "best of" version.

PIT discipline: reuses _load_cubes/_panel_dates_symbols/_series_from_rows/
build_vol_scaled_mom from builders_mom.py verbatim -- no new lookahead surface.
"""
from __future__ import annotations
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from builders_mom import (  # noqa: E402
    _load_cubes,
    _panel_dates_symbols,
    _series_from_rows,
    build_vol_scaled_mom,
)


# --------------------------------------------------------------------------
# (a) blend of 3/6/12m Sharpe-momentum, cross-sectional z-score per window
#     then averaged (skipna) per (date,symbol).
# --------------------------------------------------------------------------
def build_volmom_blend_3_6_12(panel: pd.DataFrame) -> pd.Series:
    s3 = build_vol_scaled_mom(panel, 63, "vol_63")
    s6 = build_vol_scaled_mom(panel, 126, "vol_126")
    s12 = build_vol_scaled_mom(panel, 252, "vol_252")

    def _zscore_by_date(s: pd.Series) -> pd.Series:
        def _z(g):
            std = g.std(ddof=0)
            return (g - g.mean()) / std if std > 0 else g * 0.0
        return s.groupby(level="date", group_keys=False).apply(_z)

    df = pd.concat({"z3": _zscore_by_date(s3), "z6": _zscore_by_date(s6),
                     "z12": _zscore_by_date(s12)}, axis=1)
    blended = df.mean(axis=1, skipna=True)
    return blended.dropna()


# --------------------------------------------------------------------------
# (b) skip-1m Sharpe-momentum: 12-1 convention applied to the vol-scaled build.
# --------------------------------------------------------------------------
def build_vol_scaled_mom_skip1m(panel: pd.DataFrame, window_days: int, vol_col: str) -> pd.Series:
    close, *_ = _load_cubes()
    dates, symbols = _panel_dates_symbols(panel)
    cols = [s for s in symbols if s in close.columns]
    vol_lookup = panel.set_index(["date", "symbol"])[vol_col]
    rows = []
    for d in dates:
        if d not in close.index:
            continue
        loc = close.index.get_loc(d)
        if loc < window_days + 21:
            continue
        p_t21 = close.iloc[loc - 21][cols]
        p_t0 = close.iloc[loc - 21 - window_days][cols]
        ret = (p_t21 / p_t0 - 1.0).dropna()
        for sym, val in ret.items():
            vol = vol_lookup.get((d, sym), np.nan)
            if pd.isna(vol) or vol <= 0:
                continue
            rows.append((d, sym, val / vol))
    return _series_from_rows(rows)


def build_mom_sharpe12m_skip1m(panel: pd.DataFrame) -> pd.Series:
    return build_vol_scaled_mom_skip1m(panel, 252, "vol_252")


# --------------------------------------------------------------------------
# (c) rank-band rebalancing (hysteresis) applied on top of any base factor.
#     Effective percentile rank only updates once it moves > `band` from the
#     last assigned value for that symbol; else carried forward unchanged.
# --------------------------------------------------------------------------
def apply_rank_band(factor: pd.Series, band: float = 0.10) -> pd.Series:
    f = factor.rename("factor").reset_index()
    f["date"] = pd.to_datetime(f["date"])
    dates = sorted(f["date"].unique())
    last_pct: dict = {}
    rows = []
    for d in dates:
        g = f.loc[f["date"] == d].set_index("symbol")["factor"]
        pct = g.rank(pct=True)
        eff = {}
        for sym, p in pct.items():
            prev = last_pct.get(sym)
            eff[sym] = p if (prev is None or abs(p - prev) > band) else prev
        last_pct.update(eff)
        for sym, val in eff.items():
            rows.append((d, sym, val))
    return _series_from_rows(rows)


def build_rankband_sharpe12m_b05(panel: pd.DataFrame) -> pd.Series:
    base = build_vol_scaled_mom(panel, 252, "vol_252")
    return apply_rank_band(base, band=0.05)


def build_rankband_sharpe12m_b10(panel: pd.DataFrame) -> pd.Series:
    base = build_vol_scaled_mom(panel, 252, "vol_252")
    return apply_rank_band(base, band=0.10)


def build_rankband_sharpe12m_b15(panel: pd.DataFrame) -> pd.Series:
    base = build_vol_scaled_mom(panel, 252, "vol_252")
    return apply_rank_band(base, band=0.15)


# --------------------------------------------------------------------------
# (d) winsorized vol denominator: clip vol_col at cross-sectional [5,95] pct
#     each date before dividing, so a near-zero vol print can't create a fake
#     extreme (and reversal-prone) score.
# --------------------------------------------------------------------------
def build_vol_scaled_mom_winsor(panel: pd.DataFrame, window_days: int, vol_col: str,
                                 lower_q: float = 0.05, upper_q: float = 0.95) -> pd.Series:
    close, *_ = _load_cubes()
    dates, symbols = _panel_dates_symbols(panel)
    cols = [s for s in symbols if s in close.columns]
    vol_by_date = panel.set_index(["date", "symbol"])[vol_col]
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
        vol_d = panel.loc[panel["date"] == d].set_index("symbol")[vol_col]
        if vol_d.dropna().empty:
            continue
        lo, hi = vol_d.quantile(lower_q), vol_d.quantile(upper_q)
        vol_clipped = vol_d.clip(lower=lo, upper=hi)
        for sym, val in ret.items():
            vol = vol_clipped.get(sym, np.nan)
            if pd.isna(vol) or vol <= 0:
                continue
            rows.append((d, sym, val / vol))
    return _series_from_rows(rows)


def build_mom_sharpe12m_winsor(panel: pd.DataFrame) -> pd.Series:
    return build_vol_scaled_mom_winsor(panel, 252, "vol_252")


# --------------------------------------------------------------------------
# (e) combo candidate: blend(3/6/12m) then rank-band hysteresis on top.
# --------------------------------------------------------------------------
def build_combo_blend_rankband(panel: pd.DataFrame, band: float = 0.10) -> pd.Series:
    blended = build_volmom_blend_3_6_12(panel)
    return apply_rank_band(blended, band=band)
