# -*- coding: utf-8 -*-
"""Cover slide."""
from slidekit import (NAVY, NT2, NT3, WHITE, GOLD, SERIF, SANS, ML, UW, RX, CW)
from pptx.enum.text import PP_ALIGN


def render(deck, ctx, tier):
    deck.folio += 1
    s = deck.slide(NAVY)
    c = ctx["client"]
    deck.rect(s, 0, 0, CW, 0.10, fill=GOLD)
    if deck.logo_path:
        deck.pic(s, deck.logo_path, ML, 0.55, 2.2, 0.42, halign="left")
    else:
        deck.txt(s, ML, 0.55, 4.0, 0.4, [("IONIC WEALTH", SANS, 15, WHITE, True, False, 80)])
    deck.txt(s, ML, 2.55, UW, 0.4, [("PORTFOLIO REVIEW", SANS, 13, NT2, True, False, 260)])
    deck.txt(s, ML, 3.02, UW, 0.9, [(c["name"], SANS, 44, WHITE, True)])
    deck.rule(s, ML, 4.05, 3.4, GOLD, 0.03)
    deck.txt(s, ML, 4.28, UW, 0.4, [(f"{c['account_type']}   ·   {c['profile']}   ·   {c['horizon']}",
                                     SERIF, 13, NT3, False, True)])
    deck.txt(s, ML, 6.55, RX - 3.4 - ML, 0.3, [("Co-founder in your journey of wealth creation", SERIF, 12, NT2, False, True)])
    deck.txt(s, RX - 3.0, 6.55, 3.0, 0.3, [(f"As of {c['as_of']}", SANS, 9, NT2, False)], align=PP_ALIGN.RIGHT)
    deck.txt(s, ML, 6.86, UW, 0.2, [("[ILLUSTRATIVE, synthetic demo client; not a real portfolio]",
                                     SANS, 7.5, NT2, False, True)])
    return 1
