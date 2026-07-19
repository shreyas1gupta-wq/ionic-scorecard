"""
WAVE-2 W2-sector worker -- sector / sub-sector analytics.

(a) Sector & sub-sector equal-weight price composites from cube_close.parquet
    constituents (data <= t) -> sector momentum / sector RS vs NIFTY.
(b) WITHIN-SECTOR peer-relative scoring helper: given any (date,symbol)
    factor Series, return its cross-sectional rank/z DEMEANED within
    sub_sector (or macro_sector) at each date -- lookahead-free.
(c) Sector fundamental aggregates (median ROIC / revenue-growth / earnings
    yield) from MASTER_fundamentals_pit, PIT-joined the same way the panel
    itself is (available_date-gated merge_asof), for relative comparison.

Universe for (a): the 751 symbols backing cube_close.parquet / panel.parquet
(same universe build_panel.py uses) -- NOT the wider ~2180/2825-symbol
sector_map.parquet universe, since composites need a continuous daily price
series. sector_map.parquet is still the join key for macro_sector/sub_sector
labels; symbols in sector_map without a cube_close column simply don't
contribute to a composite (documented, not an error).

PIT note: sector composites at date t are equal-weight, DAILY-rebalanced
(no rolling weight drift to leak), built only from cube_close rows <= t --
by construction there is nothing forward-looking in a same-day cross-
sectional average. Momentum/RS built on TOP of the composite (12-1 style,
skip-month) uses composite[t-skip]/composite[t-lookback], i.e. values
strictly <= t, same convention as builders_mom.py's stock-level 12-1.
"""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
ALPHA_DIR = RND_DIR.parent
PANEL_DIR = RND_DIR / "panel"

sys.path.insert(0, str(_THIS.parent))
import builders_value as _bv  # noqa: E402
import builders_quality as _bq  # noqa: E402

SECTOR_MAP_PATH = ALPHA_DIR / "data" / "universe" / "sector_map.parquet"
CUBE_CLOSE_PATH = PANEL_DIR / "cube_close.parquet"
CUBE_BENCH_PATH = PANEL_DIR / "cube_bench.parquet"
FUND_PATH = ALPHA_DIR / "data" / "fundamentals" / "MASTER_fundamentals_pit.parquet"

_CACHE: dict = {}


def load_sector_map() -> pd.DataFrame:
    if "sector_map" not in _CACHE:
        _CACHE["sector_map"] = pd.read_parquet(SECTOR_MAP_PATH)
    return _CACHE["sector_map"]


def _load_cube_close() -> pd.DataFrame:
    if "cube_close" not in _CACHE:
        _CACHE["cube_close"] = pd.read_parquet(CUBE_CLOSE_PATH)
    return _CACHE["cube_close"]


def _load_bench() -> pd.Series:
    if "bench" not in _CACHE:
        _CACHE["bench"] = pd.read_parquet(CUBE_BENCH_PATH)["NSEI"]
    return _CACHE["bench"]


# ==========================================================================
# (a) sector composites + momentum / RS
# ==========================================================================
def build_sector_composites(level: str = "macro_sector", min_names: int = 3) -> pd.DataFrame:
    """Equal-weight, daily-rebalanced composite index per sector/sub_sector,
    built only from the cube_close 751-symbol universe. Index base=100 at
    each sector's first qualifying date. Sectors with < min_names valid
    constituents on a date are NaN that day (never fabricate a "sector"
    composite off 1-2 names)."""
    assert level in ("macro_sector", "sub_sector")
    key = f"composites_{level}_{min_names}"
    if key in _CACHE:
        return _CACHE[key]
    close = _load_cube_close()
    smap = load_sector_map().set_index("symbol")[level]
    ret = close.pct_change()
    sectors = smap.reindex(ret.columns)
    out = {}
    for sec, syms in sectors.dropna().groupby(sectors.dropna()).groups.items():
        cols = [c for c in syms if c in ret.columns]
        if len(cols) < min_names:
            continue
        sub = ret[cols]
        n_valid = sub.notna().sum(axis=1)
        mean_ret = sub.mean(axis=1, skipna=True).where(n_valid >= min_names)
        out[sec] = mean_ret
    ret_df = pd.DataFrame(out).sort_index()
    idx = (1.0 + ret_df.fillna(0.0)).cumprod() * 100.0
    # mask dates before each sector first has a valid return (avoid a flat
    # 100-run standing in for "no data yet")
    first_valid = ret_df.notna().cummax()
    idx = idx.where(first_valid)
    _CACHE[key] = idx
    return idx


def sector_momentum(composites: pd.DataFrame, lookback: int = 252, skip: int = 21) -> pd.DataFrame:
    """12-1 style trailing return per sector: composite[t-skip]/composite[t-lookback]-1,
    same skip-month convention as the firm's core stock-level 12-1 momentum
    factor (FRAMEWORK_CATALOG.md #1). Values strictly <= t."""
    shifted = composites.shift(skip)
    base = composites.shift(lookback)
    return shifted / base - 1.0


def sector_rs_vs_market(composites: pd.DataFrame, lookback: int = 252, skip: int = 21) -> pd.DataFrame:
    """Sector momentum minus NIFTY (NSEI) momentum, same window."""
    bench = _load_bench()
    bench_mom = bench.shift(skip) / bench.shift(lookback) - 1.0
    sec_mom = sector_momentum(composites, lookback, skip)
    return sec_mom.sub(bench_mom, axis=0)


def own_sector_rs_factor(panel: pd.DataFrame, level: str = "macro_sector",
                          lookback: int = 252, skip: int = 21, min_names: int = 3) -> pd.Series:
    """Stock-level factor = the RS (own sector/sub_sector momentum - market
    momentum) of the sector the stock BELONGS to, broadcast to every member,
    as of each panel date t. This is the S1 'sector-momentum tilt' factor.
    PIT-safe direct lookup: panel dates are a subset of cube_close's daily
    calendar (verified), so no as-of join / lookahead risk -- every stock's
    value at t comes from a composite built using prices <= t only."""
    composites = build_sector_composites(level=level, min_names=min_names)
    rs = sector_rs_vs_market(composites, lookback=lookback, skip=skip)
    smap = load_sector_map().set_index("symbol")[level]

    ds = panel[["date", "symbol"]].drop_duplicates().copy()
    ds["date"] = pd.to_datetime(ds["date"])
    ds["sec"] = ds["symbol"].map(smap)
    ds = ds.dropna(subset=["sec"])

    rs_long = rs.reset_index().melt(id_vars="Date", var_name="sec", value_name="factor")
    rs_long = rs_long.rename(columns={"Date": "date"})

    m = ds.merge(rs_long, on=["date", "sec"], how="left").dropna(subset=["factor"])
    return m.set_index(["date", "symbol"])["factor"]


# ==========================================================================
# (b) within-sector peer-relative scoring helper (generic, any factor)
# ==========================================================================
def peer_relative(factor: pd.Series, level: str = "sub_sector", method: str = "z",
                   min_peers: int = 3) -> pd.Series:
    """Cross-sectional peer-relative transform of ANY (date,symbol)-indexed
    factor: z-score or percentile-rank WITHIN sub_sector/macro_sector at
    each date, demeaned so the score reflects standing vs SAME-SECTOR peers
    rather than the whole universe. Purely cross-sectional at each date ->
    lookahead-free by construction (no time-series component at all).
    method='z': (x - group_mean)/group_std per (date, sector).
    method='rank': percentile rank within (date, sector) minus 0.5 (centered).
    Peer groups with < min_peers members on a date are dropped (a
    'peer-relative' score needs a real peer set to mean anything)."""
    assert method in ("z", "rank")
    f = factor.rename("factor").reset_index()
    cols_lower = {c.lower(): c for c in f.columns}
    if "date" in cols_lower and "symbol" in cols_lower:
        f = f.rename(columns={cols_lower["date"]: "date", cols_lower["symbol"]: "symbol"})
    if not {"date", "symbol"}.issubset(f.columns):
        raise ValueError("factor must be indexed/columned by (date, symbol)")

    smap = load_sector_map().set_index("symbol")[level]
    f["sec"] = f["symbol"].map(smap)
    f = f.dropna(subset=["sec", "factor"])

    counts = f.groupby(["date", "sec"])["factor"].transform("count")
    f = f[counts >= min_peers].copy()
    if f.empty:
        return pd.Series(dtype=float, name="peer_score")

    grp = f.groupby(["date", "sec"])["factor"]
    if method == "z":
        mean = grp.transform("mean")
        std = grp.transform("std")
        f["peer_score"] = (f["factor"] - mean) / std.replace(0.0, np.nan)
    else:
        f["peer_score"] = grp.rank(pct=True) - 0.5

    f = f.dropna(subset=["peer_score"])
    return f.set_index(["date", "symbol"])["peer_score"]


# ==========================================================================
# (c) sector fundamental aggregates (median ROIC / EY / revenue growth)
# ==========================================================================
def _revenue_growth_factor(panel: pd.DataFrame) -> pd.Series:
    """YoY revenue growth, PIT: computed at (symbol, fiscal_year) grain then
    merge_asof'd onto panel dates by available_date (backward), same
    convention as builders_value.py/builders_quality.py. Not fed into the
    harness directly here; used only to build the descriptive sector
    median-growth aggregate in sector_fundamental_aggregates().

    Metric choice [DATA, verified]: 'sales' is the general-purpose top-line
    metric_norm (48,271 rows / 2277 symbols); 'revenue' is a SEPARATE,
    bank/NBFC-specific line item (1,158 rows / only 90 symbols -- financials
    report interest/fee income as 'revenue', not 'sales'). Using 'revenue'
    alone (as an earlier draft of this function did) silently produced
    non-null growth almost only for Financial Services -- caught here, not
    shipped. Correct construction: prefer 'sales' per (symbol, fiscal_year);
    fall back to 'revenue' only where 'sales' is absent for that row (covers
    the bank/NBFC top-line without double counting)."""
    f = pd.read_parquet(FUND_PATH)
    rev = f[f["metric_norm"].isin(["sales", "revenue"])].copy()
    # explicit priority (NOT alphabetical -- 'revenue' < 'sales' alphabetically,
    # which would silently invert the intended preference): 0=sales, 1=revenue.
    rev["_pref"] = rev["metric_norm"].map({"sales": 0, "revenue": 1})
    rev = rev.sort_values(["nse_symbol", "fiscal_year", "_pref"])
    rev = rev.drop_duplicates(subset=["nse_symbol", "fiscal_year"], keep="first")
    rev = rev.sort_values(["nse_symbol", "fiscal_year"])
    rev["growth"] = rev.groupby("nse_symbol")["value"].pct_change()
    rev = rev.dropna(subset=["growth", "available_date"])
    rev = rev.rename(columns={"nse_symbol": "symbol"})
    rev["symbol"] = rev["symbol"].astype(str)
    rev["available_date"] = pd.to_datetime(rev["available_date"]).astype("datetime64[ns]")

    ds = panel[["date", "symbol"]].drop_duplicates().copy()
    ds["symbol"] = ds["symbol"].astype(str)
    ds["date"] = pd.to_datetime(ds["date"]).astype("datetime64[ns]")
    ds = ds.sort_values("date")

    right = rev[["symbol", "available_date", "growth"]].rename(columns={"available_date": "date"})
    right = right.sort_values("date")

    merged = pd.merge_asof(ds, right, on="date", by="symbol", direction="backward")
    merged = merged.dropna(subset=["growth"])
    return merged.set_index(["date", "symbol"])["growth"]


def sector_fundamental_aggregates(panel: pd.DataFrame, level: str = "macro_sector") -> pd.DataFrame:
    """Sector-level median ROIC / earnings-yield / revenue-growth per panel
    date -- descriptive relative-comparison table (not itself fed to the
    harness). Reuses the already-PIT builders build_H014_earnings_yield
    (builders_value.py) and build_roic_factor (builders_quality.py)."""
    ey = _bv.build_H014_earnings_yield(panel)
    roic = _bq.build_roic_factor(panel)
    growth = _revenue_growth_factor(panel)
    smap = load_sector_map().set_index("symbol")[level]

    def _agg(s: pd.Series, name: str) -> pd.Series:
        d = s.rename(name).reset_index()
        d["sec"] = d["symbol"].map(smap)
        d = d.dropna(subset=["sec"])
        return d.groupby(["date", "sec"])[name].median()

    out = pd.concat(
        [_agg(ey, "ey_median"), _agg(roic, "roic_median"), _agg(growth, "growth_median")],
        axis=1,
    )
    return out.reset_index()


if __name__ == "__main__":
    from harness import load_panel

    panel, src = load_panel()
    print(f"panel_source={src} rows={len(panel)}")

    for level in ("macro_sector", "sub_sector"):
        comp = build_sector_composites(level=level)
        print(f"[{level}] composites: {comp.shape[1]} sectors, "
              f"{comp.notna().any(axis=1).sum()} dates with >=1 sector live")

    rs = own_sector_rs_factor(panel, level="macro_sector")
    print(f"own_sector_rs_factor (macro): n_obs={len(rs)}, "
          f"n_dates={rs.index.get_level_values('date').nunique()}")

    ey = _bv.build_H014_earnings_yield(panel)
    pr = peer_relative(ey, level="sub_sector", method="z")
    print(f"peer_relative(EY, sub_sector): n_obs={len(pr)} of raw {len(ey)}")

    agg = sector_fundamental_aggregates(panel, level="macro_sector")
    print(agg.tail(5).to_string())
