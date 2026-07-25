# -*- coding: utf-8 -*-
"""book_scored (F13), The whole book, scored, with the analyst read.
Distribution KPI (Sell / Trim / Hold counts from ctx totals; no book-level weighted score, frozen rule)
+ a table of the largest positions (Name | Wt | Score-bar | Rec-pill | one-line analyst read),
maxrows-capped with 'and N more in annexure'. score_band + scope_tag both attach here.
"""
from slidekit import (NAVY, INK, SLATE, HAIR, PANEL, WHITE, SELL, HOLD, AMBER,
                      SELLBG, HOLDBG, AMBERBG, NT2, SERIF, SANS, ML, RX, UW)
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

MAXROWS = 11   # 3.10 + header 0.33 + 11x0.26 = 6.29, clear of the 6.66 source zone

LABELS = {
    "hni":    {"title": "The whole book, scored, with the analyst read",
               "lead": "Every direct-equity holding carries an Ionic Score and a one-line analyst read; "
                       "the largest positions are shown, the rest sit in the annexure."},
    "std":    {"title": "The whole book, scored, with the analyst read",
               "lead": "Every stock you hold has a score and a one-line read. The biggest positions "
                       "are shown here; the full list is in the annexure."},
    "simple": {"title": "Your shares, scored",
               "lead": "Each holding gets a score out of 100 and a plain one-line read. Your biggest "
                       "holdings are shown here."},
}


def _clip(txt, n):
    txt = (txt or "").strip()
    if len(txt) <= n:
        return txt
    cut = txt[:n]
    sp = cut.rfind(" ")
    if sp > n * 0.6:
        cut = cut[:sp]
    return cut.rstrip(" ,.;:") + "…"


def _dist_band(deck, s, tot, y):
    """Compact distribution 'KPI' band: Sell / Trim / Hold / total, coloured."""
    cells = [(str(tot["n_sell"]), "SELL", SELL),
             (str(tot["n_trim"]), "TRIM", AMBER),
             (str(tot["n_hold"]), "HOLD", HOLD),
             (str(tot["n_stocks"]), "HOLDINGS", INK)]
    cw = UW / len(cells)
    for i, (val, lab, col) in enumerate(cells):
        cx = ML + i * cw
        deck.txt(s, cx, y, cw - 0.2, 0.42, [(val, SANS, 27, col, False)], anchor=MSO_ANCHOR.MIDDLE)
        deck.txt(s, cx, y + 0.44, cw - 0.2, 0.2,
                 [(lab, SANS, 8.5, SLATE, True, False, 150)])
        if i:
            deck.vrule(s, cx - 0.02, y + 0.04, 0.56, HAIR, 0.008)


def render(deck, ctx, tier):
    reg = tier["register"]
    L = LABELS.get(reg, LABELS["std"])
    eq = ctx["equity"]; tot = ctx["totals"]
    as_of = ctx["client"].get("as_of", "")
    s = deck.content(2, "Equity", "The book, scored", L["title"])
    deck.scope_tag(s, f"Direct equity only · as of {as_of}")

    deck.txt(s, ML, 1.78, UW, 0.26, [(L["lead"], SERIF, 10.5, SLATE, False, True)])

    _dist_band(deck, s, tot, 2.12)

    # override honesty line: Holds sitting below the Sell line, kept on analyst conviction
    overrides = sum(1 for e in eq if e["rec"] == "Hold" and (e.get("ionic_score") or 100) < 40)
    if overrides:
        note = (f"{overrides} name(s) score below 40 yet are held on analyst conviction, "
                "the score flags, the desk decides.")
        deck.txt(s, ML, 2.80, UW, 0.24,
                 [("ANALYST OVERRIDE   ", SANS, 8, AMBER, True, False, 40),
                  (note, SERIF, 9.5, INK, False, True)], anchor=MSO_ANCHOR.MIDDLE)

    # table — largest positions first
    rows_src = sorted(eq, key=lambda e: -(e.get("weight_pct") or 0))
    cols = [("Holding", 0.24, "l"), ("Wt %", 0.08, "r"), ("Ionic Score", 0.17, "l"),
            ("Call", 0.11, "c"), ("Analyst read", 0.40, "l")]
    rows = []
    for e in rows_src[:MAXROWS]:
        rows.append([
            ("b", e["name"]),
            ("c", f"{e['weight_pct']:.2f}", INK),
            ("bar", e.get("ionic_score")),
            ("pill", e["rec"], e["rec"]),
            _clip(e.get("analyst_read", ""), 44),
        ])
    ty = deck.table(s, ML, 3.10, UW, cols, rows, rowh=0.26, fs=9, hfs=8, maxrows=MAXROWS)

    more = len(eq) - min(MAXROWS, len(eq))
    if more > 0:
        deck.txt(s, ML, ty + 0.04, UW, 0.22,
                 [(f"and {more} more holdings, fully scored in the annexure.",
                   SERIF, 9, SLATE, False, True)])

    deck.source(s, "Ionic Score: proprietary two-horizon composite with safety gates, reviewed by the desk · "
                   "reads are the analyst summary · illustrative synthetic book.")
    deck.score_band(s)
    return 1
