# -*- coding: utf-8 -*-
"""mf_methodology (NEW, FM #12), how we assess every fund. Client-safe description of the two
fund-quality frameworks actually in use TODAY, stated honestly: the short-term framework (6-month
capture ratio, the only one of the two with a Sell verdict) and the long-term framework (a
multi-year selection framework, no Sell verdict, veto-only). Hybrid AND debt funds sit outside
BOTH frameworks today and are reviewed by hand — disclosed here, not smoothed over.

No internal codenames (tellscan's INTERNAL_JARGON bucket forbids "QFRA"/"SENTINEL"/"MERIT" etc
client-side) and no vendor/source name for the underlying fund-data feed — those belong on the
internal PAC deck, not a client page. Heights are ALWAYS callout_h-derived, never guessed, per
the standing clip-risk lesson."""
from slidekit import NAVY, GOLD, INK, SLATE, ML, UW

LABELS = {
    "hni":    {"eyebrow": "How we assess every fund",
               "title": "Two frameworks today, and one honest gap"},
    "std":    {"eyebrow": "How we assess every fund",
               "title": "Two frameworks today, and one honest gap"},
    "simple": {"eyebrow": "How we check your funds",
               "title": "Two checks we run, and what we still do by hand"},
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    simple = reg == "simple"
    L = LABELS.get(reg, LABELS["std"])
    funds = ctx["funds"]
    n_hybrid = sum(1 for f in funds if f.get("category") == "hybrid")
    n_debt = sum(1 for f in funds if f.get("category") == "debt")
    n_hand = n_hybrid + n_debt
    n_covered = len(funds) - n_hand

    s = deck.content(2, "The Fund Book", L["eyebrow"], L["title"])

    half = (UW - 0.3) / 2
    if simple:
        b1 = ("The last six months: how much of the market's fall the fund took on. The only "
              "one of our two checks that can tell us to sell a fund.")
        b2 = ("Several years, to find the strongest fund per category. No 'sell' answer, only "
              "'keep going' or 'top pick' — it can block a sell, never start one.")
    else:
        b1 = ("How much of a category benchmark's fall each fund took in the trailing six "
              "months, against a pass line set for that category. The only one of our two "
              "checks with a Sell verdict, and the only one that can start a sell.")
        b2 = ("A multi-year selection framework naming the strongest one or two funds per "
              "category. No Sell verdict — 'stays active' or 'top pick' only. Can veto a sell "
              "the short-term check wants, never originate one.")
    ch = max(deck.callout_h(half, b1, min_h=1.15, max_h=1.45),
             deck.callout_h(half, b2, min_h=1.15, max_h=1.45))
    deck.callout(s, ML, 1.90, half, ch, "SHORT-TERM CHECK · 6-MONTH CAPTURE", b1, kind="note")
    deck.callout(s, ML + half + 0.3, 1.90, half, ch, "LONG-TERM CHECK · MULTI-YEAR SELECTION",
                 b2, kind="note")

    # ---- how a fund actually gets sold, stated precisely ----
    y = 1.90 + ch + 0.14
    rule = ("Only sold when the short-term check flags it; the long-term check can soften that "
            "to a Hold, never create a sell on its own. Disagreement is written down, not "
            "resolved quietly." if not simple else
            "We only suggest selling on the six-month check's say. The multi-year check can "
            "save a fund from that call, never cause one alone.")
    rh = deck.callout_h(UW, rule, min_h=0.5, max_h=0.65)
    deck.callout(s, ML, y, UW, rh, "How a fund actually gets sold", rule, kind="human")

    # ---- quick counts, live from this book (kpi_strip's real footprint is ~0.92in
    # regardless of the h argument -- budgeted explicitly rather than guessed) ----
    y += rh + 0.14
    deck.kpi_strip(s, [
        (str(n_covered), "Funds under one of the two checks" if not simple else "Checked by a framework"),
        (str(n_hand), "Reviewed by hand today" if not simple else "Reviewed by a person"),
        (str(len(funds)), "Funds in this book" if not simple else "Funds you hold"),
    ], y=y)
    y += 0.94

    # ---- the honest gap: hybrids AND debt sit outside both checks today ----
    gap_kicker = "WHAT WE DO BY HAND TODAY"
    if n_hand == 0:
        gap_body = ("Every fund here falls inside one of the two checks above; none needed a "
                     "hand review this cycle." if not simple else
                     "Both checks above cover every fund you hold; nothing needed a manual look.")
    else:
        parts = []
        if n_hybrid:
            parts.append(f"{n_hybrid} mixing shares and bonds")
        if n_debt:
            parts.append(f"{n_debt} bond-only")
        which = " and ".join(parts)
        if simple:
            gap_body = (f"Neither check above fits {which} fund{'s' if n_hand != 1 else ''} — we "
                        "review these by hand, against a benchmark built from what each fund "
                        "actually holds.")
        else:
            gap_body = (f"Neither framework fits {which} fund{'s' if n_hand != 1 else ''}: no "
                        "single equity-style category benchmark applies. Reviewed by hand today, "
                        "against a benchmark built from each fund's own disclosed mix — a genuine "
                        "gap, disclosed rather than folded into a number implying coverage that "
                        "doesn't exist.")
    gh = deck.callout_h(UW, gap_body, min_h=0.55, max_h=1.1)
    deck.callout(s, ML, y, UW, gh, gap_kicker, gap_body, kind="warn")

    demo_tag = " Illustrative synthetic funds." if ctx.get("is_demo", False) else ""
    deck.source(s, f"Coverage counted from this book's own holdings, not assumed.{demo_tag}")
    return 1
