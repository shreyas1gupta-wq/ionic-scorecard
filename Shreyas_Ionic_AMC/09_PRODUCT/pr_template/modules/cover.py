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

    # text lockup on navy — the white-box logo PNG reads as a pasted sticker on the
    # dark cover (Principal 2026-07-25); content slides (white bg) keep the real logo
    deck.txt(s, ML, 0.52, 5.0, 0.4, [("IONIC ", SANS, 17, WHITE, True, False, 100),
                                     ("WEALTH", SANS, 17, NT3, False, False, 100)])
    deck.txt(s, ML, 0.92, 5.0, 0.22, [("BY ANGEL ONE", SANS, 7.5, GOLD, True, False, 260)])

    # two-tone headline (v7 cover device), then the client block
    deck.txt(s, ML, 2.30, 7.0, 0.85, [("Portfolio ", SANS, 40, WHITE, True),
                                      ("Review", SANS, 40, GOLD, True)])
    deck.txt(s, ML, 3.42, 7.0, 0.3, [("PREPARED FOR", SANS, 10, NT2, True, False, 260)])
    deck.txt(s, ML, 3.74, 7.0, 0.65, [(c["name"], SANS, 28, WHITE, True)])
    deck.rule(s, ML, 4.50, 3.4, GOLD, 0.03)
    # collapse repeated placeholder text (2026-07-27: a first-review client with neither
    # profile nor horizon on file printed "... · Not yet on file · Not yet on file")
    _segs = [c["account_type"]]
    if c["profile"] == c["horizon"]:
        _segs.append(f"Profile & horizon: {c['profile']}" if "file" in c["profile"].lower() else c["profile"])
    else:
        _segs += [c["profile"], c["horizon"]]
    deck.txt(s, ML, 4.72, 7.0, 0.4, [("   ·   ".join(_segs), SERIF, 12.5, NT3, False, True)])

    deck.txt(s, ML, 6.45, 7.0, 0.3, [("Co-founder in your journey of wealth creation",
                                      SERIF, 12, NT2, False, True)])
    demo_tag = ("[ILLUSTRATIVE, synthetic demo client; not a real portfolio]"
                if ctx.get("is_demo", True) else "")
    sep = "   ·   " if demo_tag else ""
    deck.txt(s, ML, 6.80, 7.0, 0.25, [(f"As of {c['as_of']}{sep}", SANS, 8.5, NT2, False),
                                      (demo_tag, SANS, 7.5, NT2, False, True)])
    return 1
