# -*- coding: utf-8 -*-
"""mandate_method (F9/F10, core), Our understanding: mandate, construction & benchmark.
'Our understanding' prose (from ctx client/ips/totals) · a 'What is core-satellite?' definition
callout (illustrative boilerplate, [OPINION]) · a typed benchmark record labelled a house-view
composite marked 'advisory to formalise' (never the bare 'Asset X house view' alias) · the NDPMS
execution note (client authorises before execution) · a 2-line pointer to the scoring method.
Score-position band attaches here (F13)."""
from slidekit import (NAVY, NT2, NT3, GOLD, INK, SLATE, HOLD, SELL, AMBER, PANEL, HAIR,
                      SERIF, SANS, ML, UW, RX)
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    simple = reg == "simple"
    c = ctx["client"]
    ips = ctx["ips"]
    t = ctx["totals"]
    stance = ctx["house_view"]["stance"]

    title = "What we manage, and how we measure it" if simple else "Mandate, construction and benchmark"
    s = deck.content(0, "Understanding", "Our understanding", title)

    # ---- LEFT: 'our understanding' prose + NDPMS execution note ----
    lx, lw = ML, 6.05
    deck.txt(s, lx, 1.80, lw, 0.2, [("OUR UNDERSTANDING", SANS, 8.5, SLATE, True, False, 120)])
    if simple:
        prose = (f"We look after the {c['name']} portfolio under a non-discretionary mandate: "
                 f"we advise, and you approve every trade yourself. The aim is to grow your money "
                 f"over {ips['horizon_yrs']} years or more, favouring good-quality businesses, using a "
                 f"‘core plus satellites’ style. Right now you hold about {t['eq_pct']:.0f}% shares, "
                 f"{t['mf_pct']:.0f}% funds and {t['cash_pct']:.0f}% cash, {t['n_stocks']} shares and "
                 f"{t['n_funds']} funds.")
    else:
        prose = (f"The {c['name']} portfolio is managed under a {c['account_type']} mandate, we advise, "
                 f"you authorise every trade. The stated objective is long-term capital growth with a "
                 f"quality bias over a {ips['horizon_yrs']}-year-plus horizon, built {c['construction'].lower()}. "
                 f"The book today runs ~{t['eq_pct']:.0f}% direct equity, {t['mf_pct']:.0f}% funds and "
                 f"{t['cash_pct']:.0f}% cash, across {t['n_stocks']} stocks and {t['n_funds']} schemes.")
    deck.txt(s, lx, 2.06, lw, 1.9, [(prose, SERIF, 11.5, INK, False)], ls=1.16)

    note_body = ("Nothing in this review is executed until you authorise it. Every recommendation is "
                 "Sell, Trim or Hold on a holding you already own · never a solicitation to buy.")
    deck.callout(s, lx, 4.15, lw, 1.55, "Non-discretionary, you authorise every trade",
                 note_body, kind="human")

    # ---- RIGHT: core-satellite definition + benchmark record ----
    rx = 7.30
    rw = RX - rx
    cs_body = ("A stable, low-turnover CORE (broad quality exposure that does the compounding) is "
               "surrounded by smaller SATELLITE positions · higher-conviction stocks and factor or "
               "thematic sleeves · that aim to add return without destabilising the core.  "
               "[OPINION · illustrative definition; advisory to ratify.]")
    deck.callout(s, rx, 1.72, rw, 2.10, "What is core–satellite?", cs_body, kind="note")

    # benchmark typed record
    by = 4.00
    deck.rect(s, rx, by, rw, 1.70, fill=PANEL, round_=0.04)
    deck.rect(s, rx, by, 0.06, 1.70, fill=NAVY)
    deck.txt(s, rx + 0.20, by + 0.14, rw - 1.6, 0.24, [("BENCHMARK", SANS, 9.5, NAVY, True, False, 60)])
    deck.pill(s, rx + rw - 1.55, by + 0.12, "Advisory to formalise", w=1.4, kind="Watch")
    deck.txt(s, rx + 0.20, by + 0.44, rw - 0.4, 0.24,
             [("Type   ", SANS, 8.5, SLATE, True, False, 60),
              ("Blended composite (house view)", SANS, 10, INK, True)])
    basis = [
        f"Foreign equity, {stance['Foreign equity']}",
        f"Gold & silver, {stance['Gold & silver']}",
        f"Low-vol / value {stance['Low-vol / value'].lower()}; momentum {stance['Momentum'].lower()}",
    ]
    for i, b in enumerate(basis):
        deck.txt(s, rx + 0.20, by + 0.72 + i * 0.22, rw - 0.4, 0.2,
                 [("·  ", SANS, 9, GOLD, True), (b, SERIF, 9.5, INK, False, True)])
    deck.txt(s, rx + 0.20, by + 1.42, rw - 0.4, 0.24,
             [("Not yet a named / APMI-tagged index, advisory to formalise (F9).",
               SERIF, 8.5, SLATE, False, True)])

    # ---- BOTTOM: pointer to the scoring method ----
    deck.rule(s, ML, 5.92, UW, HAIR, 0.008)
    deck.txt(s, ML, 6.02, UW, 0.24, [("HOW EVERY HOLDING IS SCORED", SANS, 8.5, SLATE, True, False, 120)])
    ptr = ("The Ionic Score combines a 3-year, fundamentals-led view with a 1-year, "
           "technical-tilted view (40%) across 7 pillars, with safety gates that cap weak names · "
           "it flags candidates; the team confirms. Full method in Section 02, The Equity Book.")
    deck.txt(s, ML, 6.28, UW, 0.5, [(ptr, SERIF, 10, INK, False, True)], ls=1.05)

    deck.score_band(s)   # F13: score-position band attaches on this slide
    return 1
