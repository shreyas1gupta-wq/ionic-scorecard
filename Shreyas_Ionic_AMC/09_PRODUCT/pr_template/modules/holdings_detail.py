# -*- coding: utf-8 -*-
"""Annexure, Holdings detail: a compact, paginated table of ALL direct-equity holdings, scored.
~18 rows per slide; returns the page count (v8 #35-51, toggled)."""
import math
from slidekit import ML, UW


PER = 18

# AMFI sector names run long; abbreviate to words, never chop mid-word ('Information Technolo')
_SECTOR = {"Information Technology": "IT", "Fast Moving Consumer Goods": "FMCG",
           "Oil Gas & Consumable Fuels": "Oil & Gas", "Automobile And Auto Components": "Auto & Comp.",
           "Construction Materials": "Cement", "Telecommunication": "Telecom",
           "Metals & Mining": "Metals & Mining", "Financial Services": "Financials",
           "Consumer Durables": "Cons. Durables", "Healthcare": "Healthcare",
           "Capital Goods": "Capital Goods", "Consumer Services": "Cons. Services"}


def _sector(sec):
    sec = (sec or "").strip()
    if sec in _SECTOR:
        return _SECTOR[sec]
    if len(sec) <= 20:
        return sec
    words = sec.split(" ")
    while len(words) > 1 and len(" ".join(words)) > 20:
        words.pop()
    return " ".join(words)


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    # one sort across ALL holdings — late-added names were appended after the original
    # list and broke the descending order across pages (CEO sweep 2026-07-26)
    eq = sorted(ctx["equity"], key=lambda e: -e["weight_pct"])
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
                _sector(e.get("sector")),
                f"{e['weight_pct']:.2f}",
                ("bar", e["ionic_score"]),
                f"{e['score_3y']:.0f}",
                f"{e['score_1y']:.0f}",
                ("pill", e["rec"]),
            ])
        deck.table(s, ML, 1.95, UW, cols, rows, rowh=0.24, fs=8.5, hfs=7.5)
        # fallback jump target for every name; rows with a richer card elsewhere click through
        ry = 1.95 + 0.33
        for e in chunk:
            deck.anchor(f"stock:{e['symbol']}", s, prio=0)
            deck.hotspot(s, ML, ry - 0.02, UW, 0.24, f"stock:{e['symbol']}")
            ry += 0.24
        deck.score_band(s)
    return pages
