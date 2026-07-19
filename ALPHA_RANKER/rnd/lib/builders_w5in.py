"""
WAVE-5 "earnings-suppression-then-bounce" + turnaround/cyclical builders
(Sanjay Kulkarni task, 2026-07-17, per Principal request via ALPHA_RANKER).

CORE HYPOTHESIS: raw asset-growth (bs_asset_growth leg, capstone_legs.parquet)
is the CONFIRMED NEGATIVE Cooper-Gulen-Schill anomaly on this panel. The edge
under test here is a CONDITIONAL subset: firms whose earnings are TEMPORARILY
suppressed by productive investment (capex/CWIP-heavy, margin below own
history) AND that show LEADING PIT signs of inflection (revenue re-
acceleration, CWIP converting to gross block, asset turnover starting to
rise), gated/tilted by a balance-sheet quality conditioner. Question: does
this conditional signal beat / flip the sign of raw asset growth?

Data: MASTER_fundamentals_pit.parquet (LONG, one row per nse_symbol x
fiscal_year x metric_norm, PIT available_date). Same pivot/PIT convention as
builders_w2_issuance.py / builders_w5.py:
  1. pivot to (symbol, fiscal_year) WIDE, one available_date per (symbol, FY)
     (the annual-report release date for that FY, screener_live scrape).
  2. compute ALL derived features using ONLY same-or-EARLIER fiscal years
     within a symbol's own sorted series (diff()/shift()/rolling() on an
     ascending-by-fiscal_year frame) -- nothing at fiscal_year > t is ever
     touched when building the row for fiscal_year t. This is the anti-
     lookahead discipline the task calls out explicitly: the suppression
     phase is read off data available AS OF t, never off the future bounce.
  3. merge_asof each panel (date,symbol) row to the latest fiscal_year with
     available_date <= date (direction='backward', grouped by symbol) --
     reuses builders_w2_issuance._asof_to_panel style exactly.
  4. cross-sectional z-score per date (1%/99% winsorize), reuses
     builders_w2_issuance._zscore_by_date.

Metric-name reconciliation (checked pre-build): 'sales' (2277 symbols) is the
dominant revenue metric; 'revenue' (90 symbols) is a rare alias used for the
same underlying figure (corr 0.99997 on the 77 symbol-years where both are
populated) -- coalesced sales.fillna(revenue). Same for 'borrowings' (2345
symbols) vs 'borrowing' (71 symbols, alias) -- coalesced.

capex proxy: NO direct capex/gross-block line exists in this source (checked:
34 distinct metric_norm values, no 'capex' or 'gross block'). Proxy used
(disclosed [INFERENCE]): capex_t = diff(fixed_assets_t) + depreciation_t,
i.e. a net-block roll-forward (fixed assets are NET book value here per
screener convention) -- understates true gross capex whenever an asset is
sold/written off in the same year, but is the best available reconstruction
from this source and is directionally correct for "investment happening".

Sign convention: ALL factors below are built HIGHER = economically GOOD /
MORE-suppressed-pre-inflection (repo convention, harness assumes long-top-
decile is the intended long leg).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
ALPHA_DIR = RND_DIR.parent
FUND_PATH = ALPHA_DIR / "data" / "fundamentals" / "MASTER_fundamentals_pit.parquet"

import builders_w2_issuance as BI  # noqa: E402  (reuse _zscore_by_date, winsorize convention)

_CACHE: dict = {}


# ==========================================================================
# 0. load + pivot fundamentals to (symbol, fiscal_year) wide, once
#    (independent load from builders_w2_issuance's cache -- different module,
#    different process invocation each run; re-pivoting the same source file
#    is cheap at this size: ~1.09M rows -> ~50k symbol-years).
# ==========================================================================
def _load_fund_wide() -> pd.DataFrame:
    if "wide" in _CACHE:
        return _CACHE["wide"]
    df = pd.read_parquet(FUND_PATH)
    df = df.dropna(subset=["nse_symbol"]).rename(columns={"nse_symbol": "symbol"})
    piv = df.pivot_table(index=["symbol", "fiscal_year"], columns="metric_norm",
                          values="value", aggfunc="last")
    avail = df.groupby(["symbol", "fiscal_year"])["available_date"].max()
    wide = piv.join(avail).reset_index().sort_values(["symbol", "fiscal_year"]).reset_index(drop=True)
    _CACHE["wide"] = wide
    return wide


def _annual_group(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("fiscal_year").reset_index(drop=True)

    rev = g.get("sales")
    rev = rev.fillna(g.get("revenue")) if rev is not None else g.get("revenue")
    opm = g.get("opm %")
    fixed_assets = g.get("fixed assets")
    cwip = g.get("cwip")
    total_assets = g.get("total assets")
    borrow = g.get("borrowings")
    borrow = borrow.fillna(g.get("borrowing")) if borrow is not None else g.get("borrowing")
    op_profit = g.get("operating profit")
    net_profit = g.get("net profit")
    depr = g.get("depreciation")

    n = len(g)
    z = pd.Series(np.nan, index=g.index)

    def safe(s):
        return s if s is not None else z.copy()

    rev, opm, fixed_assets, cwip, total_assets, borrow, op_profit, net_profit, depr = (
        safe(rev), safe(opm), safe(fixed_assets), safe(cwip), safe(total_assets),
        safe(borrow), safe(op_profit), safe(net_profit), safe(depr)
    )

    # ---- revenue trajectory (PIT: uses rev[<=t] only via pct_change/shift) ----
    rev_growth = rev.pct_change().replace([np.inf, -np.inf], np.nan)
    rev_accel = rev_growth - rev_growth.shift(1)

    # ---- margin suppression vs OWN trailing history (strictly PRIOR years) ----
    opm_hist_avg = opm.shift(1).rolling(3, min_periods=2).mean()
    opm_gap = opm - opm_hist_avg          # negative = currently below own history

    # ---- investment proxy (capex = d(net fixed assets) + depreciation) ----
    capex_proxy = fixed_assets.diff() + depr
    capex_sales = (capex_proxy / rev).replace([np.inf, -np.inf], np.nan)
    capex_sales_hist_avg = capex_sales.shift(1).rolling(3, min_periods=2).mean()
    capex_sales_excess = capex_sales - capex_sales_hist_avg

    # ---- capacity under construction / coming online ----
    cwip_ratio = (cwip / total_assets).replace([np.inf, -np.inf], np.nan)
    cwip_delta = cwip.diff()
    fa_delta = fixed_assets.diff()
    fa_growing = (fa_delta > 0).astype(float)
    # "conversion" = CWIP shrinking (capacity moving off the books-in-progress
    # line) AT THE SAME TIME fixed assets are growing (capacity coming online)
    # -- deflated by total_assets for cross-sectional comparability.
    cwip_conversion = (-cwip_delta / total_assets) * fa_growing

    # ---- operating leverage starting to show ----
    asset_turnover = (rev / total_assets).replace([np.inf, -np.inf], np.nan)
    asset_turnover_delta = asset_turnover.diff()

    # ---- quality conditioner ----
    leverage = (borrow / total_assets).replace([np.inf, -np.inf], np.nan)
    leverage_delta = leverage.diff()
    opm_level = opm  # current-year OPM level itself (floor/disaster check)

    # ---- turnaround / OPM-trough inflection (secondary hypothesis) ----
    opm_prev = opm.shift(1)
    trough_ref = pd.concat([opm.shift(2), opm.shift(3), opm.shift(4)], axis=1).min(axis=1)
    opm_was_trough = opm_prev <= trough_ref
    opm_improved = opm > opm_prev
    turnaround_opm_flag = (opm_improved & opm_was_trough).fillna(False)
    loss_to_profit_flag = ((net_profit.shift(1) <= 0) & (net_profit > 0)).fillna(False)
    turnaround_flag = turnaround_opm_flag | loss_to_profit_flag
    turnaround_magnitude = (opm - opm_prev)
    turnaround_score_raw = turnaround_magnitude.where(turnaround_flag)

    g["rev_growth"] = rev_growth
    g["rev_accel"] = rev_accel
    g["opm_gap"] = opm_gap
    g["capex_sales_excess"] = capex_sales_excess
    g["cwip_ratio"] = cwip_ratio
    g["cwip_conversion"] = cwip_conversion
    g["asset_turnover_delta"] = asset_turnover_delta
    g["leverage_delta"] = leverage_delta
    g["opm_level"] = opm_level
    g["turnaround_flag"] = turnaround_flag.astype(bool)
    g["turnaround_score_raw"] = turnaround_score_raw
    g["loss_to_profit_flag"] = loss_to_profit_flag.astype(bool)
    return g


def _annual_factor_table() -> pd.DataFrame:
    if "annual" in _CACHE:
        return _CACHE["annual"]
    wide = _load_fund_wide()
    out = wide.groupby("symbol", group_keys=False).apply(_annual_group, include_groups=False)
    out = out.assign(symbol=wide["symbol"].values) if "symbol" not in out.columns else out
    keep = ["symbol", "fiscal_year", "available_date",
            "rev_growth", "rev_accel", "opm_gap", "capex_sales_excess", "cwip_ratio",
            "cwip_conversion", "asset_turnover_delta", "leverage_delta", "opm_level",
            "turnaround_flag", "turnaround_score_raw", "loss_to_profit_flag"]
    out = out[keep].dropna(subset=["available_date"])
    _CACHE["annual"] = out
    return out


# ==========================================================================
# 1. PIT as-of join (identical to builders_w2_issuance._asof_to_panel)
# ==========================================================================
def _asof_to_panel(panel: pd.DataFrame, value_col: str) -> pd.DataFrame:
    annual = _annual_factor_table()
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
    return merged.dropna(subset=[value_col])


def _z_component(panel: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Returns tidy (date,symbol,z) for one raw annual column, PIT-joined then
    cross-sectionally z-scored per date (1/99% winsorize, BI convention)."""
    m = _asof_to_panel(panel, value_col)
    m["z"] = BI._zscore_by_date(m[["date", value_col]], value_col)
    return m[["date", "symbol", "z"]].dropna(subset=["z"])


def _combine_z(panel: pd.DataFrame, cols: list[str], flip: dict[str, bool] | None = None) -> pd.Series:
    """Mean of per-date z-scores across `cols` (each independently PIT-joined
    and z-scored), requiring >=1 present; NaN components skipped per row."""
    flip = flip or {}
    frames = []
    for c in cols:
        zc = _z_component(panel, c)
        if flip.get(c):
            zc["z"] = -zc["z"]
        zc = zc.rename(columns={"z": c})
        frames.append(zc.set_index(["date", "symbol"])[c])
    wide = pd.concat(frames, axis=1)
    combo = wide.mean(axis=1, skipna=True)
    n_present = wide.notna().sum(axis=1)
    combo = combo.where(n_present >= max(1, len(cols) // 2))  # need at least half the legs
    return combo.dropna().rename("factor")


# ==========================================================================
# 2. worker-facing builders (panel_df) -> Series[(date,symbol)] = factor
# ==========================================================================
SUPPRESSION_COLS = ["opm_gap", "capex_sales_excess", "cwip_ratio"]
SUPPRESSION_FLIP = {"opm_gap": True}  # higher score = MORE suppressed => flip opm_gap sign

INFLECTION_COLS = ["rev_accel", "cwip_conversion", "asset_turnover_delta"]

QUALITY_COLS = ["leverage_delta", "rev_growth", "opm_level"]
QUALITY_FLIP = {"leverage_delta": True}  # higher score = LESS leverage buildup


def build_suppression_raw(panel: pd.DataFrame) -> pd.Series:
    """Suppression markers ONLY (no inflection, no quality) -- the 'is this
    just disguised asset-growth-trap distress' control."""
    return _combine_z(panel, SUPPRESSION_COLS, SUPPRESSION_FLIP)


def build_conditional_no_quality(panel: pd.DataFrame) -> pd.Series:
    """Suppression + leading inflection, NO quality tilt -- ablation to isolate
    the quality conditioner's marginal contribution."""
    return _combine_z(panel, SUPPRESSION_COLS + INFLECTION_COLS,
                       {**SUPPRESSION_FLIP})


def build_conditional_full(panel: pd.DataFrame) -> pd.Series:
    """PRIMARY hypothesis: suppression + leading inflection + quality tilt,
    equal-weighted mean of 9 cross-sectional z-components."""
    return _combine_z(panel, SUPPRESSION_COLS + INFLECTION_COLS + QUALITY_COLS,
                       {**SUPPRESSION_FLIP, **QUALITY_FLIP})


def build_turnaround(panel: pd.DataFrame) -> pd.Series:
    """Secondary hypothesis: loss-to-profit / OPM-trough inflection, PIT.
    Non-flagged symbol-years are NaN (excluded), not zero -- this is
    inherently an event-conditional subset, not a universe-wide tilt."""
    return _combine_z(panel, ["turnaround_score_raw"])


def flag_coverage_diagnostics() -> dict:
    a = _annual_factor_table()
    return {
        "n_symbol_years": int(len(a)),
        "n_symbols": int(a["symbol"].nunique()),
        "n_turnaround_flagged": int(a["turnaround_flag"].sum()),
        "n_loss_to_profit_flagged": int(a["loss_to_profit_flag"].sum()),
        "pct_turnaround_flagged": float(a["turnaround_flag"].mean()),
    }
