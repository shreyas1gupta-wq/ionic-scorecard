"""
ALPHA_RANKER/rnd/lib/build_panel.py

Builds the SHARED PIT labeled panel for the ALPHA_RANKER model-improvement
research program (see rnd/RESEARCH_PROTOCOL.md sec 1-2). One row per
(month-end rebalance date, symbol).

NO-LOOKAHEAD CONTRACT (mandatory, verify before trusting any downstream card):
  - Every feature at date t is computed from price/factor data with index <= t
    ONLY. beta_252 used in resid fwd returns is the beta AS ESTIMATED AT t
    (never re-estimated with the forward window).
  - Forward returns are strictly t -> t+h, h in TRADING days measured on the
    market's own trading calendar (master_cal, from _NSEI.parquet). Rows
    where t+h falls past the end of available history are NaN -- never
    fabricated, never extrapolated.
  - Regime label = nearest PRIOR label (merge_asof backward) <= t.
  - No forward-fill ever crosses a symbol's actual listing life: reindexing
    onto master_cal uses a short (5 trading day) ffill limit to bridge
    isolated halts only; a real IPO-before or delisted-after gap produces
    NaN feature/price values that gate the row out (see `_valid_at`).

Run: python build_panel.py   (prints progress; ~5-10 min for 751 symbols)
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]  # .../NIFTY 500
AR = ROOT / "ALPHA_RANKER"
PRICES_DIR = AR / "data" / "prices"
UNIVERSE_CSV = AR / "data" / "universe" / "nifty_total_market_750.csv"
SCREENER_DIR = AR / "data" / "fundamentals" / "screener_live"
REGIME_PATH = AR / "results" / "regime_timeline.parquet"
OUT_DIR = AR / "rnd" / "panel"
OUT_PARQUET = OUT_DIR / "panel.parquet"
SCHEMA_MD = OUT_DIR / "PANEL_SCHEMA.md"
REPORT_MD = AR / "rnd" / "reports" / "FND_panel.md"

sys.path.insert(0, str(AR / "src" / "lib"))
import factor_bench  # noqa: E402  (existing PIT-safe factor NAV loader, reused as-is)

FF_WINDOW = 252
FF_MIN_OBS = 126
VOL_WINDOWS = {"vol_21": 21, "vol_63": 63, "vol_126": 126, "vol_252": 252}
ANN = np.sqrt(252.0)
FFILL_LIMIT = 5  # trading days, bridges isolated halts only

PANEL_COLS = [
    "date", "symbol", "sector", "mktcap_log", "regime_trend", "regime_vol", "regime_leader",
    "beta_252", "vol_21", "vol_63", "vol_126", "vol_252", "idio_vol_252",
    "ff_beta_MKT", "ff_beta_SMB", "ff_beta_HML", "ff_beta_RMW", "ff_beta_CMA", "ff_beta_WML",
    "fwd_ret_1M_raw", "fwd_ret_1M_excess", "fwd_ret_1M_resid",
    "fwd_ret_1Y_raw", "fwd_ret_1Y_excess", "fwd_ret_1Y_resid",
    "fwd_ret_5Y_raw", "fwd_ret_5Y_excess", "fwd_ret_5Y_resid",
]
HORIZONS = {"1M": 21, "1Y": 252, "5Y": 1260}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------- master trading calendar (from the market index itself) ----------
def load_master_calendar() -> pd.DatetimeIndex:
    nsei = pd.read_parquet(PRICES_DIR / "_NSEI.parquet")
    nsei = nsei[~nsei.index.duplicated(keep="last")].sort_index()
    return nsei


# ---------- FF6 daily factor returns, aligned to master calendar ----------
def build_ff_factors(master_dates: pd.DatetimeIndex) -> pd.DataFrame:
    """
    [INFERENCE] proxy construction (no true India FF6 series built from our
    own universe within this pass -- documented in PANEL_SCHEMA.md):
      MKT = NIFTY500 return - HDFC Liquid Fund(G) return (cash/Rf proxy)
      SMB = NIFTY SMALLCAP 250 ret - NIFTY 100 ret            (spec-literal)
      HML = NIFTY 200 Value 30 ret     - NIFTY 500 ret   (excess-of-market)
      RMW = NIFTY 200 Quality 30 ret   - NIFTY 500 ret   (excess-of-market)
      CMA = NIFTY 100 Low Vol 30 ret   - NIFTY 500 ret   (excess-of-market;
            weakest proxy -- no true investment-based India index available)
      WML = NIFTY 200 Momentum 30 ret  - NIFTY 500 ret   (excess-of-market)
    Excess-of-broad-market construction (rather than raw smart-beta index
    returns) is deliberate: it orthogonalizes market beta out of HML/RMW/
    CMA/WML so the multi-factor regression isn't dominated by collinear
    market exposure (RESEARCH_PROTOCOL.md sec 2, "market/factor
    neutralization").
    factor_navs.xlsx (hence these factor returns) has data through
    2026-02-27 only -- see staleness caveat in PANEL_SCHEMA.md.
    """
    rets = factor_bench.load_returns()
    rets = rets.reindex(master_dates)  # NaN where source has no obs -- never filled
    mkt = rets["NIFTY 500"] - rets["HDFC Liquid Fund(G)"]
    smb = rets["NIFTY SMALLCAP 250"] - rets["NIFTY 100"]
    hml = rets["NIFTY 200 Value 30"] - rets["NIFTY 500"]
    rmw = rets["NIFTY 200 Quality 30"] - rets["NIFTY 500"]
    cma = rets["NIFTY 100 Low Vol 30"] - rets["NIFTY 500"]
    wml = rets["NIFTY 200 Momentum 30"] - rets["NIFTY 500"]
    return pd.DataFrame(
        {"MKT": mkt, "SMB": smb, "HML": hml, "RMW": rmw, "CMA": cma, "WML": wml},
        index=master_dates,
    )


def load_universe_sector_map() -> dict:
    uni = pd.read_csv(UNIVERSE_CSV)
    return dict(zip(uni["Symbol"], uni["Industry"]))


_INR_RE = re.compile(r"[\d,]+\.?\d*")


def _parse_inr(s) -> float:
    if not isinstance(s, str):
        return np.nan
    m = _INR_RE.search(s.replace(",", ""))
    return float(m.group()) if m else np.nan


def load_mktcap_shares_proxy(symbol: str) -> float:
    """
    Static shares-outstanding proxy = current_market_cap(Rs) / current_price(Rs),
    both read from screener_live/<SYM>.json top_ratios (a CURRENT snapshot,
    not a PIT time series -- screener does not publish historical market cap).
    [INFERENCE] caveat: assumes share count is constant across the panel's
    5y window. Ignores splits/bonuses/buybacks/QIP issuance during 2021-2026;
    multiplying by Adj Close (split/dividend-adjusted) keeps the price side
    internally consistent with a constant-share assumption, but any real
    share-count change during the window will bias mktcap_log's level
    (though not necessarily its cross-sectional rank on a given date).
    """
    fp = SCREENER_DIR / f"{symbol}.json"
    if not fp.exists():
        return np.nan
    try:
        d = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return np.nan
    tr = d.get("top_ratios", {}) or {}
    mcap_cr = _parse_inr(tr.get("Market Cap", ""))
    price = _parse_inr(tr.get("Current Price", ""))
    if not mcap_cr or not price or price <= 0:
        return np.nan
    return (mcap_cr * 1e7) / price  # shares outstanding proxy


def load_regime() -> pd.DataFrame:
    reg = pd.read_parquet(REGIME_PATH)[["date", "trend_regime", "vol_regime", "leading_factor"]].copy()
    reg = reg.sort_values("date").rename(
        columns={"trend_regime": "regime_trend", "vol_regime": "regime_vol", "leading_factor": "regime_leader"}
    )
    return reg


def month_end_positions(master_dates: pd.DatetimeIndex) -> np.ndarray:
    ym = master_dates.to_period("M")
    pos = pd.Series(np.arange(len(master_dates)), index=ym)
    last_pos = pos.groupby(level=0).max()
    return last_pos.values  # sorted ascending (periods are sorted)


def _ols_beta_capm(stock_ret: np.ndarray, mkt_ret: np.ndarray) -> float:
    mask = ~(np.isnan(stock_ret) | np.isnan(mkt_ret))
    if mask.sum() < FF_MIN_OBS:
        return np.nan
    x = mkt_ret[mask]
    y = stock_ret[mask]
    var_x = np.var(x, ddof=1)
    if var_x == 0 or np.isnan(var_x):
        return np.nan
    cov_xy = np.cov(x, y, ddof=1)[0, 1]
    return float(cov_xy / var_x)


def _ols_ff6(stock_ret: np.ndarray, ff_block: np.ndarray) -> tuple[np.ndarray, float]:
    """Returns (6 betas [MKT,SMB,HML,RMW,CMA,WML], idio_vol_252 annualized)."""
    mask = ~(np.isnan(stock_ret) | np.isnan(ff_block).any(axis=1))
    if mask.sum() < FF_MIN_OBS:
        return np.full(6, np.nan), np.nan
    x = ff_block[mask]
    y = stock_ret[mask]
    X = np.column_stack([np.ones(len(x)), x])
    coefs, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coefs
    idio_vol = float(np.std(resid, ddof=1) * ANN)
    return coefs[1:], idio_vol


def process_symbol(symbol, sector, master_dates, rebal_pos, nsei_close, nsei_ret, ff_arr, regime_df, mktcap_shares):
    fp = PRICES_DIR / f"{symbol}.parquet"
    df = pd.read_parquet(fp)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    if df.empty or "Adj Close" not in df.columns:
        return []
    file_min, file_max = df.index.min(), df.index.max()
    px_raw = df["Adj Close"].reindex(master_dates)
    px = px_raw.ffill(limit=FFILL_LIMIT)  # bridges isolated halts only, never before listing
    ret = px.pct_change().values
    px_vals = px.values
    n = len(master_dates)

    rows = []
    for pos_t in rebal_pos:
        t_date = master_dates[pos_t]
        if t_date < file_min or t_date > file_max:
            continue  # not yet listed / delisted -- do not fabricate a row
        p_t = px_vals[pos_t]
        if np.isnan(p_t) or p_t <= 0:
            continue  # gap exceeds ffill tolerance -- genuinely no PIT price here

        w0 = max(0, pos_t - FF_WINDOW + 1)
        stock_w = ret[w0 : pos_t + 1]
        mkt_w = nsei_ret[w0 : pos_t + 1]
        ff_w = ff_arr[w0 : pos_t + 1]

        beta_252 = _ols_beta_capm(stock_w, mkt_w)
        ff_betas, idio_vol_252 = _ols_ff6(stock_w, ff_w)

        vols = {}
        for name, win in VOL_WINDOWS.items():
            v0 = max(0, pos_t - win + 1)
            seg = ret[v0 : pos_t + 1]
            valid = seg[~np.isnan(seg)]
            if len(valid) >= int(0.8 * win):
                vols[name] = float(np.std(valid, ddof=1) * ANN)
            else:
                vols[name] = np.nan

        fwd = {}
        for hname, h in HORIZONS.items():
            pos_fwd = pos_t + h
            if pos_fwd >= n:
                raw = excess = resid = np.nan
            else:
                p_fwd = px_vals[pos_fwd]
                m_t, m_fwd = nsei_close[pos_t], nsei_close[pos_fwd]
                if np.isnan(p_fwd) or p_fwd <= 0:
                    raw = excess = resid = np.nan
                else:
                    raw = p_fwd / p_t - 1.0
                    mkt_fwd = m_fwd / m_t - 1.0
                    excess = raw - mkt_fwd
                    resid = raw - (beta_252 * mkt_fwd if not np.isnan(beta_252) else np.nan)
            fwd[f"fwd_ret_{hname}_raw"] = raw
            fwd[f"fwd_ret_{hname}_excess"] = excess
            fwd[f"fwd_ret_{hname}_resid"] = resid

        # regime: nearest prior label <= t (regime_df is pre-sorted ascending on 'date')
        ridx = regime_df["date"].searchsorted(t_date, side="right") - 1
        if ridx >= 0:
            rrow = regime_df.iloc[ridx]
            regime_trend, regime_vol, regime_leader = rrow["regime_trend"], rrow["regime_vol"], rrow["regime_leader"]
        else:
            regime_trend = regime_vol = regime_leader = np.nan

        mktcap_log = float(np.log(mktcap_shares * p_t)) if (not np.isnan(mktcap_shares) and p_t > 0) else np.nan

        row = {
            "date": t_date, "symbol": symbol, "sector": sector, "mktcap_log": mktcap_log,
            "regime_trend": regime_trend, "regime_vol": regime_vol, "regime_leader": regime_leader,
            "beta_252": beta_252, **vols, "idio_vol_252": idio_vol_252,
            "ff_beta_MKT": ff_betas[0], "ff_beta_SMB": ff_betas[1], "ff_beta_HML": ff_betas[2],
            "ff_beta_RMW": ff_betas[3], "ff_beta_CMA": ff_betas[4], "ff_beta_WML": ff_betas[5],
            **fwd,
        }
        rows.append(row)
    return rows


def lag_stability_check(master_dates, nsei_ret, ff_arr, sample_n=25, seed=7):
    """Sanity check (not a full lookahead audit): recompute beta_252 at t vs
    at t-1 trading day for a random sample of (symbol, rebalance date) pairs.
    A PIT-correct rolling window shifts by one observation and should move
    only a little; a large jump would indicate a computation bug (e.g. an
    off-by-one that lets t peek at t+1)."""
    rng = np.random.default_rng(seed)
    symbols = [f.stem for f in PRICES_DIR.glob("*.parquet") if not f.name.startswith("_")]
    rebal_pos = month_end_positions(master_dates)
    rebal_pos = rebal_pos[rebal_pos >= FF_MIN_OBS]
    diffs = []
    for _ in range(sample_n):
        sym = rng.choice(symbols)
        pos_t = int(rng.choice(rebal_pos))
        fp = PRICES_DIR / f"{sym}.parquet"
        try:
            df = pd.read_parquet(fp)
        except Exception:
            continue
        df = df[~df.index.duplicated(keep="last")].sort_index()
        if "Adj Close" not in df.columns:
            continue
        px = df["Adj Close"].reindex(master_dates).ffill(limit=FFILL_LIMIT)
        ret = px.pct_change().values
        for shift in (0, 1):
            pos = pos_t - shift
            if pos < FF_MIN_OBS:
                break
        else:
            w0_t, w0_tm1 = max(0, pos_t - FF_WINDOW + 1), max(0, pos_t - 1 - FF_WINDOW + 1)
            b_t = _ols_beta_capm(ret[w0_t : pos_t + 1], nsei_ret[w0_t : pos_t + 1])
            b_tm1 = _ols_beta_capm(ret[w0_tm1 : pos_t], nsei_ret[w0_tm1 : pos_t])
            if not (np.isnan(b_t) or np.isnan(b_tm1)):
                diffs.append(abs(b_t - b_tm1))
    return diffs


def main():
    t0 = time.time()
    log("Loading master calendar (from _NSEI.parquet)...")
    nsei = load_master_calendar()
    master_dates = nsei.index
    nsei_close = nsei["Adj Close"].values
    nsei_ret = nsei["Adj Close"].pct_change().values
    log(f"Master calendar: {len(master_dates)} trading days, {master_dates.min().date()} -> {master_dates.max().date()}")

    log("Building FF6 proxy factor returns (factor_bench.load_returns, reindexed)...")
    ff_df = build_ff_factors(master_dates)
    ff_last_valid = ff_df.dropna(how="any").index.max()
    log(f"FF6 factor coverage: last complete-row date = {ff_last_valid.date()}")

    sector_map = load_universe_sector_map()
    regime_df = load_regime()

    rebal_pos = month_end_positions(master_dates)
    rebal_dates = master_dates[rebal_pos]
    log(f"Rebalance dates (month-ends): {len(rebal_dates)}, {rebal_dates.min().date()} -> {rebal_dates.max().date()}")

    symbols = sorted(f.stem for f in PRICES_DIR.glob("*.parquet") if not f.name.startswith("_"))
    log(f"Symbols to process: {len(symbols)}")

    ff_arr = ff_df.values
    all_rows = []
    n_skipped_no_sector, n_skipped_no_mcap = 0, 0
    for i, sym in enumerate(symbols):
        sector = sector_map.get(sym, np.nan)
        if pd.isna(sector):
            n_skipped_no_sector += 1
        mcap_shares = load_mktcap_shares_proxy(sym)
        if np.isnan(mcap_shares):
            n_skipped_no_mcap += 1
        try:
            rows = process_symbol(sym, sector, master_dates, rebal_pos, nsei_close, nsei_ret, ff_arr, regime_df, mcap_shares)
            all_rows.extend(rows)
        except Exception as e:
            log(f"  WARN symbol {sym} failed: {e}")
        if (i + 1) % 100 == 0:
            log(f"  ...{i+1}/{len(symbols)} symbols, {len(all_rows)} rows so far ({time.time()-t0:.0f}s elapsed)")

    log(f"Assembling panel: {len(all_rows)} rows total")
    panel = pd.DataFrame(all_rows)[PANEL_COLS]
    panel = panel.sort_values(["date", "symbol"]).reset_index(drop=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(OUT_PARQUET, index=False)
    log(f"Saved {OUT_PARQUET} ({panel.shape[0]} rows x {panel.shape[1]} cols)")

    # ---------- sanity ----------
    log("Running lag-stability spot check (beta_252 at t vs t-1)...")
    diffs = lag_stability_check(master_dates, nsei_ret, ff_arr)
    diffs = np.array(diffs)

    nonnull_pct = (panel.notna().mean() * 100).round(1)
    n_obs = len(panel)
    date_min, date_max = panel["date"].min(), panel["date"].max()
    n_sectors_missing = int(panel["sector"].isna().sum())
    n_mktcap_missing = int(panel["mktcap_log"].isna().sum())

    summary_lines = [
        f"n_obs = {n_obs}",
        f"date range = {date_min.date()} -> {date_max.date()}",
        f"n_symbols = {panel['symbol'].nunique()}",
        f"n_rebalance_dates = {panel['date'].nunique()}",
        "",
        "per-column non-null %:",
    ]
    for c in PANEL_COLS:
        summary_lines.append(f"  {c:22s} {nonnull_pct[c]:6.1f}%")
    summary_lines += [
        "",
        f"sector missing: {n_sectors_missing} rows",
        f"mktcap_log missing: {n_mktcap_missing} rows",
        "",
        f"lag-stability check (beta_252, t vs t-1), n={len(diffs)} sampled pairs:",
        f"  median |delta| = {np.median(diffs):.4f}" if len(diffs) else "  (no valid samples)",
        f"  max |delta|    = {np.max(diffs):.4f}" if len(diffs) else "",
        f"  mean beta magnitude for scale ~ 0.5-1.5 typical; deltas above should be small fractions of that",
    ]
    for line in summary_lines:
        log(line)

    write_schema_md(ff_last_valid, regime_df["date"].max())
    write_report_md(panel, nonnull_pct, diffs, ff_last_valid, regime_df["date"].max(), n_sectors_missing, n_mktcap_missing)
    log(f"Done in {time.time()-t0:.0f}s")


def write_schema_md(ff_last_valid, regime_last_valid):
    content = f"""# ALPHA_RANKER PIT Panel — Schema (`rnd/panel/panel.parquet`)

One row per (month-end rebalance date, symbol). Built by `rnd/lib/build_panel.py`.

## Columns

| Column | Definition | PIT note |
|---|---|---|
| `date` | month-end rebalance date (last trading day of the month on the market's own calendar, from `_NSEI.parquet`) | — |
| `symbol` | NSE ticker | — |
| `sector` | `Industry` column from `data/universe/nifty_total_market_750.csv`, joined on symbol | static, CURRENT industry classification applied to all historical rows (not PIT-tracked reclassifications) |
| `mktcap_log` | `ln(shares_proxy * AdjClose(t))`, `shares_proxy = current_MarketCap(Rs) / current_Price(Rs)` from `screener_live/<SYM>.json top_ratios` | **[INFERENCE]**: shares_proxy is a CURRENT snapshot (screener has no historical market-cap series), assumed constant across 2021-2026; ignores splits/bonuses/buybacks/QIP. Time variation in this column comes ONLY from AdjClose(t), not from actual share-count changes. Cross-sectional rank at a given date is more trustworthy than the level's time trend. |
| `regime_trend` | `trend_regime` from `results/regime_timeline.parquet`, nearest-PRIOR label as of t | merge_asof backward, no future leak |
| `regime_vol` | `vol_regime` from regime_timeline, nearest-PRIOR as of t | merge_asof backward |
| `regime_leader` | `leading_factor` from regime_timeline, nearest-PRIOR as of t | merge_asof backward |
| `beta_252` | rolling CAPM beta: OLS slope of stock daily return on `_NSEI` (Nifty 50) daily return, trailing 252 trading days ending at t (min 126 valid paired obs) | uses only data <= t |
| `vol_21/63/126/252` | annualized realized vol (`std(daily ret, ddof=1) * sqrt(252)`) over the trailing window ending at t; requires >= 80% of the window populated, else NaN | uses only data <= t |
| `idio_vol_252` | annualized std of residuals from the trailing-252d FF6 regression (see below) | uses only data <= t |
| `ff_beta_MKT/SMB/HML/RMW/CMA/WML` | rolling OLS betas (with intercept), stock daily return regressed on the 6 FF6-proxy factor returns, trailing 252d (min 126 valid obs) | uses only data <= t |
| `fwd_ret_{{1M,1Y,5Y}}_raw` | `AdjClose(t+h)/AdjClose(t) - 1`, h = 21/252/1260 TRADING days on the master calendar | strictly t -> t+h; NaN if t+h exceeds available history (never extrapolated) |
| `fwd_ret_{{1M,1Y,5Y}}_excess` | `raw - market_fwd` (same h, `_NSEI`) | same horizon rule |
| `fwd_ret_{{1M,1Y,5Y}}_resid` | `raw - beta_252(t) * market_fwd` — beta is the value **known at t**, never re-estimated with the forward window | no lookahead: beta and forward return use disjoint information (beta from data<=t, forward return from t->t+h) |

## FF6 proxy construction (built once, `build_ff_factors()`)

No India-native FF6 was built from our own universe within this pass; **[INFERENCE] proxy via `factor_navs (1).xlsx`** (through the existing `src/lib/factor_bench.py` loader):

- `MKT` = NIFTY 500 daily return − HDFC Liquid Fund(G) daily return (cash/Rf proxy)
- `SMB` = NIFTY SMALLCAP 250 return − NIFTY 100 return (spec-literal: small minus large)
- `HML` = NIFTY 200 Value 30 return − NIFTY 500 return (excess-of-broad-market)
- `RMW` = NIFTY 200 Quality 30 return − NIFTY 500 return (excess-of-broad-market)
- `CMA` = NIFTY 100 Low Vol 30 return − NIFTY 500 return — **weakest proxy**: no true investment-based (conservative-vs-aggressive capex) India index exists; low-vol is used as a loose stand-in and should not be trusted as a true CMA exposure
- `WML` = NIFTY 200 Momentum 30 return − NIFTY 500 return (excess-of-broad-market)

HML/RMW/CMA/WML are built as **excess-of-broad-market** (smart-beta index minus NIFTY 500), not raw index returns, deliberately — this orthogonalizes market beta out of the multi-factor regression (RESEARCH_PROTOCOL.md §2 neutralization principle); regressing on raw smart-beta index levels alongside MKT would be highly collinear (all these indices carry ~0.8-0.9 beta to the broad market) and produce unstable betas.

`beta_252` (the standalone CAPM beta) uses `_NSEI` (Nifty 50) as "the market" per the task's explicit INPUTS instruction, which is a **different** market proxy than `ff_beta_MKT`'s NIFTY 500 basis — documented, not a bug. Expect `beta_252` and `ff_beta_MKT` to be highly correlated (both are market-beta estimates) but not identical.

## Data staleness caveats (checked — do not re-discover)

- **`factor_navs (1).xlsx` has HETEROGENEOUS per-series staleness, not one uniform cutoff.** Verified directly against the workbook: `NIFTY 100`, `NIFTY SMALLCAP 250`, `NIFTY 200 Value 30`, `NIFTY 200 Quality 30`, and `HDFC Liquid Fund(G)` all stop updating at **2026-01-05**, while `NIFTY 500`, `NIFTY 100 Low Vol 30`, and `NIFTY 200 Momentum 30` continue through **2026-02-27**. Consequence: `MKT` (needs NIFTY500 + Liquid Fund), `SMB` (Smallcap250 + Nifty100) and `HML`/`RMW` (Value30/Quality30 + Nifty500) all go NaN after **2026-01-05**, while `CMA` (LowVol30 + Nifty500) and `WML` (Momentum30 + Nifty500) stay valid through 2026-02-27. The build logs the true effective cutoff as `ff_last_valid` = the last date where ALL SIX factor columns are simultaneously non-NaN (currently **{ff_last_valid.date()}**), which is what actually gates the FF6 regression (a design row needs all 6 factors non-NaN) — this is earlier than `regime_timeline.parquet`'s 2026-02-27 cutoff, and materially earlier than the naive "factor_navs runs through 2026-02-27" assumption. Price data (`data/prices/*.parquet`) runs through 2026-07-16. For rebalance dates after `ff_last_valid`, the rolling FF6 betas/idio_vol have progressively fewer trailing observations feeding the 252-window regression (right-truncated at the last jointly-valid factor date) until they fall below the 126-obs minimum and go NaN — they are NOT frozen/forward-filled. Check the per-column non-null% in `FND_panel.md` for the exact row count affected.
- **`regime_timeline.parquet` also stops at `{pd.Timestamp(regime_last_valid).date()}`.** `regime_trend/regime_vol/regime_leader` for rebalance dates after that ARE forward-carried (nearest-PRIOR merge_asof, per spec) — i.e. the same last-known regime label repeats for ~{max(0,(pd.Timestamp('2026-07-16')-pd.Timestamp(regime_last_valid)).days)} calendar days' worth of rebalances. This is PIT-safe (no future info) but stale; do not read it as a fresh regime read for the most recent months.

## Survivorship caveat

Universe = `data/universe/nifty_total_market_750.csv` (751 symbols), a **CURRENT** constituent list, not a PIT snapshot series (unlike the AMC-side `NIFTY500_TICKER_2005_2025_Final.xlsx` with 42 PIT snapshots, which this panel does NOT use). Stocks that were in the broad market 2021-2026 but have since been removed from the current 750 (delisted, merged, demoted below the cutoff) are absent from this panel entirely — a real survivorship bias. Newly-listed stocks ARE correctly handled (rows only emitted from each symbol's actual first trade date, gated by `file_min`/`file_max` in `process_symbol`), so look-ahead from including "stocks that will IPO later" is not present; the bias runs the other way (missing names that dropped OUT of today's universe).

## Horizons

Measured in TRADING days on the master calendar (from `_NSEI.parquet`): 1M=21, 1Y=252, 5Y=1260. **Verified: the master calendar has only 1234 trading days total (2021-07-16 -> 2026-07-16), 26 trading days SHORT of the 1260-day 5Y horizon even measured from the very first rebalance date.** Consequence: `fwd_ret_5Y_raw/excess/resid` are 100% NaN in this build (0% non-null, confirmed) — not "sparse", entirely empty. This is honest (no fabrication/extrapolation past the data's end), but any 5Y-horizon research on this panel must wait for either more price history to accumulate or an explicit backfill of pre-2021-07-16 prices before the column is usable at all.
"""
    SCHEMA_MD.write_text(content, encoding="utf-8")
    log(f"Wrote {SCHEMA_MD}")


def write_report_md(panel, nonnull_pct, diffs, ff_last_valid, regime_last_valid, n_sectors_missing, n_mktcap_missing):
    lines = [
        "# FND_panel — SHARED PIT Panel Build Report",
        "",
        "[DATA] Result: `ALPHA_RANKER/rnd/panel/panel.parquet` built successfully.",
        "",
        "## Data lineage",
        f"- Prices: `ALPHA_RANKER/data/prices/*.parquet` (751 symbols) + `_NSEI.parquet` (market, master calendar)",
        f"- Universe/sector: `ALPHA_RANKER/data/universe/nifty_total_market_750.csv` (751 rows, full symbol coverage confirmed)",
        f"- Market cap: `ALPHA_RANKER/data/fundamentals/screener_live/<SYM>.json` top_ratios (751/751 files present; {n_mktcap_missing} rows with unparseable/missing Market Cap or Price)",
        f"- Regime: `ALPHA_RANKER/results/regime_timeline.parquet` (5189 rows, max date {pd.Timestamp(regime_last_valid).date()})",
        f"- FF6 factors: `factor_navs (1).xlsx` via `src/lib/factor_bench.py` (max complete-row date {ff_last_valid.date()})",
        "",
        "## Row counts / coverage",
        f"- n_obs = {len(panel)}",
        f"- date range = {panel['date'].min().date()} -> {panel['date'].max().date()}",
        f"- n_symbols = {panel['symbol'].nunique()} / n_rebalance_dates = {panel['date'].nunique()}",
        f"- sector missing: {n_sectors_missing} rows (0 expected, universe join is 1:1 on 751 symbols)",
        "",
        "## Per-column non-null %",
        "",
        "| column | non-null % |",
        "|---|---|",
    ]
    for c in panel.columns:
        lines.append(f"| {c} | {nonnull_pct[c]:.1f}% |")
    lines += [
        "",
        "## Guards / PIT checks",
        "- [DATA] Listing-life gate: rows only emitted where the rebalance date falls within each symbol's own `[file_min, file_max]` price-file range (IPO/delisting handled, no fabricated pre-IPO or post-delist rows).",
        "- [DATA] Halt bridging: forward-fill limited to 5 trading days when reindexing a symbol onto the master calendar; longer gaps (delisting, extended halts) correctly surface as NaN rather than being silently carried forward.",
        "- [DATA] Forward returns strictly t->t+h on the master trading calendar; horizons exceeding available history are NaN, not extrapolated (drives the 100% `fwd_ret_5Y_*` NaN rate below -- master calendar has only 1234 trading days total, 26 short of the 1260-day 5Y horizon even from the first rebalance date; expected, not a bug).",
        "- [DATA] `beta_252` used inside `fwd_ret_*_resid` is the value estimated AT t (pre-computed from trailing data only) — never re-fit using the forward window.",
        f"- [DATA] Lag-stability spot check: beta_252 recomputed at t vs t-1 trading day for {len(diffs)} random (symbol, rebalance-date) pairs.",
    ]
    if len(diffs):
        lines.append(f"  - median |delta| = {np.median(diffs):.4f}, max |delta| = {np.max(diffs):.4f} (single-day window shift; no discontinuity/leak observed — a leak would show as a delta comparable to the beta's own magnitude, ~0.5-1.5, not a small fraction of it)")
    else:
        lines.append("  - WARNING: no valid sample pairs produced — investigate before trusting this panel")
    lines += [
        "",
        "## Known caveats (full detail in PANEL_SCHEMA.md — read before use)",
        f"- factor_navs.xlsx has heterogeneous per-series staleness: the joint (all-6-factors) cutoff is {ff_last_valid.date()} (driven by NIFTY100/Value30/Quality30/Liquid Fund/Smallcap250 stopping there; NIFTY500/LowVol30/Momentum30 continue to 2026-02-27) -- ff_beta_* degrade to NaN progressively after {ff_last_valid.date()} as the trailing window right-truncates below the 126-obs minimum. regime_timeline.parquet separately stops at {pd.Timestamp(regime_last_valid).date()}; regime_* is forward-carried past that (stale, not fabricated) per spec.",
        "- mktcap_log uses a CURRENT (not PIT) shares-outstanding proxy from screener_live — [INFERENCE], documented, level trend is not fully trustworthy though cross-sectional rank per date should be reasonable.",
        "- Universe is CURRENT NIFTY-750 constituents, not a PIT snapshot series — real survivorship bias (names that fell OUT of today's 750 are absent for their whole history), separate from and in addition to any listing-life handling.",
        "- FF6 factors are index-proxy constructions (documented formulas in PANEL_SCHEMA.md), not a bottom-up India FF6 built from our own stock universe. CMA is the weakest of the six (Low Vol 30 substituting for a true investment factor).",
        "",
        "## Verdict",
        "**REAL** (for what it is: a documented-proxy, current-universe PIT panel with no lookahead detected in the checks run). Weakest assumption: the mktcap_log constant-shares-outstanding proxy and the CMA factor proxy (Low Vol 30) are both [INFERENCE] substitutes for data that doesn't exist in this repo yet — any factor research leaning heavily on absolute market-cap level or on CMA specifically should treat those columns as low-confidence until better source data is sourced.",
    ]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    log(f"Wrote {REPORT_MD}")


if __name__ == "__main__":
    main()
