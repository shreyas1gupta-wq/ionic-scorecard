"""
WAVE-2 event-driven (earnings) factor builders for ALPHA_RANKER.
Worker: W2 money-first loop. PIT discipline: every factor value at panel date t
uses only quarterly prints whose available_date <= t (drift-window gated where
the hypothesis is event-window-specific).

Hypotheses:
  (a) W2_event_pead_sign      — sign of earnings surprise (actual net-profit vs
                                 own trailing-4Q-trend expectation) -> forward
                                 drift. Bernard-Thomas PEAD.
  (b) W2_event_gapcont        — sign of the results-day price reaction (2-day
                                 close-to-close return spanning the announcement)
                                 -> forward continuation of that reaction.
  (c) W2_event_accel          — QoQ acceleration of YoY sales & net-profit growth
                                 (this quarter's YoY minus the prior quarter's YoY).

Data:
  - ALPHA_RANKER/data/fundamentals/consolidated/quarterly_results.parquet
        LONG (symbol, metric, period[[Mon YYYY]], value). NO available_date column
        at all (CLAUDE.md landmine) -> PIT date is built here, not read off the file.
  - datasets/nse_earnings_dates/earnings_dates.csv (repo root)
        Real NSE board-meeting/result-broadcast dates, purpose column. Filtered to
        purpose.startswith("Financial Results"). Matched forward (merge_asof,
        tolerance 120d) to each quarter's period-end -> the ACTUAL public date for
        that print, when available (~most symbols/quarters; see coverage note in
        the run report). Where no real date exists within tolerance: conservative
        fallback available_date = period_end + 45 calendar days (matches the task
        brief's own "public ~45d after quarter-end" convention) - flagged
        `date_source` = 'actual' vs 'fallback_45d', never silently blended.
  - ALPHA_RANKER/rnd/panel/cube_close.parquet
        date x symbol adjusted-close matrix, used ONLY for the gap-continuation
        leg, and ONLY on rows with an ACTUAL earnings_dates.csv match (a fallback
        +45d date carries no informative price-reaction day to measure).

All PIT joins are merge_asof(direction='backward') of the panel rebalance date t
against `available_date`: nothing after t is ever read into a factor value at t.
"""
from __future__ import annotations
from pathlib import Path

import numpy as np
import pandas as pd

_LIB_DIR = Path(__file__).resolve().parent
ALPHA_ROOT = _LIB_DIR.parents[1]          # .../ALPHA_RANKER
REPO_ROOT = ALPHA_ROOT.parent             # .../NIFTY 500

QR_PATH = ALPHA_ROOT / "data/fundamentals/consolidated/quarterly_results.parquet"
ED_PATH = REPO_ROOT / "datasets/nse_earnings_dates/earnings_dates.csv"
CUBE_CLOSE_PATH = ALPHA_ROOT / "rnd/panel/cube_close.parquet"

FALLBACK_LAG_DAYS = 45  # [INFERENCE] conservative PIT lag, disclosed, matches task brief


# ==========================================================================
# 0. helpers (self-contained; mirrors the pattern in builders_growth.py)
# ==========================================================================
def _asof_join(panel_ds: pd.DataFrame, right: pd.DataFrame, right_time_col: str) -> pd.DataFrame:
    """panel_ds: unique (date,symbol) pairs. right: has 'symbol', right_time_col,
    value cols. Returns panel_ds matched to the latest right row per symbol with
    right_time_col <= date (backward asof) -> no lookahead."""
    left = panel_ds[["date", "symbol"]].drop_duplicates().sort_values(["date", "symbol"]).reset_index(drop=True)
    left = left.assign(date=pd.to_datetime(left["date"]).astype("datetime64[ns]"), symbol=left["symbol"].astype(str))
    r = right.rename(columns={right_time_col: "_asof_time"}).sort_values(["_asof_time", "symbol"]).reset_index(drop=True)
    r = r.assign(_asof_time=pd.to_datetime(r["_asof_time"]).astype("datetime64[ns]"), symbol=r["symbol"].astype(str))
    out = pd.merge_asof(left.sort_values("date"), r, left_on="date", right_on="_asof_time",
                         by="symbol", direction="backward")
    return out


def _zscore_by_date(df: pd.DataFrame, col: str) -> pd.Series:
    def _z(g):
        v = g[col].astype(float)
        lo, hi = v.quantile(0.01), v.quantile(0.99)
        v = v.clip(lo, hi)
        sd = v.std(ddof=0)
        if not sd or np.isnan(sd) or sd == 0:
            return pd.Series(np.nan, index=g.index)
        return (v - v.mean()) / sd
    return df.groupby("date", group_keys=False).apply(_z, include_groups=False)


def _period_to_end(period: pd.Series) -> pd.Series:
    return pd.to_datetime(period, format="%b %Y") + pd.offsets.MonthEnd(0)


# ==========================================================================
# 1. quarterly PIT build: quarterly_results.parquet + earnings_dates.csv
# ==========================================================================
_QTR_CACHE = None


def _load_earnings_dates() -> pd.DataFrame:
    ed = pd.read_csv(ED_PATH)
    ed = ed[ed["purpose"].str.startswith("Financial Results", na=False)].copy()
    ed["date"] = pd.to_datetime(ed["date"], format="%d-%b-%Y", errors="coerce")
    ed = ed.dropna(subset=["date"])
    ed = ed[["symbol", "date"]].drop_duplicates().sort_values(["symbol", "date"]).reset_index(drop=True)
    return ed


def load_quarterly_pit() -> pd.DataFrame:
    """Wide (symbol, period_end) quarterly panel with a genuinely-built PIT
    available_date, YoY growth, QoQ acceleration, and own-4Q-trend surprise.
    Cached module-level (read-only build, called repeatedly by the 3 builders)."""
    global _QTR_CACHE
    if _QTR_CACHE is not None:
        return _QTR_CACHE

    qr = pd.read_parquet(QR_PATH)
    qr = qr[qr["metric"].isin(["Sales", "Net Profit", "EPS in Rs"])]
    piv = qr.pivot_table(index=["symbol", "period"], columns="metric", values="value", aggfunc="last").reset_index()
    piv = piv.rename(columns={"Sales": "sales", "Net Profit": "net_profit", "EPS in Rs": "eps"})
    piv["period_end"] = _period_to_end(piv["period"])
    piv = piv.sort_values(["symbol", "period_end"]).reset_index(drop=True)

    # actual public date via nearest-FORWARD earnings_dates.csv match (a result
    # can only be public on/after its own period_end); fallback = +45d if none
    # within 120 calendar days (covers ~long delayed filers, rare).
    ed = _load_earnings_dates()
    m = pd.merge_asof(piv.sort_values("period_end"), ed.sort_values("date"),
                       left_on="period_end", right_on="date", by="symbol",
                       direction="forward", tolerance=pd.Timedelta(days=120))
    m["date_source"] = np.where(m["date"].notna(), "actual", "fallback_45d")
    m["available_date"] = m["date"].fillna(m["period_end"] + pd.Timedelta(days=FALLBACK_LAG_DAYS))
    m = m.drop(columns=["date"]).sort_values(["symbol", "period_end"]).reset_index(drop=True)

    # same-quarter-prior-year match (nearest, tolerance 45d around exactly -365d)
    m["q_target"] = m["period_end"] - pd.DateOffset(days=365)
    prior = m[["symbol", "period_end", "sales", "net_profit"]].rename(
        columns={"period_end": "q_prior_end", "sales": "sales_py", "net_profit": "np_py"})
    m = pd.merge_asof(m.sort_values("q_target"), prior.sort_values("q_prior_end"),
                       left_on="q_target", right_on="q_prior_end", by="symbol",
                       direction="nearest", tolerance=pd.Timedelta(days=45))
    m = m.sort_values(["symbol", "period_end"]).reset_index(drop=True)

    m["sales_yoy"] = np.where(m["sales_py"] > 0, m["sales"] / m["sales_py"] - 1, np.nan)
    m["np_yoy"] = np.where(m["np_py"] > 0, m["net_profit"] / m["np_py"] - 1, np.nan)
    m["sales_yoy_accel"] = m.groupby("symbol")["sales_yoy"].diff()
    m["np_yoy_accel"] = m.groupby("symbol")["np_yoy"].diff()

    # own-4Q-trend PEAD expectation: same-q-last-year grown by the trailing avg
    # YoY of the preceding (already-known, current print EXCLUDED) 4 quarters
    m["np_yoy_trail_avg"] = m.groupby("symbol")["np_yoy"].transform(
        lambda s: s.shift(1).rolling(4, min_periods=2).mean())
    m["np_expected"] = m["np_py"] * (1 + m["np_yoy_trail_avg"])
    m["np_surprise"] = np.where(m["np_expected"].abs() > 0,
                                 (m["net_profit"] - m["np_expected"]) / m["np_expected"].abs(), np.nan)
    m["np_surprise_sign"] = np.sign(m["np_surprise"])

    _QTR_CACHE = m
    return _QTR_CACHE


# ==========================================================================
# 2. gap-continuation price leg (cube_close, ACTUAL-date rows only)
# ==========================================================================
_CUBE_CACHE = None


def _load_cube():
    global _CUBE_CACHE
    if _CUBE_CACHE is None:
        _CUBE_CACHE = pd.read_parquet(CUBE_CLOSE_PATH)
    return _CUBE_CACHE


def _event_gap_sign(actual_rows: pd.DataFrame) -> pd.Series:
    """actual_rows: symbol, available_date (real dates only). Returns sign of the
    2-trading-day close-to-close return spanning the announcement (t-1 -> t+1
    trading day around the real event date), a proxy for the market's initial
    reaction regardless of before/after-hours release timing.
    [INFERENCE]: exact intraday release timing is not in the data; the 2-day
    window is symmetric so it does not assume before- or after-market release."""
    cube = _load_cube()
    idx = cube.index
    vals = cube.to_numpy()
    col_pos = pd.Series(np.arange(cube.shape[1]), index=cube.columns)

    dt_arr = pd.DatetimeIndex(actual_rows["available_date"])
    event_pos = idx.searchsorted(dt_arr)  # first trading day >= available_date
    sym_ok = actual_rows["symbol"].isin(col_pos.index).to_numpy()
    cidx = np.where(sym_ok, col_pos.reindex(actual_rows["symbol"]).fillna(-1).to_numpy().astype(int), -1)

    n = len(idx)
    before_pos = np.clip(event_pos - 1, 0, n - 1)
    after_pos = np.clip(event_pos + 1, 0, n - 1)
    valid = sym_ok & (cidx >= 0) & (event_pos > 0) & (event_pos < n - 1)

    out = np.full(len(actual_rows), np.nan)
    idxs = np.where(valid)[0]
    if len(idxs):
        c_before = vals[before_pos[idxs], cidx[idxs]]
        c_after = vals[after_pos[idxs], cidx[idxs]]
        with np.errstate(invalid="ignore", divide="ignore"):
            gap = np.where(c_before > 0, c_after / c_before - 1, np.nan)
        out[idxs] = gap
    return pd.Series(np.sign(out), index=actual_rows.index)


# ==========================================================================
# 3. the three W2 event factors
# ==========================================================================
def build_w2_event_pead_sign(panel_df: pd.DataFrame, drift_window_days: int = 45) -> pd.Series:
    """(a) PEAD: sign of the earnings surprise (own-4Q-trend expectation),
    active only inside the post-earnings drift window [0, drift_window_days]."""
    q = load_quarterly_pit()
    q = q.dropna(subset=["np_surprise_sign"])
    ds = panel_df[["date", "symbol"]].drop_duplicates()
    m = _asof_join(ds, q[["symbol", "available_date", "np_surprise_sign"]], "available_date")
    m["days_since_release"] = (m["date"] - m["_asof_time"]).dt.days
    m = m[(m["days_since_release"] >= 0) & (m["days_since_release"] <= drift_window_days)]
    m = m.dropna(subset=["np_surprise_sign"])
    return m.set_index(["date", "symbol"])["np_surprise_sign"]


def build_w2_event_gapcont(panel_df: pd.DataFrame, drift_window_days: int = 45) -> pd.Series:
    """(b) results-day gap-continuation: sign of the announcement-day price
    reaction, active only inside the drift window. ACTUAL earnings_dates.csv
    rows only (fallback +45d dates have no real event day to measure a gap on)."""
    q = load_quarterly_pit()
    actual = q[q["date_source"] == "actual"][["symbol", "available_date"]].drop_duplicates().reset_index(drop=True)
    actual["gap_sign"] = _event_gap_sign(actual)
    actual = actual.dropna(subset=["gap_sign"])

    ds = panel_df[["date", "symbol"]].drop_duplicates()
    m = _asof_join(ds, actual[["symbol", "available_date", "gap_sign"]], "available_date")
    m["days_since_release"] = (m["date"] - m["_asof_time"]).dt.days
    m = m[(m["days_since_release"] >= 0) & (m["days_since_release"] <= drift_window_days)]
    m = m.dropna(subset=["gap_sign"])
    return m.set_index(["date", "symbol"])["gap_sign"]


def build_w2_event_accel(panel_df: pd.DataFrame) -> pd.Series:
    """(c) revision/acceleration: z-scored blend of sales & net-profit YoY
    acceleration (this quarter's YoY minus the prior quarter's YoY). Persistent
    factor (no drift-window gate) -- the "latest known" acceleration level,
    not an event-only signal, per FRAMEWORK_CATALOG's 1M-3M framing."""
    q = load_quarterly_pit()
    ds = panel_df[["date", "symbol"]].drop_duplicates()
    m = _asof_join(ds, q[["symbol", "available_date", "sales_yoy_accel", "np_yoy_accel"]], "available_date")
    m["z_sales"] = _zscore_by_date(m[["date", "sales_yoy_accel"]], "sales_yoy_accel")
    m["z_np"] = _zscore_by_date(m[["date", "np_yoy_accel"]], "np_yoy_accel")
    m["factor"] = m[["z_sales", "z_np"]].mean(axis=1, skipna=True)
    m = m.dropna(subset=["factor"])
    return m.set_index(["date", "symbol"])["factor"]
