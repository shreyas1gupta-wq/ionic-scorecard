"""
factor_bench.py -- unit of truth for the benchmark/factor NAV panel used by
ALPHA_RANKER's oversight cascade and (later) the bottom-up scoring engine.

Source: <ROOT>/factor_navs (1).xlsx, sheet 'Sheet1'.
  'NAV Date' + 22 daily NAV series: NIFTY 50/100/250/500, Midcap 150,
  Smallcap 100/250, Multicap 50:25:25, smart-beta factor indices
  (Low Vol 30, Quality 30, Value 30, Momentum 30, Alpha 30, Value 50,
  Momentum 50, Midcap Momentum 50, Smallcap Quality Momentum 100,
  High Beta 50, BSE Midcap 150 Momentum 30), GOLDBEES, HDFC Liquid
  Fund(G) (=cash proxy), Top 20 equal weight.

NO-LOOKAHEAD CONTRACT: every helper here takes an explicit `asof` and only
ever reads rows with index <= asof. Nothing here interpolates, backfills,
or peeks forward. (D-028 / LOOKAHEAD_CONTROLS.md T1-class control.)
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path

import pandas as pd

# ALPHA_RANKER/src/lib/factor_bench.py -> parents[3] = repo root (NIFTY 500)
ROOT = Path(__file__).resolve().parents[3]
FACTOR_NAVS_PATH = ROOT / "factor_navs (1).xlsx"

# Canonical short aliases -> actual column headers in the workbook.
ALIASES = {
    "NIFTY50": "NIFTY 50",
    "NIFTY100": "NIFTY 100",
    "NIFTY250": "NIFTY 250",
    "NIFTY500": "NIFTY 500",
    "MIDCAP150": "NIFTY MIDCAP 150",
    "SMALLCAP100": "NIFTY SMALLCAP 100",
    "SMALLCAP250": "NIFTY SMALLCAP 250",
    "MULTICAP502525": "NIFTY MULTICAP 50:25:25",
    "LOWVOL30": "NIFTY 100 Low Vol 30",
    "QUALITY30": "NIFTY 200 Quality 30",
    "VALUE30": "NIFTY 200 Value 30",
    "MOMENTUM30": "NIFTY 200 Momentum 30",
    "ALPHA30": "NIFTY 200 Alpha 30",
    "MOMENTUM50": "NIFTY 500 Momentum 50",
    "VALUE50": "NIFTY 500 Value 50",
    "MIDCAP_MOM50": "Nifty Midcap Momentum 50",
    "SMALLCAP_QUAL_MOM100": "Nifty Smallcap Quality Momentum 100",
    "HIGHBETA50": "NIFTY HIGH BETA 50",
    "GOLD": "GOLDBEES",
    "CASH": "HDFC Liquid Fund(G)",
    "TOP20EW": "Top 20 equal weight",
    "BSE_MIDCAP_MOM30": "BSE Midcap 150 Momentum 30 Index",
}


def _resolve(name: str) -> str:
    return ALIASES.get(name, name)


@lru_cache(maxsize=1)
def load_navs() -> pd.DataFrame:
    """Raw NAV levels, DatetimeIndex ascending. Duplicate dates (if any) keep
    the last occurrence. Nulls (some series inception later than 2005-04-01,
    e.g. 'Top 20 equal weight' / 'BSE Midcap 150 Momentum 30 Index') are left
    as NaN -- never fabricated/filled."""
    df = pd.read_excel(FACTOR_NAVS_PATH, sheet_name="Sheet1", engine="openpyxl")
    df["NAV Date"] = pd.to_datetime(df["NAV Date"])
    df = df.sort_values("NAV Date").set_index("NAV Date")
    df = df[~df.index.duplicated(keep="last")]
    df.index.name = "date"
    return df


@lru_cache(maxsize=1)
def load_returns() -> pd.DataFrame:
    """Tidy daily simple returns for every series in the panel (pct_change of
    load_navs()). First obs of each series and any pre-inception NaN stays NaN."""
    return load_navs().pct_change()


def available_series() -> list[str]:
    return list(load_navs().columns)


def get_series(name: str, kind: str = "nav") -> pd.Series:
    """kind='nav' -> levels, kind='ret' -> daily simple returns. Drops NaN."""
    col = _resolve(name)
    df = load_navs() if kind == "nav" else load_returns()
    if col not in df.columns:
        raise KeyError(f"'{name}' (-> '{col}') not in factor_navs panel. "
                        f"Available: {list(df.columns)}")
    return df[col].dropna()


def trailing_return(name: str, asof, lookback_days: int) -> float:
    """
    Point-in-time trailing simple return over `lookback_days` TRADING days
    (i.e. rows of the panel, which are already business-day sampled) ending
    at the last observation <= asof. Lookahead-safe by construction: history
    is sliced to index <= asof BEFORE any calculation.
    Returns NaN if there isn't enough history yet.
    """
    navs = get_series(name, "nav")
    asof = pd.Timestamp(asof)
    hist = navs[navs.index <= asof]
    if len(hist) < lookback_days + 1:
        return float("nan")
    end = hist.iloc[-1]
    start = hist.iloc[-1 - lookback_days]
    if pd.isna(start) or pd.isna(end) or start == 0:
        return float("nan")
    return end / start - 1.0


def relative_strength(name: str, benchmark: str, asof, lookback_days: int) -> float:
    """RS = trailing_return(name) - trailing_return(benchmark), same window,
    same asof. NaN-propagating (no partial/implied answers)."""
    r_name = trailing_return(name, asof, lookback_days)
    r_bench = trailing_return(benchmark, asof, lookback_days)
    if pd.isna(r_name) or pd.isna(r_bench):
        return float("nan")
    return r_name - r_bench


def trend_state(name: str, asof, fast: int = 50, slow: int = 200) -> dict:
    """No-lookahead trend read: last level vs trailing SMA(fast)/SMA(slow),
    both computed using only rows with index <= asof."""
    navs = get_series(name, "nav")
    asof = pd.Timestamp(asof)
    hist = navs[navs.index <= asof]
    if len(hist) < slow:
        return {"level": float(hist.iloc[-1]) if len(hist) else float("nan"),
                "sma_fast": float("nan"), "sma_slow": float("nan"),
                "state": "insufficient_history"}
    level = float(hist.iloc[-1])
    sma_fast = float(hist.tail(fast).mean())
    sma_slow = float(hist.tail(slow).mean())
    if level > sma_fast > sma_slow:
        state = "uptrend"
    elif level < sma_fast < sma_slow:
        state = "downtrend"
    else:
        state = "mixed"
    return {"level": level, "sma_fast": sma_fast, "sma_slow": sma_slow, "state": state}


if __name__ == "__main__":
    navs = load_navs()
    print("Loaded factor_navs:", navs.shape, navs.index.min().date(), "->", navs.index.max().date())
    print("Series:", list(navs.columns))
    asof = navs.index.max()
    print(f"\nAs of {asof.date()}:")
    print(" NIFTY500 trend:", trend_state("NIFTY500", asof))
    print(" HighBeta50 vs LowVol30 RS (63d):", relative_strength("HIGHBETA50", "LOWVOL30", asof, 63))
    print(" GOLDBEES trailing 63d:", trailing_return("GOLD", asof, 63))
