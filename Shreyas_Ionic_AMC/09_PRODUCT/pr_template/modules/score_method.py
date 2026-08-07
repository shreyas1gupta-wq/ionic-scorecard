# -*- coding: utf-8 -*-
"""score_method (F13), How we score every stock.
Two horizons (3Y fundamentals-tilted / 1Y technical-tilted) blended 60/40 over 7 pillars in
3 client buckets (Quality & Growth / Value / Trend & Flow); safety gates cap at 40; the dominant
'THE HUMAN READ' callout says the score is the input, not the verdict; thresholds line at the foot.
Numbers are identical across registers (frozen methodology); only wording/density adapt.
"""
from slidekit import (NAVY, NAVYD, GOLD, INK, SLATE, HAIR, PANEL, WHITE, TRACK,
                      SELL, HOLD, AMBER, SELLBG, HOLDBG, AMBERBG, NT1, NT2, NT3,
                      SERIF, SANS, ML, RX, UW)
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

# 7 pillars, grouped into the 3 client-facing buckets. accent, bucket 3Y/1Y weight share.
BUCKETS = [
    ("Quality & Growth", NAVY, "What the business earns, and how fast it grows.", "40%", "32%",
     [("Quality", "ROE & ROCE vs peers"),
      ("Growth", "revenue growth, 3y & 1y")]),
    ("Value", GOLD, "What you pay for those earnings.", "18%", "16%",
     [("Value", "P/E, P/B & FCF yield vs sector")]),
    ("Trend & Flow", NT1, "What the price and the big investors are actually doing.", "42%", "52%",
     [("Stage / Technical", "price trend"),
      ("Sector & Macro", "regime fit"),
      ("Ownership Flow", "FII / DII flows"),
      ("Accumulation", "smart-money volume trend")]),
]

LABELS = {
    "hni":    {"title": "Two horizons, seven pillars, and one human call",
               "human": ("The Ionic Score ranks and flags candidates; it is the INPUT, not the verdict. "
                         "Every Sell, Trim and Hold that follows is confirmed by the Portfolio Review "
                         "team, who override the number when the business case demands it · a low score "
                         "on a durable franchise can still be a Hold, and vice-versa.")},
    "std":    {"title": "Two horizons, seven pillars, and one human call",
               "human": ("The Ionic Score ranks and flags candidates, it is the input, not the verdict. "
                         "Every Sell, Trim and Hold on the next pages is confirmed by the Portfolio "
                         "Review team, who can and do override the number when the business case "
                         "demands it.")},
    "simple": {"title": "A score to guide us, a person to decide",
               "human": ("The score is a starting point, not the decision. A real person on our team "
                         "looks at every holding and makes the final call · the number only helps us "
                         "spot what to look at first.")},
}


def _recipe(deck, s, y):
    """Top strip: 3-year view + 1-year view = one blended Ionic Score."""
    h = 0.66
    opw = 0.42
    bw = (UW - 2 * opw) / 3.0
    x1 = ML
    x2 = ML + bw + opw
    x3 = ML + 2 * (bw + opw)

    def leg(x, eyebrow, sub, pct, dark=False):
        bg = NAVY if dark else PANEL
        deck.rect(s, x, y, bw, h, fill=bg, line=(None if dark else HAIR), round_=0.06)
        if not dark:
            deck.rect(s, x, y, 0.06, h, fill=GOLD)
        ec = WHITE if dark else NAVY
        sc = NT3 if dark else SLATE
        deck.txt(s, x + 0.20, y + 0.11, bw - 1.0, 0.26,
                 [(eyebrow, SANS, 9.5, ec, True, False, 40)])
        deck.txt(s, x + 0.20, y + 0.37, bw - 1.0, 0.24, [(sub, SERIF, 9, sc, False, True)])
        if pct:
            deck.txt(s, x + bw - 0.95, y + 0.10, 0.80, 0.5,
                     [(pct, SANS, 20, ec, True)], align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)

    leg(x1, "3-YEAR VIEW", "Fundamentals-led", "")
    leg(x2, "1-YEAR VIEW", "Market-behaviour-led", "")
    leg(x3, "IONIC SCORE", "One number, 0 to 100", "", dark=True)
    for ox, sym in ((x1 + bw, "+"), (x2 + bw, "=")):
        deck.txt(s, ox, y, opw, h, [(sym, SANS, 20, SLATE, True)],
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def _bucket_card(deck, s, x, y, w, h, spec, simple):
    name, accent, sub, w3, w1, pillars = spec
    deck.rect(s, x, y, w, h, fill=PANEL, line=HAIR, round_=0.05)
    deck.rect(s, x, y, w, 0.09, fill=accent, round_=0.0)
    deck.txt(s, x + 0.18, y + 0.20, w - 0.32, 0.28, [(name.upper(), SANS, 11, INK, True, False, 20)])
    deck.txt(s, x + 0.18, y + 0.48, w - 0.32, 0.36,
             [(sub, SERIF, 9, SLATE, False, True)], ls=1.02)
    py = y + 0.86
    for pn, pd in pillars:
        runs = [("•  ", SANS, 9, accent, True), (pn, SANS, 9, INK, True)]
        if not simple:
            runs.append((" · " + pd, SERIF, 8, SLATE, False, True))
        deck.txt(s, x + 0.18, py, w - 0.30, 0.22, runs)
        py += 0.215


def _threshold_cell(deck, s, x, y, w, band, arrow, rec, kind):
    bg, tc = {"Sell": (SELLBG, SELL), "Trim": (AMBERBG, AMBER), "Hold": (HOLDBG, HOLD)}[kind]
    deck.rect(s, x, y, w, 0.44, fill=bg, line=tc, lw=0.75, round_=0.08)
    deck.txt(s, x + 0.14, y, w - 0.9, 0.44,
             [(band, SANS, 9, INK, True)], anchor=MSO_ANCHOR.MIDDLE)
    deck.pill(s, x + w - 0.82, y + 0.10, rec, w=0.68, kind=kind)


def render(deck, ctx, tier):
    reg = tier["register"]
    L = LABELS.get(reg, LABELS["std"])
    simple = reg == "simple"
    s = deck.content(3, "The Equity Book", "How we score every stock", L["title"])

    # 1) recipe strip -------------------------------------------------------
    _recipe(deck, s, 1.82)

    # 2) three bucket cards -------------------------------------------------
    gy = 2.66
    gap = 0.28
    cw = (UW - 2 * gap) / 3.0
    ch = 1.86
    for i, spec in enumerate(BUCKETS):
        _bucket_card(deck, s, ML + i * (cw + gap), gy, cw, ch, spec, simple)

    # 3) safety-gate one-liner ---------------------------------------------
    gyl = gy + ch + 0.16
    if simple:
        gate = ("If a company carries too much debt for its kind of business, or trades too thinly, "
                "its score is capped at 40, a built-in safety brake.")
    else:
        gate = ("A weak balance sheet or thin liquidity caps the score at 40. The debt bar is judged "
                "in context: by industry norms (utilities and lenders run levered), sovereign or "
                "group backing, and access to capital, not one fixed ratio.")
    deck.txt(s, ML, gyl, UW, 0.30,
             [("SAFETY GATES   ", SANS, 9, SELL, True, False, 40), (gate, SERIF, 10, INK, False)],
             anchor=MSO_ANCHOR.MIDDLE)

    # 4) THE HUMAN READ — dominant callout ---------------------------------
    hy = gyl + 0.40
    deck.callout(s, ML, hy, UW, 1.02, "The human read", L["human"], kind="human")

    # 5) thresholds strip ---------------------------------------------------
    ty = hy + 1.14
    gap2 = 0.22
    tw = (UW - 2 * gap2) / 3.0
    if simple:
        cells = [("Score under 40", "Sell", "Sell"),
                 ("40 to 50 + a risk flag", "Trim", "Trim"),
                 ("50 and above", "Hold", "Hold")]
    else:
        cells = [("Below 40, either horizon", "Sell", "Sell"),
                 ("40–50, only with a concentration / risk flag", "Trim", "Trim"),
                 ("50 and above", "Hold", "Hold")]
    for i, (band, arrow, rec) in enumerate(cells):
        _threshold_cell(deck, s, ML + i * (tw + gap2), ty, tw, band, arrow, rec, rec)
    deck.source(s, "Ionic scoring methodology (proprietary, held by the desk) · a 40-50 score alone is a "
                   "watch signal; Trim needs a concentration or risk flag · every call reviewed by the desk. "
                   "A directed liquidity Trim (client cash need, any score band) is a separate, explicitly "
                   "labelled case — not this score-band rule.")
    deck.score_band(s)
    return 1
