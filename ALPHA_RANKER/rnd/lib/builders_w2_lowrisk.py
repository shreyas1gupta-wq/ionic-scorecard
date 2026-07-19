"""
WAVE worker — low-risk / lottery factor builders (backlog_scout.json IDG-G-06,
IDG-G-07, IDG-G-09). Money-first loop: defensive, regime-conditional,
NEGATIVE-sign factors (raw factor UP -> forward return DOWN is the hypothesis
itself for all three).

Uses `rnd/panel/panel_long.parquet` (21yr, 249 monthly dates, 2005-2025) NOT
the short 5yr panel.parquet -- per this pass's brief, so the per-regime
breakdown (esp. bear-market defense) has real bear-month coverage (19,098
bear-labelled rows in panel_long vs only a handful of bear months in the
short panel).

Factors:
  IDG-G-06  BAB (Frazzini-Pedersen):     raw panel_long['beta_252']    (sign -)
  IDG-G-07  Idio-vol anomaly (AHXZ):     raw panel_long['idio_vol_252'] (sign -)
  IDG-G-09  MAX lottery-demand (BCW):    max single daily return over trailing
                                         21 sessions, built from
                                         rnd/panel/cube_close_long.parquet
                                         (price-only, independent of the panel
                                         columns -- a genuine build, not a
                                         tautology).                  (sign -)

All three builders return the RAW (un-negated, un-z-scored) factor. Spearman
IC in harness.evaluate() is rank-based, so z-scoring is a no-op for IC/decile
math; sign correction for the money-first scoreboard is applied downstream by
pragmatic_score_v2.py's NEGATIVE_KEYWORDS list ("bab", "idio_vol"/"idiovol",
"lottery"/"max_lottery" are all already registered there), keyed off the
factor_id/family strings this module's runner uses -- so name cards/families
to CONTAIN those substrings, don't rely on this module to flip sign.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
PANEL_DIR = RND_DIR / "panel"

_CUBE_CLOSE_LONG = None
_DAILY_RET_LONG = None


def load_panel_long() -> pd.DataFrame:
    """The 21yr companion panel (see PANEL_SCHEMA.md addendum)."""
    return pd.read_parquet(PANEL_DIR / "panel_long.parquet")


def _load_cube_long():
    global _CUBE_CLOSE_LONG, _DAILY_RET_LONG
    if _CUBE_CLOSE_LONG is None:
        _CUBE_CLOSE_LONG = pd.read_parquet(PANEL_DIR / "cube_close_long.parquet")
        _DAILY_RET_LONG = _CUBE_CLOSE_LONG.pct_change()
    return _CUBE_CLOSE_LONG, _DAILY_RET_LONG


def _panel_dates_symbols(panel: pd.DataFrame):
    dates = sorted(pd.to_datetime(panel["date"].unique()))
    symbols = sorted(panel["symbol"].unique())
    return dates, symbols


# --------------------------------------------------------------------------
# IDG-G-06: BAB -- panel_long beta_252 cross-sectional rank per date.
# Long-only low-beta tilt per construct = score -z(beta_252); we return RAW
# beta_252 (harness rank-IC is sign-agnostic to z-scoring) and let the
# money-first scorer apply the "-" expected sign via the "bab" keyword.
# --------------------------------------------------------------------------
def build_bab_beta(panel: pd.DataFrame) -> pd.Series:
    f = panel.set_index(["date", "symbol"])["beta_252"].dropna()
    return f.rename("factor")


# --------------------------------------------------------------------------
# IDG-G-07: idiosyncratic-vol anomaly -- panel_long idio_vol_252 (residual
# vol from the trailing FF6 regression, already built into the panel).
# --------------------------------------------------------------------------
def build_idiovol(panel: pd.DataFrame) -> pd.Series:
    f = panel.set_index(["date", "symbol"])["idio_vol_252"].dropna()
    return f.rename("factor")


# --------------------------------------------------------------------------
# IDG-G-09: MAX lottery-demand (Bali-Cakici-Whitelaw) -- max single-day
# return over the trailing 21 sessions ending at (and including) date t, per
# name, built independently from cube_close_long (price-only). PIT-safe: the
# window ends at t (same "uses only data <= t" convention as PANEL_SCHEMA.md's
# vol_21/vol_63/... columns), never reaches into t+1.
# --------------------------------------------------------------------------
def build_max_lottery(panel: pd.DataFrame, window: int = 21) -> pd.Series:
    _, daily_ret = _load_cube_long()
    dates, symbols = _panel_dates_symbols(panel)
    cols = [s for s in symbols if s in daily_ret.columns]
    rows = []
    for d in dates:
        if d not in daily_ret.index:
            continue
        loc = daily_ret.index.get_loc(d)
        if loc < window - 1:
            continue
        win = daily_ret.iloc[loc - window + 1: loc + 1][cols]  # last `window` obs, ending at t inclusive
        cov_ok = win.notna().mean() >= 0.80
        mx = win.max(skipna=True)
        mx = mx.where(cov_ok)
        for sym, val in mx.dropna().items():
            rows.append((d, sym, val))
    out = pd.DataFrame(rows, columns=["date", "symbol", "factor"])
    return out.set_index(["date", "symbol"])["factor"]
