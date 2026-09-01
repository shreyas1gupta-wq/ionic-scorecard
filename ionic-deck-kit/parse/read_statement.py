# -*- coding: utf-8 -*-
"""Read a holding statement of unknown layout into a clean holdings table.

WHY IT WORKS THIS WAY. The advisor will send whatever their platform produces: a CAS, a CAMS or
Kfintech statement, or some AMC's own export. Column names differ, sheet names differ, there is often
a title block above the header and a TOTAL row below the data. A reader that assumes one layout will
fail on the second file it sees, and the dangerous failure is the quiet one.

So this reads by IDENTITY, not position. It scans every sheet for cells that look like an ISIN, then
takes the numbers on that row and decides which is the market value. An ISIN is the one field every
statement format carries, and it is the key the score file is published on.

NOTHING IS EVER DROPPED SILENTLY. Rows that look like holdings but cannot be resolved go to an
exceptions list that travels with the output, and the caller is expected to show it.
"""
import os
import re

import pandas as pd

ISIN_RE = re.compile(r"^IN[A-Z0-9]\w{9}$")
# header words we might see for the two numbers that matter, in rough order of preference
VALUE_WORDS = ["market value", "current value", "closing value", "value (rs", "valuation",
               "current amount", "market val", "amount"]
COST_WORDS = ["invested", "purchase", "cost", "amount invested", "book value"]
UNIT_WORDS = ["unit", "balance unit", "closing unit", "quantity"]
NAME_WORDS = ["scheme", "fund", "security", "instrument", "description"]
HOLDER_WORDS = ["investor", "holder", "member", "name of", "account", "client"]
FOLIO_WORDS = ["folio"]
SKIP_ROW_WORDS = ("total", "grand total", "sub total", "subtotal", "sum")


def _norm(x):
    return re.sub(r"\s+", " ", str(x)).strip().lower()


def _num(x):
    """A number, or None. Never NaN.

    The string "nan" parses to float('nan') perfectly happily, and NaN then poisons every comparison
    downstream: max() over a list starting with NaN returns whatever it saw first, so the statement
    reconciliation computed a stated total of 0 and switched itself off without a word.
    """
    if isinstance(x, (int, float)):
        return None if pd.isna(x) else float(x)
    s = re.sub(r"[,\s₹]", "", str(x))
    try:
        v = float(s)
    except ValueError:
        return None
    return None if v != v else v


def _find_header(df, isin_col):
    """The header is the nearest row ABOVE the first ISIN whose cells are mostly words."""
    first = None
    for i in range(len(df)):
        v = df.iat[i, isin_col]
        if v is not None and ISIN_RE.match(str(v).strip()):
            first = i
            break
    if first is None:
        return None, {}
    for i in range(first - 1, max(-1, first - 12), -1):
        cells = [_norm(c) for c in df.iloc[i].tolist()]
        wordy = sum(1 for c in cells if c and c != "nan" and not _num(c))
        if wordy >= 3:
            return i, {j: c for j, c in enumerate(cells) if c and c != "nan"}
    return None, {}


def _pick(hdr, words, exclude=()):
    """Most SPECIFIC word wins, not the leftmost column.

    This looped columns-outer, words-inner, so the first column matching ANY word took it. On a sheet
    with "Amount Invested" before "Market Value", the generic word "amount" claimed the invested
    column as the market value and the parsed total came out at half the real figure, with no error.
    Words are listed most specific first, so they must be the outer loop.
    """
    for w in words:
        for j, name in hdr.items():
            if j in exclude:
                continue
            if w in name:
                return j
    return None


def read_statement(path):
    """Return (holdings DataFrame, exceptions DataFrame, notes dict)."""
    book = pd.read_excel(path, sheet_name=None, header=None)
    rows, exc, sheets_used = [], [], []

    for sheet, df in book.items():
        if df.empty:
            continue
        # which column holds ISINs on this sheet?
        counts = {}
        for j in range(df.shape[1]):
            counts[j] = sum(1 for v in df.iloc[:, j] if v is not None and ISIN_RE.match(str(v).strip()))
        isin_col = max(counts, key=counts.get) if counts else None
        if isin_col is None or counts[isin_col] == 0:
            continue
        sheets_used.append(sheet)

        hrow, hdr = _find_header(df, isin_col)
        c_val = _pick(hdr, VALUE_WORDS)
        c_cost = _pick(hdr, COST_WORDS, exclude={c_val} if c_val is not None else ())
        c_unit = _pick(hdr, UNIT_WORDS)
        c_name = _pick(hdr, NAME_WORDS)
        c_hold = _pick(hdr, HOLDER_WORDS)
        c_folio = _pick(hdr, FOLIO_WORDS)
        # "amount" appears in both lists; never let one column serve as value AND cost
        if c_val is not None and c_val == c_cost:
            c_cost = None

        for i in range(len(df)):
            raw = df.iloc[i].tolist()
            cell = str(raw[isin_col]).strip() if raw[isin_col] is not None else ""
            joined = " ".join(_norm(x) for x in raw if x is not None)
            if not ISIN_RE.match(cell):
                # a row with money on it but no ISIN, sitting inside the data block, is worth flagging
                if hrow is not None and i > hrow and any(_num(x) is not None and _num(x) > 1000
                                                         for x in raw):
                    if not any(w in joined for w in SKIP_ROW_WORDS):
                        exc.append(dict(sheet=sheet, row=i + 1, reason="no ISIN on the row",
                                        text=joined[:160]))
                continue
            if any(w in joined for w in SKIP_ROW_WORDS):
                continue

            val = _num(raw[c_val]) if c_val is not None else None
            if val is None:
                # fall back to the largest number on the row, which is the market value in
                # every layout seen so far
                nums = [n for n in (_num(x) for x in raw) if n is not None and n > 0]
                val = max(nums) if nums else None
            if val is None:
                exc.append(dict(sheet=sheet, row=i + 1, reason="ISIN found but no value",
                                text=joined[:160]))
                continue
            cost = _num(raw[c_cost]) if c_cost is not None else None
            rows.append(dict(
                isin=cell, sheet=sheet,
                scheme=(str(raw[c_name]).strip() if c_name is not None and raw[c_name] else ""),
                holder=(str(raw[c_hold]).strip() if c_hold is not None and raw[c_hold] else ""),
                folio=(str(raw[c_folio]).strip() if c_folio is not None and raw[c_folio] else ""),
                units=(_num(raw[c_unit]) if c_unit is not None else None),
                invested=cost, value=val))

    H = pd.DataFrame(rows)
    E = pd.DataFrame(exc)

    # RECONCILE against any TOTAL row the statement prints for itself. This is the check that would
    # have caught the column mis-pick above on its own: the parsed sum was half the stated total and
    # nothing else complained.
    stated = None
    for sheet, df in book.items():
        for i in range(len(df)):
            cells = [_norm(c) for c in df.iloc[i].tolist()]
            if any(c in ("total", "grand total") for c in cells):
                nums = [n for n in (_num(x) for x in df.iloc[i].tolist()) if n is not None]
                if nums:
                    stated = max(stated or 0, max(nums))
    parsed = float(H["value"].sum()) if len(H) else 0.0
    recon = None
    if stated:
        gap = parsed - stated
        recon = dict(stated=stated, parsed=parsed, gap=gap,
                     gap_pct=(gap / stated * 100) if stated else None,
                     ok=abs(gap) <= max(1.0, 0.005 * stated))
    notes = dict(sheets_with_holdings=sheets_used,
                 sheets_ignored=[s for s in book if s not in sheets_used],
                 # H["isin"], never H.isin: the attribute form resolves to DataFrame.isin, the method.
                 rows=len(H), schemes=int(H["isin"].nunique()) if len(H) else 0,
                 holders=int(H["holder"].nunique()) if len(H) else 0,
                 total_value=float(H["value"].sum()) if len(H) else 0.0,
                 exceptions=len(E), reconciliation=recon)
    return H, E, notes


if __name__ == "__main__":
    import sys
    p = sys.argv[1]
    H, E, n = read_statement(p)
    print(f"  read {os.path.basename(p)}")
    print(f"    sheets with holdings : {n['sheets_with_holdings']}")
    print(f"    sheets ignored       : {n['sheets_ignored']}")
    print(f"    holding rows         : {n['rows']}")
    print(f"    distinct schemes     : {n['schemes']}")
    print(f"    holders              : {n['holders']}")
    print(f"    total value          : Rs {n['total_value']:,.0f}")
    print(f"    exceptions           : {n['exceptions']}")
    r = n.get("reconciliation")
    if r:
        print(f"    statement's own total: Rs {r['stated']:,.0f}")
        print(f"    reconciliation       : {'OK' if r['ok'] else 'MISMATCH'}  "
              f"gap Rs {r['gap']:,.0f} ({r['gap_pct']:+.2f}%)")
    else:
        print("    reconciliation       : no total row in the statement to check against")
    if len(E):
        print(E.to_string(index=False))
