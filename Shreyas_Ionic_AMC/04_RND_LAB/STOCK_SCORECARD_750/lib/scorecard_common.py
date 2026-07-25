"""
scorecard_common.py -- SHARED, VALIDATED functions for STOCK_SCORECARD_750.

WHY THIS FILE EXISTS: during the 2026-07-17/18 build, winsorize(), percentile_rank(),
and the fundamental-ratio derivation formulas were each independently re-typed from
scratch in at least 3 different scripts, with small variations between copies -- this
is exactly the kind of repeated, non-trivial logic that (a) burns tokens re-deriving
every time and (b) risks silent drift/bugs between copies (the financial-sector D/E
exemption was fixed in the gate but initially missed in a separately-copied penalty
counter -- see FROZEN_METHODOLOGY.md). ONE canonical copy, reconciled with every fix
found this session. Import from here; do not re-derive these inline.

Also wraps `gs_quant.timeseries` (Goldman Sachs' open-source, credential-free technical
analytics library -- `pip install gs-quant`, Apache 2.0, verified 2026-07-22 to run
with zero GsSession/API credentials on plain pandas Series) for RSI/returns/moving
averages/volatility, instead of hand-rolling those formulas again.

Convention going forward: before writing a new helper function, check this file first.
Add a new function here ONLY if it's genuinely reused (2+ call sites) or non-trivial
enough that re-deriving it costs real tokens -- a one-line wrapper isn't worth the
indirection. Simple one-offs stay inline where they're used.
"""
import os
import numpy as np
import pandas as pd

try:
    from gs_quant.timeseries import (
        volatility as _gs_volatility,
        returns as _gs_returns,
        moving_average as _gs_moving_average,
        relative_strength_index as _gs_rsi,
        Window as _GSWindow,
    )
    HAVE_GS_QUANT = True
except ImportError:
    HAVE_GS_QUANT = False  # falls back to hand-rolled versions below -- never hard-fail on this


# ============================================================ statistics / ranking

def winsorize(s: pd.Series, pct: float = 0.02) -> pd.Series:
    """Clip to [pct, 1-pct] quantiles. Apply to every raw metric BEFORE ranking or
    using it in a formula -- prevents one erroneous/extreme data point from claiming
    an extreme rank or distorting a downstream calculation."""
    lo, hi = s.quantile(pct), s.quantile(1 - pct)
    return s.clip(lo, hi)


def percentile_rank(df: pd.DataFrame, col: str, group_col=None, ascending: bool = True,
                     min_group_size: int = 5, winsor: float = 0.02) -> pd.Series:
    """Cross-sectional percentile rank (0-100), winsorized by default.
    group_col: None = universe-wide. A single column name = sector-neutral (or
    whatever grouping that column represents), falling back to universe-wide if a
    group has fewer than min_group_size members (avoids a lone stock in a tiny group
    trivially ranking 0 or 100 regardless of its actual value).
    ascending=False inverts the ranking (use for "lower is better" metrics like P/E,
    so cheap = high score)."""
    raw = df[col]
    w = winsorize(raw, winsor) if winsor else raw
    s = w if ascending else -w
    if not group_col:
        return s.rank(pct=True) * 100
    grp_size = df.groupby(group_col)[col].transform("count")
    within = s.groupby(df[group_col]).rank(pct=True) * 100
    universe = s.rank(pct=True) * 100
    return within.where(grp_size >= min_group_size, universe)


def percentile_rank_cascading(df: pd.DataFrame, col: str, groupings: list, ascending: bool = True,
                               min_group_size: int = 5, winsor: float = 0.02) -> pd.Series:
    """Like percentile_rank, but cascades through multiple groupings from LEAST to
    MOST specific (pass groupings=['sector_tier_group', 'sector_norm'], most-specific
    first) -- the most specific grouping with enough members wins. Used for Value's
    sector x market-cap-tier blend so a stock isn't compared only against sector peers
    of a very different size (large-cap vs a sector's small-cap-heavy mix misleads)."""
    raw = df[col]
    w = winsorize(raw, winsor) if winsor else raw
    s = w if ascending else -w
    result = s.rank(pct=True) * 100
    for group_col in reversed(groupings):
        grp_size = df.groupby(group_col)[col].transform("count")
        within = s.groupby(df[group_col]).rank(pct=True) * 100
        result = within.where(grp_size >= min_group_size, result)
    return result


def coverage_aware_average(df: pd.DataFrame, score_cols: list) -> pd.DataFrame:
    """Mean across score_cols, skipping NaN (never zero-filled) + a coverage_pct/flag
    telling you how many of the inputs were actually available for that row."""
    sub = df[score_cols]
    pillar_score = sub.mean(axis=1, skipna=True)
    coverage_pct = sub.notna().sum(axis=1) / len(score_cols) * 100
    coverage_flag = pd.cut(coverage_pct, bins=[-1, 33.34, 66.67, 100], labels=["Low", "Med", "High"])
    return pd.DataFrame({"pillar_score": pillar_score, "coverage_pct": coverage_pct,
                          "coverage_flag": coverage_flag.astype(str)})


# ============================================================ PIT / data safety

def filter_pit(df: pd.DataFrame, as_of_date: str, date_col: str = "available_date") -> pd.DataFrame:
    """No-lookahead filter. Apply to fundamentals/ownership data BEFORE any computation
    touches it -- never read a raw PIT-stamped source without this."""
    cutoff = pd.Timestamp(as_of_date)
    return df[df[date_col] <= cutoff].copy()


def atomic_write(df: pd.DataFrame, path: str, fmt: str = "parquet"):
    """Write via a temp file + os.replace so a crash/kill mid-write can never leave a
    truncated file at the real path. Use for any output another process depends on."""
    tmp_path = path + ".tmp"
    if fmt == "parquet":
        df.to_parquet(tmp_path)
    else:
        df.to_csv(tmp_path, index=False)
    os.replace(tmp_path, path)


# ============================================================ sector cyclicality

# v1 approximation (MASTER_PLAN.md Open Risks) -- static lookup, not a dynamic model.
# Keys are the REAL macro_sector values from ALPHA_RANKER's sector_map.parquet
# (verified 2026-07-17, all 41, lower-cased for case-insensitive matching -- the real
# data has case-duplicate categories like "Consumer durables" vs "Consumer Durables").
SECTOR_CYCLICALITY = {
    "metals & mining": "Cyclical", "construction materials": "Cyclical", "capital goods": "Cyclical",
    "automobile and auto components": "Cyclical", "realty": "Cyclical", "construction": "Cyclical",
    "oil gas & consumable fuels": "Cyclical", "chemicals": "Cyclical", "textiles": "Cyclical",
    "non-energy minerals": "Cyclical", "energy minerals": "Cyclical", "process industries": "Cyclical",
    "producer manufacturing": "Cyclical", "transportation": "Cyclical", "forest materials": "Cyclical",
    "fast moving consumer goods": "Defensive-Stable", "healthcare": "Defensive-Stable",
    "health services": "Defensive-Stable", "health technology": "Defensive-Stable",
    "information technology": "Defensive-Stable", "technology services": "Defensive-Stable",
    "electronic technology": "Defensive-Stable", "telecommunication": "Defensive-Stable",
    "communications": "Defensive-Stable", "utilities": "Defensive-Stable", "power": "Defensive-Stable",
    "consumer non-durables": "Defensive-Stable", "consumer durables": "Defensive-Stable",
    "consumer services": "Defensive-Stable", "agriculture": "Defensive-Stable",
    "finance": "Sensitive-hybrid", "financial services": "Sensitive-hybrid",
    "commercial services": "Sensitive-hybrid", "industrial services": "Sensitive-hybrid",
    "distribution services": "Sensitive-hybrid", "retail trade": "Sensitive-hybrid",
    "services": "Sensitive-hybrid", "media entertainment & publication": "Sensitive-hybrid",
}
FINANCIAL_SECTORS = {"finance", "financial services"}  # exempt from the D/E red-flag -- leverage IS the business model


def tag_cyclicality(df: pd.DataFrame, sector_col: str = "sector") -> pd.Series:
    normalized = df[sector_col].astype(str).str.strip().str.lower()
    return normalized.map(SECTOR_CYCLICALITY).fillna("Defensive-Stable")


def is_financial_sector(sector: str) -> bool:
    return str(sector).strip().lower() in FINANCIAL_SECTORS


def market_cap_tercile(df: pd.DataFrame, mcap_col: str = "market_cap") -> pd.Series:
    return pd.qcut(df[mcap_col].rank(method="first"), 3, labels=["Small", "Mid", "Large"]).astype(str)


# ============================================================ fundamental ratio derivation
# Raw MASTER_fundamentals_pit.parquet metric_norm names (verified 2026-07-17 against the
# real file -- these are RAW Screener line items, NOT pre-computed ratios). Re-verify
# against the real file before assuming any OTHER name exists.

def pivot_wide_fundamentals(raw_fundamentals: pd.DataFrame) -> pd.DataFrame:
    """symbol/fiscal_year rows, one column per raw metric_norm, PIT metadata retained.
    Coalesces 'borrowing'/'borrowings' (both spellings appear in the real data for
    different rows) and computes 'equity' = equity capital + reserves, NaN'd out where
    <=0 (every ratio below breaks on non-positive equity -- exclude, don't fabricate)."""
    raw_metrics = ["sales", "revenue", "net profit", "operating profit", "opm %", "interest",
                   "eps in rs", "equity capital", "reserves", "borrowings", "borrowing",
                   "total assets", "cash from operating activity", "free cash flow"]
    wide = raw_fundamentals.pivot_table(index=["symbol", "fiscal_year", "available_date"],
                                          columns="metric_norm", values="value", aggfunc="last").reset_index()
    for col in raw_metrics:
        if col not in wide.columns:
            wide[col] = np.nan
    wide["total_borrowings"] = wide["borrowings"].fillna(wide["borrowing"])
    wide["equity"] = wide["equity capital"] + wide["reserves"]
    wide.loc[wide["equity"] <= 0, "equity"] = np.nan
    if "sales" not in raw_fundamentals["metric_norm"].values and "revenue" in raw_fundamentals["metric_norm"].values:
        wide["sales"] = wide["sales"].fillna(wide["revenue"])
    return wide


def derive_ratios_latest(wide: pd.DataFrame) -> pd.DataFrame:
    """Latest-fiscal-year ROE/ROCE/D-E/Interest-Coverage/Accruals for each symbol, from
    the pivoted frame above. For Quality's cyclicality-aware through-cycle averaging
    (Cyclical sectors use a longer lookback), average over multiple years' rows of
    `wide` BEFORE calling this, rather than pre-filtering to latest-only."""
    capital_employed = (wide["equity"] + wide["total_borrowings"]).where(lambda s: s > 0)
    out = wide[["symbol", "fiscal_year", "available_date"]].copy()
    out["roe"] = wide["net profit"] / wide["equity"]
    out["roce"] = wide["operating profit"] / capital_employed
    out["debt_equity"] = wide["total_borrowings"] / wide["equity"]
    out["interest_coverage"] = wide["operating profit"] / wide["interest"].replace(0, np.nan)
    out["accruals_ratio"] = (wide["net profit"] - wide["cash from operating activity"]) / wide["total assets"].replace(0, np.nan)
    out["fcf"] = wide["free cash flow"]
    return out


def derive_valuation(wide_latest: pd.DataFrame, prices: pd.DataFrame, price_col: str = "close") -> pd.DataFrame:
    """P/E, P/B, market cap, at the LATEST fiscal year per symbol, joined to current
    price. Shares outstanding has no field in the raw data -- APPROXIMATED as
    net profit / EPS. This is an [INFERENCE], not a reported figure -- label it as such
    downstream, and expect it to be noisy for companies with unusual capital structure."""
    latest = wide_latest.sort_values("fiscal_year").groupby("symbol").tail(1).copy()
    latest["shares_out_approx"] = latest["net profit"] / latest["eps in rs"].replace(0, np.nan)
    latest.loc[latest["shares_out_approx"] <= 0, "shares_out_approx"] = np.nan
    latest["book_value_per_share"] = latest["equity"] / latest["shares_out_approx"]

    px = prices.sort_values("date").groupby("symbol")[price_col].last().rename("current_price").reset_index()
    latest = latest.merge(px, on="symbol", how="left")

    latest["pe_current"] = latest["current_price"] / latest["eps in rs"].replace(0, np.nan)
    latest["pb_current"] = latest["current_price"] / latest["book_value_per_share"]
    latest["market_cap_approx"] = latest["current_price"] * latest["shares_out_approx"]
    return latest[["symbol", "pe_current", "pb_current", "market_cap_approx", "shares_out_approx"]]


def reverse_dcf_growth(avg_fcf: float, market_cap: float, risk_free_rate: float, erp: float,
                        terminal_growth: float) -> float:
    """Single-stage perpetuity reverse-DCF (closed form): what CONSTANT growth rate g
    would justify today's market cap, given avg FCF and a CAPM discount rate?
    market_cap = FCF*(1+g)/(r-g)  =>  g = (market_cap*r - FCF) / (FCF + market_cap)
    Use this, NOT a two-stage 5yr-explicit-then-terminal model -- that version was
    tried first and produced implausible 85-121% implied-growth figures even for
    fairly-priced stocks, because a thin discount-minus-terminal-growth spread
    massively amplifies the terminal-value term. This closed-form version gave far
    more sane, interpretable 8-13% figures on the same real companies. r = risk_free_rate + erp."""
    r = risk_free_rate + erp
    if pd.isna(avg_fcf) or pd.isna(market_cap) or avg_fcf <= 0 or market_cap <= 0:
        return np.nan
    return (market_cap * r - avg_fcf) / (avg_fcf + market_cap)


# ============================================================ technical indicators
# Prefers gs_quant.timeseries (Goldman Sachs, open-source, no credentials needed --
# `pip install gs-quant`, verified 2026-07-22) over hand-rolled versions. Falls back
# to a local implementation only if gs-quant isn't installed, so this module never
# hard-fails on the optional dependency.

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    if HAVE_GS_QUANT:
        return _gs_rsi(close, period)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def pct_returns(close: pd.Series, periods: int = 1) -> pd.Series:
    if HAVE_GS_QUANT and periods == 1:
        return _gs_returns(close)
    return close.pct_change(periods)


def sma(close: pd.Series, window: int) -> pd.Series:
    if HAVE_GS_QUANT:
        return _gs_moving_average(close, window)
    return close.rolling(window, min_periods=max(1, int(window * 0.6))).mean()


def realized_volatility(close: pd.Series, window: int = 22) -> pd.Series:
    """Annualized realized volatility. Only via gs_quant (no simple local equivalent
    worth hand-rolling here) -- returns NaN series if gs-quant isn't installed."""
    if HAVE_GS_QUANT:
        return _gs_volatility(close, _GSWindow(window, 0))
    return pd.Series(np.nan, index=close.index)


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-balance volume. Not in gs_quant.timeseries -- our own, used for the
    Accumulation pillar (gs-quant doesn't cover volume-flow indicators)."""
    direction = np.sign(close.diff().fillna(0))
    return (direction * volume).cumsum()
