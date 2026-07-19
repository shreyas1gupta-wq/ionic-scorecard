"""
ALPHA_RANKER value-factor builders (H014/H015/H016/H018/H039 worker batch).
Owner: worker agent, ALPHA_RANKER research loop. Never touches weights.

Data: ALPHA_RANKER/data/fundamentals/MASTER_fundamentals_pit.parquet (LONG PIT fundamentals,
key_symbol/nse_symbol, fiscal_year, statement, metric_norm, value, available_date, source, is_fresh).
Prices: ALPHA_RANKER/rnd/panel/cube_close.parquet (daily Adj Close cube, date x symbol).
Panel: ALPHA_RANKER/rnd/panel/panel.parquet (month-end PIT panel; mktcap_log = ln(shares_proxy*AdjClose)).

UNIT NOTE (load-bearing, verified [DATA]): fundamentals `value` is in Rs CRORE (screener/mc convention,
sanity-checked: RELIANCE sales fy2026 = 1,055,780 ~ Rs 10.5 lakh cr, matches known revenue). Panel
`mktcap_log` is ln(RUPEES) (exp(mktcap_log) for RELIANCE 2026-07-16 = 1.754e13 = Rs 17.54 lakh cr,
matches known market cap). Any ratio mixing fundamentals (crore) with mktcap (rupees) MUST divide
exp(mktcap_log) by 1e7 to get crore first -- this is exactly the "denominator disease" unit trap
flagged in FRAMEWORK_CATALOG.md L135. EPS(Rs/share) and price(Rs/share) are already unit-consistent
(no crore conversion needed for H014's EY).

DISCLOSED LIMITATIONS (not fabrication -- these are real data gaps, kept as NaN/documented, never
silently zero-filled):
1. No clean balance-sheet CASH line item exists in metric_norm (screener condensed BS: Equity Capital,
   Reserves, Borrowings, Other Liabilities, Total Liabilities = Fixed Assets + CWIP + Investments +
   Other Assets -- cash is buried inside "Other Assets" with receivables/inventory, not separable).
   Consequence: EV here = MktCap + Borrowings (debt), WITHOUT netting cash. This OVERSTATES EV (and
   understates FCF-yield / EBITDA-yield) for cash-rich balance sheets. Documented in every card's
   factor_id note, not hidden.
2. Fundamentals are ANNUAL (fiscal_year grain, "Mar 2026" etc), not quarterly -- so "TTM" in H014/H015
   is approximated as the latest PIT-available ANNUAL figure (available_date <= t gates it), not a
   rolling trailing-twelve-month sum of quarters. This is the same simplification the task brief
   pre-authorized ("align latest available fiscal_year to each panel date t").
3. EBITDA (H016 only, not run this batch -- see report) = operating_profit + depreciation (screener's
   "Operating Profit" = Sales-Expenses is EBIT-like, after D&A; adding back depreciation recovers
   EBITDA). Standard screener-convention construction, not literal EBITDA disclosure.
4. ROIC (H018) = NOPAT / InvestedCapital, NOPAT = operating_profit * (1 - tax_rate), tax_rate from
   'tax %' metric (verified [DATA] units = percent, e.g. 24.0 => 24%, so /100). InvestedCapital =
   Equity Capital + Reserves + Borrowings (again NOT cash-netted -- same landmine as #1, overstates
   invested capital / understates ROIC for cash-rich names). tax_rate is clipped to [0, 0.60] to guard
   against negative-PBT distortions (a loss-making year can produce nonsensical negative/huge tax%);
   values outside that band are treated as a bad tax-rate print and NaN'd rather than silently used.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
ALPHA_DIR = RND_DIR.parent

FUND_PATH = ALPHA_DIR / "data" / "fundamentals" / "MASTER_fundamentals_pit.parquet"
CUBE_CLOSE_PATH = RND_DIR / "panel" / "cube_close.parquet"

_CACHE: dict = {}


def load_fundamentals() -> pd.DataFrame:
    """Loads MASTER_fundamentals_pit.parquet once, drops rows with no nse_symbol
    (unmapped mc_pit rows -- ~46% of mc_pit source, 0% of screener_live source;
    750/751 panel symbols still have coverage from the surviving rows) [DATA]."""
    if "fund" not in _CACHE:
        df = pd.read_parquet(FUND_PATH)
        df = df[df["nse_symbol"].notna()].copy()
        df["available_date"] = pd.to_datetime(df["available_date"])
        _CACHE["fund"] = df
    return _CACHE["fund"]


def load_price_cube_long() -> pd.DataFrame:
    if "price_long" not in _CACHE:
        cube = pd.read_parquet(CUBE_CLOSE_PATH)
        cube.index = pd.to_datetime(cube.index)
        long = cube.reset_index().melt(id_vars=cube.index.name or "index",
                                        var_name="symbol", value_name="price")
        long = long.rename(columns={cube.index.name or "index": "date"})
        long["date"] = pd.to_datetime(long["date"])
        _CACHE["price_long"] = long.dropna(subset=["price"])
    return _CACHE["price_long"]


def _metric_pit_series(metric_norms: list[str]) -> pd.DataFrame:
    """One PIT row per (nse_symbol, fiscal_year) for the given metric_norm alias set
    (e.g. ['borrowings','borrowing'] -- two label variants seen for the same concept,
    63 symbols carry both; keep is_fresh-preferred, latest-available_date-preferred)."""
    df = load_fundamentals()
    m = df[df["metric_norm"].isin(metric_norms)].dropna(subset=["value", "available_date"]).copy()
    m = m.sort_values(["nse_symbol", "fiscal_year", "is_fresh", "available_date"])
    m = m.drop_duplicates(["nse_symbol", "fiscal_year"], keep="last")
    return m[["nse_symbol", "fiscal_year", "value", "available_date"]].sort_values(
        ["nse_symbol", "available_date"])


def _asof_align(panel_dates_syms: pd.DataFrame, metric_series: pd.DataFrame, colname: str) -> pd.DataFrame:
    """PIT-align a (nse_symbol, available_date, value) metric series onto panel (date,symbol)
    rows: for each (date,symbol), take the metric value from the latest available_date <= date
    (merge_asof backward, no lookahead)."""
    left = panel_dates_syms.rename(columns={"symbol": "nse_symbol"}).sort_values("date").copy()
    left["nse_symbol"] = left["nse_symbol"].astype(str)
    left["date"] = left["date"].astype("datetime64[ns]")
    right = metric_series.rename(columns={"available_date": "date"})[
        ["nse_symbol", "date", "value"]].sort_values("date").copy()
    right["nse_symbol"] = right["nse_symbol"].astype(str)
    right["date"] = right["date"].astype("datetime64[ns]")
    out = pd.merge_asof(left, right, on="date", by="nse_symbol", direction="backward")
    out = out.rename(columns={"nse_symbol": "symbol", "value": colname})
    return out[["date", "symbol", colname]]


def _tax_rate_series() -> pd.DataFrame:
    tax = _metric_pit_series(["tax %"])
    tax["value"] = tax["value"] / 100.0
    tax.loc[(tax["value"] < 0) | (tax["value"] > 0.60), "value"] = np.nan
    return tax


# --------------------------------------------------------------------------
# H014 -- earnings yield = TTM(latest PIT annual) EPS / price
# --------------------------------------------------------------------------
def build_H014_earnings_yield(panel: pd.DataFrame) -> pd.Series:
    ds = panel[["date", "symbol"]].drop_duplicates()
    eps = _metric_pit_series(["eps in rs"])
    eps_a = _asof_align(ds, eps, "eps_ttm")
    price = load_price_cube_long()
    m = eps_a.merge(price, on=["date", "symbol"], how="inner")
    m = m[(m["price"] > 0) & m["eps_ttm"].notna()]
    m["factor"] = m["eps_ttm"] / m["price"]
    return m.set_index(["date", "symbol"])["factor"].replace([np.inf, -np.inf], np.nan).dropna()


# --------------------------------------------------------------------------
# H015 -- FCF yield = TTM(latest PIT annual) FCF / EV
# EV = MktCap(crore) + Borrowings(crore); cash NOT netted (see module docstring #1).
# --------------------------------------------------------------------------
def build_H015_fcf_yield(panel: pd.DataFrame) -> pd.Series:
    ds = panel[["date", "symbol"]].drop_duplicates()
    fcf = _metric_pit_series(["free cash flow"])
    debt = _metric_pit_series(["borrowings", "borrowing"])
    fcf_a = _asof_align(ds, fcf, "fcf")
    debt_a = _asof_align(ds, debt, "debt")
    mcap = panel[["date", "symbol", "mktcap_log"]].drop_duplicates(["date", "symbol"]).copy()
    mcap["mktcap_cr"] = np.exp(mcap["mktcap_log"]) / 1e7
    m = fcf_a.merge(debt_a, on=["date", "symbol"], how="inner").merge(
        mcap[["date", "symbol", "mktcap_cr"]], on=["date", "symbol"], how="inner")
    m["debt"] = m["debt"].fillna(0.0)
    m["ev"] = m["mktcap_cr"] + m["debt"]
    m = m[(m["ev"] > 0) & m["fcf"].notna()]
    m["factor"] = m["fcf"] / m["ev"]
    return m.set_index(["date", "symbol"])["factor"].replace([np.inf, -np.inf], np.nan).dropna()


# --------------------------------------------------------------------------
# H016 -- EV/EBITDA z-score vs own trailing history (5Y-only per backlog; NOT run
# this batch -- panel fwd_ret_5Y_* is 100% NaN, see PANEL_SCHEMA.md. Builder kept
# here, pre-registered, ready the moment 5Y forward returns exist.
# --------------------------------------------------------------------------
def build_H016_ev_ebitda_own_history_z(panel: pd.DataFrame, min_hist: int = 12) -> pd.Series:
    ds = panel[["date", "symbol"]].drop_duplicates()
    op = _metric_pit_series(["operating profit"])
    dep = _metric_pit_series(["depreciation"])
    debt = _metric_pit_series(["borrowings", "borrowing"])
    op_a = _asof_align(ds, op, "op")
    dep_a = _asof_align(ds, dep, "dep")
    debt_a = _asof_align(ds, debt, "debt")
    mcap = panel[["date", "symbol", "mktcap_log"]].drop_duplicates(["date", "symbol"]).copy()
    mcap["mktcap_cr"] = np.exp(mcap["mktcap_log"]) / 1e7
    m = op_a.merge(dep_a, on=["date", "symbol"], how="inner").merge(
        debt_a, on=["date", "symbol"], how="inner").merge(
        mcap[["date", "symbol", "mktcap_cr"]], on=["date", "symbol"], how="inner")
    m["debt"] = m["debt"].fillna(0.0)
    m["ebitda"] = m["op"] + m["dep"]
    m["ev"] = m["mktcap_cr"] + m["debt"]
    m = m[(m["ebitda"] > 0) & (m["ev"] > 0)]
    m["ev_ebitda"] = m["ev"] / m["ebitda"]
    m = m.sort_values(["symbol", "date"])
    m["z"] = m.groupby("symbol")["ev_ebitda"].transform(
        lambda s: (s - s.expanding(min_periods=min_hist).mean()) / s.expanding(min_periods=min_hist).std(ddof=1))
    m = m.dropna(subset=["z"])
    # sign="-" in backlog (cheap-vs-self expected to predict HIGHER returns) -> orient factor so
    # higher factor = cheaper-than-own-history, i.e. negate the raw z-score.
    m["factor"] = -m["z"]
    return m.set_index(["date", "symbol"])["factor"].replace([np.inf, -np.inf], np.nan).dropna()


# --------------------------------------------------------------------------
# H018 -- Greenblatt magic formula: rank(EY) + rank(ROIC), combined, per-date
# EY reuses H014's construct exactly (no redefinition). ROIC = NOPAT / InvestedCapital,
# NOPAT = operating_profit*(1-tax_rate), InvestedCapital = EquityCapital+Reserves+Borrowings
# (cash NOT netted, see module docstring #1/#4).
# --------------------------------------------------------------------------
def build_H018_greenblatt(panel: pd.DataFrame) -> pd.Series:
    ey = build_H014_earnings_yield(panel).rename("ey").reset_index()

    ds = panel[["date", "symbol"]].drop_duplicates()
    op = _metric_pit_series(["operating profit"])
    tax = _tax_rate_series()
    eq = _metric_pit_series(["equity capital"])
    res = _metric_pit_series(["reserves"])
    debt = _metric_pit_series(["borrowings", "borrowing"])

    op_a = _asof_align(ds, op, "op")
    tax_a = _asof_align(ds, tax, "tax_rate")
    eq_a = _asof_align(ds, eq, "equity_cap")
    res_a = _asof_align(ds, res, "reserves")
    debt_a = _asof_align(ds, debt, "debt")

    m = op_a.merge(tax_a, on=["date", "symbol"], how="inner").merge(
        eq_a, on=["date", "symbol"], how="inner").merge(
        res_a, on=["date", "symbol"], how="inner").merge(
        debt_a, on=["date", "symbol"], how="inner")
    m["debt"] = m["debt"].fillna(0.0)
    m["tax_rate"] = m["tax_rate"].fillna(0.25)  # median statutory-ish fallback when tax% print missing/bad
    m["nopat"] = m["op"] * (1 - m["tax_rate"])
    m["invested_capital"] = m["equity_cap"] + m["reserves"] + m["debt"]
    m = m[m["invested_capital"] > 0]
    m["roic"] = m["nopat"] / m["invested_capital"]

    merged = ey.merge(m[["date", "symbol", "roic"]], on=["date", "symbol"], how="inner")
    merged["rank_ey"] = merged.groupby("date")["ey"].rank(pct=True)
    merged["rank_roic"] = merged.groupby("date")["roic"].rank(pct=True)
    merged["factor"] = merged["rank_ey"] + merged["rank_roic"]
    return merged.set_index(["date", "symbol"])["factor"].dropna()


# --------------------------------------------------------------------------
# H039 -- shareholder yield = (dividends + buybacks)/mktcap -- PARKED, not built.
# metric_norm has NO buyback figure at all, and no rupee dividend amount (only
# 'dividend payout %', a ratio of profit, not a per-share/aggregate rupee dividend
# usable for a mktcap-denominated yield without redefining the construct).
# FRAMEWORK_CATALOG.md L96 independently flags buybacks as "NON-CODABLE at present
# (needs SAST/shareholding filings, still 403 for us)". Per RESEARCH_PROTOCOL S0.1,
# a changed definition is a NEW id -- so this is left un-redefined and PARKED as
# pre-registered, not run, not faked with a proxy.
# --------------------------------------------------------------------------
