"""
W4G -- coverage-map GAP-UNTESTED cheap-test batch (Aditya Verma, R&D), 2026-07-17.
Four DISTINCT-MECHANISM candidates from rnd/wave4/coverage_map.json's
GAP-UNTESTED list, each buildable TODAY from data already on disk, never run
before (0 trials, no card). NOT part of the frozen 7-leg composite --
screening-layer-only test per RESEARCH_SOP/RESEARCH_PROTOCOL S3/S4 (one code
path = harness.evaluate()). The frozen model (composite_final.py,
FINAL_MODEL.md, canonical_7leg_scores.parquet) is READ, never edited.

1. H047 Hurst / trend-persistence exponent (coverage_map row: "Hurst / trend-
   persistence exponent (H047)", category other-families).
   Method: generalized Hurst exponent (Barabasi-Vicsek q=1 GHE, NOT classical
   rescaled-range R/S -- a documented, cheaper, equally-standard estimator):
   for lags tau in {5,10,21,42,63,126,252} trading days, compute the trailing-
   252d rolling mean of |log P(t) - log P(t-tau)|, then OLS-regress
   log(rolling_mean) on log(tau) across the 7 lag points; the slope is H.
   H>0.5 => trending/persistent, H<0.5 => mean-reverting. [INFERENCE]:
   methodology substitution, disclosed, standard in the literature (Di Matteo
   2007 surveys GHE vs R/S; both estimate the same exponent).
2. Time-series (absolute) momentum -- own-asset trailing 12-1 return, RAW
   (not beta/market-residualized), evaluated on the RAW return_basis. This
   isolates exactly what H003/mom_resid_plain deliberately strips out (the
   market-beta component of trailing momentum) -- the "distinct mechanism"
   question is whether that stripped component itself carries independent
   signal, not whether trailing-return construction differs (it is the same
   window/skip convention as build_mom_resid_12_1, minus the residualization
   step, precisely so the two are comparable apples-to-apples).
3. H038 Reinvestment runway -- (ROIC_proxy - WACC_assumed) x reinvestment_rate,
   5Y horizon. Built from data/fundamentals/MASTER_fundamentals_pit.parquet
   (long-format PIT, no direct ROIC/gross-margin/WACC columns exist --
   documented substitutions below).
4. Moat proxy -- 5yr operating-margin (NOT gross-margin, see below) level x
   stability, Dorsey-style durability, 5Y horizon.

DISCLOSED SUBSTITUTIONS (data reality, not fabrication):
- No "gross margin"/"COGS" metric exists in MASTER_fundamentals_pit
  (metric_norm has only 'opm %'/'operating profit'/'sales'/'revenue' on the
  P&L side -- verified, 34 distinct metric_norm values, none named
  gross/COGS). Moat proxy uses OPERATING margin (opm) as the closest
  available substitute for Dorsey "durability", clearly re-labeled, not
  silently presented as gross margin.
- The provided 'opm %' column itself is UNRELIABLE at the tails (verified:
  range -606900 to +18892, driven by near-zero 'sales' denominators blowing
  up a pre-computed ratio). Re-derived locally as operating_profit/sales with
  a sales floor guard instead of trusting the stored percent column.
- No ROIC, no WACC series exist. ROIC_proxy = NOPAT / invested_capital where
  NOPAT = operating_profit * (1 - tax_rate) [tax_rate = clip(tax%/100, 0, 0.6)]
  and invested_capital = equity_capital + reserves + preference_capital +
  borrowings (book capital-employed proxy -- no current-liabilities split
  exists to net out non-interest-bearing liabilities properly, so this is a
  capital-employed approximation, not a textbook NOPAT/(net debt+equity)
  computation). WACC_assumed = 0.12 flat (India large/mid-cap equity WACC
  ballpark) -- ONE fixed assumption, not fitted/tuned, [INFERENCE]/[ASSUMPTION]
  tagged; because it is a CONSTANT (not cross-sectionally varying), it does
  NOT by itself change the cross-sectional rank of ROIC, but it DOES change
  the ROIC*reinvestment INTERACTION (penalizes high reinvestment when ROIC is
  only marginally above the assumed hurdle) -- which is the whole point of
  testing "spread x redeployment" instead of plain "ROIC x reinvestment".
- reinvestment_rate = 1 - clip(dividend_payout%/100, 0, 1) (retention-ratio
  sustainable-growth proxy, Damodaran-style simplification -- no capex/
  depreciation/working-capital series exist to build the textbook
  (capex-depreciation+dWC)/NOPAT reinvestment rate).
- All ratio denominators are floored (sales, invested_capital) and all raw
  percent inputs are clipped to sane bounds BEFORE ratio construction (not
  merely winsorized after) to stop a handful of near-zero-denominator data
  errors from flipping the SIGN of a derived ratio, which post-hoc
  winsorization on the ratio's output would not fix. Bounds are documented
  inline at point of use.

Reuses rnd/run_long_confirm.py's load_all()/build_mom_resid_12_1() pattern for
price-cube access (same source as the frozen model's own legs) and
rnd/lib/builders_w4t_sanjay.py's PIT-fundamentals wide-pivot + merge_asof
pattern (same source/convention as other W4-wave fundamentals builders).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent            # ALPHA_RANKER/rnd
ALPHA_DIR = RND_DIR.parent               # ALPHA_RANKER

FUND_PATH = ALPHA_DIR / "data" / "fundamentals" / "MASTER_fundamentals_pit.parquet"

HURST_TAUS = (5, 10, 21, 42, 63, 126, 252)
HURST_WINDOW = 252

WACC_ASSUMED = 0.12          # [INFERENCE]/[ASSUMPTION] flat India equity WACC, not fitted
TAX_RATE_CLIP = (0.0, 0.60)
PAYOUT_CLIP = (0.0, 1.0)     # dividend payout ratio in [0,1] before retention_rate = 1-payout
MIN_SALES_CR = 1.0           # floor (Rs cr) before dividing into sales for margin/EY-style ratios
MIN_INVESTED_CAPITAL_CR = 5.0  # floor (Rs cr) before dividing into invested capital for ROIC

_CACHE: dict = {}


# ==========================================================================
# 1. Hurst / generalized-Hurst-exponent trend persistence (H047)
# ==========================================================================
def build_hurst_factor(close: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.Series:
    """Generalized Hurst exponent (q=1), rolling HURST_WINDOW-day estimate at
    each rebalance date, via OLS slope of log(rolling-mean-abs-lag-return) on
    log(lag) across HURST_TAUS. Requires ALL taus present (no partial-tau
    regression) -- NaN propagates naturally through plain (non-nan) numpy
    arithmetic wherever any one tau is missing, so a date/symbol is only
    scored when the full multi-scale estimate is genuinely available."""
    logpx = np.log(close.where(close > 0))
    roll_means = []
    for tau in HURST_TAUS:
        diff = (logpx - logpx.shift(tau)).abs()
        rm = diff.rolling(HURST_WINDOW, min_periods=HURST_WINDOW).mean()
        roll_means.append(rm)

    idx = close.index
    valid_dates = [d for d in dates if d in idx]
    x = np.log(np.array(HURST_TAUS, dtype=float))
    xm = x - x.mean()
    sxx = float(np.sum(xm ** 2))

    rows = []
    for d in valid_dates:
        # stack: (n_taus, n_symbols) log of that date's rolling mean per tau
        y_list = []
        ok = True
        for rm in roll_means:
            if d not in rm.index:
                ok = False
                break
            v = rm.loc[d].values.astype(float)
            with np.errstate(divide="ignore", invalid="ignore"):
                y_list.append(np.log(v))
        if not ok:
            continue
        Y = np.vstack(y_list)  # (n_taus, n_symbols)
        ymean = Y.mean(axis=0)          # NaN propagates if any tau missing for that symbol
        num = np.sum(xm[:, None] * (Y - ymean[None, :]), axis=0)
        H = num / sxx
        syms = close.columns
        for sym, h in zip(syms, H):
            if np.isfinite(h):
                rows.append((d, sym, float(h)))
    out = pd.DataFrame(rows, columns=["date", "symbol", "factor"])
    return out.set_index(["date", "symbol"])["factor"]


# ==========================================================================
# 2. Time-series (absolute) momentum -- RAW trailing 12-1, no residualization
# ==========================================================================
def build_ts_abs_mom_factor(close: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.Series:
    """Same window/skip convention as run_long_confirm.build_mom_resid_12_1
    (252d trailing window, most-recent 21d skipped) but on RAW daily returns
    -- no beta/market residualization. This is the classic own-asset time-
    series-momentum signal (Moskowitz-Ooi-Pedersen 2012 sign/magnitude), NOT
    cross-sectionally neutralized -- the deliberate point of comparison
    against H003/mom_resid_plain."""
    daily_ret = close.pct_change()
    idx = daily_ret.index
    rows = []
    for d in dates:
        if d not in idx:
            continue
        loc = idx.get_loc(d)
        if loc < 273:
            continue
        window = daily_ret.iloc[loc - 251: loc - 20]
        cov_ok = window.notna().mean() >= 0.80
        cum = (1.0 + window.fillna(0.0)).prod() - 1.0
        cum = cum.where(cov_ok)
        for sym, val in cum.dropna().items():
            rows.append((d, sym, val))
    out = pd.DataFrame(rows, columns=["date", "symbol", "factor"])
    return out.set_index(["date", "symbol"])["factor"]


# ==========================================================================
# shared fundamentals loader (same convention as builders_w4t_sanjay.py)
# ==========================================================================
def load_fundamentals() -> pd.DataFrame:
    if "fund_w4g" not in _CACHE:
        df = pd.read_parquet(FUND_PATH)
        df = df[df["nse_symbol"].notna()].copy()
        df["available_date"] = pd.to_datetime(df["available_date"])
        _CACHE["fund_w4g"] = df
    return _CACHE["fund_w4g"]


def _fund_wide() -> pd.DataFrame:
    if "fund_wide_w4g" in _CACHE:
        return _CACHE["fund_wide_w4g"]
    df = load_fundamentals().rename(columns={"nse_symbol": "symbol"})
    piv = df.pivot_table(index=["symbol", "fiscal_year"], columns="metric_norm",
                          values="value", aggfunc="last")
    avail = df.groupby(["symbol", "fiscal_year"])["available_date"].max()
    wide = piv.join(avail).reset_index().sort_values(["symbol", "fiscal_year"]).reset_index(drop=True)
    _CACHE["fund_wide_w4g"] = wide
    return wide


def _asof_to_panel(panel_ds: pd.DataFrame, annual: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """merge_asof (backward, by symbol): only fiscal years with available_date
    <= panel date are visible at that date -- no lookahead."""
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


# ==========================================================================
# 3. H038 Reinvestment runway: (ROIC_proxy - WACC) x reinvestment_rate
# ==========================================================================
def _reinvestment_annual_table() -> pd.DataFrame:
    if "reinv_annual_w4g" in _CACHE:
        return _CACHE["reinv_annual_w4g"]
    wide = _fund_wide()

    def _grp(g: pd.DataFrame) -> pd.DataFrame:
        g = g.sort_values("fiscal_year").reset_index(drop=True)
        opft = g.get("operating profit")
        sales = g.get("sales")
        taxpct = g.get("tax %")
        eqcap = g.get("equity capital")
        reserves = g.get("reserves")
        prefcap = g.get("preference capital")
        borrow = g.get("borrowings")
        payout = g.get("dividend payout %")

        if taxpct is not None and opft is not None:
            tax_rate = (taxpct / 100.0).clip(*TAX_RATE_CLIP)
            nopat = opft * (1.0 - tax_rate)
        else:
            nopat = None

        if eqcap is not None and reserves is not None and borrow is not None:
            ic = eqcap.fillna(0) + reserves.fillna(0) + (prefcap.fillna(0) if prefcap is not None else 0) + borrow.fillna(0)
            ic = ic.where(ic >= MIN_INVESTED_CAPITAL_CR)
        else:
            ic = None

        if nopat is not None and ic is not None:
            g["roic_proxy"] = (nopat / ic).replace([np.inf, -np.inf], np.nan)
        else:
            g["roic_proxy"] = np.nan
        g["reinvestment_rate"] = (1.0 - (payout / 100.0).clip(*PAYOUT_CLIP)) if payout is not None else np.nan
        return g

    out = wide.groupby("symbol", group_keys=False).apply(_grp, include_groups=False)
    out = out.assign(symbol=wide["symbol"].values) if "symbol" not in out.columns else out
    keep = ["symbol", "fiscal_year", "available_date", "roic_proxy", "reinvestment_rate"]
    out = out[keep].dropna(subset=["available_date"])
    _CACHE["reinv_annual_w4g"] = out
    return out


def build_reinvestment_runway_factor(panel_ds: pd.DataFrame) -> pd.Series:
    """panel_ds must have columns date, symbol (any panel row grain)."""
    ds = panel_ds[["date", "symbol"]].drop_duplicates()
    annual = _reinvestment_annual_table()

    roic = _asof_to_panel(ds, annual, "roic_proxy")[["date", "symbol", "roic_proxy"]]
    reinv = _asof_to_panel(ds, annual, "reinvestment_rate")[["date", "symbol", "reinvestment_rate"]]
    m = roic.merge(reinv, on=["date", "symbol"], how="inner").dropna()
    m["factor"] = (m["roic_proxy"] - WACC_ASSUMED) * m["reinvestment_rate"]
    return m.set_index(["date", "symbol"])["factor"].replace([np.inf, -np.inf], np.nan).dropna()


# ==========================================================================
# 4. Moat proxy: 5yr operating-margin level x stability (Dorsey durability)
# ==========================================================================
def _moat_annual_table() -> pd.DataFrame:
    if "moat_annual_w4g" in _CACHE:
        return _CACHE["moat_annual_w4g"]
    wide = _fund_wide()

    def _grp(g: pd.DataFrame) -> pd.DataFrame:
        g = g.sort_values("fiscal_year").reset_index(drop=True)
        opft = g.get("operating profit")
        sales = g.get("sales")
        if opft is not None and sales is not None:
            sales_floored = sales.where(sales >= MIN_SALES_CR)
            opm_recalc = (opft / sales_floored).clip(-1.0, 1.0)  # re-derived, NOT the raw 'opm %' col
        else:
            opm_recalc = pd.Series(np.nan, index=g.index)
        g["opm_recalc"] = opm_recalc
        return g

    out = wide.groupby("symbol", group_keys=False).apply(_grp, include_groups=False)
    out = out.assign(symbol=wide["symbol"].values) if "symbol" not in out.columns else out
    out = out[["symbol", "fiscal_year", "available_date", "opm_recalc"]].dropna(subset=["available_date"])
    _CACHE["moat_annual_w4g"] = out
    return out


def build_moat_margin_stability_factor(panel_ds: pd.DataFrame, n_years: int = 5, min_years: int = 3) -> pd.Series:
    """PIT trailing-up-to-n_years operating-margin consistency score:
    mean(opm)/std(opm) over the last n_years fiscal-year prints available
    STRICTLY as of each panel date (own available_date <= panel date per
    print, not a single as-of anchor for the whole window) -- higher = more
    durable (Dorsey-style: stable AND decent margin in one score). Requires
    >= min_years distinct annual prints; else NaN (thin coverage dropped, not
    fabricated)."""
    ds = panel_ds[["date", "symbol"]].drop_duplicates().copy()
    ds["symbol"] = ds["symbol"].astype(str)
    ds["date"] = pd.to_datetime(ds["date"]).astype("datetime64[ns]")

    annual = _moat_annual_table()[["symbol", "available_date", "opm_recalc"]].dropna()
    annual["symbol"] = annual["symbol"].astype(str)
    annual["available_date"] = pd.to_datetime(annual["available_date"]).astype("datetime64[ns]")

    rows = []
    for sym, g in annual.groupby("symbol"):
        g = g.sort_values("available_date").reset_index(drop=True)
        d_sym = ds.loc[ds["symbol"] == sym, "date"]
        if d_sym.empty:
            continue
        avail = g["available_date"].values
        opm = g["opm_recalc"].values
        for d in d_sym:
            # how many prints already public as of d?
            n_pub = int(np.searchsorted(avail, np.datetime64(d), side="right"))
            if n_pub < min_years:
                continue
            window = opm[max(0, n_pub - n_years):n_pub]
            if len(window) < min_years:
                continue
            mu, sd = float(np.mean(window)), float(np.std(window, ddof=1)) if len(window) > 1 else np.nan
            if sd is None or not np.isfinite(sd) or sd <= 1e-6:
                continue
            rows.append((d, sym, mu / sd))
    out = pd.DataFrame(rows, columns=["date", "symbol", "factor"])
    return out.set_index(["date", "symbol"])["factor"].replace([np.inf, -np.inf], np.nan).dropna()
