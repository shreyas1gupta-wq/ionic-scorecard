"""
ALPHA_RANKER WAVE worker: investment/issuance balance-sheet anomaly builders
(IDG-G-03 asset-growth, IDG-G-04 net-share-issuance, IDG-G-05 accruals/Sloan).
Money-first loop, orthogonal to the momentum/value core (balance-sheet-only,
no price input). Owner: this worker session.

Data: ALPHA_RANKER/data/fundamentals/MASTER_fundamentals_pit.parquet (LONG,
one row per nse_symbol x fiscal_year x metric_norm, with a per-(symbol,
fiscal_year) available_date for PIT gating -- same source/pivot convention as
builders_quality.py/_load_fund_wide). PIT method: compute each raw factor at
ANNUAL (symbol, fiscal_year) granularity (YoY diffs use actual consecutive
REPORTED fiscal years, may not be exactly 365d apart), then merge_asof each
panel (date,symbol) row to the latest fiscal_year with available_date <= date
(direction='backward', grouped by symbol) -- no lookahead.

Evaluated against rnd/panel/panel_long.parquet (969 symbols, 2005-04-29 ->
2025-12-05, real fwd_ret_1Y/5Y_resid, not the short 2021-2026 panel) so 5Y has
real (non-100%-NaN) coverage and a pre-2015-vs-post era split is possible per
the firm's DATA-TRUST directive (pre-2015 fundamentals = lower trust, down-
weight not delete).

Disclosed deviations:
1. IDG-G-04 net-share-issuance proxy = YoY %chg in "equity capital" (face-value
   paid-up capital), NOT float/shares-outstanding (source has no shares-count
   series -- confirmed, see PANEL_SCHEMA.md addendum). Checked distribution
   pre-build (/tmp/check_issuance.py, 25234 annual obs, 2356 symbols):
   median YoY chg = 0.0 (most firms flat), but 8.1% of obs have |chg|>30% and
   the right tail is extreme (99th pctile = +700%, max +19,549,900% -- clearly
   bonus-issue/split/QIP events or data artifacts, not organic buyback/dilution
   signal at that magnitude). Per-date cross-sectional winsorization at 1%/99%
   (same convention as builders_growth.py's _zscore_by_date) bounds this before
   ranking, but the construct is still confirmed noisy versus a true
   shares-outstanding based issuance factor -- flag any result as a coarse
   proxy, not the textbook Pontiff-Woodgate construct.
2. IDG-G-03 asset-growth: "total assets" YoY %chg, same PIT join. Sector-
   NOT neutralized here (backlog IDG-G-03 construct does not request it,
   unlike sibling IDG-I-01 which does; IDG-I-01 is the same construct as
   IDG-G-03 per backlog_scout._meta and is treated as covered by this run,
   not separately re-coded).
3. IDG-G-05 accruals: identical construct to the already-built H022
   (builders_quality.py build_accruals_factor / accrual_neg = -(NI-CFO)/assets)
   but re-run here against panel_long (21yr, 1Y+5Y) rather than the short
   panel (H022's card was 1Y-only on 2021-2026 data) specifically to get the
   5Y read and the pre-2015/post-2015 split this task asks for.
4. All three factors: higher factor value = more desirable (long leg), i.e.
   the raw economic quantity is sign-flipped at construction where the
   pre-registered sign is "-", matching the harness's uniform "higher=better"
   IC convention (see harness.verdict()/ builders_quality.py deviation #3).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent            # ALPHA_RANKER/rnd
ALPHA_DIR = RND_DIR.parent               # ALPHA_RANKER
FUND_PATH = ALPHA_DIR / "data" / "fundamentals" / "MASTER_fundamentals_pit.parquet"

_CACHE: dict = {}


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
# 0. load + pivot fundamentals to (symbol, fiscal_year) wide, once
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
    assets = g.get("total assets")
    eqcap = g.get("equity capital")
    ni = g.get("net profit")
    cfo = g.get("cash from operating activity")

    # IDG-G-03: asset-growth, sign-flipped (long LOW growth)
    assets_pct = assets.pct_change().replace([np.inf, -np.inf], np.nan) if assets is not None else pd.Series(np.nan, index=g.index)
    g["asset_growth_neg"] = -assets_pct

    # IDG-G-04: net share issuance proxy (equity capital YoY), sign-flipped (long shrinking/repurchasers)
    eqcap_pct = eqcap.pct_change().replace([np.inf, -np.inf], np.nan) if eqcap is not None else pd.Series(np.nan, index=g.index)
    g["issuance_neg"] = -eqcap_pct

    # IDG-G-05: Sloan accruals, sign-flipped (long LOW/negative accruals = high quality earnings)
    accrual_raw = ((ni - cfo) / assets).replace([np.inf, -np.inf], np.nan) if (ni is not None and cfo is not None and assets is not None) else pd.Series(np.nan, index=g.index)
    g["accrual_neg"] = -accrual_raw

    return g


def _annual_factor_table() -> pd.DataFrame:
    if "annual" in _CACHE:
        return _CACHE["annual"]
    wide = _load_fund_wide()
    out = wide.groupby("symbol", group_keys=False).apply(_annual_group, include_groups=False)
    out = out.assign(symbol=wide["symbol"].values) if "symbol" not in out.columns else out
    keep = ["symbol", "fiscal_year", "available_date", "asset_growth_neg", "issuance_neg", "accrual_neg"]
    out = out[keep].dropna(subset=["available_date"])
    _CACHE["annual"] = out
    return out


# ==========================================================================
# 1. PIT as-of join: annual factor table -> panel (date, symbol) grid, then
#    cross-sectional z per date (winsorized 1%/99%, per builders_growth.py convention)
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


def _build_zscored(panel: pd.DataFrame, value_col: str) -> pd.Series:
    m = _asof_to_panel(panel, value_col)
    m["z"] = _zscore_by_date(m[["date", value_col]], value_col)
    m = m.dropna(subset=["z"])
    return m.set_index(["date", "symbol"])["z"]


# ==========================================================================
# 2. worker-facing builders (panel_df) -> Series[(date,symbol)] = z-scored factor
# ==========================================================================
def build_asset_growth_factor(panel: pd.DataFrame) -> pd.Series:
    """IDG-G-03 (== IDG-I-01): -z(YoY %chg total assets). Long low-growth."""
    return _build_zscored(panel, "asset_growth_neg")


def build_issuance_factor(panel: pd.DataFrame) -> pd.Series:
    """IDG-G-04: -z(YoY %chg equity capital, face-value proxy). Long repurchasers/flat."""
    return _build_zscored(panel, "issuance_neg")


def build_accruals_factor(panel: pd.DataFrame) -> pd.Series:
    """IDG-G-05: -z((NetProfit-CFO)/Assets). Long low/negative accruals."""
    return _build_zscored(panel, "accrual_neg")


BUILDERS = {
    "IDG_G03_assetgrowth": build_asset_growth_factor,
    "IDG_G04_issuance": build_issuance_factor,
    "IDG_G05_accruals": build_accruals_factor,
}
