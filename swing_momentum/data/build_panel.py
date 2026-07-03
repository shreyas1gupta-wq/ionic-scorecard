"""Phase 1: build a clean, survivorship-safe daily panel + point-in-time
membership from the master dataset.

Master xlsx is WIDE (Date + ~1200 stock columns; close prices; duplicate-suffixed
columns .1/.2 are the same ticker across re-listings/data joins → coalesce by
taking the non-null value per date). Output:
  processed/eq_close.parquet      long: date, symbol, close
  processed/membership.parquet    date(month), symbol  (point-in-time Nifty500)
  processed/delisted.parquet      symbol, last_date
"""
from __future__ import annotations
import re
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parents[1] / "processed"
OUT.mkdir(parents=True, exist_ok=True)


def build_close_panel() -> pd.DataFrame:
    print("loading master xlsx (32MB, ~1200 cols)...", flush=True)
    df = pd.read_excel(ROOT / "Nifty500_Master_Dataset_2005_2025.xlsx", sheet_name="Sheet1")
    df = df.rename(columns={df.columns[0]: "date"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).set_index("date").sort_index()
    # coalesce duplicate-suffixed columns (FOO, FOO.1, FOO.2) into base FOO
    base = {}
    for col in df.columns:
        b = re.sub(r"\.\d+$", "", str(col))
        base.setdefault(b, []).append(col)
    out = {}
    for b, cols in base.items():
        s = pd.to_numeric(df[cols[0]], errors="coerce")
        for c in cols[1:]:
            s = s.combine_first(pd.to_numeric(df[c], errors="coerce"))
        out[b] = s
    wide = pd.DataFrame(out)
    wide = wide.where(wide > 0)  # prices must be positive
    print(f"  wide panel: {wide.shape[0]} days x {wide.shape[1]} symbols "
          f"({wide.index.min().date()}..{wide.index.max().date()})")
    long = wide.reset_index().melt(id_vars="date", var_name="symbol", value_name="close").dropna()
    print(f"  long rows: {len(long):,}")
    return long.sort_values(["symbol", "date"])


def build_membership() -> pd.DataFrame:
    t = pd.read_excel(ROOT / "NIFTY500_TICKER_2005_2025_Final.xlsx", sheet_name="Sheet1")
    t.columns = [str(c).strip() for c in t.columns]
    my, tk = t.columns[0], t.columns[1]
    t["month"] = pd.to_datetime(t[my], format="%b%Y", errors="coerce")
    t = t.dropna(subset=["month"]).rename(columns={tk: "symbol"})
    t["symbol"] = t["symbol"].astype(str).str.strip().str.upper()
    print(f"  membership: {t['month'].nunique()} months, {t['symbol'].nunique()} unique tickers "
          f"({t['month'].min().date()}..{t['month'].max().date()})")
    return t[["month", "symbol"]].drop_duplicates()


def main() -> None:
    close = build_close_panel()
    close["symbol"] = close["symbol"].str.upper()
    close.to_parquet(OUT / "eq_close.parquet")
    mem = build_membership()
    mem.to_parquet(OUT / "membership.parquet")
    # quick audit
    n_sym = close["symbol"].nunique()
    cov = close.groupby("symbol")["date"].agg(["min", "max", "count"])
    print(f"\nAUDIT: {n_sym} symbols in price panel; median history "
          f"{cov['count'].median():.0f} days; "
          f"{(cov['count'] >= 252).sum()} symbols with >=1yr.")
    # membership symbols present in price panel?
    msym = set(mem["symbol"]); psym = set(close["symbol"])
    print(f"  membership tickers with price data: {len(msym & psym)}/{len(msym)} "
          f"(missing {len(msym - psym)} — name mismatches to reconcile later)")
    print(f"saved -> {OUT}\\eq_close.parquet, membership.parquet")


if __name__ == "__main__":
    main()
