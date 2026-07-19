"""
WAVE-2 worker: single-stock OPTIONS-FLOW factor builders for the ALPHA_RANKER
research loop (money-first; hard gates = lag+placebo via rnd/lib/harness.py).

DATA SOURCE (legacy, read-only per root CLAUDE.md):
  intraday_options_strategy/datasets/raw/hf_index_options_1m/stocks_options/<SYMBOL>/<cycle_end_date>.parquet
  Columns: strike, option_type(CE/PE), open/high/low/close, settle, volume, oi,
           trading_day, timestamp.
  One file per near-month (front-month only, no far-month mixed in — verified:
  46-90 strikes/day, no expiry column) options cycle, spanning from the day
  after the PRIOR expiry through the cycle's own expiry day (file name =
  expiry/cycle-end date).

COVERAGE (checked honestly, see W2_OPT_DATA_COVERAGE.md):
  - 210 F&O-eligible symbols (subset of the 751-symbol panel universe).
  - 62 distinct cycle-end dates, 2021-07-29 .. 2026-08-25 (matches the panel's
    2021-07..2026-07 span).
  - Cross-section GROWS over time: ~25-29 symbols/cycle in H2-2021 up to
    ~190-210 by 2025-26 (universe onboarded gradually, not a uniform panel).
  - PATCHY even within a single symbol's own history — e.g. RELIANCE (surely
    F&O-liquid throughout) is missing 2021 H2 entirely plus several 2022/2023
    cycles. This is real: a genuinely single-stock, cross-sectional dataset,
    just not a dense/complete one. The harness's `min_names_per_date` gate is
    the honesty check on any given date's cross-section size.

LANDMINE AVOIDED (root CLAUDE.md landmine #9): on the expiry (last) trading
day, bhavcopy-style `settle`/`SETTLE_PR` = the UNDERLYING's final settlement
level, not an option price. This module never reads `settle` — only `oi`,
`close` (intraday option close, not settle) and `volume`.

PIT discipline: for panel date t, we use the most-recently-COMPLETED cycle
file whose last `trading_day` <= t (backward match, tolerance <=40 calendar
days) — never a file whose data extends past t.

Factors:
  build_pcr_oi(panel)    -> W2_OPT_PCR:    put-OI / call-OI on the last trading
                            day of the most-recent completed cycle as of t.
                            Contrarian-sentiment framing: high PCR = crowded
                            put positioning.
  build_oi_price_flow(panel) -> W2_OPT_OIFLOW: within-cycle correlation of
                            daily total OI (all strikes/types) vs the
                            underlying's daily close (cube_close) over the
                            cycle's trading days. +1-ish = OI built UP as price
                            rose (long-buildup-dominant cycle); -1-ish = OI
                            built up as price fell (short-buildup-dominant) —
                            a monthly aggregate of the classic long/short
                            OI-buildup classification.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
REPO_ROOT = _THIS.parents[3]
OPT_BASE = (REPO_ROOT / "intraday_options_strategy" / "datasets" / "raw"
            / "hf_index_options_1m" / "stocks_options")
PANEL_DIR = RND_DIR / "panel"

_CUBE_CLOSE = None
_SYMBOL_FILES = {}   # sym -> sorted list of (cycle_end_date, Path)
_MAX_LAG_DAYS = 40   # don't use a cycle file "stale" by more than this vs t


def _load_cube_close() -> pd.DataFrame:
    global _CUBE_CLOSE
    if _CUBE_CLOSE is None:
        _CUBE_CLOSE = pd.read_parquet(PANEL_DIR / "cube_close.parquet")
        _CUBE_CLOSE.index = pd.to_datetime(_CUBE_CLOSE.index)
    return _CUBE_CLOSE


def _list_symbol_files(sym: str):
    if sym not in _SYMBOL_FILES:
        d = OPT_BASE / sym
        if not d.is_dir():
            _SYMBOL_FILES[sym] = []
        else:
            files = sorted(d.glob("*.parquet"))
            out = []
            for f in files:
                try:
                    out.append((pd.Timestamp(f.stem), f))
                except ValueError:
                    continue
            out.sort(key=lambda x: x[0])
            _SYMBOL_FILES[sym] = out
    return _SYMBOL_FILES[sym]


def _file_for_date(sym: str, t: pd.Timestamp):
    """Most-recent completed-cycle file with cycle_end_date <= t, within
    _MAX_LAG_DAYS. Returns None if no such file (honest gap, not filled)."""
    files = _list_symbol_files(sym)
    if not files:
        return None
    best = None
    for d, f in files:
        if d <= t:
            best = (d, f)
        else:
            break
    if best is None:
        return None
    d, f = best
    if (t - d).days > _MAX_LAG_DAYS:
        return None
    return d, f


def _cycle_features(path: Path, close_series: pd.Series | None):
    """Load one symbol-cycle parquet -> (pcr_oi, oi_price_corr).

    DUAL SCHEMA (discovered building this module, not previously documented):
    ~144/210 symbols store one EOD row per (trading_day, strike, option_type)
    with an `oi` column already an end-of-day snapshot. The other ~66/210
    store genuine INTRADAY rows (multiple per strike/type/day, `open_interest`
    column, plus `expiry`/`symbol` cols) — OI must be taken as the LAST
    intraday value per (trading_day, strike, option_type), never summed
    across intraday rows (open interest is a snapshot, not additive)."""
    df = pd.read_parquet(path)
    if "oi" not in df.columns and "open_interest" in df.columns:
        df = df.rename(columns={"open_interest": "oi"})
    df["trading_day"] = pd.to_datetime(df["trading_day"]).dt.tz_localize(None)
    # collapse to one EOD row per (trading_day, strike, option_type) regardless
    # of schema — a no-op for already-EOD schema-A files, a real collapse for
    # intraday schema-B files.
    df = (df.sort_values("trading_day")
            .groupby(["trading_day", "strike", "option_type"], as_index=False)
            .last()[["trading_day", "strike", "option_type", "oi"]])

    last_day = df["trading_day"].max()
    last_snap = df[df["trading_day"] == last_day]
    call_oi = last_snap.loc[last_snap["option_type"] == "CE", "oi"].sum()
    put_oi = last_snap.loc[last_snap["option_type"] == "PE", "oi"].sum()
    pcr = put_oi / call_oi if call_oi > 0 else np.nan

    oi_price_corr = np.nan
    if close_series is not None:
        oi_by_day = df.groupby("trading_day")["oi"].sum()
        px_by_day = close_series.reindex(oi_by_day.index)
        both = pd.concat([oi_by_day.rename("oi"), px_by_day.rename("px")], axis=1).dropna()
        if len(both) >= 6 and both["oi"].std() > 0 and both["px"].std() > 0:
            oi_price_corr = both["oi"].corr(both["px"])
    return pcr, oi_price_corr


def _panel_dates_symbols(panel: pd.DataFrame):
    dates = sorted(pd.to_datetime(panel["date"].unique()))
    symbols = sorted(panel["symbol"].unique())
    return dates, symbols


def _series_from_rows(rows) -> pd.Series:
    out = pd.DataFrame(rows, columns=["date", "symbol", "factor"])
    return out.set_index(["date", "symbol"])["factor"]


def _build_both(panel: pd.DataFrame):
    """Single pass over available option data -> dict of two row-lists
    (pcr, oiflow), keyed by symbol universe intersected with the option data
    directory (210 names) and matched to panel dates by _file_for_date."""
    cube_close = _load_cube_close()
    dates, symbols = _panel_dates_symbols(panel)
    opt_symbols = sorted(s for s in symbols if (OPT_BASE / s).is_dir())

    pcr_rows, flow_rows = [], []
    # cache one loaded-file's features per (sym, path) so PCR/OIFLOW share the read
    cache: dict = {}
    n_corrupt = 0
    corrupt_examples = []
    for sym in opt_symbols:
        close_series = cube_close[sym] if sym in cube_close.columns else None
        for d in dates:
            hit = _file_for_date(sym, d)
            if hit is None:
                continue
            cyc_date, path = hit
            key = (sym, cyc_date)
            if key not in cache:
                try:
                    cache[key] = _cycle_features(path, close_series)
                except Exception as e:  # corrupt/truncated parquet — skip, disclose count
                    n_corrupt += 1
                    if len(corrupt_examples) < 10:
                        corrupt_examples.append(f"{sym}/{path.name}: {e}")
                    cache[key] = (np.nan, np.nan)
            pcr, flow = cache[key]
            if not np.isnan(pcr):
                pcr_rows.append((d, sym, pcr))
            if not np.isnan(flow):
                flow_rows.append((d, sym, flow))
    if n_corrupt:
        print(f"[builders_w2_opt] WARNING: {n_corrupt} corrupt/unreadable parquet files skipped. "
              f"Examples: {corrupt_examples}")
    return pcr_rows, flow_rows


_CACHED_BUILD = None


def _get_cached_build(panel: pd.DataFrame):
    global _CACHED_BUILD
    if _CACHED_BUILD is None:
        _CACHED_BUILD = _build_both(panel)
    return _CACHED_BUILD


def build_pcr_oi(panel: pd.DataFrame) -> pd.Series:
    pcr_rows, _ = _get_cached_build(panel)
    return _series_from_rows(pcr_rows)


def build_oi_price_flow(panel: pd.DataFrame) -> pd.Series:
    _, flow_rows = _get_cached_build(panel)
    return _series_from_rows(flow_rows)
