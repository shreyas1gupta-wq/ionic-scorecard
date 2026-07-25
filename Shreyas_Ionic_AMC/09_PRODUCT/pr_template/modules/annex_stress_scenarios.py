# -*- coding: utf-8 -*-
"""Annexure A4 - scenario replay: estimated drawdown of four historical crisis windows on
today's mix vs the proposed post-deployment mix. The deployment plan argued in risk terms."""
import chart_ext_a as CA
from slidekit import ML, RX

SCN = ["GFC 2008", "Taper 2013", "Covid 2020", "Hikes 2022"]
TODAY = [-48, -11, -34, -16]
PROP = [-38, -8, -26, -12]

LABELS = {
    "hni":    ("Four crises, replayed on this book",
               "Estimated drawdown: today's mix vs the proposed mix"),
    "std":    ("How this book would have handled past crises",
               "Estimated fall in four historical stress windows, before and after the plan"),
    "simple": ("If bad markets return",
               "How much less the proposed mix would have fallen"),
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    as_of = ctx["client"]["as_of"]
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    worst_gain = PROP[0] - TODAY[0]
    other = [PROP[i] - TODAY[i] for i in range(1, len(SCN))]

    s = deck.content(5, "Annexure", eyebrow, title)
    deck.scope_tag(s, f"[ILLUSTRATIVE] Scenario replay on synthetic weights · today's mix vs "
                      f"proposed post-deployment mix · as of {as_of}")

    png = CA.scenario_replay(SCN, TODAY, PROP, "axa_stress")
    deck.pic(s, png, ML, 1.9, 7.0, 4.4, valign="top")

    tx = 8.15; tw = RX - tx
    body1 = ("Each pair replays that window's asset-class moves through today's mix and through "
             "the proposed mix (more foreign equity, gold and staged cash). These are estimates "
             "on synthetic weights; wide error bars apply.")
    deck.callout(s, tx, 1.95, tw, 1.9, "How these are estimated", body1, kind="note")

    body2 = (f"The proposed mix would have cut the worst window (GFC 2008) by about "
             f"{worst_gain:+.0f} points and the others by {min(other):.0f} to {max(other):.0f} "
             f"points, while giving up little in calm markets. Use this page when the deployment "
             f"plan needs a reason beyond return: it is bought protection, funded by the Sell "
             f"list.")
    deck.callout(s, tx, 4.05, tw, 2.25, "The deployment plan, in risk terms", body2, kind="human")

    deck.source(s, "Scenario drawdowns are illustrative estimates: historical asset-class "
                   "peak-to-trough moves applied to synthetic current and proposed allocations; "
                   "no forecast implied. [ILLUSTRATIVE]")
    return 1
