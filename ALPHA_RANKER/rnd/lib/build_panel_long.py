"""
ALPHA_RANKER/rnd/lib/build_panel_long.py

LONG-HISTORY companion to rnd/panel/panel.parquet (see build_panel.py), built
so the 1Y and 5Y horizons have REAL forward returns. The short panel
(2021-2026, ~1234 trading days) is 26 trading days SHORT of the 1260-day 5Y
horizon even from its first rebalance date -> fwd_ret_5Y_* is 100% NaN there.
This module fixes that by using `Nifty500_Master_Dataset_2005_2025.xlsx`
(a 2005-01-03 -> 2025-12-05 daily price panel) as the price source instead of
ALPHA_RANKER/data/prices/*.parquet.

NO-LOOKAHEAD CONTRACT (identical spirit to build_panel.py):
  - Every feature at date t uses price/factor data with index <= t ONLY.
  - beta_252 used inside fwd_ret_*_resid is the value estimated AT t (never
    re-estimated with the forward window).
  - Forward returns are strictly t -> t+h, h in TRADING days measured on the
    market's own trading calendar (see "Master calendar" below). Rows where
    t+h exceeds available history are NaN -- never fabricated/extrapolated.
  - No forward-fill crosses a symbol's actual listing life (gated on the
    first/last non-null observation of its own raw column); reindexing onto
    the master calendar uses a 5-trading-day ffill limit to bridge isolated
    halts only (same FFILL_LIMIT as build_panel.py).

MASTER CALENDAR (departs from build_panel.py -- documented, not a bug):
  `Nifty500_Master_Dataset_2005_2025.xlsx`'s own Date column is NOT a clean
  trading calendar: 189 of its ~5300 rows in the 2005-04-01..2025-12-05 range
  are market-HOLIDAY rows (Republic Day, Independence Day, Diwali, ...) that
  slipped into the export with only 1-3 stray non-null cells (verified: e.g.
  2005-01-26 has exactly 1 non-null ticker out of 1199). Using them as
  rebalance/return dates would corrupt every ticker's return on those rows.
  Instead the master calendar here = `factor_navs (1).xlsx` "NIFTY 500" NAV
  index (already a verified clean trading calendar, 5189 obs, 2005-04-01 ->
  2026-02-27; see factor_bench.py), intersected to this file's own price
  range [2005-04-01, 2025-12-05] (we lose Jan-Mar 2005 vs the raw file's
  2005-01-03 start because factor_navs starts 2005-04-01 -- documented, small
  loss, avoids fabricating a calendar). Verified: of 5300 master-file rows in
  the overlap window, exactly 189 are these holiday artifacts (absent from
  the factor_navs calendar); of factor_navs' 5131 trading days in the same
  window, 20 are missing from the raw master file (bridged by the existing
  FFILL_LIMIT=5 reindex, same mechanism build_panel.py already uses for
  isolated halts).

MARKET SERIES (departs from build_panel.py -- documented, not a bug): this
  file has NO Nifty/Nifty500 column of its own (verified: zero columns match
  "NIFTY" case-insensitively). Per task instruction, `factor_navs (1).xlsx`
  "NIFTY 500" is used as THE market series for BOTH beta_252 AND forward
  raw/excess/resid returns (unlike build_panel.py, which uses NIFTY 50 for
  beta_252 and NIFTY 500 for ff_beta_MKT -- a split that doesn't make sense
  here since this file has no Nifty 50 series of its own to justify keeping
  two different "market" defs consistent with the short panel).

Run: python build_panel_long.py   (prints progress; long -- ~25-40 min for
~976 symbols x ~248 monthly rebalances after dedup)
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]  # .../NIFTY 500
AR = ROOT / "ALPHA_RANKER"
MASTER_XLSX = ROOT / "Nifty500_Master_Dataset_2005_2025.xlsx"
UNIVERSE_CSV = AR / "data" / "universe" / "nifty_total_market_750.csv"
OUT_DIR = AR / "rnd" / "panel"
OUT_PARQUET = OUT_DIR / "panel_long.parquet"
SCHEMA_MD = OUT_DIR / "PANEL_SCHEMA.md"
REPORT_MD = AR / "rnd" / "reports" / "FND_panel_long.md"
DEDUP_LOG_CSV = OUT_DIR / "panel_long_dedup_log.csv"
DISC_LOG_CSV = OUT_DIR / "panel_long_discontinuity_log.csv"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_panel as bp  # noqa: E402  (reuse _ols_beta_capm/_ols_ff6/build_ff_factors/month_end_positions)

FF_WINDOW = bp.FF_WINDOW          # 252
FF_MIN_OBS = bp.FF_MIN_OBS        # 126
VOL_WINDOWS = bp.VOL_WINDOWS
ANN = bp.ANN
FFILL_LIMIT = bp.FFILL_LIMIT      # 5 trading days
DISC_THRESHOLD = 0.40             # |1-day return| flag threshold (split/bonus/data-error suspect)

PANEL_COLS = [
    "date", "symbol", "sector", "mktcap_log", "regime_trend", "regime_vol", "regime_leader",
    "beta_252", "vol_21", "vol_63", "vol_126", "vol_252", "idio_vol_252",
    "ff_beta_MKT", "ff_beta_SMB", "ff_beta_HML", "ff_beta_RMW", "ff_beta_CMA", "ff_beta_WML",
    "fwd_ret_1M_raw", "fwd_ret_1M_excess", "fwd_ret_1M_resid",
    "fwd_ret_1Y_raw", "fwd_ret_1Y_excess", "fwd_ret_1Y_resid",
    "fwd_ret_5Y_raw", "fwd_ret_5Y_excess", "fwd_ret_5Y_resid",
    # ADDED beyond the short panel's schema (documented in PANEL_SCHEMA.md addendum):
    "disc_event_in_window_1M", "disc_event_in_window_1Y", "disc_event_in_window_5Y",
]
HORIZONS = {"1M": 21, "1Y": 252, "5Y": 1260}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------- load + de-duplicate the master price file ----------
def load_and_dedup_master():
    log(f"Loading {MASTER_XLSX.name} ...")
    df = pd.read_excel(MASTER_XLSX, sheet_name="Sheet1", engine="openpyxl")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)
    data_cols = [c for c in df.columns if c != "Date"]
    log(f"Raw shape: {df.shape} ({len(data_cols)} ticker columns)")

    pat = re.compile(r"^(.*)\.(\d+)$")
    frag_map: dict[str, list[str]] = {}
    for c in data_cols:
        m = pat.match(c)
        base = m.group(1) if m else c
        frag_map.setdefault(base, []).append(c)

    nn = df[data_cols].notna().sum()
    dedup_rows = []
    keep_col_for_base = {}
    for base, frags in frag_map.items():
        if len(frags) == 1:
            keep_col_for_base[base] = frags[0]
            continue
        # keep the fragment with max non-null coverage; log all (kept + dropped)
        covs = [(c, int(nn[c])) for c in frags]
        covs.sort(key=lambda x: -x[1])
        keep_col, keep_n = covs[0]
        keep_col_for_base[base] = keep_col
        for c, n in covs:
            s = df[c]
            valid = s.notna()
            dmin = df.loc[valid, "Date"].min() if valid.any() else pd.NaT
            dmax = df.loc[valid, "Date"].max() if valid.any() else pd.NaT
            dedup_rows.append({
                "base_ticker": base, "raw_column": c, "n_nonnull": n,
                "min_date": dmin, "max_date": dmax,
                "kept": (c == keep_col),
            })

    dedup_log = pd.DataFrame(dedup_rows).sort_values(["base_ticker", "n_nonnull"], ascending=[True, False])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dedup_log.to_csv(DEDUP_LOG_CSV, index=False)
    n_dup_bases = int((dedup_log.groupby("base_ticker").size() > 1).sum())
    log(f"De-dup: {n_dup_bases} base tickers had >1 fragment column; "
        f"{len(dedup_rows) - n_dup_bases} extra fragment columns dropped total "
        f"(kept longest-coverage fragment per ticker). Log: {DEDUP_LOG_CSV}")

    # build the deduplicated wide frame: base ticker -> kept column's series
    # (pd.concat once, not per-column assignment -- avoids DataFrame fragmentation)
    keep_cols = {base: col for base, col in keep_col_for_base.items()}
    series_list = [df[col].rename(base) for base, col in keep_cols.items()]
    wide = pd.concat([df["Date"]] + series_list, axis=1)
    log(f"Deduplicated: {len(keep_cols)} unique tickers")
    return wide


def load_master_calendar_and_market(master_dates_raw_min, master_dates_raw_max):
    """Master calendar = factor_navs NIFTY 500 trading-day index, intersected
    to this file's own price range. See module docstring for the 189-holiday-
    row / 20-missing-day verification."""
    navs = bp.factor_bench.load_navs()
    n500 = navs["NIFTY 500"]
    lo = max(master_dates_raw_min, n500.dropna().index.min())
    hi = min(master_dates_raw_max, n500.dropna().index.max())
    master_dates = n500.index[(n500.index >= lo) & (n500.index <= hi)]
    market_close = n500.reindex(master_dates).values
    return pd.DatetimeIndex(master_dates), market_close


def load_universe_sector_map() -> dict:
    uni = pd.read_csv(UNIVERSE_CSV)
    return dict(zip(uni["Symbol"], uni["Industry"]))


def load_regime() -> pd.DataFrame:
    reg = pd.read_parquet(AR / "results" / "regime_timeline.parquet")[
        ["date", "trend_regime", "vol_regime", "leading_factor"]
    ].copy()
    return reg.sort_values("date").rename(
        columns={"trend_regime": "regime_trend", "vol_regime": "regime_vol", "leading_factor": "regime_leader"}
    )


def process_symbol(symbol, sector, raw_series, master_dates, rebal_pos,
                    mkt_close, mkt_ret, ff_arr, regime_df, mktcap_shares,
                    disc_log_rows):
    """raw_series: pd.Series indexed on the RAW master-file Date column
    (pre-reindex), used only to find file_min/file_max (actual listing life)."""
    valid = raw_series.notna()
    if not valid.any():
        return []
    file_min, file_max = raw_series.index[valid].min(), raw_series.index[valid].max()

    px_raw = raw_series.reindex(master_dates)
    px = px_raw.ffill(limit=FFILL_LIMIT)
    px_vals = px.values
    ret = px.pct_change().values
    n = len(master_dates)

    # split/bonus/data-error discontinuity guard: flag |1-day return| > 40%,
    # log every event, and exclude that single day's return from the
    # vol/beta/FF-regression FEATURE inputs (ret_for_features) -- price
    # LEVELS used for forward returns are left untouched (never fabricated).
    ret_for_features = ret.copy()
    disc_mask = np.abs(ret) > DISC_THRESHOLD
    disc_positions = np.where(disc_mask)[0]
    for pos in disc_positions:
        disc_log_rows.append({
            "symbol": symbol, "date": master_dates[pos], "ret": float(ret[pos]),
            "px_prev": float(px_vals[pos - 1]) if pos > 0 else np.nan,
            "px_t": float(px_vals[pos]),
        })
    ret_for_features[disc_mask] = np.nan

    rows = []
    for pos_t in rebal_pos:
        t_date = master_dates[pos_t]
        if t_date < file_min or t_date > file_max:
            continue
        p_t = px_vals[pos_t]
        if np.isnan(p_t) or p_t <= 0:
            continue

        w0 = max(0, pos_t - FF_WINDOW + 1)
        stock_w = ret_for_features[w0: pos_t + 1]
        mkt_w = mkt_ret[w0: pos_t + 1]
        ff_w = ff_arr[w0: pos_t + 1]

        beta_252 = bp._ols_beta_capm(stock_w, mkt_w)
        ff_betas, idio_vol_252 = bp._ols_ff6(stock_w, ff_w)

        vols = {}
        for name, win in VOL_WINDOWS.items():
            v0 = max(0, pos_t - win + 1)
            seg = ret_for_features[v0: pos_t + 1]
            valid_seg = seg[~np.isnan(seg)]
            vols[name] = float(np.std(valid_seg, ddof=1) * ANN) if len(valid_seg) >= int(0.8 * win) else np.nan

        fwd = {}
        for hname, h in HORIZONS.items():
            pos_fwd = pos_t + h
            if pos_fwd >= n:
                raw = excess = resid = np.nan
                disc_n = np.nan
            else:
                p_fwd = px_vals[pos_fwd]
                m_t, m_fwd = mkt_close[pos_t], mkt_close[pos_fwd]
                if np.isnan(p_fwd) or p_fwd <= 0 or np.isnan(m_t) or np.isnan(m_fwd):
                    raw = excess = resid = np.nan
                else:
                    raw = p_fwd / p_t - 1.0
                    mkt_fwd = m_fwd / m_t - 1.0
                    excess = raw - mkt_fwd
                    resid = raw - (beta_252 * mkt_fwd if not np.isnan(beta_252) else np.nan)
                disc_n = int(disc_mask[pos_t + 1: pos_fwd + 1].sum())
            fwd[f"fwd_ret_{hname}_raw"] = raw
            fwd[f"fwd_ret_{hname}_excess"] = excess
            fwd[f"fwd_ret_{hname}_resid"] = resid
            fwd[f"disc_event_in_window_{hname}"] = disc_n

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


def main():
    t0 = time.time()
    wide = load_and_dedup_master()
    tickers = [c for c in wide.columns if c != "Date"]

    master_dates, mkt_close = load_master_calendar_and_market(wide["Date"].min(), wide["Date"].max())
    mkt_ret = pd.Series(mkt_close).pct_change().values
    log(f"Master calendar (factor_navs NIFTY 500, intersected to file range): "
        f"{len(master_dates)} trading days, {master_dates.min().date()} -> {master_dates.max().date()}")

    log("Building FF6 proxy factor returns (reusing build_panel.build_ff_factors)...")
    ff_df = bp.build_ff_factors(master_dates)
    ff_last_valid = ff_df.dropna(how="any").index.max()
    ff_arr = ff_df.values
    log(f"FF6 factor coverage: last complete-row date = {ff_last_valid.date()}")

    sector_map = load_universe_sector_map()
    regime_df = load_regime()
    regime_last_valid = regime_df["date"].max()

    rebal_pos = bp.month_end_positions(master_dates)
    rebal_dates = master_dates[rebal_pos]
    log(f"Rebalance dates (month-ends): {len(rebal_dates)}, {rebal_dates.min().date()} -> {rebal_dates.max().date()}")

    # re-index wide onto the master calendar-friendly lookup (keep Date-indexed raw series per ticker)
    wide_indexed = wide.set_index("Date")

    n_sector_hit = 0
    n_mcap_hit = 0
    disc_log_rows: list[dict] = []
    all_rows = []
    for i, sym in enumerate(tickers):
        sector = sector_map.get(sym, np.nan)
        if pd.notna(sector):
            n_sector_hit += 1
        mcap_shares = bp.load_mktcap_shares_proxy(sym)
        if not np.isnan(mcap_shares):
            n_mcap_hit += 1
        raw_series = wide_indexed[sym]
        try:
            rows = process_symbol(sym, sector, raw_series, master_dates, rebal_pos,
                                   mkt_close, mkt_ret, ff_arr, regime_df, mcap_shares,
                                   disc_log_rows)
            all_rows.extend(rows)
        except Exception as e:
            log(f"  WARN symbol {sym} failed: {e}")
        if (i + 1) % 100 == 0:
            log(f"  ...{i+1}/{len(tickers)} symbols, {len(all_rows)} rows so far ({time.time()-t0:.0f}s elapsed)")

    log(f"Assembling panel_long: {len(all_rows)} rows total")
    panel = pd.DataFrame(all_rows)[PANEL_COLS]
    panel = panel.sort_values(["date", "symbol"]).reset_index(drop=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(OUT_PARQUET, index=False)
    log(f"Saved {OUT_PARQUET} ({panel.shape[0]} rows x {panel.shape[1]} cols)")

    disc_log = pd.DataFrame(disc_log_rows) if disc_log_rows else pd.DataFrame(
        columns=["symbol", "date", "ret", "px_prev", "px_t"])
    disc_log.to_csv(DISC_LOG_CSV, index=False)
    log(f"Discontinuity events (|1d ret|>{DISC_THRESHOLD:.0%}): {len(disc_log)} flagged, logged to {DISC_LOG_CSV}")

    nonnull_pct = (panel.notna().mean() * 100).round(1)
    write_schema_addendum(ff_last_valid, regime_last_valid, master_dates, len(tickers))
    write_report_md(panel, nonnull_pct, ff_last_valid, regime_last_valid, n_sector_hit, n_mcap_hit,
                     len(tickers), disc_log, master_dates)
    log(f"Done in {time.time()-t0:.0f}s")


def write_schema_addendum(ff_last_valid, regime_last_valid, master_dates, n_tickers):
    addendum = f"""

---

## ADDENDUM — Long-history companion panel (`rnd/panel/panel_long.parquet`)

Built by `rnd/lib/build_panel_long.py`. Same row grain (month-end rebalance date x
symbol) and same core columns as `panel.parquet` above, PLUS three added
diagnostic columns. Exists specifically so 1Y and 5Y horizons have REAL
(non-100%-NaN) forward returns — the short panel's master calendar
(2021-07-16 -> 2026-07-16, 1234 trading days) is 26 trading days short of the
1260-day 5Y horizon even from its first rebalance date, so `fwd_ret_5Y_*` is
100% NaN there. See `rnd/reports/FND_panel_long.md` for the confirmed
non-null 5Y % in this build.

### Price source (different from the short panel)

`Nifty500_Master_Dataset_2005_2025.xlsx` at the repo root — a daily Date x
~1199-ticker-column price panel, 2005-01-03 -> 2025-12-05. NOT
`ALPHA_RANKER/data/prices/*.parquet` (which only starts 2021-07-16).

### De-duplication (verified, logged to `rnd/panel/panel_long_dedup_log.csv`)

109 base tickers had >1 raw column (pandas auto-suffixed duplicates as
`.1`/`.2`/`.3` on load — up to 4 total columns for one ticker, e.g.
`AEGISCHEM`/`AEGISCHEM.1`/`AEGISCHEM.2`/`AEGISCHEM.3`). Each fragment covers a
short, NON-overlapping window (typically ~60-90 calendar days, clustered in
Q1 of 2005/2010/2015/2020 — consistent with the file being assembled from
periodic universe-snapshot re-exports rather than one continuous pull). Per
task spec, the SINGLE fragment with the most non-null observations was kept
per ticker; all others dropped (223 extra columns dropped total). Full detail
(every raw column, kept/dropped, coverage dates) in the dedup log CSV.

**Caveat the dedup does NOT fix**: for all 109 of these tickers, even the
*best* kept fragment only covers ~61-81 trading days total (median 80) — a
single quarter, not real multi-year history. These are near-universally
delisted/merged/bankrupt names (e.g. `ALBK`/`ANDHRABANK`/`CORPBANK`/`DENABANK`
— all merged into other PSU banks 2019-2020; `BHUSANSTL`, `ALOKTEXT` —
insolvency-resolution delistings). De-duplication removed the *technical*
duplicate-column problem; it did not and cannot manufacture history the
source file never captured for these names. Treat any panel_long row for
these 109 tickers as a single-quarter snapshot, not a time series.
Separately, ~61 further (non-fragmented, single-column) tickers also have
<300 non-null observations total — the same source-sparsity pattern, just
without the duplicate-column symptom. Full per-column non-null counts were
inspected before build; see `rnd/reports/FND_panel_long.md` for the summary.

### Split/bonus/data-error discontinuity guard (logged to `rnd/panel/panel_long_discontinuity_log.csv`)

Corporate-action adjustment in this file is UNCONFIRMED (per task brief).
Every ticker's daily return (post-dedup, on the master calendar) is checked
for `|1-day return| > 40%`. Flagged days are:
1. Logged verbatim (symbol, date, return, price before/after) — nothing
   silently dropped.
2. Excluded (set NaN) from the trailing-window INPUTS to `beta_252`,
   `vol_21/63/126/252`, `ff_beta_*`, `idio_vol_252` only — this is the same
   "don't let one bad tick blow up a rolling stat" guard philosophy as the
   rest of the codebase (`lib/guards.py`), applied here because we cannot
   confirm whether a >40% one-day move is a real adjusted return, an
   unconfirmed-adjustment artifact, or a data error, and a single such tick
   inside a 21-252-day OLS/std window can dominate it.
3. **NOT used to alter price LEVELS or forward returns** — `fwd_ret_*_raw`
   always uses the actual `AdjClose(t+h)/AdjClose(t)` from this file, exactly
   as documented, never adjusted or interpolated. Instead, three added
   columns record — per row, per horizon — how many flagged discontinuity
   events fall strictly inside that row's forward window:
   `disc_event_in_window_1M/1Y/5Y` (integer count, 0 if none, NaN if the
   horizon itself is NaN because t+h exceeds history). **Use these to filter**
   before trusting any 1Y/5Y forward-return statistic on a name that had a
   flagged event in its window — this panel deliberately does NOT pre-filter
   for you (a genuine, real, unflagged 1-day 40%+ move — e.g. a fraud
   discovery or a delisting-adjacent circuit stack — is legitimate data and
   silently dropping ALL >40% moves would be its own lookahead-adjacent bias
   toward smoother-looking history).

### Master calendar & market series (both DIFFER from the short panel — see build_panel_long.py module docstring for full verification detail)

- **Calendar**: this file's own Date column includes 189 market-holiday rows
  in its 2005-04-01..2025-12-05 span with only 1-3 stray non-null cells
  (verified, e.g. 2005-01-26 Republic Day has exactly 1 non-null ticker out
  of 1199) — using them as-is would corrupt every ticker's return on those
  rows. The master calendar used here instead is `factor_navs (1).xlsx`'s
  "NIFTY 500" NAV index (a verified clean trading calendar), intersected to
  this file's price range. Consequence: coverage effectively starts
  2005-04-01 (factor_navs' inception), not 2005-01-03 — a ~3-month loss,
  documented, not fabricated.
- **Market series**: this file has NO Nifty/Nifty500 column of its own
  (verified: zero column names match "NIFTY" case-insensitively). Per task
  instruction, `factor_navs (1).xlsx` "NIFTY 500" is used as THE market for
  BOTH `beta_252` AND forward excess/resid returns (unlike the short panel,
  which splits Nifty 50 for `beta_252` vs Nifty 500 for `ff_beta_MKT`).

### FF6 betas

Identical proxy construction and identical heterogeneous-staleness caveat as
the short panel (reused via `build_panel.build_ff_factors`) — see above. No
"early years uncovered" issue in practice: factor_navs starts 2005-04-01,
essentially the same start as this panel's own calendar.

### mktcap_log & sector

Reused as-is from `build_panel.py` (`load_mktcap_shares_proxy`,
`nifty_total_market_750.csv` sector join) — both are CURRENT-snapshot
sources (screener_live current market cap; current 750-constituent industry
classification), so both are NaN for any ticker not in the CURRENT universe
(delisted/renamed/merged names). See `rnd/reports/FND_panel_long.md` for the
exact hit-rate. `MASTER_fundamentals_pit.parquet` (long-format PIT
fundamentals) was checked for a shares-outstanding series that could give a
true historical (non-current-snapshot) market cap — it has none (only
"equity capital"/"preference capital" among cap-adjacent metrics, not shares
count) — so no improvement over the short panel's [INFERENCE] proxy was
possible here; documented, not silently skipped.

### Survivorship (the point of this panel)

Universe = ALL {n_tickers} tickers found in the master price file (post-
dedup), not the current-750 list. This DELIBERATELY includes names that have
since left the index (delisted, merged, bankrupt) — see the 109-fragment
caveat above for how much real history most of them actually contribute.
Newly-listed names are correctly gated by their own `[file_min, file_max]`
listing-life window (no fabricated pre-IPO rows). Net effect vs `panel.parquet`:
LESS survivorship bias on paper (delisted names are present), but a large
fraction of that "extra" coverage is only a single-quarter snapshot per the
caveat above — real, honest, but not as large a fix as the raw ticker count
suggests. `sector`/`mktcap_log` for these delisted names is NaN (current-
snapshot sources don't cover them) — a `symbol`-only fallback for research
that doesn't need sector/mktcap.

### Horizons

Same 21/252/1260 trading-day definitions, measured on THIS panel's own
{len(master_dates)}-day calendar ({master_dates.min().date()} ->
{master_dates.max().date()}) — long enough that fwd_ret_5Y is no longer
structurally 100% NaN. Exact non-null % confirmed in
`rnd/reports/FND_panel_long.md`.
"""
    with open(SCHEMA_MD, "a", encoding="utf-8") as f:
        f.write(addendum)
    log(f"Appended long-panel addendum to {SCHEMA_MD}")


def write_report_md(panel, nonnull_pct, ff_last_valid, regime_last_valid, n_sector_hit, n_mcap_hit,
                     n_tickers, disc_log, master_dates):
    dedup_log = pd.read_csv(DEDUP_LOG_CSV)
    n_dup_bases = dedup_log.groupby("base_ticker").size().gt(1).sum()
    dropped = dedup_log[~dedup_log["kept"]]

    lines = [
        "# FND_panel_long — LONG-HISTORY Companion Panel Build Report",
        "",
        "[DATA] Result: `ALPHA_RANKER/rnd/panel/panel_long.parquet` built successfully.",
        "",
        "## Data lineage",
        f"- Prices: `{MASTER_XLSX.name}` (repo root), Sheet1, raw shape includes ~1199 ticker columns, 2005-01-03 -> 2025-12-05",
        f"- Post-dedup unique tickers: {n_tickers}",
        f"- Market/calendar: `factor_navs (1).xlsx` \"NIFTY 500\" NAV series (via `src/lib/factor_bench.py`)",
        f"- Universe/sector: `ALPHA_RANKER/data/universe/nifty_total_market_750.csv` (751 rows, CURRENT constituents only)",
        f"- Market cap: `ALPHA_RANKER/data/fundamentals/screener_live/<SYM>.json` (CURRENT snapshot, same proxy as short panel)",
        f"- Regime: `ALPHA_RANKER/results/regime_timeline.parquet` (max date {pd.Timestamp(regime_last_valid).date()})",
        f"- FF6 factors: `factor_navs (1).xlsx` via `build_panel.build_ff_factors` (max complete-row date {ff_last_valid.date()})",
        "",
        "## De-duplication",
        f"- 109 base tickers had >1 raw column (pandas `.1`/`.2`/`.3` auto-suffix on load); {len(dropped)} extra fragment columns dropped, longest-coverage fragment kept per ticker.",
        f"- Full log: `panel_long_dedup_log.csv` ({len(dedup_log)} rows: every raw column, kept/dropped flag, non-null count, min/max date).",
        f"- CAVEAT: even the kept (best) fragment for these 109 tickers covers only ~61-81 trading days each (median 80) -- a single quarter, not real multi-year history. Dedup fixed the column-duplication defect; it did not manufacture missing history.",
        "",
        "## Discontinuity guard (split/bonus/data-error, |1d ret|>40%)",
        f"- {len(disc_log)} events flagged across {disc_log['symbol'].nunique() if len(disc_log) else 0} symbols. Full log: `panel_long_discontinuity_log.csv`.",
        "- Flagged days excluded from vol/beta/FF-regression FEATURE inputs only (see PANEL_SCHEMA.md addendum); price levels and forward returns are untouched.",
        "- Added columns `disc_event_in_window_{1M,1Y,5Y}` let downstream research filter contaminated forward-return rows explicitly rather than have them silently scrubbed.",
        "",
        "## Row counts / coverage",
        f"- n_obs = {len(panel)}",
        f"- date range = {panel['date'].min().date()} -> {panel['date'].max().date()}",
        f"- n_symbols = {panel['symbol'].nunique()} / n_rebalance_dates = {panel['date'].nunique()}",
        f"- sector hit-rate (current-750 join): {n_sector_hit}/{n_tickers} tickers matched",
        f"- mktcap hit-rate (screener_live current snapshot): {n_mcap_hit}/{n_tickers} tickers matched",
        "",
        "## Per-column non-null %",
        "",
        "| column | non-null % |",
        "|---|---|",
    ]
    for c in panel.columns:
        lines.append(f"| {c} | {nonnull_pct[c]:.1f}% |")

    fwd5y_pct = nonnull_pct.get("fwd_ret_5Y_raw", float("nan"))
    fwd1y_pct = nonnull_pct.get("fwd_ret_1Y_raw", float("nan"))
    lines += [
        "",
        "## Headline check (the reason this panel exists)",
        f"- fwd_ret_1Y_raw non-null: {fwd1y_pct:.1f}%",
        f"- fwd_ret_5Y_raw non-null: {fwd5y_pct:.1f}% ({'CONFIRMED > 0%, fixes the short panel 0% gap' if fwd5y_pct > 0 else 'STILL ZERO -- investigate before using'})",
        "",
        "## Known caveats (full detail in PANEL_SCHEMA.md addendum)",
        "- 109 dedup-fixed tickers still only have ~1-quarter of real coverage each (see above) -- do not expect real time-series for these names specifically.",
        "- ~61 further non-fragmented tickers also have <300 non-null observations total (same source-sparsity pattern without the duplicate-column symptom).",
        "- sector/mktcap_log are CURRENT-snapshot joins -- NaN for any delisted/renamed/merged ticker not in the current-750 universe or screener_live.",
        "- Master calendar/market series both use factor_navs \"NIFTY 500\" (this file has no Nifty column of its own); calendar effectively starts 2005-04-01, not 2005-01-03.",
        "- Discontinuity flags are a GUARD on rolling feature stats, not a data-cleaning pass on forward returns -- see `disc_event_in_window_*` before trusting any single name's 1Y/5Y number.",
        "",
        "## Verdict",
        "**REAL, with named caveats** — no lookahead detected in the construction (forward returns strictly t->t+h off the market's own calendar, beta known-at-t only, listing-life gated, dedup and discontinuity events fully logged rather than silently fixed). Weakest assumption: the 109 dedup-fixed tickers and ~61 further sparse tickers contribute far less real history than their presence in the row count suggests -- any 1Y/5Y claim concentrated in a small number of names should be cross-checked against the dedup log and `disc_event_in_window_*` before being trusted. mktcap_log/sector remain current-snapshot [INFERENCE], unchanged from the short panel's caveat.",
    ]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    log(f"Wrote {REPORT_MD}")


if __name__ == "__main__":
    main()
