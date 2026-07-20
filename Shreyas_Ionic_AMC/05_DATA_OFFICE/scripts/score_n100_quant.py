"""
score_n100_quant.py — STOCK_SCORECARD_750 quant-layer extension for the 66 Nifty-100 names.

Computes mechanical quant scores for the 43 N100 names that have no quant row yet,
using formulas reverse-engineered (and exact-match verified, see
N100_QUANT_VALIDATION.md) from:
  - Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/FROZEN_METHODOLOGY.md (prose spec)
  - Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/results/reference_300_full.csv
    (the CURRENT, methodology-compliant 300-name engine output — every formula
    below was validated against this file to <1e-12 floating point precision,
    across all 300 reference names, before being trusted on the 43 new names)
  - Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/IMPLEMENTATION_PLAN.md
    (corroborating pseudocode: cyclicality windows, PE/PB/market-cap derivation)

IMPORTANT (read N100_QUANT_VALIDATION.md before trusting numbers downstream):
  full_300_scored.csv (the file the original task brief pointed at as "verification
  target") is a STALE, pre-fix artifact (built 2026-07-17 23:39, before the Value-
  formula PB/FCF-yield fix and before the NDPMS Sell/Hold recommendation ruling).
  It has no pb_current/fcf_yield columns at all, so its value_score cannot be the
  current formula. This script targets the CURRENT, correct, already-in-production
  engine (reference_300_full.csv / portfolio_quant.csv lineage), not the stale file.
  Column NAMES follow full_300_scored.csv's 54-col schema for compatibility;
  VALUES follow the current frozen methodology.

Universe / percentile-trap decision: FULL RE-RANK over the UNION of the 300
reference names + the 43 new names (343 total), matching the established firm
precedent (reference_full_with_portfolio.csv, built one day after reference_300_full.csv,
demonstrably re-ranked the whole union rather than freezing the original 300's ranks
— verified: 300/300 reference rows' pillar scores changed after the portfolio's 32
new names were added). The 23 already-scored N100 names sit inside this same union
(they are literally part of the 300), so after the union re-rank their percentile
scores will drift slightly from their standalone reference_300_full.csv values —
that drift is expected and correct, not a bug.

Run:
  "C:\\Users\\Shreyas.1Gupta\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe" score_n100_quant.py
"""
import json
import os
import re
import sys
import numpy as np
import pandas as pd

pd.set_option("future.no_silent_downcasting", True)

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
SCORECARD = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750")
RESULTS = os.path.join(SCORECARD, "results")
DATASETS = os.path.join(ROOT, "datasets")
PRICES_DIR = os.path.join(ROOT, "ALPHA_RANKER", "data", "prices")
SECTOR_MAP_PATH = os.path.join(ROOT, "ALPHA_RANKER", "data", "universe", "sector_map.parquet")

REFERENCE_300_PATH = os.path.join(RESULTS, "reference_300_full.csv")
RUN_PLAN_PATH = os.path.join(RESULTS, "n100_run_plan.json")
OUT_CSV = os.path.join(RESULTS, "n100_quant_scored.csv")
OUT_VALIDATION = os.path.join(RESULTS, "N100_QUANT_VALIDATION.md")

# AS-OF date for all price-derived (technical) fields. MUST match the date the
# reference_300_full.csv engine used (verified exact match at this date for
# market_cap_approx / pe_current / returns / RSI / OBV / turnover on ADANIENT,
# ONGC, HCLTECH, JINDALSTEL) so the 43 new names are cross-sectionally
# comparable with the 300 reference names in the union re-rank. NOT "today"
# (2026-07-20) — using a fresher date for only 43/343 names would silently
# desynchronize the technical percentile ranks.
AS_OF_DATE = pd.Timestamp("2026-07-16")

WINSOR_LO, WINSOR_HI = 2, 98
MIN_GROUP = 5  # sector/sector-tier -> universe fallback threshold (validated exact)

CYCLICAL_LOOKBACK_YEARS = 8
STANDARD_LOOKBACK_YEARS = 4

# Validated exact (100% match, 300/300 names) against reference_300_full.csv,
# sourced from IMPLEMENTATION_PLAN.md Task 3 (SECTOR_CYCLICALITY, 41-sector
# taxonomy off ALPHA_RANKER/data/universe/sector_map.parquet's macro_sector).
# Two non-Cyclical buckets (Defensive-Stable / Sensitive-hybrid) collapse to
# "NotCyclical" in the final 2-way engine; unmapped/unknown sectors default
# to NotCyclical (fillna behaviour, also validated exact on "diversified").
SECTOR_CYCLICALITY = {
    "metals & mining": "Cyclical", "construction materials": "Cyclical", "capital goods": "Cyclical",
    "automobile and auto components": "Cyclical", "realty": "Cyclical", "construction": "Cyclical",
    "oil gas & consumable fuels": "Cyclical", "chemicals": "Cyclical", "textiles": "Cyclical",
    "non-energy minerals": "Cyclical", "energy minerals": "Cyclical", "process industries": "Cyclical",
    "producer manufacturing": "Cyclical", "transportation": "Cyclical", "forest materials": "Cyclical",
    "fast moving consumer goods": "NotCyclical", "healthcare": "NotCyclical",
    "health services": "NotCyclical", "health technology": "NotCyclical",
    "information technology": "NotCyclical", "technology services": "NotCyclical",
    "electronic technology": "NotCyclical", "telecommunication": "NotCyclical",
    "communications": "NotCyclical", "utilities": "NotCyclical", "power": "NotCyclical",
    "consumer non-durables": "NotCyclical", "consumer durables": "NotCyclical",
    "consumer services": "NotCyclical", "agriculture": "NotCyclical",
    "finance": "NotCyclical", "financial services": "NotCyclical",
    "commercial services": "NotCyclical", "industrial services": "NotCyclical",
    "distribution services": "NotCyclical", "retail trade": "NotCyclical",
    "services": "NotCyclical", "media entertainment & publication": "NotCyclical",
}

BASE_W_3Y = dict(quality_score=20, growth_3y_score=20, value_score=18, stage_3y_score=14,
                  sector_macro_3y_score=11, ownership_flow_3y_score=9, accumulation_3y_score=8)
BASE_W_1Y = dict(quality_score=16, growth_1y_score=16, value_score=16, stage_1y_score=26,
                  sector_macro_1y_score=13, ownership_flow_1y_score=8, accumulation_1y_score=5)
TILT_CYC_3Y = dict(quality_score=-2, growth_3y_score=-2, value_score=3, stage_3y_score=-2,
                    sector_macro_3y_score=3, ownership_flow_3y_score=0, accumulation_3y_score=0)
TILT_NOTCYC_3Y = dict(quality_score=3, growth_3y_score=2, value_score=0, stage_3y_score=-3,
                       sector_macro_3y_score=-2, ownership_flow_3y_score=0, accumulation_3y_score=0)
TILT_CYC_1Y = dict(quality_score=-2, growth_1y_score=-2, value_score=3, stage_1y_score=-2,
                    sector_macro_1y_score=3, ownership_flow_1y_score=0, accumulation_1y_score=0)
TILT_NOTCYC_1Y = dict(quality_score=3, growth_1y_score=2, value_score=0, stage_1y_score=-3,
                       sector_macro_1y_score=-2, ownership_flow_1y_score=0, accumulation_1y_score=0)


def log(msg):
    print(msg, flush=True)


# ----------------------------------------------------------------------------
# Raw metric computation for the 43 new names
# ----------------------------------------------------------------------------

def _clean_num(v):
    if pd.isna(v):
        return np.nan
    if isinstance(v, str):
        v = v.replace(",", "").replace("%", "").strip()
        if v in ("", "-"):
            return np.nan
        try:
            return float(v)
        except ValueError:
            return np.nan
    return v


def _mar_cols(df):
    return sorted([c for c in df.columns if re.match(r"^Mar \d{4}$", c)],
                  key=lambda x: int(x.split()[1]))


def _series(df, sym, metric, mar_cols):
    row = df[(df["symbol"] == sym) & (df["metric"] == metric)]
    if len(row) == 0:
        return pd.Series(dtype=float)
    return row[mar_cols].iloc[0].apply(_clean_num)


def load_screener():
    pl = pd.read_parquet(os.path.join(DATASETS, "screener_deep", "screener_annual_pl.parquet"))
    bs = pd.read_parquet(os.path.join(DATASETS, "screener_deep", "screener_balance_sheet.parquet"))
    cf = pd.read_parquet(os.path.join(DATASETS, "screener_deep", "screener_cash_flow.parquet"))
    return pl, bs, cf


def compute_fundamentals(sym, pl, bs, cf, cyclicality_tag, notes):
    mcp = _mar_cols(pl)
    mcb = _mar_cols(bs)
    mcc = _mar_cols(cf)

    npv = _series(pl, sym, "Net Profit+", mcp)
    eps = _series(pl, sym, "EPS in Rs", mcp)
    op = _series(pl, sym, "Operating Profit", mcp)
    interest = _series(pl, sym, "Interest", mcp)
    sales = _series(pl, sym, "Sales+", mcp)

    eq_cap = _series(bs, sym, "Equity Capital", mcb)
    reserves = _series(bs, sym, "Reserves", mcb)
    # Deposit-taking banks report 'Borrowing' (no plural/+), not 'Borrowings+'
    # (verified: AXISBANK/J&KBANK-style names use this alternate metric label).
    # Validated against reference_300_full.csv: banks there DO have a populated
    # debt_equity (e.g. J&KBANK 0.207939) despite roce/interest_coverage/revenue
    # growth being NaN for the same names (those stay NaN — see note below).
    borrow = _series(bs, sym, "Borrowings+", mcb)
    if borrow.dropna().empty:
        borrow = _series(bs, sym, "Borrowing", mcb)
    equity = (eq_cap + reserves)

    fcf = _series(cf, sym, "Free Cash Flow", mcc)

    n = CYCLICAL_LOOKBACK_YEARS if cyclicality_tag == "Cyclical" else STANDARD_LOOKBACK_YEARS

    # Fixed n-year window (by calendar position, not dropna-first), then exclude
    # any year where the ratio's denominator is <=0 (distress/negative-net-worth
    # years — e.g. CG Power's 2019-fraud-era negative equity — produce an
    # economically meaningless, sign-flipping ROE that a plain multi-year mean
    # cannot absorb). Validated exact against reference_300_full.csv on CGPOWER
    # (roe: -1.559 naive vs 0.348 target -> 0.348 with this filter).
    capital_employed = equity + borrow
    roe_window = (npv / equity).iloc[-n:]
    roe_valid = roe_window[equity.iloc[-n:] > 0]
    roce_window = (op / capital_employed).iloc[-n:]
    roce_valid = roce_window[capital_employed.iloc[-n:] > 0]
    if roe_valid.notna().sum() < n:
        notes.append(f"{sym}: ROE lookback wanted {n}y, only {roe_valid.notna().sum()}y valid (recent listing, short history, or a distress/negative-equity year excluded) — used all valid years in window.")
    if roce_valid.notna().sum() < n:
        notes.append(f"{sym}: ROCE lookback wanted {n}y, only {roce_valid.notna().sum()}y valid — used all valid years in window.")
    roe = roe_valid.mean() if roe_valid.notna().any() else np.nan
    roce = roce_valid.mean() if roce_valid.notna().any() else np.nan

    equity_nz = equity.replace(0, np.nan)
    de_series = (borrow / equity_nz).dropna()
    debt_equity = de_series.iloc[-1] if len(de_series) else np.nan

    ic_series = (op / interest.replace(0, np.nan)).dropna()
    interest_coverage = ic_series.iloc[-1] if len(ic_series) else np.nan

    # Deposit-taking banks / pure lending-NBFCs report under 'Revenue+' +
    # 'Financing Profit' (no 'Sales+'/'Operating Profit' line at all) — this
    # script does NOT fall back to those, because reference_300_full.csv's own
    # bank rows (J&KBANK, TMB, UCOBANK, IDFCFIRSTB, BANDHANBNK, ICICIBANK,
    # BAJFINANCE, PFC, LICHSGFIN, ...) show the IDENTICAL gap (revenue_cagr_3y/
    # revenue_growth_1y/roce/interest_coverage all NaN there too, while
    # debt_equity IS populated via 'Borrowing'). Adding a Revenue+/Financing-
    # Profit fallback for the 43 new names ALONE would make them inconsistent
    # with how every bank/NBFC in the existing 300-name reference universe is
    # already treated — so this is an inherited, documented methodology gap,
    # not something silently patched here. growth_3y/1y_score, quality_score's
    # ROCE leg (still uses ROE alone via skipna mean, so quality is NOT NaN)
    # are affected for these names; see N100_QUANT_VALIDATION.md.
    sales_nn = sales.dropna()
    if len(sales_nn) >= 2:
        revenue_growth_1y = (sales_nn.iloc[-1] / sales_nn.iloc[-2] - 1) * 100
    else:
        revenue_growth_1y = np.nan
        notes.append(f"{sym}: revenue_growth_1y NaN — no 'Sales+' data (bank/NBFC 'Revenue+' schema, or recent listing) — matches reference_300_full.csv's bank-row gap, not patched.")
    if len(sales_nn) >= 4:
        revenue_cagr_3y = ((sales_nn.iloc[-1] / sales_nn.iloc[-4]) ** (1 / 3) - 1) * 100
    else:
        revenue_cagr_3y = np.nan
        notes.append(f"{sym}: revenue_cagr_3y NaN — no 'Sales+' data (bank/NBFC 'Revenue+' schema, or recent listing) — matches reference_300_full.csv's bank-row gap, not patched.")

    # avg_fcf: full-history mean of screener's 'Free Cash Flow' metric.
    # [INFERENCE, documented open item — see N100_QUANT_VALIDATION.md] exact
    # match confirmed on ADANIENT (12/12-year full history); could NOT be
    # reproduced exactly for HCLTECH under any window/definition tried
    # (full history, cyclicality-window 4y/8y, CFO+CFI, CFO-delta-gross-block,
    # NP+Dep, CFO-Dep, median, trimmed mean). Low materiality: fcf_yield is
    # one of four Value sub-components (20% x 18%/16% weight = ~3.6%/2.9% of
    # composite), and only for the 43 new names (the 23 known names' raw
    # fcf_yield is reused as-is from reference_300_full.csv, not recomputed).
    fcf_nn = fcf.dropna()
    avg_fcf = fcf_nn.iloc[-n:].mean() if len(fcf_nn) else np.nan
    if len(fcf_nn) < n:
        avg_fcf = fcf_nn.mean() if len(fcf_nn) else np.nan

    shares_cr = np.nan
    latest_eps = eps.dropna()
    latest_np = npv.dropna()
    if len(latest_eps) and len(latest_np) and latest_eps.iloc[-1] not in (0, np.nan):
        shares_cr = latest_np.iloc[-1] / latest_eps.iloc[-1]

    equity_latest = equity.dropna().iloc[-1] if len(equity.dropna()) else np.nan
    book_value_per_share = equity_latest / shares_cr if shares_cr and not np.isnan(shares_cr) else np.nan

    pe_latest_eps = latest_eps.iloc[-1] if len(latest_eps) else np.nan

    return dict(
        roe=roe, roce=roce, debt_equity=debt_equity, interest_coverage=interest_coverage,
        revenue_cagr_3y=revenue_cagr_3y, revenue_growth_1y=revenue_growth_1y,
        shares_cr=shares_cr, book_value_per_share=book_value_per_share,
        avg_fcf=avg_fcf, latest_eps=pe_latest_eps,
    )


def compute_technicals(sym, notes):
    path = os.path.join(PRICES_DIR, f"{sym}.parquet")
    px = pd.read_parquet(path).sort_index()
    adj = px["Adj Close"]
    close = px["Close"]
    vol = px["Volume"]

    if AS_OF_DATE not in adj.index:
        avail = adj.index[adj.index <= AS_OF_DATE]
        if len(avail) == 0:
            raise ValueError(f"{sym}: no price data on/before {AS_OF_DATE.date()}")
        asof = avail.max()
        notes.append(f"{sym}: no exact price bar on {AS_OF_DATE.date()}, used nearest prior trading day {asof.date()}.")
    else:
        asof = AS_OF_DATE
    idx = adj.index.get_loc(asof)
    last_adj = adj.iloc[idx]
    last_close = close.iloc[idx]

    def ret(days):
        if idx - days < 0:
            return np.nan
        base = adj.iloc[idx - days]
        return last_adj / base - 1 if base else np.nan

    ret_3m, ret_6m, ret_12m, ret_24m = ret(63), ret(126), ret(252), ret(504)
    if pd.isna(ret_24m):
        notes.append(f"{sym}: ret_24m NaN — fewer than 504 trading days of price history (recent listing).")
    if pd.isna(ret_12m):
        notes.append(f"{sym}: ret_12m NaN — fewer than 252 trading days of price history.")

    def sma(k):
        if idx - k + 1 < 0:
            return np.nan
        return adj.iloc[idx - k + 1: idx + 1].mean()

    sma50, sma200 = sma(50), sma(200)
    above_50sma = bool(last_adj > sma50) if not np.isnan(sma50) else np.nan
    above_200sma = bool(last_adj > sma200) if not np.isnan(sma200) else np.nan

    # Wilder RSI(14) on Adj Close
    delta = adj.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = avg_gain / avg_loss
    rsi_series = 100 - 100 / (1 + rs)
    rsi14 = rsi_series.iloc[idx]

    # OBV slope short (40td) / long (180td): total OBV change over window
    direction = np.sign(adj.diff()).fillna(0)
    obv = (direction * vol).cumsum()

    def obv_delta(n):
        if idx - n < 0:
            return np.nan
        return obv.iloc[idx] - obv.iloc[idx - n]

    obv_slope_short = obv_delta(40)
    obv_slope_long = obv_delta(180)

    # turnover median 60d, Close*Volume, trailing 60 trading days inclusive
    if idx - 59 >= 0:
        turnover_median_60d = (close.iloc[idx - 59: idx + 1] * vol.iloc[idx - 59: idx + 1]).median()
    else:
        turnover_median_60d = (close.iloc[: idx + 1] * vol.iloc[: idx + 1]).median()
        notes.append(f"{sym}: turnover_median_60d computed on <60 days of history.")

    market_cap_approx = last_close * np.nan  # filled in caller (needs shares_cr from fundamentals)
    pe_current = np.nan  # filled in caller

    return dict(
        asof_date=str(asof.date()), last_close=last_close, last_adj_close=last_adj,
        ret_3m=ret_3m, ret_6m=ret_6m, ret_12m=ret_12m, ret_24m=ret_24m,
        above_50sma=above_50sma, above_200sma=above_200sma, rsi14=rsi14,
        obv_slope_short=obv_slope_short, obv_slope_long=obv_slope_long,
        turnover_median_60d=turnover_median_60d,
    )


def compute_ownership(sym, sc, notes):
    sub = sc[sc["symbol"] == sym].sort_values("quarter_end").copy()
    if len(sub) == 0:
        notes.append(f"{sym}: no shareholding_changes data at all — ownership_flow_long/short left NaN (recent listing / data gap, not imputed).")
        return dict(ownership_flow_long=np.nan, ownership_flow_short=np.nan)
    sub["sum_qoq"] = sub["FIIs_qoq"] + sub["DIIs_qoq"]
    vals = sub["sum_qoq"].dropna()
    if len(vals) == 0:
        notes.append(f"{sym}: shareholding rows present but FIIs_qoq/DIIs_qoq all NaN — ownership scores left NaN.")
        return dict(ownership_flow_long=np.nan, ownership_flow_short=np.nan)
    max_q = sub["quarter_end"].max()
    if max_q < pd.Timestamp("2024-01-01"):
        notes.append(f"{sym}: shareholding data stale (latest quarter {max_q.date()}) — inherited data limitation, same source used for the 300-name reference universe.")
    ownership_flow_long = vals.iloc[-6:].mean() if len(vals) >= 1 else np.nan
    ownership_flow_short = vals.iloc[-2:].mean() if len(vals) >= 1 else np.nan
    if len(vals) < 6:
        notes.append(f"{sym}: only {len(vals)} quarters of FIIs/DIIs data available for ownership_flow_long (wanted 6).")
    return dict(ownership_flow_long=ownership_flow_long, ownership_flow_short=ownership_flow_short)


def build_new_names_raw(symbols_meta, pl, bs, cf, sc, sector_map, notes):
    rows = []
    for meta in symbols_meta:
        sym = meta["symbol"]
        log(f"  computing raw metrics: {sym}")
        sm_row = sector_map[sector_map["symbol"] == sym]
        if len(sm_row) == 0:
            sector = meta.get("industry", "Unknown")
            notes.append(f"{sym}: not found in sector_map.parquet, fell back to n100_run_plan.json industry field '{sector}'.")
        else:
            sector = sm_row["macro_sector"].iloc[0]
        sector_norm = sector.strip().lower()
        cyclicality_tag = SECTOR_CYCLICALITY.get(sector_norm, "NotCyclical")

        fund = compute_fundamentals(sym, pl, bs, cf, cyclicality_tag, notes)
        tech = compute_technicals(sym, notes)
        own = compute_ownership(sym, sc, notes)

        shares_cr = fund["shares_cr"]
        last_close = tech["last_close"]
        market_cap_approx = last_close * shares_cr if shares_cr and not pd.isna(shares_cr) else np.nan
        pe_current = last_close / fund["latest_eps"] if fund["latest_eps"] and not pd.isna(fund["latest_eps"]) and fund["latest_eps"] != 0 else np.nan
        bvps = fund["book_value_per_share"]
        pb_current = last_close / bvps if bvps and not pd.isna(bvps) and bvps != 0 else np.nan
        fcf_yield = fund["avg_fcf"] / market_cap_approx if market_cap_approx and not pd.isna(market_cap_approx) and market_cap_approx != 0 else np.nan

        row = dict(
            symbol=sym, company_name=meta.get("company"), isin=meta.get("isin"),
            sector=sector, sector_norm=sector_norm, cyclicality_tag=cyclicality_tag,
            market_cap_approx=market_cap_approx,
            roe=fund["roe"], roce=fund["roce"], debt_equity=fund["debt_equity"],
            interest_coverage=fund["interest_coverage"],
            revenue_cagr_3y=fund["revenue_cagr_3y"], revenue_growth_1y=fund["revenue_growth_1y"],
            pe_current=pe_current, pb_current=pb_current,
            book_value_per_share=bvps, avg_fcf=fund["avg_fcf"], fcf_yield=fcf_yield,
            ret_3m=tech["ret_3m"], ret_6m=tech["ret_6m"], ret_12m=tech["ret_12m"], ret_24m=tech["ret_24m"],
            above_50sma=tech["above_50sma"], above_200sma=tech["above_200sma"], rsi14=tech["rsi14"],
            obv_slope_short=tech["obv_slope_short"], obv_slope_long=tech["obv_slope_long"],
            turnover_median_60d=tech["turnover_median_60d"],
            ownership_flow_long=own["ownership_flow_long"], ownership_flow_short=own["ownership_flow_short"],
            price_asof=tech["asof_date"],
        )
        rows.append(row)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# Percentile / scoring engine (validated exact against reference_300_full.csv)
# ----------------------------------------------------------------------------

def winsorize(s, lo=WINSOR_LO, hi=WINSOR_HI):
    valid = s.dropna()
    if len(valid) == 0:
        return s
    lo_v, hi_v = np.nanpercentile(valid, [lo, hi])
    return s.clip(lo_v, hi_v)


def pctile_universe(s):
    return winsorize(s).rank(pct=True) * 100


def pctile_sector_fallback(df, col, sector_col="sector_norm", minn=MIN_GROUP):
    s = winsorize(df[col])
    grp_size = df.groupby(sector_col)[col].transform("count")
    sector_rank = s.groupby(df[sector_col]).rank(pct=True) * 100
    universe_rank = s.rank(pct=True) * 100
    return np.where(grp_size >= minn, sector_rank, universe_rank)


def pctile_sector_tier_cascade(df, col, transform=lambda x: x, minn=MIN_GROUP):
    s = winsorize(transform(df[col]))
    grp_st_size = df.groupby("sector_tier_group")[col].transform("count")
    grp_sec_size = df.groupby("sector_norm")[col].transform("count")
    rank_st = s.groupby(df["sector_tier_group"]).rank(pct=True) * 100
    rank_sec = s.groupby(df["sector_norm"]).rank(pct=True) * 100
    rank_uni = s.rank(pct=True) * 100
    return np.where(grp_st_size >= minn, rank_st, np.where(grp_sec_size >= minn, rank_sec, rank_uni))


def weighted_mean(row, base_w, tilt_cyc, tilt_notcyc):
    tilt = tilt_cyc if row["cyclicality_tag"] == "Cyclical" else tilt_notcyc
    num, den = 0.0, 0.0
    for k, base in base_w.items():
        wt = base + tilt[k]
        v = row[k]
        if pd.notna(v):
            num += wt * v
            den += wt
    return num / den if den > 0 else np.nan


def run_engine(df):
    """df: union dataframe (343 rows) with raw columns populated. Returns df with
    all pillar/composite/gate/final/recommendation columns added, exactly per
    the validated formulas."""
    df = df.copy()

    # Quality
    df["roe_pct"] = pctile_sector_fallback(df, "roe")
    df["roce_pct"] = pctile_sector_fallback(df, "roce")
    df["quality_score"] = df[["roe_pct", "roce_pct"]].mean(axis=1, skipna=True)

    # Growth
    df["growth_3y_score"] = pctile_universe(df["revenue_cagr_3y"])
    df["growth_1y_score"] = pctile_universe(df["revenue_growth_1y"])
    df["growth_divergence_flag"] = (df["revenue_cagr_3y"] - df["revenue_growth_1y"]).abs() > 15

    # mcap tercile + sector-tier group (recomputed over the UNION, per precedent)
    df["mcap_tercile"] = pd.qcut(df["market_cap_approx"], q=3, labels=["Small", "Mid", "Large"])
    df["sector_tier_group"] = df["sector_norm"].astype(str) + "_" + df["mcap_tercile"].astype(str)

    # Value
    df["pe_for_ranking"] = df["pe_current"].where(df["pe_current"] >= 0, np.nan)
    df["pe_abs_pctile"] = pctile_universe(-df["pe_current"])
    df["pe_sector_tier_pctile"] = pctile_sector_tier_cascade(df, "pe_current", transform=lambda x: -x)
    df["pb_sector_tier_pctile"] = pctile_sector_tier_cascade(df, "pb_current", transform=lambda x: -x)
    df["fcf_yield_sector_tier_pctile"] = pctile_sector_tier_cascade(df, "fcf_yield", transform=lambda x: x)
    df["value_score"] = (0.25 * df["pe_abs_pctile"] + 0.35 * df["pe_sector_tier_pctile"]
                          + 0.20 * df["pb_sector_tier_pctile"] + 0.20 * df["fcf_yield_sector_tier_pctile"])

    # Stage / Technical
    df["rs_12m_pct"] = pctile_sector_fallback(df, "ret_12m")
    df["ret_12m_pct"] = pctile_universe(df["ret_12m"])
    df["ret_24m_pct"] = pctile_universe(df["ret_24m"])
    # skipna mean (NOT sum/3) — validated against reference_300_full.csv's own
    # recently-listed names (e.g. THELEELA, IKS, WAAREEENER: ret_24m NaN yet
    # stage_3y_score is populated from the 2 available terms, not NaN).
    raw3y = df[["rs_12m_pct", "ret_12m_pct", "ret_24m_pct"]].mean(axis=1, skipna=True)
    df["stage_3y_score"] = np.where(df["above_200sma"] == True, raw3y, raw3y * 0.5)  # noqa: E712

    df["rs_3m_pct"] = pctile_sector_fallback(df, "ret_3m")
    df["ret_3m_pct"] = pctile_universe(df["ret_3m"])
    df["ret_6m_pct"] = pctile_universe(df["ret_6m"])
    raw1y = df[["rs_3m_pct", "ret_3m_pct", "ret_6m_pct"]].mean(axis=1, skipna=True)
    rsi_nudge = (50 - df["rsi14"]) / 10
    df["stage_1y_score"] = np.where(df["above_50sma"] == True, raw1y, raw1y * 0.5) + rsi_nudge  # noqa: E712
    df["stage_timing_tag"] = np.where(df["rsi14"] > 70, "Extended",
                                       np.where(df["rsi14"] < 35, "Pulled back", "Neutral"))

    # Sector & Macro
    df["sector_mean_ret_12m"] = df.groupby("sector_norm")["ret_12m"].transform("mean")
    df["sector_mean_ret_3m"] = df.groupby("sector_norm")["ret_3m"].transform("mean")
    mom_3y = pctile_universe(df["sector_mean_ret_12m"])
    mom_1y = pctile_universe(df["sector_mean_ret_3m"])
    regime_fit_adj = np.where(df["cyclicality_tag"] == "Cyclical", 4.6, -2.6)
    df["sector_macro_3y_score"] = (mom_3y + regime_fit_adj).clip(0, 100)
    df["sector_macro_1y_score"] = (mom_1y + regime_fit_adj).clip(0, 100)

    # Ownership Flow
    df["ownership_3y_score"] = pctile_universe(df["ownership_flow_long"])
    df["ownership_1y_score"] = pctile_universe(df["ownership_flow_short"])

    # Accumulation
    df["accumulation_3y_score"] = pctile_universe(df["obv_slope_long"])
    df["accumulation_1y_score"] = pctile_universe(df["obv_slope_short"])

    # Composite (cyclicality-tilted weighted mean, renormalized over available pillars)
    d3 = df.rename(columns={"ownership_3y_score": "ownership_flow_3y_score"})
    d1 = df.rename(columns={"ownership_1y_score": "ownership_flow_1y_score"})
    df["composite_3y"] = d3.apply(lambda r: weighted_mean(r, BASE_W_3Y, TILT_CYC_3Y, TILT_NOTCYC_3Y), axis=1)
    df["composite_1y"] = d1.apply(lambda r: weighted_mean(r, BASE_W_1Y, TILT_CYC_1Y, TILT_NOTCYC_1Y), axis=1)

    # Coverage (7 pillars)
    pillars_3y = ["quality_score", "growth_3y_score", "value_score", "stage_3y_score",
                  "sector_macro_3y_score", "ownership_3y_score", "accumulation_3y_score"]
    pillars_1y = ["quality_score", "growth_1y_score", "value_score", "stage_1y_score",
                  "sector_macro_1y_score", "ownership_1y_score", "accumulation_1y_score"]
    cov3 = df[pillars_3y].notna().sum(axis=1)
    cov1 = df[pillars_1y].notna().sum(axis=1)
    df["coverage_3y"] = cov3 / 7 * 100
    df["coverage_1y"] = cov1 / 7 * 100
    df["coverage_flag_3y"] = np.where(cov3 >= 5, "High", np.where(cov3 >= 3, "Med", "Low"))
    df["coverage_flag_1y"] = np.where(cov1 >= 5, "High", np.where(cov1 >= 3, "Med", "Low"))

    # Balance-sheet gate (financial-sector D/E exemption)
    is_financial = df["sector_norm"] == "financial services"
    red_bs = (~is_financial) & (df["debt_equity"] > 2.5) | (df["interest_coverage"] < 1.5)
    amber_bs = (~red_bs) & ((~is_financial) & (df["debt_equity"] > 1.5) | (df["interest_coverage"] < 3))
    df["bs_flag"] = np.select(
        [is_financial, red_bs, amber_bs],
        ["N/A-financial-sector", "RED", "AMBER"],
        default="GREEN",
    )

    # Liquidity gate
    tier_bar = df["mcap_tercile"].map({"Large": 50_000_000, "Mid": 10_000_000, "Small": 2_500_000}).astype(float)
    df["min_turnover"] = tier_bar
    df["liquidity_flag"] = np.where(df["turnover_median_60d"] < tier_bar, "RED", "GREEN")

    def apply_gate(row, comp):
        v = comp
        if row["bs_flag"] == "RED" or row["liquidity_flag"] == "RED":
            v = min(v, 40) if pd.notna(v) else v
        elif row["bs_flag"] == "AMBER":
            v = v * 0.85 if pd.notna(v) else v
        return v

    df["final_3y_gated"] = df.apply(lambda r: apply_gate(r, r["composite_3y"]), axis=1)
    df["final_1y_gated"] = df.apply(lambda r: apply_gate(r, r["composite_1y"]), axis=1)

    # Red flags / penalty / boost (mechanical only — no analyst-estimate flag,
    # since no qualitative pass exists yet for these 43 names)
    rf_intcov = (df["interest_coverage"] < 1.5).fillna(False)
    rf_de = ((~is_financial) & (df["debt_equity"] > 2.5)).fillna(False)
    rf_neg_growth = (df["revenue_growth_1y"] < 0).fillna(False)
    decel = df["revenue_cagr_3y"] - df["revenue_growth_1y"]
    rf_decel = (decel > 15).fillna(False)
    redflag_count = rf_intcov.astype(int) + rf_de.astype(int) + rf_neg_growth.astype(int) + rf_decel.astype(int)
    df["redflag_count"] = redflag_count
    df["penalty"] = -np.minimum(10, 2.0 ** redflag_count - 1)
    df["boost"] = np.where((redflag_count == 0) & (df["quality_score"] > 60) & (df["value_score"] > 60), 3, 0)

    df["final_score_3y"] = (df["final_3y_gated"] + df["penalty"] + df["boost"]).clip(0, 100)
    df["final_score_1y"] = (df["final_1y_gated"] + df["penalty"] + df["boost"]).clip(0, 100)

    # Recommendation — CURRENT NDPMS Sell/Hold vocabulary (frozen 2026-07-18),
    # NOT full_300_scored.csv's stale 5-tier Strong-Buy/Accumulate/Hold/Reduce/
    # Avoid scheme. See N100_QUANT_VALIDATION.md for why.
    df["recommendation_3y"] = np.where(df["final_score_3y"].isna(), "No Recommendation",
                                        np.where(df["final_score_3y"] < 40, "Sell", "Hold"))
    df["recommendation_1y"] = np.where(df["final_score_1y"].isna(), "No Recommendation",
                                        np.where(df["final_score_1y"] < 40, "Sell", "Hold"))

    return df


SCHEMA_54 = [
    "symbol", "sector", "cyclicality_tag", "market_cap_approx", "roe", "roce", "debt_equity",
    "interest_coverage", "revenue_cagr_3y", "revenue_growth_1y", "pe_current", "ret_3m", "ret_6m",
    "ret_12m", "ret_24m", "above_50sma", "above_200sma", "rsi14", "obv_slope_short", "obv_slope_long",
    "turnover_median_60d", "ownership_flow_long", "ownership_flow_short", "pe_for_ranking", "roe_pct",
    "roce_pct", "quality_score", "growth_3y_score", "growth_1y_score", "growth_divergence_flag",
    "value_score", "stage_3y_score", "stage_timing_tag", "stage_1y_score", "sector_macro_3y_score",
    "sector_macro_1y_score", "ownership_3y_score", "ownership_1y_score", "accumulation_3y_score",
    "accumulation_1y_score", "composite_3y", "coverage_3y", "composite_1y", "coverage_1y", "bs_flag",
    "mcap_tercile", "min_turnover", "liquidity_flag", "final_score_3y", "final_score_1y",
    "recommendation_3y", "recommendation_1y", "coverage_flag_3y", "coverage_flag_1y",
]


def main():
    os.makedirs(RESULTS, exist_ok=True)
    notes = []

    log("Loading reference_300_full.csv (300-name current-engine reference universe)...")
    ref300 = pd.read_csv(REFERENCE_300_PATH)
    log(f"  reference_300_full.csv: {ref300.shape}")

    log("Loading n100_run_plan.json...")
    with open(RUN_PLAN_PATH, encoding="utf-8") as f:
        plan = json.load(f)
    new_meta = [x for x in plan if x.get("quant") is None]
    known_syms = [x["symbol"] for x in plan if x.get("quant") is not None]
    log(f"  {len(new_meta)} new names to score, {len(known_syms)} already-scored gate names.")

    log("Loading sector_map.parquet, screener_deep parquets, shareholding_changes.parquet...")
    sector_map = pd.read_parquet(SECTOR_MAP_PATH)
    pl, bs, cf = load_screener()
    sc = pd.read_parquet(os.path.join(DATASETS, "derived", "shareholding_changes.parquet"))

    log("Computing raw metrics for the 43 new names from raw data...")
    new_raw = build_new_names_raw(new_meta, pl, bs, cf, sc, sector_map, notes)
    new_raw.to_csv(os.path.join(RESULTS, "n100_new43_raw_inputs.csv"), index=False)
    log(f"  saved raw inputs -> n100_new43_raw_inputs.csv ({new_raw.shape})")

    log("Also computing raw metrics for the 23 GATE names (fresh, from raw data, for validation)...")
    gate_meta = [{"symbol": s, "company": None, "isin": None, "industry": None} for s in known_syms]
    gate_raw = build_new_names_raw(gate_meta, pl, bs, cf, sc, sector_map, notes)
    gate_raw.to_csv(os.path.join(RESULTS, "n100_gate23_raw_inputs_fresh.csv"), index=False)
    log(f"  saved -> n100_gate23_raw_inputs_fresh.csv ({gate_raw.shape})")

    # ---- Build the 343-name union for the percentile engine ----
    log("Building 343-name union (300 reference + 43 new) and running the scoring engine...")
    ref_cols_needed = ["symbol", "sector", "sector_norm", "cyclicality_tag", "market_cap_approx",
                        "roe", "roce", "debt_equity", "interest_coverage", "revenue_cagr_3y",
                        "revenue_growth_1y", "pe_current", "pb_current", "fcf_yield",
                        "ret_3m", "ret_6m", "ret_12m", "ret_24m", "above_50sma", "above_200sma",
                        "rsi14", "obv_slope_short", "obv_slope_long", "turnover_median_60d",
                        "ownership_flow_long", "ownership_flow_short"]
    ref_slice = ref300[ref_cols_needed].copy()
    ref_slice["is_new"] = False

    new_slice = new_raw[["symbol", "sector", "sector_norm", "cyclicality_tag", "market_cap_approx",
                          "roe", "roce", "debt_equity", "interest_coverage", "revenue_cagr_3y",
                          "revenue_growth_1y", "pe_current", "pb_current", "fcf_yield",
                          "ret_3m", "ret_6m", "ret_12m", "ret_24m", "above_50sma", "above_200sma",
                          "rsi14", "obv_slope_short", "obv_slope_long", "turnover_median_60d",
                          "ownership_flow_long", "ownership_flow_short"]].copy()
    new_slice["is_new"] = True

    union = pd.concat([ref_slice, new_slice], ignore_index=True)
    assert union["symbol"].is_unique, "duplicate symbols in union!"
    log(f"  union shape: {union.shape}")

    scored = run_engine(union)
    scored_new = scored[scored["is_new"]].copy()

    # ---- Also score the union with FRESH (recomputed) values for the 23 gate names,
    #      to test formula fidelity against reference_300_full.csv on a like-for-like
    #      basis (i.e. is MY code right, independent of the union-widening drift) ----
    ref_slice_gate_swap = ref_slice[~ref_slice["symbol"].isin(known_syms)].copy()
    gate_slice = gate_raw[["symbol", "sector", "sector_norm", "cyclicality_tag", "market_cap_approx",
                            "roe", "roce", "debt_equity", "interest_coverage", "revenue_cagr_3y",
                            "revenue_growth_1y", "pe_current", "pb_current", "fcf_yield",
                            "ret_3m", "ret_6m", "ret_12m", "ret_24m", "above_50sma", "above_200sma",
                            "rsi14", "obv_slope_short", "obv_slope_long", "turnover_median_60d",
                            "ownership_flow_long", "ownership_flow_short"]].copy()
    gate_slice["is_new"] = False
    union_fresh_gate = pd.concat([ref_slice_gate_swap, gate_slice, new_slice], ignore_index=True)
    scored_fresh_gate = run_engine(union_fresh_gate)

    # ---- Assemble output in the 54-column full_300_scored.csv schema ----
    out = pd.DataFrame()
    for col in SCHEMA_54:
        if col in scored_new.columns:
            out[col] = scored_new[col].values
        else:
            out[col] = np.nan
    out = out.sort_values("symbol").reset_index(drop=True)
    out.to_csv(OUT_CSV, index=False)
    log(f"Saved {out.shape[0]} rows x {out.shape[1]} cols -> {OUT_CSV}")

    # ---- Save intermediate full (83-col-equivalent) union output for audit ----
    scored.to_csv(os.path.join(RESULTS, "n100_union343_full_engine_output.csv"), index=False)
    scored_fresh_gate.to_csv(os.path.join(RESULTS, "n100_union343_freshgate_engine_output.csv"), index=False)

    with open(os.path.join(RESULTS, "n100_quant_build_notes.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(notes))
    log(f"Saved {len(notes)} build notes -> n100_quant_build_notes.txt")

    log("DONE.")
    return out, scored, scored_fresh_gate, ref300, known_syms, notes


if __name__ == "__main__":
    main()
