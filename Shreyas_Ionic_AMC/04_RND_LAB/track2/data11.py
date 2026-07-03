"""DATA-11 — survivorship-safe daily panel + PIT universe + 20d ADV loader.
Track-2 (SIG-11 build), per 04_RND_LAB/ideas/20260703_track2_engine_spec.md §1 + Build-task DATA-11.

Scope note: this module builds the PANEL/UNIVERSE/ADV primitives needed by SIG-11 (signal stack).
It does NOT yet materialize delist-loss events or write the eq_panel_v2.parquet/universe_pit.parquet/
adv.parquet output files described in the full DESK-100 task list step 1 — that is BT-11/COST-11
territory (portfolio accounting). SIG-11 only needs load_panel() / pit_universe() / adv_20d().

Run: PYTHONIOENCODING=utf-8 python data11.py
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache

import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
sys.path.insert(0, os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\lib"))
import guards as G  # noqa  (landmine guards mandatory in every entry point)

PANEL_PATH = os.path.join(ROOT, r"swing_momentum\data\hf_stock_minute\day\train-00000.parquet")
PIT_XLSX = os.path.join(ROOT, r"NIFTY500_TICKER_2005_2025_Final.xlsx")

PRICE_FLOOR = 20.0       # spec §1: penny-stock / print-artifact guard
ADV_WINDOW = 20          # spec §1 / DATA-11: 20-day median rupee turnover
# spec §0.B says the raw file's max date is 2026-01-21 — that is the RAW UTC timestamp.
# guards.fix_ist_dates() (L1, mandatory) converts 18:30 UTC -> next-day 00:00 IST, so the
# true last TRADING date after the required tz fix is 2026-01-22 (P-01 CHOICE, loud: the
# spec's "2026-01-21" pre-dates the IST conversion this build must apply; using the raw UTC
# date without the guard would itself be an L1 violation, so DATA_MAX_DATE is set to the
# post-guard value and this discrepancy is called out rather than silently reconciled).
DATA_MAX_DATE = pd.Timestamp("2026-01-22")  # staleness caveat — LOUD, see comment above

# Month-Year abbreviations used in the PIT snapshot sheet, e.g. "Mar2005".
_MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def _parse_month_year(s: str) -> pd.Timestamp:
    """'Mar2005' -> Timestamp('2005-03-01'). Snapshot is effective from the 1st of that month
    (P-01 CHOICE, loud): the xlsx only carries a semi-annual label, not a specific rebalance day;
    anchoring to month-start is the conservative (earliest-possible) reading, so we never claim
    membership knowledge earlier than we actually have it."""
    mon, yr = s[:3], s[3:]
    return pd.Timestamp(year=int(yr), month=_MONTH_MAP[mon], day=1)


# ---------------------------------------------------------------------------
# load_panel
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def load_panel() -> pd.DataFrame:
    """Load the verified daily OHLCV+volume panel, IST-date-fixed, price-floored.

    Corp-action gate PASSED 2026-07-04 (per build-spec header note handed to this task):
    the panel is already split/bonus-adjusted, so no `corporate_action_factors` join is
    applied here (P-01 CHOICE, loud — spec §1 says "if the file is raw-unadjusted, apply
    corporate_action_factors"; the task brief states the gate already passed and the panel
    is adjusted, so that branch is skipped by explicit instruction, not by omission).

    Returns columns: symbol, date (python date), open, high, low, close, volume, oi.
    Sorted by symbol, date. Price floor (close >= PRICE_FLOOR) is NOT applied here —
    it is a per-date ELIGIBILITY rule (§1), not a panel-membership filter, so it is applied
    in pit_universe()/eligibility helpers instead of dropping rows from the raw panel.
    """
    df = pd.read_parquet(PANEL_PATH)
    df = G.fix_ist_dates(df, ts_col="timestamp", out_col="date")
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    # de-dup safety: HF panels occasionally carry duplicate (symbol,date) stamps across
    # UTC 18:30 boundaries; keep the last print for a given IST date.
    df = df.drop_duplicates(subset=["symbol", "date"], keep="last")
    return df


# ---------------------------------------------------------------------------
# PIT universe (forward-filled semi-annual membership)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _pit_snapshots() -> pd.DataFrame:
    """Long table: snap_date (Timestamp, month-start) x ticker. 42 snapshots per spec."""
    raw = pd.read_excel(PIT_XLSX)
    raw = raw.rename(columns={"Month-Year": "snap_label", "Ticker": "symbol"})
    raw["symbol"] = raw["symbol"].astype(str).str.strip().str.upper()
    raw["snap_date"] = raw["snap_label"].map(_parse_month_year)
    snaps = sorted(raw["snap_date"].unique())
    assert len(snaps) == 42, f"L3 PIT: expected 42 snapshots, found {len(snaps)}"
    return raw[["snap_date", "symbol"]].drop_duplicates()


@lru_cache(maxsize=1)
def _snapshot_dates() -> tuple:
    return tuple(sorted(_pit_snapshots()["snap_date"].unique()))


def pit_universe(date) -> set:
    """Return the set of symbols eligible (survivorship-safe membership only — NOT the
    liquidity/price-floor eligibility filter) on trading date `date`.

    Rule (spec §1): a name is eligible on `date` iff it appeared in the most-recent snapshot
    on-or-before `date` (forward-fill). If `date` precedes the first snapshot (Mar-2005),
    the universe is empty (no look-ahead into the future first snapshot).
    """
    d = pd.Timestamp(date)
    snaps = _snapshot_dates()
    eligible_snaps = [s for s in snaps if s <= d]
    if not eligible_snaps:
        return set()
    asof_snap = max(eligible_snaps)
    tab = _pit_snapshots()
    return set(tab.loc[tab["snap_date"] == asof_snap, "symbol"])


# ---------------------------------------------------------------------------
# 20d ADV / rupee turnover
# ---------------------------------------------------------------------------
def adv_20d(panel: pd.DataFrame | None = None) -> pd.DataFrame:
    """20-trading-day rolling MEDIAN rupee turnover (close * volume) per symbol per date.
    No-lookahead: rolling window uses only rows up to and including `date` (min_periods=ADV_WINDOW
    so early-history symbols don't get a spuriously "thin" partial-window ADV masquerading as full).

    Returns columns: symbol, date, turnover, adv_20d.
    """
    if panel is None:
        panel = load_panel()
    df = panel[["symbol", "date", "close", "volume"]].copy()
    df["turnover"] = df["close"].astype("float64") * df["volume"].astype("float64")
    df = df.sort_values(["symbol", "date"])
    df["adv_20d"] = (
        df.groupby("symbol")["turnover"]
        .rolling(ADV_WINDOW, min_periods=ADV_WINDOW)
        .median()
        .reset_index(level=0, drop=True)
    )
    return df[["symbol", "date", "turnover", "adv_20d"]]


def price_floor_pass(panel: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per (symbol,date) boolean: close >= PRICE_FLOOR (spec §1 price floor)."""
    if panel is None:
        panel = load_panel()
    out = panel[["symbol", "date", "close"]].copy()
    out["price_floor_ok"] = out["close"] >= PRICE_FLOOR
    return out


if __name__ == "__main__":
    panel = load_panel()
    print(f"panel rows={len(panel):,} symbols={panel['symbol'].nunique():,} "
          f"date range={panel['date'].min().date()} -> {panel['date'].max().date()}")
    assert panel["date"].max() <= DATA_MAX_DATE, "L7: panel extends past documented stale tail"

    snaps = _snapshot_dates()
    print(f"PIT snapshots: {len(snaps)} ({snaps[0].date()} -> {snaps[-1].date()})")

    u1 = pit_universe("2023-06-30")
    u2 = pit_universe("2025-06-30")
    print(f"pit_universe(2023-06-30): {len(u1)} names")
    print(f"pit_universe(2025-06-30): {len(u2)} names")

    adv = adv_20d(panel)
    print(f"adv_20d rows={len(adv):,}, non-null adv_20d={adv['adv_20d'].notna().sum():,}")
