"""
Worker builders for H029/H030/H046/H048 (interaction & neutralization diagnostics).
Simple, PIT-safe constituent factors built from MASTER_fundamentals_pit.parquet
(fundamentals) and rnd/panel/cube_close.parquet + cube_bench.parquet (price/mkt),
combined per RESEARCH_PROTOCOL.md into interaction factors, evaluated via
rnd/lib/harness.py. No lookahead: fundamentals gated on available_date<=t
(merge_asof backward), momentum built from price bars <= t only.
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
CUBE_BENCH_PATH = RND_DIR / "panel" / "cube_bench.parquet"

_fund_cache = {}


def _load_metric_asof(metric_norm: str, panel_dates_by_symbol: pd.DataFrame) -> pd.Series:
    """PIT as-of join: latest `value` for `metric_norm` with available_date <= date,
    per symbol. panel_dates_by_symbol: DataFrame with columns date,symbol (unique).
    Returns a Series indexed like the input (aligned by position)."""
    if metric_norm not in _fund_cache:
        df = pd.read_parquet(FUND_PATH, columns=["nse_symbol", "metric_norm", "value", "available_date"])
        d = df[df["metric_norm"] == metric_norm].dropna(subset=["value", "available_date"])
        d = d.rename(columns={"nse_symbol": "symbol", "available_date": "date"})
        d["date"] = pd.to_datetime(d["date"]).astype("datetime64[ns]")
        d = d.sort_values(["symbol", "date"])
        # de-dup: keep last value per (symbol,date) if restated
        d = d.drop_duplicates(subset=["symbol", "date"], keep="last")
        _fund_cache[metric_norm] = d[["symbol", "date", "value"]]
    d = _fund_cache[metric_norm]

    left = panel_dates_by_symbol.copy()
    left["date"] = pd.to_datetime(left["date"]).astype("datetime64[ns]")
    left = left.sort_values(["symbol", "date"]).reset_index(drop=True)
    out_parts = []
    for sym, g in left.groupby("symbol"):
        dsym = d[d["symbol"] == sym]
        if dsym.empty:
            g = g.copy()
            g["value"] = np.nan
            out_parts.append(g)
            continue
        merged = pd.merge_asof(g.sort_values("date"), dsym.sort_values("date")[["date", "value"]],
                                on="date", direction="backward")
        merged["symbol"] = sym
        out_parts.append(merged)
    res = pd.concat(out_parts, ignore_index=True)
    return res


def _panel_dates_symbols(panel: pd.DataFrame) -> pd.DataFrame:
    return panel[["date", "symbol"]].drop_duplicates().copy()


# --------------------------------------------------------------------------
# constituent factors
# --------------------------------------------------------------------------
def quality_roic_proxy(panel: pd.DataFrame) -> pd.Series:
    """Quality proxy: latest annual operating profit / total assets, PIT
    (available_date<=t). Novy-Marx-style asset-based profitability — the
    closest cheap ROIC proxy available from this metric set (no COGS/invested-
    capital breakdown on file)."""
    ds = _panel_dates_symbols(panel)
    op = _load_metric_asof("operating profit", ds).rename(columns={"value": "op"})
    ta = _load_metric_asof("total assets", ds).rename(columns={"value": "ta"})
    m = op.merge(ta[["date", "symbol", "ta"]], on=["date", "symbol"], how="inner")
    m["factor"] = m["op"] / m["ta"].replace(0, np.nan)
    m = m.replace([np.inf, -np.inf], np.nan).dropna(subset=["factor"])
    return m.set_index(["date", "symbol"])["factor"]


def value_earnings_yield(panel: pd.DataFrame) -> pd.Series:
    """Value proxy: latest annual EPS (PIT) / price at t (from cube_close)."""
    ds = _panel_dates_symbols(panel)
    eps = _load_metric_asof("eps in rs", ds).rename(columns={"value": "eps"})
    px = pd.read_parquet(CUBE_CLOSE_PATH)
    px.index = pd.to_datetime(px.index)
    rows = []
    for d, g in eps.groupby("date"):
        if d not in px.index:
            # nearest available bar <= d
            idx = px.index[px.index <= d]
            if len(idx) == 0:
                continue
            d_px = idx.max()
        else:
            d_px = d
        prow = px.loc[d_px]
        for sym, e in zip(g["symbol"], g["eps"]):
            p = prow.get(sym, np.nan)
            if pd.isna(p) or p <= 0 or pd.isna(e):
                continue
            rows.append({"date": d, "symbol": sym, "factor": e / p})
    out = pd.DataFrame(rows)
    return out.set_index(["date", "symbol"])["factor"]


def growth_sales_yoy(panel: pd.DataFrame) -> pd.Series:
    """Growth proxy: latest annual sales YoY growth, PIT (two most-recent
    available_date<=t annual filings for the same symbol)."""
    df = pd.read_parquet(FUND_PATH, columns=["nse_symbol", "metric_norm", "value", "available_date"])
    d = df[df["metric_norm"] == "sales"].dropna(subset=["value", "available_date"])
    d = d.rename(columns={"nse_symbol": "symbol", "available_date": "date"})
    d["date"] = pd.to_datetime(d["date"]).astype("datetime64[ns]")
    d = d.sort_values(["symbol", "date"]).drop_duplicates(subset=["symbol", "date"], keep="last")
    d["yoy"] = d.groupby("symbol")["value"].pct_change()
    d = d.dropna(subset=["yoy"])
    ds = _panel_dates_symbols(panel)
    ds = ds.copy()
    ds["date"] = pd.to_datetime(ds["date"]).astype("datetime64[ns]")
    out_parts = []
    for sym, g in ds.groupby("symbol"):
        dsym = d[d["symbol"] == sym]
        if dsym.empty:
            continue
        merged = pd.merge_asof(g.sort_values("date"), dsym.sort_values("date")[["date", "yoy"]],
                                on="date", direction="backward")
        merged["symbol"] = sym
        out_parts.append(merged)
    res = pd.concat(out_parts, ignore_index=True).dropna(subset=["yoy"])
    res = res.rename(columns={"yoy": "factor"})
    return res.set_index(["date", "symbol"])["factor"]


def residual_momentum_12_1(panel: pd.DataFrame) -> pd.Series:
    """12-1 residual momentum: raw trailing 252d return skipping last 21d,
    minus beta_252(t) (known at t, from the panel) times the market's
    matching-window trailing return (NIFTY 50 index, cube_bench.parquet).
    No lookahead: both legs use price bars strictly <= t."""
    px = pd.read_parquet(CUBE_CLOSE_PATH)
    px.index = pd.to_datetime(px.index)
    bench = pd.read_parquet(CUBE_BENCH_PATH)
    bench.index = pd.to_datetime(bench.index)
    mkt = bench["NSEI"]

    dates = sorted(panel["date"].unique())
    beta_map = panel.set_index(["date", "symbol"])["beta_252"]
    rows = []
    for d in dates:
        d = pd.Timestamp(d)
        idx = px.index[px.index <= d]
        if len(idx) < 253:
            continue
        loc = px.index.get_loc(idx.max())
        p_t21 = px.iloc[loc - 21]
        p_t252 = px.iloc[loc - 252]
        raw_mom = p_t21 / p_t252 - 1.0
        m_t21 = mkt.iloc[mkt.index.get_loc(idx.max()) - 21] if len(mkt.index[mkt.index <= d]) >= 253 else np.nan
        m_loc = mkt.index[mkt.index <= d]
        if len(m_loc) < 253:
            continue
        mloc = mkt.index.get_loc(m_loc.max())
        mkt_mom = mkt.iloc[mloc - 21] / mkt.iloc[mloc - 252] - 1.0
        for sym, val in raw_mom.dropna().items():
            beta = beta_map.get((d, sym), np.nan)
            beta_use = 1.0 if pd.isna(beta) else beta
            resid = val - beta_use * mkt_mom
            rows.append({"date": d, "symbol": sym, "factor": resid})
    out = pd.DataFrame(rows)
    return out.set_index(["date", "symbol"])["factor"]


# --------------------------------------------------------------------------
# helpers: cross-sectional rank + interaction combine
# --------------------------------------------------------------------------
def _xs_rank(s: pd.Series) -> pd.Series:
    """Per-date cross-sectional percentile rank in (0,1)."""
    df = s.rename("v").reset_index()
    df["r"] = df.groupby("date")["v"].rank(pct=True)
    return df.set_index(["date", "symbol"])["r"]


def interact_product(a: pd.Series, b: pd.Series) -> pd.Series:
    """Rank-product interaction: cross-sectional percentile ranks of each
    parent, centered on 0, multiplied (double-sort proxy)."""
    ra = _xs_rank(a) - 0.5
    rb = _xs_rank(b) - 0.5
    df = pd.concat([ra.rename("ra"), rb.rename("rb")], axis=1).dropna()
    return (df["ra"] * df["rb"]).rename("factor")


# --------------------------------------------------------------------------
# H029: quality x momentum
# --------------------------------------------------------------------------
def h029_quality(panel):
    return quality_roic_proxy(panel)


def h029_momentum(panel):
    return residual_momentum_12_1(panel)


def h029_interaction(panel):
    q = quality_roic_proxy(panel)
    m = residual_momentum_12_1(panel)
    return interact_product(q, m)


# --------------------------------------------------------------------------
# H030: value x quality (QARP)
# --------------------------------------------------------------------------
def h030_value(panel):
    return value_earnings_yield(panel)


def h030_quality(panel):
    return quality_roic_proxy(panel)


def h030_interaction(panel):
    v = value_earnings_yield(panel)
    q = quality_roic_proxy(panel)
    return interact_product(v, q)


# --------------------------------------------------------------------------
# H046: growth-at-reasonable-price (EY x growth)
# --------------------------------------------------------------------------
def h046_ey(panel):
    return value_earnings_yield(panel)


def h046_growth(panel):
    return growth_sales_yoy(panel)


def h046_interaction(panel):
    ey = value_earnings_yield(panel)
    g = growth_sales_yoy(panel)
    return interact_product(ey, g)


# --------------------------------------------------------------------------
# H048: sector-neutral vs sector-tilted diagnostic
# --------------------------------------------------------------------------
def sector_demean(factor: pd.Series, panel: pd.DataFrame) -> pd.Series:
    """Demean a factor within (date, sector) using panel['sector']."""
    df = factor.rename("v").reset_index()
    sec = panel[["date", "symbol", "sector"]].drop_duplicates()
    df = df.merge(sec, on=["date", "symbol"], how="inner")
    df["v_demeaned"] = df["v"] - df.groupby(["date", "sector"])["v"].transform("mean")
    return df.set_index(["date", "symbol"])["v_demeaned"].rename("factor")


def sector_variance_share(factor: pd.Series, panel: pd.DataFrame) -> float:
    """Fraction of cross-sectional variance of `factor` explained by sector
    membership (per-date sector-dummy R^2, averaged across dates) — 'how
    much of the score is a sector bet'."""
    df = factor.rename("v").reset_index()
    sec = panel[["date", "symbol", "sector"]].drop_duplicates()
    df = df.merge(sec, on=["date", "symbol"], how="inner")
    r2s = []
    for d, g in df.groupby("date"):
        if g["sector"].nunique() < 2 or len(g) < 20:
            continue
        total_var = g["v"].var(ddof=0)
        if not total_var or np.isnan(total_var):
            continue
        within = g.groupby("sector")["v"].transform("var", ddof=0)
        counts = g.groupby("sector")["v"].transform("count")
        # between-sector variance share = 1 - (mean within-group var weighted)/total_var
        grp_means = g.groupby("sector")["v"].transform("mean")
        between_var = ((grp_means - g["v"].mean()) ** 2).mean()
        r2 = between_var / total_var if total_var > 0 else np.nan
        r2s.append(r2)
    return float(np.mean(r2s)) if r2s else float("nan")


def h048_quality_raw(panel):
    return quality_roic_proxy(panel)


def h048_quality_sector_neutral(panel):
    q = quality_roic_proxy(panel)
    return sector_demean(q, panel)


def h048_momentum_raw(panel):
    return residual_momentum_12_1(panel)


def h048_momentum_sector_neutral(panel):
    m = residual_momentum_12_1(panel)
    return sector_demean(m, panel)
