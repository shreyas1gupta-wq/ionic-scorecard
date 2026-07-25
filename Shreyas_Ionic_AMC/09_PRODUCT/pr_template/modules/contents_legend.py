# -*- coding: utf-8 -*-
"""contents_legend (F, core), Contents & how-to-read.
Section list in the reading order (Understanding -> X-ray -> Equity -> Funds ->
Recommendations -> Annexure) + a one-time vocabulary strip (Sell/Trim/Hold; review,
not a solicitation) + the Ionic-Score positioning legend + a per-build tag naming the
annexure modules attached this cycle. Language/density adapt to tier['register']; the
section set and the vocabulary are identical across registers."""
from slidekit import (NAVY, NT2, NT3, GOLD, INK, SLATE, HOLD, SELL, AMBER, PANEL,
                      HAIR, WHITE, SERIF, SANS, ML, UW, RX)
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

# reading-order sections (Understanding is front matter -> gold dot; 01-05 have dividers)
_SECTIONS = [
    (None, "Understanding",   "Your mandate, policy bands and the headline plan",
                              "What you asked us to do"),
    ("01", "Portfolio X-ray", "Where the book stands today",
                              "A quick look at what you own now"),
    ("02", "The Equity Book", "Every direct holding, scored and read",
                              "Each share you hold, with our view"),
    ("03", "The Fund Book",   "Your funds, upside, downside, consistency",
                              "Your mutual funds, checked properly"),
    ("04", "Recommendations", "The plan, the cost, the tax and the sequence",
                              "What we suggest, and what it costs"),
    ("05", "Annexure",        "Supporting detail, on request",
                              "Extra detail if you want it"),
]

_ANNEX_ORDER = ["opportunity_set", "quality_vs_price", "factor_profile", "growth_projection",
                "spotlight_holdings", "holdings_detail", "sell_cards", "scheme_overlap_full",
                "scheme_scorecards", "appendix"]
_ANNEX_LABEL = {"opportunity_set": "Opportunity set", "quality_vs_price": "Quality vs price",
                "factor_profile": "Factor profile", "growth_projection": "Growth projection",
                "spotlight_holdings": "Spotlight holdings", "holdings_detail": "Holdings detail",
                "sell_cards": "Sell cards", "scheme_overlap_full": "Scheme overlap",
                "scheme_scorecards": "Scheme scorecards", "appendix": "Appendix"}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    simple = reg == "simple"
    title = "What's inside, and the words we use" if simple else "Contents · vocabulary · score legend"
    s = deck.content(0, "", "How to read this review", title)

    # ---- LEFT: reading-order section list ----
    lx = ML
    deck.txt(s, lx, 1.80, 5.2, 0.24,
             [("THE SIX SECTIONS", SANS, 8.5, SLATE, True, False, 120)])
    for i, (num, name, desc_std, desc_simple) in enumerate(_SECTIONS):
        yy = 2.18 + i * 0.60
        if num:
            deck.txt(s, lx, yy - 0.02, 0.55, 0.32, [(num, SANS, 15, NT2, True)])
        else:
            deck.oval(s, lx + 0.10, yy + 0.09, 0.15, GOLD)
        deck.txt(s, lx + 0.62, yy - 0.03, 4.6, 0.28, [(name, SANS, 12.5, NAVY, True)])
        deck.txt(s, lx + 0.62, yy + 0.25, 4.7, 0.24,
                 [((desc_simple if simple else desc_std), SERIF, 9.5, SLATE, False, True)])

    # ---- column divider ----
    deck.vrule(s, 6.45, 1.85, 4.35, HAIR, 0.01)
    rx = 6.70
    rw = RX - rx

    # ---- RIGHT-TOP: vocabulary strip ----
    deck.txt(s, rx, 1.80, rw, 0.24, [("THE WORDS WE USE", SANS, 8.5, SLATE, True, False, 120)])

    def pills_row(px, py, items):
        cx = px
        for (t, w, k) in items:
            deck.pill(s, cx, py, t, w=w, kind=k)
            cx += w + 0.14

    deck.txt(s, rx, 2.20, 0.9, 0.24, [("EQUITY", SANS, 8, NT2, True, False, 60)], anchor=MSO_ANCHOR.MIDDLE)
    pills_row(rx + 0.95, 2.19, [("Sell", 0.62, "Sell"), ("Trim", 0.62, "Trim"), ("Hold", 0.62, "Hold")])
    deck.txt(s, rx, 2.58, 0.9, 0.24, [("FUNDS", SANS, 8, NT2, True, False, 60)], anchor=MSO_ANCHOR.MIDDLE)
    pills_row(rx + 0.95, 2.57, [("Hold", 0.62, "Hold"), ("Trim", 0.62, "Trim"), ("Switch", 0.72, "Switch"),
                                ("Redeem-to-Direct", 1.5, "Redeem-to-Direct"), ("Exit", 0.6, "Exit")])
    vocab = ("A review of the holdings you already own; every call here applies to existing positions."
             if not simple else
             "A review of what you already own, and what we would do with each holding.")
    deck.txt(s, rx, 2.98, rw, 0.4, [(vocab, SERIF, 10, INK, False, True)], ls=1.05)

    # ---- RIGHT-MID: Ionic-Score positioning legend ----
    deck.rule(s, rx, 3.50, rw, HAIR, 0.008)
    deck.txt(s, rx, 3.62, rw, 0.24, [("THE IONIC SCORE, POSITIONED", SANS, 8.5, SLATE, True, False, 120)])

    def chip(cy, color, lab):
        deck.rect(s, rx, cy, 0.32, 0.20, fill=color, round_=0.4)
        deck.txt(s, rx + 0.46, cy - 0.04, rw - 0.5, 0.28, [(lab, SERIF, 10.5, INK, False)],
                 anchor=MSO_ANCHOR.MIDDLE)

    chip(3.98, SELL,  "Below 40  ·  Sell candidate")
    chip(4.31, AMBER, "40 to 50  ·  watch zone; Trim only with a concentration or risk flag")
    chip(4.64, HOLD,  "50 and above  ·  Hold")
    deck.txt(s, rx, 5.02, rw, 0.4,
             [("The Ionic Score flags candidates; the Portfolio Review team confirms every call.",
               SERIF, 9.5, SLATE, False, True)], ls=1.05)

    # ---- BOTTOM: per-build annexure tag ----
    on = [_ANNEX_LABEL[m] for m in _ANNEX_ORDER if m in tier.get("optional_on", set())]
    if on:
        tag = "Annexure attached this cycle:   " + "   ·   ".join(on)
        tk = NAVY
    else:
        tag = "This cycle: core review only, no annexure attached (available on request)."
        tk = SLATE
    deck.rule(s, ML, 5.90, UW, HAIR, 0.008)
    deck.rect(s, ML, 6.08, 0.14, 0.14, fill=NT2, round_=0.3)
    deck.txt(s, ML + 0.22, 6.04, UW - 0.3, 0.24,
             [("THIS BUILD   ", SANS, 8, SLATE, True, False, 80), (tag, SERIF, 9.5, tk, False, True)])
    return 1
