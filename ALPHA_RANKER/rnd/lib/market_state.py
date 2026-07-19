"""
market_state.py -- Market-state / valuation-breadth layer (WAVE-2 worker, ALPHA_RANKER).

Builds:
  rnd/panel/market_state.parquet   -- ONE ROW PER MONTH-END DATE, market & cap-tier
                                       valuation aggregates + regime/vol/breadth.
  rnd/panel/stock_valuation_pit.parquet -- ONE ROW PER (date, symbol): per-stock PIT
                                       EY/PE/PB + cap_pct_rank + cap_tier, i.e. the
                                       per-stock feature companion needed for M3
                                       ("stock's valuation vs its cap-tier + market state").

NO LOOKAHEAD, by construction:
  - Fundamentals (net profit, equity capital, reserves) are joined per symbol via
    merge_asof(direction='backward') on available_date <= date -- the PIT contract
    already enforced by MASTER_fundamentals_pit.parquet (Data Officer gate).
  - mktcap = exp(mktcap_log) is panel_long's own PIT market-cap proxy
    (shares_proxy [current-snapshot, CONSTANT across history -- same caveat as the
    rest of the codebase, see PANEL_SCHEMA.md] x AdjClose(t)); no future price used.
  - Cap-tier bucketing is a CROSS-SECTIONAL PERCENTILE RANK computed independently
    at each date (no absolute rupee threshold, no full-sample lookahead: the rank is
    relative to the OTHER NAMES PRESENT AT THAT SAME DATE only).
  - EY_hist_zscore_expanding uses pandas .expanding() up to and including t --
    strictly uses only (t' <= t) observations of the market's OWN EY series, never
    a full-sample mean/std.
  - market_vol / NIFTY500 forward-return alignment via factor_bench.py, which
    carries its own documented no-lookahead contract (T1-class control, D-028).
  - breadth_pct_above_200dma is computed off cube_close_long.parquet (2005-04-01
    -> 2025-12-05, 976 tickers, the SAME Nifty500_Master_Dataset-derived long cube
    that backs panel_long) rather than the short cube_close.parquet (751 names,
    2021-07-16 only) -- this gives full-history breadth instead of a ~4yr tail.
    Still NaN before the first date with >=150 valid trailing obs for the 200dma
    (rolling min_periods=150 guard), not fabricated/backfilled.

Sources:
  rnd/panel/panel_long.parquet                    -- PIT mktcap_log, monthly grid,
                                                       2005-04 -> 2025-12, 751-name
                                                       CURRENT universe (survivorship
                                                       caveat inherited as-is, see
                                                       PANEL_SCHEMA.md).
  data/fundamentals/MASTER_fundamentals_pit.parquet -- long-format PIT fundamentals,
                                                       metric_norm in {net profit,
                                                       equity capital, reserves},
                                                       available_date gates every row.
  factor_navs (1).xlsx (via src/lib/factor_bench.py) -- NIFTY 500 NAV series for
                                                       market_vol + forward market
                                                       return (M1 test), full history,
                                                       staleness cutoffs documented in
                                                       PANEL_SCHEMA.md (do not re-derive).
  rnd/panel/cube_close_long.parquet                -- daily close, 2005-04-01 ->
                                                       2025-12-05, 976 names, used
                                                       ONLY for breadth_pct_above_200dma.

EY definition (aggregate/company basis, not per-share):
  EY_i(t) = net_profit_i(t_PIT) / mktcap_i(t)   [equivalent to EPS/Price since both
  numerator and denominator scale by the same (unknown) share count -- avoids ever
  needing a per-share book/EPS split that MASTER_fundamentals_pit.parquet does not
  carry a shares-outstanding series for; PANEL_SCHEMA.md ADDENDUM already confirmed
  no shares-outstanding series exists anywhere in this dataset].
  PE_i(t) = mktcap_i(t) / net_profit_i(t) -- only defined where net_profit_i(t) > 0
  (negative/zero earners get NaN PE, not a blown-up or sign-flipped ratio; EY handles
  negative earners gracefully and is treated as the PRIMARY robust measure).
  PB_i(t) = mktcap_i(t) / book_equity_i(t), book_equity = equity_capital + reserves,
  only defined where book_equity_i(t) > 0.

Cap-tier cutoffs (percentile rank of mktcap within date, ascending pct_rank in
[0,1], 1 = largest name that date):
  large  : pct_rank >= 0.80   (top 20%)
  mid    : 0.50 <= pct_rank < 0.80   (next 30%)
  small  : 0.20 <= pct_rank < 0.50   (next 30%)
  micro  : pct_rank < 0.20    (bottom 20%)
Chosen as a clean quartile-like split of THIS date's available cross-section
(count of valid-mktcap names varies over 2005-2025, growing from a few hundred to
751) -- deliberately NOT the Principal's illustrative absolute "100/150/250/rest"
example, because that example assumes a fixed N=500-750 universe; percentile
cutoffs generalize correctly to whatever N is actually populated at each historical
date. Documented, not silently substituted.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ALPHA_ROOT = Path(__file__).resolve().parents[2]  # .../ALPHA_RANKER
RND = ALPHA_ROOT / "rnd"
PANEL_LONG_PATH = RND / "panel" / "panel_long.parquet"
FUND_PATH = ALPHA_ROOT / "data" / "fundamentals" / "MASTER_fundamentals_pit.parquet"
CUBE_CLOSE_PATH = RND / "panel" / "cube_close_long.parquet"
OUT_MARKET = RND / "panel" / "market_state.parquet"
OUT_STOCK = RND / "panel" / "stock_valuation_pit.parquet"

sys.path.insert(0, str(ALPHA_ROOT / "src" / "lib"))

TIER_CUTS = [(0.80, "large"), (0.50, "mid"), (0.20, "small"), (-np.inf, "micro")]


def assign_tier(pct_rank: pd.Series) -> pd.Series:
    tier = pd.Series(np.full(len(pct_rank), "micro", dtype=object), index=pct_rank.index)
    tier[pct_rank >= 0.80] = "large"
    tier[(pct_rank >= 0.50) & (pct_rank < 0.80)] = "mid"
    tier[(pct_rank >= 0.20) & (pct_rank < 0.50)] = "small"
    tier[pct_rank < 0.20] = "micro"
    tier[pct_rank.isna()] = np.nan
    return tier


def load_panel_long() -> pd.DataFrame:
    df = pd.read_parquet(PANEL_LONG_PATH, columns=["date", "symbol", "sector", "mktcap_log"])
    df["mktcap"] = np.exp(df["mktcap_log"])
    return df


def load_fund_pit() -> pd.DataFrame:
    f = pd.read_parquet(
        FUND_PATH,
        columns=["nse_symbol", "metric_norm", "value", "available_date"],
    )
    f = f[f["metric_norm"].isin(["net profit", "equity capital", "reserves"])].copy()
    f["value"] = pd.to_numeric(f["value"], errors="coerce")
    piv = (
        f.pivot_table(
            index=["nse_symbol", "available_date"],
            columns="metric_norm",
            values="value",
            aggfunc="last",
        )
        .reset_index()
        .rename(columns={"nse_symbol": "symbol"})
    )
    for col in ["net profit", "equity capital", "reserves"]:
        if col not in piv.columns:
            piv[col] = np.nan
    piv["book_equity"] = piv["equity capital"].fillna(0) + piv["reserves"].fillna(0)
    # a symbol with BOTH components missing (not just zero) should not get a fake 0 book_equity
    both_missing = piv["equity capital"].isna() & piv["reserves"].isna()
    piv.loc[both_missing, "book_equity"] = np.nan
    piv = piv.rename(columns={"net profit": "net_profit"})
    # UNITS FIX (caught this pass, verified against RELIANCE FY25: net profit
    # 81309 here vs mktcap ~2.08e13 from panel_long -- an EY of 3.9e-9, not the
    # sane ~0.04/~PE-25.6 both public sources agree on): MASTER_fundamentals_pit
    # values are Rs CRORE (standard Indian financial-statement convention), while
    # panel_long's mktcap_log = ln(shares_proxy * AdjClose) is ABSOLUTE RUPEES
    # (shares_proxy = current_MarketCap(Rs)/current_Price(Rs), both already in
    # raw rupees per build_panel.py). Convert crore -> rupees (x1e7) here, once,
    # at the source, so every downstream EY/PE/PB is unit-consistent.
    CRORE_TO_RUPEE = 1e7
    piv["net_profit"] = piv["net_profit"] * CRORE_TO_RUPEE
    piv["book_equity"] = piv["book_equity"] * CRORE_TO_RUPEE
    piv = piv[["symbol", "available_date", "net_profit", "book_equity"]].sort_values(
        ["symbol", "available_date"]
    )
    return piv


def asof_join(panel_long: pd.DataFrame, fund: pd.DataFrame) -> pd.DataFrame:
    pl = panel_long.sort_values(["date", "symbol"]).reset_index(drop=True)
    fd = fund.sort_values(["available_date", "symbol"]).reset_index(drop=True)
    # dtype guard: panel_long's `symbol` and MASTER_fundamentals_pit's `nse_symbol`
    # land on different pandas string backends (plain numpy-object "str" vs
    # extension "string[python]") depending on how each parquet was written;
    # merge_asof's `by=` requires identical dtypes. Cast both to plain object
    # so the join key comparison is a straight Python-string equality check,
    # not a dtype mismatch -- no value semantics change.
    pl = pl.astype({"symbol": "object"})
    fd = fd.astype({"symbol": "object"})
    merged = pd.merge_asof(
        pl,
        fd,
        left_on="date",
        right_on="available_date",
        by="symbol",
        direction="backward",
    )
    return merged


def build_stock_valuation(merged: pd.DataFrame) -> pd.DataFrame:
    df = merged.copy()
    df["EY"] = np.where(df["mktcap"] > 0, df["net_profit"] / df["mktcap"], np.nan)
    df["PE"] = np.where(
        (df["mktcap"] > 0) & (df["net_profit"] > 0), df["mktcap"] / df["net_profit"], np.nan
    )
    df["PB"] = np.where(
        (df["mktcap"] > 0) & (df["book_equity"] > 0), df["mktcap"] / df["book_equity"], np.nan
    )
    df["cap_pct_rank"] = df.groupby("date")["mktcap"].rank(pct=True)
    df["cap_tier"] = assign_tier(df["cap_pct_rank"])
    return df[
        [
            "date",
            "symbol",
            "sector",
            "mktcap",
            "cap_pct_rank",
            "cap_tier",
            "net_profit",
            "book_equity",
            "EY",
            "PE",
            "PB",
        ]
    ]


def winsorized_weight(mktcap: pd.Series, cap_pctile: float = 0.90) -> pd.Series:
    cap_val = mktcap.quantile(cap_pctile)
    w = mktcap.clip(upper=cap_val)
    return w


def winsorize_values(values: pd.Series, lo_pctile: float = 0.01, hi_pctile: float = 0.99) -> pd.Series:
    """Clip a per-date cross-section at its own [lo,hi] percentile. Applied to
    valuation-ratio VALUES (not just weights) before the cap-weighted mean:
    a single micro-cap name with a near-zero book_equity denominator (found in
    stock_valuation_pit -- e.g. ENRIN book_equity=Rs 1e5, PB=1.1e7 on 2025-12-05,
    almost certainly a MASTER_fundamentals_pit data artifact for that symbol, not
    a real 1.1-crore-times overvaluation) otherwise swamps a plain weighted mean
    (market_PB_capw was 45,441 vs the median-based market_PB_eqw of 4.45 before
    this fix -- a 10,000x gap, caught in this pass' sanity check). The
    market_{metric}_eqw / *_by_tier_* medians are already robust to this by
    construction and are left untouched."""
    if values.notna().sum() < 5:
        return values
    lo, hi = values.quantile(lo_pctile), values.quantile(hi_pctile)
    return values.clip(lower=lo, upper=hi)


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    mask = values.notna() & weights.notna() & (weights > 0)
    if mask.sum() == 0:
        return np.nan
    v, w = values[mask], weights[mask]
    return float((v * w).sum() / w.sum())


def aggregate_market_state(stock_val: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for date, g in stock_val.groupby("date"):
        row = {"date": date, "n_names": g["mktcap"].notna().sum()}
        w = winsorized_weight(g["mktcap"])
        for metric in ["EY", "PE", "PB"]:
            v_wins = winsorize_values(g[metric])
            row[f"market_{metric}_capw"] = weighted_mean(v_wins, w)
            row[f"market_{metric}_eqw"] = g[metric].median()
            for tier in ["large", "mid", "small", "micro"]:
                sub = g.loc[g["cap_tier"] == tier, metric]
                row[f"{metric}_by_tier_{tier}"] = sub.median() if len(sub) else np.nan
        rows.append(row)
    out = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    return out


def add_expanding_history(market: pd.DataFrame) -> pd.DataFrame:
    market = market.sort_values("date").reset_index(drop=True)
    ey = market["market_EY_eqw"]
    exp_mean = ey.expanding(min_periods=24).mean()
    exp_std = ey.expanding(min_periods=24).std()
    market["EY_hist_zscore_expanding"] = (ey - exp_mean) / exp_std
    market["EY_hist_pctrank_expanding"] = ey.expanding(min_periods=24).apply(
        lambda s: (s.iloc[-1] > s.iloc[:-1]).mean() if len(s) > 1 else np.nan, raw=False
    )
    market["EY_level"] = ey
    market["EY_trend_12m"] = ey - ey.shift(12)
    market["ERP_proxy"] = np.nan  # [DATA] no India bond-yield series found in datasets/;
    # only US Treasury CMT (datasets/yahoo_finance/daily_treasury_yield.parquet) exists,
    # a currency/risk-free mismatch for an INR ERP -- flagged NOT used, per fallback
    # instruction "else EY level+trend, flagged". EY_level/EY_trend_12m above are that
    # fallback.
    return market


def add_market_vol(market: pd.DataFrame) -> pd.DataFrame:
    import factor_bench

    nav = factor_bench.get_series("NIFTY500", "nav").sort_index()
    ret = nav.pct_change()
    vol21 = (ret.rolling(21).std() * np.sqrt(252)).dropna()
    vol21_df = vol21.rename("market_vol").reset_index()
    vol21_df.columns = ["nav_date", "market_vol"]
    market = market.sort_values("date")
    merged = pd.merge_asof(
        market, vol21_df.sort_values("nav_date"), left_on="date", right_on="nav_date", direction="backward"
    ).drop(columns=["nav_date"])
    return merged


def add_breadth(market: pd.DataFrame) -> pd.DataFrame:
    if not CUBE_CLOSE_PATH.exists():
        market["breadth_pct_above_200dma"] = np.nan
        return market
    cube = pd.read_parquet(CUBE_CLOSE_PATH)
    cube.index = pd.to_datetime(cube.index)
    dma200 = cube.rolling(200, min_periods=150).mean()
    above = (cube > dma200)
    valid = cube.notna() & dma200.notna()
    breadth = (above & valid).sum(axis=1) / valid.sum(axis=1).replace(0, np.nan)
    breadth_df = breadth.rename("breadth_pct_above_200dma").reset_index()
    breadth_df.columns = ["px_date", "breadth_pct_above_200dma"]
    breadth_df = breadth_df.sort_values("px_date")
    breadth_df["px_date"] = pd.to_datetime(breadth_df["px_date"])
    market = market.sort_values("date").copy()
    market["date"] = pd.to_datetime(market["date"])
    # only backward-fill WITHIN the cube_close window; before its first date -> NaN
    cube_start = cube.index.min()
    merged = pd.merge_asof(
        market, breadth_df, left_on="date", right_on="px_date", direction="backward",
        tolerance=pd.Timedelta(days=45),
    ).drop(columns=["px_date"])
    merged.loc[merged["date"] < cube_start, "breadth_pct_above_200dma"] = np.nan
    return merged


def build_market_state(write: bool = True):
    panel_long = load_panel_long()
    fund = load_fund_pit()
    merged = asof_join(panel_long, fund)
    stock_val = build_stock_valuation(merged)
    market = aggregate_market_state(stock_val)
    market = add_expanding_history(market)
    market = add_market_vol(market)
    market = add_breadth(market)
    if write:
        stock_val.to_parquet(OUT_STOCK, index=False)
        market.to_parquet(OUT_MARKET, index=False)
    return market, stock_val


if __name__ == "__main__":
    m, s = build_market_state()
    print("market_state rows:", len(m), "cols:", list(m.columns))
    print(m.tail(5).to_string())
    print("stock_valuation_pit rows:", len(s))
