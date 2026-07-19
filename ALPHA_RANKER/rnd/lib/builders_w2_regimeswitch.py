"""
WAVE-2 worker: regime-SWITCHED composite vs its static parent (K-015 discipline
-- an overlay must beat what it replaces, or it is worthless).

Uses only PIT-causal inputs: panel['regime_trend'] / panel['regime_vol'] are
merge_asof-backward (nearest-PRIOR label as of t, see PANEL_SCHEMA.md) -- the
label used to pick the blend at date t never looks past t. Regime is constant
across all symbols within a date (verified: 0 dates with >1 distinct label),
so the switch is a pure date-level gate, not a symbol-level lookahead vector.

Empirical regime map (from rnd/scoreboard.csv, this sample, given by RP):
  momentum/trend family (H004 mom-sharpe, H001/H002 dma stack/slope) ->
      POSITIVE ic_bull, NEGATIVE ic_bear.
  low-vol/idio-vol/low-beta family (H010/H011, -beta_252) ->
      POSITIVE ic_bear & ic_hivol (even where UNCONDITIONAL ic_ir is negative,
      e.g. H010_lowvol_1Y ic_ir=-0.32 overall but ic_bear=+0.005, ic_hivol=+0.051
      -- exactly the profile where a regime switch could add value a static
      factor cannot capture).

Composites are equal-weight, cross-sectional z-scored per date (no learned
weights, no TRAIN/OOS split needed for the tilts themselves since z-scoring
and equal-weighting use no forward information at all -- only the SWITCH
labels, which are already PIT-safe panel columns). Never touches weights;
writes only via harness.evaluate()/run_experiment().
"""
from __future__ import annotations

import pandas as pd

from builders_mom import build_mom_sharpe_12m
from builders_ma import dma_stack_factor, dma_slope_factor
from builders_vol import build_h010_lowvol, build_h011_idiovol

_STACK_65 = dma_stack_factor(65)          # matches H001_stack65
_SLOPE_200 = dma_slope_factor(200, 21)    # matches H002_slope200 (best 1M candidate)


def _zscore_by_date(s: pd.Series) -> pd.Series:
    return s.groupby(level="date").transform(lambda x: (x - x.mean()) / (x.std(ddof=0) or float("nan")))


def _avg_z(components: list[pd.Series]) -> pd.Series:
    """Inner-join (date,symbol) index across components, z-score each per date,
    then equal-weight average. Inner join means a name only gets a composite
    score on dates where ALL legs are populated -- conservative, no silent
    fill of missing legs."""
    z = [_zscore_by_date(c) for c in components]
    df = pd.concat(z, axis=1, join="inner")
    return df.mean(axis=1).rename("factor")


# --------------------------------------------------------------------------
# Tilts (the two regime-conditional blends)
# --------------------------------------------------------------------------
def build_momentum_tilt(panel: pd.DataFrame) -> pd.Series:
    """Momentum/trend tilt: equal-weight z-avg of mom_sharpe_12m (H004),
    dma_stack_65 (H001), dma_slope_200 (H002) -- the three best-scoring
    momentum-family factors in the scoreboard at the 1M horizon."""
    mom = build_mom_sharpe_12m(panel)
    stack = _STACK_65(panel)
    slope = _SLOPE_200(panel)
    return _avg_z([mom, stack, slope])


def build_defensive_tilt(panel: pd.DataFrame) -> pd.Series:
    """Defensive tilt: equal-weight z-avg of -vol_252 (H010 lowvol),
    -idio_vol_252 (H011), -beta_252 (low-beta, direct from panel, sign-
    oriented so higher=hypothesized higher forward return, matching H010/H011
    convention). No value leg: scoreboard shows H030 value_only is a BULL
    factor here (ic_bull=+0.065, ic_bear=-0.005), not bear/hivol-positive --
    including it in "defensive" would contradict this sample's own evidence,
    so it is deliberately left out (disclosed deviation from the generic
    low-vol/low-beta/value description in the task brief)."""
    lowvol = build_h010_lowvol(panel)
    idiovol = build_h011_idiovol(panel)
    beta = panel[["date", "symbol", "beta_252"]].dropna(subset=["beta_252"]).copy()
    beta["factor"] = -beta["beta_252"]
    inv_beta = beta.set_index(["date", "symbol"])["factor"]
    return _avg_z([lowvol, idiovol, inv_beta])


# --------------------------------------------------------------------------
# Static parent (equal-weight, unconditional -- what the switch must beat)
# --------------------------------------------------------------------------
def build_static_composite(panel: pd.DataFrame) -> pd.Series:
    """Static equal-weight composite of the SAME 6 underlying legs used by
    the two tilts (3 momentum + 3 defensive), with NO regime conditioning --
    the direct static parent the switched model is required to beat."""
    mom = build_mom_sharpe_12m(panel)
    stack = _STACK_65(panel)
    slope = _SLOPE_200(panel)
    lowvol = build_h010_lowvol(panel)
    idiovol = build_h011_idiovol(panel)
    beta = panel[["date", "symbol", "beta_252"]].dropna(subset=["beta_252"]).copy()
    beta["factor"] = -beta["beta_252"]
    inv_beta = beta.set_index(["date", "symbol"])["factor"]
    return _avg_z([mom, stack, slope, lowvol, idiovol, inv_beta])


# --------------------------------------------------------------------------
# The switch itself
# --------------------------------------------------------------------------
_TREND_WEIGHT = {"bull": (1.0, 0.0), "bear": (0.0, 1.0), "sideways": (0.5, 0.5)}
_VOL_WEIGHT = {"low": (1.0, 0.0), "high": (0.0, 1.0), "normal": (0.5, 0.5)}


def _build_switched(panel: pd.DataFrame, switch_col: str, weight_map: dict) -> pd.Series:
    mom_tilt = build_momentum_tilt(panel)
    def_tilt = build_defensive_tilt(panel)
    both = pd.concat([mom_tilt.rename("mom"), def_tilt.rename("def")], axis=1, join="inner")
    regime = panel[["date", switch_col]].drop_duplicates("date").set_index("date")[switch_col]
    both = both.reset_index()
    both["w_mom"] = both["date"].map(regime).map(lambda r: weight_map.get(r, (0.5, 0.5))[0])
    both["w_def"] = both["date"].map(regime).map(lambda r: weight_map.get(r, (0.5, 0.5))[1])
    both["factor"] = both["mom"] * both["w_mom"] + both["def"] * both["w_def"]
    return both.set_index(["date", "symbol"])["factor"]


def build_regime_switched_trend(panel: pd.DataFrame) -> pd.Series:
    """Switch on regime_trend: bull -> 100% momentum tilt, bear -> 100%
    defensive tilt, sideways -> 50/50 blend (disclosed middle-ground choice,
    not a pre-registered third state in the task brief but the only sane
    default for a 3-state variable with 2 named tilts)."""
    return _build_switched(panel, "regime_trend", _TREND_WEIGHT)


def build_regime_switched_vol(panel: pd.DataFrame) -> pd.Series:
    """Switch on regime_vol: low -> 100% momentum tilt, high -> 100% defensive
    tilt, normal -> 50/50 blend."""
    return _build_switched(panel, "regime_vol", _VOL_WEIGHT)
