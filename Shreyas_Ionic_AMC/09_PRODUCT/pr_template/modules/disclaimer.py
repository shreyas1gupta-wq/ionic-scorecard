# -*- coding: utf-8 -*-
"""Disclaimer, always on, tier-exempt. Closes with the v7 colophon card (p.56 device):
centered wordmark + gold rule + confidentiality line, so the deck ends designed, not blank."""
from pptx.enum.text import PP_ALIGN
from slidekit import NAVY, NT3, GOLD, WHITE, SERIF, SANS, ML, UW, CW

TEXT = ("This document is a review of existing holdings prepared for the named client under a "
        "Non-Discretionary Portfolio Management mandate. Recommendations are Sell / Trim / Hold on "
        "current positions only and are not a solicitation or an offer to buy any security. Nothing "
        "is executed until the client authorises it. The Ionic Score is a quantitative input reviewed "
        "by the Portfolio Review team; it is not a guarantee of future performance. Tax characterisations "
        "are indicative · confirm with the client's tax adviser before dealing. Mutual-fund evaluation "
        "uses Direct-plan NAV against total-return benchmarks, point-in-time. Past performance is not "
        "indicative of future results. This is a synthetic demonstration document; the ABXY Family is "
        "fictional and no content constitutes advice on a real portfolio.")


def render(deck, ctx, tier):
    deck.folio += 1
    s = deck.slide(NAVY)
    deck.txt(s, ML, 0.7, UW, 0.5, [("Disclaimer & basis of preparation", SANS, 20, WHITE, True)])
    deck.rule(s, ML, 1.25, 3.0, WHITE, 0.02)
    deck.txt(s, ML, 1.7, UW, 2.6, [(TEXT, SERIF, 11.5, NT3, False)], ls=1.25)

    # closing colophon — the only centered lockup in the deck (v7 p.56)
    deck.txt(s, ML, 4.95, UW, 0.5, [("IONIC WEALTH", SANS, 24, WHITE, True, False, 300)],
             align=PP_ALIGN.CENTER)
    deck.rule(s, CW / 2 - 0.55, 5.58, 1.1, GOLD, 0.02)
    deck.txt(s, ML, 5.78, UW, 0.3,
             [("Private & Confidential  ·  Prepared exclusively for the named client",
               SANS, 9.5, NT3, False, False, 60)], align=PP_ALIGN.CENTER)

    deck.txt(s, ML, 6.9, UW, 0.3, [("Ionic Wealth by Angel One  ·  Portfolio Review  ·  Private & Confidential",
                                    SANS, 8, NT3, False)])
    return 1
