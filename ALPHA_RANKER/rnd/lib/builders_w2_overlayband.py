"""
WAVE-3 fix pass: rank-band hysteresis (+ slower p_bear) applied to the
continuous regime-probability overlay (builders_w2_contoverlay.py).

MOTIVATION (rnd/CONSOLIDATION.md, rnd/reports/W2_contoverlay_results.json):
the continuous overlay WINS on signal in bears -- 21yr 1Y card
W2_contoverlay_cont_long_1Y: ic_ir 1.178, bear-regime IC +0.222 vs
W2_contoverlay_staticmom_long_1Y bear-regime IC +0.038 (~6x) -- but LOSES
net-of-cost because its turnover (0.314) is HIGHER than static momentum's
(0.262). Same shape of problem builders_w2_volmom.py already solved for the
vol-scaled-momentum family (turnover 0.27 -> 0.17) via rank-band hysteresis.
Goal here: reuse that exact trick on the overlay's blended factor, so
turnover falls toward ~0.26 while most of the bear-IC edge survives.

TWO INDEPENDENT LEVERS, testable alone or combined:

  (1) RANK-BAND HYSTERESIS on the blended factor -- apply_rank_band imported
      VERBATIM from builders_w2_volmom.py (no redefinition, no new lookahead
      surface). Turns the continuous blended score into a percentile rank
      that only updates once it moves > band from its last assigned value
      per symbol; else carries forward. Bands tested: 0.05 / 0.10 / 0.15,
      same grid already validated for vol-mom.

  (2) SLOWER p_bear -- builders_w2_contoverlay.regime_score_for_dates()
      merge_asof-backwards the DAILY continuous score onto rebalance dates.
      A name's re-tilt trigger is the day-to-day wiggle in that daily score.
      continuous_score_daily_smoothed() takes the IDENTICAL causal sigmoid
      score chain (sigmoid(trend_z - 2*(vol_pct-0.5)), unchanged) and applies
      a TRAILING rolling mean (rolling(smooth_days, min_periods=1).mean(),
      uses only rows with date <= t by construction) as the very last step
      before the merge_asof-backward onto panel dates. This slows down how
      fast the mom/def mix can move, independent of any rank-band on the
      blended output -- no new causality surface, purely a trailing filter
      on an already-causal series.

Both levers can be combined: slow-scored blend, THEN rank-band on top
(build_overlay_slowscore_band_*) -- the "combo" candidate, same pattern as
builders_w2_volmom.build_combo_blend_rankband.

PIT discipline: every building block here is either imported unchanged from
builders_w2_contoverlay.py / builders_w2_volmom.py, or a trailing-only
rolling transform of an already-audited causal series. No new panel reads,
no new joins.
"""
from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import builders_w2_contoverlay as CO          # noqa: E402
from builders_w2_volmom import apply_rank_band  # noqa: E402


# --------------------------------------------------------------------------
# lever (2): slower p_bear -- trailing-smoothed daily regime score
# --------------------------------------------------------------------------
def continuous_score_daily_smoothed(smooth_days: int = 63, min_periods: int = 60) -> pd.DataFrame:
    """Same causal sigmoid regime score as CO.continuous_score_daily, trailing-
    smoothed with a rolling mean over `smooth_days` (rolling().mean() at row t
    uses only rows <= t -- no forward information added by the smoothing)."""
    df = CO.continuous_score_daily(min_periods=min_periods).copy()
    df["regime_score"] = df["regime_score"].rolling(smooth_days, min_periods=1).mean()
    return df


def regime_score_for_dates_slow(panel_dates, smooth_days: int = 63) -> pd.Series:
    daily = continuous_score_daily_smoothed(smooth_days=smooth_days)
    daily["date"] = daily["date"].astype("datetime64[ns]")
    dates_df = pd.DataFrame({"date": pd.DatetimeIndex(sorted(pd.to_datetime(pd.Series(panel_dates)).unique()))})
    dates_df["date"] = dates_df["date"].astype("datetime64[ns]")
    merged = pd.merge_asof(dates_df, daily, on="date", direction="backward")
    return merged.set_index("date")["regime_score"]


# --------------------------------------------------------------------------
# SHORT panel (panel.parquet)
# --------------------------------------------------------------------------
def build_overlay_band_short(panel: pd.DataFrame, band: float) -> pd.Series:
    raw = CO.build_continuous_overlay_short(panel)
    return apply_rank_band(raw, band=band)


def build_overlay_band_short_b05(panel: pd.DataFrame) -> pd.Series:
    return build_overlay_band_short(panel, 0.05)


def build_overlay_band_short_b10(panel: pd.DataFrame) -> pd.Series:
    return build_overlay_band_short(panel, 0.10)


def build_overlay_band_short_b15(panel: pd.DataFrame) -> pd.Series:
    return build_overlay_band_short(panel, 0.15)


def build_overlay_slowscore_short(panel: pd.DataFrame, smooth_days: int = 63) -> pd.Series:
    mom_tilt = CO.build_momentum_tilt_short(panel)
    def_tilt = CO.build_defensive_tilt_short(panel)
    score = regime_score_for_dates_slow(panel["date"], smooth_days=smooth_days)
    return CO._blend(mom_tilt, def_tilt, score)


def build_overlay_slowscore_band_short(panel: pd.DataFrame, smooth_days: int = 63, band: float = 0.10) -> pd.Series:
    raw = build_overlay_slowscore_short(panel, smooth_days=smooth_days)
    return apply_rank_band(raw, band=band)


# --------------------------------------------------------------------------
# LONG panel (panel_long.parquet)
# --------------------------------------------------------------------------
def build_overlay_band_long(panel: pd.DataFrame, band: float) -> pd.Series:
    raw = CO.build_continuous_overlay_long(panel)
    return apply_rank_band(raw, band=band)


def build_overlay_band_long_b05(panel: pd.DataFrame) -> pd.Series:
    return build_overlay_band_long(panel, 0.05)


def build_overlay_band_long_b10(panel: pd.DataFrame) -> pd.Series:
    return build_overlay_band_long(panel, 0.10)


def build_overlay_band_long_b15(panel: pd.DataFrame) -> pd.Series:
    return build_overlay_band_long(panel, 0.15)


def build_overlay_slowscore_long(panel: pd.DataFrame, smooth_days: int = 63) -> pd.Series:
    mom_tilt = CO.build_momentum_tilt_long(panel)
    def_tilt = CO.build_defensive_tilt_long(panel)
    score = regime_score_for_dates_slow(panel["date"], smooth_days=smooth_days)
    return CO._blend(mom_tilt, def_tilt, score)


def build_overlay_slowscore_band_long(panel: pd.DataFrame, smooth_days: int = 63, band: float = 0.10) -> pd.Series:
    raw = build_overlay_slowscore_long(panel, smooth_days=smooth_days)
    return apply_rank_band(raw, band=band)
