"""
WAVE worker (ALPHA_RANKER money-first loop) -- MOMENTUM-QUALITY refinements.

Tests whether two published "does this momentum name keep going" filters add
anything OVER plain residual momentum (H003), on the LONG 2005-2025 history
(panel_long.parquet / cube_close_long.parquet, 249 monthly dates) rather than
the short 2021-2026 panel.parquet (only 61 dates, ~3 bear months -- too few to
say anything about the high-vol fragility CONSOLIDATION.md flags).

Hypotheses (rnd/backlog_scout.json):
  IDG-G-08 / IDG-I-09  Frog-in-the-Pan / information discreteness
      (Da, Gurun & Warachka 2014): momentum built from a smooth, mostly-
      same-sign-day path continues; momentum built from a few big jumps
      reverses. signed quality = sign(cum_ret) * (%same-sign-days -
      %opposite-sign-days) over the 12-1 formation window, RAW daily
      returns (paper uses raw returns, matches backlog construct text).
  IDG-I-10  Trend-quality R-squared: goodness-of-fit of an OLS of
      log(price) on time over a trailing 126-session window (smoothness of
      the trend, direction-agnostic on its own) -- signed the same way
      (sign(momentum) * R2) so it reinforces winners/losers instead of
      just measuring "is there A trend, any trend".

Both are applied as an ADDITIVE TILT on top of plain residual momentum
(cross-sectional z-score each date, factor = z(mom) + z(signed_quality)),
per backlog_scout.json's explicit instruction: "Test as a FILTER/interaction,
not standalone." All PIT: every rolling window ends at t, no forward data.

Data: rnd/panel/cube_close_long.parquet (5131 dates x 976 symbols, raw close,
2005-04-01..2025-12-05), rnd/panel/cube_bench_long.parquet (NIFTY500, same
range), rnd/panel/panel_long.parquet (249 monthly rebalance dates, same
range, with fwd_ret_*_resid PIT labels already built -- we only build the
FACTOR here, not the forward-return targets).
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
PANEL_DIR = RND_DIR / "panel"

FORM_WINDOW = 231   # 252-21, matches builders_mom.py H003 window length
SKIP_DAYS = 21       # skip most recent month (standard 12-1)
R2_WINDOW = 126       # IDG-I-10 spec

_CUBE_CLOSE = None
_CUBE_BENCH = None
_DAILY_RET = None
_BENCH_RET = None
_ROLL_BETA = None
_RESID_DAILY = None


def _load_cubes():
    global _CUBE_CLOSE, _CUBE_BENCH, _DAILY_RET, _BENCH_RET
    if _CUBE_CLOSE is None:
        _CUBE_CLOSE = pd.read_parquet(PANEL_DIR / "cube_close_long.parquet")
        _CUBE_BENCH = pd.read_parquet(PANEL_DIR / "cube_bench_long.parquet")["NIFTY500"]
        _DAILY_RET = _CUBE_CLOSE.pct_change()
        _BENCH_RET = _CUBE_BENCH.pct_change()
    return _CUBE_CLOSE, _CUBE_BENCH, _DAILY_RET, _BENCH_RET


def _rolling_daily_beta() -> pd.DataFrame:
    """Trailing 252d (min126) daily-frequency CAPM beta to NIFTY500, per stock.
    Same convention as builders_mom.py: window ENDS at t (includes day t)."""
    global _ROLL_BETA
    if _ROLL_BETA is None:
        _, _, daily_ret, bench_ret = _load_cubes()
        cov = daily_ret.rolling(252, min_periods=126).cov(bench_ret)
        var = bench_ret.rolling(252, min_periods=126).var()
        _ROLL_BETA = cov.div(var, axis=0)
    return _ROLL_BETA


def _residual_daily_returns() -> pd.DataFrame:
    global _RESID_DAILY
    if _RESID_DAILY is None:
        _, _, daily_ret, bench_ret = _load_cubes()
        beta = _rolling_daily_beta()
        _RESID_DAILY = daily_ret.sub(beta.mul(bench_ret, axis=0))
    return _RESID_DAILY


def _panel_dates_symbols(panel: pd.DataFrame):
    dates = sorted(pd.to_datetime(panel["date"].unique()))
    symbols = sorted(panel["symbol"].unique())
    return dates, symbols


def _series_from_rows(rows) -> pd.Series:
    out = pd.DataFrame(rows, columns=["date", "symbol", "factor"])
    return out.set_index(["date", "symbol"])["factor"]


def _zscore_by_date(s: pd.Series) -> pd.Series:
    """Cross-sectional (within-date) z-score, so components on different
    raw scales can be added into one tilt without one dominating."""
    df = s.rename("v").reset_index()
    g = df.groupby("date")["v"]
    mu = g.transform("mean")
    sd = g.transform("std").replace(0, np.nan)
    z = (df["v"] - mu) / sd
    return pd.Series(z.values, index=pd.MultiIndex.from_frame(df[["date", "symbol"]]), name="factor")


# --------------------------------------------------------------------------
# baseline: plain residual 12-1 momentum, rebuilt on the LONG cube so it's
# apples-to-apples with the tilted variants below (same universe/date grid
# as panel_long, NOT the short panel.parquet's H003 card).
# --------------------------------------------------------------------------
def build_mom_resid_12_1_long(panel: pd.DataFrame) -> pd.Series:
    resid = _residual_daily_returns()
    dates, symbols = _panel_dates_symbols(panel)
    cols = [s for s in symbols if s in resid.columns]
    rows = []
    for d in dates:
        if d not in resid.index:
            continue
        loc = resid.index.get_loc(d)
        if loc < 252:
            continue
        window = resid.iloc[loc - 251: loc - 20][cols]
        cov_ok = window.notna().mean() >= 0.80
        cum = (1.0 + window.fillna(0.0)).prod() - 1.0
        cum = cum.where(cov_ok)
        for sym, val in cum.dropna().items():
            rows.append((d, sym, val))
    return _series_from_rows(rows)


# --------------------------------------------------------------------------
# IDG-G-08 / IDG-I-09: frog-in-the-pan signed path-continuity quality,
# vectorized via rolling boolean-mask sums (no per-column Python apply loop
# -- 5131 rows x ~700-900 live columns x 249 rebalance dates would be too
# slow with row-wise iteration).
# --------------------------------------------------------------------------
def _fip_signed_quality() -> pd.DataFrame:
    """signed_quality(t) = sign(cum_ret over [t-251,t-21]) * (%pos - %neg)
    of RAW daily returns over that same window. High = smooth continuation
    (winners mostly up-days / losers mostly down-days); low/negative = jumpy
    (momentum built on a few big discrete moves) -> per Da-Gurun-Warachka,
    smooth continues, jumpy reverses, so signed_quality should be POSITIVELY
    related to forward return when added to momentum."""
    close, _, daily_ret, _ = _load_cubes()
    pos = (daily_ret > 0).astype(float)
    neg = (daily_ret < 0).astype(float)
    valid = daily_ret.notna().astype(float)
    roll_pos = pos.rolling(FORM_WINDOW, min_periods=1).sum()
    roll_neg = neg.rolling(FORM_WINDOW, min_periods=1).sum()
    roll_valid = valid.rolling(FORM_WINDOW, min_periods=1).sum()
    # cumulative return over the SAME window, via log-return summation
    logret = np.log1p(daily_ret.clip(lower=-0.999).fillna(0.0))
    roll_logret = logret.rolling(FORM_WINDOW, min_periods=1).sum()
    cum_ret = np.expm1(roll_logret)
    pct_pos = roll_pos.div(roll_valid.replace(0, np.nan))
    pct_neg = roll_neg.div(roll_valid.replace(0, np.nan))
    signed_q = np.sign(cum_ret) * (pct_pos - pct_neg)
    cov_ok = roll_valid.div(FORM_WINDOW) >= 0.80
    signed_q = signed_q.where(cov_ok)
    # shift so the window ENDING at (t-21) is read off at row t (skip-month)
    return signed_q.shift(SKIP_DAYS)


def build_fip_signed_quality(panel: pd.DataFrame) -> pd.Series:
    """Standalone signed FIP-quality factor (for the horse-race diagnostic
    only; backlog explicitly forbids using this standalone in production)."""
    sq = _fip_signed_quality()
    dates, symbols = _panel_dates_symbols(panel)
    cols = [s for s in symbols if s in sq.columns]
    rows = []
    for d in dates:
        if d not in sq.index:
            continue
        vals = sq.loc[d, cols].dropna()
        for sym, val in vals.items():
            rows.append((d, sym, val))
    return _series_from_rows(rows)


def build_momq_fip_tilt(panel: pd.DataFrame) -> pd.Series:
    """factor = z(plain resid 12-1 momentum) + z(signed FIP quality),
    both cross-sectionally z-scored per date before summing."""
    mom = build_mom_resid_12_1_long(panel)
    fip = build_fip_signed_quality(panel)
    common = mom.index.intersection(fip.index)
    z_mom = _zscore_by_date(mom.loc[common])
    z_fip = _zscore_by_date(fip.loc[common])
    combined = (z_mom + z_fip).dropna()
    return combined


# --------------------------------------------------------------------------
# IDG-I-10: trend-quality R^2 of OLS(log(price) ~ time) over trailing 126
# sessions. Closed-form vectorized rolling correlation (single-predictor OLS
# R^2 == squared Pearson correlation with the time index), no per-window
# Python loop:
#   idx = 0..N-1 (fixed window-local index), y = log(price)
#   sum_ixy(t) = rolling_sum(k*y_k)(t) - (t-N+1)*rolling_sum(y_k)(t)
#   corr = (N*sum_ixy - sum_x*sum_y) / sqrt((N*sum_x2-sum_x^2)(N*sum_y2-sum_y^2))
# --------------------------------------------------------------------------
def _trend_r2(window: int = R2_WINDOW) -> pd.DataFrame:
    close, *_ = _load_cubes()
    logp = np.log(close.where(close > 0))
    n = window
    k = np.arange(len(logp))
    sum_x = n * (n - 1) / 2.0
    sum_x2 = (n - 1) * n * (2 * n - 1) / 6.0

    roll_y = logp.rolling(n, min_periods=n).sum()
    roll_y2 = (logp ** 2).rolling(n, min_periods=n).sum()
    z = logp.mul(k, axis=0)
    roll_z = z.rolling(n, min_periods=n).sum()
    t_minus_nplus1 = pd.Series(k - (n - 1), index=logp.index)
    sum_ixy = roll_z.sub(roll_y.mul(t_minus_nplus1, axis=0), axis=0)

    numerator = n * sum_ixy - sum_x * roll_y
    denom_x = n * sum_x2 - sum_x ** 2
    denom_y = n * roll_y2 - roll_y ** 2
    denom = denom_x * denom_y
    corr = numerator / np.sqrt(denom.where(denom > 0))
    r2 = (corr ** 2).clip(0, 1)
    return r2


def build_trend_r2(panel: pd.DataFrame) -> pd.Series:
    """Standalone R^2 factor (unsigned; diagnostic only)."""
    r2 = _trend_r2()
    dates, symbols = _panel_dates_symbols(panel)
    cols = [s for s in symbols if s in r2.columns]
    rows = []
    for d in dates:
        if d not in r2.index:
            continue
        vals = r2.loc[d, cols].dropna()
        for sym, val in vals.items():
            rows.append((d, sym, val))
    return _series_from_rows(rows)


def build_momq_r2_tilt(panel: pd.DataFrame) -> pd.Series:
    """factor = z(plain resid 12-1 momentum) + z(sign(momentum) * R2),
    so a clean/smooth trend AMPLIFIES momentum's existing sign rather than
    just flagging "any trend, any direction" (R2 alone is direction-blind)."""
    mom = build_mom_resid_12_1_long(panel)
    r2 = _trend_r2()
    dates, symbols = _panel_dates_symbols(panel)
    cols = [s for s in symbols if s in r2.columns]
    rows = []
    for d in dates:
        if d not in r2.index:
            continue
        vals = r2.loc[d, cols].dropna()
        for sym, val in vals.items():
            rows.append((d, sym, val))
    signed_r2 = _series_from_rows(rows)
    mom_sign = np.sign(mom)
    common = mom.index.intersection(signed_r2.index)
    signed_r2_oriented = (mom_sign.loc[common] * signed_r2.loc[common]).dropna()
    z_mom = _zscore_by_date(mom.loc[common])
    z_r2 = _zscore_by_date(signed_r2_oriented)
    combined = (z_mom + z_r2).dropna()
    return combined
