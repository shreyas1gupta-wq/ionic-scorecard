"""Option-chain data accessor for NIFTY 1-min index options (buying strategy).

Each parquet file under options/NIFTY/ is named by EXPIRY date and holds the full
multi-day life of that expiry's options at 1-min (09:15-15:30), all strikes.

Columns: timestamp(tz+05:30), open, high, low, close, volume, open_interest,
         trading_day(str), symbol, strike(int), option_type(CE/PE), expiry(str)

We expose:
  - build_expiry_index(): {expiry_date: path}, sorted valid expiries, flags stubs/corrupt
  - load_expiry(exp): full df for that expiry, timestamps -> naive IST
  - day_chain(exp, day): that trading day's 1-min chain for options expiring `exp`
  - nearest_expiry(day, min_dte, max_dte): pick the target weekly expiry
"""
from __future__ import annotations

import datetime as dt
from functools import lru_cache
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

BASE = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
            r"\NIFTY 500\intraday_options_strategy\datasets\raw\hf_index_options_1m")
NIFTY_OPT_DIR = BASE / "options" / "NIFTY"
NIFTY_INDEX = BASE / "index" / "NIFTY.parquet"

# Files known to be unusable
CORRUPT = {"2023-06-29"}          # snappy/read error
MIN_FILE_BYTES = 500_000          # smaller => partial stub (e.g. 2026-06-09)


def _parse_exp(name: str) -> dt.date:
    return dt.datetime.strptime(name, "%Y-%m-%d").date()


@lru_cache(maxsize=1)
def build_expiry_index() -> tuple[dict, list]:
    """Return ({expiry_date: Path}, sorted_valid_expiry_dates)."""
    mapping: dict[dt.date, Path] = {}
    skipped = []
    for p in NIFTY_OPT_DIR.glob("*.parquet"):
        name = p.stem
        if name in CORRUPT:
            skipped.append((name, "corrupt"))
            continue
        if p.stat().st_size < MIN_FILE_BYTES:
            skipped.append((name, f"stub {p.stat().st_size}B"))
            continue
        try:
            mapping[_parse_exp(name)] = p
        except ValueError:
            skipped.append((name, "bad name"))
    exps = sorted(mapping)
    if skipped:
        print(f"[chain] skipped {len(skipped)} files: {skipped}")
    print(f"[chain] {len(exps)} valid expiries {exps[0]} .. {exps[-1]}")
    return mapping, exps


@lru_cache(maxsize=64)
def load_expiry(exp: dt.date) -> pd.DataFrame:
    mapping, _ = build_expiry_index()
    df = pq.read_table(mapping[exp]).to_pandas()
    # timestamps are tz-aware +05:30 (IST) -> naive IST
    df["t"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    df["trading_day"] = df["trading_day"].astype(str)
    df = df.drop_duplicates(["t", "strike", "option_type"])
    return df


def day_chain(exp: dt.date, day: dt.date) -> pd.DataFrame:
    """1-min chain for options expiring `exp`, on calendar `day`."""
    df = load_expiry(exp)
    return df[df["trading_day"] == day.isoformat()].copy()


def nearest_expiry(day: dt.date, min_dte: int = 0, max_dte: int = 7):
    """Nearest available expiry E with min_dte <= (E - day).days <= max_dte."""
    _, exps = build_expiry_index()
    cands = [e for e in exps if min_dte <= (e - day).days <= max_dte]
    return cands[0] if cands else None


@lru_cache(maxsize=1)
def load_index() -> pd.DataFrame:
    """NIFTY spot 1-min, naive IST index, OHLC."""
    df = pq.read_table(NIFTY_INDEX).to_pandas()
    df["t"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    df = df.drop_duplicates("t").set_index("t").sort_index()
    return df[["open", "high", "low", "close"]]


if __name__ == "__main__":
    mapping, exps = build_expiry_index()
    idx = load_index()
    print(f"[index] spot bars {len(idx):,}  {idx.index[0]} .. {idx.index[-1]}")
