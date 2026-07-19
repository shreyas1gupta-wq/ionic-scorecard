"""
W4T -- Sanjay Kulkarni (FM, Fundamental Quality & Value) NEXT-SLEEVE candidate
factor builders. NOT part of the frozen composite -- screening-layer test only,
per RESEARCH_PROTOCOL.md S3/S4 (one code path = harness.evaluate()).

Two factors, per wave4/hypotheses_w4_books.json W4B-02 and
wave4/hypotheses_w4_pms.json W4P-03:

W4T-01 distress composite (adapted Ohlson O-score / Campbell-Hilscher-Szilagyi):
    Per-date cross-sectional z-score rank-average (no fitted weights, per firm's
    no-ML-combiner rule) of 7 components, all oriented so HIGH z = MORE
    distressed, then negated so the final factor score is HIGH = LOW distress
    (per W4B-02's own convention: "score = -composite_distress").
    Components (numbered as in the hypothesis card):
      1. leverage = total_liabilities / total_assets                (direct)
      2. size     = -mktcap_log                                      (direct)
      3. profitability = net_profit / total_assets                   (NEGATED: -z)
      4. interest coverage = -(operating_profit / interest)          (direct;
         inverted so LOW coverage -> HIGH value, per W4B-02 text)
      5. negative-equity dummy = 1{(reserves+equity_capital) < 0}    (direct)
      6. earnings-deterioration dummy = 1{net_profit fell 2 consecutive FYs} (direct)
      7. equity-vol proxy = vol_252 (panel_long)                     (direct)
    composite_distress = mean(z1, z2, -z3, z4, z5, z6, z7) [skipna]
    score = -composite_distress   <- this is the returned factor (HIGH=safe)
    Refinement child (pre-registered in the hypothesis card, used ONLY if the
    7-component base fails a hard gate / has thin coverage): 4-component version
    (leverage, size, profitability, earnings-deterioration dummy only).

W4P-03 cyclical-sector normalized (multi-year-average) earnings yield:
    Within cyclical macro_sectors only (Metals & Mining, Automobile and Auto
    Components, Capital Goods, Construction Materials -- NBFC explicitly
    DROPPED, disclosed below), normalized_EY = trailing 5-7yr PIT-available
    AVERAGE eps-in-rs / price, vs plain TTM-EY (latest PIT annual EPS / price)
    computed from the SAME price source for a clean head-to-head.

DISCLOSED DEVIATIONS / CAVEATS (not fabrication):
1. W4P-03's "cyclical sectors" per the hypothesis card = "metals/mining,
   autos/CV, capital goods, cement, NBFC". sector_map.parquet's macro_sector
   taxonomy gives clean tags for the first four (Metals & Mining, Automobile
   and Auto Components, Capital Goods, Construction Materials=cement) but NBFC
   is NOT separable from banks in this map -- the underlying 79-bucket fine
   source bundles both under a single "Finance" fine label, which rolls up to
   macro_sector "Financial Services"/"Finance" alongside banks, insurers, and
   capital-markets names. Including all of "Financial Services" would dilute
   the cyclical subset with non-cyclical financials (banks, insurers) that the
   hypothesis does NOT intend to include. NBFC is therefore DROPPED from the
   cyclical universe here rather than fabricated via an ad hoc keyword split
   of company names (which would be an undisclosed, untested heuristic).
2. Price source for BOTH the TTM-EY baseline and the normalized-EY leg is
   panel/cube_close_long.parquet (per the task's DATA section), melted from
   wide (date-index, symbol-columns) to long -- distinct from
   builders_value.py's build_H014_earnings_yield which reads panel/cube_close.parquet.
   Reusing build_H014 as-is would silently mix price sources across the two
   legs being compared; this module re-derives TTM-EY locally against the same
   cube_close_long source as the normalized leg so the head-to-head is clean.
3. Fundamentals are ANNUAL (fiscal_year grain) -- same caveat as
   builders_value.py/builders_w2_issuance.py: "TTM" = latest PIT-available
   ANNUAL EPS print, not a rolling quarterly sum.
4. Trailing-average EPS window: "5-7yr" per the hypothesis card is implemented
   as up to the last 7 available fiscal-year EPS prints (chronological, PIT-
   respecting -- only fiscal years already reported as of that row), computed
   ONLY when at least 5 non-null prints exist in that window (else NaN, thin-
   coverage symbols dropped rather than averaged over <5 years, which would
   silently under-power the "cycle" the construct is meant to capture).
5. Earnings-deterioration dummy (component 6 of W4T-01) requires at least 3
   consecutive reported fiscal years of net_profit (to detect a 2-year decline
   streak); fewer years -> NaN, not a fabricated 0.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent            # ALPHA_RANKER/rnd
ALPHA_DIR = RND_DIR.parent               # ALPHA_RANKER

FUND_PATH = ALPHA_DIR / "data" / "fundamentals" / "MASTER_fundamentals_pit.parquet"
CUBE_CLOSE_LONG_PATH = RND_DIR / "panel" / "cube_close_long.parquet"
SECTOR_MAP_PATH = ALPHA_DIR / "data" / "universe" / "sector_map.parquet"

CYCLICAL_MACRO_SECTORS = {
    "Metals & Mining",
    "Automobile and Auto Components",
    "Capital Goods",
    "Construction Materials",
}

_CACHE: dict = {}


# ==========================================================================
# 0. shared loaders
# ==========================================================================
def load_price_cube_long() -> pd.DataFrame:
    """cube_close_long.parquet is a WIDE frame (date index, symbol columns)
    despite the filename -- melted here to a tidy (date,symbol,price) long
    table, same convention as builders_value.load_price_cube_long()."""
    if "price_long_w4t" in _CACHE:
        return _CACHE["price_long_w4t"]
    cube = pd.read_parquet(CUBE_CLOSE_LONG_PATH)
    cube.index = pd.to_datetime(cube.index)
    long = cube.reset_index().melt(id_vars=cube.index.name or "index",
                                    var_name="symbol", value_name="price")
    long = long.rename(columns={cube.index.name or "index": "date"})
    long["date"] = pd.to_datetime(long["date"])
    out = long.dropna(subset=["price"])
    out = out[out["price"] > 0]
    _CACHE["price_long_w4t"] = out
    return out


def load_sector_map() -> pd.DataFrame:
    if "sector_map_w4t" not in _CACHE:
        _CACHE["sector_map_w4t"] = pd.read_parquet(SECTOR_MAP_PATH)
    return _CACHE["sector_map_w4t"]


def cyclical_symbols() -> set:
    sm = load_sector_map()
    return set(sm.loc[sm["macro_sector"].isin(CYCLICAL_MACRO_SECTORS), "symbol"])


def load_fundamentals() -> pd.DataFrame:
    if "fund_w4t" not in _CACHE:
        df = pd.read_parquet(FUND_PATH)
        df = df[df["nse_symbol"].notna()].copy()
        df["available_date"] = pd.to_datetime(df["available_date"])
        _CACHE["fund_w4t"] = df
    return _CACHE["fund_w4t"]


def _fund_wide() -> pd.DataFrame:
    """One row per (symbol, fiscal_year), metric_norm columns pivoted wide,
    plus that fiscal_year's max available_date -- same pattern as
    builders_w2_issuance._load_fund_wide()."""
    if "fund_wide_w4t" in _CACHE:
        return _CACHE["fund_wide_w4t"]
    df = load_fundamentals().rename(columns={"nse_symbol": "symbol"})
    piv = df.pivot_table(index=["symbol", "fiscal_year"], columns="metric_norm",
                          values="value", aggfunc="last")
    avail = df.groupby(["symbol", "fiscal_year"])["available_date"].max()
    wide = piv.join(avail).reset_index().sort_values(["symbol", "fiscal_year"]).reset_index(drop=True)
    _CACHE["fund_wide_w4t"] = wide
    return wide


def _asof_to_panel(panel_ds: pd.DataFrame, annual: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """merge_asof (backward, by symbol) an annual (symbol, available_date, value_col)
    table onto a panel (date,symbol) grid. No lookahead: only fiscal years with
    available_date <= panel date are visible at that date."""
    sub = annual[["symbol", "available_date", value_col]].dropna(subset=[value_col]).copy()
    sub["symbol"] = sub["symbol"].astype(str)
    sub["available_date"] = pd.to_datetime(sub["available_date"]).astype("datetime64[ns]")
    sub = sub.sort_values("available_date").rename(columns={"available_date": "date"})
    p = panel_ds[["date", "symbol"]].drop_duplicates().copy()
    p["symbol"] = p["symbol"].astype(str)
    p["date"] = pd.to_datetime(p["date"]).astype("datetime64[ns]")
    p = p.sort_values("date")
    merged = pd.merge_asof(p, sub, on="date", by="symbol", direction="backward")
    return merged.dropna(subset=[value_col])


def _winsorize(s: pd.Series, p=0.01) -> pd.Series:
    lo, hi = s.quantile(p), s.quantile(1 - p)
    return s.clip(lo, hi)


def _zscore_by_date(df: pd.DataFrame, col: str) -> pd.Series:
    def _z(g):
        v = _winsorize(g[col].astype(float))
        sd = v.std(ddof=0)
        if not sd or np.isnan(sd) or sd == 0:
            return pd.Series(np.nan, index=g.index)
        return (v - v.mean()) / sd
    return df.groupby("date", group_keys=False).apply(_z, include_groups=False)


# ==========================================================================
# 1. W4T-01 distress composite
# ==========================================================================
def _distress_annual_table() -> pd.DataFrame:
    """Per (symbol, fiscal_year): raw components 1,3,4,5,6 (2=size, 7=eqvol
    come from panel_long directly, not fundamentals) + available_date."""
    if "distress_annual_w4t" in _CACHE:
        return _CACHE["distress_annual_w4t"]
    wide = _fund_wide()

    def _grp(g: pd.DataFrame) -> pd.DataFrame:
        g = g.sort_values("fiscal_year").reset_index(drop=True)
        tl = g.get("total liabilities")
        ta = g.get("total assets")
        npft = g.get("net profit")
        opft = g.get("operating profit")
        interest = g.get("interest")
        reserves = g.get("reserves")
        eqcap = g.get("equity capital")

        g["leverage"] = (tl / ta).replace([np.inf, -np.inf], np.nan) if (tl is not None and ta is not None) else np.nan
        g["profitability"] = (npft / ta).replace([np.inf, -np.inf], np.nan) if (npft is not None and ta is not None) else np.nan

        if opft is not None and interest is not None:
            cov_raw = opft / interest.where(interest > 0)
            g["int_coverage_inv"] = (-cov_raw).replace([np.inf, -np.inf], np.nan)
        else:
            g["int_coverage_inv"] = np.nan

        if reserves is not None and eqcap is not None:
            g["negeq_dummy"] = ((reserves + eqcap) < 0).astype(float)
        else:
            g["negeq_dummy"] = np.nan

        if npft is not None:
            d1 = npft.diff()          # FY_t - FY_{t-1}
            d0 = npft.shift(1).diff()  # FY_{t-1} - FY_{t-2}
            g["earn_deter_dummy"] = ((d1 < 0) & (d0 < 0)).astype(float)
            # NaN out rows without 3 consecutive reported years (not fabricated 0)
            need3 = npft.notna() & npft.shift(1).notna() & npft.shift(2).notna()
            g.loc[~need3, "earn_deter_dummy"] = np.nan
        else:
            g["earn_deter_dummy"] = np.nan

        return g

    out = wide.groupby("symbol", group_keys=False).apply(_grp, include_groups=False)
    out = out.assign(symbol=wide["symbol"].values) if "symbol" not in out.columns else out
    keep = ["symbol", "fiscal_year", "available_date", "leverage", "profitability",
            "int_coverage_inv", "negeq_dummy", "earn_deter_dummy"]
    out = out[keep].dropna(subset=["available_date"])
    _CACHE["distress_annual_w4t"] = out
    return out


def build_distress_score_7comp(panel: pd.DataFrame) -> pd.Series:
    """W4T-01 base construction: 7-component composite, score = -composite_distress
    (HIGH score = LOW distress). panel must be panel_long (needs mktcap_log, vol_252)."""
    ds = panel[["date", "symbol"]].drop_duplicates()
    annual = _distress_annual_table()

    parts = {}
    for col in ("leverage", "profitability", "int_coverage_inv", "negeq_dummy", "earn_deter_dummy"):
        a = _asof_to_panel(ds, annual, col)
        a["z"] = _zscore_by_date(a[["date", col]], col)
        parts[col] = a.set_index(["date", "symbol"])["z"]

    p2 = panel[["date", "symbol", "mktcap_log"]].drop_duplicates(["date", "symbol"]).copy()
    p2["size_raw"] = -p2["mktcap_log"]
    p2["z_size"] = _zscore_by_date(p2[["date", "size_raw"]], "size_raw")
    parts["size"] = p2.set_index(["date", "symbol"])["z_size"]

    p7 = panel[["date", "symbol", "vol_252"]].drop_duplicates(["date", "symbol"]).copy()
    p7["z_eqvol"] = _zscore_by_date(p7[["date", "vol_252"]], "vol_252")
    parts["eqvol"] = p7.set_index(["date", "symbol"])["z_eqvol"]

    z = pd.DataFrame({
        "z1_leverage": parts["leverage"],
        "z2_size": parts["size"],
        "z3_profitability_neg": -parts["profitability"],
        "z4_intcov": parts["int_coverage_inv"],
        "z5_negeq": parts["negeq_dummy"],
        "z6_earndeter": parts["earn_deter_dummy"],
        "z7_eqvol": parts["eqvol"],
    })
    composite_distress = z.mean(axis=1, skipna=True)
    n_present = z.notna().sum(axis=1)
    composite_distress = composite_distress.where(n_present >= 4)  # require >=4/7 to score a name
    score = -composite_distress
    return score.dropna().rename("factor")


def build_distress_score_4comp(panel: pd.DataFrame) -> pd.Series:
    """W4T-01 pre-registered refinement child: leverage, size, profitability,
    earnings-deterioration dummy only (dropping int-coverage/negeq/eqvol)."""
    ds = panel[["date", "symbol"]].drop_duplicates()
    annual = _distress_annual_table()

    parts = {}
    for col in ("leverage", "profitability", "earn_deter_dummy"):
        a = _asof_to_panel(ds, annual, col)
        a["z"] = _zscore_by_date(a[["date", col]], col)
        parts[col] = a.set_index(["date", "symbol"])["z"]

    p2 = panel[["date", "symbol", "mktcap_log"]].drop_duplicates(["date", "symbol"]).copy()
    p2["size_raw"] = -p2["mktcap_log"]
    p2["z_size"] = _zscore_by_date(p2[["date", "size_raw"]], "size_raw")
    parts["size"] = p2.set_index(["date", "symbol"])["z_size"]

    z = pd.DataFrame({
        "z1_leverage": parts["leverage"],
        "z2_size": parts["size"],
        "z3_profitability_neg": -parts["profitability"],
        "z6_earndeter": parts["earn_deter_dummy"],
    })
    composite_distress = z.mean(axis=1, skipna=True)
    n_present = z.notna().sum(axis=1)
    composite_distress = composite_distress.where(n_present >= 3)
    score = -composite_distress
    return score.dropna().rename("factor")


# ==========================================================================
# 2. W4P-03 cyclical normalized EY vs plain TTM-EY (same price source)
# ==========================================================================
def _eps_annual_table() -> pd.DataFrame:
    if "eps_annual_w4t" in _CACHE:
        return _CACHE["eps_annual_w4t"]
    df = load_fundamentals()
    m = df[df["metric_norm"] == "eps in rs"].dropna(subset=["value", "available_date"]).copy()
    m = m.sort_values(["nse_symbol", "fiscal_year", "is_fresh", "available_date"])
    m = m.drop_duplicates(["nse_symbol", "fiscal_year"], keep="last")
    m = m.rename(columns={"nse_symbol": "symbol"})
    m = m[["symbol", "fiscal_year", "value", "available_date"]].sort_values(["symbol", "fiscal_year"])
    _CACHE["eps_annual_w4t"] = m
    return m


def build_ttm_ey(panel: pd.DataFrame) -> pd.Series:
    """Plain TTM-EY = latest PIT-available annual EPS / price. Price source:
    cube_close_long.parquet (matches the normalized leg, NOT builders_value's
    cube_close.parquet -- see module docstring deviation #2)."""
    ds = panel[["date", "symbol"]].drop_duplicates()
    eps = _eps_annual_table().rename(columns={"value": "eps_ttm"})
    eps_a = _asof_to_panel(ds, eps, "eps_ttm")
    price = load_price_cube_long()
    m = eps_a.merge(price, on=["date", "symbol"], how="inner")
    m = m[(m["price"] > 0) & m["eps_ttm"].notna()]
    m["factor"] = m["eps_ttm"] / m["price"]
    return m.set_index(["date", "symbol"])["factor"].replace([np.inf, -np.inf], np.nan).dropna()


def _normalized_eps_annual_table(min_years: int = 5, max_years: int = 7) -> pd.DataFrame:
    """Per (symbol, fiscal_year): trailing up-to-max_years mean of eps-in-rs
    (chronological, PIT-respecting -- only fiscal years already reported as of
    that row), computed only when >= min_years non-null prints exist in the
    window. Time-stamped with THAT row's own available_date (no lookahead:
    the average becomes known exactly when the latest print in it does)."""
    if "eps_norm_annual_w4t" in _CACHE:
        return _CACHE["eps_norm_annual_w4t"]
    eps = _eps_annual_table()

    def _grp(g: pd.DataFrame) -> pd.DataFrame:
        g = g.sort_values("fiscal_year").reset_index(drop=True)
        roll = g["value"].rolling(window=max_years, min_periods=min_years).mean()
        g["eps_norm"] = roll
        return g

    out = eps.groupby("symbol", group_keys=False).apply(_grp, include_groups=False)
    out = out.assign(symbol=eps["symbol"].values) if "symbol" not in out.columns else out
    out = out[["symbol", "fiscal_year", "available_date", "eps_norm"]].dropna(subset=["eps_norm", "available_date"])
    _CACHE["eps_norm_annual_w4t"] = out
    return out


def build_cyclical_normalized_ey(panel: pd.DataFrame) -> pd.Series:
    """W4P-03: normalized_EY = trailing 5-7yr avg EPS / price, same price
    source as build_ttm_ey. Caller is responsible for restricting `panel` to
    the cyclical-sector subset before calling (this function does NOT filter
    sectors itself, so it can also be run un-restricted for diagnostics)."""
    ds = panel[["date", "symbol"]].drop_duplicates()
    epsn = _normalized_eps_annual_table()
    epsn_a = _asof_to_panel(ds, epsn, "eps_norm")
    price = load_price_cube_long()
    m = epsn_a.merge(price, on=["date", "symbol"], how="inner")
    m = m[(m["price"] > 0) & m["eps_norm"].notna()]
    m["factor"] = m["eps_norm"] / m["price"]
    return m.set_index(["date", "symbol"])["factor"].replace([np.inf, -np.inf], np.nan).dropna()
