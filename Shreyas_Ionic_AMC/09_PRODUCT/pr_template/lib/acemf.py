# -*- coding: utf-8 -*-
"""acemf.py — loader for the ACE MF "Advisory V2" monthly extract.

Single consolidated MF data source from 2026-08-05 (Principal ruling): the advisory's own ACE MF
template, refreshed monthly. Supersedes the ad-hoc mix of MF Dashboard.xlsx and repo NAV files for
every field it covers. Verification of the first file:
`05_DATA_OFFICE/ACEMF_VERIFICATION_2026-08-05.md`.

FIVE THINGS THIS FILE FORMAT WILL DO TO YOU IF YOU PARSE IT NAIVELY
-------------------------------------------------------------------
1. The real header is EXCEL ROW 9 (`header=8`). Rows 1-8 hold a template tag
   (`>>CustomTemplate:Advisory V2`), a numbered column ruler, and a row of GROUP headers.
2. Column names REPEAT across blocks: six separate `Month End`, four `Others`, two
   `Up Capture Ratio`. Read with pandas and the later ones silently overwrite the earlier ones,
   so you end up joining the Rating-Allocation as-of date onto the Expense block. We de-duplicate
   with a `#n` suffix and expose named accessors instead.
3. THE FILENAME LIES ABOUT THE DATE. The first file was named "31th July_2026" while every
   holdings-derived block was stamped 202606 (30-June). Never label a deck from the filename;
   use `block_asof()`.
4. IT IS A MIXED-AS-OF DATASET. Holdings blocks and the return block are different vintages, and
   each block carries its own `Month End`. Stamp pages per block, never once for the file.
5. 39.5% of rows are NOT at the file's modal month-end; some date to 2018. Staleness is a
   per-fund, per-block property. `stale_rows()` and the freshness gate exist for this.

Plan values are `Standard Plan` (= Regular), `Direct Plan`, `Suspended Plan`, `Regular`,
`Institutional`... `direct_growth()` filters to Direct and DROPS Suspended.
"""
import os
import re

import pandas as pd

# Block name -> its own as-of column, after de-duplication. The suffix order follows the sheet's
# left-to-right block order and is asserted on load, so a template change fails loudly.
BLOCK_ASOF = {
    "expense": "Month End",
    "asset_allocation": "Month End#1",
    "asset_type_allocation": "Month End#2",
    "sector_allocation": "Month End#3",
    "maturity_ytm": "Month End#4",
    "rating_allocation": "Month End#5",
    "maturity_profile": "Month End#6",
}

# Columns we rely on downstream. Load fails if any is missing rather than yielding NaN later.
REQUIRED = [
    "Scheme Name", "ISIN Code", "Plan", "AMC Name", "Inception Date",
    "Asset Type", "Category", "Benchmark Indices",
    "Ratio", "Direct Plan Ratio",
    "Equity", "Debt", "Others",
    "Up Capture Ratio", "Down Capture Ratio", "Up/Down Capture Ratio",
    "SD Annualised", "YTM (%)", "Average Maturity Years", "Modified Duration Years",
]

SECTOR_START, SECTOR_END = "Abrasives", "Trading"      # inclusive span of the 44 sector columns

# Categories whose ACE "Equity" figure is GROSS exposure, much of it hedged. Feeding these into an
# IPS equity-band check as if they were equity RISK misstates the book: arbitrage shows a median
# 70.5% equity and is economically debt-like. Flagged for the FM (2026-08-05); until a net-exposure
# rule is agreed these are reported as gross with the caveat attached, never silently netted.
GROSS_EQUITY_CAVEAT = {
    "Arbitrage Fund", "Equity Savings", "Balanced Advantage",
    "Dynamic Asset Allocation", "Multi Asset Allocation",
}


def _dedupe(names):
    out, seen = [], {}
    for i, h in enumerate(names):
        n = str(h).strip() if pd.notna(h) else f"col{i}"
        if n in seen:
            seen[n] += 1
            n = f"{n}#{seen[n]}"
        else:
            seen[n] = 0
        out.append(n)
    return out


def load(path, cache_parquet=None):
    """Read an ACE MF Advisory-V2 extract into a tidy frame.

    Returns (df, meta). `meta` carries the per-block as-of map and the modal file as-of, so a
    caller never has to guess a date. Numeric columns are coerced; everything else stays string.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"ACE MF extract not found: {path}")

    raw = pd.read_excel(path, sheet_name=0, header=None)

    # Locate the header by CONTENT, not by a hardcoded index. The preamble is 8 rows in the first
    # file, but it carries a template tag, a numbered ruler and a group-header row, and none of
    # those are guaranteed to stay put across monthly exports. Hardcoding row 9 already cost one
    # off-by-one here.
    col0 = raw.iloc[:, 0].astype(str)
    hdr_candidates = col0[col0.str.strip().str.lower() == "scheme name"].index
    if len(hdr_candidates) == 0:
        raise ValueError(
            "could not find the header row: no cell in column A reads 'Scheme Name'. This loader "
            "is written for the ACE 'Advisory V2' export; a different template needs its own map.")
    hdr_row = int(hdr_candidates[0])

    tag = " ".join(str(v) for v in raw.iloc[:hdr_row, 0].dropna().astype(str))
    if "CustomTemplate" not in tag:
        raise ValueError(
            f"the preamble above the header does not carry an ACE template tag (got {tag[:70]!r}).")
    df = raw.iloc[hdr_row + 1:].reset_index(drop=True)
    df.columns = _dedupe(raw.iloc[hdr_row])
    df = df.dropna(how="all").copy()

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"ACE extract is missing expected columns: {missing}. Template changed?")
    missing_asof = [c for c in BLOCK_ASOF.values() if c not in df.columns]
    if missing_asof:
        raise ValueError(f"ACE extract is missing block as-of columns: {missing_asof}.")

    num = (["Ratio", "Direct Plan Ratio", "Equity", "Debt", "Others",
            "Up Capture Ratio", "Down Capture Ratio", "Up/Down Capture Ratio",
            "Up Capture Ratio#1", "Down Capture Ratio#1", "Up/Down Capture Ratio#1",
            "SD", "SD Annualised", "YTM (%)", "Average Maturity Years",
            "Modified Duration Years", "Macaulay Duration Years",
            "1 Month", "3 Months", "6 Months", "9 Months", "1 Year", "3 Years", "5 Years",
            "SINCE INCEPTION", "SI Benchmark"]
           + sector_columns(df) + rating_columns(df))
    for c in num:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    asof = {}
    for blk, col in BLOCK_ASOF.items():
        vals = df[col].dropna().astype(str)
        asof[blk] = vals.mode().iloc[0] if len(vals) else None
    modal = pd.Series([v for v in asof.values() if v]).mode()
    meta = {"path": path, "template": tag, "block_asof": asof,
            "file_asof": modal.iloc[0] if len(modal) else None,
            "rows": len(df)}

    if cache_parquet:
        df.astype({c: "string" for c in df.columns
                   if df[c].dtype == object}).to_parquet(cache_parquet)
    return df, meta


def sector_columns(df):
    """The 44 sector columns, by position between the two known end-posts."""
    cols = list(df.columns)
    try:
        a, b = cols.index(SECTOR_START), cols.index(SECTOR_END)
    except ValueError:
        return []
    return cols[a:b + 1]


def rating_columns(df):
    return [c for c in df.columns
            if re.match(r"^(A|AA|AAA|A1|B|BB|BBB|D|SOV|Unrated|Cash & Equivalent)"
                        r"( ?/ ?[A-Z0-9+\-]+)*$", str(c).strip())]


def direct_growth(df):
    """Direct plan only, Suspended dropped. Growth-vs-IDCW is encoded in the scheme NAME, not in a
    column, so callers matching a client's holding must still resolve the option by name."""
    d = df[df["Plan"].astype(str).str.strip() == "Direct Plan"].copy()
    return d[~d["Plan"].astype(str).str.contains("Suspend", case=False, na=False)]


def block_asof(meta, block):
    """As-of for ONE block. Use this on every page; never the filename, never a single file date."""
    if block not in BLOCK_ASOF:
        raise KeyError(f"unknown block {block!r}; known: {sorted(BLOCK_ASOF)}")
    return meta["block_asof"].get(block)


def stale_rows(df, block, asof=None):
    """Rows whose own as-of for `block` is older than `asof` (default: that block's modal value).

    39.5% of the first file's allocation rows were behind the modal month-end and some were years
    behind, so this is the difference between a number a client can rely on and one that is quietly
    from 2018."""
    col = BLOCK_ASOF[block]
    vals = df[col].astype(str)
    ref = asof or (vals[vals != "nan"].mode().iloc[0] if len(vals) else None)
    if ref is None:
        return df.iloc[0:0]
    return df[(vals != ref) & (vals != "nan")]


def equity_lookthrough(df):
    """Per-row equity %, with the gross-exposure caveat surfaced rather than buried.

    Returns a frame with `equity_pct` and `equity_is_gross`. A hybrid's real equity sleeve is what
    fixes the FM's comment #2: our previous code classified funds by CATEGORY and counted every
    hybrid as 0% equity, understating a book's true equity by roughly 73% of any aggressive-hybrid
    holding's weight.
    """
    out = df.copy()
    out["equity_pct"] = pd.to_numeric(out["Equity"], errors="coerce")
    out["equity_is_gross"] = out["Category"].astype(str).str.strip().isin(GROSS_EQUITY_CAVEAT)
    return out[["Scheme Name", "ISIN Code", "Category", "Asset Type",
                "equity_pct", "equity_is_gross"]]
