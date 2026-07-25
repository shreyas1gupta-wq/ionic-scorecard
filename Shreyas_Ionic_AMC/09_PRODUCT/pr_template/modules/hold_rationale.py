# -*- coding: utf-8 -*-
"""hold_rationale (F3/F13), What stays, and why.
The biggest Holds grouped Core (high-conviction) vs Watch (hold, monitoring), each name paired with
its Ionic Score and a one-line read. A thesis-break rule footnote states what would flip a Hold.
score_band + scope_tag attach.
"""
from slidekit import (NAVY, INK, SLATE, HAIR, PANEL, WHITE, SELL, HOLD, AMBER, GOLD,
                      HOLDBG, NT2, SERIF, SANS, ML, RX, UW)
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

LABELS = {
    "hni":    {"title": "What stays, and why, core conviction versus watch",
               "core": "CORE, high conviction", "watch": "WATCH, held, monitoring",
               "break": "Thesis-break rule: any Hold is reviewed the moment its score falls below 40, "
                        "a balance-sheet gate trips, or the growth thesis we underwrote breaks."},
    "std":    {"title": "What stays, and why",
               "core": "CORE, high conviction", "watch": "WATCH, held, monitoring",
               "break": "What would change our mind: any Hold is reviewed if its score drops below 40, "
                        "a debt gate trips, or the growth we expected fails to show up."},
    "simple": {"title": "What we would keep, and why",
               "core": "STRONG KEEPS", "watch": "KEEP & WATCH",
               "break": "We would look again at any keep if its score falls below 40 or the reason we "
                        "held it stops being true."},
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


def _entry(deck, s, x, y, w, e, read_len):
    """One holding: name + score bar on line 1, one-line read on line 2."""
    deck.txt(s, x, y, w - 1.5, 0.24,
             [(e["name"], SANS, 10.5, INK, True), ("   " + f"{e['weight_pct']:.2f}%", SANS, 9, SLATE, False)],
             anchor=MSO_ANCHOR.MIDDLE)
    deck.score_bar(s, x + w - 1.30, y + 0.05, e.get("ionic_score"), w=0.75)
    deck.txt(s, x, y + 0.245, w, 0.22, [(_clip(e.get("analyst_read", ""), read_len), SERIF, 9, SLATE, False, True)])
    deck.rule(s, x, y + 0.475, w, HAIR, 0.006)


def _column(deck, s, x, y, w, title, accent, rows, read_len):
    deck.rect(s, x, y, 0.12, 0.20, fill=accent, round_=0.2)
    deck.txt(s, x + 0.20, y - 0.02, w - 0.2, 0.24, [(title, SANS, 10, accent, True, False, 40)],
             anchor=MSO_ANCHOR.MIDDLE)
    deck.txt(s, x, y + 0.02, w, 0.2, [(f"{len(rows)}", SANS, 10, SLATE, True)], align=PP_ALIGN.RIGHT)
    ey = y + 0.36
    for e in rows:
        _entry(deck, s, x, ey, w, e, read_len)
        ey += 0.55
    return ey


def render(deck, ctx, tier):
    reg = tier["register"]
    L = LABELS.get(reg, LABELS["std"])
    as_of = ctx["client"].get("as_of", "")
    holds = [e for e in ctx["equity"] if e["rec"] == "Hold"]
    core = sorted([e for e in holds if e.get("conviction") == "Core"], key=lambda e: -(e["weight_pct"] or 0))
    watch = sorted([e for e in holds if e.get("conviction") != "Core"], key=lambda e: -(e["weight_pct"] or 0))

    n_each = 4 if reg == "simple" else 6
    read_len = 60 if reg == "simple" else 68
    core_show, watch_show = core[:n_each], watch[:n_each]

    s = deck.content(2, "Equity", "What stays, and why", L["title"])
    deck.scope_tag(s, f"Direct equity only · as of {as_of}")

    lead = ("The keeps, split by how strongly we hold them. Each shows its score and a one-line read."
            if reg == "simple" else
            "Our Holds, grouped by conviction. Each name pairs its Ionic Score with a one-line read.")
    deck.txt(s, ML, 1.80, UW, 0.26, [(lead, SERIF, 10.5, SLATE, False, True)])

    gy = 2.24
    gap = 0.5
    colw = (UW - gap) / 2.0
    deck.vrule(s, ML + colw + gap / 2.0, gy, 3.6, HAIR, 0.008)
    _column(deck, s, ML, gy, colw, L["core"], HOLD, core_show, read_len)
    _column(deck, s, ML + colw + gap, gy, colw, L["watch"], SLATE, watch_show, read_len)

    extra = (len(core) - len(core_show)) + (len(watch) - len(watch_show))
    more_note = f"{extra} further Holds scored and read in the annexure · " if extra > 0 else ""

    # thesis-break footnote
    deck.callout(s, ML, 5.82, UW, 0.78, "What would flip a Hold", L["break"], kind="note")

    deck.source(s, more_note + "Conviction tier from Ionic Score × position size · reads are the analyst summary · "
                   "illustrative synthetic book.")
    deck.score_band(s)
    return 1
