# -*- coding: utf-8 -*-
"""Cover slide — v7 grammar: left text column with two-tone headline + PREPARED FOR
block; right half carries the generative 'compounding curves' art panel (no photo,
no empty navy field)."""
from slidekit import (NAVY, NT2, NT3, WHITE, GOLD, SERIF, SANS, ML, UW, RX, CW)
from pptx.enum.text import PP_ALIGN
import art


def render(deck, ctx, tier):
    deck.folio += 1
    s = deck.slide(NAVY)
    c = ctx["client"]

    # right half: art panel, edge-to-edge under the gold top bar
    deck.pic(s, art.flow_art("cover_art", seed=11), 8.03, 0.10, 5.31, 7.40,
             valign="top", halign="right")
    deck.rect(s, 0, 0, CW, 0.10, fill=GOLD)

    if deck.logo_path:
        deck.pic(s, deck.logo_path, ML, 0.55, 2.2, 0.42, halign="left")
    else:
        deck.txt(s, ML, 0.55, 4.0, 0.4, [("IONIC WEALTH", SANS, 15, WHITE, True, False, 80)])

    # two-tone headline (v7 cover device), then the client block
    deck.txt(s, ML, 2.30, 7.0, 0.85, [("Portfolio ", SANS, 40, WHITE, True),
                                      ("Review", SANS, 40, GOLD, True)])
    deck.txt(s, ML, 3.42, 7.0, 0.3, [("PREPARED FOR", SANS, 10, NT2, True, False, 260)])
    deck.txt(s, ML, 3.74, 7.0, 0.65, [(c["name"], SANS, 28, WHITE, True)])
    deck.rule(s, ML, 4.50, 3.4, GOLD, 0.03)
    deck.txt(s, ML, 4.72, 7.0, 0.4, [(f"{c['account_type']}   ·   {c['profile']}   ·   {c['horizon']}",
                                     SERIF, 12.5, NT3, False, True)])

    deck.txt(s, ML, 6.45, 7.0, 0.3, [("Co-founder in your journey of wealth creation",
                                      SERIF, 12, NT2, False, True)])
    deck.txt(s, ML, 6.80, 7.0, 0.25, [(f"As of {c['as_of']}   ·   ", SANS, 8.5, NT2, False),
                                      ("[ILLUSTRATIVE, synthetic demo client; not a real portfolio]",
                                       SANS, 7.5, NT2, False, True)])
    return 1
