"""
builders_w2_dcf.py -- H017 reverse-DCF implied-growth-gap + a simple 2-stage-DCF
intrinsic/price VALUE factor (WAVE-2 worker, ALPHA_RANKER). basis='resid',
5Y primary + 1Y secondary. Evaluated on panel_long.parquet (21yr panel -- has
REAL fwd_ret_5Y_*; the 5yr panel.parquet's fwd_ret_5Y_* is 100% NaN, see
PANEL_SCHEMA.md), joined against a per-company (not per-share) PIT earnings
basis.

WHY COMPANY-LEVEL, NOT PER-SHARE: MASTER_fundamentals_pit.parquet has no
shares-outstanding series (confirmed absent -- PANEL_SCHEMA.md ADDENDUM,
market_state.py docstring). A per-share EPS/Price DCF is therefore not
honestly buildable across history. net_profit(t) / mktcap(t) is mathematically
equivalent to EPS/Price (both numerator and denominator scale by the same
unknown share count) and is the SAME convention this codebase already uses for
EY/PE/PB in `rnd/panel/stock_valuation_pit.parquet` (built by market_state.py,
which already did the crore->rupee unit fix and the PIT merge_asof join) --
reused here directly rather than re-derived, so E0=net_profit and
price=mktcap throughout.

DCF CONSTRUCT (both legs share the same 2-stage engine, `_dcf_intrinsic`):
  E0        = latest PIT-available net_profit(t), Rs, company-level
              (stock_valuation_pit.parquet, already PIT-joined + unit-fixed)
  g_hist    = trailing 5Y CAGR of net_profit, computed from the RAW PIT
              fundamentals series itself (fiscal_year grain, shift(5) within
              symbol -- PIT-safe: a fiscal_year's growth only ever looks at
              fiscal years strictly before it, and the row is then asof-
              aligned to panel dates on `available_date`, so no future
              filing leaks into a past rebalance).
  Stage 1 (yr 1-5): E0 grows at g_hist, CLIPPED to [-40%, +60%]/yr --
              [INFERENCE] sane bound against small-base/loss-making-name
              blowups (a name going from Rs1cr to Rs5cr profit is a "+400%"
              CAGR artifact of a tiny base, not a 5-year-sustainable growth
              rate; the clip prevents one such row from dominating the
              cross-section or destabilizing the terminal-value denominator).
  Terminal (yr 5+): Gordon growth at g_terminal in {3%, 5%} -- assumption,
              tagged [INFERENCE].
  WACC in {11%, 13%, 15%} -- assumption, tagged [INFERENCE]. Flat across all
              names/years (no CAPM/size-premium build -- out of scope for this
              pass, documented as a simplification, not silently done).
  Intrinsic = sum_{i=1..5} E0*(1+g_hist_clipped)^i / (1+WACC)^i
              + [E0*(1+g_hist_clipped)^5 * (1+g_terminal)/(WACC-g_terminal)] / (1+WACC)^5

  factor_DCF_VALUE  = Intrinsic / mktcap(t)   (>1 = undervalued; oriented so
              HIGHER factor = cheaper = bullish, standard value-factor sign).

REVERSE-DCF IMPLIED-GROWTH GAP (H017, backlog sign="-"):
  Solve g_implied (stage-1 growth only, g_terminal held fixed at the same
  assumption) such that Intrinsic(g_implied; WACC, g_terminal) = mktcap(t) --
  i.e. "what 5yr growth rate is the market currently paying for". Vectorized
  bisection (60 iters, bounds [-90%, +500%]/yr -- Intrinsic is monotonic
  increasing in g_implied within these bounds for every WACC/g_terminal combo
  used here, since WACC(11-15%) always > g_terminal(3-5%): no singularity).
  gap = g_implied - g_hist. Backlog: "lower implied = cheaper" -> raw gap has
  a NEGATIVE expected relationship with forward return. Oriented here (same
  H016-style sign convention already used elsewhere in this codebase) so
  HIGHER factor = cheaper = bullish:
      factor_REVGAP = g_hist - g_implied   (= -gap)

SENSITIVITY GRID: both factors are built across all 3 WACC x 2 g_terminal = 6
combinations (see run_w2_dcf.py). A factor is reported ROBUST only if its
IC_IR sign/verdict is stable across the full grid; if it flips, it is too
fragile to trust a single point estimate and should be KILLed per the task
brief's own instruction ("if it flips with assumptions, KILL as too fragile").
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
ALPHA_DIR = RND_DIR.parent

FUND_PATH = ALPHA_DIR / "data" / "fundamentals" / "MASTER_fundamentals_pit.parquet"
STOCK_VAL_PATH = RND_DIR / "panel" / "stock_valuation_pit.parquet"

CRORE_TO_RUPEE = 1e7
G_CLIP = (-0.40, 0.60)

_CACHE: dict = {}


# --------------------------------------------------------------------------
# data loaders
# --------------------------------------------------------------------------
def load_stock_val() -> pd.DataFrame:
    """date,symbol,mktcap(Rs,company-level),net_profit(Rs,company-level) --
    reused as-is from market_state.py's already PIT-joined + unit-fixed build."""
    if "sv" not in _CACHE:
        df = pd.read_parquet(STOCK_VAL_PATH, columns=["date", "symbol", "mktcap", "net_profit"])
        df["date"] = pd.to_datetime(df["date"])
        df["symbol"] = df["symbol"].astype("object")
        _CACHE["sv"] = df
    return _CACHE["sv"]


def load_net_profit_pit_series() -> pd.DataFrame:
    """One row per (symbol, fiscal_year): PIT net_profit, Rs (crore->rupee
    converted, same unit fix as market_state.py), dedup by is_fresh/latest
    available_date when a fiscal_year has >1 print (restatements)."""
    if "np_series" not in _CACHE:
        df = pd.read_parquet(FUND_PATH, columns=[
            "nse_symbol", "fiscal_year", "metric_norm", "value", "available_date", "is_fresh"])
        df = df[df["nse_symbol"].notna() & (df["metric_norm"] == "net profit")].dropna(
            subset=["value", "available_date"]).copy()
        df["available_date"] = pd.to_datetime(df["available_date"])
        df = df.sort_values(["nse_symbol", "fiscal_year", "is_fresh", "available_date"])
        df = df.drop_duplicates(["nse_symbol", "fiscal_year"], keep="last")
        df = df.rename(columns={"nse_symbol": "symbol"})
        df["value"] = df["value"] * CRORE_TO_RUPEE
        _CACHE["np_series"] = df[["symbol", "fiscal_year", "value", "available_date"]].sort_values(
            ["symbol", "fiscal_year"])
    return _CACHE["np_series"]


def _trailing_cagr(series_df: pd.DataFrame, n_years: int = 5) -> pd.DataFrame:
    """Per symbol, trailing n_years CAGR of net_profit keyed on fiscal_year.
    PIT-safe by construction: shift(n_years) WITHIN each symbol's own
    fiscal-year-ordered series only ever reaches backward. Requires the two
    endpoints to actually be n_years apart on the fiscal calendar (guards
    against a gap in filings silently being read as a shorter/longer CAGR)
    and both endpoints > 0 (CAGR of a loss-making base is not meaningful)."""
    s = series_df.sort_values(["symbol", "fiscal_year"]).copy()
    s["value_lag"] = s.groupby("symbol")["value"].shift(n_years)
    s["fy_lag"] = s.groupby("symbol")["fiscal_year"].shift(n_years)
    valid = (s["value_lag"].notna() & (s["value"] > 0) & (s["value_lag"] > 0)
             & (s["fiscal_year"] - s["fy_lag"] == n_years))
    s["cagr"] = np.nan
    s.loc[valid, "cagr"] = (s.loc[valid, "value"] / s.loc[valid, "value_lag"]) ** (1.0 / n_years) - 1.0
    return s[["symbol", "fiscal_year", "available_date", "cagr"]]


def _asof_align_growth(ds: pd.DataFrame, growth_df: pd.DataFrame) -> pd.DataFrame:
    left = ds.sort_values("date").copy()
    left["symbol"] = left["symbol"].astype("object")
    left["date"] = left["date"].astype("datetime64[ns]")
    right = growth_df.dropna(subset=["cagr"]).rename(columns={"available_date": "date"})[
        ["symbol", "date", "cagr"]].sort_values("date").copy()
    right["symbol"] = right["symbol"].astype("object")
    right["date"] = right["date"].astype("datetime64[ns]")
    out = pd.merge_asof(left, right, on="date", by="symbol", direction="backward")
    return out


def prep_growth_and_base(panel: pd.DataFrame, n_years: int = 5) -> pd.DataFrame:
    """Returns date,symbol,E0,price,g_hist -- fully PIT-aligned, no lookahead.
    Cached per n_years since growth_and_base doesn't depend on WACC/g_terminal."""
    key = f"gb_{n_years}"
    if key in _CACHE:
        return _CACHE[key]
    ds = panel[["date", "symbol"]].drop_duplicates()
    sv = load_stock_val()
    base = ds.merge(sv, on=["date", "symbol"], how="inner").rename(
        columns={"net_profit": "E0", "mktcap": "price"})
    npit = load_net_profit_pit_series()
    growth = _trailing_cagr(npit, n_years=n_years)
    g_aligned = _asof_align_growth(ds, growth)
    out = base.merge(g_aligned[["date", "symbol", "cagr"]], on=["date", "symbol"], how="inner")
    out = out.rename(columns={"cagr": "g_hist"})
    out = out[(out["E0"] > 0) & (out["price"] > 0) & out["g_hist"].notna()].copy()
    _CACHE[key] = out
    return out


# --------------------------------------------------------------------------
# DCF engine
# --------------------------------------------------------------------------
def _dcf_intrinsic(E0: np.ndarray, g: np.ndarray, wacc: float, g_terminal: float,
                    n_years: int = 5) -> np.ndarray:
    """Vectorized 2-stage DCF intrinsic value. E0,g: arrays (N,). wacc,g_terminal: scalars."""
    E0 = np.asarray(E0, dtype=float)
    g = np.asarray(g, dtype=float)
    i = np.arange(1, n_years + 1, dtype=float)
    gf = (1.0 + g)[:, None] ** i[None, :]          # (N, n_years)
    disc = (1.0 + wacc) ** i                        # (n_years,)
    pv_stage1 = (E0[:, None] * gf / disc[None, :]).sum(axis=1)
    E_n = E0 * (1.0 + g) ** n_years
    tv = E_n * (1.0 + g_terminal) / (wacc - g_terminal)
    pv_tv = tv / (1.0 + wacc) ** n_years
    return pv_stage1 + pv_tv


def _solve_implied_growth(E0: np.ndarray, price: np.ndarray, wacc: float, g_terminal: float,
                           n_years: int = 5, lo: float = -0.90, hi: float = 5.0,
                           iters: int = 60) -> np.ndarray:
    E0 = np.asarray(E0, dtype=float)
    price = np.asarray(price, dtype=float)
    valid = (E0 > 0) & (price > 0) & np.isfinite(E0) & np.isfinite(price)
    lo_arr = np.full_like(E0, lo)
    hi_arr = np.full_like(E0, hi)
    for _ in range(iters):
        mid = (lo_arr + hi_arr) / 2.0
        val = _dcf_intrinsic(E0, mid, wacc, g_terminal, n_years=n_years) - price
        hi_arr = np.where(val > 0, mid, hi_arr)
        lo_arr = np.where(val > 0, lo_arr, mid)
    g_implied = (lo_arr + hi_arr) / 2.0
    return np.where(valid, g_implied, np.nan)


# --------------------------------------------------------------------------
# factor builders (panel -> Series indexed (date,symbol))
# --------------------------------------------------------------------------
def build_dcf_value_factor(panel: pd.DataFrame, wacc: float, g_terminal: float,
                            n_years: int = 5) -> pd.Series:
    m = prep_growth_and_base(panel, n_years=n_years).copy()
    g_clipped = np.clip(m["g_hist"].values, G_CLIP[0], G_CLIP[1])
    intrinsic = _dcf_intrinsic(m["E0"].values, g_clipped, wacc, g_terminal, n_years=n_years)
    m["factor"] = intrinsic / m["price"].values
    m = m.replace([np.inf, -np.inf], np.nan).dropna(subset=["factor"])
    return m.set_index(["date", "symbol"])["factor"]


def build_revgap_factor(panel: pd.DataFrame, wacc: float, g_terminal: float,
                         n_years: int = 5) -> pd.Series:
    m = prep_growth_and_base(panel, n_years=n_years).copy()
    g_implied = _solve_implied_growth(m["E0"].values, m["price"].values, wacc, g_terminal,
                                       n_years=n_years)
    m["factor"] = m["g_hist"].values - g_implied  # oriented: higher = cheaper = bullish
    m = m.replace([np.inf, -np.inf], np.nan).dropna(subset=["factor"])
    return m.set_index(["date", "symbol"])["factor"]


# convenience: pre-bind a (wacc, g_terminal) combo into a zero-arg-ish builder_fn
# signature expected by harness.run_experiment (builder_fn(panel_df) -> factor)
def make_dcf_value_builder(wacc: float, g_terminal: float, n_years: int = 5):
    def _b(panel):
        return build_dcf_value_factor(panel, wacc, g_terminal, n_years=n_years)
    return _b


def make_revgap_builder(wacc: float, g_terminal: float, n_years: int = 5):
    def _b(panel):
        return build_revgap_factor(panel, wacc, g_terminal, n_years=n_years)
    return _b
