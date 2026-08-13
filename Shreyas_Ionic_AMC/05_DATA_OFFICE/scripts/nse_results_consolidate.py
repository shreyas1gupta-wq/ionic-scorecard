# -*- coding: utf-8 -*-
"""nse_results_consolidate.py -- build the tidy PIT parquet from the raw
month-by-month JSON files nse_results_pull.py leaves under
datasets/nse_results_pit/raw/.

Produces two files:
  nse_results_pit_raw.parquet   -- every row, every field, exactly as NSE
                                    returned it (only fully-duplicate rows
                                    dropped), tagged with which pull surfaced it.
  nse_results_pit_tidy.parquet  -- keyed (symbol, period_end); available_date
                                    = earliest observed broadCastDate across
                                    every raw row for that key (task spec).

Nothing here re-fetches from NSE. Safe to re-run any time raw/ changes.
"""
import glob
import json
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT_DIR = ROOT / "datasets" / "nse_results_pit"
RAW_DIR = OUT_DIR / "raw"


def load_raw():
    frames = []
    files = sorted(RAW_DIR.glob("*.json"))
    if not files:
        print("No raw files found under", RAW_DIR)
        return pd.DataFrame(), 0, 0
    empty = 0
    for fp in files:
        stem = fp.stem  # e.g. quarterly_2011_01
        parts = stem.split("_")
        period_param = parts[0].capitalize()
        ym = f"{parts[1]}-{parts[2]}" if len(parts) >= 3 else None
        with open(fp, "r", encoding="utf-8") as f:
            rows = json.load(f)
        if not rows:
            empty += 1
            continue
        df = pd.DataFrame(rows)
        df["_pull_period_param"] = period_param
        df["_pull_year_month"] = ym
        frames.append(df)
    if not frames:
        return pd.DataFrame(), len(files), empty
    big = pd.concat(frames, ignore_index=True, sort=False)
    return big, len(files), empty


def parse_dt(series):
    return pd.to_datetime(series, format="mixed", dayfirst=True, errors="coerce")


def main():
    big, n_files, n_empty = load_raw()
    print(f"raw files: {n_files} ({n_empty} empty), raw rows before dedupe: {len(big)}")
    if big.empty:
        print("Nothing to consolidate yet.")
        return 1

    before = len(big)
    dedupe_cols = [c for c in big.columns if c not in ("_pull_period_param", "_pull_year_month")]
    big = big.drop_duplicates(subset=dedupe_cols, keep="first")
    print(f"exact-duplicate rows dropped: {before - len(big)} -> {len(big)} raw rows kept")

    for col in ("broadCastDate", "filingDate", "exchdisstime"):
        if col in big.columns:
            big[col + "_dt"] = parse_dt(big[col])
    for col in ("fromDate", "toDate"):
        if col in big.columns:
            big[col + "_dt"] = parse_dt(big[col])

    n_bad_broadcast = big["broadCastDate_dt"].isna().sum() if "broadCastDate_dt" in big else len(big)
    print(f"rows with unparseable broadCastDate: {n_bad_broadcast}/{len(big)}")

    raw_path = OUT_DIR / "nse_results_pit_raw.parquet"
    big.to_parquet(raw_path, index=False)
    print(f"wrote {raw_path} ({len(big)} rows, {big['symbol'].nunique() if 'symbol' in big else 'NA'} symbols)")

    # ---- tidy layer: keyed (symbol, period_end), earliest broadCastDate wins ----
    work = big.dropna(subset=["symbol", "toDate_dt", "broadCastDate_dt"]).copy()
    dropped = len(big) - len(work)
    print(f"rows dropped from tidy layer (missing symbol/period_end/broadCastDate): {dropped}")
    work["period_end"] = work["toDate_dt"].dt.date

    work = work.sort_values("broadCastDate_dt")
    grp = work.groupby(["symbol", "period_end"], as_index=False)

    tidy = grp.agg(
        available_date=("broadCastDate_dt", "min"),
        filing_date_earliest=("filingDate_dt", "min") if "filingDate_dt" in work else ("broadCastDate_dt", "min"),
        companyName=("companyName", "first"),
        isin=("isin", "first"),
        financialYear=("financialYear", "first"),
        relatingTo=("relatingTo", "first"),
        consolidated=("consolidated", "first"),
        audited=("audited", "first"),
        period_start=("fromDate_dt", "min"),
        xbrl=("xbrl", "first"),
        n_raw_rows=("symbol", "count"),
    )
    src = work.groupby(["symbol", "period_end"])["_pull_period_param"].apply(lambda s: ",".join(sorted(set(s)))).reset_index()
    src.columns = ["symbol", "period_end", "source_periods"]
    tidy = tidy.merge(src, on=["symbol", "period_end"], how="left")
    tidy["available_date"] = pd.to_datetime(tidy["available_date"]).dt.date

    tidy_path = OUT_DIR / "nse_results_pit_tidy.parquet"
    tidy.to_parquet(tidy_path, index=False)
    print(f"wrote {tidy_path} ({len(tidy)} rows, {tidy['symbol'].nunique()} symbols)")
    print(f"period_end range: {tidy['period_end'].min()} .. {tidy['period_end'].max()}")
    print(f"available_date range: {tidy['available_date'].min()} .. {tidy['available_date'].max()}")

    # sanity: how many keys have available_date BEFORE period_end (should be ~0, real error if not)
    bad = tidy[pd.to_datetime(tidy["available_date"]) < pd.to_datetime(tidy["period_end"])]
    print(f"KEYS WITH available_date BEFORE period_end (should be 0): {len(bad)}")
    if len(bad):
        print(bad.head(10).to_string())

    by_year = tidy.assign(y=pd.to_datetime(tidy["period_end"]).dt.year).groupby("y").agg(
        rows=("symbol", "size"), symbols=("symbol", "nunique"))
    print("\nper period_end-year rows/symbols:")
    print(by_year.to_string())

    return 0


if __name__ == "__main__":
    sys.exit(main())
