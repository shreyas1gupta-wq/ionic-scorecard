"""
WAVE worker (2026-07-17): India-QV money-first loop.
Builders for backlog_scout.json IDG-I-02, IDG-I-03, IDG-I-04, IDG-I-06, IDG-I-07.
Owner: this worker session. Feeds rnd/lib/harness.py's evaluate()/run_experiment(),
same PIT-join convention as builders_quality.py / builders_value.py (never redefines
IC/DSR/PBO math). No fabrication: anything not derivable from source columns is NaN.

Sources:
- ALPHA_RANKER/data/fundamentals/MASTER_fundamentals_pit.parquet (LONG, metric_norm +
  available_date, screener-condensed annual). Used by IDG-I-02/06/07.
- ALPHA_RANKER/data/fundamentals/consolidated/ratios.parquet (symbol, metric, period
  'Mon YYYY', value; NO available_date). Used by IDG-I-03; a conservative +6-month
  reporting lag is added at construction since the source carries no PIT timestamp
  (disclosed per backlog_scout.json's own instruction for this row).
- datasets/derived/shareholding_changes.parquet (repo-root relative, PIT available_date
  already present as a string column). Used by IDG-I-04. **STALE**: quarter_end max =
  2023-12-01, available_date max = 2023-12-26 (verified [DATA]) -- merge_asof backward
  means every panel date after 2023-12-26 carries the SAME last-known ownership print
  forward (PIT-legal, not a leak, but stale -- flagged in every card/report that uses
  this builder, per D-035 epistemic conduct).

Disclosed deviations:
1. IDG-I-06 "cash & investments" proxy for net-debt: MASTER_fundamentals_pit has no
   separable cash line (same gap builders_value.py #1 documents); "investments"
   metric_norm is the closest available line and is used as the cash&investments
   proxy net_debt = borrow_total - investments. This likely OVERSTATES net debt for
   balance sheets holding cash outside the "investments" line item (e.g. plain bank
   deposits classified elsewhere) -- same direction of bias as the EV construction
   elsewhere in this repo, documented not silently assumed clean.
2. IDG-I-06 net-debt/EBITDA-proxy is clipped to [-10, 30] before differencing (winsorize
   guard against tiny/near-zero operating-profit denominators blowing up the ratio) --
   disclosed, not a silent clip.
3. IDG-I-07 cumulative-CFO/PAT ratio is set NaN whenever the trailing cumulative PAT
   sum is <= 0 (a negative or zero multi-year PAT sum makes the ratio's sign
   uninterpretable as a "cash-conversion quality" measure) -- disclosed guard, not a
   fabricated value.
4. IDG-I-03 ROCE streak: `ratios.parquet` period parsed as calendar month-end via
   '%b %Y' (e.g. "Mar 2018" -> 2018-03-31); +6-month lag applied per backlog_scout.json's
   own PIT caveat instruction for this row (conservative, since no available_date exists
   in this source).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent                 # ALPHA_RANKER/rnd
ALPHA_DIR = RND_DIR.parent                    # ALPHA_RANKER
REPO_ROOT = ALPHA_DIR.parent                  # NIFTY 500 repo root

FUND_PATH = ALPHA_DIR / "data" / "fundamentals" / "MASTER_fundamentals_pit.parquet"
RATIOS_PATH = ALPHA_DIR / "data" / "fundamentals" / "consolidated" / "ratios.parquet"
SHAREHOLD_PATH = REPO_ROOT / "datasets" / "derived" / "shareholding_changes.parquet"

_CACHE: dict = {}


# ==========================================================================
# 0. shared loaders
# ==========================================================================
def _load_fund_wide() -> pd.DataFrame:
    """Same convention as builders_quality.py's _load_fund_wide (independent
    cache key so this module has no import-order dependency on that one)."""
    if "wide" in _CACHE:
        return _CACHE["wide"]
    df = pd.read_parquet(FUND_PATH)
    df = df.dropna(subset=["nse_symbol"]).rename(columns={"nse_symbol": "symbol"})
    piv = df.pivot_table(index=["symbol", "fiscal_year"], columns="metric_norm",
                          values="value", aggfunc="last")
    avail = df.groupby(["symbol", "fiscal_year"])["available_date"].max()
    wide = piv.join(avail).reset_index().sort_values(["symbol", "fiscal_year"]).reset_index(drop=True)
    if "borrowings" in wide.columns or "borrowing" in wide.columns:
        wide["borrow_total"] = wide.get("borrowings")
        if "borrowing" in wide.columns:
            wide["borrow_total"] = wide["borrow_total"].fillna(wide["borrowing"])
    else:
        wide["borrow_total"] = np.nan
    _CACHE["wide"] = wide
    return wide


def _asof_to_panel(panel: pd.DataFrame, series_df: pd.DataFrame, date_col: str, value_col: str) -> pd.Series:
    """Generic PIT as-of join: series_df has [symbol, date_col, value_col] ->
    aligned onto panel (date, symbol) via merge_asof backward (no lookahead)."""
    sub = series_df[["symbol", date_col, value_col]].dropna(subset=[value_col, date_col]).copy()
    sub["symbol"] = sub["symbol"].astype(str)
    sub[date_col] = pd.to_datetime(sub[date_col]).astype("datetime64[ns]")
    sub = sub.rename(columns={date_col: "date"}).sort_values("date")
    p = panel[["date", "symbol"]].drop_duplicates().copy()
    p["symbol"] = p["symbol"].astype(str)
    p["date"] = pd.to_datetime(p["date"]).astype("datetime64[ns]")
    p = p.sort_values("date")
    merged = pd.merge_asof(p, sub, on="date", by="symbol", direction="backward")
    merged = merged.dropna(subset=[value_col])
    return merged.set_index(["date", "symbol"])[value_col].rename("factor")


def _rank_avg(panel: pd.DataFrame, components: list[pd.Series]) -> pd.Series:
    """Per-date cross-sectional pct-rank each component, then average across
    available (non-NaN) components per (date,symbol) row -- same convention as
    builders_value.py's H018 rank-combine."""
    frames = []
    for i, comp in enumerate(components):
        f = comp.rename(f"c{i}").reset_index()
        f["date"] = pd.to_datetime(f["date"])
        f[f"c{i}"] = f.groupby("date")[f"c{i}"].rank(pct=True)
        frames.append(f.set_index(["date", "symbol"])[f"c{i}"])
    combo = pd.concat(frames, axis=1)
    out = combo.mean(axis=1, skipna=True)
    return out.dropna().rename("factor")


# ==========================================================================
# IDG-I-02 -- capital-efficiency-at-cycle (Andrade)
# rank_avg( rising asset-turnover slope(3y), LOW asset-growth )
# ==========================================================================
def _capeff_annual(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("fiscal_year").reset_index(drop=True)
    sales = g.get("sales")
    assets = g.get("total assets")
    turnover = (sales / assets).replace([np.inf, -np.inf], np.nan) if sales is not None and assets is not None else pd.Series(np.nan, index=g.index)

    def _slope(s):
        s = s.dropna()
        if len(s) < 3:
            return np.nan
        x = np.arange(len(s))
        m = np.nanmean(np.abs(s.values))
        if m == 0:
            return np.nan
        return np.polyfit(x, s.values, 1)[0] / m

    g["turnover_slope3y"] = turnover.rolling(3, min_periods=3).apply(lambda s: _slope(pd.Series(s)), raw=False)
    log_assets = np.log(assets.where(assets > 0)) if assets is not None else pd.Series(np.nan, index=g.index)
    g["asset_growth"] = log_assets.diff()
    g["neg_asset_growth"] = -g["asset_growth"]
    return g


def _capeff_table() -> pd.DataFrame:
    if "capeff" in _CACHE:
        return _CACHE["capeff"]
    wide = _load_fund_wide()
    out = wide.groupby("symbol", group_keys=False).apply(_capeff_annual, include_groups=False)
    out = out.assign(symbol=wide["symbol"].values) if "symbol" not in out.columns else out
    keep = ["symbol", "fiscal_year", "available_date", "turnover_slope3y", "neg_asset_growth"]
    out = out[keep].dropna(subset=["available_date"])
    _CACHE["capeff"] = out
    return out


def build_capeff_factor(panel: pd.DataFrame) -> pd.Series:
    """IDG-I-02: rank_avg(rising 3y asset-turnover slope, low asset growth).
    Both legs individually available for the incremental-vs-either-leg-alone
    kill condition via build_turnover_slope_only / build_asset_growth_only."""
    ann = _capeff_table()
    slope = ann.rename(columns={"turnover_slope3y": "value"})
    growth = ann.rename(columns={"neg_asset_growth": "value"})
    c1 = _asof_to_panel(panel, slope, "available_date", "value")
    c2 = _asof_to_panel(panel, growth, "available_date", "value")
    return _rank_avg(panel, [c1, c2])


def build_turnover_slope_only(panel: pd.DataFrame) -> pd.Series:
    ann = _capeff_table().rename(columns={"turnover_slope3y": "value"})
    return _asof_to_panel(panel, ann, "available_date", "value")


def build_asset_growth_only(panel: pd.DataFrame) -> pd.Series:
    ann = _capeff_table().rename(columns={"neg_asset_growth": "value"})
    return _asof_to_panel(panel, ann, "available_date", "value")


# ==========================================================================
# IDG-I-03 -- ROCE-longevity streak (Motilal QGLP / Marcellus)
# ==========================================================================
def _roce_streak_table() -> pd.DataFrame:
    if "roce_streak" in _CACHE:
        return _CACHE["roce_streak"]
    df = pd.read_parquet(RATIOS_PATH)
    df2 = df[df["metric"] == "ROCE %"].dropna(subset=["value"]).copy()
    df2["period_date"] = pd.to_datetime(df2["period"], format="%b %Y", errors="coerce") + pd.offsets.MonthEnd(0)
    df2 = df2.dropna(subset=["period_date"]).sort_values(["symbol", "period_date"]).reset_index(drop=True)
    streak_vals = np.zeros(len(df2), dtype=float)
    values = df2["value"].to_numpy()
    for _, idx in df2.groupby("symbol").groups.items():
        cur = 0
        for i in idx:  # idx is positional (df2 was reset_index(drop=True) above)
            cur = cur + 1 if values[i] > 15 else 0
            streak_vals[i] = cur
    df2["roce_streak"] = streak_vals
    # conservative PIT lag: no available_date in this source -> period_date + 6 months
    df2["available_date"] = df2["period_date"] + pd.DateOffset(months=6)
    _CACHE["roce_streak"] = df2[["symbol", "period_date", "available_date", "roce_streak"]]
    return _CACHE["roce_streak"]


def build_roce_streak_factor(panel: pd.DataFrame) -> pd.Series:
    """IDG-I-03: count of consecutive FYs with ROCE% > 15, +6mo conservative
    lag (source has no available_date). See module docstring deviation #4."""
    tbl = _roce_streak_table().rename(columns={"roce_streak": "value"})
    return _asof_to_panel(panel, tbl, "available_date", "value")


# ==========================================================================
# IDG-I-04 -- PPFAS under-owned contrarian value
# rank_avg( EY, rank_avg(-inst_level, -inst_yoy_change) )
# ==========================================================================
def _ownership_table() -> pd.DataFrame:
    if "own" in _CACHE:
        return _CACHE["own"]
    df = pd.read_parquet(SHAREHOLD_PATH)
    df = df.copy()
    df["available_date"] = pd.to_datetime(df["available_date"])
    df["combined_inst"] = df["FIIs"].fillna(0) + df["DIIs"].fillna(0)
    df["combined_inst_yoy"] = df["FIIs_yoy"].fillna(0) + df["DIIs_yoy"].fillna(0)
    # yoy=0 with both FIIs_yoy/DIIs_yoy actually NaN (first year, no prior) should stay NaN
    both_nan = df["FIIs_yoy"].isna() & df["DIIs_yoy"].isna()
    df.loc[both_nan, "combined_inst_yoy"] = np.nan
    _CACHE["own"] = df[["symbol", "available_date", "combined_inst", "combined_inst_yoy"]]
    return _CACHE["own"]


def build_underowned_value_factor(panel: pd.DataFrame) -> pd.Series:
    """IDG-I-04. STALE DATA FLAG: shareholding_changes.parquet's last
    available_date is 2023-12-26 (verified) -- every panel rebalance after
    that date reuses the same last-known ownership print (PIT-legal via
    merge_asof backward, not a leak, but a real staleness concentration;
    see coverage_report_i04() to quantify how many post-2024 panel rows this
    affects)."""
    import builders_value as bv
    ey = bv.build_H014_earnings_yield(panel)

    own = _ownership_table()
    level = own.rename(columns={"combined_inst": "value"})
    level["value"] = -level["value"]  # low ownership -> high factor
    yoy = own.rename(columns={"combined_inst_yoy": "value"})
    yoy["value"] = -yoy["value"]  # falling ownership -> high factor

    c_level = _asof_to_panel(panel, level, "available_date", "value")
    c_yoy = _asof_to_panel(panel, yoy, "available_date", "value")
    own_rank = _rank_avg(panel, [c_level, c_yoy])
    return _rank_avg(panel, [ey, own_rank])


def coverage_report_i04(panel: pd.DataFrame) -> dict:
    own = _ownership_table()
    cutoff = own["available_date"].max()
    p = panel[["date"]].drop_duplicates()
    p["date"] = pd.to_datetime(p["date"])
    n_after = int((p["date"] > cutoff).sum())
    n_total = int(len(p))
    return {"ownership_cutoff": str(cutoff.date()), "panel_dates_after_cutoff": n_after,
            "panel_dates_total": n_total, "pct_dates_stale_carryforward": round(n_after / n_total, 3) if n_total else None}


# ==========================================================================
# IDG-I-06 -- Deleveraging momentum (falling net-debt/EBITDA-proxy)
# ==========================================================================
def _delev_annual(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("fiscal_year").reset_index(drop=True)
    borrow = g.get("borrow_total")
    invest = g.get("investments")
    op = g.get("operating profit")
    cash_proxy = invest.fillna(0) if invest is not None else 0
    net_debt = (borrow.fillna(0) if borrow is not None else 0) - cash_proxy
    nd_ebitda = (net_debt / op).replace([np.inf, -np.inf], np.nan) if op is not None else pd.Series(np.nan, index=g.index)
    nd_ebitda = nd_ebitda.where(op > 0)  # guard: negative/zero EBITDA denominator is not a leverage ratio
    nd_ebitda = nd_ebitda.clip(-10, 30)  # winsorize guard, see module docstring #2
    g["nd_ebitda"] = nd_ebitda
    g["nd_ebitda_prior"] = nd_ebitda.shift(1)
    g["delev_improve"] = g["nd_ebitda_prior"] - g["nd_ebitda"]  # positive = deleveraging
    return g


def _delev_table() -> pd.DataFrame:
    if "delev" in _CACHE:
        return _CACHE["delev"]
    wide = _load_fund_wide()
    out = wide.groupby("symbol", group_keys=False).apply(_delev_annual, include_groups=False)
    out = out.assign(symbol=wide["symbol"].values) if "symbol" not in out.columns else out
    keep = ["symbol", "fiscal_year", "available_date", "nd_ebitda_prior", "delev_improve"]
    out = out[keep].dropna(subset=["available_date"])
    _CACHE["delev"] = out
    return out


def build_deleveraging_factor(panel: pd.DataFrame) -> pd.Series:
    """IDG-I-06: YoY decline in net-debt/EBITDA-proxy (winsorized). Higher =
    more deleveraging = better, per pre-registered sign='+'."""
    tbl = _delev_table().rename(columns={"delev_improve": "value"})
    return _asof_to_panel(panel, tbl[["symbol", "available_date", "value"]], "available_date", "value")


def build_deleveraging_ex_highlev_factor(panel: pd.DataFrame) -> pd.Series:
    """Pre-registered control: excludes names with PRIOR nd_ebitda > 5x before
    scoring (dead-cat-bounce control per backlog_scout.json kill condition --
    "survive after excluding names with prior net-debt/EBITDA>5x")."""
    tbl = _delev_table()
    tbl = tbl[tbl["nd_ebitda_prior"] <= 5.0].rename(columns={"delev_improve": "value"})
    return _asof_to_panel(panel, tbl[["symbol", "available_date", "value"]], "available_date", "value")


# ==========================================================================
# IDG-I-07 -- cumulative CFO/PAT (Mukherjea forensic, multi-year)
# ==========================================================================
def _cumcfo_annual(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("fiscal_year").reset_index(drop=True)
    cfo = g.get("cash from operating activity")
    ni = g.get("net profit")
    cfo_sum5y = cfo.rolling(5, min_periods=3).sum() if cfo is not None else pd.Series(np.nan, index=g.index)
    ni_sum5y = ni.rolling(5, min_periods=3).sum() if ni is not None else pd.Series(np.nan, index=g.index)
    ratio = (cfo_sum5y / ni_sum5y).replace([np.inf, -np.inf], np.nan)
    ratio = ratio.where(ni_sum5y > 0)  # guard #3: undefined sign if cumulative PAT <= 0
    g["cum_cfo_pat_5y"] = ratio
    return g


def _cumcfo_table() -> pd.DataFrame:
    if "cumcfo" in _CACHE:
        return _CACHE["cumcfo"]
    wide = _load_fund_wide()
    out = wide.groupby("symbol", group_keys=False).apply(_cumcfo_annual, include_groups=False)
    out = out.assign(symbol=wide["symbol"].values) if "symbol" not in out.columns else out
    keep = ["symbol", "fiscal_year", "available_date", "cum_cfo_pat_5y"]
    out = out[keep].dropna(subset=["available_date"])
    _CACHE["cumcfo"] = out
    return out


def build_cum_cfo_pat_factor(panel: pd.DataFrame) -> pd.Series:
    """IDG-I-07: trailing 5y sum(CFO)/sum(PAT); low=penalty per sign='+'
    (factor as-built already orients higher=better)."""
    tbl = _cumcfo_table().rename(columns={"cum_cfo_pat_5y": "value"})
    return _asof_to_panel(panel, tbl[["symbol", "available_date", "value"]], "available_date", "value")
