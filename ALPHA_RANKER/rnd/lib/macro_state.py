"""
Macro / rates / inflation regime feature -- India + US -- for the ALPHA_RANKER
WAVE money-first loop. NOT a cross-sectional stock factor (macro is the same
value for every symbol at a given date, so harness.evaluate()'s cross-sectional
IC machinery does not apply here). Instead this builds a monthly macro-state
panel and tests whether the regime CONDITIONS forward NIFTY 500 market returns,
expanding-window, no lookahead.

[DATA] = read from disk. [INFERENCE] = a construction choice, disclosed inline.
[OPINION] = a forecast/judgement call, tagged per firm protocol.

Sources used (all already on disk -- verified before use, see build() docstring):
  - datasets/index_daily/nifty500.parquet         India equity market (target)
  - datasets/index_daily/india_vix.parquet        India vol regime
  - Shreyas_Ionic_AMC/05_DATA_OFFICE/data/usdinr_fred_daily.parquet   USDINR (FRED, verified 2026-07-13)
  - Shreyas_Ionic_AMC/05_DATA_OFFICE/data/us_treasury_yields_daily.parquet  US yield curve (official, home.treasury.gov)
  - Shreyas_Ionic_AMC/05_DATA_OFFICE/data/cboe_vix_daily.parquet     US vol regime
  - datasets/etf_gold_silver/goldbees_daily.parquet  Gold-vs-equity (INR ETF proxy, more current than XAUUSD 1-min which stops 2025-12-31)

PARKED (not available on this proxy -- do NOT fabricate):
  - India 10Y G-sec yield: no series found anywhere on disk; FRED (INDIRLTLT01INM-class) and
    stooq (10yiny.b) both blocked (stooq now serves a JS proof-of-work challenge, not CSV --
    verified 2026-07-17). Home-network / RBI DBIE fetch needed.
  - Brent crude: no series found on disk; stooq blocked same as above.
  - DXY (dollar index): no series found on disk; stooq blocked same as above.
  - India CPI/WPI (for a real-rate proxy): no series found on disk. Without it, real_rate_proxy
    is left NaN rather than approximated off a US-only breakeven (would silently mix regimes).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent              # ALPHA_RANKER/rnd
ALPHA_DIR = RND_DIR.parent                 # ALPHA_RANKER
REPO_ROOT = ALPHA_DIR.parent               # NIFTY 500 repo root

NIFTY500_FP = REPO_ROOT / "datasets" / "index_daily" / "nifty500.parquet"
INDIA_VIX_FP = REPO_ROOT / "datasets" / "index_daily" / "india_vix.parquet"
GOLDBEES_FP = REPO_ROOT / "datasets" / "etf_gold_silver" / "goldbees_daily.parquet"
USDINR_FP = REPO_ROOT / "Shreyas_Ionic_AMC" / "05_DATA_OFFICE" / "data" / "usdinr_fred_daily.parquet"
US_YIELDS_FP = REPO_ROOT / "Shreyas_Ionic_AMC" / "05_DATA_OFFICE" / "data" / "us_treasury_yields_daily.parquet"
US_VIX_FP = REPO_ROOT / "Shreyas_Ionic_AMC" / "05_DATA_OFFICE" / "data" / "cboe_vix_daily.parquet"

OUT_FP = RND_DIR / "panel" / "macro_state.parquet"


def _ist_date(ts: pd.Series) -> pd.Series:
    """Fix the HF/ETF timezone bug (landmine #1): tz-aware UTC timestamps
    stamped 18:30 = next-day 00:00 IST. Convert to Asia/Kolkata THEN take the
    date, never take the date off the raw UTC/naive timestamp."""
    ts = pd.to_datetime(ts)
    if ts.dt.tz is None:
        # index_daily files carry "+05:30" already in the string; if naive,
        # assume already IST (no conversion needed).
        return ts.dt.date
    return ts.dt.tz_convert("Asia/Kolkata").dt.date


def _load_index_close(fp: Path, col: str) -> pd.Series:
    d = pd.read_parquet(fp)
    d["date"] = _ist_date(d["timestamp"])
    d["date"] = pd.to_datetime(d["date"])
    s = d.groupby("date")["close"].last().sort_index()
    s.name = col
    return s


def _month_end_reindex(daily: pd.Series, month_ends: pd.DatetimeIndex) -> pd.Series:
    """merge_asof-backward onto the target month-end calendar -- nearest PRIOR
    daily obs as of each month-end, no future leak."""
    name = daily.name
    daily = daily.sort_index()
    left = pd.DataFrame({"date": pd.to_datetime(month_ends).astype("datetime64[ns]")})
    right = daily.rename("v").reset_index()
    right.columns = ["date", "v"]
    right["date"] = pd.to_datetime(right["date"]).astype("datetime64[ns]")
    right = right.sort_values("date")
    out = pd.merge_asof(left, right, on="date", direction="backward")
    out = out.set_index("date")["v"]
    out.name = name
    return out


def build(write: bool = True) -> pd.DataFrame:
    # ---- India equity market (drives the month-end calendar + is the test target)
    nifty500 = _load_index_close(NIFTY500_FP, "nifty500")
    month_ends = nifty500.groupby(pd.PeriodIndex(nifty500.index, freq="M")).apply(lambda s: s.index.max())
    month_ends = pd.DatetimeIndex(sorted(month_ends.values))

    nifty500_me = _month_end_reindex(nifty500, month_ends)

    # ---- India VIX (vol regime)
    ivix_daily = _load_index_close(INDIA_VIX_FP, "india_vix")
    india_vix = _month_end_reindex(ivix_daily, month_ends)

    # ---- Gold (INR ETF proxy, more current than XAUUSD 1-min)
    gb = pd.read_parquet(GOLDBEES_FP)
    gb["date"] = pd.to_datetime(_ist_date(gb["timestamp"]))
    goldbees_daily = gb.groupby("date")["close"].last().sort_index()
    goldbees_me = _month_end_reindex(goldbees_daily, month_ends)

    # ---- USDINR (FRED, verified 2026-07-13)
    usdinr = pd.read_parquet(USDINR_FP)
    usdinr["date"] = pd.to_datetime(usdinr["date"])
    usdinr_daily = usdinr.set_index("date")["usdinr"].sort_index()
    usdinr_me = _month_end_reindex(usdinr_daily, month_ends)

    # ---- US treasury yield curve (official home.treasury.gov)
    usy = pd.read_parquet(US_YIELDS_FP)
    usy["date"] = pd.to_datetime(usy["Date"])
    us10y_daily = usy.set_index("date")["10 Yr"].sort_index()
    us2y_daily = usy.set_index("date")["2 Yr"].sort_index()
    us10y_me = _month_end_reindex(us10y_daily, month_ends)
    us2y_me = _month_end_reindex(us2y_daily, month_ends)

    # ---- US VIX (CBOE, global risk-off proxy)
    uvix = pd.read_parquet(US_VIX_FP)
    uvix["date"] = pd.to_datetime(uvix["DATE"])
    usvix_daily = uvix.set_index("date")["CLOSE"].sort_index()
    us_vix_me = _month_end_reindex(usvix_daily, month_ends)

    df = pd.DataFrame({
        "date": month_ends,
        "nifty500": nifty500_me.values,
        "india_vix": india_vix.values,
        "goldbees": goldbees_me.values,
        "usdinr": usdinr_me.values,
        "us10y": us10y_me.values,
        "us2y": us2y_me.values,
        "us_vix": us_vix_me.values,
    }).set_index("date")

    # ---- Parked columns, left NaN, never fabricated
    df["india10y"] = np.nan          # PARKED -- no source on disk, stooq/FRED blocked
    df["brent"] = np.nan             # PARKED -- no source on disk, stooq blocked
    df["dxy"] = np.nan               # PARKED -- no source on disk, stooq blocked
    df["real_rate_proxy"] = np.nan   # PARKED -- needs India CPI, none on disk

    # ---- Derived, all using ONLY data <= t (trailing windows, no lookahead)
    df["nifty500_ret_1m"] = df["nifty500"].pct_change(1)
    df["goldbees_ret_1m"] = df["goldbees"].pct_change(1)
    df["gold_vs_equity_1m"] = df["goldbees_ret_1m"] - df["nifty500_ret_1m"]

    df["us10y_chg_3m"] = df["us10y"].diff(3)                     # trailing 3M change in level (pp)
    df["term_spread_us"] = df["us10y"] - df["us2y"]              # 10Y-2Y, classic recession-signal spread
    df["usdinr_chg_3m"] = df["usdinr"].pct_change(3)             # trailing 3M INR depreciation trend

    # rate_regime: sign of trailing 3M US10Y change -- known at t, no lookahead
    df["rate_regime"] = np.where(df["us10y_chg_3m"] > 0, "rising",
                          np.where(df["us10y_chg_3m"] < 0, "falling", "flat"))

    # risk_regime: India VIX tercile band using an EXPANDING window up to and
    # including t (no full-sample lookahead) -- min 12 obs before banding starts.
    def _expanding_tercile(s: pd.Series) -> pd.Series:
        out = pd.Series(index=s.index, dtype=object)
        for i in range(len(s)):
            if i < 12 or pd.isna(s.iloc[i]):
                out.iloc[i] = np.nan
                continue
            hist = s.iloc[: i + 1].dropna()
            q1, q2 = hist.quantile([1 / 3, 2 / 3])
            v = s.iloc[i]
            out.iloc[i] = "low" if v <= q1 else ("high" if v >= q2 else "mid")
        return out

    df["risk_regime"] = _expanding_tercile(df["india_vix"])

    # inr_regime: sign of trailing 3M USDINR % change
    df["inr_regime"] = np.where(df["usdinr_chg_3m"] > 0, "depreciating",
                         np.where(df["usdinr_chg_3m"] < 0, "appreciating", "flat"))

    # ---- Forward targets (t -> t+h on this month-end calendar; NaN if beyond history)
    df["fwd_ret_nifty500_1M"] = df["nifty500"].shift(-1) / df["nifty500"] - 1
    df["fwd_ret_nifty500_1Y"] = df["nifty500"].shift(-12) / df["nifty500"] - 1

    df = df.reset_index()

    if write:
        OUT_FP.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(OUT_FP, index=False)

    return df


if __name__ == "__main__":
    out = build(write=True)
    print(f"macro_state.parquet: {out.shape[0]} month-ends, {out['date'].min()} -> {out['date'].max()}")
    print(out.tail(6).to_string())
