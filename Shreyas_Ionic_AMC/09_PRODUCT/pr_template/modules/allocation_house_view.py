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
    # a book with no IPS/allocation-target data yet has at most one placeholder gap sitting
    # at exactly 0 -- an over/under bar with nothing to show is dead ink, not a chart; skip it
    # and give the stance table the full width instead.
    has_real_gap = len(cats) >= 2 or any(v != 0 for v in gaps)
    if has_real_gap:
        cpath = CH.over_under_bar(cats, gaps, "azby_alloc_gap")
        deck.pic(s, cpath, ML, 2.0, 6.7, 3.55, valign="top", halign="left")
    else:
        deck.callout(s, ML, 2.0, 6.7, 3.55, "ALLOCATION TARGETS",
                     "No allocation targets are on file for this account yet — this is a first "
                     "review with no IPS agreed. Once one is in place, the book's mix will be "
                     "measured against it here.", kind="note")

    # ---- house-view stance table (right) ----
    tx = ML + 6.95; tw = RX - tx
    deck.txt(s, tx, 1.95, tw, 0.24,
             [("HOUSE-VIEW STANCE", SANS, 9, SLATE, True, False, 120)])
    rows = [[("b", dim), txt] for dim, txt in stance.items()]
    deck.table(s, tx, 2.28, tw, cols=[("Dimension", 0.42, "l"), ("Our stance", 0.58, "l")],
               rows=rows, rowh=0.56, fs=9, hfs=8, header=True, zebra=True, maxrows=6)

    # ---- one-line read (full width) ----
    # Built from the buckets this book ACTUALLY has. Keying on "Large" and "Foreign" meant a
    # statement-driven book, whose gaps are Equity, Debt/Hybrid and Gold, fell through to
    # "allocation targets aren't fully set for this account yet" printed directly beneath a chart
    # plotting three of them against published targets.
    _named = {"Debt/Hybrid": "debt and hybrid", "Gold": "gold", "Equity": "equity",
              "Large": "large-cap domestic equity", "Foreign": "foreign equity"}

    def _phrase(k, v):
        n = _named.get(k, k.lower())
        if abs(v) < 0.5:
            return f"{n} is on target"
        # SINGULAR AT ONE POINT. "gold is 1 points light" shipped on a client deck. This module
        # is retired (engine.py, FM #7) and is no longer built, but a retired module with a
        # grammar defect in it is a landmine for whoever resurrects it.
        _p = "point" if round(abs(v)) == 1 else "points"
        return f"{n} is {abs(v):.0f} {_p} {'over' if v > 0 else 'light'}"

    _ranked = sorted(((k, v) for k, v in gap.items()), key=lambda kv: -abs(kv[1]))
    if not _ranked:
        read = ("Allocation targets versus a house view aren't fully set for this account yet. "
                "Closing any gaps will follow once an IPS is agreed.")
    elif reg == "simple":
        read = ("Against what we would aim for, " +
                ", ".join(_phrase(k, v) for k, v in _ranked[:3]) +
                ". Any change here is planned with you, never done on our own.")
    else:
        read = ("Against the house view, " + ", ".join(_phrase(k, v) for k, v in _ranked[:3]) +
                ". Closing these gaps is planned at deployment, on your authorisation.")
    _alloc_note = (ctx.get("house_view") or {}).get("alloc_note")
    deck.callout(s, ML, 5.75, UW, 0.82,
                 "WHAT IT MEANS" if reg != "simple" else "IN SHORT", read,
                 kind="note")

    demo_tag = " Illustrative for the AZBY demo." if ctx.get("is_demo", False) else ""
    deck.source(s, f"House-view allocation bands.{demo_tag} "
                   "Gap = current book minus house-view target, in percentage points."
                   + (" " + _alloc_note if _alloc_note else ""))
    return 1
