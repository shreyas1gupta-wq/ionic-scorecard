"""
ALPHA_RANKER research loop — Quality factor builders (worker assignment: H019-H023, H045).
Owner: this worker session. Feeds rnd/lib/harness.py's evaluate()/run_experiment().

Source: ALPHA_RANKER/data/fundamentals/MASTER_fundamentals_pit.parquet (LONG format,
one row per key_symbol x fiscal_year x metric_norm, with a per-(symbol,fiscal_year)
`available_date` for PIT gating). Only 34 metric_norm fields exist (screener.in-style
condensed annual statements) -- there is NO current-assets/current-liabilities split, NO
COGS breakout, NO shares-outstanding series. Every factor below is built ONLY from what
is actually present; anything not derivable is left NaN (never fabricated), per
RESEARCH_PROTOCOL.md S0.1 and the firm's no-fabrication rule.

PIT method (all builders): compute each RAW factor at ANNUAL (symbol, fiscal_year)
granularity first (so trailing-window stats use actual consecutive reported fiscal
years, not calendar-interpolated ones -- same convention as
src/factors/factors_fundamental.py's trend_slope/stability), then merge_asof each
panel (date, symbol) row to the latest fiscal_year whose `available_date <= date`
(direction='backward', grouped by symbol) -- no lookahead. Banks/NBFCs lack
"operating profit"/"sales"/"opm %" rows (they report "revenue"/"financing profit"/
"financing margin %" instead) -> ROIC, gross-profitability, cash-conversion and any
factor needing "operating profit" are correctly NaN for financials, not fabricated
from the incompatible bank line items.

Disclosed deviations (read before citing any card):
1. **H021 gross profitability**: Novy-Marx's numerator is Revenue-COGS. This dataset has
   no COGS breakout, only "expenses" (ALL opex). We proxy gross profit with
   "operating profit" (= sales - expenses = pre-D&A, pre-interest operating earnings,
   verified algebraically equal to PBT+interest+depreciation-other_income on sample
   rows) -- this UNDERSTATES true gross profit (expenses includes SG&A/employee cost
   beyond COGS) and sits closer to an EBITDA margin than a literal gross margin. Cross-
   sectional ranking is still economically meaningful; the absolute level is not the
   textbook GP/A.
2. **H020 Piotroski F-score**: of the classic 9 signals, ΔCurrent-ratio (#6, needs
   current-asset/current-liability split -- absent from this source) cannot be built.
   F-score here is an 8-signal proxy (raw count 0-8, `n_components` reports how many of
   the 8 were computable per row so a thin count is visible, not hidden). The
   no-dilution signal (#7) is proxied by "equity capital did not increase YoY" (face-
   value assumption; a stock split would falsely fail this signal -- not corrected for,
   disclosed).
3. **H022 accruals**: pre-registered sign is NEGATIVE (high accrual = bad). The factor
   returned is `-(NI-CFO)/assets` (sign-flipped at construction) so a positive IC tests
   the hypothesis directly, per the harness's uniform "higher factor = better" IC
   convention (see harness.verdict(): ic_ir uses signed IC, not |IC|).
4. **H023 earnings stability + OPM slope**: backlog.json pre-registers this at 5Y ONLY.
   `fwd_ret_5Y_*` is 100% NaN in this panel build (confirmed in PANEL_SCHEMA.md: master
   calendar 26 trading days short of the 1260-day 5Y horizon). Per this task's explicit
   dispatch instruction ("Horizons 1M & 1Y; defer 5Y aspects"), this factor is instead
   tested against 1Y forward returns as a disclosed OUT-OF-REGISTRATION substitute
   horizon (not a silent redefinition) -- flag any PROMOTE verdict here for re-
   registration against 5Y once panel_long lands.
5. **ROIC invested capital** = equity_capital + reserves + (borrowings|borrowing),
   averaged over current + prior fiscal year where both exist (else current only) --
   no separate current-liabilities split means this is a financing-side proxy for
   invested capital, not asset-side (fixed assets + net working capital); documented in
   src/factors/factors_fundamental.py as the same convention ("cap_employed").
6. **Tax-rate guard**: `tax %` has extreme outliers (observed range -57136% to +86718%,
   an artifact of PBT near zero). NOPAT uses tax_rate only when `0 <= tax% <= 60`; else
   NaN (not clipped/imputed -- a guard against fabricated-looking NOPAT from garbage
   denominators).
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
    # conservative PIT date: latest available_date across statements for that FY
    avail = df.groupby(["symbol", "fiscal_year"])["available_date"].max()
    wide = piv.join(avail).reset_index().sort_values(["symbol", "fiscal_year"]).reset_index(drop=True)
    # unify borrowings/borrowing (non-bank "+"/bank singular naming, see factors_fundamental.py)
    if "borrowings" in wide.columns or "borrowing" in wide.columns:
        wide["borrow_total"] = wide.get("borrowings")
        if "borrowing" in wide.columns:
            wide["borrow_total"] = wide["borrow_total"].fillna(wide["borrowing"])
    else:
        wide["borrow_total"] = np.nan
    _CACHE["wide"] = wide
    return wide


# ==========================================================================
# 1. per-annual-row raw factor computations (each symbol's own FY series)
# ==========================================================================
def _tax_rate(x):
    x = x / 100.0 if pd.notna(x) else np.nan
    return x if (pd.notna(x) and 0.0 <= x <= 0.60) else np.nan


def _annual_group(g: pd.DataFrame) -> pd.DataFrame:
    """g = one symbol's rows, sorted by fiscal_year ascending. Adds raw per-FY
    columns used by every builder below. Trailing-window stats use the last
    N *available reported* FY rows for that symbol (may not be exactly N
    calendar years apart if a report was skipped) -- disclosed convention,
    matches src/factors/factors_fundamental.py's trend_slope/stability."""
    g = g.sort_values("fiscal_year").reset_index(drop=True)

    op = g.get("operating profit")
    sales = g.get("sales")
    assets = g.get("total assets")
    ni = g.get("net profit")
    cfo = g.get("cash from operating activity")
    opm = g.get("opm %")
    eps = g.get("eps in rs")
    borrow = g.get("borrow_total")
    eqcap = g.get("equity capital")
    reserves = g.get("reserves")
    taxpct = g.get("tax %")

    networth = (eqcap.fillna(0) + reserves.fillna(0)) if eqcap is not None and reserves is not None else pd.Series(np.nan, index=g.index)
    ic_now = networth + (borrow.fillna(0) if borrow is not None else 0)
    ic_now = ic_now.where(networth.notna())  # NaN if networth itself unknown
    ic_avg = ic_now.rolling(2, min_periods=1).mean()  # avg current+prior FY IC, else current only

    tax_rate = taxpct.map(_tax_rate) if taxpct is not None else pd.Series(np.nan, index=g.index)
    nopat = op * (1 - tax_rate) if op is not None else pd.Series(np.nan, index=g.index)
    g["roic"] = (nopat / ic_avg).replace([np.inf, -np.inf], np.nan)

    g["gp_at"] = (op / assets).replace([np.inf, -np.inf], np.nan) if op is not None and assets is not None else np.nan

    g["accrual_raw"] = ((ni - cfo) / assets).replace([np.inf, -np.inf], np.nan) if ni is not None and cfo is not None and assets is not None else np.nan
    g["accrual_neg"] = -g["accrual_raw"]  # sign-flipped per pre-registered sign="-"

    ebitda_proxy = op
    g["cfo_ebitda"] = (cfo / ebitda_proxy).replace([np.inf, -np.inf], np.nan) if cfo is not None and ebitda_proxy is not None else np.nan
    g["cfo_ebitda_multi5y"] = g["cfo_ebitda"].rolling(5, min_periods=2).mean()

    roa = (ni / assets).replace([np.inf, -np.inf], np.nan) if ni is not None and assets is not None else pd.Series(np.nan, index=g.index)
    turnover = (sales / assets).replace([np.inf, -np.inf], np.nan) if sales is not None and assets is not None else pd.Series(np.nan, index=g.index)
    lev = (borrow / assets).replace([np.inf, -np.inf], np.nan) if borrow is not None and assets is not None else pd.Series(np.nan, index=g.index)

    s1 = (roa > 0).astype(float).where(roa.notna())
    s2 = (cfo > 0).astype(float).where(cfo.notna()) if cfo is not None else pd.Series(np.nan, index=g.index)
    s3 = (roa.diff() > 0).astype(float).where(roa.diff().notna())
    s4 = (cfo > ni).astype(float).where(cfo.notna() & ni.notna()) if cfo is not None and ni is not None else pd.Series(np.nan, index=g.index)
    s5 = (lev.diff() < 0).astype(float).where(lev.diff().notna())
    s7 = (eqcap.diff() <= 0).astype(float).where(eqcap.diff().notna()) if eqcap is not None else pd.Series(np.nan, index=g.index)
    s8 = (opm.diff() > 0).astype(float).where(opm.diff().notna()) if opm is not None else pd.Series(np.nan, index=g.index)
    s9 = (turnover.diff() > 0).astype(float).where(turnover.diff().notna())
    signals = pd.concat([s1, s2, s3, s4, s5, s7, s8, s9], axis=1)
    g["fscore"] = signals.sum(axis=1, skipna=True)
    g["fscore_n"] = signals.notna().sum(axis=1)
    g["fscore"] = g["fscore"].where(g["fscore_n"] > 0)

    eps_growth = eps.pct_change().replace([np.inf, -np.inf], np.nan) if eps is not None else pd.Series(np.nan, index=g.index)
    g["eps_growth_std5y_neg"] = -eps_growth.rolling(5, min_periods=3).std()
    if opm is not None:
        def _slope(s):
            s = s.dropna()
            if len(s) < 3:
                return np.nan
            x = np.arange(len(s))
            m = np.nanmean(np.abs(s.values))
            if m == 0:
                return np.nan
            return np.polyfit(x, s.values, 1)[0] / m
        g["opm_slope5y"] = opm.rolling(5, min_periods=3).apply(lambda s: _slope(pd.Series(s)), raw=False)
    else:
        g["opm_slope5y"] = np.nan
    # composite H023 = mean of available cross-sectionally-comparable-scale components
    # (both are already "higher=better, roughly unitless" so a simple average is used;
    # disclosed equal-weight combination, no fitted weights).
    g["earn_stability_composite"] = g[["eps_growth_std5y_neg", "opm_slope5y"]].mean(axis=1, skipna=True)
    n_comp = g[["eps_growth_std5y_neg", "opm_slope5y"]].notna().sum(axis=1)
    g["earn_stability_composite"] = g["earn_stability_composite"].where(n_comp > 0)

    return g


def _annual_factor_table() -> pd.DataFrame:
    if "annual" in _CACHE:
        return _CACHE["annual"]
    wide = _load_fund_wide()
    out = wide.groupby("symbol", group_keys=False).apply(_annual_group, include_groups=False)
    out = out.assign(symbol=wide["symbol"].values) if "symbol" not in out.columns else out
    keep = ["symbol", "fiscal_year", "available_date", "roic", "gp_at", "accrual_neg",
            "cfo_ebitda_multi5y", "fscore", "fscore_n", "earn_stability_composite"]
    out = out[keep].dropna(subset=["available_date"])
    _CACHE["annual"] = out
    return out


# ==========================================================================
# 2. PIT as-of join: annual factor table -> panel (date, symbol) grid
# ==========================================================================
def _asof_to_panel(panel: pd.DataFrame, value_col: str) -> pd.Series:
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
    merged = merged.dropna(subset=[value_col])
    return merged.set_index(["date", "symbol"])[value_col].rename("factor")


# ==========================================================================
# 3. worker-facing builders (panel_df) -> Series[(date,symbol)] = 'factor'
# ==========================================================================
def build_roic_factor(panel: pd.DataFrame) -> pd.Series:
    """H019: ROIC = NOPAT / avg(current+prior FY invested capital). Level only
    here (this run defers the 5y-stability half of the construct, since the
    panel's forward-return usable horizon is 1Y, not 5Y -- see module docstring
    deviation #4 analog; `roic` itself is a single-FY level, not yet the
    mean/1-std-of-5y composite the backlog construct describes in full)."""
    return _asof_to_panel(panel, "roic")


def build_piotroski_factor(panel: pd.DataFrame) -> pd.Series:
    """H020: 8-signal F-score proxy (0-8), ΔCurrent-ratio signal dropped
    (no current-asset/liability split in source). See deviation #2."""
    return _asof_to_panel(panel, "fscore")


def build_gross_profitability_factor(panel: pd.DataFrame) -> pd.Series:
    """H021: operating_profit / total_assets (gross-profit proxy). See deviation #1."""
    return _asof_to_panel(panel, "gp_at")


def build_accruals_factor(panel: pd.DataFrame) -> pd.Series:
    """H022: -(NetProfit - CFO)/Assets (sign-flipped so higher=better). See deviation #3."""
    return _asof_to_panel(panel, "accrual_neg")


def build_earnings_stability_factor(panel: pd.DataFrame) -> pd.Series:
    """H023: equal-weight composite of (-std(EPS YoY growth, 5y)) and
    (OPM 5y trend slope, mean-normalized). Tested at 1Y as a disclosed
    substitute for the unusable 5Y horizon. See deviation #4."""
    return _asof_to_panel(panel, "earn_stability_composite")


def build_cash_conversion_factor(panel: pd.DataFrame) -> pd.Series:
    """H045: trailing-5y mean of CFO / operating_profit (EBITDA proxy)."""
    return _asof_to_panel(panel, "cfo_ebitda_multi5y")


# ==========================================================================
# 4. coverage report (fundamentals availability per panel date)
# ==========================================================================
def coverage_report(panel: pd.DataFrame) -> pd.DataFrame:
    """Per panel date: how many panel symbols have a non-NaN match for each
    raw annual factor as-of that date (via the same PIT as-of join)."""
    cols = ["roic", "gp_at", "accrual_neg", "cfo_ebitda_multi5y", "fscore", "earn_stability_composite"]
    panel_dates_symbols = panel[["date", "symbol"]].drop_duplicates()
    rows = []
    per_col_series = {c: _asof_to_panel(panel, c) for c in cols}
    for d, g in panel_dates_symbols.groupby("date"):
        n_total = g["symbol"].nunique()
        row = {"date": d, "n_symbols": n_total}
        for c in cols:
            s = per_col_series[c]
            if d in s.index.get_level_values("date"):
                n = s.loc[d].index.nunique()
            else:
                n = 0
            row[c] = n
        rows.append(row)
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(RND_DIR / "lib"))
    from harness import load_panel
    panel, src = load_panel()
    print(f"panel_source={src} rows={len(panel)}")
    cov = coverage_report(panel)
    print(cov.to_string())
    cov.to_csv(RND_DIR / "reports" / "quality_fundamentals_coverage.csv", index=False)
