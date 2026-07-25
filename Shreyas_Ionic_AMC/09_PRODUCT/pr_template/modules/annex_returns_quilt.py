# -*- coding: utf-8 -*-
"""Annexure A1 - asset-class returns quilt: annual returns 2017-2026 across five asset
classes, each cell coloured by within-year rank. The humility chart: no asset wins every year."""
import chart_ext_a as CA
from slidekit import ML, UW

YEARS = list(range(2017, 2027))
ASSETS = ["Indian equity", "Foreign equity", "Gold", "Debt", "Cash"]
RETS = [
    [30,  5, 13, 16, 26,  6, 21, 10,  8, 11],   # Indian equity
    [18,  6, 32, 18, 32, -6, 19, 30, 12,  4],   # Foreign equity (INR)
    [ 5,  8, 23, 28, -4, 14, 15, 21, 28,  9],   # Gold (INR)
    [ 6,  6, 10, 12,  3,  3,  7,  9,  8,  4],   # Debt
    [ 6,  7,  6,  4,  3,  5,  7,  7,  6,  3],   # Cash
]

LABELS = {
    "hni":    ("Ten years, five assets · the winner rotates",
               "Annual returns ranked within each year, 2017 to 2026"),
    "std":    ("No asset class wins every year",
               "Ten years of annual returns, best to worst within each year"),
    "simple": ("No single winner, any year",
               "How the five building blocks took turns on top"),
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(5, "Annexure", eyebrow, title)
    deck.scope_tag(s, "[ILLUSTRATIVE] Asset-class annual returns in INR, 2017-2026 YTD · "
                      "synthetic, directionally representative · not a performance record")

    png = CA.returns_quilt(YEARS, ASSETS, RETS, "axa_quilt")
    deck.pic(s, png, ML, 1.85, UW, 3.55, valign="top")

    if reg == "simple":
        body = ("The best asset changes almost every year. Gold, foreign shares and Indian shares "
                "each took the top spot at different times, and in 2018 plain cash beat Indian "
                "shares. That is why the money is spread across all five and rebalanced, instead "
                "of chasing last year's winner.")
    else:
        body = ("Gold led four of these ten years, foreign equity three, Indian equity three; in "
                "2018 even cash beat Indian equity. Use this page when one asset has just had a "
                "hot run: the leader rotates, so the plan is the rebalanced allocation across all "
                "five, never last year's winner.")
    deck.callout(s, ML, 5.52, UW, 1.0, "The humility chart", body, kind="human")

    deck.source(s, "Illustrative synthetic annual returns in INR; asset proxies: Nifty 50 TRI, "
                   "S&P 500 in INR, domestic gold price, short-duration debt, liquid funds. "
                   "Directionally representative, not a performance record. [ILLUSTRATIVE]")
    return 1
