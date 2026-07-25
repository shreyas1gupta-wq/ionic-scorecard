# -*- coding: utf-8 -*-
"""Annexure, Holdings detail: a compact, paginated table of ALL direct-equity holdings, scored.
~18 rows per slide; returns the page count (v8 #35-51, toggled)."""
import math
from slidekit import ML, UW


PER = 18


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    eq = list(ctx["equity"])
    asof = ctx["client"]["as_of"]
    pages = max(1, math.ceil(len(eq) / PER))

    cols = [("Holding", 0.20, "l"), ("Sector", 0.22, "l"), ("Wt %", 0.10, "r"),
            ("Ionic", 0.15, "l"), ("3Y", 0.09, "r"), ("1Y", 0.09, "r"), ("Call", 0.15, "c")]

    for p in range(pages):
        chunk = eq[p * PER:(p + 1) * PER]
        title = ("The full direct-equity book" if reg == "simple" else "The whole book, scored")
        if pages > 1:
            title += f"  (page {p + 1} of {pages})"
        s = deck.content(5, "Annexure", "All holdings, scored", title)
        deck.scope_tag(s, f"Direct equity only · as of {asof}")

        rows = []
        for e in chunk:
            rows.append([
                ("b", e["symbol"]),
                (e.get("sector") or "")[:20],
                f"{e['weight_pct']:.2f}",
                ("bar", e["ionic_score"]),
                f"{e['score_3y']:.0f}",
                f"{e['score_1y']:.0f}",
                ("pill", e["rec"]),
            ])
        deck.table(s, ML, 1.95, UW, cols, rows, rowh=0.24, fs=8.5, hfs=7.5)
        deck.score_band(s)
    return pages
