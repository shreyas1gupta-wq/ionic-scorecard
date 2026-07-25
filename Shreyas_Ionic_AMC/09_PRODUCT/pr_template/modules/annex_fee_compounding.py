# -*- coding: utf-8 -*-
"""Annexure A9 - fee compounding over 20 years: the same gross return at 0.4% vs 1.7% all-in
fees, gap shaded gold with the rupee difference labelled. Extends the Cost slide."""
import chart_ext_a as CA
from slidekit import ML, RX

GROSS, LO, HI, YRS = 12.0, 0.4, 1.7, 20

LABELS = {
    "hni":    ("The same return at two price tags",
               "20-year projection at 0.4% vs 1.7% all-in fees"),
    "std":    ("What fees quietly compound into",
               "The same portfolio, twenty years, two fee levels"),
    "simple": ("Why the fee difference matters",
               "Small yearly costs become a large gap over time"),
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    as_of = ctx["client"]["as_of"]
    eyebrow, title = LABELS.get(reg, LABELS["std"])

    v0_cr = ctx["totals"]["grand_inr"] / 1e7
    lo_end = v0_cr * (1 + (GROSS - LO) / 100.0) ** YRS
    hi_end = v0_cr * (1 + (GROSS - HI) / 100.0) ** YRS
    gap = lo_end - hi_end
    cost_bps = ctx["cost"]["total_bps"]

    s = deck.content(5, "Annexure", eyebrow, title)
    deck.scope_tag(s, f"[ILLUSTRATIVE] Whole book, ₹{v0_cr:.1f} Cr start · constant {GROSS:.0f}% "
                      f"gross return, fees the only difference · as of {as_of}")

    png = CA.fee_gap_lines(v0_cr, YRS, GROSS, LO, HI, "axa_feegap",
                           lo_label=f"{LO}% all-in", hi_label=f"{HI}% all-in")
    deck.pic(s, png, ML, 1.9, 7.2, 4.4, valign="top")

    tx = 8.35; tw = RX - tx
    body1 = (f"Both lines earn the same {GROSS:.0f}% gross. The only difference is the all-in "
             f"cost: {LO}% (Direct plans plus a flat advisory fee) against {HI}% (Regular plans "
             f"plus distribution and PMS-style layers). After {YRS} years the gap is about "
             f"₹{gap:.1f} Cr, near {gap / lo_end * 100:.0f}% of the better outcome.")
    deck.callout(s, tx, 1.95, tw, 2.25, "Same return, different price", body1, kind="note")

    body2 = (f"The Cost of Ownership slide prices this book's drag at {cost_bps} bps today; this "
             f"page is that same number left running for {YRS} years. Your review team tracks the "
             f"live all-in fee line so the gap stays visible after this review. Use it whenever a "
             f"fee difference is dismissed as small.")
    deck.callout(s, tx, 4.35, tw, 2.15, "Ties to the Cost slide", body2, kind="human")

    deck.source(s, f"Projection at a constant {GROSS:.0f}% gross return; all-in fee scenarios of "
                   f"{LO}% and {HI}% p.a.; no market volatility modelled. An illustration of "
                   f"compounding, not a forecast. [ILLUSTRATIVE]")
    return 1
