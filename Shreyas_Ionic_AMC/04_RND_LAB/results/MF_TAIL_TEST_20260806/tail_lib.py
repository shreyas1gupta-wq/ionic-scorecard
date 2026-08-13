# -*- coding: utf-8 -*-
"""Reusable tail-risk metric functions. Pre-registered definitions (Sameer Bhat, 2026-08-06).

All metrics operate on a chronologically sorted return series (fractions, not %).
"""
import numpy as np
import pandas as pd


def es_90(returns):
    """Expected Shortfall at 90% = mean of the worst decile of returns. Min 1 obs."""
    r = pd.Series(returns).dropna().sort_values()
    if len(r) == 0:
        return np.nan
    k = max(1, int(np.ceil(0.10 * len(r))))
    return r.iloc[:k].mean()


def mdd_from_returns(returns):
    """Max drawdown (most negative peak-to-trough) from a return series, cumulative-product basis."""
    r = pd.Series(returns).dropna()
    if len(r) == 0:
        return np.nan
    cum = (1 + r).cumprod()
    peak = cum.cummax()
    dd = cum / peak - 1
    return dd.min()


def mdd_from_levels(levels):
    """Max drawdown directly from a price/NAV level series (any granularity)."""
    lv = pd.Series(levels).dropna()
    if len(lv) == 0:
        return np.nan
    peak = lv.cummax()
    dd = lv / peak - 1
    return dd.min()


def drawdown_series_from_returns(returns):
    r = pd.Series(returns).dropna()
    cum = (1 + r).cumprod()
    peak = cum.cummax()
    return cum / peak - 1


def ulcer_index(returns):
    """sqrt(mean(drawdown_t^2)) over the whole path -- depth AND duration in one number."""
    dd = drawdown_series_from_returns(returns)
    if len(dd) == 0:
        return np.nan
    return np.sqrt((dd ** 2).mean())


def cdar_90(returns):
    """Conditional Drawdown at Risk 90%: mean of the worst decile of the point-in-time
    drawdown series (not just the single worst point, i.e. not just MDD)."""
    dd = drawdown_series_from_returns(returns)
    if len(dd) == 0:
        return np.nan
    d = dd.sort_values()
    k = max(1, int(np.ceil(0.10 * len(d))))
    return d.iloc[:k].mean()


def downside_deviation(returns, mar=0.0):
    r = pd.Series(returns).dropna()
    if len(r) == 0:
        return np.nan
    downside = np.minimum(r - mar, 0.0)
    return np.sqrt((downside ** 2).mean())


def monthly_returns_from_navs(dates, navs):
    s = pd.Series(navs, index=pd.to_datetime(dates)).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return s.pct_change().dropna()
