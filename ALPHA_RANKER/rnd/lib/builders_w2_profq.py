"""
WAVE-2 worker: Profitability / Quality-composite (money-first) builders.
Hypotheses: IDG-G-01 (op profitability), IDG-G-15 (profitability improvement,
delta-ROA proxy), IDG-G-02 (QMJ composite), IDG-G-12 (Buffett's-alpha composite).
Feeds rnd/lib/harness.py's evaluate() at basis='resid', horizons 1Y & 5Y, via
rnd/lib/run_w2_profq.py, against panel_long.parquet (21yr, 249 monthly dates).

Source: ALPHA_RANKER/data/fundamentals/MASTER_fundamentals_pit.parquet (LONG
format, one row per key_symbol x fiscal_year x metric_norm, PIT available_date).
Same 34-metric_norm universe as builders_quality.py (no COGS/current-ratio/
shares-outstanding split) -- every factor below uses ONLY what is present.
Banks/NBFCs report "financing profit"/"revenue" not "operating profit"/"sales"
-> profitability/leverage legs are correctly NaN for financials (not fabricated).

DATA-TRUST checked: group-by (symbol, fiscal_year, metric_norm) has a MAX group
size of 1 in this file (verified 2026-07-17) -- i.e. no duplicate/restated rows
compete at pivot time, so is_fresh cannot silently pick a stale duplicate over a
fresh one here. Freshness is instead reported as a coverage diagnostic (fraction
of PIT-joined rows with is_fresh==True) in the runner's summary, per this pass's
"honor DATA-TRUST decay" instruction -- disclosed, not silently assumed clean.

Disclosed deviations (read before citing any card):
1. **IDG-G-01 op profitability** = operating_profit / total_assets. Same proxy
   construction as H021 (builders_quality.py build_gross_profitability_factor)
   -- Novy-Marx's numerator is Revenue-COGS; this dataset has no COGS breakout,
   only "expenses" (all opex), so op_profit (= sales - expenses) sits closer to
   an EBITDA margin than literal gross profit. Re-derived independently here
   (not imported from builders_quality) per this worker's self-contained-module
   convention (matches rnd/run_long_confirm.py re-deriving build_earnings_yield
   rather than cross-importing).
2. **IDG-G-15 profitability improvement** = YoY change in op_at (op_profit/
   total_assets), i.e. delta-operating-profitability, NOT delta-net-income-ROA
   -- the backlog construct explicitly allows either "(or delta opm %)"; op_at
   delta was chosen for direct comparability with IDG-G-01's own leg (same
   denominator), so the "beat the level factor incrementally" pairing test is
   apples-to-apples.
3. **IDG-G-02 QMJ growth leg** = 3-year net-profit CAGR when both endpoint FYs
   have POSITIVE net profit ((NI_t/NI_t-3)**(1/3)-1); when either endpoint is
   <=0 (loss-making or turnaround year), CAGR is mathematically ill-defined
   under a fractional power, so we fall back to sign(NI_t - NI_t-3) scaled to
   [-1,+1] -- a disclosed fallback, not a silent NaN-drop, so turnaround names
   still get a directional growth score instead of being excluded.
4. **Safety leg** (QMJ + Buffett's-alpha) uses beta_252 read DIRECTLY off the
   panel argument (panel_long.parquet's own daily-price-derived, already-causal
   column) -- not re-derived here -- plus -(borrowings/operating_profit) built
   from the annual PIT fundamentals table (avg over reported FY only, no
   current/prior averaging since leverage ratios are typically read at a single
   point, unlike ROIC's invested-capital averaging convention in H019).
5. **Buffett's-alpha earnings-stability leg** = -std(net_profit YoY growth,
   trailing 5y, min_periods=3) -- distinct construction from H023's composite
   (which uses EPS growth std + OPM slope); this one is net-profit-growth-only
   per the IDG-G-12 backlog text ("inverse std of trailing 5y annual net_profit
   growth").
6. **Payout leg** (QMJ only) = raw "dividend payout %" cross-sectional rank per
   date, no PIT lag beyond the standard available_date asof-join (payout ratio
   is a reported-statement line item like the others, not a forward-looking
   estimate).
7. All composites are SIMPLE RANK-AVERAGES (equal-weight mean of per-date
   percentile ranks across legs) -- no learned/fitted weights, per
   CONSOLIDATION.md's "combine by simple rank-average" durable-model directive.
   A leg missing for a given (date,symbol) is skipmean'd (mean skipna=True),
   not zero-filled; the composite is NaN only if ALL legs are missing.
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
    # DATA-TRUST: (symbol, fiscal_year, metric_norm) has max group size 1 in
    # this file (no duplicate/restated rows) -- verified before writing this
    # module; aggfunc="last" is therefore a no-op tie-break, not a silent
    # freshness gamble. is_fresh coverage is reported separately by the runner.
    piv = df.pivot_table(index=["symbol", "fiscal_year"], columns="metric_norm",
                          values="value", aggfunc="last")
    avail = df.groupby(["symbol", "fiscal_year"])["available_date"].max()
    fresh_frac = df.groupby(["symbol", "fiscal_year"])["is_fresh"].mean()
    wide = piv.join(avail).join(fresh_frac.rename("is_fresh_frac")).reset_index()
    wide = wide.sort_values(["symbol", "fiscal_year"]).reset_index(drop=True)
    if "borrowings" in wide.columns or "borrowing" in wide.columns:
        wide["borrow_total"] = wide.get("borrowings")
        if "borrowing" in wide.columns:
            wide["borrow_total"] = wide["borrow_total"].fillna(wide["borrowing"])
    else:
        wide["borrow_total"] = np.nan
    _CACHE["wide"] = wide
    return wide


# ==========================================================================
# 1. per-annual-row raw factor computations
# ==========================================================================
def _cagr3_or_sign(ni: pd.Series) -> pd.Series:
    """3y net-profit CAGR when both endpoints positive; else sign(delta) in
    [-1,+1] fallback for loss-making/turnaround endpoints. See deviation #3."""
    ni_t = ni
    ni_t3 = ni.shift(3)
    both_pos = (ni_t > 0) & (ni_t3 > 0)
    cagr = (ni_t / ni_t3).pow(1.0 / 3.0) - 1.0
    cagr = cagr.where(both_pos)
    sign_fallback = np.sign(ni_t - ni_t3)
    out = cagr.where(both_pos, sign_fallback.where(ni_t3.notna() & ni_t.notna()))
    return out.replace([np.inf, -np.inf], np.nan)


def _annual_group(g: pd.DataFrame) -> pd.DataFrame:
    """g = one symbol's rows, sorted by fiscal_year ascending. Adds the raw
    per-FY legs used by every builder below."""
    g = g.sort_values("fiscal_year").reset_index(drop=True)

    op = g.get("operating profit")
    assets = g.get("total assets")
    ni = g.get("net profit")
    borrow = g.get("borrow_total")
    payout = g.get("dividend payout %")

    g["op_at"] = (op / assets).replace([np.inf, -np.inf], np.nan) if op is not None and assets is not None else np.nan
    g["op_at_delta"] = g["op_at"].diff()  # IDG-G-15

    g["ni_growth_3y"] = _cagr3_or_sign(ni) if ni is not None else np.nan  # IDG-G-02 growth leg

    g["borrow_op_neg"] = (-(borrow / op)).replace([np.inf, -np.inf], np.nan) if borrow is not None and op is not None else np.nan

    g["payout_pct"] = payout if payout is not None else np.nan

    ni_growth = ni.pct_change().replace([np.inf, -np.inf], np.nan) if ni is not None else pd.Series(np.nan, index=g.index)
    g["ni_growth_std5y_neg"] = -ni_growth.rolling(5, min_periods=3).std()  # IDG-G-12 stability leg

    return g


def _annual_factor_table() -> pd.DataFrame:
    if "annual" in _CACHE:
        return _CACHE["annual"]
    wide = _load_fund_wide()
    out = wide.groupby("symbol", group_keys=False).apply(_annual_group, include_groups=False)
    out = out.assign(symbol=wide["symbol"].values) if "symbol" not in out.columns else out
    keep = ["symbol", "fiscal_year", "available_date", "is_fresh_frac",
            "op_at", "op_at_delta", "ni_growth_3y", "borrow_op_neg",
            "payout_pct", "ni_growth_std5y_neg"]
    out = out[[c for c in keep if c in out.columns]].dropna(subset=["available_date"])
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


def freshness_coverage(panel: pd.DataFrame, value_col: str = "op_at") -> float:
    """Fraction of PIT-joined rows (date,symbol) whose matched annual FY had
    is_fresh_frac >= 0.5 (majority-fresh statement) -- DATA-TRUST diagnostic."""
    annual = _annual_factor_table()
    sub = annual[["symbol", "available_date", value_col, "is_fresh_frac"]].dropna(subset=[value_col]).copy()
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
    if merged.empty:
        return float("nan")
    return float((merged["is_fresh_frac"] >= 0.5).mean())


# ==========================================================================
# 3. rank/z helpers for cross-sectional composites
# ==========================================================================
def _rank_by_date(s: pd.Series) -> pd.Series:
    return s.groupby(level="date").rank(pct=True)


def _zscore_by_date(s: pd.Series) -> pd.Series:
    def _z(x):
        sd = x.std(ddof=0)
        return (x - x.mean()) / sd if sd and sd > 0 else pd.Series(np.nan, index=x.index)
    return s.groupby(level="date").transform(_z)


def _rank_combine(legs: list) -> pd.Series:
    """Equal-weight mean of per-date percentile ranks across legs (outer-
    aligned on (date,symbol) index); NaN leg for a row is skipna'd, not
    zero-filled. No learned weights, per CONSOLIDATION.md."""
    ranked = [_rank_by_date(leg.rename("v")) for leg in legs]
    combo = pd.concat(ranked, axis=1).mean(axis=1, skipna=True)
    return combo.rename("factor")


# ==========================================================================
# 4. worker-facing builders (panel_df with beta_252 col) -> Series[(date,symbol)]
# ==========================================================================
def build_op_profitability_factor(panel: pd.DataFrame) -> pd.Series:
    """IDG-G-01: operating_profit / total_assets (Novy-Marx proxy). See dev #1."""
    return _asof_to_panel(panel, "op_at")


def build_profitability_change_factor(panel: pd.DataFrame) -> pd.Series:
    """IDG-G-15: YoY change in op_at (profitability improvement). See dev #2."""
    return _asof_to_panel(panel, "op_at_delta")


def build_qmj_composite(panel: pd.DataFrame) -> pd.Series:
    """IDG-G-02: rank-average of 4 legs -- profitability (op_at), growth
    (ni_growth_3y), safety (z(-beta_252)+z(-borrowings/op_profit), the two
    z-scores summed into ONE safety sub-score before it enters the rank-
    average), payout (dividend payout %). See dev #3, #4, #6, #7."""
    op_at = _asof_to_panel(panel, "op_at")
    growth = _asof_to_panel(panel, "ni_growth_3y")
    lev_neg = _asof_to_panel(panel, "borrow_op_neg")
    payout = _asof_to_panel(panel, "payout_pct")

    beta = panel[["date", "symbol", "beta_252"]].dropna(subset=["beta_252"]).copy()
    beta["date"] = pd.to_datetime(beta["date"])
    beta["symbol"] = beta["symbol"].astype(str)
    beta_neg = (-beta.set_index(["date", "symbol"])["beta_252"]).rename("factor")

    beta_z = _zscore_by_date(beta_neg)
    lev_z = _zscore_by_date(lev_neg)
    safety = pd.concat([beta_z, lev_z], axis=1).mean(axis=1, skipna=True).rename("factor")

    return _rank_combine([op_at, growth, safety, payout])


def build_buffett_alpha_composite(panel: pd.DataFrame) -> pd.Series:
    """IDG-G-12: rank-average of 4 legs -- op_profitability (op_at), safety
    (-beta_252, BAB-style, its OWN leg here not combined with leverage as in
    QMJ), low-leverage (-borrowings/op_profit), earnings-stability (-std of
    trailing 5y net_profit growth). See dev #4, #5, #7."""
    op_at = _asof_to_panel(panel, "op_at")
    lev_neg = _asof_to_panel(panel, "borrow_op_neg")
    stability = _asof_to_panel(panel, "ni_growth_std5y_neg")

    beta = panel[["date", "symbol", "beta_252"]].dropna(subset=["beta_252"]).copy()
    beta["date"] = pd.to_datetime(beta["date"])
    beta["symbol"] = beta["symbol"].astype(str)
    beta_neg = (-beta.set_index(["date", "symbol"])["beta_252"]).rename("factor")

    return _rank_combine([op_at, beta_neg, lev_neg, stability])


# ==========================================================================
# 5. coverage report
# ==========================================================================
def coverage_report(panel: pd.DataFrame) -> pd.DataFrame:
    cols = ["op_at", "op_at_delta", "ni_growth_3y", "borrow_op_neg", "payout_pct", "ni_growth_std5y_neg"]
    panel_dates_symbols = panel[["date", "symbol"]].drop_duplicates()
    rows = []
    per_col_series = {c: _asof_to_panel(panel, c) for c in cols}
    for d, g in panel_dates_symbols.groupby("date"):
        n_total = g["symbol"].nunique()
        row = {"date": d, "n_symbols": n_total}
        for c in cols:
            s = per_col_series[c]
            row[c] = int(s.loc[d].index.nunique()) if d in s.index.get_level_values("date") else 0
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
