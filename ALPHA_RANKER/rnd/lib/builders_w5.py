"""
WAVE-5 priority-H convex/forensic candidates (Sanjay Kulkarni task, 2026-07-17;
per rnd/wave4/hypotheses_w5.json, author Prof. Aditya Verma).

W5-01  Cost-elasticity discipline (anti-sticky costs)
W5-02  Implied borrowing cost (lender-information channel)
W5-04  Net financial slack (fortress balance sheet, crisis-conditional)

Data: ALPHA_RANKER/data/fundamentals/MASTER_fundamentals_pit.parquet (LONG,
one row per nse_symbol x fiscal_year x metric_norm, PIT available_date).
Reuses builders_w2_issuance._load_fund_wide / _zscore_by_date (same pivot,
same winsorize-then-z convention as every prior wave). PIT method identical
to builders_w4t_forensic.py: annual (symbol, fiscal_year) factor table ->
merge_asof to the (date,symbol) panel grid on available_date <= date,
direction='backward'.

Financials excluded for all three (per hypotheses text) via panel's sector
map (sector == 'Financial Services' dropped at the annual-table level).

Sign convention: ALL factors below are built HIGHER = economically GOOD
(repo convention, harness assumes long-top-decile is the intended long leg).
No sign flip needed for W5-01 (elasticity itself is already "higher=disciplined")
or W5-04 (slack itself is already "higher=more slack"); W5-02 is explicitly
sign-flipped (-z of implied rate, long LOW rate).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
ALPHA_DIR = RND_DIR.parent
FUND_PATH = ALPHA_DIR / "data" / "fundamentals" / "MASTER_fundamentals_pit.parquet"

import builders_w2_issuance as BI  # noqa: E402  (reuse _load_fund_wide, _zscore_by_date)

_CACHE: dict = {}
FINANCIALS_SECTOR = "Financial Services"


def _sector_map(panel: pd.DataFrame) -> dict:
    return panel.groupby("symbol")["sector"].agg(
        lambda s: s.mode().iat[0] if len(s.mode()) else None
    ).to_dict()


def _diagnostic_counts() -> dict:
    return _CACHE.get("diagnostics", {})


# ==========================================================================
# W5-01: cost-elasticity discipline (trailing 8-FY window, per-symbol loop --
# window logic (variable-length down-sales-year selection) is not a clean
# vectorized rolling op, so an explicit per-symbol pass is used; data volume
# (~2,500 symbols x ~20 FYs) makes this cheap).
# ==========================================================================
def _w501_group(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("fiscal_year").reset_index(drop=True)
    fy = g["fiscal_year"].values
    sales = g.get("sales")
    expenses = g.get("expenses")
    n = len(g)
    base = np.full(n, np.nan)
    refine = np.full(n, np.nan)
    n_down = np.zeros(n, dtype=int)
    if sales is None or expenses is None:
        g["w501_elasticity_down_base"] = base
        g["w501_elasticity_down_refine"] = refine
        g["w501_n_down_years"] = n_down
        return g
    sales = sales.values.astype(float)
    expenses = expenses.values.astype(float)
    ln_sales = np.where(sales > 0, np.log(sales), np.nan)
    ln_exp = np.where(expenses > 0, np.log(expenses), np.nan)
    # pair i represents (fy[i-1] -> fy[i]); require consecutive FYs
    d_ln_sales = np.full(n, np.nan)
    d_ln_exp = np.full(n, np.nan)
    for i in range(1, n):
        if fy[i] - fy[i - 1] == 1:
            d_ln_sales[i] = ln_sales[i] - ln_sales[i - 1]
            d_ln_exp[i] = ln_exp[i] - ln_exp[i - 1]
    elasticity_pair = np.where(
        (~np.isnan(d_ln_sales)) & (~np.isnan(d_ln_exp)) & (d_ln_sales != 0),
        d_ln_exp / d_ln_sales, np.nan,
    )
    down_flag = d_ln_sales < 0
    for i in range(n):
        lo = max(1, i - 6)  # trailing-8-FY window ending at fy[i] => pairs [i-6 .. i] (7 pairs)
        idxs = [j for j in range(lo, i + 1) if down_flag[j] and not np.isnan(elasticity_pair[j])]
        if len(idxs) >= 2:
            base[i] = np.mean([elasticity_pair[j] for j in idxs])
            n_down[i] = len(idxs)
        if len(idxs) >= 3:
            refine[i] = base[i]
    g["w501_elasticity_down_base"] = base
    g["w501_elasticity_down_refine"] = refine
    g["w501_n_down_years"] = n_down
    return g


# ==========================================================================
# W5-02: implied borrowing cost (level, size+sector residualized)
# ==========================================================================
def _w502_group(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("fiscal_year").reset_index(drop=True)
    fy = g["fiscal_year"]
    interest = g.get("interest")
    borrowings = g.get("borrowings")
    ta = g.get("total assets")
    if interest is None or borrowings is None or ta is None:
        g["w502_implied_rate"] = np.nan
        return g
    borrow_lag1 = borrowings.shift(1).where((fy - fy.shift(1)) == 1)
    avg_borrow = 0.5 * (borrowings + borrow_lag1)
    avg_borrow = avg_borrow.where(borrow_lag1.notna())  # need t-1 to exist
    implied_rate = interest / avg_borrow.replace(0, np.nan)
    borrow_intensity = avg_borrow / ta.replace(0, np.nan)
    implied_rate = implied_rate.where(borrow_intensity >= 0.05)  # gate: near-zero-debt names NaN'd
    implied_rate_wins = implied_rate.clip(upper=0.30)  # winsorize refinement per hypothesis text (data errors)
    g["w502_implied_rate"] = implied_rate_wins
    g["w502_borrow_intensity"] = borrow_intensity
    return g


def _resid_size_sector(df: pd.DataFrame, value_col: str, size_col: str, sector_col: str) -> pd.Series:
    """Per-date cross-sectional residualization of value_col on ln(size_col) with
    sector fixed effects (Frisch-Waugh-Lovell: sector-demean both series, then
    OLS the demeaned value on the demeaned size regressor, no intercept needed
    post-demeaning)."""
    def _resid(g):
        v = g[value_col].astype(float)
        s = np.log(g[size_col].astype(float).clip(lower=1e-6))
        sec = g[sector_col].fillna("Unknown")
        valid = v.notna() & s.notna()
        if valid.sum() < 15:
            return pd.Series(np.nan, index=g.index)
        v_dm = v.where(valid) - v.where(valid).groupby(sec).transform("mean")
        s_dm = s.where(valid) - s.where(valid).groupby(sec).transform("mean")
        denom = float((s_dm[valid] ** 2).sum())
        slope = float((s_dm[valid] * v_dm[valid]).sum() / denom) if denom > 0 else 0.0
        resid = v_dm - slope * s_dm
        return resid
    return df.groupby("date", group_keys=False).apply(_resid, include_groups=False)


# ==========================================================================
# W5-04: net financial slack
# ==========================================================================
def _w504_group(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("fiscal_year").reset_index(drop=True)
    investments = g.get("investments")
    borrowings = g.get("borrowings")
    ta = g.get("total assets")
    if investments is None or borrowings is None or ta is None:
        g["w504_slack"] = np.nan
        return g
    g["w504_slack"] = (investments - borrowings) / ta.replace(0, np.nan)
    return g


# ==========================================================================
# annual factor table (shared build across all 3 hypotheses)
# ==========================================================================
def _annual_factor_table(panel: pd.DataFrame) -> pd.DataFrame:
    if "annual" in _CACHE:
        return _CACHE["annual"]
    wide = BI._load_fund_wide()
    smap = _sector_map(panel)
    wide["sector"] = wide["symbol"].map(smap)
    n_before = wide["symbol"].nunique()
    wide = wide[wide["sector"] != FINANCIALS_SECTOR].copy()
    n_after = wide["symbol"].nunique()

    out = wide.groupby("symbol", group_keys=False).apply(_w501_group, include_groups=False)
    out = out.assign(symbol=wide["symbol"].values) if "symbol" not in out.columns else out
    out = out.groupby("symbol", group_keys=False).apply(_w502_group, include_groups=False)
    out = out.assign(symbol=wide["symbol"].values) if "symbol" not in out.columns else out
    out = out.groupby("symbol", group_keys=False).apply(_w504_group, include_groups=False)
    out = out.assign(symbol=wide["symbol"].values) if "symbol" not in out.columns else out

    keep = ["symbol", "fiscal_year", "available_date", "sector",
            "w501_elasticity_down_base", "w501_elasticity_down_refine", "w501_n_down_years",
            "w502_implied_rate", "w502_borrow_intensity", "w504_slack",
            "total assets"]
    keep = [c for c in keep if c in out.columns]
    out = out[keep].dropna(subset=["available_date"])
    _CACHE["annual"] = out
    _CACHE["diagnostics"] = {
        "n_symbols_before_financials_excl": int(n_before),
        "n_symbols_after_financials_excl": int(n_after),
        "n_financials_excluded": int(n_before - n_after),
        "n_annual_rows": int(len(out)),
        "n_annual_rows_w501_base": int(out["w501_elasticity_down_base"].notna().sum()),
        "n_annual_rows_w501_refine": int(out["w501_elasticity_down_refine"].notna().sum()),
        "n_annual_rows_w502": int(out["w502_implied_rate"].notna().sum()),
        "n_annual_rows_w504": int(out["w504_slack"].notna().sum()),
    }
    return out


def _asof(panel: pd.DataFrame, value_cols: list) -> pd.DataFrame:
    annual = _annual_factor_table(panel)
    sub = annual[["symbol", "available_date", "sector"] + value_cols].copy()
    sub["symbol"] = sub["symbol"].astype(str)
    sub["available_date"] = pd.to_datetime(sub["available_date"]).astype("datetime64[ns]")
    sub = sub.sort_values("available_date")
    p = panel[["date", "symbol"]].drop_duplicates().copy()
    p["symbol"] = p["symbol"].astype(str)
    p["date"] = pd.to_datetime(p["date"]).astype("datetime64[ns]")
    p = p.sort_values("date")
    merged = pd.merge_asof(p, sub.rename(columns={"available_date": "date"}),
                            on="date", by="symbol", direction="backward")
    return merged


# ==========================================================================
# worker-facing builders -> Series[(date,symbol)] = z-scored, sign-corrected factor
# ==========================================================================
def build_w501_base(panel: pd.DataFrame) -> pd.Series:
    """W5-01 BASE: z(elasticity_down, >=2 down-sales-year pairs in trailing 8 FY). Long HIGH."""
    m = _asof(panel, ["w501_elasticity_down_base"])
    m = m.dropna(subset=["w501_elasticity_down_base"])
    m["z"] = BI._zscore_by_date(m[["date", "w501_elasticity_down_base"]], "w501_elasticity_down_base")
    m = m.dropna(subset=["z"])
    return m.set_index(["date", "symbol"])["z"]


def build_w501_refine(panel: pd.DataFrame) -> pd.Series:
    """W5-01 REFINEMENT: same, gated to >=3 down-sales-year pairs (pre-registered)."""
    m = _asof(panel, ["w501_elasticity_down_refine"])
    m = m.dropna(subset=["w501_elasticity_down_refine"])
    m["z"] = BI._zscore_by_date(m[["date", "w501_elasticity_down_refine"]], "w501_elasticity_down_refine")
    m = m.dropna(subset=["z"])
    return m.set_index(["date", "symbol"])["z"]


def build_w502_base(panel: pd.DataFrame) -> pd.Series:
    """W5-02 BASE: -z(implied_rate residualized on ln(total assets) + sector). Long LOW rate."""
    m = _asof(panel, ["w502_implied_rate", "total assets"])
    m = m.dropna(subset=["w502_implied_rate", "total assets"])
    m["resid"] = _resid_size_sector(m, "w502_implied_rate", "total assets", "sector")
    m = m.dropna(subset=["resid"])
    m["resid_neg"] = -m["resid"]
    m["z"] = BI._zscore_by_date(m[["date", "resid_neg"]], "resid_neg")
    m = m.dropna(subset=["z"])
    return m.set_index(["date", "symbol"])["z"]


def build_w504_base(panel: pd.DataFrame) -> pd.Series:
    """W5-04 BASE: z(net financial slack). Long HIGH slack."""
    m = _asof(panel, ["w504_slack"])
    m = m.dropna(subset=["w504_slack"])
    m["z"] = BI._zscore_by_date(m[["date", "w504_slack"]], "w504_slack")
    m = m.dropna(subset=["z"])
    return m.set_index(["date", "symbol"])["z"]


# ==========================================================================
# WAVE-5 remaining buildable candidates (Sanjay Kulkarni task, 2026-07-17):
# W5-05 treasury bloat / diworsification, W5-06 dividend continuity under
# earnings stress, W5-07 borrowed dividends red flag, W5-08 moat proxy
# (OPM level x stability, 5Y). Same annual-table / merge_asof / PIT machinery
# as W5-01/02/04 above. Financials excluded for W5-05/08 (per hypothesis
# text); W5-06/07 are payout-driven and inherently non-financial-institution
# concepts too but the hypothesis text does not explicitly gate them on
# sector, so they are NOT financials-excluded here (kept exactly as spec'd,
# [INFERENCE] flagged) -- the ~750-firm dividend-payout subset in practice
# contains very few banks/NBFCs with disk coverage of this field so the
# effect of this choice is expected to be small; disclosed, not silently
# assumed.
# ==========================================================================
def _lag_by_years(g: pd.DataFrame, col: str, k: int) -> pd.Series:
    """Exact fiscal_year-k lookup (NOT positional shift) -- robust to gaps
    in a symbol's annual coverage. Returns a Series aligned to g's index."""
    fy = g["fiscal_year"]
    val = g[col]
    fy_to_val = dict(zip(fy.values, val.values))
    return fy.map(lambda f: fy_to_val.get(f - k, np.nan))


# --------------------------------------------------------------------------
# W5-05: treasury bloat / diworsification penalty
# --------------------------------------------------------------------------
def _w505_group(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("fiscal_year").reset_index(drop=True)
    investments = g.get("investments")
    ta = g.get("total assets")
    fixed = g.get("fixed assets")
    cwip = g.get("cwip")
    payout = g.get("dividend payout %")
    n = len(g)
    if investments is None or ta is None or fixed is None or cwip is None:
        g["w505_share"] = np.nan
        g["w505_gate_capex_ok"] = np.nan
        g["w505_gate_payout_ok"] = np.nan
        g["w505_payout_available"] = False
        return g

    inv_lag3 = _lag_by_years(g, "investments", 3) if "investments" in g else pd.Series(np.nan, index=g.index)
    ta_lag3 = _lag_by_years(g, "total assets", 3)
    fixed_lag3 = _lag_by_years(g, "fixed assets", 3)
    cwip_lag3 = _lag_by_years(g, "cwip", 3)

    d_inv = investments - inv_lag3
    d_ta = ta - ta_lag3
    d_fixed_cwip = (fixed + cwip) - (fixed_lag3 + cwip_lag3)

    denom = np.maximum(d_ta.values, 0.02 * ta_lag3.values)
    denom = np.where((ta_lag3.values > 0) & np.isfinite(denom) & (denom > 0), denom, np.nan)
    share = d_inv.values / denom

    # capex gate uses RAW d_total_assets (per hypothesis text), NaN if d_ta<=0
    # (ratio not economically meaningful -- can't evaluate "share of growth
    # went to capex" when the base didn't grow).
    ratio_capex = np.where(d_ta.values > 0, d_fixed_cwip.values / d_ta.values, np.nan)
    # NaN-preserving gate (d_ta<=0 -> undefined, NOT auto-fail) so downstream
    # dropna() correctly excludes un-evaluable rows instead of silently
    # treating them as "capex gate failed".
    gate_capex_ok = np.where(np.isnan(ratio_capex), np.nan, (ratio_capex < 0.25).astype(float))

    payout_available = np.zeros(n, dtype=bool)
    gate_payout_ok = np.ones(n, dtype=bool)  # condition DROPPED (=True/non-binding) where unavailable
    if payout is not None:
        payout_lag3 = _lag_by_years(g, "dividend payout %", 3)
        both = payout.notna().values & payout_lag3.notna().values
        payout_available = both
        not_risen = (payout.values <= payout_lag3.values)
        gate_payout_ok = np.where(both, not_risen, True)

    g["w505_share"] = share
    g["w505_gate_capex_ok"] = gate_capex_ok
    g["w505_gate_payout_ok"] = gate_payout_ok
    g["w505_payout_available"] = payout_available
    return g


# --------------------------------------------------------------------------
# W5-06: dividend continuity under earnings stress (payout persistence)
# --------------------------------------------------------------------------
def _w506_group(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("fiscal_year").reset_index(drop=True)
    fy = g["fiscal_year"].values
    payout = g.get("dividend payout %")
    eps = g.get("eps in rs")
    n = len(g)
    streak = np.zeros(n, dtype=int)
    stress_bonus = np.zeros(n)  # 0 = no stress episode observed yet (neutral)
    has_payout_data = payout is not None and eps is not None
    if not has_payout_data:
        g["w506_streak"] = streak
        g["w506_stress_bonus"] = stress_bonus
        g["w506_has_data"] = False
        return g

    payout_v = payout.values.astype(float)
    eps_v = eps.values.astype(float)
    consecutive_ok = ~np.isnan(payout_v) & (payout_v > 0)
    for i in range(n):
        if not consecutive_ok[i]:
            streak[i] = 0
            continue
        s = 0
        j = i
        while j >= 0 and consecutive_ok[j] and (j == i or fy[j + 1] - fy[j] == 1):
            s += 1
            j -= 1
        streak[i] = s

    # DPS proxy = eps * payout%/100
    dps_proxy = np.where(~np.isnan(eps_v) & ~np.isnan(payout_v), eps_v * payout_v / 100.0, np.nan)
    dps_lag1 = np.roll(dps_proxy, 1)
    dps_lag1[0] = np.nan
    fy_gap1 = np.concatenate([[False], (fy[1:] - fy[:-1]) == 1])
    dps_lag1 = np.where(fy_gap1, dps_lag1, np.nan)
    eps_lag1 = np.roll(eps_v, 1)
    eps_lag1[0] = np.nan
    eps_lag1 = np.where(fy_gap1, eps_lag1, np.nan)
    eps_decline_20 = (~np.isnan(eps_v)) & (~np.isnan(eps_lag1)) & (eps_lag1 > 0) & (eps_v <= 0.8 * eps_lag1)
    dps_fell_10 = (~np.isnan(dps_proxy)) & (~np.isnan(dps_lag1)) & (dps_lag1 > 0) & (dps_proxy < 0.9 * dps_lag1)
    # +0.5 if held through the stress year (did NOT fall >10%), -0.5 if cut
    # (fell >10%) -- symmetric per hypothesis's own "cutters underperform"
    # expected_sign text; [INFERENCE]: hypothesis only specified the +0.5
    # "held" bonus explicitly, the -0.5 "cut" penalty is this build's
    # symmetric extension of the same certification logic, disclosed here.
    stress_year_bonus = np.where(eps_decline_20, np.where(dps_fell_10, -0.5, 0.5), np.nan)
    # once an episode is observed, the certification/cut carries forward
    # (reputation persists) until the NEXT stress episode updates it
    last_bonus = np.nan
    for i in range(n):
        if not np.isnan(stress_year_bonus[i]):
            last_bonus = stress_year_bonus[i]
        stress_bonus[i] = last_bonus if not np.isnan(last_bonus) else 0.0

    g["w506_streak"] = np.minimum(streak, 10)
    g["w506_stress_bonus"] = stress_bonus
    g["w506_has_data"] = consecutive_ok | (~np.isnan(payout_v))
    return g


# --------------------------------------------------------------------------
# W5-07: borrowed dividends (payout funded by debt) red flag
# --------------------------------------------------------------------------
def _w507_group(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("fiscal_year").reset_index(drop=True)
    payout = g.get("dividend payout %")
    borrowings = g.get("borrowings")
    interest = g.get("interest")
    net_profit = g.get("net profit")
    cfo = g.get("cash from operating activity")
    n = len(g)
    if payout is None or borrowings is None:
        g["w507_penalty_base"] = np.nan
        g["w507_penalty_refine"] = np.nan
        g["w507_cfo_available"] = False
        return g

    borrow_lag1 = _lag_by_years(g, "borrowings", 1)
    payout_v = payout.values.astype(float)
    borrow_v = borrowings.values.astype(float)
    borrow_lag1_v = borrow_lag1.values.astype(float)

    payout_positive = ~np.isnan(payout_v) & (payout_v > 0)
    borrow_grew_15 = (~np.isnan(borrow_lag1_v)) & (borrow_lag1_v > 0) & (borrow_v > 1.15 * borrow_lag1_v)
    flag_core = payout_positive & borrow_grew_15
    borrow_growth = np.where(borrow_grew_15, borrow_v / borrow_lag1_v - 1.0, np.nan)

    # BASE (full-coverage, no CFO condition): penalty magnitude = excess
    # borrowing-growth over the 15% trigger x payout ratio, applied ONLY on
    # flagged rows; 0.0 elsewhere (penalty-only construction, per hypothesis
    # text "Factor = penalty-only").
    excess_growth = np.where(flag_core, np.maximum(borrow_growth - 0.15, 0.0), 0.0)
    penalty_base = np.where(np.isnan(payout_v), np.nan, np.where(flag_core, excess_growth * (payout_v / 100.0), 0.0))

    cfo_available = np.zeros(n, dtype=bool)
    penalty_refine = np.full(n, np.nan)
    if cfo is not None and net_profit is not None and interest is not None:
        cfo_v = cfo.values.astype(float)
        ni_v = net_profit.values.astype(float)
        int_v = interest.values.astype(float)
        est_div = ni_v * payout_v / 100.0
        cfo_available = ~np.isnan(cfo_v) & ~np.isnan(est_div) & ~np.isnan(int_v)
        cfo_short = cfo_available & (cfo_v < (est_div + int_v))
        flag_refine = flag_core & cfo_short
        # refine universe = CFO-available rows only (subset test, per spec)
        penalty_refine = np.where(cfo_available, np.where(flag_refine, excess_growth * (payout_v / 100.0), 0.0), np.nan)

    g["w507_penalty_base"] = penalty_base
    g["w507_penalty_refine"] = penalty_refine
    g["w507_cfo_available"] = cfo_available
    g["w507_flag_rate_base"] = flag_core
    return g


# --------------------------------------------------------------------------
# W5-08: moat proxy -- OPM level x stability (5Y trailing)
# --------------------------------------------------------------------------
def _w508_group(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("fiscal_year").reset_index(drop=True)
    opm = g.get("opm %")
    n = len(g)
    moat = np.full(n, np.nan)
    if opm is None:
        g["w508_moat"] = moat
        return g
    opm_v = opm.values.astype(float)
    for i in range(n):
        lo = max(0, i - 4)  # trailing window ending at i, up to 5 FYs
        window = opm_v[lo:i + 1]
        window = window[~np.isnan(window)]
        if len(window) >= 4:  # require >=4 of the trailing-5 FYs observed
            med = np.median(window)
            q75, q25 = np.percentile(window, [75, 25])
            iqr = q75 - q25
            moat[i] = med - 1.0 * iqr  # lambda=1, pre-set
    g["w508_moat"] = moat
    return g


# ==========================================================================
# annual factor table v2 (W5-05..08), separate cache key so the original
# W5-01/02/04 table above is untouched (no shared-state regression risk).
# ==========================================================================
def _annual_factor_table_v2(panel: pd.DataFrame) -> pd.DataFrame:
    if "annual_v2" in _CACHE:
        return _CACHE["annual_v2"]
    wide = BI._load_fund_wide()
    smap = _sector_map(panel)
    wide["sector"] = wide["symbol"].map(smap)
    n_before = wide["symbol"].nunique()
    wide_nonfin = wide[wide["sector"] != FINANCIALS_SECTOR].copy()
    n_after = wide_nonfin["symbol"].nunique()

    # W5-05, W5-08 -- non-financials only
    out5 = wide_nonfin.groupby("symbol", group_keys=False).apply(_w505_group, include_groups=False)
    out5 = out5.assign(symbol=wide_nonfin["symbol"].values) if "symbol" not in out5.columns else out5
    out8 = wide_nonfin.groupby("symbol", group_keys=False).apply(_w508_group, include_groups=False)
    out8 = out8.assign(symbol=wide_nonfin["symbol"].values) if "symbol" not in out8.columns else out8

    # W5-06, W5-07 -- full universe (payout-driven concepts, not sector-gated
    # per spec text; see module-level note above)
    out6 = wide.groupby("symbol", group_keys=False).apply(_w506_group, include_groups=False)
    out6 = out6.assign(symbol=wide["symbol"].values) if "symbol" not in out6.columns else out6
    out7 = wide.groupby("symbol", group_keys=False).apply(_w507_group, include_groups=False)
    out7 = out7.assign(symbol=wide["symbol"].values) if "symbol" not in out7.columns else out7

    keep5 = ["symbol", "fiscal_year", "available_date",
             "w505_share", "w505_gate_capex_ok", "w505_gate_payout_ok", "w505_payout_available"]
    keep6 = ["symbol", "fiscal_year", "available_date", "w506_streak", "w506_stress_bonus", "w506_has_data"]
    keep7 = ["symbol", "fiscal_year", "available_date", "w507_penalty_base", "w507_penalty_refine", "w507_cfo_available"]
    keep8 = ["symbol", "fiscal_year", "available_date", "w508_moat"]
    out5 = out5[[c for c in keep5 if c in out5.columns]].dropna(subset=["available_date"])
    out6 = out6[[c for c in keep6 if c in out6.columns]].dropna(subset=["available_date"])
    out7 = out7[[c for c in keep7 if c in out7.columns]].dropna(subset=["available_date"])
    out8 = out8[[c for c in keep8 if c in out8.columns]].dropna(subset=["available_date"])

    merged = out6.merge(out7, on=["symbol", "fiscal_year", "available_date"], how="outer")
    merged = merged.merge(out5, on=["symbol", "fiscal_year", "available_date"], how="outer")
    merged = merged.merge(out8, on=["symbol", "fiscal_year", "available_date"], how="outer")

    _CACHE["annual_v2"] = merged
    _CACHE["diagnostics_v2"] = {
        "n_symbols_before_financials_excl": int(n_before),
        "n_symbols_nonfin": int(n_after),
        "n_annual_rows_w505_share": int(merged["w505_share"].notna().sum()) if "w505_share" in merged else 0,
        "n_annual_rows_w505_payout_available": int(merged["w505_payout_available"].sum()) if "w505_payout_available" in merged else 0,
        "n_annual_rows_w506_has_data": int(merged["w506_has_data"].sum()) if "w506_has_data" in merged else 0,
        "n_annual_rows_w507_cfo_available": int(merged["w507_cfo_available"].sum()) if "w507_cfo_available" in merged else 0,
        "n_annual_rows_w508_moat": int(merged["w508_moat"].notna().sum()) if "w508_moat" in merged else 0,
    }
    return merged


def _asof_v2(panel: pd.DataFrame, value_cols: list) -> pd.DataFrame:
    annual = _annual_factor_table_v2(panel)
    sub = annual[["symbol", "available_date"] + value_cols].copy()
    sub["symbol"] = sub["symbol"].astype(str)
    sub["available_date"] = pd.to_datetime(sub["available_date"]).astype("datetime64[ns]")
    sub = sub.sort_values("available_date")
    p = panel[["date", "symbol"]].drop_duplicates().copy()
    p["symbol"] = p["symbol"].astype(str)
    p["date"] = pd.to_datetime(p["date"]).astype("datetime64[ns]")
    p = p.sort_values("date")
    merged = pd.merge_asof(p, sub.rename(columns={"available_date": "date"}),
                            on="date", by="symbol", direction="backward")
    return merged


def _diagnostic_counts_v2() -> dict:
    return _CACHE.get("diagnostics_v2", {})


# ==========================================================================
# worker-facing builders, W5-05..08 -> Series[(date,symbol)]
# ==========================================================================
def build_w505_base(panel: pd.DataFrame) -> pd.Series:
    """W5-05 BASE: -z(investment share of asset growth), restricted to the
    gated universe (capex-share<0.25 AND payout-not-risen-or-unavailable) --
    i.e. among candidate "diworsifiers", rank by severity of the treasury-
    bloat share and go long the LOW-severity (or non-gated / genuinely
    capex-reinvesting) end. Long LOW bloat."""
    m = _asof_v2(panel, ["w505_share", "w505_gate_capex_ok", "w505_gate_payout_ok"])
    m = m.dropna(subset=["w505_share", "w505_gate_capex_ok"])
    gated = m["w505_gate_capex_ok"].astype(bool) & m["w505_gate_payout_ok"].astype(bool)
    m = m[gated].copy()
    m["neg_share"] = -m["w505_share"]
    m["z"] = BI._zscore_by_date(m[["date", "neg_share"]], "neg_share")
    m = m.dropna(subset=["z"])
    return m.set_index(["date", "symbol"])["z"]


def build_w506_base(panel: pd.DataFrame) -> pd.Series:
    """W5-06 BASE: z_cs(min(streak,10)) + stress_hold_bonus (pre-set +-0.5,
    not fitted). ~750-firm dividend-payout subset (disclosed via diagnostics).
    Long HIGH (persistent payers who held through stress)."""
    m = _asof_v2(panel, ["w506_streak", "w506_stress_bonus", "w506_has_data"])
    m = m[m["w506_has_data"].astype(bool)].copy()
    m = m.dropna(subset=["w506_streak"])
    m["z_streak"] = BI._zscore_by_date(m[["date", "w506_streak"]], "w506_streak")
    m = m.dropna(subset=["z_streak"])
    m["score"] = m["z_streak"] + m["w506_stress_bonus"].fillna(0.0)
    return m.set_index(["date", "symbol"])["score"]


def build_w507_base(panel: pd.DataFrame) -> pd.Series:
    """W5-07 BASE (full-coverage, no CFO condition): -z(borrowing-growth x
    payout-ratio penalty, 0 on non-flagged rows). Long HIGH (=LOW penalty)."""
    m = _asof_v2(panel, ["w507_penalty_base"])
    m = m.dropna(subset=["w507_penalty_base"])
    m["neg_pen"] = -m["w507_penalty_base"]
    m["z"] = BI._zscore_by_date(m[["date", "neg_pen"]], "neg_pen")
    m = m.dropna(subset=["z"])
    return m.set_index(["date", "symbol"])["z"]


def build_w507_refine(panel: pd.DataFrame) -> pd.Series:
    """W5-07 REFINEMENT: adds the CFO-can't-cover condition, CFO-available
    subset only (~750 firms, disclosed)."""
    m = _asof_v2(panel, ["w507_penalty_refine"])
    m = m.dropna(subset=["w507_penalty_refine"])
    m["neg_pen"] = -m["w507_penalty_refine"]
    m["z"] = BI._zscore_by_date(m[["date", "neg_pen"]], "neg_pen")
    m = m.dropna(subset=["z"])
    return m.set_index(["date", "symbol"])["z"]


def build_w508_base(panel: pd.DataFrame) -> pd.Series:
    """W5-08 BASE: z_cs(median(opm%,5Y) - IQR(opm%,5Y)), lambda=1. Long HIGH
    (persistent high-margin = moat proxy)."""
    m = _asof_v2(panel, ["w508_moat"])
    m = m.dropna(subset=["w508_moat"])
    m["z"] = BI._zscore_by_date(m[["date", "w508_moat"]], "w508_moat")
    m = m.dropna(subset=["z"])
    return m.set_index(["date", "symbol"])["z"]
