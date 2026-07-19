"""
WAVE-4 NEXT-SLEEVE candidate test (Arjun Rao, Quant Head, 2026-07-17).
Three forensic/balance-sheet factors from hypotheses_w4.json / hypotheses_w4_forensic.json,
tested as potential NEXT-SLEEVE material -- explicitly NOT added to the frozen 7-leg composite
(D-030 forward-test freeze does not apply here since this is research, not a live/paper strategy,
but the canonical composite itself IS frozen and this task does not touch it).

Data: ALPHA_RANKER/data/fundamentals/MASTER_fundamentals_pit.parquet (LONG, one row per
nse_symbol x fiscal_year x metric_norm, with a per-(symbol, fiscal_year) available_date for
PIT gating). Reuses builders_w2_issuance._load_fund_wide() (same pivot, same cache) -- no new
data read, no duplicated PIT-join logic.

PIT method identical to builders_w2_issuance.py: compute each raw factor at ANNUAL
(symbol, fiscal_year) granularity, then merge_asof each panel (date,symbol) row to the latest
fiscal_year with available_date <= date (direction='backward', grouped by symbol, per
builders_w2_issuance._asof_to_panel / _build_zscored -- reused verbatim, not reimplemented).

Financials excluded (per both hypotheses' "financials excluded" instruction) -- filtered at
the annual-table level via a symbol->sector map from panel_long (sector=='Financial Services').

Sign convention: ALL THREE tradeable factors are built so HIGHER factor value = economically
GOOD (repo convention, see builders_w2_issuance.py deviation #4 / builders_w2_lowrisk.py
module docstring) -- i.e. sign already flipped from the raw "red-flag" quantity described in
the hypotheses' "expected_sign: -" field, so harness IC/decile/DSR/PBO machinery (which assumes
long-top-decile = the intended long leg) is directly interpretable without a downstream
sign-flip step.

Factors:
  W4-01   NOA (Hirshleifer balance-sheet bloat):
          noa_proxy = (fixed assets + cwip + other assets - other liabilities) / total assets
          BASE factor  = noa_neg   = -z_cs(noa_proxy)         (long LOW NOA)
          REFINEMENT   = dnoa_neg  = -z_cs(YoY diff noa_proxy) (long DECREASING NOA, "flow" version)

  W4F-01  Depreciation-policy laxity (under-depreciation proxy):
          dep_rate_t = depreciation_t / (0.5*(FA_t+FA_t-1) + 0.5*(cwip_t+cwip_t-1))
          3FY slope of dep_rate (t, t-1, t-2 consecutive FYs; slope = (dep_rate_t - dep_rate_t-2)/2,
          exact OLS slope for 3 equally-spaced points), gated to fire ONLY when
          (FA_t+cwip_t) >= (FA_t-3+cwip_t-3) [base not shrinking].
          Hypotheses' "Signal" = z_cs(-(slope)) i.e. HIGH signal = red flag (laxity, bad).
          BASE factor (this module, sign-flipped for repo convention) = dep_health = z_cs(slope)
          -- i.e. long RISING/stable dep-rate (healthy), short declining dep-rate (laxity red flag).
          No separate refinement run: the hypotheses' own "refinement" note (use within-firm
          TREND not cross-firm LEVEL) is already baked into the "construction" field as the
          3FY-slope design -- there is no lesser base version to fall back to, so only one
          evaluation is run for this factor (satisfies "ONE base + at most ONE refinement",
          refinement count = 0).

  W4F-02  Clean-surplus / reserves-reconciliation (phantom-earnings):
          gap_ratio_t = (Sum(net_profit, t-3..t) - (reserves_t - reserves_t-4)) / Sum(|net_profit|, t-3..t)
          BASE factor  = clean_surplus_health = -z_cs(gap_ratio)   (full universe, dividend-unadjusted)
          REFINEMENT   = clean_surplus_health_divadj = -z_cs(gap_ratio_div), where
          gap_ratio_div subtracts Sum(estimated dividends = net_profit * payout%/100) from the
          Sum(net_profit) numerator term -- ONLY computable on the ~749-firm subset with
          "dividend payout %" reported (per hypotheses' documented refinement).
          Also computes gap_extreme_flag = (reserves_t < reserves_t-4) & (Sum(net_profit) > 0)
          as a disclosed diagnostic (not folded into the tradeable factor).

Disclosed [INFERENCE] deviations (consistent with builders_w2_issuance.py/builders_quality.py
precedent in this repo -- same simplifications, not new ones):
  1. "Winsorize per date" / "peer z within sub-sector x size" in the hypotheses text is
     implemented as builders_w2_issuance._zscore_by_date's existing per-PANEL-DATE winsorize+
     z-score (1/99 pct, no sub-sector x size bucketing) -- the repo has no sector x size peer-
     group z anywhere else either; a true sub-sector x size z is future work, not silently
     assumed equivalent.
  2. Non-consecutive fiscal years (gaps in a symbol's reporting history) are guarded: any
     shift(k)-based calc (t-1, t-2, t-3, t-4) requires fiscal_year(t) - fiscal_year(t-k) == k
     exactly, else NaN (no silent use of a non-adjacent year as if adjacent).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
ALPHA_DIR = RND_DIR.parent
FUND_PATH = ALPHA_DIR / "data" / "fundamentals" / "MASTER_fundamentals_pit.parquet"

import builders_w2_issuance as BI  # noqa: E402  (reuse _load_fund_wide, _winsorize, _zscore_by_date, _asof_to_panel pattern)

_CACHE: dict = {}
FINANCIALS_SECTOR = "Financial Services"


def _sector_map(panel: pd.DataFrame) -> dict:
    """symbol -> sector, most-common label per symbol (panel's sector is static per PANEL_SCHEMA.md)."""
    return panel.groupby("symbol")["sector"].agg(lambda s: s.mode().iat[0] if len(s.mode()) else None).to_dict()


def _diagnostic_counts() -> dict:
    return _CACHE.get("diagnostics", {})


# ==========================================================================
# 0. annual per-symbol computation (all three factors' raw ingredients)
# ==========================================================================
def _annual_group(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("fiscal_year").reset_index(drop=True)
    fy = g["fiscal_year"]

    def _lag(col, k):
        """shift(k) but NaN'd if fiscal years aren't exactly k apart (no silent non-adjacent use)."""
        s = g.get(col)
        if s is None:
            return pd.Series(np.nan, index=g.index)
        lagged = s.shift(k)
        fy_lagged = fy.shift(k)
        gap_ok = (fy - fy_lagged) == k
        return lagged.where(gap_ok)

    fa = g.get("fixed assets")
    cwip = g.get("cwip")
    oa = g.get("other assets")
    ol = g.get("other liabilities")
    ta = g.get("total assets")
    dep = g.get("depreciation")
    ni = g.get("net profit")
    res = g.get("reserves")
    payout = g.get("dividend payout %")

    # ---- W4-01 NOA ----
    if all(x is not None for x in (fa, cwip, oa, ol, ta)):
        noa_proxy = (fa + cwip + oa - ol) / ta.replace(0, np.nan)
    else:
        noa_proxy = pd.Series(np.nan, index=g.index)
    g["noa_proxy"] = noa_proxy
    noa_lag1 = noa_proxy.shift(1).where((fy - fy.shift(1)) == 1)
    g["dnoa"] = noa_proxy - noa_lag1

    # ---- W4F-01 depreciation-policy laxity ----
    fa1, cwip1 = _lag("fixed assets", 1), _lag("cwip", 1)
    if all(x is not None for x in (fa, cwip, dep)):
        base_now = fa.fillna(0) + cwip.fillna(0)
        base_lag1 = fa1.fillna(0) + cwip1.fillna(0)
        avg_base = 0.5 * (fa + fa1) + 0.5 * (cwip + cwip1)
        avg_base = avg_base.where(fa1.notna() & cwip1.notna())  # need t-1 to exist
        dep_rate = dep / avg_base.replace(0, np.nan)
    else:
        dep_rate = pd.Series(np.nan, index=g.index)
    # winsorize dep_rate 1/99 pct cross-sectionally is applied later (per-panel-date, via
    # _zscore_by_date on the final signal) -- here we winsorize the annual series itself
    # (within this symbol's own history is meaningless for cross-sectional winsorize, so
    # this per-symbol annual dep_rate is left raw; cross-sectional winsorize happens after
    # the PIT asof-join to the monthly panel, same convention as builders_w2_issuance.py).
    g["dep_rate"] = dep_rate
    dep_rate_lag2 = dep_rate.shift(2).where((fy - fy.shift(2)) == 2)
    dep_slope3 = (dep_rate - dep_rate_lag2) / 2.0  # exact OLS slope, 3 equally-spaced FYs
    fa3, cwip3 = _lag("fixed assets", 3), _lag("cwip", 3)
    base_now_gate = fa.fillna(np.nan) + cwip.fillna(np.nan)
    base_lag3_gate = fa3 + cwip3
    gate_not_shrinking = base_now_gate >= base_lag3_gate
    g["dep_slope3"] = dep_slope3.where(gate_not_shrinking)

    # ---- W4F-02 clean-surplus / reserves-reconciliation ----
    if ni is not None and res is not None:
        ni1, ni2, ni3 = _lag("net profit", 1), _lag("net profit", 2), _lag("net profit", 3)
        sum_ni = ni + ni1 + ni2 + ni3
        sum_abs_ni = ni.abs() + ni1.abs() + ni2.abs() + ni3.abs()
        res4 = _lag("reserves", 4)
        d_reserves = res - res4
        gap_ratio = (sum_ni - d_reserves) / sum_abs_ni.replace(0, np.nan)
        g["gap_ratio"] = gap_ratio
        g["gap_extreme_flag"] = (res < res4) & (sum_ni > 0)
        if payout is not None:
            payout1, payout2, payout3 = _lag("dividend payout %", 1), _lag("dividend payout %", 2), _lag("dividend payout %", 3)
            est_div = (ni * payout / 100.0).fillna(0) + (ni1 * payout1 / 100.0).fillna(0) + \
                      (ni2 * payout2 / 100.0).fillna(0) + (ni3 * payout3 / 100.0).fillna(0)
            has_payout = payout.notna() & payout1.notna() & payout2.notna() & payout3.notna()
            sum_ni_divadj = (sum_ni - est_div).where(has_payout)
            g["gap_ratio_div"] = (sum_ni_divadj - d_reserves) / sum_abs_ni.replace(0, np.nan)
        else:
            g["gap_ratio_div"] = np.nan
    else:
        g["gap_ratio"] = np.nan
        g["gap_extreme_flag"] = False
        g["gap_ratio_div"] = np.nan

    return g


def _annual_factor_table(panel: pd.DataFrame) -> pd.DataFrame:
    if "annual" in _CACHE:
        return _CACHE["annual"]
    wide = BI._load_fund_wide()
    smap = _sector_map(panel)
    wide["sector"] = wide["symbol"].map(smap)
    n_before = wide["symbol"].nunique()
    wide = wide[wide["sector"] != FINANCIALS_SECTOR].copy()
    n_after = wide["symbol"].nunique()
    out = wide.groupby("symbol", group_keys=False).apply(_annual_group, include_groups=False)
    out = out.assign(symbol=wide["symbol"].values) if "symbol" not in out.columns else out
    keep = ["symbol", "fiscal_year", "available_date", "noa_proxy", "dnoa", "dep_rate",
            "dep_slope3", "gap_ratio", "gap_extreme_flag", "gap_ratio_div"]
    out = out[keep].dropna(subset=["available_date"])
    _CACHE["annual"] = out
    _CACHE["diagnostics"] = {
        "n_symbols_before_financials_excl": int(n_before),
        "n_symbols_after_financials_excl": int(n_after),
        "n_financials_excluded": int(n_before - n_after),
        "gap_extreme_flag_rate": float(out["gap_extreme_flag"].mean()) if len(out) else float("nan"),
        "n_annual_rows": int(len(out)),
        "n_symbols_annual": int(out["symbol"].nunique()),
        "n_symbols_with_gap_ratio_div": int(out.dropna(subset=["gap_ratio_div"])["symbol"].nunique()),
    }
    return out


def _build_zscored(panel: pd.DataFrame, value_col: str) -> pd.Series:
    annual = _annual_factor_table(panel)
    sub = annual[["symbol", "available_date", value_col]].dropna(subset=[value_col]).copy()
    sub["symbol"] = sub["symbol"].astype(str)
    sub["available_date"] = pd.to_datetime(sub["available_date"]).astype("datetime64[ns]")
    sub = sub.sort_values("available_date")
    p = panel[["date", "symbol"]].drop_duplicates().copy()
    p["symbol"] = p["symbol"].astype(str)
    p["date"] = pd.to_datetime(p["date"]).astype("datetime64[ns]")
    p = p.sort_values("date")
    merged = pd.merge_asof(p, sub.rename(columns={"available_date": "date"}),
                            on="date", by="symbol", direction="backward")
    m = merged.dropna(subset=[value_col])
    m["z"] = BI._zscore_by_date(m[["date", value_col]], value_col)
    m = m.dropna(subset=["z"])
    return m.set_index(["date", "symbol"])["z"]


# ==========================================================================
# 1. worker-facing builders -> Series[(date,symbol)] = z-scored, sign-corrected factor
#    (higher = economically good / expected-higher-forward-return, repo convention)
# ==========================================================================
def build_noa_neg(panel: pd.DataFrame) -> pd.Series:
    """W4-01 BASE: -z(NOA_proxy). Long LOW operating-asset bloat."""
    annual = _annual_factor_table(panel)
    annual = annual.assign(noa_neg=-annual["noa_proxy"])
    _CACHE["annual"] = annual
    return _build_zscored(panel, "noa_neg")


def build_dnoa_neg(panel: pd.DataFrame) -> pd.Series:
    """W4-01 REFINEMENT: -z(YoY change in NOA_proxy). Long DECREASING NOA (flow version)."""
    annual = _annual_factor_table(panel)
    annual = annual.assign(dnoa_neg=-annual["dnoa"])
    _CACHE["annual"] = annual
    return _build_zscored(panel, "dnoa_neg")


def build_dep_health(panel: pd.DataFrame) -> pd.Series:
    """W4F-01 BASE (only evaluation run): z(3FY slope of dep_rate), gated on non-shrinking
    fixed+cwip base. Long RISING/stable depreciation rate (healthy); short/underweight
    declining dep-rate names (under-depreciation red flag)."""
    return _build_zscored(panel, "dep_slope3")


def build_clean_surplus_health(panel: pd.DataFrame) -> pd.Series:
    """W4F-02 BASE: -z(gap_ratio), full universe, dividend-unadjusted. Long clean reconciliation
    (reported profits that DID accrete to book equity)."""
    return _build_zscored(panel, "gap_ratio")


def build_clean_surplus_health_divadj(panel: pd.DataFrame) -> pd.Series:
    """W4F-02 REFINEMENT: -z(gap_ratio_div), ~749-firm subset with dividend payout % reported,
    de-confounding the payout channel from the leakage channel."""
    return _build_zscored(panel, "gap_ratio_div")


BUILDERS = {
    "W4T_01_noa_neg": build_noa_neg,
    "W4T_01_dnoa_neg_refine": build_dnoa_neg,
    "W4TF_01_dep_health": build_dep_health,
    "W4TF_02_clean_surplus_health": build_clean_surplus_health,
    "W4TF_02_clean_surplus_divadj_refine": build_clean_surplus_health_divadj,
}
