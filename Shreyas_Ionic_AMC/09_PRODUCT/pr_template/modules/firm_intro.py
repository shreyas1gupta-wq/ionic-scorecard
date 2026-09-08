# -*- coding: utf-8 -*-
"""firm_intro: who Ionic Wealth is, before the review of what the client owns.

Four pages that sit immediately after the cover, in the order the desk uses them:
  the proposal title page, the group's scale, the co-founders, the firm's own claimed edge,
  and the desk's current asset-class view.

NOTHING HERE IS WRITTEN IN THIS FILE. Every figure, name, record and stance comes from
scores/firm_profile.json, published centrally beside the calls and the house view, for the same
reason those are: an advisor cannot edit the firm's AUM or a co-founder's record to suit a meeting,
and two advisors cannot send two different versions of the firm in the same week. A deck built
without that file simply skips these pages rather than inventing a credential.
"""
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

from slidekit import (NAVY, NT2, NT3, GOLD, INK, SLATE, PANEL, HAIR, WHITE,
                      SERIF, SANS, ML, UW, RX, clip_clause)

SECTION_NO, SECTION = 0, "Understanding"
STANCE_COLOR = {"CONSTRUCTIVE": NAVY, "CAUTIOUS": GOLD, "UNDER PRESSURE": GOLD,
                "STAGGERED": NT2, "SELECTIVE": NT2}


def _title_page(deck, F, ctx):
    """The proposal title page. Deliberately quiet: a name, a date and the firm's line."""
    s = deck.slide()
    cl = ctx["client"]
    deck.rect(s, 0, 0, 13.333, 7.5, fill=NAVY)
    deck.txt(s, ML, 2.55, UW, 0.36,
             [(F.get("tagline", ""), SANS, 13, GOLD, True, False, 60)])
    deck.txt(s, ML, 3.05, UW, 0.95,
             [(F.get("proposal_title", "Portfolio Review & Proposal"), SANS, 40, WHITE, True)])
    deck.rule(s, ML, 4.22, 3.0, GOLD, 0.028)
    deck.txt(s, ML, 4.55, UW, 0.44,
             [(cl.get("name", ""), SANS, 19, WHITE, True),
              ("     as of %s" % cl.get("as_of", ""), SERIF, 13, NT3, False)])
    return 1


def _highlights(deck, F):
    H = F.get("highlights") or {}
    if not H:
        return 0
    s = deck.content(SECTION_NO, SECTION, "Key highlights",
                     H.get("heading", "IONIC Group"))
    deck.txt(s, ML, 1.62, UW, 0.28, [(H.get("lead", ""), SERIF, 11.5, SLATE, False, True)])

    stats = H.get("stats") or []
    if stats:
        cw = UW / max(1, len(stats))
        for i, st in enumerate(stats):
            x = ML + i * cw
            deck.rect(s, x + 0.05, 2.05, cw - 0.18, 1.30, fill=PANEL, round_=0.05)
            deck.rect(s, x + 0.05, 2.05, cw - 0.18, 0.045, fill=GOLD)
            deck.txt(s, x + 0.22, 2.24, cw - 0.5, 0.46,
                     [(st.get("figure", ""), SANS, 23, NAVY, True)])
            deck.txt(s, x + 0.22, 2.74, cw - 0.5, 0.30,
                     [(st.get("label", ""), SANS, 10, INK, True)])
            if st.get("note"):
                deck.txt(s, x + 0.22, 3.02, cw - 0.5, 0.26,
                         [(st["note"], SERIF, 9, SLATE, False, True)])

    profiles = H.get("client_profiles") or []
    if profiles:
        deck.txt(s, ML, 3.72, UW, 0.24,
                 [(H.get("client_profiles_heading", "Advisory client profiles").upper(),
                   SANS, 9, NAVY, True, False, 80)])
        percol = (len(profiles) + 1) // 2
        cw2 = UW / 2
        for i, p in enumerate(profiles):
            col, row = i // percol, i % percol
            x, y = ML + col * cw2, 4.06 + row * 0.62
            deck.oval(s, x, y + 0.09, 0.10, GOLD)
            deck.txt(s, x + 0.22, y - 0.02, cw2 - 0.5, 0.26,
                     [(p.get("who", ""), SANS, 11, INK, True)])
            deck.txt(s, x + 0.22, y + 0.24, cw2 - 0.5, 0.28,
                     [(p.get("what", ""), SERIF, 9.5, SLATE, False, True)])
    if H.get("footnote"):
        deck.source(s, H["footnote"])
    return 1


def _founders(deck, F):
    fo = F.get("founders") or []
    if not fo:
        return 0
    s = deck.content(SECTION_NO, SECTION, "Who you are working with",
                     F.get("founders_heading", "Co-founders"))
    cw = UW / max(1, len(fo))
    for i, p in enumerate(fo):
        x = ML + i * cw
        deck.rect(s, x + 0.06, 2.00, cw - 0.20, 3.55, fill=PANEL, round_=0.06)
        deck.rect(s, x + 0.06, 2.00, cw - 0.20, 0.045, fill=NAVY)
        deck.txt(s, x + 0.26, 2.24, cw - 0.6, 0.34, [(p.get("name", ""), SANS, 14, NAVY, True)])
        deck.txt(s, x + 0.26, 2.60, cw - 0.6, 0.26,
                 [(p.get("title", ""), SANS, 9.5, GOLD, True, False, 40)])
        y = 3.00
        for line in (p.get("record") or []):
            deck.oval(s, x + 0.28, y + 0.07, 0.07, NT2)
            deck.txt(s, x + 0.46, y - 0.04, cw - 0.78, 0.34,
                     [(line, SERIF, 9.5, INK, False, True)], ls=1.0)
            y += 0.40
        if p.get("quote"):
            deck.rule(s, x + 0.26, 4.86, cw - 0.62, HAIR, 0.008)
            deck.txt(s, x + 0.26, 5.00, cw - 0.62, 0.48,
                     [("“" + p["quote"] + "”", SERIF, 10.5, NAVY, False, True)], ls=1.05)
    return 1


def _moat(deck, F):
    blocks = F.get("moat") or []
    if not blocks:
        return 0
    s = deck.content(SECTION_NO, SECTION, F.get("moat_strapline", "Our edge"),
                     F.get("moat_heading", "Strong domain expertise"))
    cw = UW / 2
    for i, b in enumerate(blocks[:4]):
        col, row = i % 2, i // 2
        x, y0 = ML + col * cw, 2.02 + row * 2.42
        deck.rect(s, x + 0.05, y0, cw - 0.20, 2.22, fill=PANEL, round_=0.05)
        deck.rect(s, x + 0.05, y0, 0.05, 2.22, fill=GOLD)
        deck.txt(s, x + 0.28, y0 + 0.18, cw - 0.6, 0.30,
                 [(b.get("title", ""), SANS, 12.5, NAVY, True)])
        y = y0 + 0.58
        for pt in (b.get("points") or [])[:4]:
            deck.oval(s, x + 0.30, y + 0.07, 0.07, NT2)
            deck.txt(s, x + 0.48, y - 0.04, cw - 0.82, 0.38,
                     [(clip_clause(pt, 150), SERIF, 9, INK, False, True)], ls=1.0)
            y += 0.40
    return 1


def _asset_view(deck, F):
    """Three asset classes to a page, in one full-height row.

    Six of these in a two-by-three grid did not fit: the lower row ran into the source strip and
    the tactical lines ran into the card below them, five collisions on one page. Each card needs
    the height, so the page takes three and there are two pages.
    """
    rows = F.get("asset_class_view") or []
    if not rows:
        return 0
    src = F.get("asset_class_view_source")
    pages = [rows[i:i + 3] for i in range(0, len(rows), 3)]
    n = 0
    for pi, chunk in enumerate(pages):
        title = F.get("asset_class_view_heading", "Asset class view")
        if len(pages) > 1:
            title += "  (%d of %d)" % (pi + 1, len(pages))
        s = deck.content(SECTION_NO, SECTION, F.get("asset_class_view_sub", ""), title)
        cw = UW / 3
        for i, a in enumerate(chunk):
            x, y0 = ML + i * cw, 2.02
            deck.rect(s, x + 0.06, y0, cw - 0.20, 4.30, fill=PANEL, round_=0.06)
            col_st = STANCE_COLOR.get(str(a.get("stance", "")).upper(), NT2)
            deck.rect(s, x + 0.06, y0, cw - 0.20, 0.05, fill=col_st)
            deck.txt(s, x + 0.26, y0 + 0.20, cw - 0.58, 0.32,
                     [(a.get("asset", ""), SANS, 13, NAVY, True)])
            deck.txt(s, x + 0.26, y0 + 0.54, cw - 0.58, 0.24,
                     [(a.get("stance", ""), SANS, 9, col_st, True, False, 70)])
            deck.txt(s, x + 0.26, y0 + 0.86, cw - 0.58, 1.05,
                     [(clip_clause(a.get("read", ""), 230), SERIF, 9, INK, False, True)], ls=1.06)
            y = y0 + 2.02
            for lab, val in (a.get("rows") or [])[:3]:
                deck.txt(s, x + 0.26, y, cw - 0.58, 0.20,
                         [(lab, SANS, 7.5, SLATE, True, False, 60)])
                deck.txt(s, x + 0.26, y + 0.20, cw - 0.58, 0.52,
                         [(clip_clause(val, 120), SERIF, 8.5, INK, False, True)], ls=1.02)
                y += 0.74
        deck.source(s, ("Source: %s. Positioning is the desk's published view and is reviewed on "
                        "its own cadence, not per client." % src) if src else
                       "The desk's published positioning, reviewed on its own cadence.")
        n += 1
    return n


def render(deck, ctx, tier):
    F = ctx.get("firm") or {}
    if not F:
        return 0          # no published profile: say nothing rather than invent a credential
    reg = tier.get("register", "std")
    n = _title_page(deck, F, ctx)
    n += _highlights(deck, F)
    n += _founders(deck, F)
    # the plainest deck keeps the introduction to who we are and what we have done; the firm's
    # own edge and the market view are a longer read and belong in the fuller tiers.
    if reg != "simple":
        n += _moat(deck, F)
        n += _asset_view(deck, F)
    return n
