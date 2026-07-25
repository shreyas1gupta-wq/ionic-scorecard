# -*- coding: utf-8 -*-
"""Annexure, Opportunity set: an illustrative efficient frontier from long-run capital-market
assumptions, with the book's Today mix and a Proposed mix marked (v8 #30)."""
import charts as CH
from slidekit import SELL, HOLD, NAVY, ML, UW, RX

# matplotlib-safe hex mirrors of the house palette (RGBColor cannot cross into matplotlib)
SELL_HEX = "#E0402F"; NAVY_HEX = "#1B27A3"


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    title = ("Long-run risk and return, and where the book can move"
             if reg != "simple" else "How much return, for how much risk")
    s = deck.content(5, "Annexure", "Opportunity set", title)

    assets = ["Indian equity", "Foreign equity", "Debt", "Gold"]
    mu = [13, 11, 7, 8]
    sigma = [16, 15, 4, 14]
    corr = [[1.0, 0.60, 0.10, 0.20],
            [0.60, 1.0, 0.15, 0.25],
            [0.10, 0.15, 1.0, -0.05],
            [0.20, 0.25, -0.05, 1.0]]
    today = [0.80, 0.03, 0.12, 0.05]          # equity-heavy, thin foreign/gold (matches house-view gaps)
    illustrative = [0.60, 0.15, 0.15, 0.10]   # closes the foreign/gold gap toward the frontier
    # 'Illustrative', never 'Proposed' — no buy recommendation in this deck (Principal 2026-07-25)
    marks = [("Today", today, SELL_HEX), ("Illustrative", illustrative, NAVY_HEX)]
    png = CH.efficient_frontier(assets, mu, sigma, corr, marks, "annex_frontier")
    deck.pic(s, png, ML, 1.85, 7.5, 4.5, valign="top", halign="left")

    rx = ML + 7.75
    rw = RX - rx
    if reg == "simple":
        b1 = ("Each dot is a possible mix of the four assets. Higher up means more return; further "
              "right means more ups and downs. The gold dot is the best-balanced mix.")
        b2 = ("Your mix today (rust) leans almost entirely on Indian shares. The navy dot is one "
              "example of a more balanced mix, shown for comparison, not something we are "
              "asking you to buy.")
    else:
        b1 = ("Each dot is a feasible mix of the four assets; up is more expected return, right is more "
              "risk. The gold dot is the best risk-adjusted (max-Sharpe) mix on these assumptions.")
        b2 = ("The book today (rust) is concentrated in Indian equity with little foreign or gold. The "
              "navy marker is an illustrative diversified mix for discussion · it shows the direction "
              "the frontier points, it is not a recommendation.")
    deck.callout(s, rx, 1.95, rw, 1.85, "What this shows", b1, "note")
    deck.callout(s, rx, 4.00, rw, 2.05, "Today vs an illustrative mix", b2, "good")
    deck.source(s, "Illustrative long-run capital-market assumptions (expected return / risk, % p.a.): "
                   "Indian eq 13/16 · Foreign eq 11/15 · Debt 7/4 · Gold 8/14. Not a forecast, not a "
                   "recommendation.")
    return 1
