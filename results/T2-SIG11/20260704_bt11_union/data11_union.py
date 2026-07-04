"""DATA-11 UNION — survivorship-safe daily panel from the PIT UNION RETURN panel.

Drop-in replacement for track2/data11.py for the BT-11 union re-run. Same public interface
(load_panel / pit_universe / PRICE_FLOOR / DATA_MAX_DATE / PIT_XLSX / PANEL_PATH) so bt11's
engine code is reused with a ONE-LINE source swap.

DIFFERENCES vs the HF data11 (all stated loudly, per D-028):
  1. PANEL SOURCE = my FROZEN copy of the union RETURN panel (close_panel_return.parquet),
     schema LONG [date, symbol, close, source, spliced]. CLOSE-ONLY.
  2. The engine (sig11 features) needs `volume` (breakout_vol_flag) and `open` (fills).
     - `volume`: SPLICED from the HF panel where a (symbol,date) print exists; union-only
       (symbol,date) -> volume = NaN -> breakout_vol_flag = False (an OR nudge only, never a
       hard gate, so it CANNOT fabricate ALL_PASS). We keep an `has_volume` flag for the
       liquidity-coverage report.
     - `open`: the union panel has no open. bt11_union fills at NEXT-DAY CLOSE instead. To keep
       the engine's next_open_map() code path intact we set open := close (so any accidental
       open reference degrades to the close, which is exactly the intended fill deviation). The
       fill logic in bt11_union uses the CLOSE array explicitly.
  3. PIT match uses symbol_aliases.csv (old->new). Union carries CURRENT tickers; PIT xlsx
     carries historical ones (HEROHONDA, CADILAHC, ...). We map PIT ticker -> alias(new) before
     the isin() test so historical members resolve to their union rows.
  4. PIT snapshots are Mar/Sep (semi-annual) — _parse_month_year anchors to month-start, so
     as-of membership already uses the correct Mar/Sep cadence (verified in build).

Run: PYTHONIOENCODING=utf-8 python data11_union.py   (self-test)
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache

import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
RUNDIR = os.path.join(ROOT, r"results\T2-SIG11\20260704_bt11_union")
sys.path.insert(0, os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\lib"))
import guards as G  # noqa  (landmine guards mandatory in every entry point)

# ---- my FROZEN copies (never read the live pit_union_panel_v1 dir) ----
PANEL_PATH = os.path.join(RUNDIR, "close_panel_return.parquet")   # UNION RETURN panel (v1)
ALIAS_PATH = os.path.join(RUNDIR, "symbol_aliases.csv")
PIT_XLSX = os.path.join(ROOT, "NIFTY500_TICKER_2005_2025_Final.xlsx")
PANEL_VERSION = "v1"   # base build 2026-07-04T20:53:55; md5 9f5b5d42159ff810e8d554bbab35499c

# HF panel — ONLY as a read-only volume donor for breakout_vol_flag (not a price source)
HF_PANEL_PATH = os.path.join(ROOT, r"swing_momentum\data\hf_stock_minute\day\train-00000.parquet")

PRICE_FLOOR = 20.0                          # spec §1: penny-stock / print-artifact guard (unchanged)
ADV_WINDOW = 20
DATA_MAX_DATE = pd.Timestamp("2026-01-22")  # union max date == HF max date (post-IST-fix)

_MONTH_MAP = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
              "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}


def _parse_month_year(s: str) -> pd.Timestamp:
    """'Mar2005' -> 2005-03-01 (month-start; conservative earliest-membership reading)."""
    mon, yr = s[:3], s[3:]
    return pd.Timestamp(year=int(yr), month=_MONTH_MAP[mon], day=1)


@lru_cache(maxsize=1)
def _alias_map() -> dict:
    """old_ticker(upper) -> new_ticker(upper). Union panel uses the NEW tickers."""
    al = pd.read_csv(ALIAS_PATH)
    return dict(zip(al["old_ticker"].astype(str).str.upper().str.strip(),
                    al["new_ticker"].astype(str).str.upper().str.strip()))


@lru_cache(maxsize=1)
def load_panel() -> pd.DataFrame:
    """Union RETURN panel -> columns: symbol, date, open, high(=close), low(=close), close,
    volume, oi, source, spliced, has_volume. CLOSE-ONLY source; open/high/low are set to close
    (fills use CLOSE explicitly in bt11_union). volume spliced from HF where available.

    NO price-floor drop here (per-date eligibility rule, applied in the signal layer)."""
    df = pd.read_parquet(PANEL_PATH)
    df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    # de-dup safety (build reported 0 dups, assert it holds on my copy)
    n0 = len(df)
    df = df.drop_duplicates(subset=["symbol", "date"], keep="last")
    assert len(df) == n0, f"L4: union panel had {n0-len(df)} dup (symbol,date) rows"

    # ---- splice HF volume (read-only donor) ----
    hf = pd.read_parquet(HF_PANEL_PATH)
    hf = G.fix_ist_dates(hf, ts_col="timestamp", out_col="date")
    hf["date"] = pd.to_datetime(hf["date"])
    hf["symbol"] = hf["symbol"].astype(str).str.upper().str.strip()
    hf = hf.drop_duplicates(subset=["symbol", "date"], keep="last")
    vol = hf[["symbol", "date", "volume"]].copy()
    df = df.merge(vol, on=["symbol", "date"], how="left")   # left => union rows preserved
    df["has_volume"] = df["volume"].notna()

    # engine-compat columns: fills use CLOSE (deviation), so open/high/low := close.
    df["open"] = df["close"]
    df["high"] = df["close"]
    df["low"] = df["close"]
    df["oi"] = np.nan
    df = df[["symbol", "date", "open", "high", "low", "close", "volume", "oi",
             "source", "spliced", "has_volume"]]
    return df.sort_values(["symbol", "date"]).reset_index(drop=True)


@lru_cache(maxsize=1)
def _pit_snapshots() -> pd.DataFrame:
    """Long table snap_date(month-start) x symbol, alias-mapped to union tickers. 42 snapshots."""
    raw = pd.read_excel(PIT_XLSX)
    raw = raw.rename(columns={"Month-Year": "snap_label", "Ticker": "symbol"})
    raw["symbol"] = raw["symbol"].astype(str).str.strip().str.upper()
    amap = _alias_map()
    raw["symbol"] = raw["symbol"].map(lambda s: amap.get(s, s))   # PIT old -> union new
    raw["snap_date"] = raw["snap_label"].map(_parse_month_year)
    snaps = sorted(raw["snap_date"].unique())
    assert len(snaps) == 42, f"L3 PIT: expected 42 snapshots, found {len(snaps)}"
    return raw[["snap_date", "symbol"]].drop_duplicates()


@lru_cache(maxsize=1)
def _snapshot_dates() -> tuple:
    return tuple(sorted(_pit_snapshots()["snap_date"].unique()))


def pit_universe(date) -> set:
    """Survivorship-safe membership as-of `date` (forward-fill most-recent Mar/Sep snapshot
    on-or-before date), alias-mapped to union tickers. Empty before the first snapshot."""
    d = pd.Timestamp(date)
    snaps = _snapshot_dates()
    eligible = [s for s in snaps if s <= d]
    if not eligible:
        return set()
    asof_snap = max(eligible)
    tab = _pit_snapshots()
    return set(tab.loc[tab["snap_date"] == asof_snap, "symbol"])


if __name__ == "__main__":
    import time
    t0 = time.time()
    panel = load_panel()
    print(f"[union] panel rows={len(panel):,} symbols={panel['symbol'].nunique():,} "
          f"dates {panel['date'].min().date()} -> {panel['date'].max().date()}")
    print(f"[union] has_volume rows={int(panel['has_volume'].sum()):,} "
          f"({100*panel['has_volume'].mean():.1f}%); union-only(no vol)={int((~panel['has_volume']).sum()):,}")
    print(f"[union] source split:\n{panel['source'].value_counts().to_string()}")
    assert panel["date"].max() <= DATA_MAX_DATE, "L7: panel past documented stale tail"

    snaps = _snapshot_dates()
    print(f"[union] PIT snapshots: {len(snaps)} ({snaps[0].date()} -> {snaps[-1].date()}) "
          f"months={sorted(set(s.month for s in snaps))}")
    for d in ["2014-03-31", "2016-03-31", "2023-06-30", "2025-06-30"]:
        u = pit_universe(d)
        have = panel[panel["symbol"].isin(u)]["symbol"].nunique()
        print(f"[union] pit_universe({d}): {len(u)} names, {have} present in union panel")
    print(f"[union] self-test {time.time()-t0:.0f}s")
