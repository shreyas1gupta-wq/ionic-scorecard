"""Phase 1: build canonical processed datasets from raw Kaggle 1-min CSVs.

Outputs (datasets/processed/):
  nifty_1min.parquet      — cleaned 1-min Nifty 50 index bars
  vix_1min.parquet        — cleaned 1-min India VIX (close only)
  banknifty_1min.parquet  — cleaned 1-min BankNifty bars
  trading_calendar.csv    — list of kept trading days

Cleaning rules (per PLAN.md caveats):
  - session filter 09:15–15:29 inclusive
  - drop duplicate timestamps (keep first), sort ascending
  - drop days with < MIN_BARS_PER_DAY bars (Muhurat sessions, 2021-02-24 outage)
  - volume column dropped (always 0 for indices)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import PROCESSED_DIR, RAW_DIR  # noqa: E402

KAGGLE_DIR = RAW_DIR / "kaggle" / "debashis74017__nifty-50-minute-data"
MIN_BARS_PER_DAY = 300


def load_clean(csv_name: str) -> pd.DataFrame:
    """Load one raw 1-min CSV → cleaned frame indexed by naive IST datetime."""
    df = pd.read_csv(KAGGLE_DIR / csv_name, parse_dates=["date"])
    df = (df.rename(columns={"date": "dt"})
            .drop(columns=["volume"], errors="ignore")
            .drop_duplicates(subset="dt", keep="first")
            .sort_values("dt")
            .set_index("dt"))
    df = df.between_time("09:15", "15:29")
    bars = df.groupby(df.index.normalize()).size()
    keep_days = bars[bars >= MIN_BARS_PER_DAY].index
    dropped = bars[bars < MIN_BARS_PER_DAY]
    if len(dropped):
        print(f"  dropped {len(dropped)} short days: "
              f"{[str(d.date()) for d in dropped.index[:8]]}{'...' if len(dropped) > 8 else ''}")
    df = df[df.index.normalize().isin(keep_days)]
    assert df.index.is_monotonic_increasing and df.index.is_unique
    assert (df[["open", "high", "low", "close"]] > 0).all().all(), "non-positive prices"
    return df


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print("NIFTY 50:")
    nifty = load_clean("NIFTY 50_minute.csv")
    nifty.to_parquet(PROCESSED_DIR / "nifty_1min.parquet")

    print("INDIA VIX:")
    vix = load_clean("INDIA VIX_minute.csv")[["close"]].rename(columns={"close": "vix"})
    vix.to_parquet(PROCESSED_DIR / "vix_1min.parquet")

    print("NIFTY BANK:")
    bnf = load_clean("NIFTY BANK_minute.csv")
    bnf.to_parquet(PROCESSED_DIR / "banknifty_1min.parquet")

    days = pd.Series(nifty.index.normalize().unique(), name="day")
    days.to_csv(PROCESSED_DIR / "trading_calendar.csv", index=False)

    # coverage: how many nifty bars lack a same-minute VIX print (forward-fill later)
    vix_cov = nifty.index.isin(vix.index).mean()
    print(f"\nnifty: {len(nifty):,} bars over {len(days)} days "
          f"({days.iloc[0].date()} -> {days.iloc[-1].date()})")
    print(f"vix:   {len(vix):,} bars; same-minute coverage of nifty bars: {vix_cov:.2%}")
    print(f"bnf:   {len(bnf):,} bars")
    print("OK -> processed parquets written")


if __name__ == "__main__":
    main()
