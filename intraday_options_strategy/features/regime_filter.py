"""Regime & eligibility filters C1–C4 (mandatory before every trade).

build_filters() returns one DataFrame aligned to the 1-min index:
  vix          — last COMPLETED 1-min VIX close (shift(1) + ffill → no lookahead)
  vix_ok       — C1: vix <= VIX_MAX
  adx          — ADX(14) of last completed 5-min bucket
  regime       — 'trend' (ADX>30) / 'meanrev' (ADX<20) / 'mixed' (20–30)
  size_mult    — 1.0, or ADX_MIXED_SIZE_MULT in the mixed band
  entry_window — C3: 09:30 <= t < 15:20
  event_ok     — C4: not an RBI policy / Union Budget day
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import (  # noqa: E402
    ADX_MEANREV_MAX, ADX_MIXED_SIZE_MULT, ADX_PERIOD, ADX_TREND_MIN,
    DATASETS_DIR, HARD_CLOSE, TRADE_START, VIX_MAX,
)
from features.indicators import adx_5min_on_1min  # noqa: E402

EVENT_CSV = DATASETS_DIR / "event_dates.csv"


def load_event_days() -> set[pd.Timestamp]:
    df = pd.read_csv(EVENT_CSV, parse_dates=["date"])
    return set(df["date"].dt.normalize())


def build_filters(nifty: pd.DataFrame, vix_1min: pd.DataFrame) -> pd.DataFrame:
    idx = nifty.index
    out = pd.DataFrame(index=idx)

    # C1 — VIX: previous completed bar's close, forward-filled across gaps
    vix = vix_1min["vix"].shift(1).reindex(idx).ffill()
    out["vix"] = vix
    out["vix_ok"] = vix <= VIX_MAX

    # C2 — ADX regime on 5-min buckets
    a = adx_5min_on_1min(nifty, ADX_PERIOD)
    out["adx"] = a
    out["regime"] = np.select(
        [a > ADX_TREND_MIN, a < ADX_MEANREV_MAX], ["trend", "meanrev"], default="mixed")
    out.loc[a.isna(), "regime"] = "none"  # warm-up: no trading
    out["size_mult"] = np.where(out["regime"] == "mixed", ADX_MIXED_SIZE_MULT, 1.0)

    # C3 — entry time window (signal bars whose NEXT-bar entry is still valid
    # are handled in the engine; this flags the signal bar itself)
    t = idx.time
    h, m = map(int, TRADE_START.split(":"))
    hc, mc = map(int, HARD_CLOSE.split(":"))
    from datetime import time as dtime
    out["entry_window"] = (t >= dtime(h, m)) & (t < dtime(hc, mc))

    # C4 — macro event days (best-effort list, see datasets/event_dates.csv)
    out["event_ok"] = ~idx.normalize().isin(load_event_days())
    return out
