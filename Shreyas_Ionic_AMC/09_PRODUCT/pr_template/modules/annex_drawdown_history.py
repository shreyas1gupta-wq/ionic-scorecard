# -*- coding: utf-8 -*-
"""Annexure B, education slide: India equity drawdown history. Five peak-to-trough episodes with
approximate depths and recovery times [approx, ILLUSTRATIVE], and the 'drawdowns are the admission
price' framing. No client numbers on this slide; it sets expectations for the mandate."""
import chart_ext_b as CB
from slidekit import ML, UW, RX, SERIF, SLATE

LABELS = {
    "hni":    ("Living with drawdowns", "Every equity decade includes falls like these"),
    "std":    ("Living with drawdowns", "Every equity decade includes falls like these"),
    "simple": ("Living with drawdowns", "Big falls happen, and they have always passed"),
}

# (episode, approx peak-to-trough %, approx months trough back to prior peak) [ILLUSTRATIVE]
EPISODES = [
    ("2008 global crisis", -60, 20),
    ("2011 taper / EU stress", -28, 19),
    ("2013 taper tantrum", -15, 7),
    ("2020 Covid crash", -38, 9),
    ("2022 rate reset", -17, 16),
]


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    horizon = ctx.get("client", {}).get("horizon", "long term")
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(5, "Annexure", eyebrow, title)
    deck.scope_tag(s, "India large-cap equity, approximate historical episodes [ILLUSTRATIVE]; "
                      "an education slide, no client positions shown")

    png = CB.drawdown_bars(EPISODES, "annexb_ddhist")
    deck.pic(s, png, ML, 2.0, UW, 3.35, valign="top", halign="center")

    worst = min(e[1] for e in EPISODES)
    if reg == "simple":
        body = (f"Over the last 20 years the Indian market has fallen hard several times, once by "
                f"about {abs(worst):.0f}%. Each time it came back, though the wait ran from months to "
                f"a couple of years. The plan expects falls like these; the only investor who loses "
                f"permanently is the one forced to sell at the bottom.")
    else:
        body = (f"Drawdowns are the admission price of equity returns: the same market that compounds "
                f"wealth over a {horizon.lower()} horizon has fallen {abs(worst):.0f}% peak-to-trough "
                f"within it. Every fall above looked permanent in the middle of it, and each recovery "
                f"ran on its own clock, from months to a couple of years. The mandate's cash buffer and "
                f"staged deployment exist precisely so this portfolio is never a forced seller in the "
                f"trough, which is the only way a temporary fall becomes a permanent loss.")
    deck.callout(s, ML, 5.5, UW, 1.05, "The admission price", body, kind="human")

    deck.source(s, "Peak-to-trough depths and trough-to-recovery months are approximate, rounded "
                   "episode markers [ILLUSTRATIVE]; verify against exchange index data before any "
                   "external use. Past falls and recoveries do not guarantee future ones.")
    return 1
