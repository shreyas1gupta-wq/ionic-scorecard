# -*- coding: utf-8 -*-
"""allocation_house_view, current book vs house-view targets (over/under diverging bar) + stance table.
House-view allocation bands are advisory-owned (illustrative for the AZBY demo)."""
from slidekit import (NAVY, GOLD, INK, SLATE, SELL, SANS, SERIF, ML, UW, RX)
import charts as CH

# preferred display order for allocation buckets
_ORDER = ["Large", "Mid", "Small", "Foreign", "Gold", "Debt/Hybrid"]

LABELS = {
    "hni":    {"eyebrow": "Allocation vs house view",
               "title": "Book positioning against house-view allocation targets"},
    "std":    {"eyebrow": "Allocation vs house view",
               "title": "Where the book sits against our house-view targets"},
    "simple": {"eyebrow": "Where you have too much · and too little",
               "title": "Your mix against what we would target"},
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    hv = ctx["house_view"]; gap = hv["alloc_gap"]; stance = hv["stance"]

    s = deck.content(1, "Portfolio X-ray", L["eyebrow"], L["title"])

    # ---- over/under bar (left) ----
    cats = [k for k in _ORDER if k in gap] + [k for k in gap if k not in _ORDER]
    gaps = [gap[k] for k in cats]
    cpath = CH.over_under_bar(cats, gaps, "azby_alloc_gap")
    deck.pic(s, cpath, ML, 2.0, 6.7, 3.55, valign="top", halign="left")

    # ---- house-view stance table (right) ----
    tx = ML + 6.95; tw = RX - tx
    deck.txt(s, tx, 1.95, tw, 0.24,
             [("HOUSE-VIEW STANCE", SANS, 9, SLATE, True, False, 120)])
    rows = [[("b", dim), txt] for dim, txt in stance.items()]
    deck.table(s, tx, 2.28, tw, cols=[("Dimension", 0.42, "l"), ("Our stance", 0.58, "l")],
               rows=rows, rowh=0.56, fs=9, hfs=8, header=True, zebra=True, maxrows=6)

    # ---- one-line read (full width) ----
    lg = gap.get("Large"); fg = gap.get("Foreign"); gd = gap.get("Gold")
    if reg == "simple":
        read = ("Right now there is a lot in big Indian companies and very little in foreign "
                "shares and gold. When we reinvest, we plan to balance this out, with you.")
    elif reg == "hni":
        read = (f"Pronounced large-cap domestic tilt (+{lg:.1f} vs target); foreign ~{abs(fg):.0f}pts and "
                f"gold ~{abs(gd):.0f}pts light. Closing these gaps is planned at deployment "
                f"(transition framework, annexure), on your authorisation.")
    else:
        read = (f"The book leans heavily into large-cap domestic equity (+{lg:.1f} vs target), while "
                f"foreign equity is ~{abs(fg):.0f} points light and gold ~{abs(gd):.0f} points light. "
                "Closing these gaps is planned at deployment, on your authorisation.")
    deck.callout(s, ML, 5.75, UW, 0.82,
                 "WHAT IT MEANS" if reg != "simple" else "IN SHORT", read,
                 kind="note")

    deck.source(s, "House-view allocation bands are illustrative for this demo. "
                   "Gap = current book minus house-view target, in percentage points.")
    return 1
