# -*- coding: utf-8 -*-
"""book_scored (F13), The whole book, scored, with the analyst read.
Distribution KPI (Sell / Trim / Hold counts from ctx totals; no book-level weighted score, frozen rule)
+ a table of the largest positions (Name | Wt | Score-bar | Rec-pill | one-line analyst read),
maxrows-capped with 'and N more in annexure'. score_band + scope_tag both attach here.
"""
from slidekit import (NAVY, INK, SLATE, HAIR, PANEL, WHITE, SELL, HOLD, AMBER,
                      SELLBG, HOLDBG, AMBERBG, NT2, SERIF, SANS, ML, RX, UW, clip_clause)
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

MAXROWS = 11

LABELS = {
    "hni":    {"title": "The largest positions, with the analyst's one-line read"},
    "std":    {"title": "The largest positions, with the analyst's one-line read"},
    "simple": {"title": "Your biggest holdings, each with a score and a plain read"},
}


def _dist_band(deck, s, tot, y):
    """Compact distribution 'KPI' band. Zero-count calls are dropped — a '0 TRIM'
    tile is dead ink (declutter pass, 2026-07-25)."""
    cells = [(str(tot["n_sell"]), "SELL", SELL),
             (str(tot["n_trim"]), "TRIM", AMBER),
             (str(tot["n_hold"]), "HOLD", HOLD),
             (str(tot["n_stocks"]), "HOLDINGS", INK)]
    cells = [c for c in cells if c[0] != "0" or c[1] in ("SELL", "HOLDINGS")]
    # content-sized tiles (v7 stat-strip rule) — 3 numbers spread across the full
    # width read as gaps, not as a band
    cw = min(UW / len(cells), 2.35)
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

    _dist_band(deck, s, tot, 1.95)

    # override honesty line: Holds sitting below the Sell line, kept on analyst conviction
    overrides = sum(1 for e in eq if e["rec"] == "Hold" and (e.get("ionic_score") or 100) < 40)
    if overrides:
        note = (f"{overrides} name(s) score below 40 yet are held on analyst conviction, "
                "the score flags, the desk decides.")
        deck.txt(s, ML, 2.66, UW, 0.24,
                 [("ANALYST OVERRIDE   ", SANS, 8, AMBER, True, False, 40),
                  (note, SERIF, 9.5, INK, False, True)], anchor=MSO_ANCHOR.MIDDLE)

    # table — largest positions first; the read column gets the width it needs to say
    # something complete (clause-aware clip, never a broken mid-phrase ellipsis)
    rows_src = sorted(eq, key=lambda e: -(e.get("weight_pct") or 0))
    cols = [("Holding", 0.22, "l"), ("Wt %", 0.07, "r"), ("Ionic Score", 0.15, "l"),
            ("Call", 0.10, "c"), ("Analyst read", 0.46, "l")]
    ROWH = 0.28
    rows = []
    for e in rows_src[:MAXROWS]:
        rows.append([
            ("b", e["name"]),
            ("c", f"{e['weight_pct']:.1f}", INK),
            ("bar", e.get("ionic_score")),
            ("pill", e["rec"], e["rec"]),
            clip_clause(e.get("analyst_read", ""), 58),
        ])
    ty = deck.table(s, ML, 2.98, UW, cols, rows, rowh=ROWH, fs=9, hfs=8, maxrows=MAXROWS)

    # each row clicks through to the name's rationale page in the annexure (resolved at save)
    deck.anchor("tbl:book", s, prio=5)
    linked = ("sell_cards" in tier.get("optional_on", set())
              or "holdings_detail" in tier.get("optional_on", set()))
    ry = 2.98 + 0.33
    for e in rows_src[:MAXROWS]:
        deck.hotspot(s, ML, ry - 0.02, UW, ROWH, f"stock:{e['symbol']}")
        ry += ROWH

    more = len(eq) - min(MAXROWS, len(eq))
    extra = " Rows link to each name's page there." if (linked and more > 0) else ""
    demo_tag = " Illustrative synthetic book." if ctx.get("is_demo", False) else ""
    deck.source(s, (f"All {len(eq)} holdings are scored; the remaining {more} sit in the annexure.{extra} " if more > 0 else "")
                   + "Ionic Score: two-horizon composite with safety gates, reviewed by the desk."
                   + demo_tag)
    deck.score_band(s)
    return 1
