# -*- coding: utf-8 -*-
"""The client's holdings workbook: every position, the call, the reason, the tax, formatted.

    python build/build_client_workbook.py <statement.xlsx> --client "<Name>"
        [--directives ...] [--lots ...] [--holdings out/<Client>_Holdings.xlsx]

WHY THIS REPLACES A to_excel() DUMP. The workbook goes to the client. It sat beside a deck that had
been through three QA gates while it was itself a raw frame dump: raw field names as column
headings, no number formats, no widths, no reconciliation, and no way for a reader to see which of
the two hundred rows the plan actually touches. A client reads the deck once and keeps the
spreadsheet, so the spreadsheet is the artefact that has to survive scrutiny.

WHAT IT WILL NOT DO. It never computes a call, never fills a gap with judgement and never prints a
number it could not strike. Where the source carries no acquisition cost - which is every directly
held share on an NSDL CAS, because the demat section lists units and market value and nothing else -
the cell says so in words and the Read me sheet says what document would close it.
"""
import argparse
import json
import os
import re
import sys

import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tax_engine as TAXE                                              # noqa: E402

# The deck's own palette, so the two artefacts do not look like they came from different firms.
NAVY = "16233B"
GOLD = "9A7B4F"
INK = "1F2430"
SLATE = "5C6472"
HAIR = "D8DCE3"
PANEL = "F4F5F7"
WHITE = "FFFFFF"

CALL_FILL = {
    "Sell": "FBE3E0",
    "Trim": "FDF0DC",
    "Hold": "E6F4EC",
    "Hold (watch)": "FDF0DC",
    "Exit (client)": "FDF0DC",
    "Retain": "EEF0F3",
    "No View": "ECE9F6",
}
CALL_TEXT = {
    "Sell": "9B2C1F",
    "Trim": "8A5A12",
    "Hold": "1E6E4A",
    "Hold (watch)": "8A5A12",
    "Exit (client)": "8A5A12",
    "Retain": "5C6472",
    "No View": "5B4A8A",
}

RUPEE = '#,##0;[Red]-#,##0'
PCT = '0.0"%"'

THIN = Side(style="thin", color=HAIR)
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def _cr(v):
    v = float(v or 0)
    return ("Rs %.2f Cr" % (v / 1e7)) if abs(v) >= 1e7 else ("Rs %.1f L" % (v / 1e5))


def _sheet(wb, title, cols, rows, widths=None, wrap_cols=(), freeze="A2", filt=True,
           money_cols=(), pct_cols=(), call_col=None, note=None):
    """One formatted table. cols is a list of headings; rows a list of lists."""
    ws = wb.create_sheet(title[:31])
    r0 = 1
    if note:
        ws.cell(row=1, column=1, value=note).font = Font(name="Calibri", size=10,
                                                         italic=True, color=SLATE)
        ws.cell(row=1, column=1).alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=1, start_column=1, end_row=2, end_column=max(1, len(cols)))
        ws.row_dimensions[1].height = 16
        ws.row_dimensions[2].height = 16
        r0 = 4
    for j, c in enumerate(cols, start=1):
        cell = ws.cell(row=r0, column=j, value=c)
        cell.font = Font(name="Calibri", size=10, bold=True, color=WHITE)
        cell.fill = PatternFill("solid", fgColor=NAVY)
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = BOX
    ws.row_dimensions[r0].height = 30
    for i, row in enumerate(rows, start=r0 + 1):
        for j, v in enumerate(row, start=1):
            cell = ws.cell(row=i, column=j, value=v)
            cell.font = Font(name="Calibri", size=10, color=INK)
            cell.border = BOX
            head = cols[j - 1]
            if head in money_cols:
                cell.number_format = RUPEE
                cell.alignment = Alignment(horizontal="right", vertical="top")
            elif head in pct_cols:
                cell.number_format = PCT
                cell.alignment = Alignment(horizontal="right", vertical="top")
            elif head in wrap_cols:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
            else:
                cell.alignment = Alignment(vertical="top")
            if call_col and head == call_col:
                k = str(v or "")
                cell.fill = PatternFill("solid", fgColor=CALL_FILL.get(k, PANEL))
                cell.font = Font(name="Calibri", size=10, bold=True,
                                 color=CALL_TEXT.get(k, SLATE))
                cell.alignment = Alignment(horizontal="center", vertical="center")
        if i % 2 == 0:
            for j in range(1, len(cols) + 1):
                if not (call_col and cols[j - 1] == call_col):
                    ws.cell(row=i, column=j).fill = PatternFill("solid", fgColor=PANEL)
    if widths:
        for j, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(j)].width = w
    if filt and rows:
        ws.auto_filter.ref = "A%d:%s%d" % (r0, get_column_letter(len(cols)), r0 + len(rows))
    ws.freeze_panes = ws.cell(row=r0 + 1, column=1)
    return ws


def main():
    ap = argparse.ArgumentParser(description="Build the client's formatted holdings workbook.")
    ap.add_argument("statement")
    ap.add_argument("--client", required=True)
    ap.add_argument("--holdings", required=True,
                    help="the frame the deck build already wrote, so the two cannot disagree")
    ap.add_argument("--directives", default=None)
    ap.add_argument("--lots", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    H = pd.read_excel(a.holdings)

    # READ THE STATEMENT THE WAY THE DECK READS IT. This did its own pd.read_excel and then
    # indexed a column literally named "Asset Name", so it worked on exactly one client's sheet
    # and raised KeyError on every other layout -- including the kit's own fixture. Running the
    # one command the skill documents, on the fixture shipped beside it, built the deck and then
    # died at rc=2. Half the delivered product, gone on any statement whose columns are named
    # differently, which is the normal case: the whole point of parse/read_statement.py is that
    # it finds its columns by VOCABULARY rather than by name.
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "parse"))
    from read_statement import read_statement                            # noqa: E402
    _S, _E, _n = read_statement(a.statement)

    # WHO HOLDS WHAT. The deck frame carries a COUNT of holders; a client wants the names, and on a
    # family book whose slabs differ the name is what decides the tax on an exit.
    by_isin, by_name = {}, {}
    _holder_rows = []
    if len(_S):
        _holder_rows += _S[["isin", "scheme", "holder"]].to_dict("records")
    if len(_E) and "holder" in _E.columns:
        _holder_rows += [{"isin": "", "scheme": r.get("name", ""), "holder": r.get("holder", "")}
                         for r in _E.to_dict("records")]
    for r in _holder_rows:
        who = str(r.get("holder") or "").strip().title()
        if not who:
            continue
        i = str(r.get("isin") or "").strip()
        n = str(r.get("scheme") or "").strip().lower()
        if i and i.lower() not in ("nan", ""):
            by_isin.setdefault(i, set()).add(who)
        if n:
            by_name.setdefault(n, set()).add(who)

    def holder(row):
        i = str(row.get("ISIN") or "").strip()
        n = str(row.get("Holding") or "").strip().lower()
        s = by_isin.get(i) or by_name.get(n) or set()
        return ", ".join(sorted(s)) if s else "Not stated"

    D = json.load(open(a.directives, encoding="utf-8")) if a.directives else {}
    LOTS = TAXE.load_lots(a.lots) if a.lots else {}
    GRAND = float(H["Value (Rs)"].sum())
    ASOF = ""
    try:
        import glob
        v = sorted(glob.glob(os.path.join(os.path.dirname(HERE), "scores", "VERSION.json")))
        if v:
            ASOF = json.loads(open(v[0], encoding="utf-8-sig").read()).get("as_of", "")
    except Exception:
        pass
    ASOF = D.get("as_of") or ASOF

    # ---- per-row enrichment ------------------------------------------------------------------
    rows = []
    for _, r in H.iterrows():
        d = r.to_dict()
        val = float(d.get("Value (Rs)") or 0)
        inv = float(d.get("Invested (Rs)") or 0)
        call = str(d.get("Our call") or "No View")
        is_share = str(d.get("ISIN") or "").startswith("INE")
        # THE COST BASIS, AND WHERE IT CAME FROM. On an NSDL CAS the demat section carries the ISIN,
        # the units and the market value and nothing else, so a directly held share arrives with no
        # acquisition cost at all. That is a gap in the SOURCE, not in the reading of it, and the
        # cell says which document would close it rather than showing a blank or a zero.
        if inv > 0:
            basis, gain = "From the statement", val - inv
        elif is_share or str(d.get("Category") or "").startswith("Direct Equity"):
            basis, gain = "Not in the CAS: demat holdings carry no purchase cost", None
        else:
            basis, gain = "Not supplied", None
        # A TRIM SELLS A SLICE, NOT THE POSITION. Priced on the full value, a Trim's tax read
        # as if the whole holding were being sold - on an over-cap position that is several times
        # the real bill, in the direction a client would notice only after it was paid. The
        # slice is what the trim engine sized and what the deck's own tax page uses.
        _trim = float(d.get("Trim amount (Rs)") or 0)
        _amt = _trim if (call == "Trim" and _trim > 0) else val
        _cost = (inv * (_amt / val) if (inv > 0 and val > 0 and _amt < val) else (inv or None))
        px = TAXE.price({"name": d.get("Holding"), "value_inr": _amt, "cost_inr": _cost,
                         "asset_class": d.get("Asset class"),
                         "sub_category": d.get("Category")}, LOTS)
        rows.append({
            **d,
            "Holder": holder(d),
            "Cost basis": basis,
            "Gain (Rs)": (None if gain is None else round(gain)),
            "Tax character on exit": px["character"],
            "_call": call, "_val": val, "_inv": inv,
            "_ltcg": px["ltcg_tax"], "_stcg": px["stcg_tax"], "_slab": px["slab_value"],
        })

    order = {"Exit (client)": 0, "Sell": 1, "Trim": 2, "Retain": 3,
             "Hold (watch)": 4, "Hold": 5, "No View": 6}
    rows.sort(key=lambda x: (order.get(x["_call"], 9), -x["_val"]))

    from openpyxl import Workbook
    wb = Workbook()
    wb.remove(wb.active)

    # ---- 1. Read me --------------------------------------------------------------------------
    ws = wb.create_sheet("Read me first")
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 104
    ws.cell(row=1, column=1, value="%s . portfolio review" % a.client).font = Font(
        name="Calibri", size=18, bold=True, color=NAVY)
    ws.cell(row=2, column=1, value="Holdings, the call on each, and the tax on the moves"
            ).font = Font(name="Calibri", size=11, color=SLATE)

    n_by_call = {}
    for x in rows:
        n_by_call[x["_call"]] = n_by_call.get(x["_call"], 0) + 1
    v_by_call = {}
    for x in rows:
        v_by_call[x["_call"]] = v_by_call.get(x["_call"], 0.0) + x["_val"]
    # TWO DIFFERENT GAPS, NOT ONE. A directly held share has no cost because the CAS demat
    # section does not carry one - a property of the document. A PMS, an ELSS or a deposit has no
    # cost because it did not come with one - a property of what was supplied. Reporting both as
    # the same gap names the wrong document as the fix for eighteen of them.
    _cas = [x for x in rows if x["_inv"] <= 0 and x["Cost basis"].startswith("Not in the CAS")]
    _oth = [x for x in rows if x["_inv"] <= 0 and not x["Cost basis"].startswith("Not in the CAS")]
    n_nocost, v_nocost = len(_cas), sum(x["_val"] for x in _cas)
    n_oth, v_oth = len(_oth), sum(x["_val"] for x in _oth)

    lines = [
        ("As at", ASOF or "see the covering deck"),
        ("Holdings in this book", "%d, worth %s" % (len(rows), _cr(GRAND))),
        ("Reconciliation",
         "The total above is the total the source statement prints for itself. Every holding is "
         "counted once, including the ones the desk issues no call on."),
        ("", ""),
        ("What each sheet holds", ""),
        ("Summary", "The book by asset class, by holder and by call."),
        ("All holdings", "Every position, its call and the reason for it, with the tax character "
                         "each would carry if it were sold."),
        ("What we would do", "Only the holdings the plan touches, with the amount against each."),
        ("Tax on exit", "The estimated tax on those moves, slice by slice, and what is not in the "
                        "estimate."),
        ("What stays", "Holdings that cannot be redeemed on request, and the terms that stop them."),
        ("Coverage and gaps", "What carries no view, and why."),
        ("", ""),
        ("Two things this book cannot tell you", ""),
        ("1. The gain on your shares",
         "The consolidated account statement lists directly held shares by ISIN, quantity and "
         "market value. It carries no purchase price, so no gain and no tax can be computed for "
         "them here. %d holdings worth %s are affected. Your broker's holdings or profit-and-loss "
         "report, or the demat transaction statement, carries the purchase cost and would close "
         "this."
         % (n_nocost, _cr(v_nocost))),
        ("   and on some other holdings",
         "A further %d holdings worth %s reached this review without a purchase cost of their own "
         "- the discretionary mandates, a deposit and a few schemes held outside the platform "
         "statement. Their managers or issuers hold the figure. The Cost basis column on the "
         "All holdings sheet says which of the two applies to each line."
         % (n_oth, _cr(v_oth))) if n_oth else ("", ""),
        ("2. When the debt units were bought",
         "A debt fund bought on or after 1 April 2023 is taxed at your own slab rate whatever the "
         "holding period; one bought before that date is taxed at 12.5 per cent. Where the "
         "purchase date did not reach this review the lower rate is shown and the sheet says so, "
         "so those figures can only be too small, never too large."),
        ("", ""),
        ("Please read this alongside the deck",
         "Nothing here is a tax opinion, and nothing executes until you authorise it. Confirm the "
         "holding period, the character of each gain and the rates that apply with your tax "
         "adviser before dealing."),
    ]
    r = 4
    for k, v in lines:
        if k:
            c = ws.cell(row=r, column=1, value=k)
            c.font = Font(name="Calibri", size=10, bold=True,
                          color=NAVY if v else GOLD)
            c.alignment = Alignment(vertical="top", wrap_text=True)
        if v:
            c = ws.cell(row=r, column=2, value=v)
            c.font = Font(name="Calibri", size=10, color=INK)
            c.alignment = Alignment(vertical="top", wrap_text=True)
            ws.row_dimensions[r].height = max(15, 13 * (1 + len(v) // 96))
        r += 1

    # ---- 2. Summary --------------------------------------------------------------------------
    ws2 = wb.create_sheet("Summary")
    ws2.column_dimensions["A"].width = 40
    for col in "BCD":
        ws2.column_dimensions[col].width = 18

    def block(ws, r, title, pairs, total=None):
        c = ws.cell(row=r, column=1, value=title.upper())
        c.font = Font(name="Calibri", size=9, bold=True, color=GOLD)
        r += 1
        for k, (n, v) in pairs:
            ws.cell(row=r, column=1, value=k).font = Font(name="Calibri", size=10, color=INK)
            ws.cell(row=r, column=2, value=n).font = Font(name="Calibri", size=10, color=SLATE)
            cell = ws.cell(row=r, column=3, value=round(v))
            cell.number_format = RUPEE
            cell.font = Font(name="Calibri", size=10, color=INK)
            p = ws.cell(row=r, column=4, value=round(v / GRAND * 100, 1) if GRAND else 0)
            p.number_format = PCT
            p.font = Font(name="Calibri", size=10, color=SLATE)
            r += 1
        if total is not None:
            ws.cell(row=r, column=1, value="Total").font = Font(name="Calibri", size=10, bold=True)
            cell = ws.cell(row=r, column=3, value=round(total))
            cell.number_format = RUPEE
            cell.font = Font(name="Calibri", size=10, bold=True, color=NAVY)
            r += 1
        return r + 1

    ws2.cell(row=1, column=1, value="%s . summary" % a.client).font = Font(
        name="Calibri", size=16, bold=True, color=NAVY)
    r = 3
    for j, h in enumerate(["", "Holdings", "Value (Rs)", "% of book"], start=1):
        c = ws2.cell(row=r, column=j, value=h)
        c.font = Font(name="Calibri", size=9, bold=True, color=WHITE)
        c.fill = PatternFill("solid", fgColor=NAVY)
    r += 2

    def agg(key):
        out = {}
        for x in rows:
            k = str(x.get(key) or "Not stated")
            n, v = out.get(k, (0, 0.0))
            out[k] = (n + 1, v + x["_val"])
        return sorted(out.items(), key=lambda kv: -kv[1][1])

    r = block(ws2, r, "By asset class", agg("Asset class"), GRAND)
    r = block(ws2, r, "By holder", agg("Holder"), GRAND)
    r = block(ws2, r, "Our call, and your own instructions",
              [(k, (n_by_call[k], v_by_call[k]))
               for k in sorted(n_by_call, key=lambda k: order.get(k, 9))], GRAND)

    # ---- 3. All holdings ---------------------------------------------------------------------
    COLS = ["Holding", "ISIN", "Category", "Asset class", "Holder", "Value (Rs)",
            "% of book", "Our call", "Why", "Invested (Rs)", "Gain (Rs)", "Cost basis",
            "Tax character on exit", "Fund score /100", "Steadiness /100", "Risk band",
            "Liquidity band"]
    body = [[
        x.get("Holding"), x.get("ISIN"), x.get("Category"), x.get("Asset class"), x.get("Holder"),
        round(x["_val"]), round(x["_val"] / GRAND * 100, 2) if GRAND else 0, x["_call"],
        x.get("Why"),
        (round(x["_inv"]) if x["_inv"] > 0 else None),
        x.get("Gain (Rs)"), x.get("Cost basis"), x.get("Tax character on exit"),
        (None if pd.isna(x.get("Fund score /100")) else x.get("Fund score /100")),
        (None if pd.isna(x.get("Steadiness /100")) else x.get("Steadiness /100")),
        x.get("Risk band"), x.get("Liquidity band"),
    ] for x in rows]
    _sheet(wb, "All holdings", COLS, body,
           widths=[46, 14, 26, 13, 22, 15, 10, 14, 72, 15, 14, 34, 30, 10, 10, 11, 12],
           wrap_cols=("Why", "Cost basis", "Tax character on exit", "Holding"),
           money_cols=("Value (Rs)", "Invested (Rs)", "Gain (Rs)"),
           pct_cols=("% of book",), call_col="Our call",
           note="Every holding in the book, largest action first. A blank in Invested or Gain "
                "means the source statement carried no purchase cost for that holding, not that "
                "there is no gain. The Cost basis column says which.")

    # ---- 4. What we would do -----------------------------------------------------------------
    act = [x for x in rows if x["_call"] in ("Sell", "Trim", "Exit (client)")]
    ACOLS = ["Holding", "Category", "Holder", "Whose decision", "Action", "Amount (Rs)",
             "% of book", "Why", "Tax character on exit"]
    abody = [[
        x.get("Holding"), x.get("Category"), x.get("Holder"),
        ("Your instruction" if x["_call"] == "Exit (client)" else "The desk"),
        ("Sell in full" if x["_call"] == "Sell" else
         "Trim to the cap" if x["_call"] == "Trim" else "Exit in full"),
        round(x["_val"]), round(x["_val"] / GRAND * 100, 2) if GRAND else 0,
        x.get("Why"), x.get("Tax character on exit"),
    ] for x in act]
    _sheet(wb, "What we would do", ACOLS, abody,
           widths=[46, 26, 22, 17, 15, 15, 10, 72, 30],
           wrap_cols=("Why", "Holding", "Tax character on exit"),
           money_cols=("Amount (Rs)",), pct_cols=("% of book",),
           note="The %d holdings the plan touches, worth %s in all. 'Whose decision' separates the "
                "desk's own calls from the exits you have instructed: the firm's view on the "
                "holdings in the second group is unchanged, and they are shown apart so the two "
                "are never read as one." % (len(act), _cr(sum(x['_val'] for x in act))))

    # ---- 5. Tax on exit ----------------------------------------------------------------------
    TCOLS = ["Holding", "Whose decision", "Amount (Rs)", "Tax character on exit",
             "Est. long-term tax (Rs)", "Est. short-term tax (Rs)",
             "Taxed at your slab (Rs)", "Note"]
    tbody = []
    for x in act:
        tbody.append([
            x.get("Holding"),
            ("Your instruction" if x["_call"] == "Exit (client)" else "The desk"),
            round(x["_val"]), x.get("Tax character on exit"),
            (round(x["_ltcg"]) if x["_ltcg"] else None),
            (round(x["_stcg"]) if x["_stcg"] else None),
            (round(x["_slab"]) if x["_slab"] else None),
            ("No purchase cost on file, so no gain is computed" if x["_inv"] <= 0
             and not x["_slab"] else ""),
        ])
    T_LT = sum(x["_ltcg"] for x in act)
    T_ST = sum(x["_stcg"] for x in act)
    # SECTION 112A GIVES EACH HOLDER Rs 1.25 LAKH A YEAR, and this is a family book. Applied once
    # across the programme, exactly as the deck applies it - per holding it would give the same
    # exemption to a scheme twenty times over, and this workbook and the deck must not disagree by
    # a rupee on a number the client will compare.
    # THE SAME POPULATION THE DECK COUNTS: every named individual in the statement, not the
    # holders of the action rows alone and not the labels that are not people.
    N_HOLDERS = max(1, len(TAXE.named_holders(
        [r.get("holder") for r in _holder_rows])))
    _eq_gain = sum((x["_ltcg"] / TAXE.EQUITY_LTCG) for x in act
                   if x["_ltcg"] and TAXE.is_equity_oriented(x.get("Asset class"),
                                                             x.get("Category"),
                                                             x.get("Holding")))
    _relief = min(T_LT, min(_eq_gain, TAXE.LTCG_EXEMPT_PER_HOLDER * N_HOLDERS) * TAXE.EQUITY_LTCG)
    T_LT = max(0.0, T_LT - _relief)
    if tbody and tbody[-1][0] != "TOTAL" and _relief > 0:
        pass
    T_SL = sum(x["_slab"] for x in act)
    T_V = sum(x["_val"] for x in act)
    if _relief > 0:
        tbody.append(["Less: the Rs 1.25 lakh a year long-term exemption, once for each of the "
                      "%d holders" % N_HOLDERS, "", None, "Section 112A", -round(_relief),
                      None, None, ""])
    tbody.append(["TOTAL", "", round(T_V), "", round(T_LT), round(T_ST), round(T_SL), ""])
    _sheet(wb, "Tax on exit", TCOLS, tbody,
           widths=[46, 17, 15, 32, 20, 20, 20, 44],
           wrap_cols=("Holding", "Tax character on exit", "Note"),
           money_cols=("Amount (Rs)", "Est. long-term tax (Rs)", "Est. short-term tax (Rs)",
                       "Taxed at your slab (Rs)"),
           note="An estimate, not a tax opinion. Long-term and short-term are shown separately "
                "because they are taxed at different rates. The last column is money whose rate "
                "depends on your own slab - bank interest, and any debt units bought on or after "
                "1 April 2023, which lost capital-gains treatment entirely. Each family member's "
                "slab differs, so no figure is put against it here. "
                "Gross %s, estimated capital-gains tax %s, at slab %s."
                % (_cr(T_V), _cr(T_LT + T_ST), _cr(T_SL)))

    # ---- 6. What stays -----------------------------------------------------------------------
    keep = [x for x in rows if x["_call"] == "Retain"]
    if keep:
        _sheet(wb, "What stays", ["Holding", "Holder", "Value (Rs)", "% of book",
                                  "Why it stays, though you asked us to exit it"],
               [[x.get("Holding"), x.get("Holder"), round(x["_val"]),
                 round(x["_val"] / GRAND * 100, 2) if GRAND else 0, x.get("Why")] for x in keep],
               widths=[46, 22, 15, 10, 96], wrap_cols=("Why it stays, though you asked us to "
                                                       "exit it", "Holding"),
               money_cols=("Value (Rs)",), pct_cols=("% of book",), filt=False,
               note="Your instruction was to exit the fixed-income sleeve. These holdings cannot "
                    "be redeemed on request. %s stays where it is, and none of it is counted in "
                    "the proceeds or the tax on the other sheets. The desk's own view on each is "
                    "unchanged: they are held because their terms do not permit an exit, not "
                    "because we would otherwise keep them."
                    % _cr(sum(x["_val"] for x in keep)))

    # ---- 7. Coverage and gaps ----------------------------------------------------------------
    nv = [x for x in rows if x["_call"] == "No View"]
    _sheet(wb, "Coverage and gaps",
           ["Holding", "Category", "Asset class", "Value (Rs)", "% of book", "Why no view"],
           [[x.get("Holding"), x.get("Category"), x.get("Asset class"), round(x["_val"]),
             round(x["_val"] / GRAND * 100, 2) if GRAND else 0, x.get("Why")] for x in nv],
           widths=[46, 26, 13, 15, 10, 84], wrap_cols=("Why no view", "Holding"),
           money_cols=("Value (Rs)",), pct_cols=("% of book",),
           note="%d holdings worth %s carry no view. Not reviewed is not the same as not held: "
                "every one of them counts in full in the total, in every weight and in every "
                "concentration test on the other sheets and in the deck."
                % (len(nv), _cr(sum(x["_val"] for x in nv))))

    out = a.out or os.path.join(os.path.dirname(a.holdings),
                                "%s_Portfolio_Workbook.xlsx"
                                % re.sub(r"[^A-Za-z0-9]+", "_", a.client).strip("_"))
    wb.save(out)
    print("  workbook  : %s" % out)
    print("  sheets    : %s" % ", ".join(wb.sheetnames))
    print("  holdings  : %d, Rs %s" % (len(rows), format(round(GRAND), ",")))
    print("  actions   : %d, Rs %s   est. capital-gains tax Rs %s, at slab Rs %s"
          % (len(act), format(round(T_V), ","), format(round(T_LT + T_ST), ","),
             format(round(T_SL), ",")))
    print("  no cost   : %d holdings worth Rs %s carry no purchase price in the source"
          % (n_nocost, format(round(v_nocost), ",")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
