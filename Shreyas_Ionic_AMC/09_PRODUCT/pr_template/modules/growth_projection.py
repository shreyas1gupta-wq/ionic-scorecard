# -*- coding: utf-8 -*-
"""Annexure, Growth projection: an illustrative lognormal cone for the portfolio value over the
mandate horizon, with a goal line (v8 #33, CH.projection_cone)."""
import charts as CH
from slidekit import ML, UW, RX


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    v0 = ctx["totals"]["grand_inr"]
    years = int(ctx.get("ips", {}).get("horizon_yrs") or 7)
    mu, sigma = 12, 14
    goal = round(v0 * 2.0)
    goals = [(years, f"Illustrative goal ~ Rs {goal / 1e7:.1f} Cr", goal)]
    png = CH.projection_cone(v0, years, mu, sigma, "annex_cone", goals=goals)

    title = ("An illustrative path for the portfolio over the horizon"
             if reg != "simple" else "Where this could grow over time")
    s = deck.content(5, "Annexure", "Growth projection", title)
    deck.pic(s, png, ML, 1.85, 8.0, 4.6, valign="top", halign="left")

    rx = ML + 8.15
    rw = RX - rx
    if reg == "simple":
        b1 = (f"Starting from ₹{v0 / 1e7:.2f} Cr, this shows a possible range over {years} years on an "
              f"assumed {mu}% average return. It is an illustration, not a promise.")
        b2 = ("Markets do not move in a straight line, the shaded band shows the good and bad cases "
              "around the middle line.")
    else:
        b1 = (f"Median path from ₹{v0 / 1e7:.2f} Cr at an assumed {mu}% p.a. return and {sigma}% "
              f"volatility over {years} years. The dashed line is an illustrative wealth goal.")
        b2 = ("Read the band, not the line: the shaded area is the 10th-to-90th-percentile range. "
              "Outcomes compound path-dependently and will differ from any single number.")
    deck.callout(s, rx, 1.95, rw, 2.15, "Assumptions", b1, "note")
    deck.callout(s, rx, 4.25, rw, 2.05, "Read the band", b2, "human")
    deck.source(s, "Illustrative projection on assumed return/volatility; not a forecast, guarantee, or "
                   "indication of future returns. Actual outcomes will differ.")
    return 1
