# -*- coding: utf-8 -*-
"""contents_legend (F, core), Contents & how-to-read.
Section list in the reading order (Understanding -> X-ray -> Funds -> Equity ->
Recommendations -> Annexure -- restructured FM #11, 2026-08-06: portfolio statistics, then
MF, then direct equity) + a one-time vocabulary strip (Sell/Trim/Hold; review,
not a solicitation) + the Ionic-Score positioning legend + a per-build tag naming the
annexure modules attached this cycle. Language/density adapt to tier['register']; the
section set and the vocabulary are identical across registers."""
from slidekit import (NAVY, NT2, NT3, GOLD, INK, SLATE, HOLD, SELL, AMBER, PANEL,
                      HAIR, WHITE, SERIF, SANS, ML, UW, RX)
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

# reading-order sections (Understanding is front matter -> gold dot; 01-05 have dividers)
# Which chapter each module belongs to, read off the engine's own registry so the two cannot drift.
try:
    from engine import MODULES as _ENG_MODULES
    _SEC_OF = {m: sec for m, sec, _n, _c in _ENG_MODULES if not m.startswith("_div")}
except Exception:
    _SEC_OF = {}

_SECTIONS = [
    (None, "Understanding",   "Your mandate, policy bands and the headline plan",
                              "What you asked us to do"),
    ("01", "Portfolio X-ray", "Where the book stands today",
                              "A quick look at what you own now"),
    # restructure (FM #11, 2026-08-06): MF before direct equity -- portfolio statistics,
    # then MF, then direct equity.
    ("02", "The Fund Book",   "Your funds, upside, downside, consistency",
                              "Your mutual funds, checked properly"),
    ("03", "The Equity Book", "Every direct holding, scored and read",
                              "Each share you hold, with our view"),
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
    # The contents page is the reader's map of THIS document. Printed from a fixed list it promised
    # an Equity Book chapter on every mutual-fund book, six sections on a deck carrying five. The
    # engine's probe pass records which modules render, so the chapter list is the chapters that
    # exist.
    _r = ctx.get("_rendered")
    if _r:
        _live = {str(sec) for mod, sec in _SEC_OF.items() if _r.get(mod)}
        sections = [row for row in _SECTIONS if row[0] is None or row[0].lstrip("0") in
                    {x.lstrip("0") for x in _live}]
    else:
        sections = list(_SECTIONS)
    _NUMWORD = {2: "TWO", 3: "THREE", 4: "FOUR", 5: "FIVE", 6: "SIX", 7: "SEVEN"}
    lx = ML
    deck.txt(s, lx, 1.80, 5.2, 0.24,
             [(f"THE {_NUMWORD.get(len(sections), len(sections))} SECTIONS",
               SANS, 8.5, SLATE, True, False, 120)])
    for i, (num, name, desc_std, desc_simple) in enumerate(sections):
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
    # "Redeem-to-Direct" displays as "Switch" now (Principal 2026-07-27) -- dropped as its own
    # legend row since it would be a second, identical-looking "Switch" pill
    pills_row(rx + 0.95, 2.57, [("Hold", 0.62, "Hold"), ("Trim", 0.62, "Trim"), ("Switch", 0.72, "Switch"),
                                ("Exit", 0.6, "Exit")])
    # THE TWO WORDS THAT ARE NOT OURS. Where a client has directed an exit, "Exit (client)" and
    # "Retain" appear on this deck's tables against a quarter of the book while this panel, the
    # one page that teaches the reader the vocabulary, listed neither. A reader meeting an unlabelled
    # word in a table of the firm's calls will read it as one of the firm's calls.
    _cd = ctx.get("client_directive") or {}
    _y = 2.98
    if _cd.get("exits") or _cd.get("retains"):
        deck.txt(s, rx, 2.96, 0.9, 0.24, [("YOURS", SANS, 8, NT2, True, False, 60)],
                 anchor=MSO_ANCHOR.MIDDLE)
        _p = []
        if _cd.get("exits"):
            _p.append(("Exit (client)", 1.05, "Exit (client)"))
        if _cd.get("retains"):
            _p.append(("Retain", 0.72, "Retain"))
        pills_row(rx + 0.95, 2.95, _p)
        _y = 3.34
    vocab = ("A review of the holdings you already own; every call here applies to existing positions."
             if not simple else
             "A review of what you already own, and what we would do with each holding.")
    if _cd.get("exits") or _cd.get("retains"):
        vocab = "Every call above is ours; the two beside YOURS record your own instructions."
    deck.txt(s, rx, _y, rw, 0.4, [(vocab, SERIF, 10, INK, False, True)], ls=1.05)

    # ---- RIGHT-MID: score positioning legend ----
    # Two different scores, two different scales. The Ionic Score is the direct-equity score and
    # its 40 / 50 thresholds mean nothing on a book of funds; a deck that scores no share printed
    # its legend anyway, teaching the reader a scale no page in front of them uses. The legend
    # names whichever score the deck carries, and is dropped when it carries neither.
    _has_stock_score = any(e.get("ionic_score") is not None for e in (ctx.get("equity") or []))
    _has_fund_score = any(f.get("qfra") is not None for f in (ctx.get("funds") or []))
    if not (_has_stock_score or _has_fund_score):
        return 1
    _dy = 0.0 if _y == 2.98 else 0.44
    deck.rule(s, rx, 3.50 + _dy, rw, HAIR, 0.008)
    deck.txt(s, rx, 3.62 + _dy, rw, 0.24,
             [(("THE IONIC SCORE, POSITIONED" if _has_stock_score
                else "THE FUND SCORE, POSITIONED"), SANS, 8.5, SLATE, True, False, 120)])

    def chip(cy, color, lab):
        deck.rect(s, rx, cy, 0.32, 0.20, fill=color, round_=0.4)
        deck.txt(s, rx + 0.46, cy - 0.04, rw - 0.5, 0.28, [(lab, SERIF, 10.5, INK, False)],
                 anchor=MSO_ANCHOR.MIDDLE)

    if _has_stock_score:
        chip(3.98 + _dy, SELL,  "Below 40  ·  Sell candidate")
        chip(4.31 + _dy, AMBER, "40 to 50  ·  watch zone; Trim only with a concentration or risk flag")
        chip(4.64 + _dy, HOLD,  "50 and above  ·  Hold")
    else:
        # The fund score is a share of the scheme's OWN peer group beaten, so the bottom third is
        # the line the desk's framework actually draws, not 40 and 50.
        chip(3.98 + _dy, SELL,  "Bottom third of its own category  ·  Sell candidate")
        chip(4.31 + _dy, AMBER, "Middle of its category  ·  held and watched")
        chip(4.64 + _dy, HOLD,  "Top third of its own category  ·  Hold")
    deck.txt(s, rx, 5.02 + _dy, rw, 0.4,
             [(("The Ionic Score flags candidates; the Portfolio Review team confirms every call."
                if _has_stock_score else
                "The fund score flags candidates; the Portfolio Review team confirms every call."),
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
    deck.txt(s, ML + 0.22, 6.04, UW - 0.3, 0.55,
             [("THIS BUILD   ", SANS, 8, SLATE, True, False, 80), (tag, SERIF, 9.5, tk, False, True)])
    return 1
