# -*- coding: utf-8 -*-
"""Annexure, Quality vs price: every direct-equity holding mapped on quality (ROE) against
valuation (P/E), coloured by call, sized by weight (v8 #31, CH.value_map)."""
import charts as CH
from pptx.enum.text import MSO_ANCHOR
from slidekit import INK, SLATE, HOLD, GOLD, SELL, SANS, ML, UW, RX

SELL_HEX = "#E0402F"; HOLD_HEX = "#1E9E6A"; GOLD_HEX = "#F2A93C"


def _col(rec):
    return SELL_HEX if rec == "Sell" else (GOLD_HEX if rec == "Trim" else HOLD_HEX)


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    eq = ctx["equity"]
    asof = ctx["client"]["as_of"]
    rows = [e for e in eq if e.get("pe") is not None and e.get("roe") is not None and e["roe"] != 0]

    title = ("Every holding on quality against valuation"
             if reg != "simple" else "Good businesses, and what you pay for them")
    s = deck.content(5, "Annexure", "Quality vs price", title)
    deck.scope_tag(s, f"Direct equity only · as of {asof}")

    pe = [e["pe"] for e in rows]
    roe = [e["roe"] for e in rows]
    sizes = [e["value_inr"] for e in rows]
    colors = [_col(e["rec"]) for e in rows]
    labels = [e["symbol"] for e in rows]
    png = CH.value_map(pe, roe, sizes, colors, labels, "annex_valuemap")
    deck.pic(s, png, ML, 1.95, 7.6, 4.35, valign="top", halign="left")

    rx = ML + 7.85
    rw = RX - rx
    if reg == "simple":
        body = ("Further right = a pricier share (higher P/E). Higher up = a better-quality business "
                "(higher return on equity). Bigger bubble = bigger position. Top-left is best.")
    else:
        body = ("Right = pricier (higher P/E). Up = higher quality (higher ROE). Bubble size = position "
                "size in the book. The sweet spot is top-left · quality you are not overpaying for.")
    deck.callout(s, rx, 2.05, rw, 1.95, "How to read it", body, "note")

    ly = 4.25
    deck.txt(s, rx, ly - 0.28, rw, 0.22, [("THE CALL", SANS, 8, SLATE, True, False, 120)])
    for i, (lab, c) in enumerate([("Hold", HOLD), ("Trim", GOLD), ("Sell", SELL)]):
        yy = ly + i * 0.34
        deck.oval(s, rx, yy, 0.17, c)
        deck.txt(s, rx + 0.28, yy - 0.03, rw - 0.3, 0.24,
                 [(lab, SANS, 10.5, INK, False)], anchor=MSO_ANCHOR.MIDDLE)

    deck.source(s, f"{len(rows)} of {len(eq)} holdings shown (names with a reported P/E and ROE). "
                   f"Bubble colour = current call; dashed lines = book medians.")
    return 1
