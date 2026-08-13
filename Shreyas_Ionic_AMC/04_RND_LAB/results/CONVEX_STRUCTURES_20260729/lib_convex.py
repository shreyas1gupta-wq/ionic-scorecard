"""Shared engine for near-zero-cost convexity structures on NIFTY weekly index options:
ratio backspreads, calendars/diagonals, broken-wing/skewed directional structures.

Reuses intraday_options_strategy/buying/chain.py for data access. Real 1-min fills on
every leg; entry at next-bar-open after signal (no lookahead); cash-settle at intrinsic
if held to expiry (landmine #9). Costs: Rs25/lot/side (mandate). Margin: dynamic,
spot-scaled, 5% notional (defined-risk, all structures here) / 10% (naked comparator).
"""
from __future__ import annotations

import datetime as dt
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

BUYING_DIR = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
                   r"\NIFTY 500\intraday_options_strategy\buying")
sys.path.insert(0, str(BUYING_DIR))
import chain  # noqa: E402

# Memory is TIGHT on this box (multiple parallel research arms share it; observed as low as
# ~1GB free). chain.load_expiry() has its own lru_cache(maxsize=64) which alone can hold
# 0.6-1.3GB of expiry frames -> OOM risk. We bypass it and read parquet directly with a much
# smaller cache (few expiries are ever needed live at once: 1 for a backspread, 2 for a
# calendar), loading only the columns we actually use.
_EXP_COLS = ["timestamp", "open", "high", "low", "close", "volume",
             "strike", "option_type", "trading_day"]

STEP = 50
LOT_SIZE = 75
COST_PER_LOT_SIDE = 25.0          # Rs, mandate
SLIPPAGE_PT_SIDE_DEFAULT = 0.375  # midpoint of mandate's 0.25-0.5 pt/side
MARGIN_PCT_DEFINED = 0.05         # Principal ruling 22:56
MARGIN_PCT_NAKED = 0.10
EQUITY0 = 10_00_000.0             # S1-F sizing convention
LOTS_FRACTION = 0.75              # of equity/margin, matches S1-F

BUILD_END = dt.date(2025, 12, 31)


# -----------------------------------------------------------------------------
# data access
# -----------------------------------------------------------------------------
@lru_cache(maxsize=512)
def _leg_series_raw(exp: dt.date, strike: int, otype: str) -> pd.DataFrame:
    """Targeted read for ONE strike+type out of an expiry file, using parquet predicate
    pushdown so we never materialize the full ~500k-row / ~100-strike chain in memory
    (this box runs at ~1-2GB free RAM shared with other parallel research arms -- a full
    expiry-frame cache OOM'd twice during dev). Small cache (512 legs) since each is tiny
    (a few thousand rows) yet legs get reused across nearby entry cycles."""
    mapping, _ = chain.build_expiry_index()

    def _read():
        tbl = pq.read_table(mapping[exp], columns=_EXP_COLS,
                             filters=[("strike", "=", strike), ("option_type", "=", otype)])
        return tbl.to_pandas()
    df = with_memory_retry(_read)
    if df.empty:
        return df
    df["t"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    df = df.drop_duplicates("t").sort_values("t")
    return df.set_index("t")[["open", "high", "low", "close", "volume"]]


@lru_cache(maxsize=1)
def spot_index() -> pd.DataFrame:
    return chain.load_index()


@lru_cache(maxsize=1)
def _spot_close_arr():
    """Precompute numpy arrays once (index + close) for cheap searchsorted lookups --
    avoids repeated boolean-mask filtering of the full 463k-row spot frame, which was
    OOM-crashing under this box's tight/volatile shared memory (other parallel agents)."""
    s = spot_index()
    return s.index.values, s["close"].values


def spot_close_asof(t0: pd.Timestamp) -> float | None:
    """Last known spot close at or before t0, via searchsorted (no full-frame copy)."""
    idx_arr, close_arr = _spot_close_arr()
    pos = np.searchsorted(idx_arr, np.datetime64(t0), side="right") - 1
    if pos < 0:
        return None
    return float(close_arr[pos])


def with_memory_retry(fn, *args, retries: int = 6, base_sleep: float = 1.5, **kwargs):
    """Retry a callable on transient MemoryError/ArrayMemoryError (this box's free RAM
    fluctuates sharply -- other parallel research arms share it). gc.collect() + short
    backoff between attempts. Re-raises after exhausting retries."""
    import gc
    import time as _time
    last_err = None
    for i in range(retries):
        try:
            return fn(*args, **kwargs)
        except MemoryError as e:
            last_err = e
            gc.collect()
            _time.sleep(base_sleep * (i + 1))
    raise last_err


@lru_cache(maxsize=1)
def expiries() -> list[dt.date]:
    _, exps = chain.build_expiry_index()
    return exps


@lru_cache(maxsize=1)
def monthly_expiries() -> set[dt.date]:
    exps = expiries()
    out = []
    for i, e in enumerate(exps):
        if i + 1 == len(exps) or exps[i + 1].month != e.month or exps[i + 1].year != e.year:
            out.append(e)
    return set(out)


def leg_frame(exp: dt.date, strike: int, otype: str) -> pd.DataFrame:
    return _leg_series_raw(exp, strike, otype)


@lru_cache(maxsize=300)
def leg_first_day(exp: dt.date, strike: int | None = None, otype: str | None = None) -> dt.date | None:
    """First trading day this SPECIFIC strike/type has data (used to gate far/monthly legs
    that may not be listed yet -- the K-012-adjacent liquidity check). If strike/otype not
    given, probes the ATM-ish strike is caller's job; here we just need file existence, so
    fall back to a cheap metadata-only check via the expiry's price file for ANY strike by
    reading just the trading_day column (still predicate-pushdown light)."""
    mapping, _ = chain.build_expiry_index()
    if exp not in mapping:
        return None
    if strike is None or otype is None:
        tbl = pq.read_table(mapping[exp], columns=["trading_day"])
        days = tbl.column("trading_day").to_pylist()
        if not days:
            return None
        return dt.date.fromisoformat(sorted(set(days))[0])
    df = _leg_series_raw(exp, strike, otype)
    if df.empty:
        return None
    return df.index[0].date()


def atm_strike(spot: float) -> int:
    return int(round(spot / STEP) * STEP)


def near_weekly(day: dt.date, min_dte=1, max_dte=8) -> dt.date | None:
    return chain.nearest_expiry(day, min_dte, max_dte)


def n_weeks_out(near_exp: dt.date, n: int) -> dt.date | None:
    exps = expiries()
    if near_exp not in exps:
        return None
    i = exps.index(near_exp)
    if i + n >= len(exps):
        return None
    return exps[i + n]


def monthly_after(near_exp: dt.date) -> dt.date | None:
    """Last expiry of near_exp's calendar month (== near_exp if near_exp itself is the
    month's last expiry)."""
    exps = expiries()
    mset = monthly_expiries()
    cands = [e for e in exps if e >= near_exp and e.month == near_exp.month and e.year == near_exp.year]
    return cands[-1] if cands else None


# -----------------------------------------------------------------------------
# costs / margin
# -----------------------------------------------------------------------------
def friction_rs(lot_units_side: int, lot_size: int = LOT_SIZE,
                slippage_pt_side: float = SLIPPAGE_PT_SIDE_DEFAULT) -> float:
    """One-sided friction (commission + slippage) in Rs for `lot_units_side` total lots
    traded on that side (sum of |qty| across all legs)."""
    commission = COST_PER_LOT_SIDE * lot_units_side
    slippage = slippage_pt_side * lot_size * lot_units_side
    return commission + slippage


def margin_rs(spot: float, lots: int, defined_risk: bool = True,
              lot_size: int = LOT_SIZE) -> float:
    pct = MARGIN_PCT_DEFINED if defined_risk else MARGIN_PCT_NAKED
    return pct * spot * lot_size * lots


def size_lots(equity: float, spot: float, defined_risk: bool = True,
              lot_size: int = LOT_SIZE, frac: float = LOTS_FRACTION) -> int:
    per_lot = margin_rs(spot, 1, defined_risk, lot_size)
    return max(1, int((frac * equity) // per_lot))


# -----------------------------------------------------------------------------
# generic leg + trade containers
# -----------------------------------------------------------------------------
@dataclass
class Leg:
    expiry: dt.date
    otype: str      # CE/PE
    side: int        # +1 buy, -1 sell
    qty_ratio: int    # lots per 1x position unit (e.g. backspread long leg = 2)
    strike: int | None = None   # filled in at entry


@dataclass
class Trade:
    entry_day: dt.date
    entry_t: pd.Timestamp
    legs: list = field(default_factory=list)          # list[Leg] with strike filled
    entry_prices: list = field(default_factory=list)   # per-leg entry price (raw, no slippage)
    entry_vols: list = field(default_factory=list)      # per-leg entry bar volume
    exit_t: pd.Timestamp | None = None
    exit_prices: list = field(default_factory=list)
    exit_reason: str | None = None
    spot_entry: float = np.nan
    lots: int = 1
    label: str = ""


def net_debit(prices: list[float], legs: list[Leg]) -> float:
    """+ve = net debit paid, -ve = net credit received (position-unit basis, i.e. per
    qty_ratio=1 lot each leg's own ratio already applied)."""
    return sum(leg.side * leg.qty_ratio * p for leg, p in zip(legs, prices))


def lot_units_side(legs: list[Leg]) -> int:
    return sum(abs(leg.qty_ratio) for leg in legs)


def intrinsic(spot_close: float, strike: int, otype: str) -> float:
    if otype == "CE":
        return max(spot_close - strike, 0.0)
    return max(strike - spot_close, 0.0)


# -----------------------------------------------------------------------------
# fill helper: next bar open strictly after t0, from a leg's own price frame
# -----------------------------------------------------------------------------
def next_open(frame: pd.DataFrame, t0: pd.Timestamp) -> tuple[pd.Timestamp, float, float] | None:
    after = frame[frame.index > t0]
    if after.empty:
        return None
    row = after.iloc[0]
    px = float(row["open"])
    if not np.isfinite(px) or px <= 0:
        return None
    return after.index[0], px, float(row.get("volume", np.nan))


def price_at_or_before(frame: pd.DataFrame, t: pd.Timestamp) -> float | None:
    s = frame[frame.index <= t]
    if s.empty:
        return None
    return float(s["close"].iloc[-1])


def day_snapshot_time(day: dt.date, hhmm="15:15") -> pd.Timestamp:
    h, m = map(int, hhmm.split(":"))
    return pd.Timestamp(day) + pd.Timedelta(hours=h, minutes=m)


def trading_days_between(start: dt.date, end: dt.date) -> list[dt.date]:
    idx = spot_index()
    days = sorted({d for d in idx.index.date if start <= d <= end})
    return days


if __name__ == "__main__":
    print("STEP", STEP, "LOT_SIZE", LOT_SIZE)
    exps = expiries()
    print(f"{len(exps)} expiries, {len(monthly_expiries())} monthly-tagged")
    e0 = exps[10]
    print("near", e0, "n_weeks_out(+1)", n_weeks_out(e0, 1), "monthly_after", monthly_after(e0))
    print("cost 3 lot-units/side:", friction_rs(3))
    print("margin 1 lot defined-risk @ spot 25000:", margin_rs(25000, 1, True))
    print("margin 1 lot naked @ spot 25000:", margin_rs(25000, 1, False))
