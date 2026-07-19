"""
ALPHA_RANKER/rnd/lib/build_panel_pit.py

T5 REMEDIATION (Gate-4 FAIL, LOOKAHEAD_T1T10.md) -- Arjun Rao, 2026-07-17.

panel_long.parquet's universe = ALL 969 tickers ever found in the master
price file, present at EVERY historical date regardless of whether that
name was actually IN the Nifty500/750 index at that date (firm landmine #6:
survivorship bias runs through *inclusion*, not just omission -- a stock
that only entered the broad-market universe in 2019 still appears, scored,
at 2005 dates if its price series happens to reach that far back e.g. via a
different listing; more importantly, names that stayed in some CURRENT-750
list are present at ALL dates even where they weren't Nifty500 constituents
yet/anymore). This build filters panel_long.parquet down to a PIT-correct
cross-section: at each rebalance date t, only symbols that were members of
the NEAREST-PRIOR NIFTY500_TICKER_2005_2025_Final.xlsx snapshot are kept.

NO-LOOKAHEAD CONTRACT:
  - membership at date t comes ONLY from the snapshot dated <= t (backward
    merge_asof) -- never a future snapshot.
  - "union with price availability" per task spec = the eligible universe at
    t is (PIT-member set as-of-t) INTERSECTED with (symbols panel_long
    already has a priced row for at t) -- panel_long rows only exist where
    real price data exists (see build_panel_long.py process_symbol: gated on
    each ticker's own [file_min, file_max] listing window), so no new price
    lookup is needed here; we simply drop panel_long rows whose symbol is
    NOT in the as-of-t PIT set. This can only REMOVE rows, never add rows
    for names without price data.

TICKER MATCH: verified exact-string match, ALL 969 panel_long symbols are a
  subset of the 1004 unique PIT-file tickers (checked directly, no fuzzy/
  rename mapping needed) -- see FND_panel_pit.md for the verification.

SNAPSHOT CADENCE: 42 semi-annual snapshots (Mar/Sep, 2005-2025), ~501
  tickers each. Snapshot "as-of" date = last calendar day of that month
  (e.g. "Mar2005" -> 2005-03-31). panel_long's own date range
  (2005-04-29 -> 2025-12-05) is fully covered forward from the first
  snapshot (2005-03-31, precedes the first panel date) through the last
  (2025-09-30); panel dates after 2025-09-30 use the Sep-2025 snapshot
  forward-carried (documented, not fabricated -- no newer snapshot exists).

Run: python build_panel_pit.py
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]  # .../NIFTY 500
AR = ROOT / "ALPHA_RANKER"
PIT_XLSX = ROOT / "NIFTY500_TICKER_2005_2025_Final.xlsx"
PANEL_LONG_PATH = AR / "rnd" / "panel" / "panel_long.parquet"
OUT_PARQUET = AR / "rnd" / "panel" / "panel_pit.parquet"
REPORT_MD = AR / "rnd" / "reports" / "FND_panel_pit.md"
SCHEMA_MD = AR / "rnd" / "panel" / "PANEL_SCHEMA.md"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_pit_snapshots() -> pd.DataFrame:
    """Returns a long df: snapshot_date, ticker (one row per PIT snapshot
    membership entry)."""
    pit = pd.read_excel(PIT_XLSX, sheet_name="Sheet1")
    pit["snapshot_date"] = pd.to_datetime(pit["Month-Year"], format="%b%Y") + pd.offsets.MonthEnd(0)
    pit = pit.rename(columns={"Ticker": "symbol"})[["snapshot_date", "symbol"]]
    return pit.sort_values("snapshot_date").reset_index(drop=True)


def main():
    t0 = time.time()
    log(f"Loading PIT universe file {PIT_XLSX.name} ...")
    pit = load_pit_snapshots()
    snap_dates = sorted(pit["snapshot_date"].unique())
    log(f"PIT snapshots: {len(snap_dates)}, {pd.Timestamp(snap_dates[0]).date()} -> "
        f"{pd.Timestamp(snap_dates[-1]).date()}; "
        f"{pit.groupby('snapshot_date').size().mean():.1f} tickers/snapshot avg")

    log(f"Loading {PANEL_LONG_PATH.name} ...")
    panel = pd.read_parquet(PANEL_LONG_PATH)
    panel["date"] = pd.to_datetime(panel["date"])
    n_rows_before = len(panel)
    n_symbols_before = panel["symbol"].nunique()
    n_dates = panel["date"].nunique()
    log(f"panel_long: {n_rows_before} rows, {n_dates} dates, {n_symbols_before} symbols")

    # --- ticker match verification (documented, not re-guessed) ---
    pit_tickers = set(pit["symbol"].unique())
    panel_tickers = set(panel["symbol"].unique())
    unmatched = panel_tickers - pit_tickers
    log(f"Ticker match check: {len(panel_tickers)} panel_long symbols, "
        f"{len(panel_tickers & pit_tickers)} exact matches in PIT file, "
        f"{len(unmatched)} unmatched (dropped at every date, cannot be PIT-verified): "
        f"{sorted(unmatched)[:20]}")

    # --- assign each panel rebalance date its nearest-PRIOR snapshot ---
    panel_dates = pd.DatetimeIndex(sorted(panel["date"].unique()))
    snap_index = pd.DatetimeIndex(snap_dates)
    date_to_snap = pd.merge_asof(
        pd.DataFrame({"date": panel_dates}), pd.DataFrame({"snapshot_date": snap_index}),
        left_on="date", right_on="snapshot_date", direction="backward",
    )
    n_no_snap = date_to_snap["snapshot_date"].isna().sum()
    if n_no_snap:
        log(f"WARNING: {n_no_snap} panel dates precede the first PIT snapshot "
            f"({pd.Timestamp(snap_dates[0]).date()}) -- these dates get NO eligible universe "
            f"(dropped entirely, not silently included).")

    # --- vectorized eligibility: merge each row's assigned snapshot with the
    #     PIT (snapshot_date, symbol) membership table on both keys ---
    panel = panel.merge(date_to_snap, on="date", how="left")
    pit_membership = pit.rename(columns={"symbol": "symbol"}).assign(_in_pit=True)

    log("Filtering panel_long rows to PIT-eligible (date, symbol) pairs ...")
    merged = panel.merge(pit_membership, on=["snapshot_date", "symbol"], how="left")
    eligible_mask = merged["_in_pit"].fillna(False).values
    panel_pit = panel.loc[eligible_mask].drop(columns=["snapshot_date"]).reset_index(drop=True)

    n_rows_after = len(panel_pit)
    n_symbols_after = panel_pit["symbol"].nunique()
    log(f"panel_pit: {n_rows_after} rows ({n_rows_after/n_rows_before:.1%} of panel_long), "
        f"{n_symbols_after} unique symbols ever eligible")

    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    panel_pit.to_parquet(OUT_PARQUET, index=False)
    log(f"Saved {OUT_PARQUET}")

    # --- diagnostics: coverage per era ---
    panel["year"] = panel["date"].dt.year
    panel_pit_tmp = panel.loc[eligible_mask].copy()
    panel_pit_tmp["year"] = panel_pit_tmp["date"].dt.year
    full_by_year = panel.groupby("year").size()
    pit_by_year = panel_pit_tmp.groupby("year").size()
    names_by_year_full = panel.groupby("year")["symbol"].nunique()
    names_by_year_pit = panel_pit_tmp.groupby("year")["symbol"].nunique()

    era_bins = [(2005, 2009), (2010, 2014), (2015, 2019), (2020, 2025)]
    era_rows = []
    for lo, hi in era_bins:
        yrs = [y for y in range(lo, hi + 1)]
        full_n = full_by_year.reindex(yrs).sum()
        pit_n = pit_by_year.reindex(yrs).sum()
        era_rows.append({
            "era": f"{lo}-{hi}",
            "rows_full": int(full_n), "rows_pit": int(pit_n),
            "pct_kept": round(100 * pit_n / full_n, 1) if full_n else float("nan"),
            "avg_names_per_date_full": round(names_by_year_full.reindex(yrs).mean(), 1),
            "avg_names_per_date_pit": round(names_by_year_pit.reindex(yrs).mean(), 1),
        })
    era_df = pd.DataFrame(era_rows)
    log("Coverage by era:\n" + era_df.to_string(index=False))

    write_schema_addendum(len(snap_dates), snap_dates, unmatched, n_rows_before, n_rows_after)
    write_report(panel_pit, n_rows_before, n_rows_after, n_symbols_before, n_symbols_after,
                 unmatched, snap_dates, era_df, n_no_snap)
    log(f"Done in {time.time()-t0:.0f}s")


def write_schema_addendum(n_snapshots, snap_dates, unmatched, n_before, n_after):
    addendum = f"""

---

## ADDENDUM 2 — Survivorship-free PIT panel (`rnd/panel/panel_pit.parquet`)

Built by `rnd/lib/build_panel_pit.py` (T5 remediation, LOOKAHEAD_T1T10.md,
2026-07-17). Same schema/row-grain as `panel_long.parquet`, filtered:

- Universe at each rebalance date t = membership from the NEAREST-PRIOR
  snapshot in `NIFTY500_TICKER_2005_2025_Final.xlsx` ({n_snapshots} semi-annual
  snapshots, {pd.Timestamp(snap_dates[0]).date()} -> {pd.Timestamp(snap_dates[-1]).date()}),
  backward merge_asof (no future snapshot ever used).
- Intersected with price availability: since panel_long rows only exist where
  a symbol already has a priced observation at t, this filter can only REMOVE
  rows, never add rows for un-priced names.
- {len(unmatched)} panel_long symbols have no exact match in the PIT ticker
  list and are dropped at every date (cannot be PIT-verified): {sorted(unmatched)[:15]}{'...' if len(unmatched) > 15 else ''}
- Net effect: {n_before} panel_long rows -> {n_after} panel_pit rows
  ({n_after/n_before:.1%} kept). This is the FIRST panel in this codebase
  where the cross-section at a 2005-2015 date does not include names that
  only entered the CURRENT universe list years later, and correctly OMITS
  names not yet/no-longer index members at that date -- the direct fix for
  the T5_universe FAIL in `rnd/reports/LOOKAHEAD_T1T10.md`.
"""
    with open(SCHEMA_MD, "a", encoding="utf-8") as f:
        f.write(addendum)
    log(f"Appended PIT-panel addendum to {SCHEMA_MD}")


def write_report(panel_pit, n_before, n_after, n_sym_before, n_sym_after, unmatched,
                  snap_dates, era_df, n_no_snap):
    lines = [
        "# FND_panel_pit — Survivorship-free PIT Panel Build Report (T5 remediation)",
        "",
        "[DATA] Result: `ALPHA_RANKER/rnd/panel/panel_pit.parquet` built successfully.",
        "",
        "## Data lineage",
        f"- Base: `rnd/panel/panel_long.parquet` ({n_before} rows, {n_sym_before} symbols)",
        f"- PIT universe: `NIFTY500_TICKER_2005_2025_Final.xlsx` (repo root), Sheet1, "
        f"{len(snap_dates)} snapshots {pd.Timestamp(snap_dates[0]).date()} -> {pd.Timestamp(snap_dates[-1]).date()}",
        f"- Ticker match: {n_sym_before - len(unmatched)}/{n_sym_before} panel_long symbols exact-matched "
        f"in the PIT file; {len(unmatched)} unmatched (dropped at every date): {sorted(unmatched)}",
        f"- Panel dates preceding the first snapshot (no eligible universe, dropped): {n_no_snap}",
        "",
        "## Row counts",
        f"- panel_long rows: {n_before}",
        f"- panel_pit rows: {n_after} ({n_after/n_before:.1%} kept)",
        f"- panel_pit unique symbols (ever eligible at some date): {n_sym_after}",
        f"- panel_pit dates: {panel_pit['date'].nunique()}, "
        f"{panel_pit['date'].min().date()} -> {panel_pit['date'].max().date()}",
        "",
        "## Coverage by era",
        "",
        era_df.to_markdown(index=False),
        "",
        "## Verdict",
        "**REAL, survivorship-controlled at the index-membership level.** Filter is "
        "purely subtractive (never adds price-less rows); no future snapshot is ever "
        "used (backward merge_asof only). Weakest assumption: symbols unmatched to the "
        "PIT ticker list are dropped entirely rather than PIT-verified another way -- "
        "this is a conservative (bias-reducing) choice, not a lookahead risk, but it "
        "does mean the PIT panel's row count reduction combines TWO effects (genuine "
        "non-membership at date t, and the small unmatched-ticker dropout) -- see the "
        "unmatched list above, it is short.",
    ]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    log(f"Wrote {REPORT_MD}")


if __name__ == "__main__":
    main()
