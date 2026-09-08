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


def _mix_clause(ctx, simple=False):
    """How the book is split, on ONE axis, plus how it is held on the other.

    eq_pct is the EQUITY ASSET CLASS as a share of the whole book and mf_pct is the share held
    through FUNDS. They are two different axes: a share bought through an equity fund is in both.
    Printing them side by side as "~76% direct equity, 61% funds" labelled the first as direct
    holdings, which it is not, and offered a reader two figures summing to 137%. Asset class is the
    split that answers the mandate question, so that is the one stated as percentages; the vehicle
    question is answered with counts, which cannot be mistaken for shares of the same whole."""
    tot = 0.0
    by = {}
    for h in (list(ctx.get("funds") or []) + list(ctx.get("equity") or [])
              + list(ctx.get("other") or [])):
        v = float(h.get("value_inr") or 0.0)
        k = (h.get("asset_class") or "").strip().title() or "Other"
        by[k] = by.get(k, 0.0) + v
        tot += v
    if not tot:
        return ""
    order = ["Equity", "Fixed Income", "Alternates", "Cash", "Other"]
    parts = [(k, by[k] / tot * 100.0) for k in order if by.get(k)]
    parts += [(k, v / tot * 100.0) for k, v in by.items() if k not in order]
    words = {"Fixed Income": "fixed income" if not simple else "bonds and debt funds",
             "Alternates": "alternates", "Equity": "equity", "Cash": "cash", "Other": "other"}
    return ", ".join(f"{p:.0f}% {words.get(k, k.lower())}" for k, p in parts if p >= 0.5)


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    simple = reg == "simple"
    c = ctx["client"]
    ips = ctx["ips"]
    t = ctx["totals"]
    stance = (ctx.get("house_view") or {}).get("stance") or {}

    title = "What we manage, and how we measure it" if simple else "Mandate, construction and benchmark"
    s = deck.content(0, "Understanding", "Our understanding", title)

    # ---- LEFT: 'our understanding' prose + NDPMS execution note ----
    lx, lw = ML, 6.05
    deck.txt(s, lx, 1.80, lw, 0.2, [("OUR UNDERSTANDING", SANS, 8.5, SLATE, True, False, 120)])
    # first-review accounts may not have a horizon/construction on file yet (no IPS) — phrase
    # around the gap honestly instead of printing "None" or "built not yet on file"
    horizon_known = ips.get('horizon_yrs') is not None
    horizon_txt = f"{ips['horizon_yrs']} years or more" if horizon_known else "a horizon to be agreed with you"
    horizon_txt_formal = f"a {ips['horizon_yrs']}-year-plus horizon" if horizon_known else "a horizon still to be agreed with you"
    construction_known = (c.get('construction') or '').strip().lower() not in ('', 'not yet on file')
    if simple:
        prose = (f"We look after the {c['name']} portfolio under a non-discretionary mandate: "
                 f"we advise, and you approve every trade yourself. The aim is to grow your money "
                 f"over {horizon_txt}, favouring good-quality businesses, using a "
                 f"‘core plus satellites’ style. Right now the money is about "
                 f"{_mix_clause(ctx, simple=True)}, held across {t['n_funds']} funds and "
                 f"{t['n_stocks']} shares you own directly.")
    else:
        built_clause = f", built {c['construction'].lower()}" if construction_known else ""
        prose = (f"The {c['name']} portfolio is managed under a {c['account_type']} mandate, we advise, "
                 f"you authorise every trade. The stated objective is long-term capital growth with a "
                 f"quality bias over {horizon_txt_formal}{built_clause}. "
                 f"The book today runs ~{_mix_clause(ctx)} by asset class, held across "
                 f"{t['n_funds']} schemes and {t['n_stocks']} directly-owned stocks.")
    deck.txt(s, lx, 2.06, lw, 1.9, [(prose, SERIF, 11.5, INK, False)], ls=1.16)

    note_body = ("Nothing in this review is executed until you authorise it. Every recommendation is "
                 "Sell, Trim or Hold on a holding you already own · never a solicitation to buy.")
    # WHERE THE CLIENT HAS DIRECTED SOMETHING, this page has to say so, because it is the page that
    # tells the reader what a call on the following sixty pages means. Without it the deck's own
    # framing ("every recommendation is Sell, Trim or Hold") is contradicted by every table in it.
    _cd = ctx.get("client_directive") or {}
    if _cd.get("exits") or _cd.get("retains"):
        _instr = (_cd.get("instruction") or "").strip().rstrip(".")
        note_body += (" Holdings marked EXIT (CLIENT) or RETAIN are your own instructions, "
                      "recorded here and priced, and are not calls of ours.")
    deck.callout(s, lx, 4.15, lw, 1.55, "Non-discretionary, you authorise every trade",
                 note_body, kind="human")

    # ---- RIGHT: core-satellite definition + benchmark record ----
    rx = 7.30
    rw = RX - rx
    # client copy: simple, marketable, never internal-workflow language (Principal 2026-07-26 —
    # no '[OPINION…]' tags, no 'advisory to formalise', no ticket codes, no blend percentages)
    cs_body = ("A stable core of quality businesses does the compounding; smaller satellite "
               "positions around it aim to add return without disturbing the core. Steady at "
               "the centre, selective at the edges.")
    deck.callout(s, rx, 1.72, rw, deck.callout_h(rw, cs_body, min_h=1.4),
                 "What is core–satellite?", cs_body, kind="note")

    # benchmark record — plain client language
    by = 4.00
    deck.rect(s, rx, by, rw, 1.70, fill=PANEL, round_=0.04)
    deck.rect(s, rx, by, 0.06, 1.70, fill=NAVY)
    deck.txt(s, rx + 0.20, by + 0.14, rw - 0.4, 0.24, [("HOW WE MEASURE PROGRESS", SANS, 9.5, NAVY, True, False, 60)])
    # Indexed with [] these four keys made a client page hostage to the desk's own wording: rename
    # one stance in house_view.json and this module raises, and a raise here used to take the whole
    # mandate page out of the deck with nothing on the deck to say so. A stance the published view
    # does not carry is simply not claimed.
    _st = ((ctx.get("house_view") or {}).get("stance_all") or {}) | dict(stance or {})

    def _s(k):
        return str(_st.get(k) or "").strip()

    basis = [b for b in (
        (f"Foreign equity, {_s('Foreign equity')}" if _s("Foreign equity") else ""),
        (f"Gold & silver, {_s('Gold & silver')}" if _s("Gold & silver") else ""),
        ("; ".join(p for p in (
            (f"Low-vol / value {_s('Low-vol / value').lower()}" if _s("Low-vol / value") else ""),
            (f"momentum {_s('Momentum').lower()}" if _s("Momentum") else "")) if p)),
    ) if b]
    if not basis:
        basis = ["Against our published house view of markets, not a single index."]
    deck.txt(s, rx + 0.20, by + 0.42, rw - 0.4, 0.24,
             [("Against our house-view mix of markets, not a single index:", SERIF, 9.5, INK, False, True)])
    for i, b in enumerate(basis):
        deck.txt(s, rx + 0.20, by + 0.72 + i * 0.22, rw - 0.4, 0.2,
                 [("·  ", SANS, 9, GOLD, True), (b, SERIF, 9.5, INK, False, True)])
    deck.txt(s, rx + 0.20, by + 1.42, rw - 0.4, 0.24,
             [("A formal named benchmark will be agreed with you.", SERIF, 8.5, SLATE, False, True)])

    # ---- BOTTOM: pointer to the scoring method (gist only — never the blend weights) ----
    deck.rule(s, ML, 5.92, UW, HAIR, 0.008)
    deck.txt(s, ML, 6.02, UW, 0.24, [("HOW EVERY HOLDING IS SCORED", SANS, 8.5, SLATE, True, False, 120)])
    ptr = ("Every holding earns an Ionic Score out of 100, blending the long-term health of the "
           "business with how the market is treating it now, with built-in safety checks on debt "
           "and liquidity. The score flags; our team decides. Full method in Section 02.")
    deck.txt(s, ML, 6.28, UW, 0.5, [(ptr, SERIF, 10, INK, False, True)], ls=1.05)

    deck.score_band(s)   # F13: score-position band attaches on this slide
    return 1
