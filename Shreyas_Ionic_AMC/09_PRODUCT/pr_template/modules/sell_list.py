# -*- coding: utf-8 -*-
"""sell_list (F3), the names we would sell — CLIENT PAGE, Principal-reworked 2026-07-25:
- action column shows ONLY Sell (the old 'Under review' pill was ambiguous client-side;
  committee status stays internal). Reason-category column removed.
- each name gets a TWO-LINE case (client_case overlay if present, else the binding trigger,
  clause-clipped) + a visible 'p.NN' link to its full rationale card in the annexure.
- paginated 5 rows a page (2 pages for a 9-name book) so nothing is cramped.
- exceptional-call rule (asymmetric bars, Principal 2026-07-26): a Sell scoring ABOVE 40
  needs a 90%+-conviction exceptional case; holding a sub-40 scorer needs 60%+. Rows
  selling above 40 carry an amber EXCEPTIONAL tag and the page carries one footnote.
Returns the page count. score_band + scope_tag attach.
"""
from slidekit import NAVY, INK, SLATE, SELL, AMBER, SERIF, SANS, ML, UW, RX, clip_clause
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

PER = 5

LABELS = {
    "hni":    {"title": "The names we would sell, and the case for each",
               "lead": "Confirmed Sells only. Two lines carry the case; the linked page carries the full reasoning."},
    "std":    {"title": "The names we would sell, and why",
               "lead": "Confirmed Sells only. Two lines carry the case; the linked page has the full detail."},
    "simple": {"title": "The shares we would sell, and why",
               "lead": "Each name shows the reason in two lines; the page link has the full story."},
}

EXC_NOTE = ("Names selling above the 40 score line are exceptional, high-conviction calls; "
            "the linked page documents each case in full.")


def render(deck, ctx, tier):
    reg = tier["register"]
    L = LABELS.get(reg, LABELS["std"])
    as_of = ctx["client"].get("as_of", "")
    sells = sorted([e for e in ctx["equity"] if e["rec"] == "Sell"],
                   key=lambda e: -(e.get("weight_pct") or 0))
    pages = max(1, (len(sells) + PER - 1) // PER)

    cols = [("Holding", 0.20, "l"), ("Share %" if reg == "simple" else "Wt %", 0.06, "r"), ("Ionic Score", 0.13, "l"),
            ("Call", 0.09, "c"), ("The case", 0.46, "l"), ("Detail", 0.06, "r")]

    for p in range(pages):
        chunk = sells[p * PER:(p + 1) * PER]
        title = L["title"] + (f"  ({p + 1} of {pages})" if pages > 1 else "")
        s = deck.content(2, "Equity", "What we would sell", title)
        if p == 0:
            deck.anchor("tbl:sell_list", s, prio=5)
            deck.pill(s, 11.05, 1.42, f"Sell ×{len(sells)}", w=1.36, kind="Sell")
        deck.scope_tag(s, f"Direct equity only · as of {as_of}")
        deck.txt(s, ML, 1.84, UW, 0.24, [(L["lead"], SERIF, 10.5, SLATE, False, True)])

        ROWH = 0.62
        rows = []
        for e in chunk:
            exceptional = (e.get("ionic_score") or 0) >= 40
            # case must lean WITH the call: overlay (analyst-authored) first, else the
            # negative para (opens with the concern), never the trigger (can read bullish)
            case = e.get("client_case") or clip_clause(e.get("negative") or e.get("binding_trigger", ""), 118)
            rows.append([
                ("b", e["name"]),
                ("c", f"{e['weight_pct']:.1f}", INK),
                ("bar", e.get("ionic_score")),
                ("pill", "Sell", "Sell"),
                (case, ),                       # marker tuple replaced below (serif 2-liner)
                "",                             # detail link drawn as a pageref overlay
            ])
        # draw the table shell (case cell blank; we draw the 2-liner + pageref manually
        # so the case wraps to two clean serif lines and the link is clickable)
        shell = [[r[0], r[1], r[2], r[3], "", ""] for r in rows]
        deck.table(s, ML, 2.22, UW, cols, shell, rowh=ROWH, fs=9.5, hfs=8)

        tot = sum(c[1] for c in cols)
        score_x = ML + UW * sum(c[1] for c in cols[:2]) / tot + 0.08
        case_x = ML + UW * sum(c[1] for c in cols[:4]) / tot + 0.08
        case_w = UW * cols[4][1] / tot - 0.16
        ref_x = ML + UW * sum(c[1] for c in cols[:5]) / tot
        ry = 2.22 + 0.33
        exc_any = False
        for e, r in zip(chunk, rows):
            case = r[4][0]
            deck.txt(s, case_x, ry + 0.06, case_w, ROWH - 0.12,
                     [(case, SERIF, 9, INK, False)], ls=1.05, anchor=MSO_ANCHOR.MIDDLE)
            deck.pageref(s, ref_x, ry + ROWH / 2 - 0.09, f"stock:{e['symbol']}",
                         w=UW * cols[5][1] / tot - 0.06)
            deck.hotspot(s, ML, ry - 0.02, UW, ROWH, f"stock:{e['symbol']}")
            if (e.get("ionic_score") or 0) >= 40:
                exc_any = True
                deck.txt(s, score_x, ry + ROWH - 0.22, UW * cols[2][1] / tot - 0.1, 0.16,
                         [("EXCEPTIONAL", SANS, 6.5, AMBER, True, False, 80)])
            ry += ROWH

        fy = ry + 0.08
        if exc_any:
            deck.txt(s, ML, fy, UW, 0.2, [(EXC_NOTE, SERIF, 8.5, SLATE, False, True)])

        demo_tag = " Illustrative synthetic book." if ctx.get("is_demo", False) else ""
        deck.source(s, "Each row links to the name's full rationale page (score panel, the case, the bull "
                       f"we rejected, valuation check).{demo_tag}")
        deck.score_band(s)
    return pages
