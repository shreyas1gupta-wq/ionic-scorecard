"""
Factor builders for ALPHA_RANKER worker hypotheses H028/H032/H033/H034.
Each builder(panel_df) -> pd.Series indexed by (date, symbol), PIT-safe
(uses only data <= t). Shared by rnd/lib/harness.py's run_experiment().

Owner: worker session 2026-07-16. Read-only wrt weights (RESEARCH_PROTOCOL S5).
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ALPHA_DIR = Path(__file__).resolve().parents[2]
PRICES_DIR = ALPHA_DIR / "data" / "prices"
FUND_PATH = ALPHA_DIR / "data" / "fundamentals" / "MASTER_fundamentals_pit.parquet"

_PRICE_CACHE: dict[str, pd.Series] = {}


def _load_prices(symbols: list[str]) -> dict[str, pd.Series]:
    out = {}
    for sym in symbols:
        if sym in _PRICE_CACHE:
            out[sym] = _PRICE_CACHE[sym]
            continue
        fp = PRICES_DIR / f"{sym}.parquet"
        if not fp.exists():
            continue
        d = pd.read_parquet(fp)
        if "Adj Close" not in d.columns:
            continue
        s = d["Adj Close"].copy()
        s.index = pd.to_datetime(s.index)
        s = s.sort_index()
        _PRICE_CACHE[sym] = s
        out[sym] = s
    return out


# --------------------------------------------------------------------------
# H028 — size / marketcap tilt
# --------------------------------------------------------------------------
def build_size_factor(panel: pd.DataFrame) -> pd.Series:
    """Factor = mktcap_log directly (already PIT in the panel). Expected sign
    per backlog H028 is NEGATIVE (small-cap premium: low mktcap_log -> higher
    fwd return), so a working size effect should show IC < 0."""
    f = panel.set_index(["date", "symbol"])["mktcap_log"]
    return f.dropna()


def build_quality_proxy(min_obs_per_symbol: int = 2) -> pd.DataFrame:
    """Coarse annual quality score = ROA-like: net profit / total assets,
    PIT (available_date), from MASTER_fundamentals_pit.parquet (long format).
    Returns tidy (symbol, available_date, quality) for merge_asof use.
    Sparse (~annual) by construction -- documented, not a bug."""
    f = pd.read_parquet(FUND_PATH)
    sub = f[f["metric_norm"].isin(["net profit", "total assets"])].copy()
    piv = sub.pivot_table(index=["nse_symbol", "available_date"],
                           columns="metric_norm", values="value", aggfunc="last")
    piv = piv.rename(columns={"net profit": "net_profit", "total assets": "total_assets"})
    piv = piv.dropna(subset=["net_profit", "total_assets"])
    piv = piv[piv["total_assets"] > 0]
    piv["quality"] = piv["net_profit"] / piv["total_assets"]
    piv = piv.reset_index().rename(columns={"nse_symbol": "symbol", "available_date": "date"})
    piv["date"] = pd.to_datetime(piv["date"])
    counts = piv.groupby("symbol").size()
    keep = counts[counts >= min_obs_per_symbol].index
    return piv[piv["symbol"].isin(keep)][["symbol", "date", "quality"]].sort_values(["symbol", "date"])


def attach_quality_pit(panel: pd.DataFrame) -> pd.DataFrame:
    """merge_asof (backward, PIT-safe: quality known at t must have
    available_date <= t) the quality proxy onto each panel row."""
    q = build_quality_proxy()
    out = []
    p = panel.sort_values(["symbol", "date"]).copy()
    p["date"] = pd.to_datetime(p["date"]).astype("datetime64[ns]")
    q = q.copy()
    q["date"] = pd.to_datetime(q["date"]).astype("datetime64[ns]")
    for sym, g in p.groupby("symbol"):
        qg = q[q["symbol"] == sym].sort_values("date")
        if qg.empty:
            g = g.copy()
            g["quality"] = np.nan
        else:
            g = pd.merge_asof(g.sort_values("date"), qg[["date", "quality"]],
                               on="date", direction="backward")
        out.append(g)
    return pd.concat(out, ignore_index=True)


# --------------------------------------------------------------------------
# H032 — closet-beta diagnostic: strong factor (12-1 residual momentum) under
# raw / excess / resid bases. Built independently from prices (not read off
# the panel) so this is a genuine factor->harness round trip.
# --------------------------------------------------------------------------
def build_momentum_12_1_factor(panel: pd.DataFrame) -> pd.Series:
    dates = sorted(pd.to_datetime(panel["date"].unique()))
    symbols = sorted(panel["symbol"].unique())
    px = _load_prices(symbols)
    prices = pd.DataFrame(px).sort_index()
    rows = []
    for d in dates:
        if d not in prices.index:
            asof = prices.index[prices.index <= d]
            if len(asof) == 0:
                continue
            d_eff = asof[-1]
        else:
            d_eff = d
        loc = prices.index.get_loc(d_eff)
        if isinstance(loc, slice):
            loc = loc.stop - 1
        i_skip = loc - 21   # skip most recent 1 month
        i_start = loc - 252  # 12m lookback
        if i_start < 0 or i_skip < 0:
            continue
        p_skip = prices.iloc[i_skip]
        p_start = prices.iloc[i_start]
        mom = (p_skip / p_start - 1.0)
        for sym, val in mom.items():
            if pd.notna(val):
                rows.append((d, sym, val))
    out = pd.DataFrame(rows, columns=["date", "symbol", "factor"])
    return out.set_index(["date", "symbol"])["factor"]


# --------------------------------------------------------------------------
# H034 — short-term mean-reversion (1-5d reversal, RSI2), non-monotone modifier
# test. Built independently from prices at each month-end t.
# --------------------------------------------------------------------------
def build_shortterm_reversal_factor(panel: pd.DataFrame, lookback: int = 5) -> pd.Series:
    """factor = -(trailing `lookback`-day return as of t). Sign per backlog
    H034 = '-' (i.e. recent losers expected to bounce -> positive fwd return
    for negative recent return, so factor sign-flipped so + factor = expect + fwd ret)."""
    dates = sorted(pd.to_datetime(panel["date"].unique()))
    symbols = sorted(panel["symbol"].unique())
    px = _load_prices(symbols)
    prices = pd.DataFrame(px).sort_index()
    rows = []
    for d in dates:
        asof = prices.index[prices.index <= d]
        if len(asof) == 0:
            continue
        d_eff = asof[-1]
        loc = prices.index.get_loc(d_eff)
        if isinstance(loc, slice):
            loc = loc.stop - 1
        i_start = loc - lookback
        if i_start < 0:
            continue
        p_now = prices.iloc[loc]
        p_start = prices.iloc[i_start]
        ret = (p_now / p_start - 1.0)
        for sym, val in ret.items():
            if pd.notna(val):
                rows.append((d, sym, -val))  # sign-flip: reversal
    out = pd.DataFrame(rows, columns=["date", "symbol", "factor"])
    return out.set_index(["date", "symbol"])["factor"]


def build_rsi2_factor(panel: pd.DataFrame, period: int = 2) -> pd.Series:
    """Classic RSI(2), sign-flipped (factor = 50 - RSI2) so high factor
    (low/oversold RSI) => expected positive forward return (reversal bounce)."""
    dates = sorted(pd.to_datetime(panel["date"].unique()))
    symbols = sorted(panel["symbol"].unique())
    px = _load_prices(symbols)
    rows = []
    for sym, s in px.items():
        delta = s.diff()
        up = delta.clip(lower=0.0)
        down = -delta.clip(upper=0.0)
        roll_up = up.rolling(period).mean()
        roll_down = down.rolling(period).mean()
        rs = roll_up / roll_down.replace(0.0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi_asof = rsi.reindex(sorted(set(dates)), method="ffill")
        for d in dates:
            if d in rsi_asof.index and pd.notna(rsi_asof.loc[d]):
                rows.append((d, sym, 50.0 - float(rsi_asof.loc[d])))
    out = pd.DataFrame(rows, columns=["date", "symbol", "factor"])
    return out.set_index(["date", "symbol"])["factor"]


# --------------------------------------------------------------------------
# H033 — beta as standalone factor (after size/value control)
# --------------------------------------------------------------------------
def build_beta_factor(panel: pd.DataFrame) -> pd.Series:
    """Factor = beta_252 directly. Expected sign per backlog H033 is
    NEGATIVE (BAB / low-vol anomaly: low beta -> higher risk-adjusted fwd
    return), so a working effect should show IC < 0."""
    f = panel.set_index(["date", "symbol"])["beta_252"]
    return f.dropna()
