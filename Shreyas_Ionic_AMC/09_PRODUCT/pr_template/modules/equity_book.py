# -*- coding: utf-8 -*-
"""equity_book, the direct-equity book at a glance.
Brief overview line + a weight-vs-Ionic-Score bubble (each dot a holding, size = rupee value,
colour = Sell / Trim / Hold), with the Sell threshold shaded. score_band + scope_tag attach.
"""
import charts as CH
from slidekit import (NAVY, INK, SLATE, HAIR, PANEL, SELL, HOLD, AMBER, GOLD,
                      SERIF, SANS, ML, RX, UW)
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

REC_HEX = {"Sell": "#E0402F", "Trim": "#F2A93C", "Hold": "#1E9E6A"}

LABELS = {
    "hni":    {"title": "The equity book at a glance, weight against conviction",
               "lead": ("Each dot is a holding: how much of the book it is (across) against its Ionic "
                        "Score (up). Dot size is rupee value. Anything in the shaded band scores below "
                        "the Sell line; the far right, low-scoring dots are the concentration to watch.")},
    "std":    {"title": "The equity book at a glance",
               "lead": ("Each dot is a holding, its weight in the book (across) against its Ionic Score "
                        "(up), sized by value. Dots in the shaded band score below the Sell line.")},
    "simple": {"title": "Your shares, all on one picture",
               "lead": ("Every dot is one holding. Further right = a bigger part of your money. Higher "
                        "up = a stronger score. Anything in the red band scores low.")},
}


def render(deck, ctx, tier):
    reg = tier["register"]
    L = LABELS.get(reg, LABELS["std"])
    eq = ctx["equity"]
    as_of = ctx["client"].get("as_of", "")
    s = deck.content(2, "Equity", "The book at a glance", L["title"])
    deck.scope_tag(s, f"Direct equity only · as of {as_of}")

    deck.txt(s, ML, 1.80, UW, 0.5, [(L["lead"], SERIF, 10.5, SLATE, False, True)], ls=1.05)

    xs = [e["weight_pct"] for e in eq]
    ys = [(e.get("ionic_score") if e.get("ionic_score") is not None else 50) for e in eq]
    sizes = [e.get("value_inr", 0) for e in eq]
    colors = [REC_HEX.get(e["rec"], "#8C95DE") for e in eq]
    labels = [e["symbol"] for e in eq]
    png = CH.bubble(xs, ys, sizes, colors, "equity_book_bubble", labels=labels, threshold=40,
                    figsize=(11.0, 4.7), xlabel="Weight in book (%)", ylabel="Ionic Score (0–100)")
    deck.pic(s, png, ML, 2.45, UW, 3.55, valign="top")

    # legend — only the calls actually present in the book
    ly = 6.14
    items = [(n, c) for n, c in (("Sell", SELL), ("Trim", AMBER), ("Hold", HOLD))
             if any(e["rec"] == n for e in eq)]
    lx = ML
    for name, col in items:
        deck.oval(s, lx, ly + 0.03, 0.13, col)
        deck.txt(s, lx + 0.20, ly - 0.02, 1.0, 0.24, [(name, SANS, 9.5, INK, True)],
                 anchor=MSO_ANCHOR.MIDDLE)
        lx += 1.05
    deck.txt(s, lx + 0.15, ly - 0.02, UW - (lx - ML) - 0.2, 0.24,
             [("dot size = rupee value held · gold line = Sell threshold (40)",
               SERIF, 9, SLATE, False, True)], anchor=MSO_ANCHOR.MIDDLE)

    deck.source(s, "Weight = share of direct-equity book · Ionic Score post gate/penalty/boost, "
                   "forward-growth adjusted · illustrative synthetic book.")
    deck.score_band(s)
    return 1
